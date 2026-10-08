"""Check release archives and exercise an installed wheel outside the source checkout."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*arguments, cwd, env):
    result = subprocess.run(arguments, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        print(result.stderr)
        result.check_returncode()
    return result.stdout


def verify_http(python, isolated, environment):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with (isolated / "server.log").open("w+") as log:
        server = subprocess.Popen(
            [
                python,
                "-I",
                "-c",
                "import sys, uvicorn; from reco.api import create_app; "
                "uvicorn.run(create_app(), host='127.0.0.1', port=int(sys.argv[1]), "
                "access_log=False)",
                str(port),
            ],
            cwd=isolated,
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            url = f"http://127.0.0.1:{port}"

            def get(path):
                with urllib.request.urlopen(url + path, timeout=2) as response:
                    return response.read()

            deadline = time.monotonic() + 30
            while True:
                try:
                    assert json.loads(get("/readyz"))["status"] == "ready"
                    break
                except (OSError, urllib.error.URLError):
                    if server.poll() is not None or time.monotonic() >= deadline:
                        log.seek(0)
                        raise RuntimeError("Installed API failed startup: " + log.read()) from None
                    time.sleep(0.1)
            assert b"Find your next movie" in get("/")
            assert json.loads(get("/v1/model"))["data_mode"] == "fictional_fixture"
            for payload in ({"user_id": 1, "k": 20}, {"liked_movie_ids": [1], "k": 3}):
                request = urllib.request.Request(
                    url + "/v1/recommendations",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    result = json.load(response)
                excluded = {1, 2, 3, 4, 5} if "user_id" in payload else {1}
                assert not excluded & {row["movie_id"] for row in result["items"]}
                assert result["data_mode"] == "fictional_fixture"
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def verify(directory, allow_downloads=False):
    repository = Path.cwd()
    project = tomllib.loads((repository / "pyproject.toml").read_text())["project"]
    version = project["version"]
    assert (repository / "src/reco/runtime.lock").read_bytes() == (
        repository / "uv.lock"
    ).read_bytes(), "Refresh the packaged runtime.lock after changing uv.lock"
    stem = project["name"].replace("-", "_") + "-" + version
    wheel = (directory / (stem + "-py3-none-any.whl")).resolve()
    sdist = (directory / (stem + ".tar.gz")).resolve()
    expected = {
        str(path.relative_to(repository / "src")): digest(path)
        for path in sorted((repository / "src/reco").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    with zipfile.ZipFile(wheel) as archive:
        files = archive.namelist()
        metadata = BytesParser().parsebytes(archive.read(stem + ".dist-info/METADATA"))
        assert metadata["Name"] == project["name"] and metadata["Version"] == version
        actual = {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in files
            if name.startswith("reco/")
        }
        assert actual == expected, "Wheel source differs from the checkout"
        assert all(name.startswith(("reco/", stem + ".dist-info/")) for name in files)
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        assert all(member.isfile() or member.isdir() for member in members)
        names = set()
        for member in members:
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] == stem
            assert not {"artifacts", ".venv", ".uv-cache", ".git"} & set(path.parts)
            names.add(str(Path(*path.parts[1:])))
        assert {
            "pyproject.toml",
            "uv.lock",
            "Makefile",
            "config/benchmark.json",
            "benchmarks/verify_distribution.py",
        } <= names
        assert {"src/" + name for name in expected} <= names
        assert not any(name.endswith(("ratings.dat", "movies.dat", "users.dat")) for name in names)
    uv = str(repository / ".bootstrap/bin/uv")
    environment = {
        **os.environ,
        "UV_CACHE_DIR": str(repository / ".uv-cache"),
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "2",
    }
    with tempfile.TemporaryDirectory(prefix="reco-wheel-") as temporary:
        isolated = Path(temporary).resolve()
        requirements = isolated / "requirements.txt"
        run(
            uv,
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--no-annotate",
            "--output-file",
            str(requirements),
            cwd=repository,
            env=environment,
        )
        run(
            uv,
            "venv",
            "--python",
            str(repository / ".venv/bin/python"),
            str(isolated / "env"),
            cwd=isolated,
            env=environment,
        )
        python = str(isolated / "env/bin/python")
        run(
            uv,
            "pip",
            "install",
            *([] if allow_downloads else ["--offline"]),
            "--require-hashes",
            "--python",
            python,
            "-r",
            str(requirements),
            cwd=isolated,
            env=environment,
        )
        run(
            uv,
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--python",
            python,
            str(wheel),
            cwd=isolated,
            env=environment,
        )
        installed = json.loads(
            run(
                python,
                "-I",
                "-c",
                "import hashlib, importlib.metadata, json, pathlib, reco; "
                "root = pathlib.Path(reco.__file__).parent; "
                "print(json.dumps({'version': "
                "importlib.metadata.version('cpu-recommendation-service'), "
                "'source': {str(p.relative_to(root.parent)): "
                "hashlib.sha256(p.read_bytes()).hexdigest() "
                "for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}, "
                "'installed_path': str(root)}))",
                cwd=isolated,
                env=environment,
            )
        )
        assert installed["version"] == version and installed["source"] == expected
        assert Path(installed["installed_path"]).resolve().is_relative_to(isolated)
        environment["UV_OFFLINE"] = "1"
        reco = str(isolated / "env/bin/reco")
        smoke = isolated / "smoke.json"
        run(reco, "fixture-smoke", "--output", str(smoke), cwd=isolated, env=environment)
        fixture = json.loads(smoke.read_text())
        assert fixture["data_mode"] == "fictional_fixture"
        assert {row["variant"] for row in fixture["variants"]} == {
            "popularity",
            "item_knn",
            "als_cpu",
        }
        assert all(row["failed_users"] == 0 for row in fixture["variants"])
        bundle = run(
            reco,
            "build-bundle",
            "--fixture",
            "--root",
            str(isolated / "models"),
            "--lock",
            str(repository / "uv.lock"),
            cwd=isolated,
            env=environment,
        ).strip()
        run(reco, "verify-bundle", bundle, cwd=isolated, env=environment)
        assert not (isolated / "uv.lock").exists()
        verify_http(python, isolated, environment)
    evidence = {
        "schema_version": 1,
        "passed": True,
        "package": project["name"],
        "version": version,
        "archives": {
            path.name: {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in (wheel, sdist)
        },
        "dependency_lock_sha256": digest(repository / "uv.lock"),
        "installed_source": expected,
        "checks": {
            "wheel_metadata_and_source": True,
            "sdist_contains_reproduction_inputs_without_dataset_rows": True,
            "isolated_noneditable_wheel_install": True,
            "offline_three_variant_fixture": True,
            "installed_cli_bundle_roundtrip": True,
            "installed_http_api_and_browser_without_checkout_or_cwd_lock": True,
        },
        "scope": (
            "Explicit locked dependency setup may download; installed fixture commands run offline"
            if allow_downloads
            else "Locked dependencies installed from an explicitly populated local cache"
        ),
    }
    report = directory / "verification.json"
    report.write_text(json.dumps(evidence, indent=2) + "\n")
    (directory / "SHA256SUMS").write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in (wheel, sdist, report))
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    parser.add_argument("--allow-downloads", action="store_true")
    args = parser.parse_args()
    verify(args.directory, args.allow_downloads)
