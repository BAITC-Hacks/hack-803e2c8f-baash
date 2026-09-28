"""Regenerate additive Ask Pulse schemas without rewriting existing contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "services/core/src"), str(ROOT / "services/inference/src")]

from pulse109.analytics.ask_models import (  # noqa: E402
    AskDrilldownRequest,
    AskExportRequest,
    AskRequest,
    AskResponse,
)
from pulse109.datalab.models import Drilldown  # noqa: E402
from pulse109_inference.analytics_intent import (  # noqa: E402
    AnalyticsIntentRequest,
    AnalyticsIntentResponse,
)


def schemas(models: list[type[BaseModel]]) -> dict[str, Any]:
    collected: dict[str, Any] = {}
    for model in models:
        document = model.model_json_schema()
        collected.update(document.pop("$defs", {}))
        collected[model.__name__] = document
    return collected


def main() -> None:
    ask = schemas([AskRequest, AskResponse, AskExportRequest, AskDrilldownRequest, Drilldown])
    inference = schemas([AnalyticsIntentRequest, AnalyticsIntentResponse])
    for filename, definitions in (
        ("ask-pulse.schema.json", ask),
        ("analytics-intent.schema.json", inference),
    ):
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": definitions}
        (ROOT / "contracts" / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    names = {name: name if name.startswith("Ask") else f"Ask{name}" for name in ask}
    names.update({name: f"Inference{name}" for name in inference})
    all_schemas = {**ask, **inference}

    # Definitions are shared structurally; use one deterministic namespace.
    def replace_refs(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: f"#/components/schemas/{names[item.rsplit('/', 1)[-1]]}"
                if key == "$ref" and isinstance(item, str) and item.startswith("#/$defs/")
                else replace_refs(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [replace_refs(item) for item in value]
        return value

    definitions = {names[name]: replace_refs(value) for name, value in all_schemas.items()}
    path = ROOT / "contracts/openapi.yaml"
    source = path.read_text(encoding="utf-8")
    start_marker, end_marker = "  # BEGIN ASK PULSE PATHS\n", "  # END ASK PULSE PATHS\n"
    if start_marker in source:
        first = source.index(start_marker)
        last = source.index(end_marker, first) + len(end_marker)
        source = source[:first] + source[last:]
    paths: dict[str, Any] = {}
    for route, operation_id, request, response, description in (
        (
            "/v1/analytics/ask",
            "askPulse",
            "AskRequest",
            "AskResponse",
            "Governed RU/KK question; returns numbers, chart, provenance or clarification.",
        ),
        (
            "/v1/analytics/ask/drilldown",
            "drilldownAskPulse",
            "AskDrilldownRequest",
            names["Drilldown"],
            "Appeals behind a signed validated query, with the original scope.",
        ),
        (
            "/v1/inference/analytics-intent",
            "parseAnalyticsIntent",
            names["AnalyticsIntentRequest"],
            names["AnalyticsIntentResponse"],
            "Internal local inference gateway; receives no citizen records.",
        ),
    ):
        paths[route] = {
            "post": {
                "tags": ["Analytics"],
                "summary": description,
                "operationId": operation_id,
                "security": [{"bearerAuth": []}],
                "parameters": [{"$ref": "#/components/parameters/RegionId"}]
                if "/inference/" not in route
                else [],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {"schema": {"$ref": f"#/components/schemas/{request}"}}
                    },
                },
                "responses": {
                    "200": {
                        "description": description,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{response}"}
                            }
                        },
                    },
                    "422": {"$ref": "#/components/responses/Unprocessable"},
                    "503": {"$ref": "#/components/responses/ServiceUnavailable"},
                },
            }
        }
    paths["/v1/analytics/ask/export"] = {
        "post": {
            "tags": ["Reports"],
            "summary": "Export the signed displayed aggregate snapshot as PDF or XLSX",
            "operationId": "exportAskPulse",
            "security": [{"bearerAuth": []}],
            "parameters": [
                {"$ref": "#/components/parameters/RegionId"},
                {
                    "name": "X-Export-Purpose",
                    "in": "header",
                    "schema": {"type": "string", "maxLength": 256},
                },
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/AskExportRequest"}
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Authenticated snapshot artifact",
                    "content": {
                        "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                            "schema": {"type": "string", "format": "binary"}
                        },
                    },
                },
                "403": {"$ref": "#/components/responses/Forbidden"},
                "422": {"$ref": "#/components/responses/Unprocessable"},
                "503": {"$ref": "#/components/responses/ServiceUnavailable"},
            },
        }
    }
    # The inference gateway is a separate server and is documented in its JSON
    # schema; the core OpenAPI remains the core application's mounted surface.
    paths.pop("/v1/inference/analytics-intent")
    block = yaml.safe_dump(paths, allow_unicode=True, sort_keys=False, width=100)
    source = source.replace(
        "components:\n",
        start_marker
        + "".join("  " + line + "\n" for line in block.splitlines())
        + end_marker
        + "components:\n",
        1,
    )
    schema_marker = "    # BEGIN ASK PULSE SCHEMAS\n"
    if schema_marker in source:
        source = source[: source.index(schema_marker)]
    block = yaml.safe_dump(definitions, allow_unicode=True, sort_keys=True, width=100)
    source = (
        source.rstrip()
        + "\n"
        + schema_marker
        + "".join("    " + line + "\n" for line in block.splitlines())
    )
    path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
