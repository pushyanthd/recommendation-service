import json
import socket
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from reco.api import create_app
from reco.bundles import load_bundle, write_bundle
from reco.contracts import RecommendationRequest
from reco.data import chronological_split, load_fixture
from reco.lifecycle import activate, active_bundle, probe, select_initial, start, stop
from reco.ranking import Ranker
from reco.storage import atomic_json, json_hash, sha256_file


def build(root, variant="popularity", history=None):
    dataset = load_fixture()
    split = chronological_split(dataset.ratings)
    ranker = Ranker(dataset, history or split.train, variant)
    directory = write_bundle(
        root,
        ranker,
        split.validation_cutoff,
        {
            "selected_for_final_refit": variant,
            "quality_gates": [{"variant": variant, "passed": True}],
        },
        "fictional_fixture_no_real_quality_claim",
        {"test": True},
    )
    return ranker, directory


def rehash(directory):
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text())
    for name in manifest["files"]:
        manifest["files"][name] = sha256_file(directory / name)
    manifest["model_id"] = (
        manifest["ranking_model_id"]
        + "-"
        + json_hash({k: v for k, v in manifest.items() if k != "model_id"})[:16]
    )
    atomic_json(path, manifest)


@pytest.mark.parametrize("variant", ["popularity", "item_knn", "als_cpu"])
def test_roundtrip_preserves_rankings_and_ephemeral_fold_in(tmp_path, variant):
    original, directory = build(tmp_path, variant)
    loaded = load_bundle(directory).ranker
    for request in [
        RecommendationRequest(user_id=1, k=20),
        RecommendationRequest(user_id=7),
        RecommendationRequest(liked_movie_ids=[1, 2, 3]),
        RecommendationRequest(liked_movie_ids=[1], genre="Sci-Fi"),
        RecommendationRequest(user_id=1, variant="popularity"),
    ]:
        expected, actual = original.recommend(request), loaded.recommend(request)
        assert [hit.movie_id for hit in actual.items] == [hit.movie_id for hit in expected.items]
        np.testing.assert_allclose(
            [hit.score for hit in actual.items],
            [hit.score for hit in expected.items],
            rtol=1e-6,
            atol=1e-6,
        )
        assert actual.variant == expected.variant
        assert actual.fallback_reason == expected.fallback_reason
    assert loaded.seen == dict(original.seen)
    assert loaded.liked == dict(original.liked)
    assert (
        write_bundle(
            tmp_path,
            original,
            load_bundle(directory).manifest.training_cutoff,
            load_bundle(directory).manifest.selection,
            load_bundle(directory).manifest.release_status,
            {"test": True},
        )
        == directory
    )


def test_checksum_failure_does_not_replace_active_pointer(tmp_path):
    _, directory = build(tmp_path)
    select_initial(tmp_path, directory.name)
    before = (tmp_path / "active.json").read_bytes()
    (directory / "popularity.npz").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        activate(tmp_path, directory.name)
    assert (tmp_path / "active.json").read_bytes() == before


@pytest.mark.parametrize(
    "damage",
    [
        "nonfinite",
        "csr_bounds",
        "positive_not_seen",
        "popularity",
        "users",
        "catalog",
        "extra",
        "symlink",
    ],
)
def test_self_consistent_checksums_do_not_bypass_semantic_validation(tmp_path, damage):
    _, directory = build(tmp_path)
    if damage == "nonfinite":
        np.savez_compressed(directory / "popularity.npz", scores=np.full(12, np.nan))
    elif damage in ("csr_bounds", "positive_not_seen"):
        path = directory / ("positive.npz" if damage == "csr_bounds" else "seen.npz")
        with np.load(path, allow_pickle=False) as archive:
            arrays = {key: archive[key] for key in archive.files}
        if damage == "csr_bounds":
            arrays["indices"][0] = 999
        else:
            arrays["data"][0] = 2
        np.savez_compressed(path, **arrays)
    elif damage == "popularity":
        np.savez_compressed(directory / "popularity.npz", scores=np.zeros(12))
    elif damage == "users":
        users = json.loads((directory / "users.json").read_text())
        users["training"][0] = users["training"][1]
        atomic_json(directory / "users.json", users)
    elif damage == "catalog":
        rows = json.loads((directory / "catalog.json").read_text())
        rows[0]["movie_id"] = rows[1]["movie_id"]
        atomic_json(directory / "catalog.json", rows)
    elif damage == "extra":
        (directory / "extra.npy").write_bytes(b"unexpected")
    else:
        original = directory / "popularity.npz"
        target = tmp_path / "outside.npz"
        original.rename(target)
        original.symlink_to(target)
    rehash(directory)
    with pytest.raises(ValueError):
        load_bundle(directory)


