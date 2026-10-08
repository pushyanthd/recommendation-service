"""Process-backed HTTP/recovery evidence bound to a locally verified model snapshot."""

import asyncio
import html
import json
import os
import platform
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from reco.benchmark import execution_identity
from reco.bundles import write_bundle
from reco.contracts import RecommendationRequest
from reco.evidence import verify_evidence
from reco.lifecycle import activate, active_bundle, select_initial, start, stop
from reco.load import measure_http
from reco.selection import select_variant
from reco.storage import atomic_json, json_hash, sha256_file


def _http_recommend(port: int, payload: RecommendationRequest) -> dict[str, Any]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/recommendations",
        data=payload.model_dump_json(exclude_none=True).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        result: dict[str, Any] = json.load(response)
    return result


def _write_reports(output: Path, report: dict[str, Any]) -> None:
    atomic_json(output / "report.json", report)
    rows = report["quality_variants"]
    markdown = (
        "# CPU recommendation service showcase\n\n"
        f"Status: **{report['release_status']}**. Selected: **{report['variant']}**.\n\n"
        f"Model: `{report['model_id']}`. Data: `{report['data_mode']}`.\n\n"
        "| Method | Final NDCG@10 | Final Recall@20 |\n|---|---:|---:|\n"
    )
    for row in rows:
        markdown += (
            f"| {row['variant']} | {row['metrics']['ndcg_at_10']:.6f} | "
            f"{row['metrics']['recall_at_20']:.6f} |\n"
        )
    load = report["http_load"]
    markdown += (
        f"\nHTTP: {load['completed']}/{load['scheduled']} completed; "
        f"{load['failed']} failures; warm client P95 {load['client_wall_ms']['p95']:.3f} ms; "
        f"{load['achieved_requests_per_second']:.2f} requests/s.\n\n"
        f"API process peak RSS: {load['peak_api_process_rss_bytes'] / 1024**2:.1f} MiB. "
        f"Snapshot startup load: {load['startup_load_ms']:.2f} ms.\n\n"
        "## Recovery drills\n\n"
    )
    for name, result in report["drills"].items():
        markdown += f"- {name}: {'passed' if result['passed'] else 'failed'}\n"
    markdown += (
        "\nValidation selection is preserved. Final metrics do not select a new model. "
        "Offline rating recovery does not establish viewing, clicks or revenue. "
        "HTTP latency includes client queueing. Docker/whole-system memory is separate. "
        "Raw timings and process evidence remain in ignored local artifacts.\n"
    )
    (output / "report.md").write_text(markdown)
    table = "".join(
        f"<tr><td>{html.escape(row['variant'])}</td>"
        f"<td>{row['metrics']['ndcg_at_10']:.6f}</td>"
        f"<td>{row['metrics']['recall_at_20']:.6f}</td></tr>"
        for row in rows
    )
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>CPU recommendation service showcase</title><style>"
        "body{font:16px/1.65 system-ui;max-width:1000px;margin:48px auto;padding:0 24px;"
        "background:#f4f6f1;color:#19332d}table{border-collapse:collapse;width:100%;"
        "background:white}th,td{text-align:left;padding:12px;border-bottom:1px solid #ccd8d0}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:24px;"
        "border-radius:12px}h1{font-size:40px}</style><h1>CPU ranking, measured.</h1>"
        f"<p>{html.escape(report['release_status'])} · {html.escape(report['data_mode'])}</p>"
        "<table><tr><th>Method</th><th>Final NDCG@10</th><th>Final Recall@20</th></tr>"
        f"{table}</table><h2>Serving and recovery evidence</h2><pre>{html.escape(markdown)}</pre>"
        "<details><summary>Full provenance and acceptance evidence</summary>"
        f"<pre>{html.escape(json.dumps(report, indent=2))}</pre></details></html>"
    )
    (output / "report.html").write_text(document)
    atomic_json(
        output / "checksums.json",
        {name: sha256_file(output / name) for name in ("report.json", "report.md", "report.html")},
    )


