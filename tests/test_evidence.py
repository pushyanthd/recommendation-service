import copy
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reco.benchmark import run_benchmark
from reco.cli import app
from reco.data import Dataset, chronological_split, load_fixture
from reco.evidence import compare_evidence, export_summary, verify_evidence
from reco.reports import write_reports

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def development(tmp_path):
    run_benchmark(load_fixture(), tmp_path, ROOT / "config/benchmark.json", ROOT / "uv.lock")
    return tmp_path / "development"


def test_report_files_and_population_accounting_verified(development):
    report = verify_evidence(development)
    result = compare_evidence(report, report, unchanged_treatment=True)
    assert result["compatible"]
    assert all(
        comparison["metrics"]["ndcg_at_10"]["absolute_difference"] == 0
        for comparison in result["comparisons"]
    )


def test_corrupted_report_rejected(development):
    (development / "report.html").write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        verify_evidence(development)


def test_public_summary_has_aggregate_provenance_without_users(development, tmp_path):
    destination = tmp_path / "public"
    export_summary(development, destination)
    summary = json.loads((destination / "report.json").read_text())
    assert summary["raw_user_accounting_verified_before_export"]
    assert all("users" not in variant for variant in summary["variants"])
    assert '"user_id"' not in (destination / "report.json").read_text()
    assert len(summary["raw_source_report_sha256"]) == 64


def test_changed_model_is_allowed_only_as_declared_treatment(development):
    old = verify_evidence(development)
    new = copy.deepcopy(old)
    new["variants"][0]["model_id"] = "new-model"
    assert compare_evidence(old, new)["compatible"]
    with pytest.raises(ValueError, match="model/configuration"):
        compare_evidence(old, new, unchanged_treatment=True)


def test_changed_user_metrics_fail_unchanged_treatment_reproduction(development):
    old = verify_evidence(development)
    new = copy.deepcopy(old)
    new["variants"][0]["users"][0]["metrics"]["ndcg_at_10"] += 0.01
    with pytest.raises(ValueError, match="not reproducible"):
        compare_evidence(old, new, unchanged_treatment=True)


@pytest.mark.parametrize("field", ["data_fingerprint", "split", "protocol", "phase"])
def test_incompatible_benchmarks_fail_without_overwriting_baseline(development, field):
    raw = (development / "report.json").read_bytes()
    old = verify_evidence(development)
    new = copy.deepcopy(old)
    new[field] = "changed"
    with pytest.raises(ValueError, match="Incompatible"):
        compare_evidence(old, new)
    assert (development / "report.json").read_bytes() == raw


def test_escaped_standalone_report(development):
    report = verify_evidence(development)
    report["release_status"] = '<script>alert("unsafe")</script>'
    write_reports(development, report)
    rendered = (development / "report.html").read_text()
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_cli_missing_setup_and_missing_frozen_report_fail_with_typed_output(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--dataset-dir",
            str(tmp_path / "absent"),
            "--output",
            str(tmp_path / "run"),
        ],
    )
    assert result.exit_code == 1
    failure = json.loads((tmp_path / "run/failure.json").read_text())
    assert failure["stage"] == "development"
    assert failure["error_type"] == "FileNotFoundError"
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--fixture",
            "--final",
            "--output",
            str(tmp_path / "no-freeze"),
            "--protocol",
            str(ROOT / "config/benchmark.json"),
            "--lock",
            str(ROOT / "uv.lock"),
        ],
    )
    assert result.exit_code == 1
    assert json.loads((tmp_path / "no-freeze/failure.json").read_text())["stage"] == "frozen_final"
    assert not (tmp_path / "no-freeze/final").exists()


def test_cli_verification_rejects_missing_evidence(tmp_path):
    result = CliRunner().invoke(app, ["verify-report", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "Unusable evidence" in result.output


def test_held_out_test_labels_cannot_change_validation_selection(tmp_path):
    data = load_fixture()
    split = chronological_split(data.ratings)
    changed = Dataset(
        data.movies,
        tuple(
            event.model_copy(update={"rating": 1})
            if event.timestamp >= split.test_cutoff
            else event
            for event in data.ratings
        ),
        "changed-test-labels",
    )
    first = run_benchmark(data, tmp_path / "a", ROOT / "config/benchmark.json", ROOT / "uv.lock")
    second = run_benchmark(
        changed, tmp_path / "b", ROOT / "config/benchmark.json", ROOT / "uv.lock"
    )
    assert first["selection"] == second["selection"]
    for left, right in zip(first["variants"], second["variants"], strict=True):
        assert left["metrics"] == pytest.approx(right["metrics"])


def test_code_and_lock_identity_changes_block_final_scoring(tmp_path, monkeypatch):
    from reco import benchmark

    data = load_fixture()
    benchmark.run_benchmark(data, tmp_path, ROOT / "config/benchmark.json", ROOT / "uv.lock")
    real_identity = benchmark.execution_identity(ROOT / "uv.lock")
    real_identity["source_files"]["ranking.py"] = "changed"
    monkeypatch.setattr(benchmark, "execution_identity", lambda _: real_identity)
    with pytest.raises(ValueError, match="identity changed"):
        benchmark.run_benchmark(
            data, tmp_path, ROOT / "config/benchmark.json", ROOT / "uv.lock", True
        )
    assert not (tmp_path / "final").exists()
