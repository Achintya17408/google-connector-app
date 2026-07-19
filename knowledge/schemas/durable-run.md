---
type: schema
title: Durable run state and lineage
owner: project-admin
version: 1
timestamp: 2026-07-19T00:00:00Z
visibility: public
publication_status: approved
approved_by: project-admin
approved_at: 2026-07-19T00:00:00Z
tags: [runs, events, artifacts, lineage]
---
# State

A request creates one run, typed dependency steps, append-only events, exact model/tool
attempts, and verified artifact records. Every row is user-scoped. Terminal states are
completed, partial, failed, and cancelled; resume resets only a safe failed step.

# Version lineage

Record deployment, prompt, chunker, OKF, model, trace, and idempotency versions so an
incident and replay can reconstruct the exact policy that ran.
