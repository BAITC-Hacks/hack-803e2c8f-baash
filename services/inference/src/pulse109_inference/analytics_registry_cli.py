"""Prepare a health-checked alias replacement after explicit operator approval."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Literal, cast

import httpx

from .analytics_registry import AnalyticsModelRegistry, prepare_alias_change


async def _prepare(args: argparse.Namespace) -> AnalyticsModelRegistry:
    registry = AnalyticsModelRegistry.load(Path(args.registry))
    async with httpx.AsyncClient(timeout=5.0, trust_env=False, follow_redirects=False) as client:
        updated = await prepare_alias_change(
            registry,
            action=cast(Literal["promote", "rollback"], args.action),
            approval_ref=args.approval_ref,
            client=client,
        )
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--action", choices=("promote", "rollback"), required=True)
    parser.add_argument("--approval-ref", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        updated = asyncio.run(_prepare(args))
        # Never overwrite a previously reviewed registry or the active registry.
        with Path(args.output).open("x", encoding="utf-8") as output:
            output.write(updated.model_dump_json(indent=2) + "\n")
    except (ValueError, OSError):
        parser.exit(
            1, "Alias change was not prepared: check pinned references, approval and health.\n"
        )


if __name__ == "__main__":
    main()
