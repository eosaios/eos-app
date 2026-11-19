import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("guard", Path(__file__).with_name("check-core-recovery-run.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class CoreRecoveryRun(unittest.TestCase):
    def fixture(self):
        return {"status": "completed", "conclusion": "failure", "jobs": [{
            "name": "build (darwin/amd64)", "conclusion": "failure",
            "steps": [{"name": name, "conclusion": "success"} for name in guard.REQUIRED]
                + [{"name": "Verify packaged legacy upgrade and restart", "conclusion": "failure"}],
        }]}

    def test_completed_core_can_be_reused_after_later_packaging_failure(self):
        guard.validate(self.fixture(), "darwin/amd64")

    def test_reject_unfinished_or_failed_core_and_wrong_target(self):
        for status in ["in_progress", "queued"]:
            run = self.fixture()
            run["status"] = status
            with self.assertRaises(ValueError):
                guard.validate(run, "darwin/amd64")
        for name in guard.REQUIRED:
            run = self.fixture()
            next(step for step in run["jobs"][0]["steps"] if step["name"] == name)["conclusion"] = "failure"
            with self.assertRaises(ValueError):
                guard.validate(run, "darwin/amd64")
        with self.assertRaises(ValueError):
            guard.validate(self.fixture(), "darwin/arm64")


if __name__ == "__main__":
    unittest.main()
