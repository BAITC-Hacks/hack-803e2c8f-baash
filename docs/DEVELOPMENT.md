# Development and verification

The [product README](../README.md) contains the judge-facing route. This page keeps the local checks and CI details.

## Local checks

From the repository root:

```bash
make lint typecheck test contract-test e2e
make eda
uv run python scripts/demo_runtime.py prepare
```

`prepare` builds the real demo profile, exercises the API path, resets only the `pulse109-demo` volumes, seeds a fresh synthetic world and verifies the Golden Demo checks. Its success marker is `PULSE 109 DEMO READY`. See the [runbook](DEMO_RUNBOOK.md) for ports, operating-system commands and failure boundaries.

PostgreSQL integration tests require `PULSE109_TEST_DATABASE_URL`. A pytest skip without that variable is not a passing integration test. Use the isolated runner for repeated verification:

```bash
PULSE109_TEST_DATABASE_URL=postgresql://<role>:<password>@<host>:5432/<any-existing-db> \
  uv run python scripts/run_integration_tests.py --runs 2
```

The database role needs permission to create and drop the runner's UUID-named test databases. The runner leaves the configured base database and demo database untouched.

## CI

The workflow has four jobs: quality, a containerised stack smoke with a restore drill, a demo-profile smoke and a supply-chain audit. The second integration pass checks repeatability. See the [workflow](../.github/workflows/ci.yml) for exact commands and gates.

As observed on the BAITC-Hacks mirror when the previous English README was written, GitHub Actions reported `The job was not started because your account is locked due to a billing issue`. Those jobs did not execute, so a red badge there is not a test result. A development-repository [passing run](https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36299408363) is historical evidence for that revision, not proof that the current checkout has passed CI.

## Runtime boundaries

The demo runs FastAPI, PostgreSQL, migrations, worker, outbox, audit and Next.js with synthetic municipal records. The external replay adapter is deterministic. `PULSE109_PROFILE=demo` must report a ready PostgreSQL database before seeding; the in-memory repository is for tests, not a fallback demo. The [feature matrix](FEATURE_STATUS.md) records the remaining production dependencies.
