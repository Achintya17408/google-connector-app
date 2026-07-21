"""Encrypted, tenant-scoped transient storage for projected-away tool payloads."""

from __future__ import annotations

import hashlib
import json
import uuid

from app.config.settings import get_settings
from app.db.oauth_credentials import decrypt_private_payload, encrypt_private_payload


async def store_private_tool_result(
    pool, *, user_id: str | None, run_id: str | None, step_id: str | None,
    tool_name: str, result,
) -> str | None:
    if not pool or not user_id or not run_id or not step_id:
        return None
    raw = json.dumps(result, default=str, separators=(",", ":")).encode()
    settings = get_settings()
    if not raw or len(raw) > settings.private_tool_result_max_bytes:
        return None
    encrypted = encrypt_private_payload(raw)
    async with pool.acquire() as conn:
        result_id = await conn.fetchval(
            """INSERT INTO private_tool_results
               (user_id,run_id,step_id,tool_name,encrypted_payload,content_hash,
                original_bytes,expires_at)
               VALUES($1,$2,$3,$4,$5,$6,$7,
                      now()+($8 * interval '1 hour')) RETURNING id""",
            user_id, run_id, step_id, tool_name, encrypted,
            hashlib.sha256(raw).hexdigest(), len(raw),
            settings.private_tool_result_retention_hours,
        )
    return f"private-tool-result:{result_id}"


async def load_private_tool_result(pool, reference: str, user_id: str):
    prefix = "private-tool-result:"
    if not reference.startswith(prefix):
        raise ValueError("Invalid private tool-result reference")
    try:
        result_id = uuid.UUID(reference.removeprefix(prefix))
    except ValueError as exc:
        raise ValueError("Invalid private tool-result reference") from exc
    async with pool.acquire() as conn:
        encrypted = await conn.fetchval(
            """SELECT encrypted_payload FROM private_tool_results
               WHERE id=$1 AND user_id=$2 AND expires_at>now()""",
            result_id, user_id,
        )
    if encrypted is None:
        raise ValueError("Private tool result is unavailable or expired")
    return json.loads(decrypt_private_payload(encrypted))
