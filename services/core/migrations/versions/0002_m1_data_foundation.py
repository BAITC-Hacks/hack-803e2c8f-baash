"""Create M1 ingestion, appeal, privacy, audit and outbox tables."""

from alembic import op

revision = "0002_m1_data_foundation"
down_revision = "0001_extensions_and_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE integration.source_system (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            system_code varchar(64) NOT NULL UNIQUE,
            display_name varchar(256) NOT NULL,
            region_id varchar(32) NOT NULL,
            adapter_id varchar(128) NOT NULL,
            adapter_version varchar(64) NOT NULL,
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE integration.source_schema_version (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            version varchar(64) NOT NULL,
            contract_version varchar(64) NOT NULL,
            mapping_version varchar(64) NOT NULL,
            schema_hash char(64) NOT NULL CHECK (schema_hash ~ '^[0-9a-fA-F]{64}$'),
            status varchar(32) NOT NULL CHECK (status IN ('approved', 'review', 'quarantined', 'retired')),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            UNIQUE (source_system_id, version)
        );
        CREATE INDEX source_schema_effective_idx ON integration.source_schema_version
            (source_system_id, effective_from DESC);

        CREATE TABLE integration.import_run (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            region_id varchar(32) NOT NULL,
            export_id varchar(256),
            source_file_ref text,
            source_checksum char(64) CHECK (source_checksum IS NULL OR source_checksum ~ '^[0-9a-fA-F]{64}$'),
            parser_version varchar(64) NOT NULL,
            mapping_version varchar(64) NOT NULL,
            row_count bigint NOT NULL DEFAULT 0 CHECK (row_count >= 0),
            accepted_count bigint NOT NULL DEFAULT 0 CHECK (accepted_count >= 0),
            warning_count bigint NOT NULL DEFAULT 0 CHECK (warning_count >= 0),
            quarantined_count bigint NOT NULL DEFAULT 0 CHECK (quarantined_count >= 0),
            duplicate_count bigint NOT NULL DEFAULT 0 CHECK (duplicate_count >= 0),
            data_cutoff timestamptz,
            observed_at timestamptz NOT NULL,
            status varchar(32) NOT NULL CHECK (status IN ('received', 'validated', 'completed', 'failed')),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (source_system_id, export_id),
            UNIQUE (source_system_id, source_checksum)
        );

        CREATE TABLE integration.source_record (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            import_run_id uuid NOT NULL REFERENCES integration.import_run(id),
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            source_schema_version_id uuid REFERENCES integration.source_schema_version(id),
            source_request_id varchar(128) NOT NULL,
            source_row_ref varchar(256),
            raw_payload_ref text NOT NULL,
            raw_payload_hash char(64) NOT NULL CHECK (raw_payload_hash ~ '^[0-9a-fA-F]{64}$'),
            raw_payload_size bigint CHECK (raw_payload_size IS NULL OR raw_payload_size >= 0),
            canonical_payload jsonb,
            validation_status varchar(32) NOT NULL CHECK (validation_status IN ('accepted', 'accepted_with_warnings', 'quarantined')),
            occurred_at timestamptz,
            observed_at timestamptz NOT NULL,
            source_timezone varchar(64),
            time_quality varchar(32) NOT NULL CHECK (time_quality IN ('exact', 'source_tz_assumed', 'date_only', 'missing')),
            CHECK (occurred_at IS NOT NULL OR time_quality IN ('missing', 'date_only')),
            CHECK (time_quality <> 'source_tz_assumed' OR source_timezone IS NOT NULL),
            UNIQUE (source_system_id, source_request_id),
            UNIQUE (import_run_id, source_row_ref)
        );
        CREATE INDEX source_record_observed_idx ON integration.source_record
            (source_system_id, observed_at DESC);
        CREATE INDEX source_record_import_idx ON integration.source_record (import_run_id);

        CREATE TABLE integration.quarantine_record (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_record_id uuid REFERENCES integration.source_record(id),
            import_run_id uuid NOT NULL REFERENCES integration.import_run(id),
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            source_row_ref varchar(256),
            raw_payload_ref text NOT NULL,
            raw_payload_hash char(64) NOT NULL CHECK (raw_payload_hash ~ '^[0-9a-fA-F]{64}$'),
            error_code varchar(128) NOT NULL,
            error_detail text,
            status varchar(32) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted', 'rejected', 'needs_mapping_review')),
            reviewed_by_token varchar(256),
            reviewed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK ((reviewed_at IS NULL AND reviewed_by_token IS NULL) OR (reviewed_at IS NOT NULL AND reviewed_by_token IS NOT NULL)),
            UNIQUE (import_run_id, source_row_ref, error_code)
        );
        CREATE INDEX quarantine_status_idx ON integration.quarantine_record (status, created_at);

        CREATE TABLE integration.idempotency_key (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            scope varchar(128) NOT NULL,
            idempotency_key varchar(256) NOT NULL,
            request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-fA-F]{64}$'),
            resource_id uuid,
            response_status integer,
            response_body jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz,
            UNIQUE (scope, idempotency_key)
        );

        CREATE TABLE privacy.private_ref (
            token varchar(256) PRIMARY KEY,
            vault_ref text NOT NULL,
            classification varchar(64) NOT NULL,
            access_scope text[] NOT NULL CHECK (cardinality(access_scope) > 0),
            retention_class varchar(128) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            deletion_due_at timestamptz
        );

        CREATE TABLE appeals.appeal (
            request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_record_id uuid NOT NULL UNIQUE REFERENCES integration.source_record(id),
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            source_request_id varchar(128) NOT NULL,
            region_id varchar(32) NOT NULL,
            channel varchar(32) NOT NULL CHECK (channel IN ('phone', 'web', 'mobile', 'telegram', 'whatsapp', 'email', 'walk_in', 'import', 'other')),
            language varchar(16) NOT NULL CHECK (language IN ('kk', 'ru', 'mixed', 'unknown')),
            status varchar(32) NOT NULL DEFAULT 'new'
                CHECK (status IN ('new', 'triage', 'assigned', 'in_progress', 'resolved', 'closed', 'reopened', 'cancelled')),
            version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
            occurred_at timestamptz,
            observed_at timestamptz NOT NULL,
            source_timezone varchar(64),
            time_quality varchar(32) NOT NULL CHECK (time_quality IN ('exact', 'source_tz_assumed', 'date_only', 'missing')),
            CHECK (occurred_at IS NOT NULL OR time_quality IN ('missing', 'date_only')),
            CHECK (time_quality <> 'source_tz_assumed' OR source_timezone IS NOT NULL),
            citizen_token varchar(256),
            address_private_ref varchar(256),
            raw_text_ref text,
            transcript_ref text,
            geo_id varchar(256),
            object_id varchar(256),
            location geography(Point, 4326),
            precision_m numeric CHECK (precision_m IS NULL OR precision_m >= 0),
            normalization_status varchar(32) CHECK (normalization_status IS NULL OR normalization_status IN ('exact', 'approximate', 'ambiguous', 'missing')),
            legal_basis varchar(256),
            retention_class varchar(128),
            redaction_version varchar(128),
            deletion_due_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (source_system_id, source_request_id)
        );
        CREATE INDEX appeal_region_status_idx ON appeals.appeal (region_id, status, observed_at DESC);
        CREATE INDEX appeal_region_time_idx ON appeals.appeal (region_id, occurred_at DESC);
        CREATE INDEX appeal_location_gist_idx ON appeals.appeal USING GIST (location);

        CREATE TABLE appeals.appeal_event (
            event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            appeal_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            source_system_id uuid REFERENCES integration.source_system(id),
            source_event_id varchar(256),
            event_type varchar(128) NOT NULL,
            event_version integer NOT NULL CHECK (event_version > 0),
            occurred_at timestamptz,
            occurred_at_quality varchar(32) NOT NULL CHECK (occurred_at_quality IN ('exact', 'source_tz_assumed', 'date_only', 'missing')),
            observed_at timestamptz NOT NULL,
            actor_type varchar(32) NOT NULL CHECK (actor_type IN ('citizen', 'operator', 'supervisor', 'service', 'source_system', 'model', 'rule', 'system')),
            actor_id_token varchar(256),
            correlation_id varchar(128),
            causation_id varchar(128),
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (occurred_at IS NOT NULL OR occurred_at_quality IN ('missing', 'date_only')),
            UNIQUE (source_system_id, source_event_id)
        );
        CREATE INDEX appeal_event_timeline_idx ON appeals.appeal_event (appeal_id, observed_at, event_id);

        CREATE TABLE appeals.attachment_ref (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            appeal_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            object_ref text NOT NULL,
            object_hash char(64) NOT NULL CHECK (object_hash ~ '^[0-9a-fA-F]{64}$'),
            media_type varchar(128),
            byte_size bigint CHECK (byte_size IS NULL OR byte_size >= 0),
            data_classification varchar(64) NOT NULL
                CHECK (data_classification IN ('public', 'internal', 'confidential', 'restricted', 'security')),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (appeal_id, object_hash)
        );

        CREATE TABLE integration.outbox (
            event_id uuid PRIMARY KEY,
            event_type varchar(128) NOT NULL,
            event_version integer NOT NULL CHECK (event_version > 0),
            aggregate_type varchar(128) NOT NULL,
            subject_id varchar(128) NOT NULL,
            aggregate_version bigint CHECK (aggregate_version IS NULL OR aggregate_version > 0),
            region_id varchar(32) NOT NULL,
            occurred_at timestamptz,
            occurred_at_quality varchar(32) NOT NULL CHECK (occurred_at_quality IN ('exact', 'source_tz_assumed', 'date_only', 'missing')),
            observed_at timestamptz NOT NULL,
            producer varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            causation_id varchar(128),
            data_classification varchar(64) NOT NULL
                CHECK (data_classification IN ('public', 'internal', 'confidential', 'restricted', 'security')),
            payload jsonb NOT NULL,
            status varchar(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'published', 'retrying', 'dead_letter')),
            attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            available_at timestamptz NOT NULL DEFAULT now(),
            last_error_code varchar(128),
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (occurred_at IS NOT NULL OR occurred_at_quality IN ('missing', 'date_only'))
        );
        CREATE INDEX outbox_poll_idx ON integration.outbox (status, available_at, created_at);
        CREATE INDEX outbox_aggregate_idx ON integration.outbox (aggregate_type, subject_id, created_at);

        CREATE TABLE audit.audit_event (
            event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_type varchar(32) NOT NULL,
            actor_id_token varchar(256),
            action varchar(128) NOT NULL,
            aggregate_type varchar(128) NOT NULL,
            aggregate_id varchar(128),
            region_id varchar(32),
            reason_code varchar(128),
            before_hash char(64) CHECK (before_hash IS NULL OR before_hash ~ '^[0-9a-fA-F]{64}$'),
            after_hash char(64) CHECK (after_hash IS NULL OR after_hash ~ '^[0-9a-fA-F]{64}$'),
            correlation_id varchar(128),
            observed_at timestamptz NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX audit_aggregate_idx ON audit.audit_event (aggregate_type, aggregate_id, created_at);
        CREATE INDEX audit_region_idx ON audit.audit_event (region_id, created_at);

        CREATE OR REPLACE FUNCTION audit.reject_append_only_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'append-only table % cannot be modified', TG_TABLE_NAME
                USING ERRCODE = '55000';
        END;
        $$;
        CREATE TRIGGER source_record_append_only BEFORE UPDATE OR DELETE ON integration.source_record
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER appeal_event_append_only BEFORE UPDATE OR DELETE ON appeals.appeal_event
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER audit_event_append_only BEFORE UPDATE OR DELETE ON audit.audit_event
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_event_append_only ON audit.audit_event")
    op.execute("DROP TRIGGER IF EXISTS appeal_event_append_only ON appeals.appeal_event")
    op.execute("DROP TRIGGER IF EXISTS source_record_append_only ON integration.source_record")
    op.execute("DROP FUNCTION IF EXISTS audit.reject_append_only_mutation()")
    for table in (
        "audit.audit_event",
        "integration.outbox",
        "appeals.attachment_ref",
        "appeals.appeal_event",
        "appeals.appeal",
        "privacy.private_ref",
        "integration.idempotency_key",
        "integration.quarantine_record",
        "integration.source_record",
        "integration.import_run",
        "integration.source_schema_version",
        "integration.source_system",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
