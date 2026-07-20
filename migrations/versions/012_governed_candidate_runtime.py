"""Governed candidate builds, hierarchical failures, and version-pinned canaries.

Revision ID: 012
Revises: 011
"""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r'''
ALTER TABLE agent_runs
  ADD COLUMN executor_version TEXT,
  ADD COLUMN canary_id UUID REFERENCES improvement_canaries(id) ON DELETE SET NULL,
  ADD COLUMN cohort_assignment TEXT NOT NULL DEFAULT 'control'
    CHECK(cohort_assignment IN ('control','candidate')),
  ADD COLUMN assignment_reason TEXT,
  ADD COLUMN assigned_at TIMESTAMPTZ,
  ADD COLUMN okf_bundle_version TEXT;
UPDATE agent_runs SET executor_version=COALESCE(deployment_version,'local'),
  assignment_reason='pre-migration control assignment',assigned_at=queued_at
WHERE executor_version IS NULL;
ALTER TABLE agent_runs ALTER COLUMN executor_version SET DEFAULT 'local';
ALTER TABLE agent_runs ALTER COLUMN executor_version SET NOT NULL;
CREATE INDEX agent_runs_executor_claim_idx
  ON agent_runs(executor_version,status,queued_at)
  WHERE status IN ('queued','running');
CREATE INDEX agent_runs_canary_cohort_idx
  ON agent_runs(canary_id,cohort_assignment,queued_at);

ALTER TABLE improvement_canaries
  ADD COLUMN routing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN traffic_percent INTEGER NOT NULL DEFAULT 5
    CHECK(traffic_percent BETWEEN 0 AND 100),
  ADD COLUMN allowed_users TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN denied_users TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN activated_by TEXT,
  ADD COLUMN rollback_at TIMESTAMPTZ,
  ADD COLUMN rollback_cutoff_run_id UUID,
  ADD COLUMN candidate_deployment_id TEXT,
  ADD COLUMN candidate_image_digest TEXT;

CREATE TABLE failure_clusters (
    cluster_key TEXT PRIMARY KEY,
    stage TEXT NOT NULL,
    category TEXT NOT NULL,
    component TEXT NOT NULL,
    service TEXT,
    operation TEXT,
    title TEXT NOT NULL,
    normalized_signature TEXT NOT NULL,
    occurrence_count BIGINT NOT NULL DEFAULT 0,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'active'
      CHECK(status IN ('active','resolved','suppressed')),
    latest_incident_id UUID REFERENCES failure_incidents(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE failure_cluster_occurrences (
    cluster_key TEXT NOT NULL REFERENCES failure_clusters(cluster_key) ON DELETE CASCADE,
    incident_id UUID NOT NULL REFERENCES failure_incidents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(cluster_key,incident_id)
);
CREATE TABLE failure_themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    theme_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    systemic_cause TEXT NOT NULL,
    strategy_options JSONB NOT NULL,
    recommended_option TEXT NOT NULL CHECK(recommended_option IN ('A','B')),
    status TEXT NOT NULL DEFAULT 'active'
      CHECK(status IN ('active','candidate_building','resolved','suppressed')),
    occurrence_count BIGINT NOT NULL DEFAULT 0,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE failure_theme_clusters (
    theme_id UUID NOT NULL REFERENCES failure_themes(id) ON DELETE CASCADE,
    cluster_key TEXT NOT NULL REFERENCES failure_clusters(cluster_key) ON DELETE CASCADE,
    confidence NUMERIC(5,2) NOT NULL DEFAULT 100,
    PRIMARY KEY(theme_id,cluster_key)
);

CREATE TABLE candidate_builds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id UUID NOT NULL REFERENCES improvement_proposals(id) ON DELETE CASCADE,
    selected_option TEXT NOT NULL CHECK(selected_option IN ('A','B')),
    mode TEXT NOT NULL CHECK(mode IN ('single','multi_role')),
    status TEXT NOT NULL DEFAULT 'queued'
      CHECK(status IN ('queued','investigating','drafted','validating','validated','failed','cancelled')),
    base_commit TEXT NOT NULL,
    candidate_commit TEXT,
    candidate_tree TEXT,
    canonical_digest TEXT,
    model_name TEXT NOT NULL,
    model_policy_version TEXT NOT NULL,
    tool_policy_version TEXT NOT NULL,
    token_budget INTEGER NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb,
    sanitized_input JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX candidate_builds_queue_idx ON candidate_builds(status,created_at);
CREATE TABLE candidate_build_files (
    build_id UUID NOT NULL REFERENCES candidate_builds(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK(change_type IN ('create','replace','delete')),
    preimage_hash TEXT,
    result_hash TEXT NOT NULL,
    content TEXT,
    PRIMARY KEY(build_id,path)
);
CREATE TABLE candidate_validation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    build_id UUID NOT NULL REFERENCES candidate_builds(id) ON DELETE CASCADE,
    suite_version TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued','running','passed','failed')),
    commands JSONB NOT NULL DEFAULT '[]'::jsonb,
    results JSONB NOT NULL DEFAULT '{}'::jsonb,
    log_digest TEXT,
    attestation JSONB NOT NULL DEFAULT '{}'::jsonb,
    trusted_identity TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE okf_bundle_versions (
    bundle_hash TEXT PRIMARY KEY,
    source_version TEXT NOT NULL,
    publication_status TEXT NOT NULL DEFAULT 'draft'
      CHECK(publication_status IN ('draft','validated','canary','trusted','rolled_back','rejected')),
    manifest JSONB NOT NULL,
    validation_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    privacy_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    security_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE okf_bundle_documents (
    bundle_hash TEXT NOT NULL REFERENCES okf_bundle_versions(bundle_hash) ON DELETE CASCADE,
    document_id TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK(visibility IN ('public','private')),
    concept_type TEXT NOT NULL,
    title TEXT NOT NULL,
    version TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY(bundle_hash,document_id)
);
CREATE TABLE okf_bundle_chunks (
    bundle_hash TEXT NOT NULL,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    heading TEXT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY(bundle_hash,document_id,chunk_index),
    FOREIGN KEY(bundle_hash,document_id)
      REFERENCES okf_bundle_documents(bundle_hash,document_id) ON DELETE CASCADE
);
CREATE INDEX okf_bundle_chunks_search_idx ON okf_bundle_chunks(bundle_hash,document_id);

INSERT INTO feature_flags(name,enabled,config,updated_by)
VALUES('dp_context_packing',FALSE,
       jsonb_build_object('control','greedy','candidate','quantized_knapsack_v1',
                          'quantum',32),
       'system') ON CONFLICT(name) DO NOTHING;

CREATE OR REPLACE VIEW reporting.failure_cluster_details AS
SELECT c.*,count(DISTINCT tc.theme_id) AS theme_count
FROM failure_clusters c
LEFT JOIN failure_theme_clusters tc ON tc.cluster_key=c.cluster_key
GROUP BY c.cluster_key;
CREATE OR REPLACE VIEW reporting.failure_theme_summary AS
SELECT t.id,t.theme_key,t.title,t.systemic_cause,t.recommended_option,t.status,
       t.occurrence_count,t.first_seen,t.last_seen,count(tc.cluster_key) AS cluster_count
FROM failure_themes t LEFT JOIN failure_theme_clusters tc ON tc.theme_id=t.id
GROUP BY t.id;
CREATE OR REPLACE VIEW reporting.candidate_build_status AS
SELECT b.id,p.proposal_key,p.title,b.selected_option,b.mode,b.status,b.base_commit,
       b.candidate_commit,b.model_name,b.model_policy_version,b.tool_policy_version,
       b.token_budget,b.tokens_used,b.error_message,b.created_at,b.updated_at,b.completed_at
FROM candidate_builds b JOIN improvement_proposals p ON p.id=b.proposal_id;
CREATE OR REPLACE VIEW reporting.canary_run_assignments AS
SELECT r.id AS run_id,r.session_id,r.user_id,r.status,r.executor_version,r.canary_id,
       r.cohort_assignment,r.assignment_reason,r.assigned_at,r.okf_bundle_version,
       r.technical_completion,r.functional_completion,r.user_visible_completion,
       r.side_effect_integrity,r.queued_at,r.completed_at
FROM agent_runs r WHERE r.canary_id IS NOT NULL;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='dbeaver_analyst') THEN
    GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO dbeaver_analyst;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='grafana_reader') THEN
    GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO grafana_reader;
  END IF;
END $$;
''')


