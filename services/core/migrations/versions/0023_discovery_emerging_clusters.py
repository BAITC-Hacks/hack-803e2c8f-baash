"""Persist emerging clusters and their membership, without copying appeal text."""

from alembic import op

revision = "0023_discovery_emerging_clusters"
down_revision = "0022_privacy_region"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS discovery")
    op.execute(
        """
        CREATE TABLE discovery.emerging_cluster (
            cluster_id uuid PRIMARY KEY,
            region_id varchar(32) NOT NULL CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$'),
            state varchar(32) NOT NULL DEFAULT 'open'
                CHECK (state IN ('open', 'under_review', 'promoted', 'dismissed', 'known_pattern')),
            first_seen_at timestamptz NOT NULL,
            last_seen_at timestamptz NOT NULL,
            appeal_count integer NOT NULL CHECK (appeal_count >= 0),
            centroid geography(Point, 4326),
            radius_m numeric CHECK (radius_m IS NULL OR radius_m >= 0),
            cohesion_score numeric NOT NULL CHECK (cohesion_score BETWEEN 0 AND 1),
            novelty_score numeric NOT NULL CHECK (novelty_score BETWEEN 0 AND 1),
            cluster_score numeric NOT NULL CHECK (cluster_score BETWEEN 0 AND 1),
            signals_used jsonb NOT NULL DEFAULT '[]'::jsonb,
            top_topics jsonb NOT NULL DEFAULT '[]'::jsonb,
            languages jsonb NOT NULL DEFAULT '{}'::jsonb,
            algorithm_version varchar(128) NOT NULL,
            -- Which thresholds produced this cluster. A reviewer must be able to
            -- reconstruct the alert, and thresholds change between releases.
            policy_snapshot jsonb NOT NULL,
            promoted_incident_id uuid,
            reviewed_by_token varchar(256),
            review_reason_code varchar(128),
            reviewed_at timestamptz,
            synthetic boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CHECK (last_seen_at >= first_seen_at)
        )
        """
    )
    op.execute(
        "CREATE INDEX emerging_cluster_region_state_idx "
        "ON discovery.emerging_cluster (region_id, state, last_seen_at DESC)"
    )
    op.execute(
        """
        CREATE TABLE discovery.cluster_member (
            cluster_id uuid NOT NULL
                REFERENCES discovery.emerging_cluster (cluster_id) ON DELETE CASCADE,
            request_id uuid NOT NULL REFERENCES appeals.appeal (request_id),
            score numeric NOT NULL CHECK (score BETWEEN 0 AND 1),
            -- Controlled codes only. Appeal text never enters this table.
            membership_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (cluster_id, request_id)
        )
        """
    )
    op.execute("CREATE INDEX cluster_member_request_idx ON discovery.cluster_member (request_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS discovery.cluster_member")
    op.execute("DROP TABLE IF EXISTS discovery.emerging_cluster")
    op.execute("DROP SCHEMA IF EXISTS discovery")
