"""Regression tests for the manual ChatGPT Chat A/B evaluation scaffold."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tests" / "agent_handoff_eval" / "chat_pilot.py"


class ChatPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / "pilot"

    def command(self, action, *options, exit_code=0):
        cmd = [sys.executable, "-B", str(CLI), action, "--root", str(self.base),
               *options]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        self.assertEqual(p.returncode, exit_code, p.stderr + p.stdout)
        return json.loads(p.stdout) if exit_code == 0 else p

    def test_three_arms_restore_the_identical_interruption_snapshot(self):
        self.command("prepare", "--case", "pagination")
        self.command("snapshot")
        expected = (self.base / "workspace" / "paging.py").read_bytes()
        for arm in ("control", "handoff", "receipt"):
            self.command("restore", "--arm", arm)
            self.assertEqual((self.base / "workspace" / "paging.py").read_bytes(), expected)
            verified = self.command("verify-restore")
            self.assertEqual(verified["status"], "ready")
            graded = self.command("grade")
            self.assertFalse(graded["acceptance_passed"])
            self.assertIsNone(graded["agent_success_rate"])
            self.assertFalse(graded["model_execution_verified"])
        totals = self.command("summary")
        self.assertTrue(totals["complete"])
        self.assertIsNone(totals["agent_success_rate"])

    def test_failing_case_can_be_fixed_and_grader_does_not_claim_agent(self):
        self.command("prepare", "--case", "stale-receipt")
        old = (self.base / "workspace" / "quota.py").read_bytes()
        self.command("inject")
        self.assertNotEqual(old, (self.base / "workspace" / "quota.py").read_bytes())
        self.command("inject", exit_code=2)
        self.command("snapshot")
        self.command("restore", "--arm", "receipt")
        self.command("verify-restore")
        path = self.base / "workspace" / "quota.py"
        path.write_text(path.read_text().replace("return used <= limit", "return used < limit"))
        got = self.command("grade")
        self.assertTrue(got["acceptance_passed"])
        self.assertFalse(got["model_execution_verified"])

    def test_no_overwrite_or_unmanaged_restore(self):
        self.command("prepare", "--case", "pagination")
        self.command("prepare", "--case", "pagination", exit_code=2)
        self.command("restore", "--arm", "control", exit_code=2)
        self.command("snapshot")
        self.command("snapshot", exit_code=2)
        self.command("restore", "--arm", "control")
        self.command("grade", exit_code=2)
        self.command("verify-restore")
        self.command("grade")
        self.command("grade", exit_code=2)
        self.command("restore", "--arm", "control", exit_code=2)

    def test_cross_call_source_mutation_is_invalid_and_retry_requires_opt_in(self):
        self.command("prepare", "--case", "pagination")
        self.command("snapshot")
        self.command("restore", "--arm", "control")
        target = self.base / "workspace" / "paging.py"
        target.write_text(target.read_text() + "\n# other context overwrote source\n")
        result = self.command("verify-restore", exit_code=1)
        self.assertEqual(json.loads(result.stdout)["status"], "invalid_environment")
        self.assertIn("paging.py", json.loads(result.stdout)["mismatched_paths"])
        self.command("grade", exit_code=2)
        self.command("restore", "--arm", "control", exit_code=2)
        excluded = list((self.base / "results").glob("invalid-*.json"))
        self.assertEqual(len(excluded), 1)
        self.assertEqual(json.loads(excluded[0].read_text())["status"],
                         "invalid_environment")
        self.command("restore", "--arm", "control", "--retry-invalid")
        self.assertEqual(self.command("verify-restore")["status"], "ready")
        self.assertFalse(self.command("grade")["acceptance_passed"])

    def test_head_and_index_changes_are_rejected(self):
        for variation in ("head", "index"):
            with self.subTest(variation=variation):
                self.base = Path(self.temp.name) / ("pilot-" + variation)
                self.command("prepare", "--case", "pagination")
                self.command("snapshot")
                self.command("restore", "--arm", "handoff")
                source = self.base / "workspace" / "paging.py"
                if variation == "index":
                    source.write_text(source.read_text() + "\n# staged\n")
                    subprocess.run(["git", "-C", str(source.parent), "add", "paging.py"],
                                   check=True)
                    source.write_text(source.read_text() + "\n# different worktree\n")
                else:
                    subprocess.run(["git", "-C", str(source.parent), "config",
                                    "user.name", "test"], check=True)
                    subprocess.run(["git", "-C", str(source.parent), "config",
                                    "user.email", "test@example.invalid"], check=True)
                    source.write_text(source.read_text() + "\n# commit\n")
                    subprocess.run(["git", "-C", str(source.parent), "add", "paging.py"],
                                   check=True)
                    subprocess.run(["git", "-C", str(source.parent), "commit", "-m", "drift"],
                                   check=True, capture_output=True)
                rejected = self.command("verify-restore", exit_code=1)
                codes = json.loads(rejected.stdout)["mismatched_paths"]
                self.assertIn("index_sha256" if variation == "index" else "head", codes)

    def test_dirty_status_unmodified_but_bytes_drift(self):
        self.command("prepare", "--case", "pagination")
        source = self.base / "workspace" / "paging.py"
        source.write_text(source.read_text() + "\n# original dirty\n")
        self.command("snapshot")
        self.command("restore", "--arm", "receipt")
        source.write_text(source.read_text().replace("original dirty", "changed dirty"))
        failed = self.command("verify-restore", exit_code=1)
        mismatches = json.loads(failed.stdout)["mismatched_paths"]
        self.assertIn("paging.py", mismatches)
        self.assertNotIn("status_sha256", mismatches)

    def test_untrusted_snapshot_or_concurrent_pilot_lock_fails_closed(self):
        self.command("prepare", "--case", "pagination")
        self.command("snapshot")
        lock = self.base / ".pilot-command.lock"
        lock.mkdir()
        self.command("restore", "--arm", "control", exit_code=2)
        lock.rmdir()
        saved = self.base / "snapshots" / "interruption" / "paging.py"
        saved.write_text("print('tampered')\n")
        self.command("restore", "--arm", "control", exit_code=2)
        self.assertTrue((self.base / "workspace" / "paging.py").is_file())

    def test_mtime_refresh_does_not_invalidate_bytes(self):
        self.command("prepare", "--case", "pagination")
        self.command("snapshot")
        self.command("restore", "--arm", "control")
        path = self.base / "workspace" / "paging.py"
        os.utime(path, None)
        self.assertEqual(self.command("verify-restore")["status"], "ready")

    def test_cannot_start_next_arm_while_previous_is_active(self):
        self.command("prepare", "--case", "pagination")
        self.command("snapshot")
        self.command("restore", "--arm", "control")
        self.command("restore", "--arm", "handoff", exit_code=2)
        self.command("verify-restore")
        self.command("restore", "--arm", "handoff", exit_code=2)
        self.command("grade")
        self.command("restore", "--arm", "handoff")
        self.assertEqual(self.command("verify-restore")["status"], "ready")



if __name__ == "__main__":
    unittest.main()
