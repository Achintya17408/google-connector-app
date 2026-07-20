"""Offline greedy-vs-DP context packing comparison; no live APIs."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.context_packer import select_context_documents


CASES = [
    {"id": "two-medium-beat-one-large", "budget": 192, "documents": [
        {"content": "large evidence " * 90, "score": 0.9, "citation": {"id": "a"}},
        {"content": "medium b " * 45, "score": 0.62, "citation": {"id": "b"}},
        {"content": "medium c " * 45, "score": 0.62, "citation": {"id": "c"}},
    ]},
    {"id": "citation-and-recency-value", "budget": 160, "documents": [
        {"content": "old " * 100, "score": 0.8},
        {"content": "cited " * 65, "score": 0.62, "citation": {"id": "b"}},
        {"content": "recent " * 65, "score": 0.6, "recency_bonus": 0.1,
         "citation": {"id": "c"}},
    ]},
]

reports = []
for case in CASES:
    greedy = select_context_documents(case["documents"], case["budget"], strategy="greedy")
    dynamic = select_context_documents(case["documents"], case["budget"], strategy="dp")
    reports.append({
        "case": case["id"], "budget": case["budget"],
        "greedy_tokens": greedy.estimated_tokens,
        "greedy_value": round(greedy.estimated_value, 6),
        "dp_tokens": dynamic.estimated_tokens,
        "dp_value": round(dynamic.estimated_value, 6),
        "value_delta": round(dynamic.estimated_value - greedy.estimated_value, 6),
    })

failures = [item for item in reports if item["dp_tokens"] > item["budget"]]
print(json.dumps({
    "suite": "context-packing-dp-v1", "cases": len(reports),
    "failures": failures, "reports": reports,
    "production_decision": "feature-flagged candidate; labelled canary still required",
}, indent=2))
if failures:
    raise SystemExit(1)
