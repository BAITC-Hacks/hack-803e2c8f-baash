"""Stage immutable confidence proposals and independent review decisions."""

from alembic import op

revision = "0015_m8_confidence_publication"
down_revision = "0014_m8_confidence_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS btree_gist;
        ALTER TABLE triage.confidence_policy_version
            ADD CONSTRAINT confidence_policy_no_approved_overlap
            EXCLUDE USING gist (
                region_id WITH =,
                artifact_sha256 WITH =,
                taxonomy_version WITH =,
                preprocess_version WITH =,
                tstzrange(effective_from, effective_to, '[)') WITH &&
            ) WHERE (state = 'approved');

        CREATE TABLE triage.confidence_policy_proposal (
            proposal_id uuid PRIMARY KEY,
            region_id varchar(32) NOT NULL CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$'),
            artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
            taxonomy_version varchar(64) NOT NULL,
            preprocess_version varchar(64) NOT NULL,
            version varchar(64) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            high_min numeric(6,5) NOT NULL,
            medium_min numeric(6,5) NOT NULL,
            abstain_below numeric(6,5) NOT NULL,
            source_ref varchar(72) NOT NULL CHECK (source_ref ~ '^sha256:[0-9a-f]{64}$'),
            author_token varchar(256) NOT NULL,
            synthetic_only boolean NOT NULL,
            idempotency_key varchar(128) NOT NULL,
            request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
            correlation_id varchar(128) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (region_id, idempotency_key),
            UNIQUE (proposal_id, region_id),
            CHECK (taxonomy_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'),
            CHECK (preprocess_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'),
            CHECK (length(btrim(version)) > 0),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (high_min BETWEEN 0 AND 1),
            CHECK (medium_min BETWEEN 0 AND 1),
            CHECK (abstain_below BETWEEN 0 AND 1),
            CHECK (high_min >= medium_min AND medium_min >= abstain_below)
        );
        CREATE INDEX confidence_proposal_context_idx
            ON triage.confidence_policy_proposal
            (region_id, artifact_sha256, taxonomy_version, preprocess_version, version);
        CREATE TRIGGER confidence_proposal_append_only
            BEFORE UPDATE OR DELETE ON triage.confidence_policy_proposal
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();

        CREATE TABLE triage.confidence_policy_review (
            review_id uuid PRIMARY KEY,
            proposal_id uuid NOT NULL UNIQUE,
            region_id varchar(32) NOT NULL CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$'),
            decision varchar(16) NOT NULL CHECK (decision IN ('approve', 'reject')),
            reviewer_token varchar(256) NOT NULL,
            reason_code varchar(64) NOT NULL CHECK (reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'),
            approval_ref varchar(72) CHECK (approval_ref ~ '^sha256:[0-9a-f]{64}$'),
            policy_id uuid REFERENCES triage.confidence_policy_version(policy_id),
            idempotency_key varchar(128) NOT NULL,
            request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
            correlation_id varchar(128) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (proposal_id, region_id)
                REFERENCES triage.confidence_policy_proposal(proposal_id, region_id),
            UNIQUE (region_id, idempotency_key),
            CHECK ((decision = 'approve') = (approval_ref IS NOT NULL AND policy_id IS NOT NULL))
        );
        CREATE INDEX confidence_review_region_idx
            ON triage.confidence_policy_review (region_id, created_at DESC);
        CREATE FUNCTION triage.enforce_confidence_review() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            proposal triage.confidence_policy_proposal%ROWTYPE;
        BEGIN
            SELECT * INTO proposal FROM triage.confidence_policy_proposal
            WHERE proposal_id = NEW.proposal_id AND region_id = NEW.region_id;
            IF NOT FOUND OR proposal.author_token = NEW.reviewer_token THEN
                RAISE EXCEPTION 'independent regional review required' USING ERRCODE = '23514';
            END IF;
            IF NEW.decision = 'approve' AND NOT EXISTS (
                SELECT 1 FROM triage.confidence_policy_version AS p
                WHERE p.policy_id = NEW.policy_id AND p.region_id = proposal.region_id
                  AND p.artifact_sha256 = proposal.artifact_sha256
                  AND p.taxonomy_version = proposal.taxonomy_version
                  AND p.preprocess_version = proposal.preprocess_version
                  AND p.version = proposal.version
                  AND p.effective_from = proposal.effective_from
                  AND p.effective_to IS NOT DISTINCT FROM proposal.effective_to
                  AND p.high_min = proposal.high_min
                  AND p.medium_min = proposal.medium_min
                  AND p.abstain_below = proposal.abstain_below
                  AND p.source_ref = proposal.source_ref
                  AND p.created_by_token = proposal.author_token
                  AND p.reviewed_by_token = NEW.reviewer_token
                  AND p.approval_ref = NEW.approval_ref
                  AND p.synthetic_only = proposal.synthetic_only
                  AND p.state = 'approved'
            ) THEN
                RAISE EXCEPTION 'reviewed policy does not match proposal' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER confidence_review_integrity
            BEFORE INSERT ON triage.confidence_policy_review
            FOR EACH ROW EXECUTE FUNCTION triage.enforce_confidence_review();
        CREATE TRIGGER confidence_review_append_only
            BEFORE UPDATE OR DELETE ON triage.confidence_policy_review
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS triage.confidence_policy_review")
    op.execute("DROP TABLE IF EXISTS triage.confidence_policy_proposal")
    op.execute("DROP FUNCTION IF EXISTS triage.enforce_confidence_review()")
    op.execute(
        "ALTER TABLE triage.confidence_policy_version "
        "DROP CONSTRAINT IF EXISTS confidence_policy_no_approved_overlap"
    )
