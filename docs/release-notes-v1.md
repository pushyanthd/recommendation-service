# CPU Recommendation Service v1.0.0

CPU-only movie recommendations with a typed API, browser demo and independently reproducible offline evaluation. The release compares popularity, item similarity and ALS; selects from validation; and preserves that decision through verified bundles and actual restart/rollback.

- Chronological full-catalog MovieLens comparison for 1,188 final users, zero scoring failures and unreachable positives retained as misses.
- Saved/ephemeral preferences, genre filtering, all-seen exclusion, cold-start fallback and explicit popularity comparison.
- 137 passing local tests, lint/types, isolated installed-wheel HTTP startup outside the checkout and desktop/mobile browser verification.
- A smaller staged CPU image with native-library provenance, offline/non-root/read-only serving and actual healthcheck/CPU ALS verification.
- Complete vulnerability scans, CycloneDX SBOM, checksum-listed release assets and tag-workflow provenance/SBOM attestations.
- Selected-baseline serving: 5,000 HTTP requests, zero failures, 11.65 ms client P95 and 175.8 MiB API RSS on Apple M1; four recovery drills passed.
- An actual fictional-fixture screenshot and captioned video, plus standalone HTML/JSON/Markdown reports, cards and reproduction guides.

Item similarity gained 11.97% final NDCG, but its 3.41% validation gain missed the frozen 10% objective. Popularity remains selected and quality retains its experimental label. Trivy reports no HIGH/CRITICAL findings in the local candidate; independent Scout reports one unfixed zlib HIGH, and the required C++ library has an additional tracked Debian advisory. The locked Python dependency audit is clear. This is a local benchmark/demo with no active-personalization, online-effect or production-security claim.

Start with the [README](https://github.com/pushyanthd/recommendation-service/blob/v1.0.0/README.md), [case study](https://github.com/pushyanthd/recommendation-service/blob/v1.0.0/docs/engineering-case-study.md), [security review](https://github.com/pushyanthd/recommendation-service/blob/v1.0.0/docs/security.md) and [current evidence](https://github.com/pushyanthd/recommendation-service/tree/v1.0.0/evals/hardened-v1-2026-10-07). Download the attached fixture video and showcase HTML for a walkthrough without dataset setup.

```bash
make setup
make check
make demo-fixture
```

Python 3.12 is required. Dependency and optional dataset preparation are explicit network steps; subsequent fixture/runtime execution is offline. Attached wheel/source/image assets contain fictional fixtures, no MovieLens rows or trained real-data bundles. The CPU image archive is linux/amd64; Apple Silicon can build natively. Use the source archive and committed lock for reproduction; a wheel alone does not pin external dependencies. Verify attached checksums and attestations with the [publishing guide](https://github.com/pushyanthd/recommendation-service/blob/v1.0.0/docs/publishing.md).
