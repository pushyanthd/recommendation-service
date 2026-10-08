"""Locally built immutable CPU snapshots. Checksums detect damage, not outside trust."""

import json
import re
import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from pydantic import Field
from scipy.sparse import csr_matrix
from threadpoolctl import threadpool_limits

from reco.contracts import Contract, DataMode, Movie, Rating, Variant
from reco.data import Dataset, chronological_split
from reco.evidence import verify_evidence
from reco.ranking import ALSConfig, Ranker
from reco.selection import select_variant
from reco.storage import atomic_json, json_hash, process_lock, sha256_file

MAX_BUNDLE_BYTES = 1_073_741_824
MODEL_ID = re.compile(r"[a-z0-9_]+-[a-f0-9]{16}-[a-f0-9]{16}")


class ModelManifest(Contract):
    schema_version: Literal[1] = 1
    model_id: str
    ranking_model_id: str
    variant: Variant
    data_mode: DataMode
    data_fingerprint: str
    history_fingerprint: str
    training_cutoff: int = Field(ge=0, strict=True)
    config: dict[str, Any]
    catalog_size: int = Field(gt=0, le=10000, strict=True)
    training_users: int = Field(gt=0, le=100000, strict=True)
    known_user_count: int = Field(gt=0, le=100000, strict=True)
    selection: dict[str, Any]
    release_status: str
    final_report_sha256: str | None
    execution_identity: dict[str, Any]
    files: dict[str, str]


class Bundle:
    def __init__(self, ranker: Ranker, manifest: ModelManifest) -> None:
        self.ranker = ranker
        self.manifest = manifest


def _write_csr(path: Path, matrix: Any) -> None:
    matrix = matrix.tocsr(copy=True)
    matrix.sort_indices()
    np.savez_compressed(
        path,
        data=matrix.data,
        indices=matrix.indices,
        indptr=matrix.indptr,
        shape=np.array(matrix.shape, dtype=np.int64),
    )


def _arrays(path: Path, keys: set[str]) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        if sum(info.file_size for info in archive.infolist()) > MAX_BUNDLE_BYTES:
            raise ValueError("Expanded model arrays exceed byte limit")
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != keys:
            raise ValueError("Unexpected model arrays")
        result = {key: archive[key] for key in keys}
    for array in result.values():
        if array.dtype.kind not in "ifu" or not np.isfinite(array).all():
            raise ValueError("Invalid or nonfinite model array")
    return result


def _read_csr(path: Path, shape: tuple[int, int], binary: bool = False) -> Any:
    arrays = _arrays(path, {"data", "indices", "indptr", "shape"})
    data, indices, indptr = arrays["data"], arrays["indices"], arrays["indptr"]
    if (
        arrays["shape"].shape != (2,)
        or tuple(arrays["shape"]) != shape
        or data.ndim != 1
        or indices.ndim != 1
        or indptr.shape != (shape[0] + 1,)
        or indices.dtype.kind not in "iu"
        or indptr.dtype.kind not in "iu"
        or len(data) != len(indices)
        or indptr[0] != 0
        or indptr[-1] != len(data)
        or np.any(np.diff(indptr) < 0)
        or np.any(indices < 0)
        or np.any(indices >= shape[1])
        or np.any(data <= 0)
        or (binary and np.any(data != 1))
    ):
        raise ValueError("Invalid CSR dimensions, bounds or values")
    matrix = csr_matrix((data, indices, indptr), shape=shape)
    if not matrix.has_canonical_format:
        raise ValueError("CSR indices must be sorted and unique")
    return matrix


def _history_matrix(ranker: Ranker) -> Any:
    rows, columns = [], []
    for uid, row in ranker.users.items():
        for movie_id in sorted(ranker.seen[uid]):
            rows.append(row)
            columns.append(ranker.columns[movie_id])
    return csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, columns)),
        shape=ranker.positive.shape,
    )


