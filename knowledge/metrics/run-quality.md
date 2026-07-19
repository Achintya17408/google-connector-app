---
type: metric
title: Run quality objectives
owner: project-admin
version: 1
timestamp: 2026-07-19T00:00:00Z
visibility: public
publication_status: approved
approved_by: project-admin
approved_at: 2026-07-19T00:00:00Z
tags: [metrics, evaluation, canary]
---
# Separate objectives

Track technical, functional, user-visible, and side-effect completion independently.
Canary gates also preserve failure rate, cancellation rate, p95 latency, token use,
retrieval quality, and tenant isolation. Do not hide safety regressions inside one reward.
