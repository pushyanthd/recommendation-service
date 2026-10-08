"""CLI-owned loopback process management, atomic selection and verified restoration."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from reco.bundles import MODEL_ID, Bundle, load_bundle
from reco.storage import atomic_json, process_lock, sha256_file


def pointer_for(directory: Path) -> dict[str, str]:
    bundle = load_bundle(directory)
    if directory.name != bundle.manifest.model_id:
        raise ValueError("Bundle directory/model identity mismatch")
    if bundle.manifest.selection.get("activation_allowed") is False:
        raise ValueError("Candidate operation gate rejected activation")
    selected = bundle.manifest.selection.get("selected_for_final_refit")
    if bundle.manifest.variant != selected:
        raise ValueError("Candidate differs from the frozen selection")
    if bundle.manifest.variant != "popularity":
        gates = bundle.manifest.selection.get("quality_gates", [])
        if not any(
            gate.get("variant") == selected and gate.get("passed") is True for gate in gates
        ):
            raise ValueError("Candidate validation gate rejected personalization")
    return {
        "model_id": bundle.manifest.model_id,
        "manifest_sha256": sha256_file(directory / "manifest.json"),
    }


def read_pointer(root: Path, name: str = "active.json") -> dict[str, str]:
    value: dict[str, str] = json.loads((root / name).read_text())
    if set(value) != {"model_id", "manifest_sha256"} or not MODEL_ID.fullmatch(value["model_id"]):
        raise ValueError("Invalid model pointer")
    return value


def active_bundle(root: Path) -> Bundle:
    pointer = read_pointer(root)
    directory = root / pointer["model_id"]
    if (
        directory.is_symlink()
        or sha256_file(directory / "manifest.json") != pointer["manifest_sha256"]
    ):
        raise ValueError("Active pointer manifest mismatch")
    return load_bundle(directory)


def select_initial(root: Path, model_id: str) -> None:
    """Initial offline selection only; subsequent switches require verified activation."""
    if not MODEL_ID.fullmatch(model_id):
        raise ValueError("Invalid model ID")
    with process_lock(root / ".models.lock"):
        if (root / "active.json").exists():
            raise ValueError("Active pointer exists; use activate/rollback")
        atomic_json(root / "active.json", pointer_for(root / model_id))


def probe(port: int, model_id: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=1) as response:
        result: dict[str, Any] = json.load(response)
    if result.get("status") != "ready" or result.get("model_id") != model_id:
        raise ValueError("Readiness model identity mismatch")
    return result


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _command(pid: int) -> str:
    # Linux ps truncates piped output unless unlimited width is requested. The
    # ownership token is the last argument and must survive long checkout paths.
    result = subprocess.run(
        ["ps", "-ww", "-p", str(pid), "-o", "args="], capture_output=True, text=True
    )
    return result.stdout.strip()


def stop(root: Path) -> None:
    state_path = root / "process.json"
    if not state_path.exists():
        return
    state = json.loads(state_path.read_text())
    pid = state["pid"]
    if type(pid) is not int or pid <= 1:
        raise ValueError("Invalid owned process PID")
    if _alive(pid):
        command = _command(pid)
        if "reco.runtime" not in command or state["token"] not in command:
            raise ValueError("Recorded PID no longer belongs to this service")
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 8
        while _alive(pid) and time.monotonic() < deadline:
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
            time.sleep(0.05)
        if _alive(pid):
            raise ValueError("Service did not stop; refusing concurrent startup")
    state_path.unlink(missing_ok=True)


def start(root: Path, port: int = 8000) -> dict[str, Any]:
    from uuid import uuid4

    bundle = active_bundle(root)
    if (root / "process.json").exists():
        raise ValueError("Recorded service already exists; stop it before starting")
    if not 1024 <= port <= 65535:
        raise ValueError("Port must be between 1024 and 65535")
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
    token = uuid4().hex
    command = [
        sys.executable,
        "-m",
        "reco.runtime",
        "--root",
        str(root.resolve()),
        "--port",
        str(port),
        "--token",
        token,
    ]
    with (root / "service.log").open("ab") as log:
        child = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
    state = {"pid": child.pid, "port": port, "token": token, "model_id": bundle.manifest.model_id}
    atomic_json(root / "process.json", state)
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise ValueError("Service exited during startup; see service.log")
            try:
                probe(port, bundle.manifest.model_id)
                return state
            except (OSError, urllib.error.URLError, ValueError):
                time.sleep(0.1)
        raise ValueError("Service readiness timed out")
    except BaseException:
        stop(root)
        raise


def activate(root: Path, model_id: str, rollback: bool = False) -> dict[str, Any]:
    if not MODEL_ID.fullmatch(model_id):
        raise ValueError("Invalid model ID")
    with process_lock(root / ".models.lock"):
        previous = read_pointer(root)
        active_bundle(root)
        candidate = pointer_for(root / model_id)
        if rollback:
            verified = json.loads((root / "verified.json").read_text())
            if verified.get(model_id) != candidate["manifest_sha256"]:
                raise ValueError("Rollback requires a previously verified activation")
        state = json.loads((root / "process.json").read_text())
        probe(state["port"], previous["model_id"])
        atomic_json(root / "last-known-good.json", previous)
        stop(root)
        atomic_json(root / "active.json", candidate)
        try:
            current = start(root, state["port"])
        except (OSError, ValueError) as exc:
            atomic_json(root / "active.json", previous)
            restored = start(root, state["port"])
            failure = {
                "status": "activation_failed_restored",
                "requested_model_id": model_id,
                "restored_model_id": previous["model_id"],
                "pid": restored["pid"],
                "error": str(exc),
            }
            atomic_json(root / "last-activation.json", failure)
            raise ValueError(f"Activation failed; restored {previous['model_id']}: {exc}") from exc
        verified_path = root / "verified.json"
        verified = json.loads(verified_path.read_text()) if verified_path.exists() else {}
        verified[previous["model_id"]] = previous["manifest_sha256"]
        verified[model_id] = candidate["manifest_sha256"]
        atomic_json(verified_path, verified)
        result = {
            "status": "rolled_back" if rollback else "activated",
            "previous_model_id": previous["model_id"],
            "model_id": model_id,
            "pid": current["pid"],
            "port": current["port"],
        }
        atomic_json(root / "last-activation.json", result)
        return result


def recover(root: Path, port: int = 8000) -> dict[str, Any]:
    """Restore a verified last-known-good pointer after an interrupted local activation."""
    with process_lock(root / ".models.lock"):
        previous = read_pointer(root, "last-known-good.json")
        directory = root / previous["model_id"]
        if pointer_for(directory) != previous:
            raise ValueError("Last-known-good bundle changed; recovery rejected")
        stop(root)
        atomic_json(root / "active.json", previous)
        current = start(root, port)
        result = {
            "status": "recovered",
            "model_id": previous["model_id"],
            "pid": current["pid"],
            "port": port,
        }
        atomic_json(root / "last-activation.json", result)
        return result
