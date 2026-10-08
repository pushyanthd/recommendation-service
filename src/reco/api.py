import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from reco.benchmark import peak_rss_bytes
from reco.contracts import RecommendationRequest, RecommendationResponse
from reco.data import chronological_split, load_fixture
from reco.ranking import Ranker
from reco.serving import ServingRanker
from reco.storage import json_hash
from reco.telemetry import Telemetry


def create_app(bundle_root: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        startup_started = time.perf_counter()
        if bundle_root is None:
            dataset = load_fixture()
            split = chronological_split(dataset.ratings)
            application.state.ranker = Ranker(dataset, split.train, "popularity")
            application.state.metadata = {
                "training_cutoff": split.validation_cutoff,
                "release_status": "fictional_fixture_no_real_quality_claim",
                "selection": {"selected_for_final_refit": "popularity"},
            }
        else:
            from reco.lifecycle import active_bundle

            bundle = active_bundle(bundle_root)
            application.state.ranker = bundle.ranker
            application.state.metadata = bundle.manifest.model_dump()
        from reco.benchmark import execution_identity

        with as_file(files("reco").joinpath("runtime.lock")) as runtime_lock:
            application.state.runtime_identity = execution_identity(runtime_lock)
        application.state.startup_ms = (time.perf_counter() - startup_started) * 1000
        application.state.telemetry = Telemetry()
        application.state.ranker = ServingRanker(
            application.state.ranker, application.state.telemetry
        )
        yield

    application = FastAPI(title="CPU Recommendation Service", lifespan=lifespan)
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    @application.middleware("http")
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check same-origin on browsers, and cap JSON before Pydantic deserialization.
        from starlette.responses import JSONResponse

        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin request rejected"}, status_code=403)
        if request.method == "POST":
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 16_384:
                    return JSONResponse({"detail": "Request body too large"}, status_code=413)
            request._body = bytes(body)
        return await call_next(request)

    @application.middleware("http")
    async def observe_http(request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        request_id = str(uuid4())
        request.state.request_id = request_id
        telemetry: Telemetry = request.app.state.telemetry
        try:
            response = await call_next(request)
        except Exception:
            telemetry.count("errors", "internal")
            raise
        finally:
            elapsed = time.perf_counter() - started
            telemetry.observe("http", elapsed)
        reason = (
            "success"
            if response.status_code < 400
            else "invalid_request"
            if response.status_code == 422
            else "boundary"
            if response.status_code < 500
            else "internal"
        )
        telemetry.count("requests", reason)
        if response.status_code >= 400:
            telemetry.count("errors", reason)
        response.headers["X-Request-ID"] = request_id
        logging.getLogger("reco.requests").info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "status": response.status_code,
                    "elapsed_ms": elapsed * 1000,
                    "model_id": request.app.state.ranker.model_id,
                }
            )
        )
        return response

    @application.get("/", response_class=HTMLResponse)
    def index() -> str:
        return files("reco").joinpath("ui/index.html").read_text()

    @application.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz")
    def ready(request: Request) -> dict[str, str]:
        if not hasattr(request.app.state, "ranker"):
            raise HTTPException(503, "Ranker not loaded")
        ranker: Ranker = request.app.state.ranker
        return {"status": "ready", "data_mode": ranker.data_mode, "model_id": ranker.model_id}

    @application.get("/v1/model")
    def model(request: Request) -> dict[str, object]:
        ranker: Ranker = request.app.state.ranker
        return {
            "model_id": ranker.model_id,
            "variant": ranker.variant,
            "data_mode": ranker.data_mode,
            "backend": "cpu",
            "data_fingerprint": ranker.data_fingerprint,
            "training_cutoff": request.app.state.metadata["training_cutoff"],
            "release_status": request.app.state.metadata["release_status"],
            "selection": request.app.state.metadata["selection"],
            "config": ranker.config,
            "config_sha256": json_hash(ranker.config),
            "genres": sorted(ranker.genres),
            "startup_load_ms": request.app.state.startup_ms,
            "peak_process_rss_bytes": peak_rss_bytes(),
            "runtime_identity_sha256": json_hash(request.app.state.runtime_identity),
            "runtime_source_identity_sha256": json_hash(
                request.app.state.runtime_identity["source_files"]
            ),
        }

    @application.get("/v1/catalog")
    def catalog(
        request: Request, q: Annotated[str, Query(max_length=100)] = ""
    ) -> list[dict[str, object]]:
        ranker: Ranker = request.app.state.ranker
        return [
            movie.model_dump() for movie in ranker.movies if q.casefold() in movie.title.casefold()
        ][:50]

    @application.get("/v1/profiles")
    def profiles(request: Request) -> list[dict[str, object]]:
        ranker: Ranker = request.app.state.ranker
        results: list[dict[str, object]] = []
        for cohort, minimum, maximum in (
            ("warm", 5, 100000),
            ("sparse", 1, 4),
            ("zero_history", 0, 0),
        ):
            for uid in sorted(ranker.known_users):
                if minimum <= len(ranker.liked.get(uid, set())) <= maximum:
                    results.append({"user_id": uid, "cohort": cohort})
                    if sum(row["cohort"] == cohort for row in results) == 3:
                        break
        return results

    @application.get("/metrics")
    def metrics(request: Request) -> Response:
        telemetry: Telemetry = request.app.state.telemetry
        return Response(
            telemetry.render(request.app.state.ranker.variant),
            media_type="text/plain; version=0.0.4",
        )

    @application.post("/v1/recommendations", response_model=RecommendationResponse)
    def recommend(payload: RecommendationRequest, request: Request) -> RecommendationResponse:
        try:
            ranker: Ranker = request.app.state.ranker
            response = ranker.recommend(payload)
            telemetry: Telemetry = request.app.state.telemetry
            telemetry.observe("ranking", response.elapsed_ms / 1000)
            telemetry.count("recommendations", response.variant)
            telemetry.count("fallback", response.fallback_reason or "none")
            telemetry.record_returned(response.returned_count)
            return response.model_copy(update={"request_id": request.state.request_id})
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return application
