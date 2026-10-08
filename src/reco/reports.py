"""Escaped standalone comparison reports backed by checksummed JSON evidence."""

import html
import json
from pathlib import Path
from typing import Any

from reco.storage import atomic_json, sha256_file


def write_reports(directory: Path, report: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    atomic_json(directory / "report.json", report)
    rows = []
    for variant in report["variants"]:
        metrics = variant["metrics"]
        rows.append(
            [
                variant["variant"],
                str(variant["eligible_users"]),
                f"{metrics['ndcg_at_10']:.6f}",
                f"{metrics['recall_at_10']:.6f}",
                f"{metrics['recall_at_20']:.6f}",
                f"{metrics['hit_rate_at_10']:.6f}",
                f"{variant['coverage_at_10']:.4f}",
                f"{variant['fallback_rate']:.4f}",
                f"{variant['scoring_latency_ms']['p95']:.3f}",
                str(variant["failed_users"]),
            ]
        )
    headers = [
        "Variant",
        "Users",
        "NDCG@10",
        "Recall@10",
        "Recall@20",
        "HitRate@10",
        "Coverage@10",
        "Fallback",
        "Scoring P95 ms",
        "Failures",
    ]
    details = {key: value for key, value in report.items() if key != "variants"}
    details["variant_diagnostics"] = [
        {key: value for key, value in variant.items() if key != "users"}
        for variant in report["variants"]
    ]
    serialized = json.dumps(details, indent=2, allow_nan=False)
    prefix = (
        f"# CPU recommendation comparison — {report['data_mode']}\n\n"
        f"Phase: **{report['phase']}**. Status: **{report['release_status']}**.\n\n"
        "Full prediction-time catalog; all unseen future positives remain in denominators. "
        "Scoring timings are in-process measurements, not HTTP load results. "
        "Offline ratings do not establish engagement or revenue effects.\n\n"
    )
    table = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n"
    table += "".join("| " + " | ".join(row) + " |\n" for row in rows)
    (directory / "report.md").write_text(prefix + table + "\n```json\n" + serialized + "\n```\n")
    html_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>CPU recommendation comparison</title><style>"
        "body{font:16px system-ui;margin:40px auto;max-width:1200px;padding:0 20px;color:#182638}"
        "table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #ccd4dd}"
        "pre{white-space:pre-wrap;background:#eef2f6;padding:20px}a{color:#1454a3}"
        "</style><h1>CPU recommendation comparison</h1>"
        f"<p>{html.escape(report['data_mode'])} · {html.escape(report['phase'])} · "
        f"{html.escape(report['release_status'])}</p>"
        "<p>Full-catalog ranking with chronological history. Unreachable targets count as misses. "
        "Scoring latency excludes HTTP. Offline ratings establish no engagement "
        "or revenue uplift.</p>"
        "<table><thead><tr>"
        + "".join(f"<th>{cell}</th>" for cell in headers)
        + "</tr></thead><tbody>"
        + html_rows
        + "</tbody></table><h2>Decision, cohorts and provenance</h2><pre>"
        + html.escape(serialized)
        + "</pre></html>"
    )
    (directory / "report.html").write_text(document)
    atomic_json(
        directory / "checksums.json",
        {
            name: sha256_file(directory / name)
            for name in ("report.json", "report.md", "report.html")
        },
    )
