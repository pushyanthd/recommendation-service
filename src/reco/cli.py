import json
import platform
import time
from pathlib import Path

import typer

from reco.contracts import Variant
from reco.data import chronological_split, load_fixture
from reco.evaluation import evaluate
from reco.ranking import Ranker
from reco.storage import atomic_json

app = typer.Typer(no_args_is_help=True)


@app.command()
def export_summary(source: Path, destination: Path) -> None:
    """Export verified aggregate JSON/Markdown/HTML, without dataset rows or user identifiers."""
    from reco.evidence import export_summary as export

    try:
        export(source, destination)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(f"Unusable source evidence: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Saved verified aggregate comparison to {destination}")


@app.command()
def verify_report(
    directory: Path,
    against: Path | None = None,
    unchanged_treatment: bool = False,
) -> None:
    """Verify files/accounting and optionally compare compatible evidence without rewriting it."""
    from reco.evidence import compare_evidence, verify_evidence

    try:
        current = verify_evidence(directory)
        if unchanged_treatment and against is None:
            raise ValueError("--unchanged-treatment requires --against")
        result = {"verified": True, "phase": current["phase"]}
        if against is not None:
            result.update(compare_evidence(verify_evidence(against), current, unchanged_treatment))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(f"Unusable evidence: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(result, indent=2, allow_nan=False))


@app.command()
def data_fetch(
    destination: Path = Path("artifacts/datasets/ml-1m"),
    archive: Path | None = None,
) -> None:
    """Explicitly install pinned MovieLens 1M; --archive uses an existing offline ZIP."""
    from reco.ingestion import setup_movielens

    try:
        manifest = setup_movielens(destination, archive)
    except (OSError, ValueError) as exc:
        atomic_json(
            destination.parent / "data-failure.json",
            {
                "stage": "data_setup",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(manifest, indent=2))


@app.command()
def benchmark(
    dataset_dir: Path = Path("artifacts/datasets/ml-1m"),
    output: Path = Path("artifacts/benchmark"),
    protocol: Path = Path("config/benchmark.json"),
    lock: Path = Path("uv.lock"),
    fixture: bool = False,
    final: bool = False,
) -> None:
    """Freeze validation selection; --final refits/scores once using that exact frozen identity."""
    from reco.benchmark import run_benchmark
    from reco.ingestion import load_movielens

    try:
        dataset = load_fixture() if fixture else load_movielens(dataset_dir)
        report = run_benchmark(dataset, output, protocol, lock, final)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        atomic_json(
            output / "failure.json",
            {
                "stage": "frozen_final" if final else "development",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"{report['phase']}: {report['selection']['selected_for_final_refit']}; "
        f"{report['release_status']}. Reports: {output}"
    )


@app.command()
def fixture_smoke(output: Path | None = None) -> None:
    """Train all three CPU variants and score only fictional development validation events."""
    dataset = load_fixture()
    split = chronological_split(dataset.ratings)
    reports = []
    variants: tuple[Variant, ...] = ("popularity", "item_knn", "als_cpu")
    for variant in variants:
        started = time.perf_counter()
        ranker = Ranker(dataset, split.train, variant)
        fit_ms = (time.perf_counter() - started) * 1000
        report = evaluate(ranker, split.validation)
        report["fit_ms"] = fit_ms
        reports.append(report)
    evidence = {
        "data_mode": "fictional_fixture",
        "split": "development_validation",
        "backend": "cpu",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "data_fingerprint": dataset.fingerprint,
        "split_counts": {
            "train": len(split.train),
            "validation": len(split.validation),
            "test_reserved": len(split.test),
        },
        "validation_cutoff": split.validation_cutoff,
        "test_cutoff": split.test_cutoff,
        "quality_claim": "Fixture feasibility only; no MovieLens accuracy or promotion claim",
        "variants": reports,
    }
    rendered = json.dumps(evidence, indent=2, allow_nan=False) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered)
        typer.echo(f"Saved three CPU fixture comparisons to {output}")
    else:
        typer.echo(rendered)


@app.command()
def serve_fixture() -> None:
    """Serve the fictional popularity baseline on loopback, with no network downloads."""
    import uvicorn

    uvicorn.run("reco.api:create_app", factory=True, host="127.0.0.1", port=8000)


@app.command()
def build_bundle(
    report: Path = Path("artifacts/benchmark/final"),
    dataset_dir: Path = Path("artifacts/datasets/ml-1m"),
    root: Path = Path("artifacts/models"),
    lock: Path = Path("uv.lock"),
    fixture: bool = False,
    select: bool = False,
) -> None:
    """Build a trusted frozen real-data snapshot, or a visibly fictional offline snapshot."""
    from reco.benchmark import execution_identity
    from reco.bundles import build_from_report, write_bundle
    from reco.ingestion import load_movielens
    from reco.lifecycle import select_initial

    try:
        if fixture and (report / "report.json").exists():
            destination = build_from_report(load_fixture(), report, root, lock)
        elif fixture:
            dataset = load_fixture()
            split = chronological_split(dataset.ratings)
            destination = write_bundle(
                root,
                Ranker(dataset, split.train, "popularity"),
                split.validation_cutoff,
                {"selected_for_final_refit": "popularity"},
                "fictional_fixture_no_real_quality_claim",
                execution_identity(lock),
            )
        else:
            destination = build_from_report(load_movielens(dataset_dir), report, root, lock)
        if select:
            select_initial(root, destination.name)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(f"Bundle build rejected: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(str(destination))


@app.command()
def verify_bundle(directory: Path) -> None:
    """Verify all files, identities, numerical arrays and history mappings without training."""
    from reco.bundles import load_bundle

    try:
        bundle = load_bundle(directory)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(f"Unusable model bundle: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(bundle.manifest.model_dump_json(indent=2))


@app.command()
def serve(root: Path = Path("artifacts/models"), port: int = 8000) -> None:
    """Run a validated snapshot in the foreground on loopback; no training/downloads."""
    import uvicorn

    from reco.api import create_app

    uvicorn.run(create_app(root), host="127.0.0.1", port=port, access_log=False)


@app.command()
def start(root: Path = Path("artifacts/models"), port: int = 8000) -> None:
    """Start a CLI-owned local process and verify requested model readiness."""
    from reco.lifecycle import start as start_process
    from reco.storage import process_lock

    try:
        with process_lock(root / ".models.lock"):
            result = start_process(root, port)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(result, indent=2))


@app.command()
def stop(root: Path = Path("artifacts/models")) -> None:
    """Stop only the locally owned service process, preserving its active pointer."""
    from reco.lifecycle import stop as stop_process
    from reco.storage import process_lock

    try:
        with process_lock(root / ".models.lock"):
            stop_process(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@app.command()
def activate(
    model_id: str = typer.Option(..., "--model-id"), root: Path = Path("artifacts/models")
) -> None:
    """Verify candidate, restart/probe and automatically restore on startup failure."""
    _activate(model_id, root, False)


@app.command()
def rollback(
    model_id: str = typer.Option(..., "--model-id"), root: Path = Path("artifacts/models")
) -> None:
    """Restore a previously activated bundle through the same restart/readiness checks."""
    _activate(model_id, root, True)


def _activate(model_id: str, root: Path, rollback: bool) -> None:
    from reco.lifecycle import activate as activate_process

    try:
        result = activate_process(root, model_id, rollback)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(result, indent=2))


@app.command()
def showcase(
    root: Path = Path("artifacts/models"),
    report: Path = Path("artifacts/benchmark/final"),
    output: Path = Path("artifacts/showcase"),
    lock: Path = Path("uv.lock"),
    port: int = 8765,
    requests: int = 5000,
    rate: float = 20,
    warmup: int = 200,
    container_evidence: Path | None = None,
) -> None:
    """Run actual HTTP/restart/fault/load checks in isolated processes and emit evidence."""
    from reco.showcase import run_showcase

    try:
        result = run_showcase(
            root, report, output, lock, port, requests, rate, warmup, container_evidence
        )
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        atomic_json(
            output / "failure.json",
            {"stage": "showcase", "error": str(exc), "error_type": type(exc).__name__},
        )
        typer.echo(f"Showcase failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"{result['release_status']}; engineering acceptance: "
        f"{result['engineering_acceptance_passed']}. Evidence: {output}"
    )
    if not result["engineering_acceptance_passed"]:
        raise typer.Exit(1)


@app.command()
def recover(root: Path = Path("artifacts/models"), port: int = 8000) -> None:
    """Restore last-known-good after an interrupted activation, then verify readiness."""
    from reco.lifecycle import recover as recover_process

    try:
        result = recover_process(root, port)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(result, indent=2))


@app.command()
def verify_showcase(directory: Path, aggregate: bool = False, root: Path | None = None) -> None:
    """Verify showcase checksums/accounting and optionally bind evidence to the active model."""
    from reco.benchmark import execution_identity
    from reco.lifecycle import active_bundle
    from reco.showcase import verify_showcase as verify
    from reco.storage import sha256_file

    try:
        result = verify(directory, raw=not aggregate)
        if root is not None:
            bundle = active_bundle(root)
            if (
                result["model_id"] != bundle.manifest.model_id
                or result["bundle_manifest_sha256"]
                != sha256_file(root / bundle.manifest.model_id / "manifest.json")
                or result["execution_identity"] != execution_identity(Path("uv.lock"))
            ):
                raise ValueError("Showcase differs from active bundle/current code")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(f"Unusable showcase: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Verified {result['model_id']}; {result['release_status']}")


@app.command()
def export_showcase(source: Path, destination: Path) -> None:
    """Export verified aggregate showcase evidence without histories/raw profile traffic."""
    from reco.showcase import export_showcase as export

    try:
        export(source, destination)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(f"Unusable showcase export: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(str(destination))
