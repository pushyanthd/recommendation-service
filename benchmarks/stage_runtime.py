"""Stage a bounded Python runtime and retain Debian provenance for every copied library."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

OPTIONAL_EXTENSIONS = ("_curses", "_uuid", "readline", "_tkinter")


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def exclude_optional_extensions(destination):
    removed = []
    for path in (destination / "usr/local/lib/python3.12/lib-dynload").iterdir():
        if path.name.startswith(OPTIONAL_EXTENSIONS):
            removed.append(str(path.relative_to(destination)))
            path.unlink()
    # The amd64 implicit wheel ships an optional CUDA binary. Keep its Python
    # fallback and all CPU extensions, but exclude GPU code before resolving ELF
    # dependencies so the CPU image never needs CUDA/RMM runtime libraries.
    gpu = destination / "opt/venv/lib/python3.12/site-packages/implicit/gpu"
    for path in gpu.glob("_cuda*.so"):
        removed.append(str(path.relative_to(destination)))
        path.unlink()
    return sorted(removed)


def stage(destination, base):
    if destination.exists():
        raise ValueError("Runtime staging directory must be new")
    destination.mkdir()

    def copy(path):
        target = destination / path.relative_to("/")
        if target.exists() or target.is_symlink():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            target.symlink_to(path.readlink())
            copy(path.resolve(strict=True))
        else:
            shutil.copy2(path, target)

    shutil.copytree("/usr/local", destination / "usr/local", symlinks=True)
    shutil.copytree("/opt/venv", destination / "opt/venv", symlinks=True)
    shutil.copytree("/opt/models", destination / "opt/models", symlinks=True)
    # Preserve Debian's merged-/usr loader paths, including parent symlinks.
    (destination / "usr/lib").mkdir(exist_ok=True)
    (destination / "lib").symlink_to("usr/lib")
    if Path("/lib64").exists():
        (destination / "usr/lib64").mkdir(exist_ok=True)
        (destination / "lib64").symlink_to("usr/lib64")
    # The API never installs packages, compiles extensions, or opens a terminal.
    for directory in ("usr/local/include", "usr/local/share", "usr/local/lib/pkgconfig"):
        target = destination / directory
        if target.exists():
            shutil.rmtree(target)
    global_packages = destination / "usr/local/lib/python3.12/site-packages"
    shutil.rmtree(global_packages)
    global_packages.mkdir()
    for path in (destination / "usr/local/bin").iterdir():
        if path.name not in ("python", "python3", "python3.12"):
            path.unlink()
    removed = exclude_optional_extensions(destination)
    # uuid.uuid4 uses os.urandom; Python supplies a fallback without optional _uuid.
    binaries = [Path("/usr/local/bin/python3.12")]
    for tree in (destination / "usr/local/lib", destination / "opt/venv"):
        for path in tree.rglob("*"):
            if path.is_file() and (path.suffix == ".so" or ".so." in path.name):
                with path.open("rb") as stream:
                    if stream.read(4) == b"\x7fELF":
                        binaries.append(Path("/") / path.relative_to(destination))
    dependencies = set()
    for binary in sorted(set(binaries)):
        result = subprocess.run(["ldd", str(binary)], capture_output=True, text=True, check=True)
        if "not found" in result.stdout:
            raise ValueError(f"Unresolved library for {binary}: {result.stdout}")
        for line in result.stdout.splitlines():
            match = re.match(r"\s*(?:\S+\s*=>\s*)?(/\S+)", line)
            if match:
                dependencies.add(Path(match.group(1)))
    owners = {"base-files", "ca-certificates", "tzdata"}
    # Name-service modules may be loaded dynamically rather than through ELF NEEDED.
    dependencies.update(Path("/usr/lib").glob("*/libnss_*.so*"))
    external_libraries = []
    for path in sorted(dependencies):
        if path.is_relative_to("/usr/local") or path.is_relative_to("/opt/venv"):
            continue
        copy(path)
        result = subprocess.run(
            ["dpkg-query", "-S", str(path.resolve())], capture_output=True, text=True
        )
        if result.returncode:
            result = subprocess.run(
                ["dpkg-query", "-S", str(path)], capture_output=True, text=True, check=True
            )
        owner = result.stdout.split(": ", 1)[0].split(":", 1)[0]
        owners.add(owner)
        external_libraries.append(
            {"path": str(path), "sha256": sha256(path), "debian_package": owner}
        )
    for name in ("os-release", "debian_version", "nsswitch.conf", "gai.conf"):
        path = Path("/etc") / name
        if path.exists():
            copy(path)
    shutil.copytree("/etc/ssl/certs", destination / "etc/ssl/certs", symlinks=True)
    # Certificate symlinks may point at Debian's CA bundle source files.
    shutil.copytree("/usr/share/ca-certificates", destination / "usr/share/ca-certificates")
    shutil.copytree("/usr/share/zoneinfo", destination / "usr/share/zoneinfo", symlinks=True)
    for name in ("localtime", "timezone"):
        path = Path("/etc") / name
        if path.exists():
            copy(path)
    copy(Path("/app/uv.lock"))
    (destination / "etc/passwd").write_text(
        "root:x:0:0:root:/root:/sbin/nologin\nreco:x:10001:10001:reco:/nonexistent:/sbin/nologin\n"
    )
    (destination / "etc/group").write_text("root:x:0:\nreco:x:10001:\n")
    (destination / "tmp").mkdir(mode=0o1777)
    (destination / "tmp").chmod(0o1777)
    status = []
    packages = []
    for owner in sorted(owners):
        control = subprocess.check_output(["dpkg-query", "-s", owner], text=True).strip()
        if "Status: install ok installed" not in control:
            raise ValueError(f"Invalid package provenance: {owner}")
        status.append(control)
        package = re.search(r"^Package: (.+)$", control, re.MULTILINE).group(1)
        version = re.search(r"^Version: (.+)$", control, re.MULTILINE).group(1)
        packages.append({"name": package, "version": version})
        copyright_path = Path("/usr/share/doc") / package / "copyright"
        if copyright_path.exists():
            copy(copyright_path)
    package_db = destination / "var/lib/dpkg/status"
    package_db.parent.mkdir(parents=True)
    package_db.write_text("\n\n".join(status) + "\n")
    inventory = destination / "usr/share/reco-runtime/inventory.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_base": base,
                "staging_helper_sha256": sha256(Path(__file__)),
                "debian_packages": packages,
                "external_libraries": external_libraries,
                "optional_extensions_excluded": sorted(removed),
                "package_managers_and_shells_included": False,
                "scope": "Runtime for the recommendation API and CPU inference; no runtime setup",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--base", required=True)
    arguments = parser.parse_args()
    stage(arguments.destination, arguments.base)
