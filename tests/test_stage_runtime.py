"""CPU staging excludes optional CUDA binaries while preserving inference code."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "stage_runtime", Path(__file__).resolve().parents[1] / "benchmarks/stage_runtime.py"
)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@pytest.mark.parametrize("cuda_name", ["_cuda.so", "_cuda.cpython-312-x86_64-linux-gnu.so", None])
def test_cpu_staging_preserves_cpu_extensions_and_gpu_import_fallback(tmp_path, cuda_name):
    dynload = tmp_path / "usr/local/lib/python3.12/lib-dynload"
    packages = tmp_path / "opt/venv/lib/python3.12/site-packages"
    dynload.mkdir(parents=True)
    (packages / "implicit/gpu").mkdir(parents=True)
    (packages / "implicit/cpu").mkdir()
    retained = [
        dynload / "_ssl.so",
        packages / "implicit/cpu/_als.so",
        packages / "implicit/gpu/__init__.py",
        packages / "implicit/gpu/als.py",
    ]
    excluded = [dynload / "_curses.so"]
    if cuda_name:
        excluded.append(packages / "implicit/gpu" / cuda_name)
    for path in retained + excluded:
        path.write_bytes(b"\x7fELFfixture")

    removed = runtime.exclude_optional_extensions(tmp_path)

    assert removed == sorted(str(path.relative_to(tmp_path)) for path in excluded)
    assert all(not path.exists() for path in excluded)
    assert all(path.read_bytes() == b"\x7fELFfixture" for path in retained)
