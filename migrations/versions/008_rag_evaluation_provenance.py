"""Separate RAG evaluation metrics from runtime prompt telemetry.

Revision ID: 008
Revises: 007
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r'''
ALTER TABLE prompt_metrics
  ADD COLUMN metric_source TEXT NOT NULL DEFAULT 'runtime'
  CHECK(metric_source IN ('runtime','rag_evaluation'));
CREATE INDEX prompt_metrics_rag_evaluation_idx
  ON prompt_metrics(recorded_at DESC)
  WHERE metric_source='rag_evaluation';
''')


def downgrade():
    op.execute(r'''
DROP INDEX IF EXISTS prompt_metrics_rag_evaluation_idx;
ALTER TABLE prompt_metrics DROP COLUMN IF EXISTS metric_source;
''')
