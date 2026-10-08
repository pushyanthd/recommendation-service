# v1 container security review

The hardened v1 candidate removes unused operating-system tools, preserves the provenance of every retained native library, and passes offline CPU/API verification. It is a local portfolio demo with unresolved library advisories. A lower scanner count does not establish that every advisory was fixed.

## What changed

The build pins the official Python 3.12.15 Debian Trixie image by digest. A staging helper copies Python, the locked virtual environment, fictional model bundle, certificates, timezone data and the ELF library dependencies into a `scratch` runtime. It excludes package managers, shells, Perl, mount/session utilities and optional terminal/GUI extensions. The API retains Python's UUID fallback. This image supports API serving and CPU inference; dependency setup and host process-management commands belong outside it.

`/usr/share/reco-runtime/inventory.json` records the base digest, staging-helper hash, each native library's SHA-256 and Debian owner/version. `/var/lib/dpkg/status` retains the corresponding package control records, including source-package attribution. Scanner metadata was preserved rather than deleted to reduce findings. The verifier checks those library hashes, the missing tools, UID 10001, the actual executable-form Docker healthcheck, HTTP seen-item exclusion and the imported CPU ALS backend. Its container has no network, a read-only root, dropped capabilities and no GPU.

The local arm64 image is 244.0 MiB, compared with 344.0 MiB for the earlier candidate. [Checksummed evidence](../evals/hardened-v1-2026-10-07/README.md) binds the image ID, inventory, complete scans, SBOM and dependency audit. CI separately builds and checks linux/amd64; that new revision still needs your commit/push.

## Findings and applicability

| Exposure | Change or remaining risk |
| --- | --- |
| Four util-linux advisories in the earlier image | Its tools and libraries are absent from the staged runtime; removing `_uuid` avoids retaining libuuid |
| Perl advisories | Perl is absent; the API does not execute Perl |
| OpenSSL CVE-2026-84782 | Retained OpenSSL is `3.5.7-1~deb13u3`, the [Debian fixed Trixie version](https://security-tracker.debian.org/tracker/CVE-2026-84782) |
| Additional Trivy findings in ncurses, systemd and libacl | These packages are absent from the staged runtime |
| zlib CVE-2026-85091 | Scout reports one unfixed HIGH. [Debian's tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091) discusses an affected-range discrepancy; keep it unresolved without suppressing it |
| libstdc++ CVE-2026-95619 | The required `libstdc++6` library remains at `14.2.0-19`. [Debian marks gcc-14 vulnerable](https://security-tracker.debian.org/tracker/CVE-2026-95619). Current scans omit it, so it remains explicitly tracked |

The final independent scans disagree. Trivy 0.74.0 reports **0 CRITICAL, 0 HIGH, 24 MEDIUM, 10 LOW and 1 UNKNOWN** package findings. Scout 1.24.0 reports **one HIGH** plus lower-severity findings. The locked Python dependency audit reports zero vulnerabilities across 38 audited packages. Those are dated scanner observations, not a proof of absence. The C++ advisory affects aligned allocation and zlib's advisory concerns non-blocking gzip writes; no complete native-call reachability proof was performed.

## Repeat the checks

```bash
make image image-check audit
# Independent review; this may transmit image-derived package metadata to Docker.
docker scout cves cpu-reco:local --format sarif \
  --output artifacts/image-audit/scout.sarif.json
```

`make audit` scans an exported image with a digest-pinned Trivy container, disables telemetry/version checks, uses no ignore file, records all severities and converts the same report to CycloneDX. It rejects a wrong image, missing native/Python inventories, an unsupported/EOL OS, suppressed results, and every Trivy HIGH/CRITICAL finding even without a fix. It preserves raw results before failing. CI uploads scan and container evidence even when this gate fails. Independent Scout and Debian review remain necessary; a passing Trivy gate cannot close those findings.

Publish the API port on `127.0.0.1`, retain the documented request limits and use trusted locally produced model bundles. Refresh the pinned base and scan databases for a future release, rebuild and rerun the functional checks; never rewrite earlier dated evidence or declare a finding fixed solely because a scanner omitted it. No image, package or website has been published during this hardening work.
