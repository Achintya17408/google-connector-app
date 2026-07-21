"""Validation and immutable staging for governed OKF candidate overlays."""

from __future__ import annotations

import hashlib
import json
import posixpath
from typing import Any

import yaml

from app.rag.context_packer import PROMPT_INJECTION_LINE
from app.okf.loader import (
    ALLOWED_VISIBILITY, EMAIL_PATTERN, FRONTMATTER, MARKDOWN_LINK,
    RESERVED_FILENAMES, SECRET_PATTERN, section_chunks,
)
from app.tools.registry import registered_tool_names


def _parse_candidate_document(path: str, raw: str) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    document_id = path.removeprefix("knowledge/")
    if posixpath.basename(document_id) in RESERVED_FILENAMES:
        return None, [
            f"{path}: reserved OKF navigation/history files cannot be candidate concepts"
        ]
    match = FRONTMATTER.match(raw or "")
    if not match:
        return None, [f"{path}: missing YAML frontmatter"]
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        return None, [f"{path}: invalid YAML: {exc}"]
    if not isinstance(metadata, dict):
        return None, [f"{path}: YAML frontmatter must be an object"]
    for field in (
        "type", "title", "owner", "version", "timestamp", "visibility",
        "publication_status",
    ):
        if metadata.get(field) in (None, ""):
            errors.append(f"{path}: required field '{field}' is missing")
    visibility = metadata.get("visibility", "public")
    if visibility not in ALLOWED_VISIBILITY:
        errors.append(f"{path}: invalid visibility '{visibility}'")
    if metadata.get("publication_status") != "draft":
        errors.append(
            f"{path}: generated OKF candidates must remain publication_status: draft"
        )
    tools = metadata.get("tools") or []
    if not isinstance(tools, list) or not all(isinstance(item, str) for item in tools):
        errors.append(f"{path}: tools must be a list of tool names")
        tools = []
    unknown = sorted(set(tools) - registered_tool_names())
    if unknown:
        errors.append(f"{path}: unknown tool references: {unknown}")
    if SECRET_PATTERN.search(raw):
        errors.append(f"{path}: secret-like value detected")
    if visibility == "public":
        public_emails = [
            value for value in EMAIL_PATTERN.findall(raw)
            if not value.lower().endswith("@example.com")
        ]
        if public_emails:
            errors.append(f"{path}: public document contains email-like PII")
    body = match.group(2).strip()
    for line in body.splitlines():
        stripped = line.strip().casefold()
        if PROMPT_INJECTION_LINE.search(line) and not stripped.startswith(
            ("never ", "do not ", "must not ", ">", "`")
        ):
            errors.append(
                f"{path}: authority-changing or secret-exfiltration instruction detected"
            )
    for target in MARKDOWN_LINK.findall(body):
        if target.startswith(("http://", "https://", "/")):
            continue
        resolved = posixpath.normpath(
            posixpath.join(posixpath.dirname(document_id), target)
        )
        if resolved == ".." or resolved.startswith("../"):
            errors.append(f"{path}: link escapes bundle: {target}")
    if errors:
        return None, errors
    return {
        "document_id": document_id,
        "visibility": visibility,
        "concept_type": metadata["type"],
        "title": metadata["title"],
        "version": str(metadata["version"]),
        "content": body,
        "content_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "metadata": metadata,
    }, []


async def stage_okf_candidate_bundle(
    conn, files: list[dict[str, Any]], *, source_version: str,
    validation_report: dict, privacy_report: dict, security_report: dict,
) -> str:
    """Apply a validated draft overlay to the latest trusted immutable bundle."""
    if validation_report.get("passed") is not True or not validation_report.get(
        "trusted_identity"
    ):
        raise ValueError("OKF candidates require a passing trusted CI attestation")
    if privacy_report.get("pii_scan") != "passed":
        raise ValueError("OKF candidates require a passing PII scan")
    base_hash = await conn.fetchval(
        """SELECT bundle_hash FROM okf_bundle_versions
           WHERE publication_status='trusted'
           ORDER BY approved_at DESC NULLS LAST,created_at DESC LIMIT 1"""
    )
    documents: dict[str, dict] = {}
    if base_hash:
        for row in await conn.fetch(
            "SELECT * FROM okf_bundle_documents WHERE bundle_hash=$1", base_hash,
        ):
            item = dict(row)
            item.pop("bundle_hash", None)
            documents[item["document_id"]] = item
    errors: list[str] = []
    for item in files:
        path = item["path"]
        if not path.startswith("knowledge/") or not path.endswith(".md"):
            errors.append(f"OKF candidate path is not a knowledge Markdown file: {path}")
            continue
        document_id = path.removeprefix("knowledge/")
        if item["change_type"] == "delete":
            documents.pop(document_id, None)
            continue
        document, item_errors = _parse_candidate_document(path, item.get("content") or "")
        errors.extend(item_errors)
        if document:
            documents[document_id] = document
    if errors:
        raise ValueError("Invalid OKF candidate:\n" + "\n".join(errors))
    manifest = {
        "okf_version": "0.1", "base_bundle_hash": base_hash,
        "documents": [
            {"id": item["document_id"], "content_hash": item["content_hash"],
             "version": item["version"], "visibility": item["visibility"]}
            for item in sorted(documents.values(), key=lambda value: value["document_id"])
        ],
    }
    bundle_hash = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    await conn.execute(
        """INSERT INTO okf_bundle_versions
           (bundle_hash,source_version,publication_status,manifest,validation_report,
            privacy_report,security_report)
           VALUES($1,$2,'validated',$3::jsonb,$4::jsonb,$5::jsonb,$6::jsonb)
           ON CONFLICT(bundle_hash) DO UPDATE SET validation_report=excluded.validation_report,
             privacy_report=excluded.privacy_report,security_report=excluded.security_report""",
        bundle_hash, source_version, json.dumps(manifest), json.dumps(validation_report),
        json.dumps(privacy_report), json.dumps(security_report),
    )
    for document in documents.values():
        await conn.execute(
            """INSERT INTO okf_bundle_documents
               (bundle_hash,document_id,visibility,concept_type,title,version,content,
                content_hash,metadata)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
               ON CONFLICT(bundle_hash,document_id) DO NOTHING""",
            bundle_hash, document["document_id"], document["visibility"],
            document["concept_type"], document["title"], document["version"],
            document["content"], document["content_hash"],
            json.dumps(document["metadata"], default=str),
        )
        compatible = {
            "title": document["title"], "content": document["content"],
        }
        for chunk in section_chunks(compatible):
            await conn.execute(
                """INSERT INTO okf_bundle_chunks
                   (bundle_hash,document_id,chunk_index,heading,content,content_hash,metadata)
                   VALUES($1,$2,$3,$4,$5,$6,$7::jsonb)
                   ON CONFLICT(bundle_hash,document_id,chunk_index) DO NOTHING""",
                bundle_hash, document["document_id"], chunk["chunk_index"],
                chunk["heading"], chunk["content"], chunk["content_hash"],
                json.dumps({"concept_type": document["concept_type"],
                            "candidate": True}),
            )
    return bundle_hash
