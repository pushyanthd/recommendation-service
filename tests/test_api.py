import pytest
from fastapi.testclient import TestClient

from reco.api import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as session:
        yield session


def test_api_ready_demo_and_catalog(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json()["status"] == "ready"
    assert "Find your next movie" in client.get("/").text
    assert client.get("/v1/model").json()["variant"] == "popularity"
    assert len(client.get("/v1/catalog?q=Orbit").json()) == 1


def test_api_prior_dislikes_excluded_and_provenance_explicit(client):
    response = client.post("/v1/recommendations", json={"user_id": 1, "k": 20})
    assert response.status_code == 200
    result = response.json()
    assert result["data_mode"] == "fictional_fixture"
    assert not {1, 2, 3, 4, 5} & {hit["movie_id"] for hit in result["items"]}
    assert result["catalog_exhausted"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"user_id": 1, "liked_movie_ids": []},
        {"user_id": 999},
        {"user_id": 1, "k": 21},
        {"user_id": 1, "k": True},
        {"liked_movie_ids": [999]},
        {"liked_movie_ids": [1, 1]},
        {"liked_movie_ids": [True]},
        {"liked_movie_ids": ["1"]},
        {"liked_movie_ids": [], "extra": "not_allowed"},
        {"liked_movie_ids": [], "variant": "als_cpu"},
    ],
)
def test_invalid_requests(client, payload):
    assert client.post("/v1/recommendations", json=payload).status_code == 422


def test_body_limit_and_origin_boundary(client):
    response = client.post(
        "/v1/recommendations", content=b"x" * 20_000, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert (
        client.post(
            "/v1/recommendations",
            json={"liked_movie_ids": []},
            headers={"Origin": "https://untrusted.example"},
        ).status_code
        == 403
    )
    assert client.get("/healthz", headers={"Host": "untrusted.example"}).status_code == 400


def test_empty_preferences_is_valid_cold_start(client):
    result = client.post("/v1/recommendations", json={"liked_movie_ids": [], "k": 3})
    assert result.status_code == 200
    assert result.json()["returned_count"] == 3
