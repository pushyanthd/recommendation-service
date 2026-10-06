PYTHON ?= python3.12
UV = .bootstrap/bin/uv
export UV_CACHE_DIR := $(CURDIR)/.uv-cache
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1
export OMP_NUM_THREADS := 2

.PHONY: setup check test smoke demo-fixture
setup:
	$(PYTHON) -m venv .bootstrap
	.bootstrap/bin/python -m pip install --no-cache-dir uv==0.12.18
	$(UV) sync --locked

check:
	.venv/bin/ruff check src tests
	.venv/bin/ruff format --check src tests
	.venv/bin/mypy
	.venv/bin/pytest

test:
	.venv/bin/pytest

smoke:
	.venv/bin/reco fixture-smoke --output artifacts/fixture-smoke.json

demo-fixture:
	.venv/bin/reco serve-fixture
