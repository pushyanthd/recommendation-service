"""The release gate must reject missing scans and vulnerabilities without fixes."""

import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "image_audit", Path(__file__).resolve().parents[1] / "benchmarks/image_audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.fixture
def report():
    return {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "Metadata": {"ImageID": "sha256:test", "OS": {"Family": "debian", "Name": "13.7"}},
        "Results": [
            {
                "Class": "os-pkgs",
                "Type": "debian",
                "Target": "debian",
                "Packages": [{"Name": n} for n in ("libc6", "libgomp1", "libstdc++6", "zlib1g")],
            },
            {
                "Class": "lang-pkgs",
                "Type": "python-pkg",
                "Target": "python",
                "Packages": [
                    {"Name": n} for n in ("numpy", "scipy", "implicit", "fastapi", "uvicorn")
                ],
            },
        ],
    }


def test_complete_scan_passes(report):
    assert audit.summarize(report, "sha256:test")["passed"]


@pytest.mark.parametrize("severity", ["HIGH", "CRITICAL", "MEDIUM", "UNKNOWN"])
def test_findings_without_fixes_are_preserved_and_high_findings_block(report, severity):
    report["Results"][0]["Vulnerabilities"] = [
        {
            "VulnerabilityID": "CVE-test",
            "PkgName": "libc6",
            "InstalledVersion": "1",
            "Severity": severity,
        }
    ]
    result = audit.summarize(report, "sha256:test")
    assert result["passed"] == (severity not in {"HIGH", "CRITICAL"})
    assert result["findings"][0]["fixed_version"] is None
    assert result["severity_counts"][severity] == 1


def test_wrong_image_rejected(report):
    with pytest.raises(ValueError, match="different image"):
        audit.summarize(report, "sha256:other")


@pytest.mark.parametrize("missing", ["Results", "Metadata", "SchemaVersion"])
def test_missing_scan_fields_rejected(report, missing):
    del report[missing]
    with pytest.raises(ValueError):
        audit.summarize(report, "sha256:test")


@pytest.mark.parametrize("index", [0, 1])
def test_missing_package_inventory_rejected(report, index):
    report["Results"][index]["Packages"] = []
    with pytest.raises(ValueError, match="inventory"):
        audit.summarize(report, "sha256:test")


def test_suppression_rejected(report):
    report["Results"][0]["ModifiedFindings"] = [{"Status": "ignored"}]
    with pytest.raises(ValueError, match="Suppressed"):
        audit.summarize(report, "sha256:test")


def test_ambiguous_os_and_end_of_life_rejected(report):
    other = copy.deepcopy(report)
    other["Metadata"]["OS"]["Family"] = "unknown"
    with pytest.raises(ValueError):
        audit.summarize(other, "sha256:test")
    report["Metadata"]["OS"]["EOSL"] = True
    with pytest.raises(ValueError, match="End-of-life"):
        audit.summarize(report, "sha256:test")
