"""Persist immutable closure preflights and human-confirmed closure receipts."""
from alembic import op

revision = "0016_m9_closure_integrity"
down_revision = "0015_m8_confidence_publication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE appeals.appeal ADD CONSTRAINT appeal_region_identity_unique UNIQUE(request_id, region_id);
        CREATE TABLE appeals.closure_preflight (
            preflight_id uuid PRIMARY KEY,
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            region_id varchar(32) NOT NULL,
            appeal_version bigint NOT NULL CHECK (appeal_version > 0),
            resolution_code varchar(64) NOT NULL CHECK (resolution_code ~ '^[A-Z][A-Z0-9_]{0,63}$'),
            evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'array' AND jsonb_array_length(evidence) BETWEEN 1 AND 50),
            evidence_hash char(64) NOT NULL CHECK (evidence_hash ~ '^[0-9a-f]{64}$'),
            created_by_token varchar(256) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            closure_id uuid UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            confirmed_at timestamptz,
            FOREIGN KEY (request_id, region_id) REFERENCES appeals.appeal(request_id, region_id)
        );
        CREATE INDEX closure_preflight_appeal_idx ON appeals.closure_preflight(request_id, created_at DESC);
        CREATE TRIGGER closure_preflight_append_only
            BEFORE DELETE ON appeals.closure_preflight
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE FUNCTION appeals.prevent_closure_preflight_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.preflight_id IS DISTINCT FROM OLD.preflight_id OR NEW.request_id IS DISTINCT FROM OLD.request_id
             OR NEW.region_id IS DISTINCT FROM OLD.region_id OR NEW.appeal_version IS DISTINCT FROM OLD.appeal_version
             OR NEW.resolution_code IS DISTINCT FROM OLD.resolution_code OR NEW.evidence IS DISTINCT FROM OLD.evidence
             OR NEW.evidence_hash IS DISTINCT FROM OLD.evidence_hash OR NEW.created_by_token IS DISTINCT FROM OLD.created_by_token
             OR NEW.correlation_id IS DISTINCT FROM OLD.correlation_id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
             RAISE EXCEPTION 'closure preflight is immutable';
          END IF;
          IF OLD.confirmed_at IS NOT NULL OR NEW.confirmed_at IS NULL OR NEW.closure_id IS NULL THEN
             RAISE EXCEPTION 'closure preflight can only be consumed once';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER closure_preflight_immutable
            BEFORE UPDATE ON appeals.closure_preflight
            FOR EACH ROW EXECUTE FUNCTION appeals.prevent_closure_preflight_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS appeals.closure_preflight")
    op.execute("ALTER TABLE appeals.appeal DROP CONSTRAINT IF EXISTS appeal_region_identity_unique")
    op.execute("DROP FUNCTION IF EXISTS appeals.prevent_closure_preflight_mutation()")
