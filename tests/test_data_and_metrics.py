import math

import pytest

from reco.contracts import Rating
from reco.data import Dataset, chronological_split, load_fixture
from reco.evaluation import evaluate, ranking_metrics
from reco.ranking import Ranker


def test_split_ties_never_cross_periods():
    events = tuple(
        Rating(user_id=1, movie_id=i + 1, rating=4, timestamp=ts)
        for i, ts in enumerate([1, 2, 2, 3, 4, 4, 5, 6, 7, 8])
    )
    split = chronological_split(events, 0.3, 0.6)
    assert split.validation_cutoff == 3
    assert split.test_cutoff == 5
    assert {event.timestamp for event in split.train} == {1, 2}
    assert {event.timestamp for event in split.validation} == {3, 4}
    assert {event.timestamp for event in split.test} == {5, 6, 7, 8}
    assert len(split.train + split.validation + split.test) == len(events)


@pytest.mark.parametrize("fractions", [(0, 0.9), (0.9, 0.8), (0.8, 1)])
def test_invalid_split_configuration(fractions):
    with pytest.raises(ValueError, match="fractions"):
        chronological_split(load_fixture().ratings, *fractions)


def test_ties_with_no_validation_fail_instead_of_splitting_timestamp():
    events = tuple(Rating(user_id=1, movie_id=i + 1, rating=4, timestamp=1) for i in range(10))
    with pytest.raises(ValueError, match="empty split"):
        chronological_split(events)


def test_catalog_and_event_contracts():
    source = load_fixture()
    with pytest.raises(ValueError, match="Duplicate catalog"):
        Dataset(source.movies + (source.movies[0],), source.ratings, "bad")
    with pytest.raises(ValueError, match="Duplicate user/movie"):
        Dataset(source.movies, source.ratings + (source.ratings[0],), "bad")
    bad = Rating(user_id=1, movie_id=999, rating=4, timestamp=1)
    with pytest.raises(ValueError, match="unknown movie"):
        Dataset(source.movies, (bad,), "bad")


def test_metrics_against_hand_computed_discounted_gain():
    result = ranking_metrics([99, 1, 98, 2], {1, 2, 3})
    expected_dcg = 1 / math.log2(3) + 1 / math.log2(5)
    expected_ideal = 1 + 1 / math.log2(3) + 1 / math.log2(4)
    assert result.recall_at_10 == pytest.approx(2 / 3)
    assert result.ndcg_at_10 == pytest.approx(expected_dcg / expected_ideal)
    assert result.hit_rate_at_10 == 1


def test_metric_cutoffs_and_failure_zero():
    result = ranking_metrics(list(range(1, 21)), {10, 20, 21})
    assert result.recall_at_10 == pytest.approx(1 / 3)
    assert result.recall_at_20 == pytest.approx(2 / 3)
    empty = ranking_metrics([], {1, 2})
    assert empty.ndcg_at_10 == 0
    assert empty.recall_at_10 == 0
    with pytest.raises(ValueError, match="Duplicate"):
        ranking_metrics([1, 1], {1})
    with pytest.raises(ValueError, match="relevant"):
        ranking_metrics([1], set())


def test_unreachable_positive_stays_in_denominator():
    source = load_fixture()
    ranker = Ranker(source, tuple(e for e in source.ratings if e.timestamp < 25), "popularity")
    report = evaluate(ranker, (Rating(user_id=7, movie_id=13, rating=5, timestamp=30),))
    assert report["eligible_users"] == 1
    assert report["metrics"]["recall_at_10"] == 0
    assert report["users"][0]["unreachable_positive_count"] == 1
    assert report["users"][0]["cohort"] == "zero_history"


def test_failed_user_is_scored_and_retained(monkeypatch):
    source = load_fixture()
    ranker = Ranker(source, tuple(e for e in source.ratings if e.timestamp < 25), "popularity")

    def fail(_request):
        raise RuntimeError("injected scoring failure")

    monkeypatch.setattr(ranker, "recommend", fail)
    report = evaluate(ranker, (Rating(user_id=1, movie_id=5, rating=5, timestamp=25),))
    assert report["eligible_users"] == report["failed_users"] == 1
    assert report["metrics"]["ndcg_at_10"] == 0
    assert report["users"][0]["error"] == "injected scoring failure"


def test_no_targets_is_unusable():
    source = load_fixture()
    ranker = Ranker(source, source.ratings, "popularity")
    with pytest.raises(ValueError, match="No eligible"):
        evaluate(ranker, source.ratings)
