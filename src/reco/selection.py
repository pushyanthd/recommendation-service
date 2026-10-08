"""Paired numerical evidence and development-only quality selection."""

from typing import Any

import numpy as np


def validate_report(report: dict[str, Any]) -> None:
    if set(report["metrics"]) != {"recall_at_10", "recall_at_20", "ndcg_at_10", "hit_rate_at_10"}:
        raise ValueError("Metric evidence is incomplete")
    users = report["users"]
    ids = [record["user_id"] for record in users]
    if not ids or ids != sorted(set(ids)) or len(ids) != report["eligible_users"]:
        raise ValueError("Missing, duplicate or unordered user evidence")
    failed = sum(record["error"] is not None for record in users)
    if failed != report["failed_users"] or len(ids) - failed != report["completed_users"]:
        raise ValueError("User completion accounting mismatch")
    if report["total_users"] != report["eligible_users"] + report["no_target_users"]:
        raise ValueError("Population accounting mismatch")
    if report["positive_targets"] != sum(record["relevant_count"] for record in users):
        raise ValueError("Positive target accounting mismatch")
    if report["unreachable_positives"] != sum(
        record["unreachable_positive_count"] for record in users
    ):
        raise ValueError("Unreachable target accounting mismatch")
    if any(
        record["relevant_count"] <= 0
        or not 0 <= record["unreachable_positive_count"] <= record["relevant_count"]
        for record in users
    ):
        raise ValueError("Invalid positive target counts")
    timings = np.array([record["scoring_ms"] for record in users])
    if not np.isfinite(timings).all() or np.any(timings < 0):
        raise ValueError("Invalid scoring timings")
    if not np.isfinite(report["fit_ms"]) or report["fit_ms"] < 0:
        raise ValueError("Invalid fit timing")
    for name, mean in report["metrics"].items():
        values = np.array([record["metrics"][name] for record in users], dtype=float)
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ValueError("Invalid metric evidence")
        if not np.isclose(mean, values.mean(), atol=1e-12, rtol=0):
            raise ValueError("Aggregate metric does not match user records")
        if any(record["error"] is not None and record["metrics"][name] != 0 for record in users):
            raise ValueError("Failed users must score zero")


def paired_comparison(
    baseline: dict[str, Any], candidate: dict[str, Any], samples: int = 2000, seed: int = 42
) -> dict[str, Any]:
    validate_report(baseline)
    validate_report(candidate)
    if samples < 1:
        raise ValueError("Bootstrap requires at least one resample")
    for field in (
        "data_mode",
        "data_fingerprint",
        "history_fingerprint",
        "target_fingerprint",
        "metric_protocol",
        "catalog_fingerprint",
        "total_users",
        "no_target_users",
    ):
        if baseline[field] != candidate[field]:
            raise ValueError(f"Incompatible comparison evidence: {field}")
    for left, right in zip(baseline["users"], candidate["users"], strict=True):
        for field in ("user_id", "cohort", "relevant_count", "unreachable_positive_count"):
            if left[field] != right[field]:
                raise ValueError(f"Incompatible paired user evidence: {field}")
    rng = np.random.default_rng(seed)
    count = len(baseline["users"])
    differences = np.array(
        [
            [right["metrics"][name] - left["metrics"][name] for name in baseline["metrics"]]
            for left, right in zip(baseline["users"], candidate["users"], strict=True)
        ]
    )
    # Bounded batches avoid allocating samples x users x metrics for larger cohorts.
    means = np.empty((samples, differences.shape[1]))
    for start in range(0, samples, 64):
        end = min(samples, start + 64)
        indices = rng.integers(0, count, size=(end - start, count))
        means[start:end] = differences[indices].mean(axis=1)
    output = {}
    for column, name in enumerate(baseline["metrics"]):
        lower, upper = np.percentile(means[:, column], [2.5, 97.5])
        output[name] = {
            "absolute_difference": float(differences[:, column].mean()),
            "paired_95_interval": [float(lower), float(upper)],
        }
    baseline_ndcg = baseline["metrics"]["ndcg_at_10"]
    return {
        "candidate": candidate["variant"],
        "paired_users": count,
        "samples": samples,
        "seed": seed,
        "metrics": output,
        "relative_ndcg_gain": (
            output["ndcg_at_10"]["absolute_difference"] / baseline_ndcg
            if baseline_ndcg > 1e-12
            else None
        ),
        "interval_scope": "Paired benchmark users; shared items/training limit generalization",
    }


def quality_gate(
    baseline: dict[str, Any], candidate: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, Any]:
    comparison = paired_comparison(
        baseline, candidate, protocol["bootstrap_samples"], protocol["bootstrap_seed"]
    )
    reasons = []
    gain = comparison["relative_ndcg_gain"]
    if gain is None:
        reasons.append("near_zero_baseline_requires_new_development_protocol")
    elif gain < protocol["minimum_relative_ndcg_gain"]:
        reasons.append("ndcg_relative_gain_below_objective")
    if comparison["metrics"]["ndcg_at_10"]["paired_95_interval"][0] <= 0:
        reasons.append("ndcg_interval_not_above_zero")
    if (
        comparison["metrics"]["recall_at_20"]["absolute_difference"]
        < -protocol["maximum_recall_at_20_drop"]
    ):
        reasons.append("recall_at_20_regression")
    if baseline["failed_users"] or candidate["failed_users"]:
        reasons.append("scoring_or_invariant_failures")
    if candidate["fit_ms"] > protocol["maximum_single_fit_seconds"] * 1000:
        reasons.append("training_time_objective_failed")
    return {
        "variant": candidate["variant"],
        "passed": not reasons,
        "reasons": reasons,
        "comparison": comparison,
    }


def select_variant(reports: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    if [report["variant"] for report in reports] != protocol["variants"]:
        raise ValueError("Missing or reordered variant evidence")
    for report in reports:
        validate_report(report)
    baseline = reports[0]
    if baseline["failed_users"]:
        raise ValueError("Popularity baseline has failures; selection is unusable")
    gates = [quality_gate(baseline, report, protocol) for report in reports[1:]]
    passing = {gate["variant"] for gate in gates if gate["passed"]}
    candidates = [report for report in reports[1:] if report["variant"] in passing]
    selected = "popularity"
    if candidates:
        highest = max(report["metrics"]["ndcg_at_10"] for report in candidates)
        tied = [
            report
            for report in candidates
            if highest - report["metrics"]["ndcg_at_10"] <= protocol["near_tie_absolute_ndcg"]
        ]
        selected = min(tied, key=lambda report: protocol["variants"].index(report["variant"]))[
            "variant"
        ]
    return {
        "selected_for_final_refit": selected,
        "quality_gates": gates,
        "serving_variant": "popularity",
        "promotion_status": "pending_http_resource_and_bundle_gates",
        "test_labels_used_for_selection": False,
    }
