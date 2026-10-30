"""Regression coverage for explicit revision-bound verification receipts."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "verification_receipt.py"


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


class VerificationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "receipt@example.invalid")
        git(self.repo, "config", "user.name", "Receipt Tests")
        self.source = self.repo / "code.py"
        self.source.write_text("print(1)\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "initial")
        self.receipt = self.base / "receipt.json"

    def cli(self, *args, expected=0):
        r = subprocess.run([sys.executable, "-B", str(CLI), "--repo", str(self.repo), *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, expected, r.stdout + "\n" + r.stderr)
        return r

    def run_check(self, *command, extra=(), expected=0, output=True):
        args = ["run", *extra]
        if output:
            args += ["--output", str(self.receipt)]
        args += ["--", *command]
        return json.loads(self.cli(*args, expected=expected).stdout)

    def check(self, expected=0):
        return json.loads(self.cli("check", "--input", str(self.receipt),
                                   expected=expected).stdout)

    def test_explicit_success_is_source_bound_and_reread_without_execution(self):
        good = self.run_check(sys.executable, "-c", "print('ok')")
        self.assertEqual(good["outcome"], "passed")
        self.assertEqual(good["exit_code"], 0)
        self.assertEqual(self.receipt.stat().st_mode & 0o777, 0o600)
        rec = json.loads(self.receipt.read_text())
        self.assertEqual(rec["result"]["output"]["stdout"]["bytes"], 3)
        self.assertEqual(rec["result"]["output"]["stdout"]["sha256"],
                         hashlib.sha256(b"ok\n").hexdigest())
        self.assertIn("specs.lock.json", str(rec["revision"]["observed_files"]))
        self.assertEqual(self.check()["outcome"], "passed")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_default_run_writes_only_stdout_metadata(self):
        got = self.run_check(sys.executable, "-c", "print(42)", output=False)
        self.assertEqual(got["outcome"], "passed")
        self.assertIsNone(got["written"])
        self.assertFalse(self.receipt.exists())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_command_failure_is_evidence_and_never_success(self):
        got = self.run_check(sys.executable, "-c", "raise SystemExit(3)", expected=1)
        self.assertEqual(got["outcome"], "failed")
        self.assertEqual(got["exit_code"], 3)
        result = self.check(expected=1)
        self.assertEqual(result["outcome"], "failed")

    def test_command_not_found_is_unknown(self):
        got = self.run_check("no-such-command-rf-receipt-v1", expected=1)
        self.assertEqual(got["outcome"], "unknown")
        self.assertIn("COMMAND_NOT_FOUND", got["reason_codes"])
        self.assertEqual(self.check(expected=1)["outcome"], "unknown")

    def test_source_changes_during_execution_cannot_pass(self):
        command = "from pathlib import Path; Path('code.py').write_text('changed')"
        got = self.run_check(sys.executable, "-c", command, expected=1)
        self.assertEqual(got["outcome"], "unknown")
        self.assertIn("OBSERVED_BYTES_CHANGED", got["reason_codes"])
        self.assertEqual(self.check(expected=1)["outcome"], "unknown")

    def test_post_check_git_head_drift_is_stale(self):
        self.run_check(sys.executable, "-c", "pass")
        self.source.write_text("print(2)\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "next")
        status = self.check(expected=1)
        self.assertEqual(status["outcome"], "stale")
        self.assertIn("HEAD_CHANGED", status["reasons"])

    def test_dirty_worktree_bytes_changed_are_stale(self):
        self.source.write_text("before\n")
        self.run_check(sys.executable, "-c", "pass")
        self.source.write_text("after\n")
        status = self.check(expected=1)
        self.assertIn("OBSERVED_BYTES_CHANGED", status["reasons"])

    def test_git_index_changes_with_same_worktree_are_stale(self):
        self.source.write_text("first\n")
        git(self.repo, "add", ".")
        self.source.write_text("second\n")
        self.run_check(sys.executable, "-c", "pass")
        git(self.repo, "add", ".")  # files unchanged, but Git index changes
        status = self.check(expected=1)
        self.assertIn("STAGED_INDEX_CHANGED", status["reasons"])

    def test_new_untracked_file_stales(self):
        self.run_check(sys.executable, "-c", "pass")
        (self.repo / "new.txt").write_text("new")
        self.assertIn("WORKTREE_STATUS_CHANGED", self.check(expected=1)["reasons"])

    def test_spec_lock_is_checked_even_without_explicit_flag(self):
        self.run_check(sys.executable, "-c", "pass")
        lock = self.repo / "docs" / ".engineering" / "specs.lock.json"
        lock.parent.mkdir(parents=True)
        lock.write_text('{"version":"new"}')
        self.assertIn("OBSERVED_BYTES_CHANGED", self.check(expected=1)["reasons"])

    def test_ignore_file_requires_explicit_path_to_be_bound(self):
        (self.repo / ".gitignore").write_text("hidden.txt\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-m", "ignore")
        hidden = self.repo / "hidden.txt"
        hidden.write_text("one")
        self.run_check(sys.executable, "-c", "pass", extra=("--path", "hidden.txt"))
        hidden.write_text("two")
        self.assertIn("OBSERVED_BYTES_CHANGED", self.check(expected=1)["reasons"])

    def test_base_reference_is_resolved_and_recorded(self):
        current = git(self.repo, "rev-parse", "HEAD")
        self.run_check(sys.executable, "-c", "pass", extra=("--base-ref", "HEAD"))
        self.assertEqual(json.loads(self.receipt.read_text())["revision"]["base_sha"], current)
        self.assertEqual(self.check()["outcome"], "passed")

    def test_unverified_source_outside_worktree_is_not_captured(self):
        self.run_check(sys.executable, "-c", "pass")
        self.assertEqual(self.check()["source_integrity"],
                         "digest_checked_not_authenticated")
        self.assertIn("ignored_and_external_unknown", self.check()["scope"])

    def test_no_overwrite_and_no_output_inside_repo(self):
        self.run_check(sys.executable, "-c", "pass")
        saved = self.receipt.read_bytes()
        self.cli("run", "--output", str(self.receipt),
                 "--", sys.executable, "-c", "pass", expected=2)
        self.assertEqual(self.receipt.read_bytes(), saved)
        inside = self.repo / "receipt.json"
        self.cli("run", "--output", str(inside), "--",
                 sys.executable, "-c", "pass", expected=2)
        self.assertFalse(inside.exists())

    def test_tampered_digest_is_error_not_stale(self):
        self.run_check(sys.executable, "-c", "pass")
        record = json.loads(self.receipt.read_text())
        record["result"]["outcome"] = "failed"
        self.receipt.write_text(json.dumps(record))
        self.cli("check", "--input", str(self.receipt), expected=2)

    def test_forged_success_with_valid_digest_is_rejected(self):
        self.run_check(sys.executable, "-c", "raise SystemExit(5)", expected=1)
        record = json.loads(self.receipt.read_text())
        record["result"]["outcome"] = "passed"
        body = {k: v for k, v in record.items() if k != "payload_sha256"}
        record["payload_sha256"] = hashlib.sha256(
            (json.dumps(body, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False) + "\n").encode()).hexdigest()
        self.receipt.write_text(json.dumps(record))
        self.cli("check", "--input", str(self.receipt), expected=2)

    def test_symlink_receipt_is_rejected(self):
        self.run_check(sys.executable, "-c", "pass")
        link = self.base / "link.json"
        link.symlink_to(self.receipt)
        self.cli("check", "--input", str(link), expected=2)

    def test_command_argv_not_shell_expanded(self):
        got = self.run_check(sys.executable, "-c", "import sys; print(sys.argv[1])",
                             "$(touch never-created)", output=False)
        self.assertEqual(got["outcome"], "passed")
        self.assertFalse((self.repo / "never-created").exists())

    def test_path_traversal_and_invalid_base_rejected(self):
        self.cli("run", "--path", "../escape", "--", sys.executable, "-c", "pass", expected=2)
        self.cli("run", "--base-ref", "--danger", "--", sys.executable, "-c", "pass", expected=2)
        self.assertFalse(self.receipt.exists())


if __name__ == "__main__":
    unittest.main()
