"""Build a deterministic hash index for release-candidate evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    "contracts/openapi.yaml",
    "contracts/canonical_request.schema.json",
    "contracts/inference.schema.json",
    "data/reports/synthetic-m1-dq-report.json",
    "ml/evaluation/synthetic_m3/metrics.json",
    "ml/evaluation/synthetic_m4/retrieval_report.json",
    "ml/evaluation/synthetic_mlop/evidence_manifest.json",
    "release/evidence/synthetic-load.json",
    "uv.lock",
    "pnpm-lock.yaml",
)


def _markdown(index: dict[str, object]) -> str:
    files = index["files"]
    assert isinstance(files, list)
    lines = [
        "# Pulse 109 Release Evidence Index",
        "",
        "> Synthetic pilot evidence only. This index is not a production approval.",
        "",
        f"- Git commit: `{index['git_commit']}`",
        f"- Generated at: `{index['generated_at']}`",
        "- Migration head: `0011_m7_incident_persistence`",
        "- API contract: OpenAPI 3.1, 20 operations, 29 schemas",
        "- Signature: **unsigned** — release signing identity remains an external approval",
        "- Container digest: unavailable until the container CI/build environment runs",
        "",
        "## Immutable evidence hashes",
        "",
        "| Artifact | Bytes | SHA-256 |",
        "| --- | ---: | --- |",
    ]
    for item in files:
        assert isinstance(item, dict)
        lines.append(
            f"| [{item['path']}](../{item['path']}) | {item['bytes']} | `{item['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Verification and operating evidence",
            "",
            "- [Implementation status](../IMPLEMENTATION_STATUS.md)",
            "- [Acceptance matrix](../ACCEPTANCE_MATRIX.md)",
            "- [Failure-mode demonstration](../infra/runbooks/FAILURE_MODE_DEMO.md)",
            "- [Backup and restore drill](../infra/runbooks/BACKUP_RESTORE.md)",
            "- [Model and policy rollback](../infra/runbooks/MODEL_POLICY_ROLLBACK.md)",
            "- [Security and privacy gate](../infra/runbooks/SECURITY_PRIVACY.md)",
            "- [Release rehearsal](../infra/runbooks/RELEASE_REHEARSAL.md)",
            "- [External blockers](../DECISIONS_AND_BLOCKERS.md)",
            "",
            "The release owner must add CI test reports, image digest, vulnerability scan/SBOM, "
            "restore timing, and an approved signature before a production release.",
            "",
        ]
    )
    return "\n".join(lines)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_index() -> dict[str, object]:
    files = []
    missing = []
    for relative in EVIDENCE:
        path = ROOT / relative
        if path.exists():
            files.append({"path": relative, "sha256": _hash(path), "bytes": path.stat().st_size})
        else:
            missing.append(relative)
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required for release evidence")
    commit = subprocess.run(  # noqa: S603 -- executable is resolved locally, arguments are fixed.
        [git, "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "schema_version": "pulse109-release-evidence/1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "synthetic_only": True,
        "files": files,
        "missing": missing,
        "complete": not missing,
        "signature": {
            "state": "unsigned",
            "reason": "release signing identity is an external approval",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    index = build_index()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output = args.markdown_output or output.with_suffix(".md")
    if not markdown_output.is_absolute():
        markdown_output = ROOT / markdown_output
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_markdown(index), encoding="utf-8")
    if not index["complete"]:
        raise SystemExit(f"missing release evidence: {index['missing']}")


if __name__ == "__main__":
    main()
