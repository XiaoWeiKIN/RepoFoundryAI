"""Regression tests for the manual ChatGPT Chat A/B evaluation scaffold."""
import json
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
        self.command("grade")
        self.command("grade", exit_code=2)
        self.command("restore", "--arm", "control", exit_code=2)


if __name__ == "__main__":
    unittest.main()