def write_bundle(
    root: Path,
    ranker: Ranker,
    cutoff: int,
    selection: dict[str, Any],
    release_status: str,
    execution_identity: dict[str, Any],
    report_digest: str | None = None,
) -> Path:
    """Build/verify before atomic rename. No active pointer is changed here."""
    root.mkdir(parents=True, exist_ok=True)
    with process_lock(root / ".models.lock"):
        temporary = Path(tempfile.mkdtemp(prefix=".build-", dir=root))
        try:
            atomic_json(temporary / "catalog.json", [movie.model_dump() for movie in ranker.movies])
            atomic_json(
                temporary / "users.json",
                {
                    "training": sorted(ranker.users),
                    "known": sorted(ranker.known_users),
                },
            )
            _write_csr(temporary / "positive.npz", ranker.positive)
            _write_csr(temporary / "seen.npz", _history_matrix(ranker))
            np.savez_compressed(temporary / "popularity.npz", scores=ranker.popularity)
            if ranker.variant == "item_knn":
                _write_csr(temporary / "neighbors.npz", ranker.neighbors)
            elif ranker.variant == "als_cpu":
                np.savez_compressed(
                    temporary / "factors.npz",
                    users=ranker.als.user_factors,
                    items=ranker.als.item_factors,
                )
            payload = {
                "schema_version": 1,
                "ranking_model_id": ranker.model_id,
                "variant": ranker.variant,
                "data_mode": ranker.data_mode,
                "data_fingerprint": ranker.data_fingerprint,
                "history_fingerprint": ranker.history_fingerprint,
                "training_cutoff": cutoff,
                "config": ranker.config,
                "catalog_size": len(ranker.movies),
                "training_users": len(ranker.users),
                "known_user_count": len(ranker.known_users),
                "selection": selection,
                "release_status": release_status,
                "final_report_sha256": report_digest,
                "execution_identity": execution_identity,
                "files": {path.name: sha256_file(path) for path in sorted(temporary.iterdir())},
            }
            model_id = ranker.model_id + "-" + json_hash(payload)[:16]
            atomic_json(temporary / "manifest.json", {**payload, "model_id": model_id})
            load_bundle(temporary)
            destination = root / model_id
            if destination.exists():
                existing = load_bundle(destination)
                if existing.manifest.model_dump() != {**payload, "model_id": model_id}:
                    raise ValueError("Immutable bundle conflict")
            else:
                temporary.rename(destination)
            return destination
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)


