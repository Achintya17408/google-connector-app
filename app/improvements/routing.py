"""Stable, persisted control/candidate assignment for governed canaries."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutorAssignment:
    executor_version: str
    canary_id: str | None
    cohort: str
    reason: str
    okf_bundle_version: str | None = None


def stable_bucket(canary_id: str, user_id: str) -> int:
    digest = hashlib.sha256(f"{canary_id}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % 100


def candidate_applies(manifest: dict, plan: dict | None) -> bool:
    """Require an explicit service/operation boundary before routing a candidate."""
    applicability = manifest.get("applicability") or {}
    if not applicability:
        return False
    plan_services = set((plan or {}).get("services") or [])
    plan_operations = {
        step.get("operation") for step in ((plan or {}).get("steps") or [])
        if step.get("operation")
    }
    required_services = set(applicability.get("services") or [])
    required_operations = set(applicability.get("operations") or [])
    required_rag_modes = set(applicability.get("rag_modes") or [])
    plan_rag_mode = (plan or {}).get("rag_mode", "none")
    return not (
        (required_services and not (required_services & plan_services))
        or (required_operations and not (required_operations & plan_operations))
        or (required_rag_modes and plan_rag_mode not in required_rag_modes)
    )


async def resolve_executor_assignment(
    conn, user_id: str, control_version: str, plan: dict | None = None,
) -> ExecutorAssignment:
    canaries = await conn.fetch(
        """SELECT c.*,p.candidate_kind,p.candidate_manifest
           FROM improvement_canaries c
           JOIN improvement_proposals p ON p.id=c.proposal_id
           WHERE c.status='active' AND c.routing_enabled=TRUE
           ORDER BY c.started_at,c.id FOR UPDATE"""
    )
    for row in canaries:
        manifest = row["candidate_manifest"] or {}
        if not candidate_applies(manifest, plan):
            continue
        allowed = set(row["allowed_users"] or [])
        denied = set(row["denied_users"] or [])
        if user_id in denied:
            continue
        selected = user_id in allowed or (
            not allowed and stable_bucket(str(row["id"]), user_id) < row["traffic_percent"]
        )
        cohort = "candidate" if selected else "control"
        version = (
            row["control_version"]
            if selected and row["candidate_kind"] in {"okf", "config", "prompt"}
            else (row["candidate_version"] if selected else row["control_version"])
        )
        return ExecutorAssignment(
            executor_version=version or control_version,
            canary_id=str(row["id"]),
            cohort=cohort,
            reason=("explicit allowlist" if user_id in allowed else
                    f"stable bucket {stable_bucket(str(row['id']), user_id)}"),
            okf_bundle_version=(manifest.get("okf_bundle_hash") if selected else None),
        )
    current_okf = await conn.fetchval(
        """SELECT bundle_hash FROM okf_bundle_versions
           WHERE publication_status='trusted' ORDER BY approved_at DESC NULLS LAST LIMIT 1"""
    )
    return ExecutorAssignment(
        executor_version=control_version, canary_id=None, cohort="control",
        reason="no compatible active canary",
        okf_bundle_version=current_okf,
    )
