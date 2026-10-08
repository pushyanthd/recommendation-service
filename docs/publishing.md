# Publishing v1.0.0 yourself

Package v1.0.0 is prepared locally. No commits, pushes, tags or releases were made during this preparation. The software release covers the bounded local benchmark/demo; the failed personalized validation objective remains experimental and popularity stays selected.

## Verified scope and retained findings

The release image `cpu-reco:v1.0.0` passed non-root/read-only/network-disabled CPU checks. Its current high/critical scan records eight unfixed high findings and zero fixable high/critical findings; the Python dependency audit is clear. [Release evidence](../evals/release-v1-2026-10-07/README.md) retains the image and scan identities. Review these limits before publishing the local experimental demo.

Automatic approval review initially rejected the Docker Scout scan because of potential image-metadata transfer. A read-only check established that all image source/build instructions match the public repository and that the image contains only public dependencies and fictional fixtures. Review then allowed the scan; the fresh result above was retained without suppressions.

To refresh the scan yourself later:

```bash
cd /Users/pushyanth/Desktop/Code/recommendation-service
docker scout cves cpu-reco:v1.0.0 --only-severity critical,high --exit-code
```

This exits nonzero while high/critical findings remain. It may send image-derived package metadata to Docker's service. Preserve new results with their actual image identity and date rather than rewriting the historical evidence.

## Review, commit and push

```bash
git diff --check
git diff
git status --short
git add pyproject.toml uv.lock Makefile .github/workflows/check.yml \
  benchmarks/verify_distribution.py README.md arch_plan/recommendation-service-plan.md \
  docs/acceptance.md docs/progress.md docs/release-v1.md docs/reproduction.md \
  docs/system-card.md docs/publishing.md docs/release-notes-v1.md \
  evals/release-v1-2026-10-07
git diff --cached --stat
git commit -m "Prepare verified CPU recommendation service v1.0.0"
git push origin main
```

Only project release files are staged. Real data, model bundles, raw profile traffic and generated distributions stay ignored. The separate portfolio working tree is outside this commit.

## Check the committed revision in CI

Wait for the `checks` workflow on the exact pushed commit. It checks the fixture, full test suite, package installation and CPU image. The prior passing jobs cover 0.1.0 and do not verify the new packaging step.

```bash
release_commit=$(git rev-parse HEAD)
release_run=$(gh run list --commit "$release_commit" --workflow check.yml \
  --limit 1 --json databaseId --jq '.[0].databaseId // empty')
test -n "$release_run" && gh run watch "$release_run" --exit-status
```

If the run has not appeared yet, repeat the last two commands. Continue only after that exact commit passes both jobs. GitHub upload artifacts retain the Python distributions and container verification for the committed source.

## Build final assets and publish

```bash
make distribution-check DIST_DIR=artifacts/full-release-v1/distribution
(cd artifacts/full-release-v1/distribution && shasum -a 256 -c SHA256SUMS)
git tag -a v1.0.0 -m "CPU Recommendation Service v1.0.0"
git push origin v1.0.0
gh release create v1.0.0 --verify-tag --title "CPU Recommendation Service v1.0.0" \
  --notes-file docs/release-notes-v1.md \
  artifacts/full-release-v1/distribution/cpu_recommendation_service-1.0.0-py3-none-any.whl \
  artifacts/full-release-v1/distribution/cpu_recommendation_service-1.0.0.tar.gz \
  artifacts/full-release-v1/distribution/verification.json \
  artifacts/full-release-v1/distribution/SHA256SUMS
gh release view v1.0.0 --web
```

Tag the verified commit without further source changes. The wheel and source archive include fictional fixtures; neither includes MovieLens rows or trained real-data bundles. Dataset setup remains an explicit step governed by the preserved GroupLens terms. PyPI publication and public API hosting are outside this release.
