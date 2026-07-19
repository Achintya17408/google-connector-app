# Production baseline — 2026-07-19

This is the immutable pre-pilot comparison point captured from aggregate Neon queries.
It contains no message bodies, addresses, OAuth data, or other user content.

## Legacy execution baseline

| Measure | Value |
|---|---:|
| Tool attempts | 35 |
| Tool errors | 16 (45.7%) |
| Mean tool duration | 595 ms |
| p95 tool duration | 1,235 ms |
| Feedback rows | 11 |
| Positive / negative feedback | 6 / 5 |
| Historical prompt-metric rows | 53 |
| Mean faithfulness | 0.083 |
| Mean answer relevance | 0.498 |
| Mean context recall | 0.143 |

The most frequent legacy calls were `search_gmail` (10 calls, 2 errors),
`get_gmail_message` (4 calls, 3 errors), and `reply_gmail` (4 calls, 4 errors).
These aggregates describe the old synchronous path and must not be represented as
end-to-end user latency.

## New durable path starting point

At capture time there were zero durable runs, model-call accounting rows, retrieval
events, and tracked artifacts. This is expected because the schema/executor had just
been deployed. It means no candidate canary, contextual-bandit, offline-RL, or
fine-tuning conclusion is statistically valid yet.

## Pilot comparison rules

- Compare by immutable `deployment_version`, not calendar time alone.
- Report technical, functional, user-visible, and side-effect completion separately.
- Compare p50/p95/p99 end-to-end duration, queue time, step duration, model tokens,
  tool errors, verification failures, recovery, cancellation, and orphaned artifacts.
- Segment by service, read/write risk, single/multi-service, model, RAG mode, and source.
- Do not promote unless cross-user isolation, external-write approval, idempotency,
  prompt-injection, cancellation, and artifact verification guardrails remain green.
- Use at least five measured control and candidate runs for the current mechanical
  canary gate; substantially larger samples are required for learning decisions.
