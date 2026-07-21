"""Deterministic dry-run model for version-specific queue ownership."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatedRun:
    run_id: str
    executor_version: str


def simulate_claims(runs: list[SimulatedRun], control: str, candidate: str) -> dict:
    control_claims = {run.run_id for run in runs if run.executor_version == control}
    candidate_claims = {run.run_id for run in runs if run.executor_version == candidate}
    overlap = control_claims & candidate_claims
    return {
        "control": sorted(control_claims), "candidate": sorted(candidate_claims),
        "overlap": sorted(overlap), "safe": not overlap,
    }


def simulate_rollback(runs: list[SimulatedRun], control: str) -> list[SimulatedRun]:
    """New assignments return to control; already pinned runs remain unchanged."""
    return [*runs, SimulatedRun("after-rollback", control)]
