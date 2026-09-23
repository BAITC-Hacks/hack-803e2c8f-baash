from pathlib import Path

import yaml
from pulse109.main import app

ROOT = Path(__file__).resolve().parents[2]
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def test_runtime_mounts_every_versioned_openapi_operation() -> None:
    specification = yaml.safe_load(
        (ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8")
    )
    expected = {
        (path, method)
        for path, operations in specification["paths"].items()
        for method in operations
        if method in HTTP_METHODS
    }
    runtime = app.openapi()
    mounted = {
        (path, method)
        for path, operations in runtime["paths"].items()
        for method in operations
        if method in HTTP_METHODS
    }

    assert expected <= mounted


def test_runtime_preserves_bearer_security_for_protected_contract_operations() -> None:
    specification = yaml.safe_load(
        (ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8")
    )
    runtime = app.openapi()
    assert "bearerAuth" in runtime["components"]["securitySchemes"]
    for path, operations in specification["paths"].items():
        for method, operation in operations.items():
            if method not in HTTP_METHODS or operation.get("security") == []:
                continue
            runtime_security = runtime["paths"][path][method].get("security", [])
            assert {"bearerAuth": []} in runtime_security, (
                f"missing bearer security: {method} {path}"
            )
