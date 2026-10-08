import json
from pathlib import Path

import pytest
from test_bundles_and_lifecycle import free_port

from reco.benchmark import run_benchmark
from reco.bundles import build_from_report
from reco.data import load_fixture
from reco.lifecycle import select_initial
from reco.showcase import export_showcase, run_showcase, verify_showcase
from reco.storage import sha256_file


def test_process_backed_showcase_accounts_for_requests_and_all_four_drills(tmp_path):
    dataset = load_fixture()
    benchmark = tmp_path / "benchmark"
    run_benchmark(dataset, benchmark, Path("config/benchmark.json"), Path("uv.lock"))
    run_benchmark(dataset, benchmark, Path("config/benchmark.json"), Path("uv.lock"), final=True)
    root = tmp_path / "models"
    directory = build_from_report(dataset, benchmark / "final", root, Path("uv.lock"))
    select_initial(root, directory.name)
    output = tmp_path / "showcase"
    evidence = run_showcase(
        root,
        benchmark / "final",
        output,
        Path("uv.lock"),
        free_port(),
        requests=12,
        rate=100,
        warmup=6,
    )
    assert evidence["http_load"]["scheduled"] == 12
    assert evidence["http_load"]["completed"] == 12
    assert evidence["http_load"]["failed"] == 0
    assert len(evidence["drills"]) == 4
    assert all(result["passed"] for result in evidence["drills"].values())
    assert not evidence["engineering_acceptance_passed"]
    assert not evidence["http_load"]["reference_protocol_complete"]
    assert not (output / "service" / "process.json").exists()
    timings = json.loads((output / "http" / "timings.json").read_text())
    assert [row["sequence"] for row in timings] == list(range(12))
    assert all(row["wall_ms"] >= row["queue_ms"] for row in timings)
    checksums = json.loads((output / "checksums.json").read_text())
    for name, digest in checksums.items():
        assert sha256_file(output / name) == digest
    assert verify_showcase(output)["model_id"] == directory.name
    public = tmp_path / "public"
    export_showcase(output, public)
    assert verify_showcase(public, raw=False)["raw_accounting_verified_before_export"]
    (output / "http" / "timings.json").write_text("[]")
    with pytest.raises(ValueError, match="timings"):
        verify_showcase(output)
    with pytest.raises(ValueError, match="Immutable"):
        run_showcase(root, benchmark / "final", output, Path("uv.lock"))


def test_unsafe_load_configuration_rejected_before_http(tmp_path):
    import asyncio

    from reco.load import measure_http

    with pytest.raises(ValueError, match="owned loopback"):
        asyncio.run(measure_http("https://untrusted.example", tmp_path, "irrelevant"))
    with pytest.raises(ValueError, match="configuration"):
        asyncio.run(measure_http("http://127.0.0.1:9999", tmp_path, "irrelevant", requests=0))
