"""Complete read-only reporting surface.

Revision ID: 006
Revises: 005
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r'''
CREATE OR REPLACE VIEW reporting.artifact_cleanup AS
SELECT a.id AS artifact_id,a.run_id,a.user_id,a.artifact_type,a.external_id,a.url,
       a.verification_status,a.sharing_state,a.cleanup_state,a.safe_to_delete,
       a.created_at,a.verified_at,r.status AS run_status,r.deployment_version
FROM agent_artifacts a JOIN agent_runs r ON r.id=a.run_id
WHERE r.deleted_at IS NULL;

CREATE OR REPLACE VIEW reporting.canary_evaluations AS
SELECT p.proposal_key,p.title,p.status AS proposal_status,p.severity,p.risk_level,
       c.id AS canary_id,c.status AS canary_status,c.cohort,c.control_version,
       c.candidate_version,c.metrics,c.started_at,c.ended_at,c.rollback_reason,
       e.suite_version,e.control_metrics,e.candidate_metrics,e.regressions,
       e.passed AS evaluation_passed,e.created_at AS evaluated_at
FROM improvement_proposals p
LEFT JOIN improvement_canaries c ON c.proposal_id=p.id
LEFT JOIN LATERAL (
  SELECT * FROM improvement_evaluations evaluation
  WHERE evaluation.proposal_id=p.id ORDER BY evaluation.created_at DESC LIMIT 1
) e ON TRUE;

CREATE OR REPLACE VIEW reporting.prompt_experiment_results AS
SELECT e.id AS experiment_id,e.name,e.prompt_name,e.status,e.traffic_split,e.winner,
       e.started_at,e.ended_at,summary.arm,summary.total_requests,
       summary.avg_latency_ms,summary.avg_rating,summary.avg_faithfulness,
       summary.avg_relevancy,summary.error_rate_pct,summary.completion_rate_pct
FROM prompt_experiments e
LEFT JOIN experiment_summary summary ON summary.experiment_name=e.name;

CREATE OR REPLACE VIEW reporting.security_audit AS
SELECT 'run_approval'::text AS event_type,a.decided_by AS actor,a.status,
       COALESCE(a.decided_at,a.created_at) AS occurred_at,r.user_id AS subject_user,
       jsonb_build_object('run_id',a.run_id,'risk_level',r.risk_level) AS details
FROM run_approvals a JOIN agent_runs r ON r.id=a.run_id
UNION ALL
SELECT 'improvement_approval',a.decided_by,a.decision,a.decided_at,NULL,
       jsonb_build_object('proposal_id',a.proposal_id,'stage',a.stage,
                          'proposal_hash',a.proposal_hash)
FROM improvement_approvals a
UNION ALL
SELECT 'data_deletion','user',d.status,d.requested_at,d.user_id,
       jsonb_build_object('completed_at',d.completed_at)
FROM deletion_requests d
UNION ALL
SELECT 'retention','system',a.action,a.executed_at,NULL,
       jsonb_build_object('policy',a.policy_name,'table',a.table_name,
                          'affected_rows',a.affected_rows)
FROM retention_audit a;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='dbeaver_analyst') THEN
    GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO dbeaver_analyst;
  END IF;
END $$;
''')


def downgrade():
    op.execute(r'''
DROP VIEW IF EXISTS reporting.security_audit;
DROP VIEW IF EXISTS reporting.prompt_experiment_results;
DROP VIEW IF EXISTS reporting.canary_evaluations;
DROP VIEW IF EXISTS reporting.artifact_cleanup;
''')
