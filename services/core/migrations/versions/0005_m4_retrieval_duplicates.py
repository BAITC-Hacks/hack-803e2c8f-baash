"""Create governed retrieval corpus and duplicate proposals."""

from alembic import op

revision = "0005_m4_retrieval_duplicates"
down_revision = "0004_m3_routing_assistance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE triage.retrieval_document (
            document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            region_id varchar(32) NOT NULL,
            service_id varchar(128),
            evidence_type varchar(32) NOT NULL
                CHECK (evidence_type IN ('resolved_appeal', 'knowledge_article', 'service_definition')),
            approved_redacted_text text NOT NULL,
            search_vector tsvector GENERATED ALWAYS AS
                (to_tsvector('simple', approved_redacted_text)) STORED,
            embedding vector(1024),
            embedding_model_version varchar(128),
            preprocess_version varchar(64) NOT NULL,
            index_version varchar(64) NOT NULL,
            outcome_summary text,
            outcome_ref text,
            occurred_at timestamptz,
            occurred_at_quality varchar(32) NOT NULL
                CHECK (occurred_at_quality IN ('exact', 'source_tz_assumed', 'date_only', 'missing')),
            source_hash char(64) NOT NULL CHECK (source_hash ~ '^[0-9a-f]{64}$'),
            synthetic_only boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (request_id, index_version),
            CHECK (occurred_at IS NOT NULL OR occurred_at_quality IN ('date_only', 'missing'))
        );
        CREATE INDEX retrieval_document_fts_idx ON triage.retrieval_document USING gin(search_vector);
        CREATE INDEX retrieval_document_scope_idx ON triage.retrieval_document
            (region_id, service_id, index_version);
        CREATE INDEX retrieval_document_embedding_idx ON triage.retrieval_document
            USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL;

        CREATE TABLE triage.retrieval_run (
            retrieval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            request_version bigint NOT NULL CHECK (request_version > 0),
            region_id varchar(32) NOT NULL,
            query_snapshot_id uuid NOT NULL,
            index_version varchar(64) NOT NULL,
            embedding_model_version varchar(128),
            reranker_version varchar(128),
            fallback_mode varchar(32) NOT NULL
                CHECK (fallback_mode IN ('hybrid', 'lexical_only', 'rules_only')),
            ranked_candidates jsonb NOT NULL,
            latency_ms integer NOT NULL CHECK (latency_ms >= 0),
            trace_id varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            produced_at timestamptz NOT NULL,
            synthetic_only boolean NOT NULL DEFAULT true
        );

        CREATE TABLE incidents.duplicate_candidate (
            proposal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            candidate_type varchar(16) NOT NULL CHECK (candidate_type IN ('request', 'incident')),
            candidate_id uuid NOT NULL,
            region_id varchar(32) NOT NULL,
            score numeric NOT NULL CHECK (score >= 0 AND score <= 1),
            reasons jsonb NOT NULL,
            distance_m numeric CHECK (distance_m IS NULL OR distance_m >= 0),
            time_delta_minutes numeric CHECK (time_delta_minutes IS NULL OR time_delta_minutes >= 0),
            model_version varchar(128) NOT NULL,
            evidence_ref text NOT NULL,
            needs_human_confirmation boolean NOT NULL DEFAULT true
                CHECK (needs_human_confirmation = true),
            status varchar(24) NOT NULL DEFAULT 'proposed'
                CHECK (status IN ('proposed', 'confirmed', 'rejected', 'expired')),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (request_id, candidate_type, candidate_id, model_version),
            CHECK (request_id <> candidate_id OR candidate_type <> 'request')
        );

        CREATE TRIGGER retrieval_document_append_only
            BEFORE UPDATE OR DELETE ON triage.retrieval_document
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER retrieval_run_append_only
            BEFORE UPDATE OR DELETE ON triage.retrieval_run
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER duplicate_candidate_append_only
            BEFORE UPDATE OR DELETE ON incidents.duplicate_candidate
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    for table, trigger in (
        ("incidents.duplicate_candidate", "duplicate_candidate_append_only"),
        ("triage.retrieval_run", "retrieval_run_append_only"),
        ("triage.retrieval_document", "retrieval_document_append_only"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    op.execute("DROP TABLE IF EXISTS incidents.duplicate_candidate")
    op.execute("DROP TABLE IF EXISTS triage.retrieval_run")
    op.execute("DROP TABLE IF EXISTS triage.retrieval_document")
