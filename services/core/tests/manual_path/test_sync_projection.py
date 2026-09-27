"""The outbox vocabulary and the operator-facing one must not drift apart.

A partial projection used to pass unmapped values straight to pydantic, so
reading an appeal returned 500 the moment the worker published its outbox
entry. That is the normal delivery path, not an edge case.
"""

import pathlib
import re

import pytest
from pulse109.manual_path.models import SyncState
from pulse109.manual_path.service import (
    OUTBOX_SYNC_STATUS,
    ManualPathError,
    sync_status_from_outbox,
)

MIGRATION = (
    pathlib.Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "0002_m1_data_foundation.py"
)


def outbox_statuses_from_migration() -> set[str]:
    """Read the CHECK constraint that defines the storage vocabulary."""
    text = MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        r"status varchar\(32\) NOT NULL DEFAULT 'pending' CHECK \(status IN \(([^)]+)\)\)",
        text,
    )
    assert match, "outbox status CHECK constraint not found in migration 0002"
    return set(re.findall(r"'([a-z_]+)'", match.group(1)))


def test_projection_covers_every_stored_status():
    assert outbox_statuses_from_migration() == set(OUTBOX_SYNC_STATUS)


@pytest.mark.parametrize(
    ("stored", "reported"),
    [
        ("pending", "queued"),
        ("processing", "queued"),
        ("published", "delivered"),
        ("retrying", "retrying"),
        ("dead_letter", "failed_permanent"),
    ],
)
def test_every_stored_status_builds_a_valid_sync_state(stored, reported):
    assert sync_status_from_outbox(stored) == reported
    assert SyncState(status=sync_status_from_outbox(stored)).status == reported


def test_unknown_status_fails_closed():
    with pytest.raises(ManualPathError) as raised:
        sync_status_from_outbox("teleported")
    assert raised.value.code == "unknown_outbox_status"
    assert raised.value.status_code == 503
