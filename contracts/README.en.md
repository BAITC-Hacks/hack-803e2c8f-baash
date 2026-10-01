[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Pulse 109 Technical Pack

This package accompanies the technical specification and architecture document.

## Contents

- `openapi.yaml`: external and internal application API baseline.
- `canonical_request.schema.json`: canonical appeal contract for regional adapters.
- `event_catalog.md`: integration event envelope, catalog and compatibility rules.
- `model_stack.md`: fixed pilot model stack, serving topology, fallbacks and promotion gates.
- `ask-pulse.schema.json` and `analytics-intent.schema.json`: versioned Ask Pulse response/export and private inference gateway JSON Schemas; `openapi.yaml` contains the operator-facing routes.
- `adr/`: decisions that keep the first production release small and replaceable.
- `diagrams/`: architecture diagrams generated from the same design used in the specification.

## Fixed decisions

1. Business modules start as a modular monolith. Model inference and background work run as separate processes because they scale and fail differently.
2. PostgreSQL, PostGIS and pgvector form the transactional and retrieval core until measured load proves the need for another database.
3. Each regional system integrates through a stable canonical contract and an isolated adapter.
4. Lifecycle history is append-only. Current state is a derived snapshot for fast reads.
5. AI proposes. A person confirms routing, priority changes, duplicate membership and generated replies.
6. Missing or ambiguous dates remain missing or ambiguous. The pipeline records time quality and never fabricates precision.
7. The pilot starts with XLM-RoBERTa, BGE-M3, BGE reranker v2 m3, Qwen3 8B and Whisper large v3 turbo behind replaceable serving contracts.

## Validation

Run these checks in CI:

```bash
python -c "import json; json.load(open('canonical_request.schema.json', encoding='utf-8'))"
python -c "import yaml; yaml.safe_load(open('openapi.yaml', encoding='utf-8'))"
```

Add an OpenAPI linter and JSON Schema contract tests in the implementation repository. Adapter tests must replay anonymized source fixtures and verify idempotency, timezone handling, quarantine behavior and round-trip status mapping.
