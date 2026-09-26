"""Print the single alembic head revision, read from the migration files.

CI compares the head the database reports against the head the repository
expects. Reading it from the files rather than from alembic keeps the check
free of any database connection or alembic configuration of its own, and a
frozen revision id in the workflow cannot go stale again.

The head is the revision that no other migration lists as its down_revision.
"""

from __future__ import annotations

import pathlib
import re
import sys

VERSIONS = pathlib.Path("services/core/migrations/versions")
REVISION = re.compile(r"^revision(?::[^=]+)?\s*=\s*[\"']([^\"']+)", re.M)
DOWN = re.compile(r"^down_revision(?::[^=]+)?\s*=\s*[\"']([^\"']+)", re.M)


def main() -> int:
    revisions: set[str] = set()
    parents: set[str] = set()
    for path in VERSIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        found = REVISION.search(text)
        if found:
            revisions.add(found.group(1))
        parent = DOWN.search(text)
        if parent:
            parents.add(parent.group(1))

    heads = sorted(revisions - parents)
    if len(heads) != 1:
        print(f"expected exactly one head, found {heads}", file=sys.stderr)
        return 1
    print(heads[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
