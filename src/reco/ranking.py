import hashlib
import time
from collections import defaultdict
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, diags
from threadpoolctl import threadpool_limits

from reco.contracts import Hit, Rating, RecommendationRequest, RecommendationResponse, Variant
from reco.data import Dataset
from reco.storage import json_hash


class ALSConfig:
    """Single bounded v1 treatment; changes must be frozen before test scoring."""

    factors = 32
    iterations = 15
    regularization = 0.1
    positive_confidence = 20
    seed = 42
    threads = 2


class Ranker:
    """Fit only supplied history; the rest of the dataset supplies metadata/known sample IDs."""

    def __init__(self, dataset: Dataset, history: tuple[Rating, ...], variant: Variant) -> None:
        self.variant = variant
        self.data_fingerprint = dataset.fingerprint
        self.data_mode = dataset.data_mode
        observed = {event.movie_id for event in history}
        self.movies = tuple(
            sorted(
                (movie for movie in dataset.movies if movie.movie_id in observed),
                key=lambda movie: movie.movie_id,
            )
        )
        if not self.movies:
            raise ValueError("Cannot fit an empty catalog")
        self.columns = {movie.movie_id: index for index, movie in enumerate(self.movies)}
        self.movie_ids = np.array([movie.movie_id for movie in self.movies], dtype=np.int64)
        self.genres = {genre for movie in self.movies for genre in movie.genres}
        self.known_users = {event.user_id for event in dataset.ratings}
        self.users = {uid: i for i, uid in enumerate(sorted({e.user_id for e in history}))}
        self.seen: dict[int, set[int]] = defaultdict(set)
        self.liked: dict[int, set[int]] = defaultdict(set)
        rows, columns = [], []
        for event in history:
            self.seen[event.user_id].add(event.movie_id)
            if event.rating >= 4:
                self.liked[event.user_id].add(event.movie_id)
                rows.append(self.users[event.user_id])
                columns.append(self.columns[event.movie_id])
        self.positive = csr_matrix(
            (np.ones(len(rows), dtype=np.float32), (rows, columns)),
            shape=(len(self.users), len(self.movies)),
        )
        self.popularity: NDArray[np.float32] = np.asarray(
            self.positive.sum(axis=0), dtype=np.float32
        ).ravel()
        self.neighbors: Any = None
        self.als: Any = None
        if variant == "item_knn":
            norms = np.sqrt(np.asarray(self.positive.power(2).sum(axis=0)).ravel())
            inverse = np.divide(1.0, norms, out=np.zeros_like(norms), where=norms > 0)
            normalized = self.positive @ diags(inverse)
            similarity = (normalized.T @ normalized).tocsr()
            similarity.setdiag(0)
            similarity.eliminate_zeros()
            # Stable top-100 neighbor pruning, without a dense item-by-item matrix.
            for row in range(similarity.shape[0]):
                start, end = similarity.indptr[row : row + 2]
                order = np.lexsort((similarity.indices[start:end], -similarity.data[start:end]))
                similarity.data[start + order[100:]] = 0
            similarity.eliminate_zeros()
            self.neighbors = similarity
        elif variant == "als_cpu":
            from implicit.cpu.als import AlternatingLeastSquares

            self.als = AlternatingLeastSquares(
                factors=ALSConfig.factors,
                iterations=ALSConfig.iterations,
                regularization=ALSConfig.regularization,
                random_state=ALSConfig.seed,
                num_threads=ALSConfig.threads,
            )
            with threadpool_limits(limits=1, user_api="blas"):
                self.als.fit(self.positive * ALSConfig.positive_confidence, show_progress=False)
        elif variant != "popularity":
            raise ValueError("Unknown ranking variant")
        history_digest = hashlib.sha256()
        for event in history:
            history_digest.update(
                f"{event.user_id}:{event.movie_id}:{event.rating}:{event.timestamp}\n".encode()
            )
        self.history_fingerprint = history_digest.hexdigest()
        self.config = {
            "variant": variant,
            "positive_rating_min": 4,
            "min_likes_for_personalization": 3,
            "neighbors": 100 if variant == "item_knn" else None,
            "als": {
                "factors": ALSConfig.factors,
                "iterations": ALSConfig.iterations,
                "regularization": ALSConfig.regularization,
                "positive_confidence": ALSConfig.positive_confidence,
                "seed": ALSConfig.seed,
                "threads": ALSConfig.threads,
            }
            if variant == "als_cpu"
            else None,
        }
        identity = json_hash(
            {
                "dataset": dataset.fingerprint,
                "history": history_digest.hexdigest(),
                "config": self.config,
                "implementation": "ranking-v2",
            }
        )
        self.model_id = dataset.data_mode + "-" + identity[:16]

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
