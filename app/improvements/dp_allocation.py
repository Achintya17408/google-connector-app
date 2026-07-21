"""Bounded offline DP oracles for policy selection and periodic quota planning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationOption:
    task_id: str
    option_id: str
    token_cost: int
    latency_ms: int
    risk: int
    expected_value: float
    user_id: str = ""


@dataclass(frozen=True)
class AllocationDecision:
    selected: tuple[AllocationOption, ...]
    expected_value: float
    token_cost: int
    latency_ms: int
    strategy: str


def select_workflow_options(
    options: list[AllocationOption], *, token_budget: int, latency_budget_ms: int,
    max_risk: int, token_quantum: int = 100, latency_quantum_ms: int = 100,
    max_tasks: int = 30, max_options_per_task: int = 8,
) -> AllocationDecision:
    """Multiple-choice knapsack: select at most one validated option per task."""
    if token_budget <= 0 or latency_budget_ms <= 0:
        return AllocationDecision((), 0.0, 0, 0, "dp_multiple_choice")
    grouped: dict[str, list[AllocationOption]] = {}
    for option in options:
        if option.risk <= max_risk and option.token_cost >= 0 and option.latency_ms >= 0:
            grouped.setdefault(option.task_id, []).append(option)
    token_cap = max(1, token_budget // token_quantum)
    latency_cap = max(1, latency_budget_ms // latency_quantum_ms)
    states: dict[tuple[int, int], tuple[float, tuple[AllocationOption, ...]]] = {
        (0, 0): (0.0, ())
    }
    for task_id in sorted(grouped)[:max_tasks]:
        updated = dict(states)
        task_options = sorted(grouped[task_id], key=lambda item: item.option_id)
        for option in task_options[:max_options_per_task]:
            token_units = (option.token_cost + token_quantum - 1) // token_quantum
            latency_units = (option.latency_ms + latency_quantum_ms - 1) // latency_quantum_ms
            for (used_tokens, used_latency), (value, selected) in states.items():
                key = (used_tokens + token_units, used_latency + latency_units)
                if key[0] > token_cap or key[1] > latency_cap:
                    continue
                candidate = (value + option.expected_value, (*selected, option))
                current = updated.get(key)
                if current is None or candidate[0] > current[0]:
                    updated[key] = candidate
        states = _prune_states(updated, 20_000)
    _, (value, selected) = max(
        states.items(), key=lambda item: (item[1][0], -item[0][0], -item[0][1]),
    )
    return AllocationDecision(
        selected, value, sum(item.token_cost for item in selected),
        sum(item.latency_ms for item in selected), "dp_multiple_choice",
    )


def allocate_periodic_quota(
    runs: list[AllocationOption], *, token_budget: int, worker_time_budget_ms: int,
    max_risk: int, per_user_limit: int = 2, token_quantum: int = 100,
    time_quantum_ms: int = 100, max_candidates: int = 50,
) -> AllocationDecision:
    """Periodic 0/1 quota oracle; immediate dispatch remains queue/heap based."""
    eligible = [item for item in runs[:max_candidates] if item.risk <= max_risk]
    token_cap = max(1, token_budget // token_quantum)
    time_cap = max(1, worker_time_budget_ms // time_quantum_ms)
    states: dict[tuple[int, int, tuple[tuple[str, int], ...]],
                 tuple[float, tuple[AllocationOption, ...]]] = {
        (0, 0, ()): (0.0, ())
    }
    for option in eligible:
        updated = dict(states)
        token_units = (option.token_cost + token_quantum - 1) // token_quantum
        time_units = (option.latency_ms + time_quantum_ms - 1) // time_quantum_ms
        for (used_tokens, used_time, user_counts), (value, selected) in states.items():
            counts = dict(user_counts)
            user = option.user_id or option.task_id
            if counts.get(user, 0) >= per_user_limit:
                continue
            key_tokens, key_time = used_tokens + token_units, used_time + time_units
            if key_tokens > token_cap or key_time > time_cap:
                continue
            counts[user] = counts.get(user, 0) + 1
            key = (key_tokens, key_time, tuple(sorted(counts.items())))
            candidate = (value + option.expected_value, (*selected, option))
            current = updated.get(key)
            if current is None or candidate[0] > current[0]:
                updated[key] = candidate
        states = _prune_states(updated, 30_000)
    _, (value, selected) = max(
        states.items(), key=lambda item: (item[1][0], -item[0][0], -item[0][1]),
    )
    return AllocationDecision(
        selected, value, sum(item.token_cost for item in selected),
        sum(item.latency_ms for item in selected), "dp_periodic_quota",
    )


def _prune_states(states: dict, limit: int) -> dict:
    if len(states) <= limit:
        return states
    return dict(sorted(
        states.items(),
        key=lambda item: (item[1][0], -item[0][0], -item[0][1]),
        reverse=True,
    )[:limit])
