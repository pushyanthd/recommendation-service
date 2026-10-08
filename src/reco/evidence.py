"""Verify complete report files and reject incompatible regression comparisons."""

import json
from pathlib import Path
from typing import Any

import numpy as np

from reco.selection import paired_comparison, validate_report
from reco.storage import sha256_file


def verify_evidence(directory: Path) -> dict[str, Any]:
    expected = json.loads((directory / "checksums.json").read_text())
    if set(expected) != {"report.json", "report.md", "report.html"}:
        raise ValueError("Report checksums are incomplete")
    for name, digest in expected.items():
        if sha256_file(directory / name) != digest:
            raise ValueError(f"Report checksum mismatch: {name}")
    report: dict[str, Any] = json.loads((directory / "report.json").read_text())
    if report["schema_version"] != 1 or report["phase"] not in (
        "development_validation",
        "frozen_final_test",
    ):
        raise ValueError("Unsupported report protocol")
    if [variant["variant"] for variant in report["variants"]] != report["protocol"]["variants"]:
        raise ValueError("Report is missing frozen ranking variants")
    for variant in report["variants"]:
        validate_report(variant)
        if variant["data_fingerprint"] != report["data_fingerprint"]:
            raise ValueError("Variant data identity does not match run")
    for variant in report["variants"][1:]:
        paired_comparison(report["variants"][0], variant, samples=1)
    return report


def compare_evidence(
    previous: dict[str, Any], current: dict[str, Any], unchanged_treatment: bool = False
) -> dict[str, Any]:
    for field in ("schema_version", "phase", "data_mode", "data_fingerprint", "split", "protocol"):
        if previous[field] != current[field]:
            raise ValueError(f"Incompatible report comparison: {field}")
    if unchanged_treatment and previous["execution_identity"] != current["execution_identity"]:
        raise ValueError("Unchanged-treatment code/dependency identity differs")
    comparisons = []
    for left, right in zip(previous["variants"], current["variants"], strict=True):
        if left["variant"] != right["variant"]:
            raise ValueError("Variant treatment mapping differs")
        if unchanged_treatment:
            if left["model_id"] != right["model_id"] or left["config"] != right["config"]:
                raise ValueError("Unchanged-treatment model/configuration identity differs")
            for a, b in zip(left["users"], right["users"], strict=True):
                for name in left["metrics"]:
                    if not np.isclose(a["metrics"][name], b["metrics"][name], atol=1e-6, rtol=0):
                        raise ValueError("Unchanged-treatment user metrics are not reproducible")
        comparisons.append(
            paired_comparison(
                left,
                right,
                current["protocol"]["bootstrap_samples"],
                current["protocol"]["bootstrap_seed"],
            )
        )
    return {
        "compatible": True,
        "unchanged_treatment": unchanged_treatment,
        "comparisons": comparisons,
    }


def export_summary(source: Path, destination: Path) -> None:
    """Export only aggregates after verifying every raw user and all report files."""
    from reco.reports import write_reports

    report = verify_evidence(source)
    for variant in report["variants"]:
        del variant["users"]
    for library in report["hardware"]["numerical_libraries"]:
        if "filepath" in library:
            library["filepath"] = Path(library["filepath"]).name
    report["evidence_kind"] = "aggregate_summary_not_raw_user_evidence"
    report["raw_source_report_sha256"] = sha256_file(source / "report.json")
    report["raw_user_accounting_verified_before_export"] = True
    write_reports(destination, report)
