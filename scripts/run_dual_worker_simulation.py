import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.improvements.canary_simulator import SimulatedRun, simulate_claims, simulate_rollback


control = "control-v1"
candidate = "candidate-v2"
runs = [SimulatedRun("control-run", control), SimulatedRun("candidate-run", candidate)]
before = simulate_claims(runs, control, candidate)
assert before["safe"] and before["control"] == ["control-run"]
assert before["candidate"] == ["candidate-run"]
after = simulate_claims(simulate_rollback(runs, control), control, candidate)
assert after["safe"] and after["candidate"] == ["candidate-run"]
assert after["control"] == ["after-rollback", "control-run"]
print("dual-worker simulation passed: version claims are disjoint and rollback is sticky")
