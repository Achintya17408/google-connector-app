---
type: rag-source
title: Source-aware ingestion strategies
owner: project-admin
version: 1
timestamp: 2026-07-19T00:00:00Z
visibility: public
publication_status: approved
approved_by: project-admin
approved_at: 2026-07-19T00:00:00Z
tags: [rag, chunking, provenance]
---
# Strategies

Gmail is thread-aware and removes quoted history; Docs/Drive preserve headings; PDFs
preserve page, bounding box, OCR, and tables; Sheets use headers and row ranges; Chat
preserves space/thread/sender/time; Meet transcripts preserve speakers; Calendar,
participants, Contacts, and Tasks remain structured records whenever possible.

# Lineage

Every chunk records tenant ACL, source/parent, position, content hash, chunker/embedding
version, timestamps, and tombstone state. Re-embed only when content or relevant version
metadata changes.
