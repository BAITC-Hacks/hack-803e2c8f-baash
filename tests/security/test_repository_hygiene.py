import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tracked_sources_do_not_contain_private_keys() -> None:
    git = shutil.which("git")
    assert git is not None
    tracked = subprocess.run(  # noqa: S603 -- executable is resolved locally, arguments are fixed.
        [git, "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    candidates = [
        ROOT / name
        for name in tracked
        if Path(name).suffix in {".py", ".ts", ".tsx", ".yml", ".yaml", ".json", ".toml"}
    ]
    marker = "BEGIN " + "PRIVATE KEY"
    assert all(
        marker not in path.read_text(encoding="utf-8", errors="ignore") for path in candidates
    )


def test_web_proxy_never_forwards_development_identity_headers() -> None:
    proxy = (ROOT / "apps/web/app/api/core/[...path]/route.ts").read_text(encoding="utf-8")
    assert "x-actor-token" not in proxy.lower()
    assert "x-actor-roles" not in proxy.lower()
    assert "x-actor-regions" not in proxy.lower()


def test_observability_does_not_capture_request_bodies() -> None:
    source = (ROOT / "services/core/src/pulse109/observability.py").read_text(encoding="utf-8")
    assert "await request.body" not in source
    assert "request.json" not in source
