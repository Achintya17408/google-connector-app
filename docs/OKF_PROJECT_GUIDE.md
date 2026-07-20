# Open Knowledge Format in Google Connector

## Verified specification status

Open Knowledge Format (OKF) v0.1 is currently a draft in the public
`GoogleCloudPlatform/knowledge-catalog` repository. It defines a vendor-neutral bundle
of UTF-8 Markdown concept documents with YAML frontmatter. The only required concept
field is a non-empty `type`; `index.md` and `log.md` are reserved; ordinary Markdown
links create relationships; broken internal links must be tolerated; and unknown
frontmatter fields and concept types must be preserved or handled gracefully.

Primary specification:
https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

## What OKF is and is not

OKF is a portable representation for curated knowledge. It is not:

- a vector database;
- an embedding model;
- a replacement for PostgreSQL;
- a replacement for live Google APIs;
- an agent framework;
- a fixed ontology or centralized schema registry.

A useful mental model is “knowledge as reviewed source code”: readable files, Git
history, diffs, ownership, links, and normal pull-request governance.

## This repository's bundle

The bundle lives in `knowledge/` and contains capabilities, policies, workflows,
runbooks, failure guidance, RAG source strategies, metric definitions, and durable-run
schemas. The project deliberately adds governance fields beyond minimum OKF v0.1:

```yaml
---
type: capability
title: Google Calendar and Meet
owner: project-admin
version: 1
timestamp: 2026-07-19T00:00:00Z
visibility: public
publication_status: approved
approved_by: project-admin
approved_at: 2026-07-19T00:00:00Z
tags: [calendar, meet]
---
```

These extra fields implement the project's human-publication boundary. They are valid
OKF extensions; they are not universal OKF requirements.

## Runtime path

```text
knowledge/*.md
    -> app/okf/loader.py validates structure and governance
    -> sync_bundle stores trusted documents and structural chunks
    -> app/okf/retriever.py performs trusted full-text lookup
    -> pack_operational_knowledge attaches ID, version, and heading provenance
    -> planner/agent consumes only approved operational knowledge
```

`app/runs/informational.py` also uses the human-approved OKF capability catalog for
bounded Workspace guidance. Draft or rejected concepts cannot become runtime policy.

## Four knowledge/data paths

| Need | Correct source | Why |
| --- | --- | --- |
| Stable approval/tool/recovery policy | trusted OKF | curated, versioned, reviewed |
| User's semantically relevant historical content | tenant-scoped RAG | content is large and query-dependent |
| Run state, incidents, artifacts, metrics | PostgreSQL/Neon | structured, transactional, auditable |
| Latest email or a new Calendar event | live Google API | current external system of record |

Routing these correctly is more important than embedding everything. “Create a Sheet”
needs a live API, not RAG. “What is our approval policy?” should prefer trusted OKF.
“Which past documents discuss pricing?” may need tenant-scoped hybrid retrieval.

## OKF and source-aware chunking

OKF documents are split by Markdown structure, not arbitrary global character counts.
Tool schemas stay intact; prerequisites and warnings stay with their operation; child
sections retain the document ID and version. The original OKF files remain the source
of truth, while database chunks and embeddings are disposable derived indexes.

## Publication lifecycle

```text
draft document
  -> structural/YAML/link/secret validation
  -> human review
  -> approved metadata with reviewer and time
  -> synchronization
  -> trusted retrieval
```

Automatic failure analysis may draft an OKF proposal, but cannot approve or publish
it. A material change invalidates the reviewed hash and must return to human review.

## Safe project exercise

1. Copy an existing public capability concept into a temporary test fixture.
2. Change its `type` to a new, unknown value and verify the consumer tolerates it.
3. Remove `type` and verify conformance validation rejects it.
4. Add a broken internal link and verify it is reported or tolerated without making
   the whole bundle unreadable.
5. Mark the document `publication_status: draft` and verify trusted retrieval excludes
   it.
6. Run `pytest tests/unit/test_core.py -q` and inspect `test_okf_bundle_is_valid`.

## Why OKF improves this project

- Policy is separated from model prompts and user content.
- Human changes are reviewable and reversible in Git.
- The same knowledge is readable by humans, deterministic code, and agents.
- Retrieval can cite stable document IDs and versions.
- Operational knowledge is portable if the project moves away from LangChain,
  LangGraph, Groq, PostgreSQL, or a particular vector store.
- The system can compare deterministic lookup, OKF full-text retrieval, and vector
  retrieval rather than forcing every question through one mechanism.
