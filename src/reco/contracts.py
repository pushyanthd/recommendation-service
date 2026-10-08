from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

type Variant = Literal["popularity", "item_knn", "als_cpu"]
type DataMode = Literal["fictional_fixture", "movielens_1m"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Movie(Contract):
    movie_id: int = Field(gt=0, strict=True)
    title: str = Field(min_length=1, max_length=500)
    genres: tuple[str, ...]


class Rating(Contract):
    user_id: int = Field(gt=0, strict=True)
    movie_id: int = Field(gt=0, strict=True)
    rating: int = Field(ge=1, le=5, strict=True)
    timestamp: int = Field(ge=0, strict=True)


class Fixture(Contract):
    data_mode: Literal["fictional_fixture"]
    movies: tuple[Movie, ...]
    ratings: tuple[Rating, ...]


class BenchmarkProtocol(Contract):
    protocol: Literal["chronological-full-catalog-v1"]
    train_fraction: float = Field(gt=0, lt=1, allow_inf_nan=False)
    test_start: float = Field(gt=0, lt=1, allow_inf_nan=False)
    positive_rating_min: Literal[4]
    variants: tuple[Variant, ...]
    bootstrap_samples: int = Field(ge=1, le=10000, strict=True)
    bootstrap_seed: int = Field(ge=0, strict=True)
    minimum_relative_ndcg_gain: float = Field(ge=0, allow_inf_nan=False)
    maximum_recall_at_20_drop: float = Field(ge=0, le=1, allow_inf_nan=False)
    near_tie_absolute_ndcg: float = Field(ge=0, le=1, allow_inf_nan=False)
    warm_http_p95_objective_ms: float = Field(gt=0, allow_inf_nan=False)
    maximum_peak_rss_bytes: int = Field(gt=0, strict=True)
    maximum_single_fit_seconds: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def bounded_protocol(self) -> Self:
        if self.variants != ("popularity", "item_knn", "als_cpu"):
            raise ValueError("v1 requires exactly the three bounded ranking treatments")
        if not self.train_fraction < self.test_start:
            raise ValueError("Training must precede validation and test")
        return self


class RecommendationRequest(Contract):
    user_id: int | None = Field(default=None, gt=0, strict=True)
    liked_movie_ids: list[Annotated[int, Field(gt=0, strict=True)]] | None = Field(
        default=None, max_length=50
    )
    genre: str | None = Field(default=None, max_length=50)
    k: int = Field(default=10, ge=1, le=20, strict=True)
    variant: Literal["selected", "popularity"] = "selected"

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        if (self.user_id is None) == (self.liked_movie_ids is None):
            raise ValueError("Supply exactly one of user_id or liked_movie_ids")
        if self.liked_movie_ids is not None:
            if any(type(item) is not int or item <= 0 for item in self.liked_movie_ids):
                raise ValueError("Movie IDs must be positive integers")
            if len(self.liked_movie_ids) != len(set(self.liked_movie_ids)):
                raise ValueError("Repeated movie IDs are not allowed")
        return self


class Hit(Contract):
    movie_id: int
    title: str
    score: float = Field(allow_inf_nan=False)
    reason: Literal["popular", "similar_to_history", "collaborative_match"]


class RecommendationResponse(Contract):
    request_id: str
    model_id: str
    data_mode: DataMode
    variant: Variant
    fallback_reason: Literal["insufficient_history"] | None
    catalog_exhausted: bool
    returned_count: int
    elapsed_ms: float
    items: list[Hit]
