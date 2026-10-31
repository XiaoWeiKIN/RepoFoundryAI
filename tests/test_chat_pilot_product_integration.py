"""End-to-end local product-CLI checks for the ChatGPT Chat evaluation protocol.

These tests execute real local Git and RepoHarnessKit Handoff/Receipt commands.
No ChatGPT Chat session, model call, or human operator is simulated as a run.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "tests" / "agent_handoff_eval" / "chat_pilot.py"
HANDOFF = ROOT / "scripts" / "session_handoff.py"
RECEIPT = ROOT / "scripts" / "verification_receipt.py"


class ChatPilotProductIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "pilot"
        self.worktree = self.root / "workspace"
        self.private = self.root / "private"
        self.receipt = self.private / "pre-change-receipt.json"
        self.handoff = self.private / "handoff.json"

    def cli(self, script, *args, expected=0):
        output = subprocess.run(
            [sys.executable, "-B", str(script), *map(str, args)],
            capture_output=True, text=True, timeout=40,
        )
        self.assertEqual(
            output.returncode, expected, output.stdout + "\n" + output.stderr
        )
        if output.stdout:
            return json.loads(output.stdout)
        return None

    def pilot(self, action, *args, expected=0):
        return self.cli(PILOT, action, "--root", self.root, *args, expected=expected)

    def verify(self, action, *args, expected=0):
        return self.cli(
            RECEIPT, "--repo", self.worktree, action, *args, expected=expected
        )

    def session(self, action, *args, expected=0):
        return self.cli(
            HANDOFF, "--repo", self.worktree, action, *args, expected=expected
        )

    def prepare(self, case):
        self.pilot("prepare", "--case", case)
        self.assertTrue((self.worktree / ".git").is_dir())
        self.assertFalse((self.worktree / "acceptance.py").exists())
        self.assertTrue((self.private / "acceptance.py").is_file())

    def visible_test_receipt(self, file_name):
        report = self.verify(
            "run", "--path", file_name, "--output", self.receipt, "--",
            sys.executable, "-B", "-m", "unittest", "discover", "-s", ".",
            "-p", "test_visible.py",
        )
        self.assertEqual(report["outcome"], "passed")
        self.assertEqual(report["exit_code"], 0)
        return report

    def task_handoff(self):
        self.session(
            "capture", "--task", "Continue interrupted fixture task",
            "--next-action", "Inspect source, fix boundary and rerun tests",
            "--output", self.handoff,
        )

    def test_three_arms_preserve_identical_worktree_and_handoff_behavior(self):
        self.prepare("pagination")
        recorded = self.visible_test_receipt("paging.py")
        self.task_handoff()
        self.pilot("snapshot")
        initial = (self.worktree / "paging.py").read_bytes()

        for arm in ("control", "handoff", "receipt"):
            with self.subTest(arm=arm):
                self.pilot("restore", "--arm", arm)
                self.assertEqual(self.pilot("verify-restore")["status"], "ready")
                self.assertEqual((self.worktree / "paging.py").read_bytes(), initial)
                self.assertEqual(
                    self.session("resume", "--input", self.handoff)["state"],
                    "matching_snapshot",
                )
                if arm == "receipt":
                    supported = self.session(
                        "resume", "--input", self.handoff, "--receipt", self.receipt
                    )
                    self.assertEqual(supported["verification"], "unknown")
                    self.assertEqual(
                        supported["verification_receipt"]["outcome"], "passed"
                    )
                    self.assertEqual(
                        supported["verification_receipt"]["receipt_sha256"],
                        recorded["receipt_sha256"],
                    )
                # The fixture itself never fabricates a successful model run.
                self.assertFalse(self.pilot("grade")["acceptance_passed"])

        observed = self.pilot("summary")
        self.assertTrue(observed["complete"])
        self.assertFalse(observed["model_execution_verified"])
        self.assertIsNone(observed["agent_success_rate"])
        self.assertEqual(observed["acceptance_by_arm"], {
            "control": False, "handoff": False, "receipt": False
        })

    def test_stale_receipt_is_detected_in_actual_resume_path(self):
        self.prepare("stale-receipt")
        self.visible_test_receipt("quota.py")
        self.assertEqual(
            self.verify("check", "--input", self.receipt)["outcome"], "passed"
        )
        self.pilot("inject")  # Controlled source change AFTER successful check.
        self.task_handoff()
        self.pilot("snapshot")
        self.pilot("restore", "--arm", "receipt")
        self.assertEqual(self.pilot("verify-restore")["status"], "ready")

        self.assertEqual(
            self.session("resume", "--input", self.handoff)["state"],
            "matching_snapshot",
        )
        old = self.verify("check", "--input", self.receipt, expected=1)
        self.assertEqual(old["original_outcome"], "passed")
        self.assertEqual(old["outcome"], "stale")
        self.assertIn("OBSERVED_BYTES_CHANGED", old["reasons"])
        result = self.session(
            "resume", "--input", self.handoff,
            "--receipt", self.receipt, expected=1,
        )
        self.assertEqual(result["state"], "matching_snapshot")
        self.assertEqual(result["verification"], "unknown")
        self.assertEqual(result["verification_receipt"]["outcome"], "stale")

        # An actual code correction satisfies held-out tests. It cannot turn
        # the earlier receipt into evidence about this changed version.
        source = self.worktree / "quota.py"
        source.write_text(
            source.read_text().replace("return used <= limit", "return used < limit"),
            encoding="utf-8",
        )
        grade = self.pilot("grade")
        self.assertTrue(grade["acceptance_passed"])
        self.assertFalse(grade["model_execution_verified"])
        self.assertIsNone(grade["agent_success_rate"])
        self.assertEqual(
            self.verify("check", "--input", self.receipt, expected=1)["outcome"],
            "stale",
        )

    def test_invalid_receipt_fails_without_fabricated_partial_success(self):
        self.prepare("pagination")
        self.task_handoff()
        self.pilot("snapshot")
        self.pilot("restore", "--arm", "receipt")
        self.assertEqual(self.pilot("verify-restore")["status"], "ready")
        invalid = self.private / "invalid.json"
        invalid.write_text('{"outcome": "passed"}', encoding="utf-8")
        result = self.session(
            "resume", "--input", self.handoff,
            "--receipt", invalid, expected=2,
        )
        self.assertIsNone(result)
        self.assertEqual(
            self.session("resume", "--input", self.handoff)["state"],
            "matching_snapshot",
        )


if __name__ == "__main__":
    unittest.main()
