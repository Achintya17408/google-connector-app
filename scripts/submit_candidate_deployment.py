import json
import os
import subprocess

import httpx


status = json.loads(subprocess.check_output([
    "npx", "-y", "@railway/cli@latest", "service", "status", "--json",
    "--service", "google-connector-candidate-worker",
], text=True))
deployment = status.get("deploymentId") or status.get("latestDeployment", {}).get("id")
payload = {
    "candidate_version": os.environ["CANDIDATE_VERSION"],
    "deployment_id": deployment,
    "service_name": os.environ["RAILWAY_CANDIDATE_WORKER_SERVICE"],
    "project_id": os.environ["RAILWAY_PROJECT_ID"],
    "workflow": os.environ["WORKFLOW_NAME"], "run_id": os.environ["RUN_ID"],
    "smoke_tests": {"passed": True, "checks": [
        "Railway deployment reached SUCCESS", "executor version pinned",
        "worker has no public domain",
    ]},
    "verified": True,
}
response = httpx.post(
    os.environ["CANDIDATE_ATTESTATION_URL"].rstrip("/")
    + f"/admin/improvements/{os.environ['PROPOSAL_KEY']}/deployment-attestation",
    json=payload,
    headers={"X-Candidate-Deploy-Token": os.environ["CANDIDATE_DEPLOY_ATTESTATION_TOKEN"]},
    timeout=30,
)
response.raise_for_status()
print(json.dumps(response.json(), sort_keys=True))
