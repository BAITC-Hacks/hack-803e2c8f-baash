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
    mounted = {
        (route.path, method.lower())
        for route in app.routes
        for method in getattr(route, "methods", [])
        if method.lower() in HTTP_METHODS
    }

    assert expected <= mounted
