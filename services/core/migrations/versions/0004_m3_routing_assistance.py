"""Create routing recommendations, human feedback and model registry evidence."""

from alembic import op

revision = "0004_m3_routing_assistance"
down_revision = "0003_m2_manual_path"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS registry;

        CREATE TABLE registry.dataset_manifest (
            manifest_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            dataset_name varchar(128) NOT NULL,
            dataset_version varchar(64) NOT NULL,
            manifest_sha256 char(64) NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
            synthetic_only boolean NOT NULL,
            data_cutoff timestamptz NOT NULL,
            manifest jsonb NOT NULL,
            leakage_audit_ref text NOT NULL,
            calibration_set_ref text NOT NULL,
            approval_or_legal_ref text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (dataset_name, dataset_version),
            UNIQUE (manifest_sha256),
            CHECK (synthetic_only = true)
        );

        CREATE TABLE registry.model_artifact (
            artifact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            model_name varchar(128) NOT NULL,
            model_version varchar(64) NOT NULL,
            artifact_uri text NOT NULL,
            artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
            input_contract_version varchar(64) NOT NULL,
            preprocess_version varchar(64) NOT NULL,
            dataset_manifest_id uuid NOT NULL REFERENCES registry.dataset_manifest(manifest_id),
            status varchar(32) NOT NULL CHECK (status IN ('candidate', 'approved', 'champion', 'retired')),
            model_card_ref text NOT NULL,
            license_ref text NOT NULL,
            security_review_ref text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (model_name, model_version),
            UNIQUE (artifact_sha256)
        );

        CREATE TABLE registry.model_evaluation (
            evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id uuid NOT NULL REFERENCES registry.model_artifact(artifact_id),
            dataset_manifest_id uuid NOT NULL REFERENCES registry.dataset_manifest(manifest_id),
            evaluation_cutoff timestamptz NOT NULL,
            seed integer NOT NULL,
            metrics jsonb NOT NULL,
            calibration jsonb NOT NULL,
            slice_dimensions text[] NOT NULL,
            report_ref text NOT NULL,
            generated_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (artifact_id, dataset_manifest_id, evaluation_cutoff)
        );

        CREATE TABLE registry.model_alias (
            model_name varchar(128) NOT NULL,
            alias varchar(32) NOT NULL CHECK (alias IN ('champion', 'challenger', 'baseline', 'mock')),
            artifact_id uuid NOT NULL REFERENCES registry.model_artifact(artifact_id),
            rollback_artifact_id uuid REFERENCES registry.model_artifact(artifact_id),
            approval_id varchar(128) NOT NULL,
            effective_at timestamptz NOT NULL,
            PRIMARY KEY (model_name, alias)
        );

        CREATE TABLE triage.recommendation (
            recommendation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            request_version bigint NOT NULL CHECK (request_version > 0),
            task varchar(32) NOT NULL DEFAULT 'routing' CHECK (task = 'routing'),
            model_name varchar(128) NOT NULL,
            model_alias varchar(32) NOT NULL CHECK (model_alias IN ('champion', 'challenger', 'baseline', 'mock')),
            model_version varchar(64) NOT NULL,
            artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
            input_contract_version varchar(64) NOT NULL,
            preprocess_version varchar(64) NOT NULL,
            taxonomy_version varchar(64) NOT NULL,
            feature_snapshot_id uuid NOT NULL,
            confidence_band varchar(32) NOT NULL CHECK (confidence_band IN ('high', 'medium', 'low', 'out_of_domain')),
            confidence numeric NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            ood_state varchar(32) NOT NULL CHECK (ood_state IN ('in_domain', 'out_of_domain')),
            ood_score numeric NOT NULL CHECK (ood_score >= 0 AND ood_score <= 1),
            fallback_mode varchar(32) NOT NULL CHECK (fallback_mode IN ('linear_cpu', 'lexical_cpu', 'mock', 'rules_only')),
            rule_hits jsonb NOT NULL DEFAULT '[]'::jsonb,
            evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
            requires_human_confirmation boolean NOT NULL DEFAULT true CHECK (requires_human_confirmation = true),
            trace_id varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            latency_ms integer NOT NULL CHECK (latency_ms >= 0),
            produced_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (request_id, request_version, task, model_alias, model_version)
        );

        CREATE TABLE triage.recommendation_candidate (
            recommendation_id uuid NOT NULL REFERENCES triage.recommendation(recommendation_id),
            candidate_kind varchar(16) NOT NULL CHECK (candidate_kind IN ('topic', 'service')),
            candidate_id varchar(128) NOT NULL,
            rank smallint NOT NULL CHECK (rank BETWEEN 1 AND 3),
            score numeric NOT NULL CHECK (score >= 0 AND score <= 1),
            PRIMARY KEY (recommendation_id, candidate_kind, rank),
            UNIQUE (recommendation_id, candidate_kind, candidate_id)
        );

        ALTER TABLE triage.operator_decision
            ADD CONSTRAINT operator_decision_recommendation_fk
            FOREIGN KEY (recommendation_id) REFERENCES triage.recommendation(recommendation_id);

        CREATE TABLE triage.feedback (
            feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            recommendation_id uuid NOT NULL REFERENCES triage.recommendation(recommendation_id),
            decision_id uuid NOT NULL UNIQUE REFERENCES triage.operator_decision(decision_id),
            task varchar(32) NOT NULL DEFAULT 'routing' CHECK (task = 'routing'),
            human_action varchar(32) NOT NULL CHECK (human_action IN ('accepted', 'corrected')),
            selected_topic_id varchar(128) NOT NULL,
            selected_service_id varchar(128) NOT NULL,
            selected_priority varchar(32) NOT NULL,
            correction_reason text,
            actor_token varchar(256) NOT NULL,
            feature_snapshot_id uuid NOT NULL,
            training_eligible boolean NOT NULL DEFAULT false,
            exclusion_reason varchar(256) NOT NULL DEFAULT 'pending_governance_review',
            decided_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (human_action <> 'corrected' OR (correction_reason IS NOT NULL AND length(trim(correction_reason)) > 0))
        );

        CREATE TRIGGER dataset_manifest_append_only
            BEFORE UPDATE OR DELETE ON registry.dataset_manifest
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER model_artifact_append_only
            BEFORE UPDATE OR DELETE ON registry.model_artifact
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER model_evaluation_append_only
            BEFORE UPDATE OR DELETE ON registry.model_evaluation
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER recommendation_append_only
            BEFORE UPDATE OR DELETE ON triage.recommendation
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER recommendation_candidate_append_only
            BEFORE UPDATE OR DELETE ON triage.recommendation_candidate
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER feedback_append_only
            BEFORE UPDATE OR DELETE ON triage.feedback
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    for table, trigger in (
        ("triage.feedback", "feedback_append_only"),
        ("triage.recommendation_candidate", "recommendation_candidate_append_only"),
        ("triage.recommendation", "recommendation_append_only"),
        ("registry.model_evaluation", "model_evaluation_append_only"),
        ("registry.model_artifact", "model_artifact_append_only"),
        ("registry.dataset_manifest", "dataset_manifest_append_only"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    op.execute(
        "ALTER TABLE triage.operator_decision DROP CONSTRAINT IF EXISTS operator_decision_recommendation_fk"
    )
    for table in (
        "triage.feedback",
        "triage.recommendation_candidate",
        "triage.recommendation",
        "registry.model_alias",
        "registry.model_evaluation",
        "registry.model_artifact",
        "registry.dataset_manifest",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    op.execute("DROP SCHEMA IF EXISTS registry")
