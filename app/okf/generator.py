"""Deterministic candidate generation; generated knowledge is never auto-approved."""

from datetime import datetime, timezone

from app.db.google_clients import SCOPES
from app.tools.registry import registered_tool_names


METRIC_NAMES = (
    "agent_requests_total", "agent_request_latency_seconds",
    "agent_run_transitions_total", "agent_run_failures_total",
    "agent_run_duration_seconds", "agent_run_queue_depth",
    "agent_approval_requests_total", "agent_rag_decisions_total",
    "agent_stale_runs", "agent_embedding_jobs", "agent_improvement_proposals",
)


def build_catalog_draft() -> str:
    """Create a reviewable Markdown candidate from authoritative code constants."""
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tools = sorted(registered_tool_names())
    return "\n".join([
        "---", "type: catalog", "title: Generated Runtime Catalog",
        "owner: project-admin", "version: candidate", f"timestamp: {timestamp}",
        "visibility: public", "publication_status: draft", "tags: [generated, catalog]",
        "---", "# Tool registry", *[f"- `{name}`" for name in tools],
        "", "# OAuth scopes", *[f"- `{scope}`" for scope in sorted(SCOPES)],
        "", "# Production metrics", *[f"- `{name}`" for name in METRIC_NAMES],
        "", "This candidate must pass validation and receive `approved_by` and "
        "`approved_at` metadata before trusted retrieval can use it.",
    ]) + "\n"
