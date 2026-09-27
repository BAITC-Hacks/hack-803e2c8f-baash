.PHONY: bootstrap format lint typecheck test contract-test e2e build up down migrate eda dq-report model-eval retrieval-eval mlops-eval load-test release-evidence

bootstrap:
	uv sync --all-groups --frozen
	pnpm install --frozen-lockfile

format:
	uv run ruff format .
	uv run ruff check --fix .
	pnpm format

lint:
	uv run ruff format --check .
	uv run ruff check .
	pnpm format:check
	pnpm lint

typecheck:
	uv run mypy
	pnpm typecheck

test:
	uv run python -m pytest services/core/tests services/inference/tests services/worker/tests adapters/replay/tests adapters/open311/tests adapters/regional_csv/tests tests/architecture tests/integration tests/load tests/model tests/retrieval tests/resilience tests/security -q

contract-test:
	uv run pytest tests/contract -q

e2e:
	uv run pytest tests/e2e -q

build:
	uv build
	pnpm build

up:
	docker compose -f infra/compose/docker-compose.yml up --build -d

down:
	docker compose -f infra/compose/docker-compose.yml down

migrate:
	uv run alembic -c services/core/alembic.ini upgrade head

eda:
	# Runs against the committed synthetic fixture by default. Point INPUT at an
	# approved canonical dataset outside the repository for the real thing, which
	# is where real records stay.
	uv run python -m analytics.offline.report --input $(or $(INPUT),data/reports/synthetic-m1-accepted.jsonl) --output $(or $(OUTPUT),data/reports/eda) $(if $(INPUT),,--synthetic)

dq-report:
	uv run pulse109-ingest data/fixtures/synthetic/import_batch.jsonl --manifest data/manifests/synthetic-m1.json --schema contracts/canonical_request.schema.json --accepted data/reports/synthetic-m1-accepted.jsonl --quarantine data/reports/synthetic-m1-quarantine.jsonl --report data/reports/synthetic-m1-dq-report.json

model-eval:
	uv run python -m ml.training.synthetic_baseline --manifest ml/datasets/synthetic_m3_manifest.json --output-dir ml/evaluation/synthetic_m3

retrieval-eval:
	uv run python -m ml.evaluation.m4_retrieval_eval --output ml/evaluation/synthetic_m4/retrieval_report.json

mlops-eval:
	uv run python -m ml.evaluation.synthetic_mlop --output-dir ml/evaluation/synthetic_mlop

load-test:
	uv run python -m tests.load.run_synthetic_load --requests 100 --concurrency 10 --output release/evidence/synthetic-load.json

release-evidence:
	uv run python scripts/release_evidence.py --output release/evidence-index.json
