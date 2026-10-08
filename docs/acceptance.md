# Recommendation service v1 acceptance

The bounded local service and corrected-code engineering verification are complete. Package v1.0.0 is prepared locally; commits, tags and publication remain user-managed. The original engineering acceptance passed, including HTTP/resource objectives and all four recovery drills. The personalized quality objective failed validation, so popularity stays active and the benchmark retains its experimental quality label. Software release status and model-quality results are separate outcomes, and the failed objective remains visible.

## Architecture acceptance criteria

The nine criteria in the [architecture plan](../arch_plan/recommendation-service-plan.md#11-test-strategy-and-automated-acceptance) map to the following evidence.

| Criterion | Status | Evidence |
| --- | --- | --- |
| 1. Locked installation, fictional demo and CPU image | Delivered | [Clean environment reproduction](../evals/reproduction-2026-10-07/README.md): new non-editable installation, 119 passing tests, fixture workflow and CPU image recheck; dependency setup explicitly uses a populated cache |
| 2. Explicit validated data setup and offline pipeline | Delivered | [Dataset manifest](../datasets/manifest.json), [data card](data-card.md), archive checksum and immutable split identity |
| 3. Three frozen full-catalog final reports | Delivered | [Final report](../evals/2026-10-06/final/report.html): 1,188 users per method, zero failures, 45 unreachable positives retained |
| 4. Automatic selection and honest release label | Delivered with failed quality objective | [Validation report](../evals/2026-10-06/development/report.html): popularity selected; final label `experimental_quality_objective_failed` |
| 5. Saved and ephemeral browser/API workflow | Delivered | [System card](system-card.md), saved/ephemeral/filter API tests and recorded Chromium verification in [progress](progress.md) |
| 6. Declared hardware and resource measurements | Passed for selected baseline | [Showcase](../evals/2026-10-07/report.html): HTTP P95 11.52 ms, zero failures, API RSS 175.3 MiB; [quality report](../evals/2026-10-06/final/report.html): training-process peak RSS 914 MiB |
| 7. Four failure drills and ranking invariants | Passed | Actual-process [showcase](../evals/2026-10-07/report.html) and [rollback runbook](rollback.md) |
| 8. Checksummed showcase bound to tested identities | Delivered | [Showcase manifest](../evals/2026-10-07/manifest.json), raw and aggregate `verify-showcase` commands in the [evidence guide](../evals/2026-10-07/README.md) |
| 9. Results, limitations, cards and reproduction | Delivered | [README](../README.md), [case study](engineering-case-study.md), [data card](data-card.md), [system card](system-card.md) and [reproduction guide](reproduction.md) |

Engineering completion does not imply that personalization passed or that the service is ready for production. The hardened candidate passes the Trivy HIGH/CRITICAL gate while retaining independent Scout and Debian advisories in the [security review](security.md). Public hosting, release tags and online experiments are outside local v1 acceptance.

The clean environment reproduction also rebuilt real-data reports and a serving bundle. All three numerical treatment identities matched the original run, and every per-user metric reproduced with maximum difference 0.0. Actual HTTP checks verified readiness, real-data provenance and seen-item exclusion without using the original serving bundle.

## Portfolio release work

The implementation, measured reports, case study and demo walkthrough were published in the source repository. The Linux process-inspection correction passed both [GitHub fixture and CPU-image jobs](https://github.com/pushyanthd/recommendation-service/actions/runs/37709752278). The remaining work is tracked in [release readiness](release-v1.md). No release tag or GitHub release has been published. The [publishing guide](publishing.md) provides commands for the remaining commit, CI and publication steps.

The [recorded fictional demo](demo/README.md) includes a screenshot, captioned walkthrough and desktop/mobile verification. The case study explains the real-data reports and failed validation gate. Additional recommenders, a learned reranker and cloud infrastructure are follow-up projects rather than requirements for this release.

## Corrected code verification

The [corrected-code evidence](../evals/ci-corrected-2026-10-07/README.md) refreshes criteria 1, 6, 7 and 8 after the Linux lifecycle correction. All 121 local tests pass, the dependency audit is clear and [both GitHub jobs pass](https://github.com/pushyanthd/recommendation-service/actions/runs/37710120597). The full HTTP protocol completed 5,000 requests with zero failures, 12.07 ms client P95 and 175.5 MiB API RSS; all four recovery drills passed. Raw and exported evidence verify against the tested active bundle/current package. The original numerical treatment, quality decision and dated reports remain unchanged.

## v1.0.0 preparation

The [release verification](../evals/release-v1-2026-10-07/README.md) refreshes package/bundle/image identities for v1.0.0. The full HTTP protocol completed 5,000 requests with zero failures, 11.66 ms client P95 and 175.4 MiB API RSS; all four recovery drills passed. All 121 local tests, lint/types and the offline fixture canary pass. Built distributions pass an isolated installed-CLI check outside the source checkout. That earlier image retained eight unfixed high findings. See the hardened verification below for current evidence; the original report remains historical.

## Hardened v1 verification

The [hardened evidence](../evals/hardened-v1-2026-10-07/README.md) refreshes the runtime and full serving protocol. Local checks pass 137 tests, lint/format/types, real installed-wheel HTTP startup outside the checkout, offline CPU image checks and desktop/mobile browser interactions. Runtime library provenance and the actual Docker healthcheck are verified. Complete independent scans and a CycloneDX SBOM are retained, with the unresolved zlib and C++ advisories explicitly tracked.

CI now pins actions to full commits, rejects incomplete/suppressed image scans and fails every Trivy HIGH/CRITICAL finding. The prepared tag workflow produces checksum-listed release assets and provenance/SBOM attestations. New-revision CI, tag attestations and publication remain unperformed until your commit/push; use [publishing](publishing.md). The existing source preparation passed [both prior GitHub jobs](https://github.com/pushyanthd/recommendation-service/actions/runs/37711672719), which does not verify these changes.
