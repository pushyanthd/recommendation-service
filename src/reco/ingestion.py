"""Explicit, pinned MovieLens 1M setup. Parsing is shared with offline verification."""

import json
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from reco.contracts import Movie, Rating
from reco.data import Dataset, chronological_split
from reco.storage import atomic_json, process_lock, sha256_file

SOURCE_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"
ARCHIVE_SHA256 = "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20"
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_BYTES = 32 * 1024 * 1024
PREPROCESSING_VERSION = "movielens-1m-v1"
EXPECTED_FILES = {"ml-1m/movies.dat", "ml-1m/ratings.dat", "ml-1m/users.dat", "ml-1m/README"}
RETAINED_FILES = ("movies.dat", "ratings.dat", "README")


def extract_archive(archive: Path, destination: Path, expected_sha256: str) -> None:
    """Validate every entry before extracting only ratings, catalog and source terms."""
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds byte limit")
    if sha256_file(archive) != expected_sha256:
        raise ValueError("Archive checksum mismatch")
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entry")
        if set(names) - EXPECTED_FILES - {"ml-1m/"} or not EXPECTED_FILES <= set(names):
            raise ValueError("Unexpected or missing archive entries")
        if sum(entry.file_size for entry in entries) > MAX_EXTRACTED_BYTES:
            raise ValueError("Extracted archive exceeds byte limit")
        for entry in entries:
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("Nonregular archive entry")
        destination.mkdir(parents=True, exist_ok=True)
        for name in RETAINED_FILES:
            entry = zipped.getinfo("ml-1m/" + name)
            if entry.is_dir():
                raise ValueError("Expected file is a directory")
            with zipped.open(entry) as source, (destination / name).open("wb") as target:
                copied = 0
                while chunk := source.read(1024 * 1024):
                    copied += len(chunk)
                    if copied > entry.file_size or copied > MAX_EXTRACTED_BYTES:
                        raise ValueError("Extracted file exceeds declared size")
                    target.write(chunk)
            if copied != entry.file_size:
                raise ValueError("Extracted size mismatch")


def parse_movielens(directory: Path, fingerprint: str) -> Dataset:
    movies = []
    with (directory / "movies.dat").open(encoding="latin-1") as handle:
        for number, line in enumerate(handle, 1):
            try:
                movie_id, title, genres = line.rstrip("\r\n").split("::")
                if not genres or any(not genre for genre in genres.split("|")):
                    raise ValueError("Empty genre")
                movies.append(
                    Movie(movie_id=int(movie_id), title=title, genres=tuple(genres.split("|")))
                )
            except ValueError as exc:
                raise ValueError(f"Invalid movie record at line {number}") from exc
    ratings = []
    with (directory / "ratings.dat").open(encoding="ascii") as handle:
        for number, line in enumerate(handle, 1):
            try:
                user, movie, rating, timestamp = map(int, line.rstrip("\r\n").split("::"))
                ratings.append(
                    Rating(user_id=user, movie_id=movie, rating=rating, timestamp=timestamp)
                )
            except ValueError as exc:
                raise ValueError(f"Invalid rating record at line {number}") from exc
    return Dataset(tuple(movies), tuple(ratings), fingerprint, "movielens_1m")


def dataset_manifest(dataset: Dataset, directory: Path) -> dict[str, Any]:
    split = chronological_split(dataset.ratings)
    return {
        "schema_version": 1,
        "data_mode": dataset.data_mode,
        "source_url": SOURCE_URL,
        "archive_sha256": ARCHIVE_SHA256,
        "preprocessing_version": PREPROCESSING_VERSION,
        "encoding": {"movies.dat": "latin-1", "ratings.dat": "ascii", "README": "ascii"},
        "files": {name: sha256_file(directory / name) for name in RETAINED_FILES},
        "counts": {
            "movies": len(dataset.movies),
            "rated_movies": len({event.movie_id for event in dataset.ratings}),
            "users": len({event.user_id for event in dataset.ratings}),
            "ratings": len(dataset.ratings),
        },
        "timestamp_min": min(event.timestamp for event in dataset.ratings),
        "timestamp_max": max(event.timestamp for event in dataset.ratings),
        "split": {
            "protocol": "global-timestamp-strict-before-v1",
            "fractions": [0.8, 0.9],
            "validation_cutoff": split.validation_cutoff,
            "test_cutoff": split.test_cutoff,
            "train_events": len(split.train),
            "validation_events": len(split.validation),
            "test_events": len(split.test),
        },
        "demographics": "users.dat is not extracted or parsed",
        "terms": "Upstream README retained locally; no dataset redistribution",
    }


def load_movielens(directory: Path) -> Dataset:
    """Fail closed on missing setup, changed source rows, terms, counts or split identity."""
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("archive_sha256") != ARCHIVE_SHA256:
        raise ValueError("Dataset manifest does not match pinned archive")
    expected = manifest.get("files", {})
    if set(expected) != set(RETAINED_FILES):
        raise ValueError("Dataset file manifest is incomplete")
    for name in RETAINED_FILES:
        path = directory / name
        if path.is_symlink() or sha256_file(path) != expected[name]:
            raise ValueError(f"Dataset file checksum mismatch: {name}")
    dataset = parse_movielens(directory, ARCHIVE_SHA256)
    if dataset_manifest(dataset, directory) != manifest:
        raise ValueError("Dataset counts, split or preprocessing manifest mismatch")
    return dataset


def setup_movielens(destination: Path, archive: Path | None = None) -> dict[str, Any]:
    """Explicit setup only. Atomically install a fully validated directory; never replace it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with process_lock(destination.parent / ".data.lock"):
        if destination.exists():
            dataset = load_movielens(destination)
            return dataset_manifest(dataset, destination)
        with tempfile.TemporaryDirectory(prefix=".data-", dir=destination.parent) as temporary:
            staging = Path(temporary)
            if archive is None:
                archive = staging / "ml-1m.zip"
                request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "cpu-reco/0.1"})
                with (
                    urllib.request.urlopen(request, timeout=30) as response,
                    archive.open("wb") as out,
                ):
                    if response.geturl() != SOURCE_URL:
                        raise ValueError("Unexpected dataset redirect")
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_ARCHIVE_BYTES:
                            raise ValueError("Download exceeds byte limit")
                        out.write(chunk)
            extracted = staging / "validated"
            extract_archive(archive, extracted, ARCHIVE_SHA256)
            dataset = parse_movielens(extracted, ARCHIVE_SHA256)
            manifest = dataset_manifest(dataset, extracted)
            if manifest["counts"] != {
                "movies": 3883,
                "rated_movies": 3706,
                "users": 6040,
                "ratings": 1000209,
            }:
                raise ValueError("Parsed counts do not match the fixed MovieLens 1M release")
            atomic_json(extracted / "manifest.json", manifest)
            # Rename on the same filesystem only after all validation succeeds.
            shutil.move(str(extracted), str(destination))
            return manifest
