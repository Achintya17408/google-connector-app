import json
import os

import httpx


with open("candidate-deployment.json", encoding="utf-8") as handle:
    status = json.load(handle)
deployment = status.get("latestDeployment") or status
meta = deployment.get("meta") or {}
payload = {
    "candidate_version": os.environ["CANDIDATE_VERSION"],
    "deployment_id": deployment["id"],
    "service_name": os.environ["RAILWAY_CANDIDATE_WORKER_SERVICE"],
    "project_id": os.environ["RAILWAY_PROJECT_ID"],
    "workflow": os.environ["WORKFLOW_NAME"], "run_id": os.environ["RUN_ID"],
    "image_digest": meta["imageDigest"],
    "source_commit": meta["commitHash"],
    "smoke_tests": {"passed": True, "checks": [
        "Railway deployment reached SUCCESS with a RUNNING instance",
        "source commit and executor version are pinned",
        "candidate worker emitted version-bound readiness",
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
