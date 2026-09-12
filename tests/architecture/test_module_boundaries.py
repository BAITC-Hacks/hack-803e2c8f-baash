from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_required_process_scaffolds_exist() -> None:
    for path in (
        "apps/web/app/page.tsx",
        "services/worker/src/pulse109_worker/main.py",
        "services/inference/src/pulse109_inference/main.py",
        "adapters/replay/src/pulse109_replay/main.py",
        "adapters/sdk/__init__.py",
    ):
        assert (ROOT / path).is_file(), path


def test_adapter_boundary_does_not_import_core() -> None:
    for path in (ROOT / "adapters").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "pulse109.appeals" not in text
        assert "services.core" not in text


def test_compose_declares_failure_boundaries() -> None:
    compose = (ROOT / "infra/compose/docker-compose.yml").read_text(encoding="utf-8")
    for service in (
        "postgres",
        "minio",
        "core-api",
        "web",
        "worker",
        "inference",
        "adapter-runtime",
    ):
        assert f"  {service}:" in compose
