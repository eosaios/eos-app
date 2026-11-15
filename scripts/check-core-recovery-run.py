"""Require completed, successful Core stages, even if later app packaging failed."""
import json
import sys

REQUIRED = {
    "Build sidecar (release)", "Sign and package sidecar",
    "Verify sidecar sha256", "Preserve verified sidecar for candidate recovery",
}


def validate(run, target):
    if run.get("status") != "completed":
        raise ValueError("Core source run is not completed")
    jobs = [job for job in run.get("jobs", []) if job.get("name") == f"build ({target})"]
    if len(jobs) != 1:
        raise ValueError("expected exactly one matching Core build job")
    steps = {step["name"]: step.get("conclusion") for step in jobs[0].get("steps", [])}
    if any(steps.get(name) != "success" for name in REQUIRED):
        raise ValueError("Core build, signing, checksum and artifact stages must all succeed")


if __name__ == "__main__":
    validate(json.load(sys.stdin), sys.argv[1])
