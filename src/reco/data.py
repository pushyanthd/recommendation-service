import hashlib
import math
from dataclasses import dataclass
from importlib.resources import files

from reco.contracts import DataMode, Fixture, Movie, Rating


@dataclass(frozen=True)
class Dataset:
    movies: tuple[Movie, ...]
    ratings: tuple[Rating, ...]
    fingerprint: str
    data_mode: DataMode = "fictional_fixture"

    def __post_init__(self) -> None:
        movie_ids = {movie.movie_id for movie in self.movies}
        if len(movie_ids) != len(self.movies):
            raise ValueError("Duplicate catalog IDs")
        pairs = {(event.user_id, event.movie_id) for event in self.ratings}
        if len(pairs) != len(self.ratings):
            raise ValueError("Duplicate user/movie ratings")
        if any(event.movie_id not in movie_ids for event in self.ratings):
            raise ValueError("Rating references an unknown movie")
        if not self.ratings:
            raise ValueError("No rating events")


@dataclass(frozen=True)
class TemporalSplit:
    train: tuple[Rating, ...]
    validation: tuple[Rating, ...]
    test: tuple[Rating, ...]
    validation_cutoff: int
    test_cutoff: int


def chronological_split(
    events: tuple[Rating, ...], train_fraction: float = 0.8, test_start: float = 0.9
) -> TemporalSplit:
    if not 0 < train_fraction < test_start < 1:
        raise ValueError("Split fractions must satisfy 0 < train < test_start < 1")
    if len(events) < 3:
        raise ValueError("At least three events are required")
    ordered = sorted(event.timestamp for event in events)
    first = ordered[math.ceil((len(ordered) - 1) * train_fraction)]
    second = ordered[math.ceil((len(ordered) - 1) * test_start)]
    train = tuple(event for event in events if event.timestamp < first)
    validation = tuple(event for event in events if first <= event.timestamp < second)
    test = tuple(event for event in events if event.timestamp >= second)
    if not train or not validation or not test:
        raise ValueError("Timestamp ties leave an empty split; choose explicit wider periods")
    return TemporalSplit(train, validation, test, first, second)


def load_fixture() -> Dataset:
    raw = files("reco").joinpath("fixtures/movies.json").read_bytes()
    parsed = Fixture.model_validate_json(raw)
    return Dataset(parsed.movies, parsed.ratings, hashlib.sha256(raw).hexdigest())
