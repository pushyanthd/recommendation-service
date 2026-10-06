# Implementation progress

## First development slice

Implemented package/CLI scaffolding, fictional fixture data, global chronological splits, popularity, item cosine similarity, CPU ALS, seen-item filtering, ephemeral fold-in, ranking metrics, validation evaluation, local API and a small browser demo. The serving baseline is popularity; no automatic promotion is claimed.

Tests target leakage, metric arithmetic, low-rated seen items, cold-start fallback, filter preservation, finite scores, malformed requests and fixture HTTP behavior. The dependency lock and CI checks belong to this milestone.

### Verification on October 5, 2026

The documented `make setup` completes in a project-owned environment on arm64 macOS / Python 3.12.12. `make check` passes 48 tests, Ruff and strict mypy. The three-method CPU smoke trains on 29 fictional events and accounts for all four validation users per method with zero scoring failures; four final-period events remain reserved. The ALS backend is asserted to be `implicit.cpu.als`.

A temporary loopback Uvicorn process passes actual HTTP readiness, page and recommendation requests. The saved-profile request returns seven unseen titles, excluding all five of that profile's prior rated movies. The process stops after verification. This checks HTTP behavior rather than browser interaction, real-data recommendation quality or load capacity.

## Next milestone

Implement explicit MovieLens 1M ingestion with pinned archive identity, bounded extraction, source terms and data-contract checks. Then produce real development comparisons and paired intervals before freezing selection gates. Keep held-out test labels out of parameter selection.

Bundle lifecycle, operations evidence and final release acceptance follow the architecture plan. Fixture smoke results cannot substitute for any real-data or product-quality gate.
