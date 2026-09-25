"""Record append-only, version-bound advisory Decision Gateway assessments."""

from alembic import op

revision = "0019_m8_gateway_assessment"
down_revision = "0018_m8_unit_org_crosswalk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE triage.recommendation
            ADD CONSTRAINT recommendation_assessment_identity_unique
            UNIQUE (recommendation_id, request_id, request_version);

        CREATE TABLE triage.gateway_assessment (
            assessment_id uuid PRIMARY KEY,
            request_id uuid NOT NULL,
            region_id varchar(32) NOT NULL,
            request_version bigint NOT NULL CHECK (request_version > 0),
            recommendation_id uuid NOT NULL,
            policy_version varchar(64),
            decision varchar(32) NOT NULL CHECK (
                decision IN ('REVIEW_REQUIRED', 'INSUFFICIENT_DATA', 'OUT_OF_DOMAIN')
            ),
            input_sha256 char(64) NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
            evidence_sha256 char(64) NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
            result jsonb NOT NULL CHECK (
                jsonb_typeof(result) = 'object'
                AND result @> '{"requires_human_confirmation":true,
                                 "assigned_organization_id":null}'::jsonb
                AND result ? 'decision'
                AND result->>'decision' = decision
            ),
            observed_at timestamptz NOT NULL,
            correlation_id varchar(128) NOT NULL CHECK (length(btrim(correlation_id)) > 0),
            created_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (request_id, region_id)
                REFERENCES appeals.appeal(request_id, region_id),
            FOREIGN KEY (recommendation_id, request_id, request_version)
                REFERENCES triage.recommendation(recommendation_id, request_id, request_version),
            UNIQUE (request_id, request_version, recommendation_id,
                    input_sha256, evidence_sha256)
        );
        CREATE INDEX gateway_assessment_request_idx
            ON triage.gateway_assessment(region_id, request_id, observed_at DESC);
        CREATE TRIGGER gateway_assessment_append_only
            BEFORE UPDATE OR DELETE ON triage.gateway_assessment
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS triage.gateway_assessment")
    op.execute(
        "ALTER TABLE triage.recommendation "
        "DROP CONSTRAINT IF EXISTS recommendation_assessment_identity_unique"
    )