def run_showcase(
    root: Path,
    report_dir: Path,
    output: Path,
    lock: Path,
    port: int = 8765,
    requests: int = 5000,
    rate: float = 20,
    warmup: int = 200,
    container_evidence: Path | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise ValueError("Immutable showcase already exists; choose a fresh output directory")
    original = active_bundle(root)
    identity = execution_identity(lock)
    if original.manifest.execution_identity != identity:
        raise ValueError("Serving bundle code/dependencies differ; build a current snapshot")
    final = verify_evidence(report_dir)
    if (
        original.manifest.final_report_sha256 != sha256_file(report_dir / "report.json")
        or original.manifest.data_fingerprint != final["data_fingerprint"]
        or original.manifest.variant != final["selection"]["selected_for_final_refit"]
    ):
        raise ValueError("Active snapshot and final evidence differ")
    output.mkdir(parents=True)
    service_root = output / "service"
    service_root.mkdir()
    shutil.copytree(root / original.manifest.model_id, service_root / original.manifest.model_id)
    select_initial(service_root, original.manifest.model_id)
    snapshot = original.ranker
    payload = RecommendationRequest(liked_movie_ids=[], k=10)
    expected = snapshot.recommend(payload)
    expected_ids = [hit.movie_id for hit in expected.items]
    drills: dict[str, Any] = {}
    started = time.perf_counter()
    try:
        first = start(service_root, port)
        readiness_wall_ms = (time.perf_counter() - started) * 1000
        actual = _http_recommend(port, payload)
        if [hit["movie_id"] for hit in actual["items"]] != expected_ids:
            raise ValueError("HTTP ranking differs from verified snapshot")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/model", timeout=5) as response:
            runtime = json.load(response)
        if runtime["runtime_identity_sha256"] != json_hash(identity):
            raise ValueError("Actual process source/dependencies differ from tested identity")
        # A second locally built version exercises activation/rollback without changing treatment.
        snapshot.model_id = original.manifest.ranking_model_id
        second = write_bundle(
            service_root,
            snapshot,
            original.manifest.training_cutoff,
            original.manifest.selection,
            original.manifest.release_status,
            {**identity, "drill": "second_trusted_version"},
            original.manifest.final_report_sha256,
        )
        before = (service_root / "active.json").read_bytes()
        saved = (second / "popularity.npz").read_bytes()
        (second / "popularity.npz").write_bytes(b"forced corruption")
        try:
            activate(service_root, second.name)
            raise RuntimeError("Corrupt candidate was activated")
        except ValueError as exc:
            if "checksum" not in str(exc):
                raise
            drills["corrupt_candidate_rejected"] = {
                "passed": before == (service_root / "active.json").read_bytes(),
                "error": str(exc),
                "active_pointer_unchanged": before == (service_root / "active.json").read_bytes(),
            }
        finally:
            (second / "popularity.npz").write_bytes(saved)
        development = verify_evidence(report_dir.parent / "development")
        forced = select_variant(
            development["variants"],
            {
                **development["protocol"],
                "minimum_relative_ndcg_gain": 1_000_000,
            },
        )
        if forced["selected_for_final_refit"] != "popularity":
            raise ValueError("Forced development rejection did not preserve baseline")
        rejected = write_bundle(
            service_root,
            snapshot,
            original.manifest.training_cutoff,
            {**original.manifest.selection, "activation_allowed": False},
            "experimental_forced_gate_rejection",
            identity,
            original.manifest.final_report_sha256,
        )
        try:
            activate(service_root, rejected.name)
            raise RuntimeError("Rejected candidate was activated")
        except ValueError as exc:
            if "gate rejected" not in str(exc):
                raise
            drills["forced_gate_rejection"] = {
                "passed": before == (service_root / "active.json").read_bytes(),
                "development_selected": forced["selected_for_final_refit"],
                "candidate_error": str(exc),
            }
        stop(service_root)
        restarted = start(service_root, port)
        after = _http_recommend(port, payload)
        drills["restart_preserves_version_and_ranking"] = {
            "passed": restarted["pid"] != first["pid"]
            and after["model_id"] == original.manifest.model_id
            and [hit["movie_id"] for hit in after["items"]] == expected_ids
            and np.allclose(
                [hit["score"] for hit in after["items"]],
                [hit.score for hit in expected.items],
                atol=1e-6,
                rtol=1e-6,
            ),
            "before_pid": first["pid"],
            "after_pid": restarted["pid"],
            "model_id": after["model_id"],
        }
        changed = activate(service_root, second.name)
        restored = activate(service_root, original.manifest.model_id, rollback=True)
        after = _http_recommend(port, payload)
        drills["rollback_restores_exact_prior_version"] = {
            "passed": changed["pid"] != restored["pid"]
            and after["model_id"] == original.manifest.model_id
            and [hit["movie_id"] for hit in after["items"]] == expected_ids
            and np.allclose(
                [hit["score"] for hit in after["items"]],
                [hit.score for hit in expected.items],
                atol=1e-6,
                rtol=1e-6,
            ),
            "activated_model_id": second.name,
            "restored_model_id": after["model_id"],
            "activated_pid": changed["pid"],
            "restored_pid": restored["pid"],
        }
        if not all(drill["passed"] for drill in drills.values()):
            raise ValueError("Recovery drill failed")
        load = asyncio.run(
            measure_http(
                f"http://127.0.0.1:{port}",
                output / "http",
                original.manifest.model_id,
                requests,
                rate,
                warmup,
            )
        )
        container = None
        if container_evidence is not None:
            container = json.loads(container_evidence.read_text())
            if (
                container["source_identity_sha256"] != json_hash(identity["source_files"])
                or not container["passed"]
            ):
                raise ValueError("Container evidence is incompatible or failed")
        evidence = {
            "schema_version": 1,
            "evidence_kind": "process_backed_showcase",
            "model_id": original.manifest.model_id,
            "variant": original.manifest.variant,
            "data_mode": original.manifest.data_mode,
            "data_fingerprint": original.manifest.data_fingerprint,
            "execution_identity": identity,
            "bundle_manifest_sha256": sha256_file(
                root / original.manifest.model_id / "manifest.json"
            ),
            "final_report_sha256": original.manifest.final_report_sha256,
            "release_status": original.manifest.release_status,
            "selection": original.manifest.selection,
            "quality_variants": [
                {
                    key: value
                    for key, value in row.items()
                    if key in ("variant", "metrics", "eligible_users", "failed_users", "cohorts")
                }
                for row in final["variants"]
            ],
            "http_load": load,
            "drills": drills,
            "container": container,
            "cold_start_to_readiness_wall_ms": readiness_wall_ms,
            "hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "logical_cpus": os.cpu_count(),
                "python": platform.python_version(),
            },
            "engineering_acceptance_passed": load["reference_protocol_complete"]
            and load["http_gate_passed"]
            and load["memory_gate_passed"]
            and container is not None,
            "quality_objective_passed": any(
                gate["variant"] == original.manifest.variant and gate["passed"]
                for gate in final["final_quality_gates"]
            ),
        }
        if not load["http_gate_passed"] or not load["memory_gate_passed"]:
            evidence["release_status"] = "experimental_serving_objective_failed"
        _write_reports(output, evidence)
        return evidence
    finally:
        stop(service_root)


