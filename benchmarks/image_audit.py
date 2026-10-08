"""Scan an exported image with pinned Trivy, retain its SBOM, and fail closed."""

import argparse
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from reco.storage import atomic_json, sha256_file

TRIVY_IMAGE = (
    "aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969"
)
SEVERITIES = {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


def summarize(report, image_id):
    if report.get("SchemaVersion") != 2 or report.get("ArtifactType") != "container_image":
        raise ValueError("Unsupported image scan schema")
    metadata = report.get("Metadata", {})
    if metadata.get("ImageID") != image_id:
        raise ValueError("Scan is for a different image")
    operating_system = metadata.get("OS", {})
    if operating_system.get("Family") != "debian" or not str(
        operating_system.get("Name", "")
    ).startswith("13."):
        raise ValueError("Expected Debian 13 runtime inventory")
    if operating_system.get("EOSL"):
        raise ValueError("End-of-life runtime is not releasable")
    results = report.get("Results", [])
    os_results = [r for r in results if r.get("Class") == "os-pkgs" and r.get("Type") == "debian"]
    python_results = [
        r for r in results if r.get("Class") == "lang-pkgs" and r.get("Type") == "python-pkg"
    ]
    if len(os_results) != 1 or len(python_results) != 1:
        raise ValueError("Incomplete OS/Python scan")
    packages = {
        "debian": {p["Name"] for p in os_results[0].get("Packages", [])},
        "python": {p["Name"] for p in python_results[0].get("Packages", [])},
    }
    if not {"libc6", "libgomp1", "libstdc++6", "zlib1g"} <= packages["debian"]:
        raise ValueError("Missing native runtime package inventory")
    if not {"numpy", "scipy", "implicit", "fastapi", "uvicorn"} <= packages["python"]:
        raise ValueError("Missing Python runtime package inventory")
    findings = []
    for result in results:
        if result.get("ModifiedFindings"):
            raise ValueError("Suppressed or modified findings are not accepted")
        for finding in result.get("Vulnerabilities", []):
            if finding.get("Severity") not in SEVERITIES or not all(
                finding.get(field) for field in ("VulnerabilityID", "PkgName", "InstalledVersion")
            ):
                raise ValueError("Incomplete vulnerability finding")
            findings.append(
                {
                    "id": finding["VulnerabilityID"],
                    "package": finding["PkgName"],
                    "installed_version": finding["InstalledVersion"],
                    "severity": finding["Severity"],
                    "fixed_version": finding.get("FixedVersion"),
                    "scanner_target": result["Target"],
                }
            )
    counts = Counter(f["severity"] for f in findings)
    blocking = [f for f in findings if f["severity"] in {"HIGH", "CRITICAL"}]
    return {
        "schema_version": 1,
        "passed": not blocking,
        "image_id": image_id,
        "scanner": {"image": TRIVY_IMAGE, "version": report.get("Trivy", {}).get("Version")},
        "scan_created_at": report.get("CreatedAt"),
        "operating_system": operating_system,
        "package_counts": {kind: len(names) for kind, names in packages.items()},
        "severity_counts": {severity: counts[severity] for severity in sorted(SEVERITIES)},
        "high_critical_findings": len(blocking),
        "findings": findings,
        "policy": "Fail on every Trivy HIGH/CRITICAL; no ignore file or severity filtering",
        "scope": "Trivy snapshot only; independent Scout/advisory evidence must also be reviewed",
    }


def docker(*arguments):
    return subprocess.check_output(["docker", *map(str, arguments)], text=True).strip()


def audit(image, output, cache, verification):
    output = output.resolve()
    cache = cache.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    info = json.loads(docker("image", "inspect", image))[0]
    verified = json.loads(verification.read_text())
    if not verified.get("passed") or verified.get("image_id") != info["Id"]:
        raise ValueError("Verify this exact image before scanning")
    if verified["dockerfile_sha256"] != sha256_file(Path("Dockerfile")):
        raise ValueError("Container evidence predates the Dockerfile")
    with tempfile.TemporaryDirectory(prefix="reco-image-") as temporary:
        source = Path(temporary).resolve()
        docker("save", "--output", source / "image.tar", info["Id"])
        scanner = [
            "run",
            "--rm",
            # Bind mounts retain the runner's Linux ownership. Root with every
            # capability dropped cannot write another user's 0755 directories
            # or read the user's 0700 temporary input directory.
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=512m",
            "--mount",
            f"type=bind,source={source},target=/input,readonly",
            "--mount",
            f"type=bind,source={output},target=/output",
            "--mount",
            f"type=bind,source={cache},target=/cache",
            TRIVY_IMAGE,
        ]
        docker(
            *scanner,
            "image",
            "--input",
            "/input/image.tar",
            "--cache-dir",
            "/cache",
            "--disable-telemetry",
            "--skip-version-check",
            "--scanners",
            "vuln",
            "--ignorefile",
            "/dev/null",
            "--list-all-pkgs",
            "--format",
            "json",
            "--output",
            "/output/trivy.json",
        )
        docker(
            *scanner,
            "convert",
            "--ignorefile",
            "/dev/null",
            "--format",
            "cyclonedx",
            "--output",
            "/output/sbom.cdx.json",
            "/output/trivy.json",
        )
    summary = summarize(json.loads((output / "trivy.json").read_text()), info["Id"])
    sbom = json.loads((output / "sbom.cdx.json").read_text())
    if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("components"):
        raise ValueError("Empty or unsupported SBOM")
    summary["architecture"] = info["Architecture"]
    summary["evidence"] = {
        path.name: sha256_file(path)
        for path in (output / "trivy.json", output / "sbom.cdx.json", verification)
    }
    summary["runtime_inventory"] = verified["checks"]["runtime_inventory"]
    database = cache / "db/metadata.json"
    summary["vulnerability_database"] = json.loads(database.read_text())
    atomic_json(output / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    if not summary["passed"]:
        raise SystemExit("Image security gate failed; retain and review the raw scan")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="cpu-reco:local")
    parser.add_argument("--output", type=Path, default=Path("artifacts/image-audit"))
    parser.add_argument("--cache", type=Path, default=Path("artifacts/trivy-cache"))
    parser.add_argument(
        "--verification", type=Path, default=Path("artifacts/container/verification.json")
    )
    args = parser.parse_args()
    audit(args.image, args.output, args.cache, args.verification)
