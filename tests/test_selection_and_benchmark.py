import copy
import json
from pathlib import Path

import pytest

from reco.benchmark import run_benchmark
from reco.data import chronological_split, load_fixture
from reco.evaluation import evaluate
from reco.ranking import Ranker
from reco.selection import paired_comparison, select_variant
from reco.storage import process_lock, sha256_file

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config/benchmark.json"
LOCK = ROOT / "uv.lock"


def authored_report(variant, ndcg, recall=0.5):
    source = load_fixture()
    split = chronological_split(source.ratings)
    report = evaluate(Ranker(source, split.train, "popularity"), split.validation)
    report["variant"] = variant
    report["fit_ms"] = 1
    for record in report["users"]:
        record["metrics"].update(ndcg_at_10=ndcg, recall_at_20=recall)
    report["metrics"].update(ndcg_at_10=ndcg, recall_at_20=recall)
    return report


def test_paired_interval_known_constant_difference_and_seed_repeatability():
    baseline = authored_report("popularity", 0.2)
    candidate = authored_report("item_knn", 0.3)
    first = paired_comparison(baseline, candidate)
    assert first == paired_comparison(baseline, candidate)
    assert first["relative_ndcg_gain"] == pytest.approx(0.5)
    assert first["metrics"]["ndcg_at_10"]["paired_95_interval"] == pytest.approx([0.1, 0.1])


def test_gates_and_simpler_near_tie_selection():
    reports = [
        authored_report("popularity", 0.2),
        authored_report("item_knn", 0.3),
        authored_report("als_cpu", 0.3005),
    ]
    decision = select_variant(reports, json.loads(PROTOCOL.read_text()))
    assert decision["selected_for_final_refit"] == "item_knn"
    assert decision["serving_variant"] == "popularity"  # HTTP/bundle gates still required.
    assert all(gate["passed"] for gate in decision["quality_gates"])


def test_failed_quality_keeps_popularity_and_records_reasons():
    reports = [
        authored_report("popularity", 0.2),
        authored_report("item_knn", 0.201),
        authored_report("als_cpu", 0.3, recall=0.48),
    ]
    decision = select_variant(reports, json.loads(PROTOCOL.read_text()))
    assert decision["selected_for_final_refit"] == "popularity"
    assert "ndcg_relative_gain_below_objective" in decision["quality_gates"][0]["reasons"]
    assert "recall_at_20_regression" in decision["quality_gates"][1]["reasons"]


def test_zero_baseline_does_not_invent_relative_improvement():
    reports = [
        authored_report("popularity", 0),
        authored_report("item_knn", 0.2),
        authored_report("als_cpu", 0.3),
    ]
    decision = select_variant(reports, json.loads(PROTOCOL.read_text()))
    assert decision["selected_for_final_refit"] == "popularity"
    assert decision["quality_gates"][0]["comparison"]["relative_ndcg_gain"] is None


@pytest.mark.parametrize(
    "field",
    [
        "data_fingerprint",
        "history_fingerprint",
        "target_fingerprint",
        "metric_protocol",
        "catalog_fingerprint",
    ],
)
def test_incompatible_evidence_never_passes(field):
    baseline = authored_report("popularity", 0.2)
    candidate = authored_report("item_knn", 0.3)
    candidate[field] = "changed"
    with pytest.raises(ValueError, match="Incompatible"):
        paired_comparison(baseline, candidate)


def test_missing_duplicate_or_rewritten_user_evidence_is_unusable():
    baseline = authored_report("popularity", 0.2)
    for mutation in ("missing", "duplicate", "mean", "failures"):
        candidate = copy.deepcopy(baseline)
        if mutation == "missing":
            candidate["users"].pop()
        elif mutation == "duplicate":
            candidate["users"][1]["user_id"] = candidate["users"][0]["user_id"]
        elif mutation == "mean":
            candidate["metrics"]["ndcg_at_10"] = 0.9
        else:
            candidate["failed_users"] = 1
        with pytest.raises(ValueError):
            paired_comparison(baseline, candidate)


def test_development_freeze_and_final_report_are_separate_immutable_phases(tmp_path):
    data = load_fixture()
    development = run_benchmark(data, tmp_path, PROTOCOL, LOCK)
    assert development["phase"] == "development_validation"
    assert not (tmp_path / "final").exists()
    frozen = (tmp_path / "freeze.json").read_bytes()
    final = run_benchmark(data, tmp_path, PROTOCOL, LOCK, final=True)
    assert final["phase"] == "frozen_final_test"
    assert final["selection"] == development["selection"]
    assert (tmp_path / "freeze.json").read_bytes() == frozen
    for phase in ("development", "final"):
        directory = tmp_path / phase
        for name, digest in json.loads((directory / "checksums.json").read_text()).items():
            assert sha256_file(directory / name) == digest
        for variant in json.loads((directory / "report.json").read_text())["variants"]:
            assert variant["eligible_users"] == variant["completed_users"] + variant["failed_users"]
    with pytest.raises(ValueError, match="already exists"):
        run_benchmark(data, tmp_path, PROTOCOL, LOCK, final=True)


@pytest.mark.parametrize("change", ["protocol", "validation", "freeze"])
def test_frozen_input_tampering_prevents_final_scoring(tmp_path, change):
    data = load_fixture()
    run_benchmark(data, tmp_path, PROTOCOL, LOCK)
    protocol = PROTOCOL
    if change == "protocol":
        protocol = tmp_path / "new-protocol.json"
        config = json.loads(PROTOCOL.read_text())
        config["minimum_relative_ndcg_gain"] = 0
        protocol.write_text(json.dumps(config))
    elif change == "validation":
        (tmp_path / "development/report.json").write_text("{}")
    else:
        freeze = json.loads((tmp_path / "freeze.json").read_text())
        freeze["selection"]["selected_for_final_refit"] = "als_cpu"
        (tmp_path / "freeze.json").write_text(json.dumps(freeze))
    with pytest.raises(ValueError, match="Frozen"):
        run_benchmark(data, tmp_path, protocol, LOCK, final=True)
    assert not (tmp_path / "final").exists()


def test_process_lock_prevents_concurrent_selection(tmp_path):
    with (
        process_lock(tmp_path / ".benchmark.lock"),
        pytest.raises(ValueError, match="process lock"),
    ):
        run_benchmark(load_fixture(), tmp_path, PROTOCOL, LOCK)