def verify_showcase(directory: Path, raw: bool = True) -> dict[str, Any]:
    checksums = json.loads((directory / "checksums.json").read_text())
    if set(checksums) != {"report.json", "report.md", "report.html"}:
        raise ValueError("Incomplete showcase files")
    for name, digest in checksums.items():
        if sha256_file(directory / name) != digest:
            raise ValueError("Showcase checksum mismatch")
    report: dict[str, Any] = json.loads((directory / "report.json").read_text())
    if report["schema_version"] != 1 or report["evidence_kind"] != "process_backed_showcase":
        raise ValueError("Unsupported showcase evidence")
    if len(report["drills"]) != 4 or not all(
        drill["passed"] is True for drill in report["drills"].values()
    ):
        raise ValueError("Missing/failed recovery evidence")
    load = report["http_load"]
    if (
        load["model_id"] != report["model_id"]
        or load["scheduled"] != load["completed"] + load["failed"]
    ):
        raise ValueError("Incompatible HTTP model or completion accounting")
    if raw:
        timings_path = directory / "http" / "timings.json"
        if sha256_file(timings_path) != load["raw_timings_sha256"]:
            raise ValueError("Raw HTTP timings changed")
        rows = json.loads(timings_path.read_text())
        if (
            [row["sequence"] for row in rows] != list(range(load["scheduled"]))
            or sum(row["error"] is not None for row in rows) != load["failed"]
            or not np.isclose(
                np.percentile([row["wall_ms"] for row in rows], 95),
                load["client_wall_ms"]["p95"],
                rtol=0,
                atol=1e-9,
            )
        ):
            raise ValueError("HTTP raw/aggregate accounting mismatch")
        if sha256_file(directory / "http" / "metrics.prom") != load["metrics_sha256"]:
            raise ValueError("HTTP telemetry changed")
    elif report.get("raw_accounting_verified_before_export") is not True:
        raise ValueError("Aggregate showcase lacks verified raw accounting")
    return report


def export_showcase(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError("Immutable showcase export already exists")
    report = verify_showcase(source)
    report["raw_accounting_verified_before_export"] = True
    report["raw_source_report_sha256"] = sha256_file(source / "report.json")
    destination.mkdir(parents=True)
    _write_reports(destination, report)
