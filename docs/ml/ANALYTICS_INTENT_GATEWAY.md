# Local Ask Pulse inference

`POST /v1/inference/analytics-intent` translates a question into
`AnalyticsIntent`; it never calculates statistics or reads citizen records.
The existing `/v1/inference/classify` contract remains available.

The gateway receives a bounded question, locale, explicit reference clock and
scoped `IntentCatalog`. A constrained JSON schema limits model output to the
existing metrics and the catalog's region/topic/service IDs. Only the question,
catalog and safe clock/schema instructions reach the local model. Conversation
follow-ups use the deterministic parser without forwarding prior chat context.
The business service remains the final authorization and metric policy gate.

Unsafe SQL, PII requests, causal claims and unapproved SLA queries are refused
before inference. Ambiguous questions retain their clarification. Timeout,
HTTP failure, truncation, invalid JSON, schema violation and out-of-catalog IDs
return the CPU parser result. Raw questions, model output and records are never
added to logs, traces or error envelopes. Redirects and proxy environment
variables are disabled for model HTTP requests.

## Registry

`ml/registry/analytics_intent_registry.json` ships with no model or alias. This
honestly selects the baseline until real immutable artifacts and approval are
supplied. `analytics_intent_candidates.json` names Qwen and Gemma proposals;
all pins, quality and approvals remain absent. No weights are downloaded.
The Qwen proposal is identified by its author's
[Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).
The model card is not local municipal RU/KK evaluation evidence.

Each registered model requires an immutable model revision, tokenizer revision,
artifact SHA-256, runtime/version, quantization, prompt/schema versions and a
private endpoint. `champion` and `rollback` require an approval reference and an
evaluation reference over approved questions. Synthetic contract reports cannot
approve them. `challenger` may reference an evaluation artifact and is only used
when explicitly requested in offline comparisons. The core requests `champion`.

Endpoints accept loopback, RFC1918/unique-local addresses or private single-label
service names. Deploy those names on the approved private network; do not map
them to an external host. The gateway re-reads the registry for each request.
Publish registry replacements atomically and keep the previous file for rollback.

Explicit human approval can prepare a replacement file after health and exact
served-model ID checks:

```powershell
$env:PYTHONPATH = "services/core/src;services/inference/src"
uv run python -m pulse109_inference.analytics_registry_cli --registry active.json --action promote --approval-ref approved-change-reference --output reviewed-next.json
uv run python -m pulse109_inference.analytics_registry_cli --registry active.json --action rollback --approval-ref approved-rollback-reference --output reviewed-rollback.json
```

The CLI refuses to overwrite files and does not publish the replacement. Its
approval reference records an existing human decision; the command does not
create approval or model quality evidence. Health verifies the endpoint's model
identifier, while artifact/revision correctness still requires deployment review.

## Optional model server

Use `infra/compose/docker-compose.analytics-llm.yml` with the normal Compose
stack and the `analytics-llm` profile. Supply a reviewed vLLM image **by digest**,
an approved local artifact directory, served model ID and registry file. This
overlay uses one GPU, publishes no model-server port, mounts artifacts read-only,
disables request logging and sets Hub/Transformers offline mode. Runtime and
quantization must match the artifact evaluated and listed in the registry.
There is no default image digest or fabricated model revision.

The gateway uses `response_format.type=json_schema`, documented by the official
[vLLM structured-output API](https://docs.vllm.ai/en/v0.21.0/features/structured_outputs/)
and its [current source documentation](https://github.com/vllm-project/vllm/blob/main/docs/features/structured_outputs.md).
Confirm API compatibility of the reviewed runtime before deployment. Default
inference readiness still reports `no-model-loaded`; a CPU fallback is ready
even when the optional GPU server is unavailable.

## Frozen contract checks

```powershell
$env:PYTHONPATH = "services/core/src;services/inference/src"
uv run python -m ml.evaluation.analytics_intent_benchmark --alias baseline --output contract-report.json
uv run python -m ml.evaluation.analytics_intent_benchmark --alias challenger --registry reviewed-registry.json --output challenger-contract-report.json
```

The frozen fixture includes RU, KK, mixed, adversarial and ambiguous questions,
an explicit clock and SHA-256 cohort pin. Reports show expected-field agreement,
schema validity, refusals, fallback metadata and measured local latency. They are
labelled `synthetic_contract_only`, set `model_quality` and VRAM to null and must
never be used as measured RU/KK model quality, capacity or promotion evidence.
Reported token counts come from the runtime; missing counts remain null.

B01/B06 authoritative catalogs, B08 approved private hosting/identity profile,
B09 GPU capacity and real approved RU/KK evaluation remain visible prerequisites.
This instruction parser does not replace the classifier or retrieval models.
