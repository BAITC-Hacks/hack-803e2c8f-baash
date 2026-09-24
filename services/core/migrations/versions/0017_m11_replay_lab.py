"""Store immutable replay manifests and aggregate comparison evidence."""

from alembic import op

revision = "0017_m11_replay_lab"
down_revision = "0016_m9_closure_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS replay;
        CREATE TABLE replay.dataset_manifest (
            dataset_id varchar(128) PRIMARY KEY,
            region_id varchar(32) NOT NULL CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$'),
            snapshot_sha256 char(64) NOT NULL CHECK (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
            schema_version varchar(64) NOT NULL,
            cutoff_at timestamptz NOT NULL,
            feature_allowlist text[] NOT NULL CHECK (cardinality(feature_allowlist) > 0),
            case_count bigint NOT NULL CHECK (case_count > 0),
            synthetic_case_count bigint NOT NULL CHECK (
                synthetic_case_count >= 0 AND synthetic_case_count <= case_count
            ),
            eligible_real_case_count bigint NOT NULL CHECK (
                eligible_real_case_count = case_count - synthetic_case_count
            ),
            immutable_snapshot_ref varchar(71) NOT NULL CHECK (
                immutable_snapshot_ref ~ '^sha256:[0-9a-f]{64}$'
            ),
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (immutable_snapshot_ref = 'sha256:' || snapshot_sha256),
            UNIQUE(snapshot_sha256, schema_version)
        );
        CREATE INDEX replay_dataset_region_idx ON replay.dataset_manifest(region_id, cutoff_at DESC);
        CREATE TABLE replay.comparison_run (
            report_id char(64) PRIMARY KEY CHECK (report_id ~ '^[0-9a-f]{64}$'),
            dataset_id varchar(128) NOT NULL REFERENCES replay.dataset_manifest(dataset_id),
            baseline_policy_id varchar(128) NOT NULL,
            baseline_version varchar(128) NOT NULL,
            candidate_policy_id varchar(128) NOT NULL,
            candidate_version varchar(128) NOT NULL,
            metrics jsonb NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
            created_by_token varchar(256) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            promoted boolean NOT NULL DEFAULT false CHECK (promoted = false),
            CHECK ((baseline_policy_id, baseline_version) <> (candidate_policy_id, candidate_version))
        );
        CREATE INDEX replay_run_dataset_created_idx
            ON replay.comparison_run(dataset_id, created_at DESC, report_id);
        CREATE TRIGGER replay_dataset_append_only
            BEFORE UPDATE OR DELETE ON replay.dataset_manifest
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER replay_run_append_only
            BEFORE UPDATE OR DELETE ON replay.comparison_run
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS replay CASCADE")
