import hashlib
import json
import stat
import zipfile

import pytest

from reco import ingestion
from reco.ingestion import extract_archive, parse_movielens


def source_archive(tmp_path, extra=None, entries=None):
    path = tmp_path / "source.zip"
    contents = entries or {
        "ml-1m/movies.dat": "1::Café (fictional)::Drama\n2::Orbit::Sci-Fi\n".encode("latin-1"),
        "ml-1m/ratings.dat": b"1::1::5::1\n1::2::2::2\n2::1::4::3\n",
        "ml-1m/users.dat": b"ignored demographic data",
        "ml-1m/README": b"authored fixture terms",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in contents.items():
            archive.writestr(name, payload)
        if extra:
            archive.writestr(*extra)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_bounded_extraction_preserves_encoding_and_terms_ignores_demographics(tmp_path):
    archive, digest = source_archive(tmp_path)
    directory = tmp_path / "data"
    extract_archive(archive, directory, digest)
    data = parse_movielens(directory, digest)
    assert data.data_mode == "movielens_1m"
    assert data.movies[0].title == "Café (fictional)"
    assert len(data.ratings) == 3
    assert (directory / "README").read_text() == "authored fixture terms"
    assert not (directory / "users.dat").exists()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "ml-1m/../../escape", "other.txt"])
def test_unknown_and_traversal_entries_rejected_before_writes(tmp_path, name):
    archive, digest = source_archive(tmp_path, extra=(name, b"bad"))
    directory = tmp_path / "data"
    with pytest.raises(ValueError, match="archive entries"):
        extract_archive(archive, directory, digest)
    assert not directory.exists()


def test_duplicate_entry_rejected(tmp_path):
    with pytest.warns(UserWarning, match="Duplicate"):
        archive, digest = source_archive(tmp_path, extra=("ml-1m/README", b"duplicate"))
    with pytest.raises(ValueError, match="Duplicate"):
        extract_archive(archive, tmp_path / "data", digest)


def test_symlink_rejected(tmp_path):
    entry = zipfile.ZipInfo("ml-1m/README")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    archive, digest = source_archive(
        tmp_path,
        entries={
            "ml-1m/movies.dat": b"",
            "ml-1m/ratings.dat": b"",
            "ml-1m/users.dat": b"",
            entry: b"/private/secret",
        },
    )
    with pytest.raises(ValueError, match="Nonregular"):
        extract_archive(archive, tmp_path / "data", digest)


def test_checksum_and_size_fail_closed(tmp_path, monkeypatch):
    archive, digest = source_archive(tmp_path)
    with pytest.raises(ValueError, match="checksum"):
        extract_archive(archive, tmp_path / "data", "0" * 64)
    monkeypatch.setattr(ingestion, "MAX_ARCHIVE_BYTES", 1)
    with pytest.raises(ValueError, match="byte limit"):
        extract_archive(archive, tmp_path / "data", digest)
    monkeypatch.setattr(ingestion, "MAX_ARCHIVE_BYTES", 10000)
    monkeypatch.setattr(ingestion, "MAX_EXTRACTED_BYTES", 1)
    with pytest.raises(ValueError, match="byte limit"):
        extract_archive(archive, tmp_path / "data", digest)


@pytest.mark.parametrize(
    "ratings",
    [
        b"1::999::5::1\n",
        b"1::1::6::1\n",
        b"1::1::4::-1\n",
        b"1::1::5::1\n1::1::4::2\n",
    ],
)
def test_invalid_rating_values_joins_and_duplicates(tmp_path, ratings):
    archive, digest = source_archive(tmp_path)
    directory = tmp_path / "data"
    extract_archive(archive, directory, digest)
    (directory / "ratings.dat").write_bytes(ratings)
    with pytest.raises(ValueError):
        parse_movielens(directory, digest)


def test_dataset_file_tampering_fails_before_parsing(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "archive_sha256": ingestion.ARCHIVE_SHA256,
                "files": {name: "0" * 64 for name in ingestion.RETAINED_FILES},
            }
        )
    )
    (directory / "movies.dat").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        ingestion.load_movielens(directory)


def test_setup_rejects_bad_archive_without_partial_install(tmp_path):
    archive, _ = source_archive(tmp_path)
    destination = tmp_path / "installed"
    with pytest.raises(ValueError, match="checksum"):
        ingestion.setup_movielens(destination, archive)
    assert not destination.exists()
