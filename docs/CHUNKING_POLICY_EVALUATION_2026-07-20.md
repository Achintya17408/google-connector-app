# Offline chunk-policy evaluation — 2026-07-20

The repository now compares the approved 256, 512, 768, and 1,024-token hypotheses
without network access or production mutations. Fixtures cover Gmail cleanup, Drive
heading hierarchy and long sections, PDF blocks/tables, Sheets row groups, Meet speaker
turns, and Calendar atomic records.

Command:

```bash
python scripts/run_chunking_evals.py
```

| Target | Chunks | Mean tokens | Max tokens including provenance | Duplicate ratio | Recall@3 | MRR | nDCG@3 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 37 | 203.162 | 268 | 0.025510 | 0.886111 | 1.0 | 1.0 |
| 512 | 24 | 299.333 | 524 | 0 | 0.933333 | 1.0 | 1.0 |
| 768 | 19 | 371.105 | 780 | 0 | 0.979167 | 1.0 | 1.0 |
| 1,024 | 18 | 395.500 | 1,035 | 0 | 1.0 | 1.0 |

All policies have zero missing-evidence and lineage failures. The maximum includes a
small repeated title/section provenance prefix, so it may exceed the payload target.
The 256-token duplicate ratio exposes an expected weakness in a deliberately repetitive
long fixture.

These are synthetic lexical results, not production relevance judgments. They prove
the experiment machinery and structural invariants, not that 1,024 tokens is best.
Production selection remains blocked until at least ten tenant-safe, provenance-bearing
`rag_evaluation` cases cover context precision/recall, faithfulness, relevance,
citations, permission isolation, latency, and cost. The deployed default is unchanged.