def downgrade():
    op.execute(r'''
DROP VIEW IF EXISTS reporting.failure_cluster_details;
DROP VIEW IF EXISTS reporting.canary_run_assignments;
DROP VIEW IF EXISTS reporting.candidate_build_status;
DROP VIEW IF EXISTS reporting.failure_theme_summary;
DELETE FROM feature_flags WHERE name='dp_context_packing';
DROP TABLE IF EXISTS okf_bundle_chunks;
DROP TABLE IF EXISTS okf_bundle_documents;
DROP TABLE IF EXISTS okf_bundle_versions;
DROP TABLE IF EXISTS candidate_validation_runs;
DROP TABLE IF EXISTS candidate_build_files;
DROP TABLE IF EXISTS candidate_builds;
DROP TABLE IF EXISTS failure_theme_clusters;
DROP TABLE IF EXISTS failure_themes;
DROP TABLE IF EXISTS failure_cluster_occurrences;
DROP TABLE IF EXISTS failure_clusters;
ALTER TABLE improvement_canaries
  DROP COLUMN IF EXISTS candidate_image_digest,
  DROP COLUMN IF EXISTS candidate_deployment_id,
  DROP COLUMN IF EXISTS rollback_cutoff_run_id,
  DROP COLUMN IF EXISTS rollback_at,
  DROP COLUMN IF EXISTS activated_by,
  DROP COLUMN IF EXISTS denied_users,
  DROP COLUMN IF EXISTS allowed_users,
  DROP COLUMN IF EXISTS traffic_percent,
  DROP COLUMN IF EXISTS routing_enabled;
DROP INDEX IF EXISTS agent_runs_canary_cohort_idx;
DROP INDEX IF EXISTS agent_runs_executor_claim_idx;
ALTER TABLE agent_runs
  DROP COLUMN IF EXISTS okf_bundle_version,
  DROP COLUMN IF EXISTS assigned_at,
  DROP COLUMN IF EXISTS assignment_reason,
  DROP COLUMN IF EXISTS cohort_assignment,
  DROP COLUMN IF EXISTS canary_id,
  DROP COLUMN IF EXISTS executor_version;
''')
