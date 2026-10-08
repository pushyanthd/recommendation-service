"""Development selection, frozen refit and final scoring in separate invocations."""

import gc
import importlib.metadata
import json
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any, cast

from threadpoolctl import threadpool_info, threadpool_limits

from reco.contracts import BenchmarkProtocol, Rating, Variant
from reco.data import Dataset, chronological_split
from reco.evaluation import evaluate
from reco.ranking import Ranker
from reco.reports import write_reports
from reco.selection import quality_gate, select_variant
from reco.storage import atomic_json, json_hash, process_lock, sha256_file


def execution_identity(lock: Path) -> dict[str, Any]:
    source = Path(__file__).parent
    return {
        "source_files": {
            str(path.relative_to(source)): sha256_file(path)
            for path in sorted(source.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        },
        "dependency_lock_sha256": sha256_file(lock),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "implicit", "fastapi", "pydantic", "threadpoolctl")
        },
        "python": platform.python_version(),
    }


def peak_rss_bytes() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == "darwin" else rss * 1024)


def score_variants(
    dataset: Dataset,
    history: tuple[Rating, ...],
    future: tuple[Rating, ...],
    variants: list[str],
) -> list[dict[str, Any]]:
    reports = []
    for variant in variants:
        started = time.perf_counter()
        with threadpool_limits(limits=1, user_api="blas"):
            ranker = Ranker(dataset, history, cast(Variant, variant))
            fit_ms = (time.perf_counter() - started) * 1000
            report = evaluate(ranker, future)
        report["fit_ms"] = fit_ms
        reports.append(report)
        del ranker
        gc.collect()
    return reports


def run_benchmark(
    dataset: Dataset, output: Path, protocol_path: Path, lock: Path, final: bool = False
) -> dict[str, Any]:
    protocol = BenchmarkProtocol.model_validate_json(protocol_path.read_bytes()).model_dump(
        mode="json"
    )
    identity = execution_identity(lock)
    split = chronological_split(dataset.ratings, protocol["train_fraction"], protocol["test_start"])
    split_manifest = {
        "validation_cutoff": split.validation_cutoff,
        "test_cutoff": split.test_cutoff,
        "train_events": len(split.train),
        "validation_events": len(split.validation),
        "test_events": len(split.test),
    }
    frozen_inputs = {
        "data_mode": dataset.data_mode,
        "data_fingerprint": dataset.fingerprint,
        "split": split_manifest,
        "protocol": protocol,
        "execution_identity": identity,
    }
    output.mkdir(parents=True, exist_ok=True)
    with process_lock(output / ".benchmark.lock"):
        phase_dir = output / ("final" if final else "development")
        if phase_dir.exists():
            raise ValueError(
                "Immutable benchmark phase already exists; choose a new output directory"
            )
        freeze_path = output / "freeze.json"
        if final:
            freeze = json.loads(freeze_path.read_text())
            freeze_digest = freeze.pop("freeze_sha256", None)
            if freeze_digest != json_hash(freeze) or freeze["inputs"] != frozen_inputs:
                raise ValueError(
                    "Frozen data, split, protocol, code or dependency identity changed"
                )
            development = output / "development" / "report.json"
            if sha256_file(development) != freeze["development_report_sha256"]:
                raise ValueError("Frozen validation evidence changed")
            selection = freeze["selection"]
            reports = score_variants(
                dataset, split.train + split.validation, split.test, protocol["variants"]
            )
            baseline = reports[0]
            final_gates = [quality_gate(baseline, report, protocol) for report in reports[1:]]
            selected = selection["selected_for_final_refit"]
            selected_pass = next(
                (gate["passed"] for gate in final_gates if gate["variant"] == selected), False
            )
            status = (
                "experimental_operations_pending"
                if selected_pass
                else "experimental_quality_objective_failed"
            )
            phase = "frozen_final_test"
        else:
            if freeze_path.exists():
                raise ValueError("A frozen development decision already exists")
            reports = score_variants(dataset, split.train, split.validation, protocol["variants"])
            selection = select_variant(reports, protocol)
            final_gates = []
            status = "development_only"
            phase = "development_validation"
        report = {
            **frozen_inputs,
            "schema_version": 1,
            "phase": phase,
            "backend": "cpu",
            "release_status": status,
            "selection": selection,
            "final_quality_gates": final_gates,
            "variants": reports,
            "hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "peak_process_rss_bytes": peak_rss_bytes(),
                "numerical_libraries": threadpool_info(),
                "blas_threads_during_fit_and_scoring": 1,
                "als_threads": 2,
            },
            "resource_gate": peak_rss_bytes() < protocol["maximum_peak_rss_bytes"],
            "http_load_gate": "unmeasured_no_promotion",
            "limitations": [
                "Rating activity timestamps are not verified viewing/exposure times",
                "Missing ratings are unobserved preferences",
                "Fixture correctness cannot establish MovieLens ranking quality",
                "No product pass or deployment promotion before HTTP and bundle checks",
            ],
        }
        if not report["resource_gate"]:
            report["release_status"] = "experimental_memory_objective_failed"
            report["selection"]["serving_variant"] = "popularity"
        write_reports(phase_dir, report)
        if not final:
            freeze = {
                "inputs": frozen_inputs,
                "selection": selection,
                "development_report_sha256": sha256_file(phase_dir / "report.json"),
            }
            atomic_json(freeze_path, {**freeze, "freeze_sha256": json_hash(freeze)})
        return report
