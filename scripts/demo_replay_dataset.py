"""Seed a synthetic Replay Lab dataset and run one comparison.

Why the numbers in it are empty, on purpose.

The replay engine skips every case marked synthetic:

    for case in ordered:
        if case.is_synthetic:
            continue

That is the guardrail the whole capability exists to enforce. Synthetic traffic
must never contribute to a claim about model quality, so a demo cannot fill this
screen with agreeable percentages without breaking the one promise Replay Lab
makes.

What this seed produces instead is a real report with its real structure, in
which every metric is empty and the reason is stated: N synthetic cases present,
0 evaluated. A reviewer sees the machinery and the rule at the same time, rather
than an empty screen that looks unfinished or a full screen that lies.

Real numbers here need an approved historical sample of genuine decisions, which
is blocked on B02 (no raw appeal text) and B05 (no reassignment history).

This module is piped into the core container, which has the package but not the
repository scripts.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from pulse109.config import get_settings
from pulse109.replay.engine import (
    FeatureValue,
    ReplayCase,
    ReplayDataset,
    ReplayEngine,
    ReplayLabel,
)
from pulse109.replay.persistence import (
    ObjectStorageSnapshotStore,
    PostgresReplayRepository,
    snapshot_sha256,
)
from pulse109.security.object_storage import LocalImmutableObjectStorage

REGION = "ALA"
SEED_ACTOR = "demo-seed"
DATASET_ID = "demo-synthetic-ala-2026-09"
CASE_COUNT = 48
ROUTES = ("service:water", "service:roads", "service:utilities", "service:waste")
LANGUAGES = ("ru", "kk", "mixed")
CHANNELS = ("phone", "web", "mobile", "import")


class StaticPolicy:
    """A deterministic approved policy. No training, no state, no side effects."""

    def __init__(self, policy_id: str, version: str, *, offset: int) -> None:
        self.policy_id = policy_id
        self.version = version
        self.region_id = REGION
        self._offset = offset

    def predict(self, features: dict[str, object]) -> str:
        # Routes are derived from allowlisted pre-decision features only.
        channel = str(features.get("channel") or "web")
        language = str(features.get("language") or "ru")
        index = (len(channel) + len(language) + self._offset) % len(ROUTES)
        return ROUTES[index]


def build_dataset(now: datetime) -> ReplayDataset:
    cutoff = now - timedelta(minutes=5)
    cases: list[ReplayCase] = []
    for index in range(CASE_COUNT):
        decided_at = cutoff - timedelta(hours=index + 1)
        observed_at = decided_at - timedelta(minutes=2)
        key = hashlib.sha256(f"{DATASET_ID}:{index}".encode()).hexdigest()
        cases.append(
            ReplayCase(
                case_key=key,
                region_id=REGION,
                decision_at=decided_at,
                features={
                    "channel": FeatureValue(
                        value=CHANNELS[index % len(CHANNELS)], observed_at=observed_at
                    ),
                    "language": FeatureValue(
                        value=LANGUAGES[index % len(LANGUAGES)], observed_at=observed_at
                    ),
                    "time_quality": FeatureValue(value="exact", observed_at=observed_at),
                    "hour_bucket": FeatureValue(
                        value=f"h{decided_at.hour:02d}", observed_at=observed_at
                    ),
                },
                label=ReplayLabel(
                    confirmed_route=ROUTES[index % len(ROUTES)],
                    handoff_count=index % 3,
                    label_observed_at=decided_at + timedelta(hours=2),
                ),
                # The whole point. These cases are synthetic and the engine will
                # refuse to score them.
                is_synthetic=True,
            )
        )

    placeholder = "0" * 64
    draft = ReplayDataset(
        dataset_id=DATASET_ID,
        region_id=REGION,
        snapshot_sha256=placeholder,
        schema_version="replay-demo/1.0.0",
        cases=tuple(cases),
        allowed_features=frozenset({"channel", "language", "time_quality", "hour_bucket"}),
        cutoff_at=cutoff,
    )
    # The canonical snapshot excludes the hash field, so computing it from the
    # draft and copying it back is not circular.
    return draft.model_copy(update={"snapshot_sha256": snapshot_sha256(draft)})


def main() -> int:
    # Read the application's own settings rather than guessing an environment
    # variable name, so the seed writes exactly where the running service reads.
    settings = get_settings()
    if settings.effective_profile != "demo":
        print("refusing to seed a synthetic replay dataset outside the demo profile")
        return 1
    repository = PostgresReplayRepository(
        settings.database_url,
        ObjectStorageSnapshotStore(LocalImmutableObjectStorage(settings.replay_snapshot_dir)),
    )

    dataset = build_dataset(datetime.now(timezone.utc))
    repository.persist_dataset(dataset)

    baseline = StaticPolicy("routing-lexical", "1.0.0", offset=0)
    candidate = StaticPolicy("routing-lexical", "1.1.0", offset=1)
    report = ReplayEngine().compare(dataset, baseline, candidate)
    # An actor label, not a credential. The store records who produced a report.
    repository.persist_report(report, dataset, created_by_token=SEED_ACTOR)

    print(
        f"replay dataset {dataset.dataset_id}: {len(dataset.cases)} synthetic cases, "
        f"{report.candidate.evaluated_count} evaluated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
