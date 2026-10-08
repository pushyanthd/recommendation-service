"""Measured serving path for frozen rankings; fixture parity covers every treatment.

The benchmark implementation stays unchanged. This equivalent inference path adds
stage boundaries without refitting models or modifying histories/factors.
"""

import time
from typing import Literal
from uuid import uuid4

import numpy as np
from scipy.sparse import csr_matrix
from threadpoolctl import threadpool_limits

from reco.contracts import Hit, RecommendationRequest, RecommendationResponse, Variant
from reco.ranking import ALSConfig, Ranker
from reco.telemetry import Telemetry


class ServingRanker(Ranker):
    def __init__(self, snapshot: Ranker, telemetry: Telemetry) -> None:
        self.__dict__.update(snapshot.__dict__)
        self.telemetry = telemetry

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        started = time.perf_counter()
        if request.user_id is not None:
            if request.user_id not in self.known_users:
                raise ValueError("Unknown benchmark user")
            liked = self.liked.get(request.user_id, set())
            seen = self.seen.get(request.user_id, set())
        else:
            liked = set(request.liked_movie_ids or [])
            if not liked <= self.columns.keys():
                raise ValueError("Unknown or unavailable movie ID")
            seen = liked
        if request.genre is not None and request.genre not in self.genres:
            raise ValueError("Unknown genre")
        self.telemetry.observe("history_lookup", time.perf_counter() - started)
        scoring_started = time.perf_counter()
        variant = self.variant if request.variant == "selected" else "popularity"
        fallback: Literal["insufficient_history"] | None = None
        if variant != "popularity" and len(liked) < 3:
            variant, fallback = "popularity", "insufficient_history"
        scores = self.popularity.copy()
        if variant == "item_knn":
            indices = [self.columns[movie_id] for movie_id in sorted(liked)]
            scores = np.asarray(self.neighbors[indices].sum(axis=0), dtype=np.float32).ravel()
        elif variant == "als_cpu":
            if request.user_id is not None:
                factors = self.als.user_factors[self.users[request.user_id]]
            else:
                indices = [self.columns[movie_id] for movie_id in sorted(liked)]
                row = csr_matrix(
                    (
                        np.full(len(indices), ALSConfig.positive_confidence, dtype=np.float32),
                        ([0] * len(indices), indices),
                    ),
                    shape=(1, len(self.movies)),
                )
                with threadpool_limits(limits=1, user_api="blas"):
                    factors = self.als.recalculate_user(0, row)
            scores = np.asarray(self.als.item_factors @ factors, dtype=np.float32)
        if not np.isfinite(scores).all():
            raise RuntimeError("Nonfinite ranking scores")
        self.telemetry.observe("scoring", time.perf_counter() - scoring_started)
        filtering_started = time.perf_counter()
        eligible = [
            index
            for index, movie in enumerate(self.movies)
            if movie.movie_id not in seen
            and (request.genre is None or request.genre in movie.genres)
        ]
        eligible_array = np.array(eligible, dtype=np.int64)
        order = np.lexsort((self.movie_ids[eligible_array], -scores[eligible_array]))
        ordered = eligible_array[order][: request.k]
        reasons: dict[Variant, Literal["popular", "similar_to_history", "collaborative_match"]] = {
            "popularity": "popular",
            "item_knn": "similar_to_history",
            "als_cpu": "collaborative_match",
        }
        reason = reasons[variant]
        items = [
            Hit(
                movie_id=self.movies[i].movie_id,
                title=self.movies[i].title,
                score=float(scores[i]),
                reason=reason,
            )
            for i in ordered
        ]
        self.telemetry.observe("filtering_top_k", time.perf_counter() - filtering_started)
        return RecommendationResponse(
            request_id=str(uuid4()),
            model_id=self.model_id,
            data_mode=self.data_mode,
            variant=variant,
            fallback_reason=fallback,
            catalog_exhausted=len(items) < request.k,
            returned_count=len(items),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            items=items,
        )
