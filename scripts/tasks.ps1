param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("bootstrap", "format", "lint", "typecheck", "test", "contract-test", "e2e", "build", "up", "down", "migrate", "dq-report", "model-eval", "retrieval-eval", "mlops-eval", "load-test", "release-evidence")]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command exited with code $LASTEXITCODE"
    }
}

switch ($Task) {
    "bootstrap" {
        Invoke-Checked "uv" @("sync", "--all-groups", "--frozen")
        Invoke-Checked "pnpm" @("install", "--frozen-lockfile")
    }
    "format" {
        Invoke-Checked "uv" @("run", "ruff", "format", ".")
        Invoke-Checked "uv" @("run", "ruff", "check", "--fix", ".")
        Invoke-Checked "pnpm" @("format")
    }
    "lint" {
        Invoke-Checked "uv" @("run", "ruff", "format", "--check", ".")
        Invoke-Checked "uv" @("run", "ruff", "check", ".")
        Invoke-Checked "pnpm" @("format:check")
        Invoke-Checked "pnpm" @("lint")
    }
    "typecheck" {
        Invoke-Checked "uv" @("run", "mypy")
        Invoke-Checked "pnpm" @("typecheck")
    }
    "test" {
        Invoke-Checked "uv" @("run", "python", "-m", "pytest", "services/core/tests", "services/inference/tests", "services/worker/tests", "adapters/replay/tests", "adapters/open311/tests", "adapters/regional_csv/tests", "tests/architecture", "tests/integration", "tests/load", "tests/model", "tests/retrieval", "tests/resilience", "tests/security", "-q")
    }
    "contract-test" { Invoke-Checked "uv" @("run", "pytest", "tests/contract", "-q") }
    "e2e" { Invoke-Checked "uv" @("run", "pytest", "tests/e2e", "-q") }
    "build" {
        Invoke-Checked "uv" @("build")
        Invoke-Checked "pnpm" @("build")
    }
    "up" { Invoke-Checked "docker" @("compose", "-f", "infra/compose/docker-compose.yml", "up", "--build", "-d") }
    "down" { Invoke-Checked "docker" @("compose", "-f", "infra/compose/docker-compose.yml", "down") }
    "migrate" { Invoke-Checked "uv" @("run", "alembic", "-c", "services/core/alembic.ini", "upgrade", "head") }
    "dq-report" { Invoke-Checked "uv" @("run", "pulse109-ingest", "data/fixtures/synthetic/import_batch.jsonl", "--manifest", "data/manifests/synthetic-m1.json", "--schema", "contracts/canonical_request.schema.json", "--accepted", "data/reports/synthetic-m1-accepted.jsonl", "--quarantine", "data/reports/synthetic-m1-quarantine.jsonl", "--report", "data/reports/synthetic-m1-dq-report.json") }
    "model-eval" { Invoke-Checked "uv" @("run", "python", "-m", "ml.training.synthetic_baseline", "--manifest", "ml/datasets/synthetic_m3_manifest.json", "--output-dir", "ml/evaluation/synthetic_m3") }
    "retrieval-eval" { Invoke-Checked "uv" @("run", "python", "-m", "ml.evaluation.m4_retrieval_eval", "--output", "ml/evaluation/synthetic_m4/retrieval_report.json") }
    "mlops-eval" { Invoke-Checked "uv" @("run", "python", "-m", "ml.evaluation.synthetic_mlop", "--output-dir", "ml/evaluation/synthetic_mlop") }
    "load-test" { Invoke-Checked "uv" @("run", "python", "-m", "tests.load.run_synthetic_load", "--requests", "100", "--concurrency", "10", "--output", "release/evidence/synthetic-load.json") }
    "release-evidence" { Invoke-Checked "uv" @("run", "python", "scripts/release_evidence.py", "--output", "release/evidence-index.json") }
}
