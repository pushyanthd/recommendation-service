import math
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from reco.contracts import Rating, RecommendationRequest
from reco.ranking import Ranker
from reco.storage import json_hash


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
    scoring_ms: float


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


def evaluate(ranker: Ranker, future: tuple[Rating, ...]) -> dict[str, Any]:
    targets: dict[int, set[int]] = defaultdict(set)
    for event in future:
        if event.rating >= 4 and event.movie_id not in ranker.seen.get(event.user_id, set()):
            targets[event.user_id].add(event.movie_id)
    records: list[UserResult] = []
    recommended: set[int] = set()
    exposure_count = 0
    popular_count = 0
    popularity_order = np.lexsort((ranker.movie_ids, -ranker.popularity))
    popular = {
        ranker.movies[i].movie_id for i in popularity_order[: math.ceil(len(ranker.movies) / 10)]
    }
    for user_id, relevant in sorted(targets.items()):
        error = None
        started = time.perf_counter()
        try:
            response = ranker.recommend(RecommendationRequest(user_id=user_id, k=20))
            ranked = [hit.movie_id for hit in response.items]
            if (
                len(ranked) != len(set(ranked))
                or not set(ranked) <= ranker.columns.keys()
                or set(ranked) & ranker.seen.get(user_id, set())
            ):
                raise RuntimeError("Ranking invariants failed: duplicate, unavailable or seen item")
            fallback = response.fallback_reason
        except Exception as exc:
            # A single failed request remains in the denominator. Process interruptions
            # (BaseException) still abort the pipeline rather than producing false evidence.
            ranked, fallback, error = [], None, str(exc)
        nlikes = len(ranker.liked.get(user_id, set()))
        recommended.update(ranked[:10])
        exposure_count += len(ranked[:10])
        popular_count += len(set(ranked[:10]) & popular)
        records.append(
            UserResult(
                user_id=user_id,
                cohort="warm" if nlikes >= 5 else "sparse" if nlikes else "zero_history",
                relevant_count=len(relevant),
                unreachable_positive_count=len(relevant - ranker.columns.keys()),
                metrics=ranking_metrics(ranked, relevant),
                fallback_reason=fallback,
                error=error,
                scoring_ms=(time.perf_counter() - started) * 1000,
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
        "data_mode": ranker.data_mode,
        "model_id": ranker.model_id,
        "variant": ranker.variant,
        "data_fingerprint": ranker.data_fingerprint,
        "history_fingerprint": ranker.history_fingerprint,
        "target_fingerprint": json_hash(
            [[uid, sorted(items)] for uid, items in sorted(targets.items())]
        ),
        "metric_protocol": "binary-future-positive-4-unseen-full-catalog-v1",
        "eligible_users": len(records),
        "failed_users": sum(record.error is not None for record in records),
        "completed_users": sum(record.error is None for record in records),
        "total_users": len(ranker.known_users),
        "no_target_users": len(ranker.known_users - targets.keys()),
        "positive_targets": sum(record.relevant_count for record in records),
        "unreachable_positives": sum(record.unreachable_positive_count for record in records),
        "catalog_size": len(ranker.movies),
        "catalog_fingerprint": json_hash([movie.movie_id for movie in ranker.movies]),
        "config": ranker.config,
        "coverage_at_10": len(recommended) / len(ranker.movies),
        "popular_fraction_at_10": popular_count / exposure_count if exposure_count else 0,
        "fallback_rate": sum(record.fallback_reason is not None for record in records)
        / len(records),
        "scoring_latency_ms": {
            "p50": float(np.percentile([record.scoring_ms for record in records], 50)),
            "p95": float(np.percentile([record.scoring_ms for record in records], 95)),
        },
        "cohorts": {
            cohort: {
                "users": len(group := [record for record in records if record.cohort == cohort]),
                "descriptive_only": len(group) < 30,
                "metrics": {
                    name: sum(getattr(record.metrics, name) for record in group) / len(group)
                    if group
                    else None
                    for name in names
                },
            }
            for cohort in ("warm", "sparse", "zero_history")
        },
        "metrics": means,
        "users": [asdict(record) for record in records],
    }