def load_bundle(directory: Path) -> Bundle:
    manifest = ModelManifest.model_validate_json((directory / "manifest.json").read_bytes())
    payload = manifest.model_dump(exclude={"model_id"})
    if manifest.model_id != manifest.ranking_model_id + "-" + json_hash(payload)[:16]:
        raise ValueError("Manifest identity mismatch")
    if not MODEL_ID.fullmatch(manifest.model_id):
        raise ValueError("Invalid model ID")
    expected = {"catalog.json", "users.json", "positive.npz", "seen.npz", "popularity.npz"}
    if manifest.variant == "item_knn":
        expected.add("neighbors.npz")
    elif manifest.variant == "als_cpu":
        expected.add("factors.npz")
    if set(manifest.files) != expected or {p.name for p in directory.iterdir()} != expected | {
        "manifest.json"
    }:
        raise ValueError("Incomplete or unexpected bundle files")
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ValueError("Bundle files must be regular local files")
    if sum(p.stat().st_size for p in directory.iterdir()) > MAX_BUNDLE_BYTES:
        raise ValueError("Bundle exceeds byte limit")
    for name, digest in manifest.files.items():
        if sha256_file(directory / name) != digest:
            raise ValueError(f"Bundle checksum mismatch: {name}")
    ranker = Ranker.__new__(Ranker)
    ranker.movies = tuple(
        Movie.model_validate(row) for row in json.loads((directory / "catalog.json").read_text())
    )
    ids = [movie.movie_id for movie in ranker.movies]
    if len(ids) != manifest.catalog_size or ids != sorted(set(ids)):
        raise ValueError("Invalid catalog mapping")
    user_data = json.loads((directory / "users.json").read_text())
    if set(user_data) != {"training", "known"}:
        raise ValueError("Invalid user mapping")
    for name, count in (
        ("training", manifest.training_users),
        ("known", manifest.known_user_count),
    ):
        values = user_data[name]
        if (
            len(values) != count
            or any(type(uid) is not int or uid <= 0 for uid in values)
            or values != sorted(set(values))
        ):
            raise ValueError("Invalid user mapping")
    if not set(user_data["training"]) <= set(user_data["known"]):
        raise ValueError("Training user absent from known users")
    ranker.users = {uid: row for row, uid in enumerate(user_data["training"])}
    ranker.known_users = set(user_data["known"])
    ranker.columns = {mid: column for column, mid in enumerate(ids)}
    ranker.movie_ids = np.array(ids, dtype=np.int64)
    ranker.genres = {genre for movie in ranker.movies for genre in movie.genres}
    shape = (manifest.training_users, manifest.catalog_size)
    ranker.positive = _read_csr(directory / "positive.npz", shape, binary=True)
    seen = _read_csr(directory / "seen.npz", shape, binary=True)
    if ranker.positive.multiply(seen).nnz != ranker.positive.nnz:
        raise ValueError("Positive history must be contained in seen history")
    ranker.seen = {}
    ranker.liked = {}
    for uid, row in ranker.users.items():
        ranker.seen[uid] = {ids[i] for i in seen.indices[seen.indptr[row] : seen.indptr[row + 1]]}
        ranker.liked[uid] = {
            ids[i]
            for i in ranker.positive.indices[
                ranker.positive.indptr[row] : ranker.positive.indptr[row + 1]
            ]
        }
    popularity = _arrays(directory / "popularity.npz", {"scores"})["scores"]
    if popularity.shape != (manifest.catalog_size,) or not np.array_equal(
        popularity, np.asarray(ranker.positive.sum(axis=0)).ravel()
    ):
        raise ValueError("Popularity does not match positive history")
    ranker.popularity = popularity.astype(np.float32)
    ranker.neighbors = None
    ranker.als = None
    if manifest.variant == "item_knn":
        ranker.neighbors = _read_csr(directory / "neighbors.npz", (shape[1], shape[1]))
        if (
            np.any(np.diff(ranker.neighbors.indptr) > 100)
            or np.any(ranker.neighbors.diagonal() != 0)
            or np.any(ranker.neighbors.data > 1.00001)
        ):
            raise ValueError("Invalid item neighbors")
    elif manifest.variant == "als_cpu":
        from implicit.cpu.als import AlternatingLeastSquares

        factors = _arrays(directory / "factors.npz", {"users", "items"})
        if factors["users"].shape != (shape[0], ALSConfig.factors) or factors["items"].shape != (
            shape[1],
            ALSConfig.factors,
        ):
            raise ValueError("Invalid factor dimensions")
        ranker.als = AlternatingLeastSquares(
            factors=ALSConfig.factors,
            regularization=ALSConfig.regularization,
            num_threads=ALSConfig.threads,
        )
        ranker.als.user_factors = factors["users"].astype(np.float32)
        ranker.als.item_factors = factors["items"].astype(np.float32)
    ranker.variant = manifest.variant
    ranker.data_mode = manifest.data_mode
    ranker.data_fingerprint = manifest.data_fingerprint
    ranker.history_fingerprint = manifest.history_fingerprint
    ranker.config = manifest.config
    # Configuration and algorithm identity are independently reconstructed.
    reference = Ranker.__new__(Ranker)
    tiny = Dataset(
        ranker.movies,
        (Rating(user_id=1, movie_id=ids[0], rating=4, timestamp=0),),
        manifest.data_fingerprint,
        manifest.data_mode,
    )
    Ranker.__init__(reference, tiny, tiny.ratings, "popularity")
    expected_config = dict(
        reference.config,
        variant=manifest.variant,
        neighbors=100 if manifest.variant == "item_knn" else None,
        als={
            "factors": ALSConfig.factors,
            "iterations": ALSConfig.iterations,
            "regularization": ALSConfig.regularization,
            "positive_confidence": ALSConfig.positive_confidence,
            "seed": ALSConfig.seed,
            "threads": ALSConfig.threads,
        }
        if manifest.variant == "als_cpu"
        else None,
    )
    ranking_id = (
        manifest.data_mode
        + "-"
        + json_hash(
            {
                "dataset": manifest.data_fingerprint,
                "history": manifest.history_fingerprint,
                "config": expected_config,
                "implementation": "ranking-v2",
            }
        )[:16]
    )
    if manifest.config != expected_config or manifest.ranking_model_id != ranking_id:
        raise ValueError("Model configuration identity mismatch")
    ranker.model_id = manifest.model_id
    return Bundle(ranker, manifest)


