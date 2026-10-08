# System card

This is a local CPU recommendation benchmark and demo. It recovers future highly rated movies from historical rating events, serves unseen titles, and compares the frozen selection with popularity. It is not an online experiment or an authenticated personal-profile service.

## Model and serving behavior

Popularity counts prior four/five-star ratings. Item similarity uses positive-interaction cosine neighbors capped at 100 per movie. ALS uses the directly imported `implicit.cpu.als` implementation with 32 factors, 15 iterations, regularization 0.1, confidence 20 and seed 42. The numerical implementation and configuration remain those used in the October 6 frozen evaluation. Popularity is selected because both personalized methods missed validation; item similarity's stronger final result cannot change that decision.

All methods use the same prediction-time catalog and exclude every prior rating, including dislikes. Ephemeral likes never modify stored histories or factors. Unknown identifiers and genres are rejected, filters stay in place, ties use movie IDs, and an exhausted catalog returns a shorter list. Scores are within-method ranking values rather than calibrated probabilities. Method reason codes do not explain a causal preference.

The serving path records history lookup, scoring, filtering/top-k, complete ranking and HTTP histograms. Independent parity checks compare its outputs with the frozen benchmark implementation for all three methods, saved users, ephemeral profiles and filters. Request counters and logs omit profile identifiers and histories. `/metrics` has bounded labels; model versions are carried in status/logs rather than accumulating labels.

## Model lifecycle

The CLI refits the selected method using only pre-test events, verifies numerical code/configuration/history/catalog identities against the frozen report, and writes a hash-verified immutable bundle. Positive and all-seen CSR histories remain separate. Arrays load with pickle disabled; checks cover canonical CSR indices, bounds, binary histories, finite values, mappings, popularity consistency and factor dimensions. Local checksums detect damage and do not authenticate downloaded third-party models.

Initial selection is explicit. Activation validates a candidate before changing the active pointer, stops only the process whose command and ownership token match its recorded PID, restarts and checks readiness against the requested model ID. A failed startup restores the prior pointer/process. Rollback requires a previously verified activation. Interrupted selection can recover from a validated last-known-good pointer. The HTTP API exposes no training, activation, model upload or filesystem path input.

Showcase drills run in an isolated artifact root with real files and processes. The second version contains the same frozen treatment with different lifecycle provenance, so testing rollback does not change model settings after final evaluation. Raw process IDs, pointers, request timings and logs support the aggregate evidence.

## Boundaries and packaging

Native serving binds to loopback. Trusted-host, same-origin, JSON-body and typed request limits apply. The browser inserts movie titles with DOM text nodes rather than interpreting them as HTML. Benchmark sample IDs select public-dataset examples and do not represent authenticated accounts. Preferences are not persisted.

The image pins the official Python base by digest, installs the locked Python runtime dependencies and a pinned OpenMP library, and runs as UID 10001. The portable image includes only fictional fixtures and their verified snapshot. Verification runs with a read-only filesystem, no network, dropped capabilities and no GPU device requests; it checks real HTTP requests and trains CPU ALS. MovieLens rows and real bundles stay outside Git and the image. Host port publication must use `127.0.0.1`.

The October 7 dependency audit is clear. The patched image's high/critical scan retains eight high findings with no fixed version reported. The complete finding list and image identity are in the [security evidence](../evals/2026-10-07/security.json). This remains an experimental local demo, with no production-security claim. `make audit` deliberately reports those outstanding image findings with a nonzero exit.

## Evidence limits

The [October 6 quality report](../evals/2026-10-06/final/report.html) accounts for all 1,188 eligible users across three methods. MovieLens already filters participation; observed ratings are not exposure or viewing events. Missing labels are unobserved preferences. Shared items/training constrain interpretation of paired user bootstrap intervals. No engagement, causal discovery or revenue uplift is established.

The [October 7 showcase](../evals/2026-10-07/report.html) records HTTP measurements, application memory, startup, actual recovery and image checks. Client latency includes queueing. Training, API-process, container-runtime and whole-system memory are distinct measurements. CI uses fixtures and verifies image/correctness behavior; shared runners do not enforce the reference-hardware latency objective.
