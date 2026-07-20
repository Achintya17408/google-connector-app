#!/usr/bin/env python3
"""Compare approved chunk-size hypotheses without changing production policy."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.chunking import EXPERIMENT_POLICIES
from app.rag.chunking_evaluation import evaluate_chunk_policy


def main() -> int:
    path = Path("evaluations/chunking_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    reports = [
        evaluate_chunk_policy(cases, policy)
        for policy in EXPERIMENT_POLICIES.values()
    ]
    print(json.dumps({
        "suite": "source-aware-chunking-offline-v1",
        "warning": (
            "Lexical synthetic evidence compares structural hypotheses only; it cannot "
            "authorize a production winner without labelled tenant-safe retrieval cases."
        ),
        "reports": reports,
    }, indent=2))
    failed = any(
        report["lineage_failures"] or report["evidence_failures"]
        or report["retrieval"].get("recall@3", 0) < 0.8
        for report in reports
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
