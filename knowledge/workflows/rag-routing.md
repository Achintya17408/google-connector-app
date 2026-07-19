---
type: workflow
title: RAG routing boundaries
owner: project-admin
version: 1
timestamp: 2026-07-19T00:00:00Z
visibility: public
publication_status: approved
approved_by: project-admin
approved_at: 2026-07-19T00:00:00Z
tags: [rag, routing, live-api]
---
# Skip RAG

Use live Google APIs for latest/recent records and for create, update, send, share,
schedule, or delete operations. Hidden embedding must never block a live tool result.

# Use RAG

Use tenant-scoped hybrid retrieval for semantic historical discovery and cross-document
synthesis. Apply structured filters first, preserve citations, and return empty evidence
when relevance is weak. Trusted operational knowledge is a separate OKF lookup.
