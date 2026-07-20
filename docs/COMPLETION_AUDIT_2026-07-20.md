# Completion audit — 2026-07-20

This audit distinguishes implemented engineering from conclusions that require
external credentials or longitudinal production evidence.

## Newly closed engineering gaps

- Embedding persistence has atomic PostgreSQL admission control with global,
  per-user, and payload-size limits. Rejections are reason-labelled metrics.
- Temporary Google/API 500, 502, 503, and 504 failures are retryable network
  failures; 403 remains permission, 404 remains a non-retryable execution error,
  and 429 remains rate/quota.
- Browser disconnection is tested by closing one application client, reconnecting
  through a fresh client, restoring the durable run, and cancelling it safely.
- Google Meet `space` no longer creates a false Google Chat step. Instant Meet
  creation routes to the registered Meet create/verify tools.
- Structured HTTP logs include only method, route, status, duration, a validated
  correlation ID, and a validated traceparent. Bodies, queries, users, client
  addresses, OAuth data, and Google content are excluded.
- Uvicorn's raw access log is disabled so query strings cannot bypass that
  policy. Authentication rejections are resolved to bounded route templates and
  remain observable without storing resource identifiers.
- Optional OpenTelemetry instruments FastAPI, HTTPX, and asyncpg and exports over
  OTLP/HTTP only when a safe endpoint is configured. Public non-TLS exporters are
  rejected.
- Metrics and alerts now cover OAuth outcomes, rolling offline RAG quality,
  embedding admission rejection, and immutable deployment telemetry.
- A mounted protected OKF directory is validated and namespaced under `private/`.
  Normal runtime retrieval is public-only; protected retrieval requires an
  explicit authorized code path that no current user request enables.
- Grafana Cloud receives Railway API/worker metrics through Alloy, traces through
  Tempo, and bounded-cardinality sanitized request logs through Loki. Both the
  aggregate and restricted Neon session dashboards are installed; all 17 alert
  rules evaluate successfully and route to the Grafana administrator.
- Migration 008 separates runtime prompt telemetry from valid RAG-evaluation
  samples. RAG regression is evaluated only after ten evidence-bearing examples,
  while a separate alert reports insufficient evaluation data.
- The OKF consumer follows the official v0.1 reserved-file rules: `index.md` and
  `log.md` are not concepts, the root index declares `okf_version: "0.1"`, minimal
  concepts require only `type`, and broken links remain consumable. Production
  synchronization separately enforces this project's human-approval profile.

## Direct evaluation evidence

The combined suite covers:

- Gmail, Drive, Docs, Sheets, Calendar, Meet, Chat, Tasks, Contacts, and mixed
  workflows through planner golden cases and tool/verification tests.
- Missing time, duration, timezone, Chat destination, ambiguity, misspelling,
  quota/rate limit, OAuth/permission, 4xx/5xx, and malformed model output.
- Browser/proxy disconnect, cancellation, expired worker lease, duplicate run,
  duplicate Google write, retry, partial side effects, compensation, prompt
  injection, and cross-user isolation.

The authoritative commands are the repository CI jobs, `pytest tests/`,
`scripts/run_golden_evals.py`, `scripts/run_workflow_replays.py`, and
`scripts/run_policy_evals.py`.

The final verified evidence is recorded in the progress log and repository CI.
It includes exact-image and host backend suites, 22 planner golden cases, four
no-network mutation replays, migration downgrade/forward repair through revision
008, Python/web/mobile security and build gates, healthy local and production
services, 17 evaluated Grafana Cloud rules, and 34 installed dashboard panels.

## Correctly unresolved conclusions

- Chunk-size, overlap, parent-size, query transformation, HyDE, reranker, and
  source-specific retrieval winners require labelled relevance judgments.
- Prompt/model/routing/OKF policy winners and offline RL require at least the
  approved verified sample minimum and stable train/validation/test splits.
- Pilot expansion requires real consenting users and elapsed production evidence.
- DBeaver secure-storage completion requires the user's local GUI/master-password
  action.
- External proposal email/GitHub delivery requires a chosen recipient or scoped
  publisher token and an explicit publication confirmation.

These are not replaced with fabricated synthetic production claims.
