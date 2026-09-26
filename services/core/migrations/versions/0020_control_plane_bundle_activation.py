"""Persist signed regional bundle history and the active last-known-good release."""

from alembic import op

revision = "0020_bundle_activation"
down_revision = "0019_m8_gateway_assessment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE triage.release_bundle (
            bundle_id varchar(128) NOT NULL,
            region_id varchar(128) NOT NULL,
            version bigint NOT NULL CHECK (version > 0),
            sequence bigint NOT NULL CHECK (sequence > 0),
            issued_at timestamptz NOT NULL,
            expires_at timestamptz NOT NULL CHECK (expires_at > issued_at),
            schema_version varchar(64) NOT NULL,
            signer_key_id varchar(128) NOT NULL,
            signer_signature_sha256 char(64) NOT NULL
                CHECK (signer_signature_sha256 ~ '^[0-9a-f]{64}$'),
            content jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object'),
            content_sha256 char(64) NOT NULL
                CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
            signed_envelope bytea NOT NULL
                CHECK (octet_length(signed_envelope) BETWEEN 1 AND 256000),
            activated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, bundle_id),
            UNIQUE (region_id, version),
            UNIQUE (region_id, sequence),
            UNIQUE (region_id, bundle_id, version, sequence)
        );
        CREATE TABLE triage.active_release_bundle (
            region_id varchar(128) PRIMARY KEY,
            bundle_id varchar(128) NOT NULL,
            version bigint NOT NULL CHECK (version > 0),
            sequence bigint NOT NULL CHECK (sequence > 0),
            activated_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (region_id, bundle_id, version, sequence)
                REFERENCES triage.release_bundle(region_id, bundle_id, version, sequence)
                DEFERRABLE INITIALLY DEFERRED
        );
        CREATE FUNCTION triage.reject_release_bundle_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'release bundle history is append-only'
                USING ERRCODE = '55000';
        END;
        $$;
        CREATE TRIGGER release_bundle_append_only
            BEFORE UPDATE OR DELETE ON triage.release_bundle
            FOR EACH ROW EXECUTE FUNCTION triage.reject_release_bundle_mutation();
        CREATE INDEX release_bundle_history_idx
            ON triage.release_bundle(region_id, version DESC, sequence DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS triage.active_release_bundle")
    op.execute("DROP TABLE IF EXISTS triage.release_bundle")
    op.execute("DROP FUNCTION IF EXISTS triage.reject_release_bundle_mutation()")
