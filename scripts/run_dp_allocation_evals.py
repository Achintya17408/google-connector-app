import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.improvements.dp_allocation import (
    AllocationOption, allocate_periodic_quota, select_workflow_options,
)


def main() -> None:
    workflows = [
        AllocationOption("safe-read", "8b-rag", 600, 800, 1, 0.72),
        AllocationOption("safe-read", "70b-rag", 1800, 1400, 1, 0.90),
        AllocationOption("complex-write", "constrained-70b", 2400, 1800, 3, 0.96),
        AllocationOption("complex-write", "unsafe-8b", 500, 500, 8, 10.0),
    ]
    workflow = select_workflow_options(
        workflows, token_budget=3200, latency_budget_ms=2600, max_risk=3,
    )
    runs = [
        AllocationOption("run-1", "validated", 900, 900, 1, 0.9, "user-a"),
        AllocationOption("run-2", "validated", 900, 900, 1, 0.85, "user-a"),
        AllocationOption("run-3", "validated", 700, 700, 1, 0.8, "user-b"),
        AllocationOption("run-4", "unsafe", 100, 100, 9, 10.0, "user-c"),
    ]
    quota = allocate_periodic_quota(
        runs, token_budget=1800, worker_time_budget_ms=1800,
        max_risk=3, per_user_limit=1,
    )
    report = {
        "suite": "offline-dp-allocation-v1",
        "workflow": {
            "selected": [item.option_id for item in workflow.selected],
            "value": workflow.expected_value,
            "tokens": workflow.token_cost,
            "latency_ms": workflow.latency_ms,
        },
        "periodic_quota": {
            "selected": [item.task_id for item in quota.selected],
            "value": quota.expected_value,
            "tokens": quota.token_cost,
            "worker_time_ms": quota.latency_ms,
        },
        "production_decision": "offline oracle only; human canary and verified samples required",
    }
    assert "unsafe-8b" not in report["workflow"]["selected"]
    assert "run-4" not in report["periodic_quota"]["selected"]
    assert len({item.user_id for item in quota.selected}) == len(quota.selected)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