def verify_serving_lock(lock: Path, frozen_digest: str) -> None:
    """Permit pytest security fixes and local release versions; preserve dependency records."""
    if sha256_file(lock) == frozen_digest:
        return
    original = Path("config/frozen") / (frozen_digest + ".uv.lock")
    if sha256_file(original) != frozen_digest:
        raise ValueError("Original frozen dependency lock is unavailable or changed")
    before = tomllib.loads(original.read_text())
    after = tomllib.loads(lock.read_text())
    for value in (before, after):
        packages = value.pop("package")
        cleaned = []
        for package in packages:
            if package["name"] == "pytest":
                continue
            if package["name"] == "cpu-recommendation-service":
                # The local project's release version does not change the frozen
                # numerical treatment. Its source/dependency records still match.
                package.pop("version")
                package["dev-dependencies"]["dev"] = [
                    entry
                    for entry in package["dev-dependencies"]["dev"]
                    if entry["name"] != "pytest"
                ]
                package["metadata"]["requires-dev"]["dev"] = [
                    entry
                    for entry in package["metadata"]["requires-dev"]["dev"]
                    if entry["name"] != "pytest"
                ]
            cleaned.append(package)
        value["package"] = cleaned
    if before != after:
        raise ValueError("Frozen runtime or other dependency lock records changed")


def build_from_report(dataset: Dataset, report_dir: Path, root: Path, lock: Path) -> Path:
    """Refit the frozen selected treatment; never use test metrics to choose a model."""
    from reco.benchmark import execution_identity

    report = verify_evidence(report_dir)
    if report["phase"] != "frozen_final_test" or dataset.fingerprint != report["data_fingerprint"]:
        raise ValueError("A matching complete final report is required")
    development = verify_evidence(report_dir.parent / "development")
    freeze = json.loads((report_dir.parent / "freeze.json").read_text())
    digest = freeze.pop("freeze_sha256", None)
    if (
        digest != json_hash(freeze)
        or freeze["development_report_sha256"]
        != sha256_file(report_dir.parent / "development" / "report.json")
        or freeze["selection"] != select_variant(development["variants"], report["protocol"])
        or freeze["selection"] != report["selection"]
        or freeze["inputs"]["execution_identity"] != report["execution_identity"]
        or any(
            freeze["inputs"][field] != report[field] or development[field] != report[field]
            for field in ("data_mode", "data_fingerprint", "split", "protocol")
        )
    ):
        raise ValueError("Frozen selection evidence mismatch")
    identity = execution_identity(lock)
    old = report["execution_identity"]
    for name in ("ranking.py", "data.py", "contracts.py"):
        if identity["source_files"][name] != old["source_files"][name]:
            raise ValueError(f"Frozen numerical implementation changed: {name}")
    verify_serving_lock(lock, old["dependency_lock_sha256"])
    for name in ("dependencies", "python"):
        if identity[name] != old[name]:
            raise ValueError(f"Frozen dependency identity changed: {name}")
    protocol = report["protocol"]
    split = chronological_split(dataset.ratings, protocol["train_fraction"], protocol["test_start"])
    if split.test_cutoff != report["split"]["test_cutoff"]:
        raise ValueError("Frozen cutoff changed")
    selected = cast(Variant, report["selection"]["selected_for_final_refit"])
    if not report["resource_gate"]:
        selected = "popularity"
    with threadpool_limits(limits=1, user_api="blas"):
        ranker = Ranker(dataset, split.train + split.validation, selected)
    evidence = next(row for row in report["variants"] if row["variant"] == selected)
    if (
        ranker.model_id != evidence["model_id"]
        or ranker.config != evidence["config"]
        or ranker.history_fingerprint != evidence["history_fingerprint"]
        or json_hash([movie.movie_id for movie in ranker.movies]) != evidence["catalog_fingerprint"]
    ):
        raise ValueError("Refit identity differs from frozen evidence")
    return write_bundle(
        root,
        ranker,
        split.test_cutoff,
        report["selection"],
        report["release_status"],
        identity,
        sha256_file(report_dir / "report.json"),
    )
