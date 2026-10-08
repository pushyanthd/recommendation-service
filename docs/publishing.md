# Publish v1.0.0 yourself

The hardened candidate passed local arm64 verification. Its first amd64 CI build at `b34a1c6` failed because the `implicit` wheel ships an optional CUDA binary and runtime staging attempted to resolve its unavailable GPU libraries. The CPU staging fix excludes only `implicit/gpu/_cuda*.so` before dependency resolution, preserves its Python fallback and CPU extensions, and adds container checks and regression coverage. Publish after the fixed committed revision passes CI and the tag workflow produces verified, attested assets. This is a local experimental benchmark/demo; popularity remains selected and the failed personalization objective stays visible.

Local verification of the fix passes all 140 tests, Ruff lint/format, strict mypy and fixture smoke. A fresh linux/amd64 image builds and passes CPU ALS, HTTP exclusion, healthcheck, native-library hashes and offline/non-root/read-only verification under Docker's emulation on Apple Silicon. Its Trivy gate passes with 0 HIGH/CRITICAL, 24 MEDIUM, 10 LOW and 1 UNKNOWN; its full scan and CycloneDX SBOM remain under ignored `artifacts/ci-fix-amd64/`. This does not replace the required native amd64 GitHub checks on the new commit. The dated arm64 showcase evidence is unchanged.

Review [release readiness](release-v1.md), [security review](security.md) and [current evidence](../evals/hardened-v1-2026-10-07/README.md). Trivy reports no HIGH/CRITICAL findings, while Scout reports one unfixed HIGH and the required C++ library has an additional tracked Debian advisory. A passing CI scan does not erase either risk. Current raw scans, lower-severity findings and package provenance remain available.

## Review and commit the fixes

```bash
cd /Users/pushyanth/Desktop/Code/recommendation-service
git diff --check
git diff
git status --short
git add benchmarks/stage_runtime.py benchmarks/verify_container.py \
  benchmarks/README.md tests/test_stage_runtime.py docs/publishing.md
git diff --cached --stat
git commit -m "Fix amd64 CPU image staging by excluding optional CUDA binary"
git -c http.version=HTTP/1.1 -c http.postBuffer=16777216 push origin main
```

The commands stage project files explicitly. Real data, model bundles, local browser tools, scanner caches and distributions remain ignored. No portfolio files outside this repository are included.

## Wait for checks on your exact commit

```bash
release_commit=$(git rev-parse HEAD)
release_run=$(gh run list --commit "$release_commit" --workflow check.yml \
  --limit 1 --json databaseId --jq '.[0].databaseId // empty')
test -n "$release_run" && gh run watch "$release_run" --exit-status
```

Repeat the last two commands if the run has not appeared. Continue only when both jobs pass for this commit. The earlier passing run verifies the earlier preparation, not the CPU staging fix. CI checks tests, installed-wheel HTTP startup, fixture evaluation, CPU serving, native library provenance, vulnerability inventory and SBOM generation. Raw scan evidence is retained on gate failure; resolve a new failure before tagging.

## Tag and produce attested assets

```bash
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = "$release_commit"
git tag -a v1.0.0 -m "CPU Recommendation Service v1.0.0"
git -c http.version=HTTP/1.1 -c http.postBuffer=16777216 push origin v1.0.0
```

The tag starts `release-candidate`; it does not automatically publish a release. The workflow verifies tag/package version agreement, repeats engineering/package/image checks, scans the linux/amd64 image and generates provenance and SBOM attestations. It uploads `verified-release-assets`, including the wheel, source archive, compressed CPU image, complete Trivy scan, CycloneDX SBOM, checksums, showcase and fixture demo. Local arm64 security evidence is explicitly named separately from the fresh CI amd64 scan.

```bash
candidate_run=$(gh run list --commit "$release_commit" --workflow release.yml \
  --limit 1 --json databaseId --jq '.[0].databaseId // empty')
test -n "$candidate_run" && gh run watch "$candidate_run" --exit-status
```

Repeat those two commands if needed. Continue only after the tag workflow succeeds. Download into a new empty directory so old local builds cannot be mixed with attested assets:

```bash
release_assets="artifacts/publish-v1-${candidate_run}"
test ! -e "$release_assets" && mkdir -p "$release_assets"
gh run download "$candidate_run" --name verified-release-assets --dir "$release_assets"
(cd "$release_assets" && shasum -a 256 -c SHA256SUMS)
gh attestation verify "$release_assets/cpu_recommendation_service-1.0.0-py3-none-any.whl" \
  --repo pushyanthd/recommendation-service --source-digest "$release_commit" \
  --signer-workflow pushyanthd/recommendation-service/.github/workflows/release.yml
gh attestation verify "$release_assets/cpu_recommendation_service-1.0.0.tar.gz" \
  --repo pushyanthd/recommendation-service --source-digest "$release_commit" \
  --signer-workflow pushyanthd/recommendation-service/.github/workflows/release.yml
gh attestation verify "$release_assets/cpu-recommendation-service-linux-amd64.tar.gz" \
  --repo pushyanthd/recommendation-service --source-digest "$release_commit" \
  --signer-workflow pushyanthd/recommendation-service/.github/workflows/release.yml
gh attestation verify "$release_assets/cpu-recommendation-service-linux-amd64.tar.gz" \
  --repo pushyanthd/recommendation-service --source-digest "$release_commit" \
  --signer-workflow pushyanthd/recommendation-service/.github/workflows/release.yml \
  --predicate-type https://cyclonedx.org/bom
```

Inspect `image-audit.json`, `trivy.json`, `security-review-arm64.json` and the workflow attestation summary. The SBOM attestation uses the CycloneDX predicate `https://cyclonedx.org/bom`. If any verification fails, stop before publication and inspect that run's evidence.

## Publish the verified assets

```bash
gh release create v1.0.0 --verify-tag --title "CPU Recommendation Service v1.0.0" \
  --notes-file docs/release-notes-v1.md \
  "$release_assets"/*.whl "$release_assets"/*.tar.gz "$release_assets"/*.json \
  "$release_assets"/*.jsonl "$release_assets"/*.html "$release_assets"/*.png \
  "$release_assets"/*.webm "$release_assets/SHA256SUMS"
gh release view v1.0.0 --web
```

The release wheel/source/image contain fictional fixtures and no MovieLens rows or trained real-data bundles. Dataset preparation remains explicit and subject to GroupLens terms. A wheel installed alone does not pin external dependencies; use the source archive and committed lock for reproduction. Attach the CI-built bytes above so the attestations match; do not replace them with a subsequent local build. Public API hosting and PyPI publication are separate decisions.

To use the attached CPU image locally:

```bash
gzip -dc cpu-recommendation-service-linux-amd64.tar.gz | docker load
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges \
  -p 127.0.0.1:8000:8000 cpu-reco:local
```

That archive is linux/amd64. Apple Silicon can use Docker's emulation or build its own native image with `make image image-check audit`. The native local image is verified separately and is not the attested amd64 archive.
