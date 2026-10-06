from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.resources import files
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from reco.contracts import RecommendationRequest, RecommendationResponse
from reco.data import chronological_split, load_fixture
from reco.ranking import Ranker


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        dataset = load_fixture()
        split = chronological_split(dataset.ratings)
        application.state.ranker = Ranker(dataset, split.train, "popularity")
        application.state.cutoff = split.validation_cutoff
        yield

    application = FastAPI(title="CPU Recommendation Service — fictional fixture", lifespan=lifespan)
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
        return {"status": "ready", "data_mode": "fictional_fixture"}

    @application.get("/v1/model")
    def model(request: Request) -> dict[str, object]:
        ranker: Ranker = request.app.state.ranker
        return {
            "model_id": ranker.model_id,
            "variant": ranker.variant,
            "data_mode": "fictional_fixture",
            "backend": "cpu",
            "data_fingerprint": ranker.data_fingerprint,
            "training_cutoff": request.app.state.cutoff,
            "selection_status": "baseline_only_no_promotion_gate_yet",
        }

    @application.get("/v1/catalog")
    def catalog(
        request: Request, q: Annotated[str, Query(max_length=100)] = ""
    ) -> list[dict[str, object]]:
        ranker: Ranker = request.app.state.ranker
        return [
            movie.model_dump() for movie in ranker.movies if q.casefold() in movie.title.casefold()
        ][:50]

    @application.post("/v1/recommendations", response_model=RecommendationResponse)
    def recommend(payload: RecommendationRequest, request: Request) -> RecommendationResponse:
        try:
            ranker: Ranker = request.app.state.ranker
            return ranker.recommend(payload)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return application
