.PHONY: bootstrap format lint typecheck test contract-test e2e build up down migrate dq-report model-eval

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
	uv run pytest services/core/tests services/inference/tests services/worker/tests adapters/replay/tests tests/architecture tests/integration tests/model -q

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

dq-report:
	uv run pulse109-ingest data/fixtures/synthetic/import_batch.jsonl --manifest data/manifests/synthetic-m1.json --schema contracts/canonical_request.schema.json --accepted data/reports/synthetic-m1-accepted.jsonl --quarantine data/reports/synthetic-m1-quarantine.jsonl --report data/reports/synthetic-m1-dq-report.json

model-eval:
	uv run python -m ml.training.synthetic_baseline --manifest ml/datasets/synthetic_m3_manifest.json --output-dir ml/evaluation/synthetic_m3
