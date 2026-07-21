import json
import os
import subprocess
import time


service = os.environ["RAILWAY_CANDIDATE_WORKER_SERVICE"]
candidate_version = os.environ["CANDIDATE_VERSION"]
healthy = None
for _ in range(60):
    value = json.loads(subprocess.check_output([
        "npx", "-y", "@railway/cli@latest", "service", "status", "--json",
        "--service", service,
    ], text=True))
    deployment = value.get("latestDeployment") or value
    status = deployment.get("status")
    if status == "SUCCESS":
        meta = deployment.get("meta") or {}
        instances = deployment.get("instances") or []
        if meta.get("commitHash") != candidate_version:
            raise SystemExit("Candidate deployment source commit is not the approved commit")
        if not meta.get("imageDigest", "").startswith("sha256:"):
            raise SystemExit("Candidate deployment has no immutable image digest")
        if not instances or any(item.get("status") != "RUNNING" for item in instances):
            time.sleep(10)
            continue
        healthy = value
        break
    if status in {"FAILED", "CRASHED", "REMOVED"}:
        raise SystemExit(f"Candidate deployment failed: {status}")
    time.sleep(10)
else:
    raise SystemExit("Candidate deployment did not become healthy within ten minutes")

deployment = (healthy or {}).get("latestDeployment") or healthy
deployment_id = deployment["id"]
for _ in range(18):
    logs = subprocess.check_output([
        "npx", "-y", "@railway/cli@latest", "logs", deployment_id,
        "--service", service, "--lines", "200", "--json",
    ], text=True)
    if (
        "worker_ready role=candidate" in logs
        and f"executor_version={candidate_version}" in logs
        and "Traceback" not in logs
    ):
        break
    time.sleep(10)
else:
    raise SystemExit("Candidate worker did not emit version-bound readiness evidence")

with open("candidate-deployment.json", "w", encoding="utf-8") as handle:
    json.dump(healthy, handle)
print(json.dumps(healthy))
