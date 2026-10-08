"""Summarize retained scan evidence for the locally verified image."""

import json
import re
from pathlib import Path

from reco.storage import atomic_json, sha256_file


def summarize() -> None:
    container_path = Path("artifacts/container/verification.json")
    container = json.loads(container_path.read_text())
    scan_path = Path("artifacts/security/image-final.sarif.json")
    results = json.loads(scan_path.read_text())["runs"][0].get("results", [])
    findings = []
    for result in results:
        message = result["message"]["text"]

        def field(name: str, message: str = message) -> str | None:
            match = re.search(r"^" + name + r"\s*:(.*)$", message, re.MULTILINE)
            return match.group(1).strip() if match else None

        findings.append(
            {
                "id": result["ruleId"],
                "severity": field("Severity"),
                "package": field("Package"),
                "fixed_version": field("Fixed version"),
            }
        )
    dependency_path = Path("artifacts/security/dependencies-patched.json")
    security = {
        "scan_date": "2026-10-07",
        "image_id": container["image_id"],
        "docker_scout_version": "1.24.0",
        "scanned_severities": ["critical", "high"],
        "high_critical_findings": len(findings),
        "fixable_high_critical_findings": sum(
            row["fixed_version"] != "not fixed" for row in findings
        ),
        "findings": findings,
        "image_scan_sha256": sha256_file(scan_path),
        "dependency_audit": json.loads(dependency_path.read_text())["summary"],
        "dependency_audit_sha256": sha256_file(dependency_path),
        "status": "experimental_unfixed_base_image_findings" if findings else "scan_clear",
    }
    atomic_json(Path("artifacts/security/summary.json"), security)
    container["security_scan"] = security
    atomic_json(container_path, container)


if __name__ == "__main__":
    summarize()
