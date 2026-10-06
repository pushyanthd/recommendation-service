import math
from collections import defaultdict
from dataclasses import asdict, dataclass

from reco.contracts import Rating, RecommendationRequest
from reco.ranking import Ranker


@dataclass(frozen=True)
class Metrics:
    recall_at_10: float
    recall_at_20: float
    ndcg_at_10: float
    hit_rate_at_10: float


@dataclass(frozen=True)
class UserResult:
    user_id: int
    cohort: str
    relevant_count: int
    unreachable_positive_count: int
    metrics: Metrics
    fallback_reason: str | None
    error: str | None


def ranking_metrics(ranked: list[int], relevant: set[int]) -> Metrics:
    if not relevant:
        raise ValueError("A scored user must have at least one relevant item")
    if len(ranked) != len(set(ranked)):
        raise ValueError("Duplicate recommendations invalidate a ranking")
    hits10 = len(set(ranked[:10]) & relevant)
    hits20 = len(set(ranked[:20]) & relevant)
    dcg = sum(1 / math.log2(rank + 2) for rank, item in enumerate(ranked[:10]) if item in relevant)
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(relevant))))
    return Metrics(hits10 / len(relevant), hits20 / len(relevant), dcg / ideal, float(hits10 > 0))


def evaluate(ranker: Ranker, future: tuple[Rating, ...]) -> dict[str, object]:
    targets: dict[int, set[int]] = defaultdict(set)
    for event in future:
        if event.rating >= 4 and event.movie_id not in ranker.seen.get(event.user_id, set()):
            targets[event.user_id].add(event.movie_id)
    records: list[UserResult] = []
    for user_id, relevant in sorted(targets.items()):
        error = None
        try:
            response = ranker.recommend(RecommendationRequest(user_id=user_id, k=20))
            ranked = [hit.movie_id for hit in response.items]
            fallback = response.fallback_reason
        except (ValueError, RuntimeError) as exc:
            ranked, fallback, error = [], None, str(exc)
        nlikes = len(ranker.liked.get(user_id, set()))
        records.append(
            UserResult(
                user_id=user_id,
                cohort="warm" if nlikes >= 5 else "sparse" if nlikes else "zero_history",
                relevant_count=len(relevant),
                unreachable_positive_count=len(relevant - ranker.columns.keys()),
                metrics=ranking_metrics(ranked, relevant),
                fallback_reason=fallback,
                error=error,
            )
        )
    if not records:
        raise ValueError("No eligible users; evaluation is unusable")
    names = Metrics.__dataclass_fields__
    means = {
        name: sum(getattr(record.metrics, name) for record in records) / len(records)
        for name in names
    }
    return {
        "data_mode": "fictional_fixture",
        "model_id": ranker.model_id,
        "variant": ranker.variant,
        "eligible_users": len(records),
        "failed_users": sum(record.error is not None for record in records),
        "metrics": means,
        "users": [asdict(record) for record in records],
    }
