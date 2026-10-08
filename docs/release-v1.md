# Recommendation service v1.0.0 release readiness

The local engineering candidate is verified; publication is user-managed. No commits, tags or release uploads were made during this hardening work. Follow [publishing](publishing.md) after reviewing the [current evidence](../evals/hardened-v1-2026-10-07/README.md) and [security review](security.md).

## Completed locally

- [x] Deliver the nine architecture criteria with the [acceptance mapping](acceptance.md).
- [x] Preserve the frozen MovieLens treatment, external dependencies and validation selection; popularity remains active.
- [x] Pass 137 tests, Ruff lint/format and strict mypy.
- [x] Verify isolated wheel installation, three CPU fixture methods, bundle roundtrip and real HTTP/browser-page startup without a checkout or working-directory lock.
- [x] Stage a smaller CPU runtime with no shells/package managers or unused operating-system tools; retain Debian library owners, versions, hashes and scanner metadata.
- [x] Verify non-root/read-only/network-disabled HTTP, actual Docker healthcheck, native library hashes and CPU ALS.
- [x] Retain complete independent scans, CycloneDX SBOM and clear locked Python dependency audit; explicitly track unresolved zlib and C++ advisories.
- [x] Add a fail-closed Trivy gate and failure evidence upload to CI; pin GitHub actions to full commit IDs.
- [x] Prepare a tag-triggered workflow for checked distributions, CPU image archive and provenance/SBOM attestations.
- [x] Capture an actual [fixture screenshot and captioned recording](demo/README.md), with desktop/mobile verification.
- [x] Refresh full-protocol HTTP/recovery evidence against the current runtime source and hardened image.

Historical October 6/7 reports remain immutable. The new scanner gate passes for the local image, with zero Trivy HIGH/CRITICAL findings. Scout reports one unfixed HIGH; libstdc++ remains required and Debian's advisory is tracked even though the scanners omit it. This candidate does not claim zero known vulnerabilities or production readiness.

## Publication steps remaining

- [ ] Review, commit and push the prepared files yourself.
- [ ] Verify both `checks` jobs on that exact commit.
- [ ] Tag the passing revision `v1.0.0` and wait for `release-candidate`.
- [ ] Download its CI-built assets; verify checksums and provenance/SBOM attestations.
- [ ] Publish the GitHub release with those exact assets and the prepared notes.

The new CI/tag workflows cannot be verified remotely until you push them. Local syntax validation has passed; earlier GitHub results apply to the prior commit. The [publishing guide](publishing.md) includes every command and stops publication on a failed check.

## Research and deployment scope

The frozen final comparison covers 1,188 eligible users, with zero scoring failures per method. Item similarity gained 11.97% final NDCG, but its 3.41% validation gain missed the frozen 10% objective. The label `experimental_quality_objective_failed` remains visible. A future personalization study needs a separate protocol and an untouched holdout.

Authenticated users, public API deployment, large catalogs and online engagement claims remain outside the bounded v1. Local engineering completion does not imply that the research objective passed.