def test_active_manifest_digest_and_path_are_checked(tmp_path):
    _, directory = build(tmp_path)
    select_initial(tmp_path, directory.name)
    with pytest.raises(ValueError, match="exists"):
        select_initial(tmp_path, directory.name)
    pointer = json.loads((tmp_path / "active.json").read_text())
    pointer["model_id"] = "../../outside"
    atomic_json(tmp_path / "active.json", pointer)
    with pytest.raises(ValueError, match="pointer"):
        active_bundle(tmp_path)


def test_api_loads_snapshot_once_and_returns_bounded_telemetry(tmp_path):
    _, directory = build(tmp_path, "item_knn")
    select_initial(tmp_path, directory.name)
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/readyz").json()["model_id"] == directory.name
        profiles = client.get("/v1/profiles").json()
        assert {profile["cohort"] for profile in profiles} == {"warm", "sparse", "zero_history"}
        response = client.post("/v1/recommendations", json={"liked_movie_ids": [1]})
        assert response.json()["fallback_reason"] == "insufficient_history"
        assert response.headers["x-request-id"] == response.json()["request_id"]
        text = client.get("/metrics").text
        assert 'reco_fallback_total{reason="insufficient_history"} 1' in text
        assert "user_id" not in text and "movie_id" not in text
        (tmp_path / "active.json").write_text("invalid pointer")
        assert client.get("/readyz").json()["model_id"] == directory.name
    with pytest.raises(ValueError):
        with TestClient(create_app(tmp_path)):
            pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_actual_restart_activation_and_rollback(tmp_path):
    _, first = build(tmp_path)
    _, second = build(
        tmp_path, history=tuple(e for e in load_fixture().ratings if e.timestamp < 25)
    )
    select_initial(tmp_path, first.name)
    try:
        original = start(tmp_path, free_port())
        changed = activate(tmp_path, second.name)
        assert changed["pid"] != original["pid"]
        assert probe(changed["port"], second.name)["model_id"] == second.name
        restored = activate(tmp_path, first.name, rollback=True)
        assert restored["pid"] != changed["pid"]
        assert probe(restored["port"], first.name)["model_id"] == first.name
    finally:
        stop(tmp_path)


def test_failed_startup_restores_previous_process_and_pointer(tmp_path, monkeypatch):
    import reco.lifecycle as lifecycle

    _, first = build(tmp_path)
    _, second = build(
        tmp_path, history=tuple(e for e in load_fixture().ratings if e.timestamp < 25)
    )
    select_initial(tmp_path, first.name)
    real_start = lifecycle.start

    def fail_candidate(root, port):
        if active_bundle(root).manifest.model_id == second.name:
            raise ValueError("Injected candidate startup failure")
        return real_start(root, port)

    try:
        original = real_start(tmp_path, free_port())
        monkeypatch.setattr(lifecycle, "start", fail_candidate)
        with pytest.raises(ValueError, match="restored"):
            activate(tmp_path, second.name)
        assert active_bundle(tmp_path).manifest.model_id == first.name
        assert probe(original["port"], first.name)["status"] == "ready"
        assert json.loads((tmp_path / "process.json").read_text())["pid"] != original["pid"]
    finally:
        stop(tmp_path)


def test_stop_refuses_unrelated_pid(tmp_path):
    import os

    atomic_json(tmp_path / "process.json", {"pid": os.getpid(), "token": "not-owned"})
    with pytest.raises(ValueError, match="belongs"):
        stop(tmp_path)


def test_process_inspection_preserves_token_after_long_arguments():
    import subprocess
    import sys
    from uuid import uuid4

    from reco.lifecycle import _command

    token = uuid4().hex
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)", "x" * 400, "--token", token]
    )
    try:
        command = _command(child.pid)
        assert "x" * 400 in command
        assert command.endswith("--token " + token)
    finally:
        child.terminate()
        child.wait(timeout=5)


