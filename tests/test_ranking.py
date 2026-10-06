import numpy as np
import pytest

from reco.contracts import RecommendationRequest
from reco.data import Dataset, load_fixture
from reco.ranking import Ranker


@pytest.fixture(params=["popularity", "item_knn", "als_cpu"])
def ranker(request):
    source = load_fixture()
    history = tuple(event for event in source.ratings if event.timestamp < 25)
    return Ranker(source, history, request.param)


def test_all_prior_ratings_including_dislikes_are_excluded(ranker):
    response = ranker.recommend(RecommendationRequest(user_id=1, k=20))
    ids = [hit.movie_id for hit in response.items]
    assert not {1, 2, 3, 4} & set(ids)
    assert len(ids) == len(set(ids)) == 8
    assert response.catalog_exhausted
    assert all(np.isfinite(hit.score) for hit in response.items)


def test_prediction_catalog_excludes_future_movie(ranker):
    assert 13 not in ranker.columns
    with pytest.raises(ValueError, match="unavailable"):
        ranker.recommend(RecommendationRequest(liked_movie_ids=[13]))


def test_genre_filter_survives_catalog_exhaustion(ranker):
    response = ranker.recommend(RecommendationRequest(user_id=4, genre="Sci-Fi", k=20))
    assert {hit.movie_id for hit in response.items} == {11}
    assert response.catalog_exhausted


def test_sparse_fallback_and_zero_history(ranker):
    response = ranker.recommend(RecommendationRequest(liked_movie_ids=[1]))
    assert response.variant == "popularity"
    assert 1 not in {hit.movie_id for hit in response.items}
    if ranker.variant != "popularity":
        assert response.fallback_reason == "insufficient_history"
    zero = ranker.recommend(RecommendationRequest(user_id=7))
    assert zero.variant == "popularity"
    assert zero.items


def test_ephemeral_fold_in_does_not_mutate_model(ranker):
    factors = ranker.als.user_factors.copy() if ranker.als is not None else None
    first = ranker.recommend(RecommendationRequest(liked_movie_ids=[1, 2, 3]))
    second = ranker.recommend(RecommendationRequest(liked_movie_ids=[1, 2, 3]))
    assert [hit.movie_id for hit in first.items] == [hit.movie_id for hit in second.items]
    assert not {1, 2, 3} & {hit.movie_id for hit in first.items}
    if factors is not None:
        np.testing.assert_array_equal(factors, ranker.als.user_factors)


def test_unknown_identifiers_and_genres(ranker):
    with pytest.raises(ValueError, match="Unknown benchmark"):
        ranker.recommend(RecommendationRequest(user_id=999))
    with pytest.raises(ValueError, match="genre"):
        ranker.recommend(RecommendationRequest(liked_movie_ids=[], genre="NoSuchGenre"))


def test_popularity_counts_and_ties_have_independent_expected_order():
    source = load_fixture()
    history = tuple(event for event in source.ratings if event.timestamp < 25)
    ranker = Ranker(source, history, "popularity")
    result = ranker.recommend(RecommendationRequest(liked_movie_ids=[], k=5))
    # Movies 2 and 3 each have three positives. 1, 5, 6 each have two.
    assert [hit.movie_id for hit in result.items] == [2, 3, 1, 5, 6]
    assert [hit.score for hit in result.items] == [3, 3, 2, 2, 2]


def test_future_labels_cannot_change_training_scores():
    source = load_fixture()
    history = tuple(event for event in source.ratings if event.timestamp < 25)
    changed = tuple(
        event.model_copy(update={"rating": 1}) if event.timestamp >= 25 else event
        for event in source.ratings
    )
    other = Dataset(source.movies, changed, "changed-future")
    for variant in ["popularity", "item_knn", "als_cpu"]:
        first, second = Ranker(source, history, variant), Ranker(other, history, variant)
        request = RecommendationRequest(user_id=1)
        a, b = first.recommend(request), second.recommend(request)
        assert [hit.movie_id for hit in a.items] == [hit.movie_id for hit in b.items]
        np.testing.assert_allclose([hit.score for hit in a.items], [hit.score for hit in b.items])


def test_cpu_als_backend_is_selected_explicitly():
    source = load_fixture()
    ranker = Ranker(source, tuple(e for e in source.ratings if e.timestamp < 25), "als_cpu")
    assert type(ranker.als).__module__ == "implicit.cpu.als"


def test_training_does_not_treat_low_ratings_as_positive():
    source = load_fixture()
    ranker = Ranker(source, tuple(e for e in source.ratings if e.timestamp < 25), "popularity")
    assert ranker.popularity[ranker.columns[4]] == 0
    assert ranker.popularity[ranker.columns[12]] == 0
