[Русский](REPOSITORY_CLEANUP.md) · [English](REPOSITORY_CLEANUP.en.md) · [Қазақша](REPOSITORY_CLEANUP.kk.md)

> Historical audit of 2026-09-27. Its branch/SHA and checks describe that revision, not current main. Current status: [FEATURE_STATUS](../FEATURE_STATUS.en.md).

# Repository cleanup review

Review date: 2026-09-27. Baseline: `32951f272420932c9d044189511c5ecea6e3aec8` on `codex/production-platform-20260923`.

## Classification before cleanup

| Class            | Candidates                                                                                                                                                                                                                                     | Evidence and decision                                                                                                                                                                                                                                                                                                                                                        |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Safe to delete   | None confirmed                                                                                                                                                                                                                                 | The tracked-file SHA-256 scan found no byte-identical duplicates. No apparently dead source file was sufficiently proven unused to delete. Git history retains earlier versions, but that alone is not a reason to remove review evidence.                                                                                                                                   |
| Archive/move     | Early `START_HERE.md`, `START_CODEX_PROMPT.md`, `IMPLEMENTATION_STATUS_TEMPLATE.md`; old `DEMO_FLOW.md`, `BUSINESS_LOGIC_QUESTIONS.md`, old questions PDF; dated `PRODUCTION_ROADMAP.md`, `PRODUCTION_AUDIT.md`; source specification PDF/DOCX | The current README, demo runbook, feature matrix, and GovTech questions supersede their instructions or claims. The documents retain historical/review value, so they moved to [`docs/archive/`](../archive/README.en.md). Internal references and the documentation index were updated.                                                                                     |
| Still referenced | `CODEX_IMPLEMENTATION_HANDOFF.md`, `ACCEPTANCE_MATRIX.md`, `IMPLEMENTATION_STATUS.md`, migrations, contracts, `demo.ps1`, Compose/Docker files, synthetic datasets and ML reports, release evidence, historical decision log                   | The handoff is explicitly referenced by `AGENTS.md` and the acceptance matrix by `scripts/release_evidence.py`. Synthetic reports/model artifacts are referenced by tests, release evidence, generators or decision records. The regional corpus and quarantine artifacts are privacy-gate test inputs. Applied migrations and contracts are durable history. Kept in place. |
| Uncertain — keep | Small package `__init__.py` modules, adapter packages, older screenshots and benchmark outputs, apparently unused dependencies or TS/Python symbols                                                                                            | Dynamic imports, CLI entry points, documentation evidence and package metadata make absence of a simple import inconclusive. No unverified code or dependency pruning was done.                                                                                                                                                                                              |

## Size and reference audit

The largest tracked file is the 5.7 MB withheld regional retrieval corpus. It is intentionally redacted and asserted by `tests/security/test_research_artifact_gate.py`; removing it would weaken the privacy regression gate. The 2.1 MB specification PDF and 0.97 MB DOCX moved to the archive. The `ml/` directory is about 6.2 MB, most of it that withheld corpus; `docs/` is about 3.3 MB including the source specification. `uv.lock` and `pnpm-lock.yaml` remain reproducibility inputs. The PNG diagrams and synthetic UI screenshots are review evidence, not deployable assets to trim on appearance alone.

Checked tracked generated PDF/JSON/JSONL/PNG/joblib files, `data/reports`, `ml/evaluation`, `release/evidence-index`, Docker/Compose variants, workflow, scripts, manifests and major dependency imports. The old question PDF is archived; the current `output/pdf/govtech_business_questions.pdf` remains a requested deliverable. The base Compose file and demo override are both active, and one CI workflow was found. No redundant Docker/Compose variant or manifest was removed. No tracked WIP/scratch/temp-named file or commented-out source block warranted removal; `infra/runbooks/BACKUP_RESTORE.md` is an active runbook, not a backup copy. The active `demo.ps1` calls `scripts/demo_runtime.py`; three pre-existing untracked demo helper scripts were left untouched.

The root retains project entry points, configuration, status, contracts/acceptance references and the handoff required by `AGENTS.md`. Archiving that handoff while `AGENTS.md` has separate user changes would leave a broken repository instruction, so it remains for a later coordinated revision.

## Changes

- **Deleted:** no tracked files. Nothing met the safe-delete threshold.
- **Archived:** the ten files enumerated above, preserving Git rename history and their content.
- **Ignore/build context:** `.gitignore` now excludes common local temporary files; `.dockerignore` excludes runtime data, secrets, documentation, tests, research evidence and generated outputs that neither Dockerfile copies. It keeps source, contracts and lockfiles in context.
- **Navigation:** `docs/README.en.md` and project-journal links point to the archive; dated audit evidence in the decision log points to the new path.

No runtime capability changed, so `IMPLEMENTATION_STATUS.md` was not rewritten. This cleanup does not establish that every Python/TS module or dependency is unused; a future removal must demonstrate static and dynamic reachability, then pass its relevant tests.

## Verification

- Relative Markdown links under `docs/`: all targets resolve.
- Tracked Python files: Ruff check passed; Ruff format check reported 248 files already formatted; mypy passed 123 source files.
- Python test, contract and E2E collection: **329 passed, 21 skipped**. All skipped cases require `PULSE109_TEST_DATABASE_URL`, which was not configured on this host.
- Frontend Prettier check, ESLint, TypeScript typecheck and Next production build: passed. `uv build`: passed.
- Base plus demo Compose configuration: `docker compose ... config --quiet` passed.
- The repository-wide Ruff command also sees the pre-existing, untracked `scripts/seed_demo.py` and reports 21 issues in that unrelated file. It was neither edited nor staged for this cleanup; the tracked-file check above is the relevant clean result.
- Docker engine did not respond to `docker info` on this host, so a container build and PostgreSQL-backed checks were not asserted here. CI should run its Compose smoke and database gate after push.
