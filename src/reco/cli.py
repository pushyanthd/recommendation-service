import json
import platform
import time
from pathlib import Path

import typer

from reco.contracts import Variant
from reco.data import chronological_split, load_fixture
from reco.evaluation import evaluate
from reco.ranking import Ranker

app = typer.Typer(no_args_is_help=True)


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
