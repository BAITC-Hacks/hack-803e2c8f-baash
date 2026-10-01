[Русский](DEVELOPMENT.md) · [English](DEVELOPMENT.en.md) · [Қазақша](DEVELOPMENT.kk.md)

# Development and verification

[README](../../README.en.md) is the judge overview. This page contains developer commands and dated CI results; technical names are preserved.

## Local checks

```sh
make lint typecheck test contract-test e2e build
make eda
uv run python scripts/demo_runtime.py prepare
```

`prepare` builds the local PostgreSQL demo, exercises the complete API flow, removes only `pulse109-demo` project volumes, seeds a fresh world, and verifies Golden Demo. Success is `PULSE 109 DEMO READY`. Ports and boundaries: [runbook](../demo/DEMO_RUNBOOK.en.md). This command does not maintain the public VPS project `pulse109-final`.

PostgreSQL integration tests require `PULSE109_TEST_DATABASE_URL`. Skipped without this variable is not passed. For two independent runs:

```sh
PULSE109_TEST_DATABASE_URL=postgresql://<role>:<password>@<host>:5432/<existing-db> \
  uv run python scripts/run_integration_tests.py --runs 2
```

The role must create and drop test databases whose names contain UUIDs. The runner does not alter the supplied source database or the demo database.

## Verified stabilization release

[CI 36889724226](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889724226) on executable revision `135680a`, October 1, 2026: **all four jobs passed**.

| Job / step | Result |
| --- | --- |
| quality: lint, typecheck, build, Compose | passed |
| quality: pytest | 439 passed, 23 skipped without an integration DB |
| quality: contract / e2e | 26 passed / 18 passed |
| container-smoke | passed: services, extensions, migrations, and restore drill |
| isolated integration runner | 23 passed in each of two disposable PostgreSQL databases |
| demo-profile-smoke | passed: seed and complete API flow |
| security-supply-chain | passed: Python/Node audit, gitleaks, image build, both Trivy steps, SBOM |

Current full-run counts live in this section; other documents link here.

### Targeted dependency fixes

| Component | Before → after |
| --- | --- |
| PyJWT | 2.14.0 → 2.15.0 |
| urllib3 | 2.7.0 → 2.8.0 |
| Next.js / eslint-config-next | 16.3.4 → 16.3.6 |
| brace-expansion | 1.1.18 → 1.1.21; 5.0.9 → 5.0.12 |
| libpcre2-8-0 in the API image | 10.46-1~deb13u2 → 10.46-1~deb13u3 |
| OpenSSL packages in the API image | 3.5.7-1~deb13u2 → 3.5.7-1~deb13u3 |

`uv.lock` was updated using `uv lock`; the Node lockfile using pnpm. `boto3 1.40.30` / `botocore 1.40.76` were retained: their constraints allow urllib3 2.8.0. Python checks without extras and with `--extra s3`, plus `pnpm audit --audit-level high`, returned “No known vulnerabilities found”. No vulnerabilities were excluded. The Dockerfile upgrades only four OpenSSL/PCRE packages in the pinned base image; the Trivy gate remains enabled.

The first repeated [run 36889227122](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889227122) passed audits and found fixable system HIGH findings. The next commit resolved them. The previous red [run 36885199904](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36885199904) describes the state before stabilization.

The existing backend suite, contract/E2E checks, mypy, Ruff, web lint/typecheck/build, and safety tests for the new command also passed locally. PostgreSQL verification ran in CI and was not credited from locally skipped tests. ESLint font warnings and Actions Node 20 warnings do not block jobs or require architecture changes.

### Public Golden World

An operator refresh ran on October 1 at **21:13 Asia/Qyzylorda (16:13 UTC)**: the database backup was verified using `pg_restore --list` and SHA-256, then fresh fixtures were added through normal APIs. The world retains 121 calendar days of history; six new messages form a six-hour Radar cluster. Ask Pulse RU/KK, source records, PDF/XLSX, and 30/60/90-day forecasts passed. The landing, `/demo`, and both health endpoints are accessible from the workstation. Details and the repeatable command: [PUBLIC_DEPLOYMENT](../../infra/runbooks/PUBLIC_DEPLOYMENT.en.md).

CI verifies the new dependencies and images. Running VPS images were retained: web `22d89e7` and the previous backend. This pass refreshed demo data rather than deploying new images; the green image audit is not attributed to the older containers.

## Working runtime and documentation

The demo executes FastAPI/PostgreSQL/migrations/audit/outbox/worker/Next.js; records and external receipts are synthetic. The in-memory fixture serves tests and local simulation but does not replace the public PostgreSQL demo. [FEATURE_STATUS](../submission/FEATURE_STATUS.en.md) is the current-state source of truth.

The previous documentation pass `91fd220` is documented separately and predates stabilization; its dated results are historical. Results are listed in the [documentation report](../review/DOCUMENTATION_REVIEW_2026-10-01.en.md).
