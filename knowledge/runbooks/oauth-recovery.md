---
type: runbook
title: Google OAuth recovery
owner: project-admin
version: 1
timestamp: 2026-07-19T00:00:00Z
visibility: public
publication_status: approved
approved_by: project-admin
approved_at: 2026-07-19T00:00:00Z
tags: [oauth, scopes, recovery]
---
# Diagnosis

Distinguish an expired/used authorization code, missing newly added scope, revoked token,
testing-mode tester denial, redirect mismatch, and provider outage. Never retry an OAuth
code. Restart login with PKCE and require consent when the stored scope set is incomplete.
