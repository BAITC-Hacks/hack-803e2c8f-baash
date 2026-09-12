"""Create governed analytics, alerts, forecasts and report artifacts."""

from alembic import op

revision = "0007_m6_analytics_reports"
down_revision = "0006_m5_incidents_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE analytics.metric_definition (
            metric_id varchar(128) NOT NULL,
            metric_version varchar(64) NOT NULL,
            display_name jsonb NOT NULL,
            definition_hash char(64) NOT NULL CHECK (definition_hash ~ '^[0-9a-f]{64}$'),
            value_type varchar(32) NOT NULL CHECK (value_type IN ('count', 'ratio', 'duration', 'state')),
            allowed_dimensions jsonb NOT NULL,
            filter_schema jsonb NOT NULL,
            query_plan jsonb NOT NULL,
            required_sources jsonb NOT NULL,
            freshness_policy jsonb NOT NULL,
            status varchar(24) NOT NULL CHECK (status IN ('draft', 'approved', 'retired')),
            synthetic_only boolean NOT NULL DEFAULT true,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (metric_id, metric_version),
            CHECK (effective_to IS NULL OR effective_to > effective_from)
        );

        CREATE TABLE analytics.metric_result (
            result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            metric_id varchar(128) NOT NULL,
            metric_version varchar(64) NOT NULL,
            region_scope jsonb NOT NULL,
            dimensions jsonb NOT NULL,
            filters jsonb NOT NULL,
            columns jsonb NOT NULL,
            rows jsonb NOT NULL,
            quality_state varchar(16) NOT NULL CHECK (quality_state IN ('complete', 'partial', 'stale', 'missing')),
            coverage jsonb NOT NULL,
            missing_regions jsonb NOT NULL,
            provenance jsonb NOT NULL,
            data_cutoff timestamptz NOT NULL,
            computed_at timestamptz NOT NULL,
            result_hash char(64) NOT NULL CHECK (result_hash ~ '^[0-9a-f]{64}$'),
            FOREIGN KEY (metric_id, metric_version)
                REFERENCES analytics.metric_definition(metric_id, metric_version),
            UNIQUE (metric_id, metric_version, result_hash)
        );
        CREATE INDEX metric_result_lookup_idx ON analytics.metric_result
            (metric_id, metric_version, data_cutoff DESC);

        CREATE TABLE analytics.source_freshness (
            source_system varchar(128) NOT NULL,
            region_id varchar(32) NOT NULL,
            observed_cutoff timestamptz,
            freshness_state varchar(16) NOT NULL CHECK (freshness_state IN ('fresh', 'stale', 'missing')),
            lag_seconds integer CHECK (lag_seconds IS NULL OR lag_seconds >= 0),
            assessed_at timestamptz NOT NULL,
            evidence_ref text NOT NULL,
            PRIMARY KEY (source_system, region_id, assessed_at)
        );

        CREATE TABLE analytics.alert (
            alert_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            alert_type varchar(32) NOT NULL CHECK (alert_type IN ('volume_spike', 'incident_growth', 'sla_risk', 'data_quality', 'model_drift')),
            region_id varchar(32) NOT NULL,
            severity varchar(16) NOT NULL CHECK (severity IN ('info', 'warning', 'high', 'critical')),
            status varchar(16) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'acknowledged', 'resolved', 'dismissed')),
            metric_id varchar(128) NOT NULL,
            metric_version varchar(64) NOT NULL,
            data_cutoff timestamptz NOT NULL,
            evidence jsonb NOT NULL,
            confidence numeric CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
            detected_at timestamptz NOT NULL,
            version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
            FOREIGN KEY (metric_id, metric_version)
                REFERENCES analytics.metric_definition(metric_id, metric_version)
        );

        CREATE TABLE analytics.alert_review (
            review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            alert_id uuid NOT NULL REFERENCES analytics.alert(alert_id),
            alert_version bigint NOT NULL CHECK (alert_version > 0),
            action varchar(16) NOT NULL CHECK (action IN ('acknowledge', 'resolve', 'dismiss')),
            disposition varchar(128) NOT NULL,
            evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
            actor_token varchar(256) NOT NULL,
            reviewed_at timestamptz NOT NULL,
            UNIQUE (alert_id, alert_version)
        );

        CREATE TABLE analytics.forecast (
            forecast_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            metric_id varchar(128) NOT NULL,
            metric_version varchar(64) NOT NULL,
            region_id varchar(32) NOT NULL,
            data_cutoff timestamptz NOT NULL,
            method varchar(64) NOT NULL,
            model_version varchar(128) NOT NULL,
            horizon jsonb NOT NULL,
            point_values jsonb NOT NULL,
            lower_values jsonb NOT NULL,
            upper_values jsonb NOT NULL,
            quality_state varchar(16) NOT NULL CHECK (quality_state IN ('complete', 'stale', 'missing')),
            generated_at timestamptz NOT NULL,
            evidence_ref text NOT NULL,
            FOREIGN KEY (metric_id, metric_version)
                REFERENCES analytics.metric_definition(metric_id, metric_version)
        );

        CREATE TABLE reports.report_job (
            job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            format varchar(8) NOT NULL CHECK (format IN ('pdf', 'xlsx')),
            template_id varchar(128) NOT NULL,
            metric_id varchar(128) NOT NULL,
            metric_version varchar(64) NOT NULL,
            query jsonb NOT NULL,
            data_cutoff timestamptz NOT NULL,
            region_scope jsonb NOT NULL,
            purpose varchar(256) NOT NULL,
            masking_policy_version varchar(64) NOT NULL,
            watermark text NOT NULL,
            status varchar(16) NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
            idempotency_key varchar(128) NOT NULL,
            actor_token varchar(256) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz,
            error_code varchar(128),
            UNIQUE (actor_token, idempotency_key),
            FOREIGN KEY (metric_id, metric_version)
                REFERENCES analytics.metric_definition(metric_id, metric_version)
        );

        CREATE TABLE reports.report_artifact (
            artifact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id uuid NOT NULL UNIQUE REFERENCES reports.report_job(job_id),
            object_ref text NOT NULL,
            artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
            byte_size bigint NOT NULL CHECK (byte_size > 0),
            content_type varchar(128) NOT NULL,
            metric_id varchar(128) NOT NULL,
            metric_version varchar(64) NOT NULL,
            data_cutoff timestamptz NOT NULL,
            metadata jsonb NOT NULL,
            created_at timestamptz NOT NULL,
            UNIQUE (artifact_sha256)
        );

        CREATE TRIGGER metric_definition_append_only
            BEFORE UPDATE OR DELETE ON analytics.metric_definition
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER metric_result_append_only
            BEFORE UPDATE OR DELETE ON analytics.metric_result
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER alert_review_append_only
            BEFORE UPDATE OR DELETE ON analytics.alert_review
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER forecast_append_only
            BEFORE UPDATE OR DELETE ON analytics.forecast
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER report_artifact_append_only
            BEFORE UPDATE OR DELETE ON reports.report_artifact
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    for table, trigger in (
        ("reports.report_artifact", "report_artifact_append_only"),
        ("analytics.forecast", "forecast_append_only"),
        ("analytics.alert_review", "alert_review_append_only"),
        ("analytics.metric_result", "metric_result_append_only"),
        ("analytics.metric_definition", "metric_definition_append_only"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    for table in (
        "reports.report_artifact",
        "reports.report_job",
        "analytics.forecast",
        "analytics.alert_review",
        "analytics.alert",
        "analytics.source_freshness",
        "analytics.metric_result",
        "analytics.metric_definition",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