@pytest.mark.parametrize("variant", ["popularity", "item_knn", "als_cpu"])
def test_instrumented_serving_preserves_frozen_rankings(tmp_path, variant):
    from reco.serving import ServingRanker
    from reco.telemetry import Telemetry

    frozen, _ = build(tmp_path, variant)
    telemetry = Telemetry()
    serving = ServingRanker(frozen, telemetry)
    requests = [RecommendationRequest(user_id=uid, k=20) for uid in frozen.known_users]
    requests.extend(
        [
            RecommendationRequest(liked_movie_ids=[1, 2, 3]),
            RecommendationRequest(liked_movie_ids=[]),
            RecommendationRequest(user_id=1, genre="Sci-Fi", variant="popularity"),
        ]
    )
    for request in requests:
        a, b = frozen.recommend(request), serving.recommend(request)
        assert a.items == b.items
        assert a.variant == b.variant and a.fallback_reason == b.fallback_reason
    assert set(telemetry.timings) == {"history_lookup", "scoring", "filtering_top_k"}


def test_forced_validation_rejection_keeps_active_version(tmp_path):
    _, first = build(tmp_path)
    candidate, _ = build(tmp_path, "item_knn")
    split = chronological_split(load_fixture().ratings)
    rejected = write_bundle(
        tmp_path,
        candidate,
        split.validation_cutoff,
        {
            "selected_for_final_refit": "item_knn",
            "quality_gates": [{"variant": "item_knn", "passed": False}],
        },
        "experimental_quality_objective_failed",
        {"test": True},
    )
    select_initial(tmp_path, first.name)
    before = (tmp_path / "active.json").read_bytes()
    with pytest.raises(ValueError, match="gate rejected"):
        activate(tmp_path, rejected.name)
    assert (tmp_path / "active.json").read_bytes() == before


def test_stale_pointer_recovery_uses_validated_last_known_good(tmp_path):
    from reco.lifecycle import pointer_for, recover

    _, first = build(tmp_path)
    select_initial(tmp_path, first.name)
    atomic_json(tmp_path / "last-known-good.json", pointer_for(first))
    (tmp_path / "active.json").write_text("interrupted pointer")
    try:
        result = recover(tmp_path, free_port())
        assert result["status"] == "recovered"
        assert probe(result["port"], first.name)["model_id"] == first.name
        assert active_bundle(tmp_path).manifest.model_id == first.name
    finally:
        stop(tmp_path)


def test_release_metadata_and_pytest_fix_preserve_frozen_dependencies(tmp_path):
    from reco.bundles import verify_serving_lock

    frozen = next(Path("config/frozen").glob("*.uv.lock"))
    verify_serving_lock(Path("uv.lock"), frozen.name.split(".")[0])
    changed = tmp_path / "changed.lock"
    changed.write_text(
        Path("uv.lock")
        .read_text()
        .replace('name = "implicit"\nversion = "0.7.3"', 'name = "implicit"\nversion = "0.7.4"')
    )
    with pytest.raises(ValueError, match="runtime"):
        verify_serving_lock(changed, frozen.name.split(".")[0])


def test_local_release_version_does_not_allow_project_dependency_changes(tmp_path):
    from reco.bundles import verify_serving_lock

    frozen = next(Path("config/frozen").glob("*.uv.lock"))
    changed = tmp_path / "changed.lock"
    current = Path("uv.lock").read_text()
    project_start = current.index('name = "cpu-recommendation-service"')
    project_end = current.index("[[package]]", project_start)
    project = current[project_start:project_end].replace(
        '{ name = "implicit" },', '{ name = "pytest" },', 1
    )
    assert project != current[project_start:project_end]
    changed.write_text(current[:project_start] + project + current[project_end:])
    with pytest.raises(ValueError, match="runtime"):
        verify_serving_lock(changed, frozen.name.split(".")[0])


@pytest.mark.parametrize("command", ["activate", "rollback"])
def test_documented_model_id_option_reaches_validation(tmp_path, command):
    from typer.testing import CliRunner

    from reco.cli import app

    result = CliRunner().invoke(app, [command, "--model-id", "invalid", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Invalid model ID" in result.output
