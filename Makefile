PYTHON ?= python3.12
BENCHMARK_DIR ?= artifacts/benchmark
DIST_DIR ?= dist
DIST_SETUP ?= --allow-downloads
IMAGE ?= cpu-reco:local
IMAGE_AUDIT_DIR ?= artifacts/image-audit
TRIVY_CACHE ?= artifacts/trivy-cache
UV = .bootstrap/bin/uv
export UV_CACHE_DIR := $(CURDIR)/.uv-cache
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1
export OMP_NUM_THREADS := 2

.PHONY: setup check test smoke demo-fixture data-fetch benchmark benchmark-final
setup:
	$(PYTHON) -m venv .bootstrap
	.bootstrap/bin/python -m pip install --no-cache-dir uv==0.12.18
	$(UV) sync --locked

check:
	.venv/bin/ruff check src tests benchmarks
	.venv/bin/ruff format --check src tests benchmarks
	.venv/bin/mypy
	.venv/bin/pytest

test:
	.venv/bin/pytest

smoke:
	.venv/bin/reco fixture-smoke --output artifacts/fixture-smoke.json

demo-fixture:
	.venv/bin/reco serve-fixture

data-fetch:
	.venv/bin/reco data-fetch

benchmark:
	.venv/bin/reco benchmark --output $(BENCHMARK_DIR)

benchmark-final:
	.venv/bin/reco benchmark --final --output $(BENCHMARK_DIR)

.PHONY: bundle dev start stop showcase image
bundle:
	.venv/bin/reco build-bundle --report $(BENCHMARK_DIR)/final --select

dev:
	.venv/bin/reco serve

start:
	.venv/bin/reco start

stop:
	.venv/bin/reco stop

showcase:
	.venv/bin/reco showcase --report $(BENCHMARK_DIR)/final --container-evidence artifacts/container/verification.json

image:
	docker build -t $(IMAGE) .

.PHONY: image-check audit
image-check:
	.venv/bin/python benchmarks/verify_container.py --image $(IMAGE)

audit:
	$(UV) audit --locked
	.venv/bin/python benchmarks/image_audit.py --image $(IMAGE) --output $(IMAGE_AUDIT_DIR) --cache $(TRIVY_CACHE)

.PHONY: distribution distribution-check
distribution:
	$(UV) build --out-dir $(DIST_DIR)

distribution-check: distribution
	.venv/bin/python benchmarks/verify_distribution.py --directory $(DIST_DIR) $(DIST_SETUP)
