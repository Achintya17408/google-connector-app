import json
import subprocess
import time


for _ in range(60):
    value = json.loads(subprocess.check_output([
        "npx", "-y", "@railway/cli@latest", "service", "status", "--json",
        "--service", "google-connector-candidate-worker",
    ], text=True))
    status = value.get("status") or value.get("latestDeployment", {}).get("status")
    if status == "SUCCESS":
        print(json.dumps(value))
        break
    if status in {"FAILED", "CRASHED", "REMOVED"}:
        raise SystemExit(f"Candidate deployment failed: {status}")
    time.sleep(10)
else:
    raise SystemExit("Candidate deployment did not become healthy within ten minutes")
