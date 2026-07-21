"""Candidate scope and trusted OKF publication reporting.

Revision ID: 013
Revises: 012
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r'''
ALTER TABLE failure_incidents
  ADD COLUMN failure_mechanism TEXT NOT NULL DEFAULT 'unknown',
  ADD COLUMN architectural_boundary TEXT NOT NULL DEFAULT 'unknown',
  ADD COLUMN provider_code TEXT,
  ADD COLUMN recoverable BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN last_verified_operation TEXT,
  ADD COLUMN source_version TEXT NOT NULL DEFAULT 'unknown';

ALTER TABLE failure_clusters
  ADD COLUMN mechanism TEXT NOT NULL DEFAULT 'unknown',
  ADD COLUMN boundary TEXT NOT NULL DEFAULT 'unknown',
  ADD COLUMN first_version TEXT,
  ADD COLUMN latest_version TEXT,
  ADD COLUMN resolution_version TEXT,
  ADD COLUMN reopened_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN regression_case_ids JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE improvement_approvals DROP CONSTRAINT improvement_approvals_stage_check;
ALTER TABLE improvement_approvals ADD CONSTRAINT improvement_approvals_stage_check
  CHECK(stage IN ('okf_publication','canary','promotion'));

CREATE TABLE private_tool_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_run_steps(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    encrypted_payload TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    original_bytes INTEGER NOT NULL CHECK(original_bytes>0),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX private_tool_results_tenant_idx
  ON private_tool_results(user_id,expires_at);

CREATE OR REPLACE VIEW reporting.okf_candidate_publication AS
SELECT b.bundle_hash,b.source_version,b.publication_status,b.approved_by,b.approved_at,
       b.created_at,p.proposal_key,p.status AS proposal_status,p.candidate_version,
       p.candidate_manifest->'applicability' AS applicability
FROM okf_bundle_versions b
LEFT JOIN improvement_proposals p
  ON p.candidate_manifest->>'okf_bundle_hash'=b.bundle_hash;

CREATE OR REPLACE VIEW reporting.candidate_applicability AS
SELECT p.proposal_key,p.candidate_kind,p.candidate_state,p.status,
       p.source_version,p.candidate_version,
       p.candidate_manifest->'applicability' AS applicability,
       c.id AS canary_id,c.status AS canary_status,c.routing_enabled,c.traffic_percent,
       c.control_version,c.candidate_version AS routed_candidate_version
FROM improvement_proposals p
LEFT JOIN LATERAL (
  SELECT * FROM improvement_canaries ic
  WHERE ic.proposal_id=p.id ORDER BY ic.started_at DESC NULLS LAST,ic.id DESC LIMIT 1
) c ON TRUE
WHERE p.candidate_state<>'diagnosis_only';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='dbeaver_analyst') THEN
    GRANT SELECT ON reporting.okf_candidate_publication TO dbeaver_analyst;
    GRANT SELECT ON reporting.candidate_applicability TO dbeaver_analyst;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='grafana_reader') THEN
    GRANT SELECT ON reporting.okf_candidate_publication TO grafana_reader;
    GRANT SELECT ON reporting.candidate_applicability TO grafana_reader;
  END IF;
END $$;
''')


def downgrade():
    op.execute(r'''
DROP VIEW IF EXISTS reporting.candidate_applicability;
DROP VIEW IF EXISTS reporting.okf_candidate_publication;
DROP TABLE IF EXISTS private_tool_results;
UPDATE improvement_approvals SET stage='canary' WHERE stage='okf_publication';
ALTER TABLE improvement_approvals DROP CONSTRAINT improvement_approvals_stage_check;
ALTER TABLE improvement_approvals ADD CONSTRAINT improvement_approvals_stage_check
  CHECK(stage IN ('canary','promotion'));
ALTER TABLE failure_clusters
  DROP COLUMN IF EXISTS regression_case_ids,
  DROP COLUMN IF EXISTS reopened_count,
  DROP COLUMN IF EXISTS resolution_version,
  DROP COLUMN IF EXISTS latest_version,
  DROP COLUMN IF EXISTS first_version,
  DROP COLUMN IF EXISTS boundary,
  DROP COLUMN IF EXISTS mechanism;
ALTER TABLE failure_incidents
  DROP COLUMN IF EXISTS source_version,
  DROP COLUMN IF EXISTS last_verified_operation,
  DROP COLUMN IF EXISTS recoverable,
  DROP COLUMN IF EXISTS provider_code,
  DROP COLUMN IF EXISTS architectural_boundary,
  DROP COLUMN IF EXISTS failure_mechanism;
''')
