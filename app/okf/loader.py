import hashlib
import json
import re
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")
SECRET_PATTERN = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
ALLOWED_VISIBILITY = {"public", "private"}
ALLOWED_PUBLICATION = {"draft", "approved", "rejected"}
RESERVED_FILENAMES = {"index.md", "log.md"}


def load_bundle(
    root: Path,
    known_tools: set[str] | None = None,
    *,
    enforce_governance: bool = False,
) -> tuple[list[dict], list[str]]:
    documents = []
    errors = []
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        raw = path.read_text(encoding="utf-8")
        match = FRONTMATTER.match(raw)
        if path.name in RESERVED_FILENAMES:
            # OKF v0.1 reserves index.md and log.md for navigation/history;
            # they are not concepts. Only the bundle-root index may contain
            # frontmatter, primarily to declare okf_version.
            if match and relative != "index.md":
                errors.append(f"{relative}: reserved file must not have YAML frontmatter")
            if relative == "index.md" and match:
                try:
                    index_metadata = yaml.safe_load(match.group(1)) or {}
                except yaml.YAMLError as exc:
                    errors.append(f"{relative}: invalid YAML: {exc}")
                    continue
                version = str(index_metadata.get("okf_version", "0.1"))
                if version != "0.1":
                    errors.append(f"{relative}: unsupported okf_version '{version}'")
            continue
        if not match:
            errors.append(f"{relative}: missing YAML frontmatter")
            continue
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{relative}: invalid YAML: {exc}")
            continue
        required_fields = ["type"]
        if enforce_governance:
            required_fields.extend((
                "title", "owner", "version", "timestamp", "visibility",
                "publication_status",
            ))
        for required in required_fields:
            if metadata.get(required) in (None, ""):
                errors.append(f"{relative}: required field '{required}' is missing")
        visibility = metadata.get("visibility", "public")
        publication = metadata.get("publication_status", "draft")
        if visibility not in ALLOWED_VISIBILITY:
            errors.append(f"{relative}: invalid visibility '{visibility}'")
        if publication not in ALLOWED_PUBLICATION:
            errors.append(f"{relative}: invalid publication_status '{publication}'")
        approval_complete = bool(
            metadata.get("approved_by") and metadata.get("approved_at")
        )
        if enforce_governance and publication == "approved" and not approval_complete:
            errors.append(f"{relative}: approved documents require approved_by and approved_at")
        tool_references = set(metadata.get("tools") or [])
        if known_tools is not None:
            unknown = sorted(tool_references - known_tools)
            if unknown:
                errors.append(f"{relative}: unknown tool references: {unknown}")
        body = match.group(2).strip()
        if SECRET_PATTERN.search(raw):
            errors.append(f"{relative}: secret-like value detected")
        if visibility == "public":
            public_emails = [value for value in EMAIL_PATTERN.findall(raw)
                             if not value.lower().endswith("@example.com")]
            if public_emails:
                errors.append(f"{relative}: public document contains email-like PII")
        for target in MARKDOWN_LINK.findall(body):
            if target.startswith(("http://", "https://", "/")):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{relative}: link escapes bundle: {target}")
                continue
            # OKF consumers must tolerate broken links. They can represent
            # intentionally not-yet-written knowledge, so absence is not a
            # conformance or synchronization failure.
        content_hash = hashlib.sha256(raw.encode()).hexdigest()
        documents.append({
            "id": relative,
            "concept_type": metadata.get("type", "invalid"),
            "title": metadata.get("title") or path.stem.replace("-", " ").title(),
            "description": metadata.get("description"),
            "resource": metadata.get("resource"),
            "tags": metadata.get("tags") or [],
            "owner": metadata.get("owner"),
            "version": str(metadata.get("version", "1")),
            "visibility": visibility,
            "trusted": publication == "approved" and approval_complete,
            "content": body,
            "content_hash": content_hash,
            "metadata": metadata,
        })
    return documents, errors


def section_chunks(document: dict) -> list[dict]:
    sections = []
    heading = document["title"]
    current = []
    for line in document["content"].splitlines():
        if line.startswith("#") and current:
            sections.append((heading, "\n".join(current).strip()))
            heading = line.lstrip("#").strip()
            current = [line]
        else:
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            current.append(line)
    if current:
        sections.append((heading, "\n".join(current).strip()))
    return [
        {
            "heading": title,
            "content": content,
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "chunk_index": index,
        }
        for index, (title, content) in enumerate(sections) if content
    ]


async def sync_bundle(pool, root: Path | None = None):
    root = root or Path(__file__).resolve().parents[2] / "knowledge"
    from app.tools.registry import registered_tool_names
    documents, errors = load_bundle(
        root, registered_tool_names(), enforce_governance=True
    )
    from app.config.settings import get_settings
    private_path = get_settings().okf_private_bundle_path.strip()
    if private_path and root.name == "knowledge":
        private_root = Path(private_path).expanduser()
        if not private_root.is_dir():
            errors.append(f"private bundle directory does not exist: {private_root}")
        else:
            private_documents, private_errors = load_bundle(
                private_root, registered_tool_names(), enforce_governance=True
            )
            errors.extend(f"private/{error}" for error in private_errors)
            for document in private_documents:
                if document["visibility"] != "private":
                    errors.append(
                        f"private/{document['id']}: protected bundle documents must "
                        "declare visibility: private"
                    )
                document["id"] = f"private/{document['id']}"
            documents.extend(private_documents)
    if errors:
        raise ValueError("Invalid OKF bundle:\n" + "\n".join(errors))
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Older builds incorrectly stored the reserved root index as a
            # concept. Remove that stale row while leaving generated drafts and
            # all genuine concept IDs untouched.
            await conn.execute("DELETE FROM okf_documents WHERE id='index.md'")
            for document in documents:
                await conn.execute(
                    """INSERT INTO okf_documents
                       (id,visibility,concept_type,title,description,resource,tags,
                        owner,version,content,content_hash,metadata,trusted,published_at)
                       VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13,
                              CASE WHEN $13 THEN now() ELSE NULL END)
                       ON CONFLICT(id) DO UPDATE SET visibility=excluded.visibility,
                        concept_type=excluded.concept_type,title=excluded.title,
                        description=excluded.description,resource=excluded.resource,
                        tags=excluded.tags,owner=excluded.owner,version=excluded.version,
                        content=excluded.content,content_hash=excluded.content_hash,
                        metadata=excluded.metadata,trusted=excluded.trusted,
                        published_at=CASE WHEN excluded.trusted
                          THEN COALESCE(okf_documents.published_at,now()) ELSE NULL END,
                        updated_at=now()""",
                    document["id"], document["visibility"], document["concept_type"],
                    document["title"], document["description"], document["resource"],
                    document["tags"], document["owner"], document["version"],
                    document["content"], document["content_hash"],
                    json.dumps(document["metadata"], default=str), document["trusted"],
                )
                await conn.execute("DELETE FROM okf_chunks WHERE document_id=$1", document["id"])
                for chunk in section_chunks(document):
                    await conn.execute(
                        """INSERT INTO okf_chunks
                           (document_id,heading,chunk_index,content,content_hash,
                            chunker_version,metadata)
                           VALUES($1,$2,$3,$4,$5,'okf-structure-v1',$6::jsonb)""",
                        document["id"], chunk["heading"], chunk["chunk_index"],
                        chunk["content"], chunk["content_hash"],
                        json.dumps({"concept_type": document["concept_type"],
                                    "tags": document["tags"]}),
                    )
    return len(documents)
