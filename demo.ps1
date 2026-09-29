param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet('up', 'seed', 'verify', 'prepare', 'status', 'down', 'reset')]
  [string]$Action
)

$env:PYTHONUTF8 = '1'
uv run python scripts/demo_runtime.py $Action
exit $LASTEXITCODE
