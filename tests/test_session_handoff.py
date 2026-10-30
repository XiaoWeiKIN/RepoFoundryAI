"""Source-backed CLI regression tests for explicit Session Handoff / Resume v1."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "session_handoff.py"


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                       text=True, check=True)
    return p.stdout.strip()


class SessionHandoffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "tests@example.invalid")
        git(self.repo, "config", "user.name", "Handoff Tests")
        (self.repo / "src").mkdir()
        self.source = self.repo / "src" / "main.py"
        self.source.write_text("print('before')\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "baseline")
        self.output = self.base / "handoff.json"

    def cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        p = subprocess.run([sys.executable, "-B", str(CLI), "--repo", str(self.repo),
                            *args], capture_output=True, text=True)
        self.assertEqual(p.returncode, expected, p.stdout + "\n" + p.stderr)
        return p

    def capture(self, *extra: str, output: bool = True) -> dict:
        command = ["capture", "--task", "Fix cursor edge case",
                   "--next-action", "Run targeted regression tests", *extra]
        if output:
            command += ["--output", str(self.output)]
        return json.loads(self.cli(*command).stdout)

    def resume(self, expected: int = 0) -> dict:
        return json.loads(self.cli("resume", "--input", str(self.output),
                                   expected=expected).stdout)

    def test_default_capture_is_stdout_only_and_non_mutating(self) -> None:
        before = git(self.repo, "status", "--porcelain")
        record = self.capture(output=False)
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["repository"]["head"], git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(record["repository"]["changes"], [])
        self.assertEqual(before, git(self.repo, "status", "--porcelain"))
        self.assertFalse(self.output.exists())
        self.assertEqual(record["payload_sha256"], hashlib.sha256(
            (json.dumps({k: v for k, v in record.items() if k != "payload_sha256"},
                        sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")).hexdigest())

    def test_explicit_output_is_private_nonoverwriting_and_round_trips(self) -> None:
        result = self.capture("--evidence", "pytest run: manually reported",
                              "--blocker", "Await API detail")
        self.assertEqual(result["verification"], "not_evaluated")
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        checked = self.resume()
        self.assertEqual(checked["state"], "matching_snapshot")
        self.assertEqual(checked["verification"], "unknown")
        self.assertEqual(checked["evidence_refs"], ["pytest run: manually reported"])
        self.assertEqual(checked["blockers"], ["Await API detail"])
        self.assertEqual(checked["source_integrity"], "digest_checked_not_authenticated")
        saved = self.output.read_bytes()
        self.cli("capture", "--task", "again", "--next-action", "again",
                 "--output", str(self.output), expected=2)
        self.assertEqual(saved, self.output.read_bytes())

    def test_modified_tracked_source_stales_verification(self) -> None:
        self.capture()
        self.source.write_text("print('after')\n")
        got = self.resume(expected=1)
        self.assertEqual(got["state"], "stale")
        self.assertEqual(got["verification"], "stale")
        self.assertIn("WORKTREE_STATUS_CHANGED", got["reasons"])

    def test_existing_dirty_source_changed_without_status_change_is_stale(self) -> None:
        self.source.write_text("print('one')\n")
        self.capture()
        self.source.write_text("print('two')\n")
        result = self.resume(expected=1)
        self.assertIn("OBSERVED_BYTES_CHANGED", result["reasons"])

    def test_head_advance_marks_stale(self) -> None:
        self.capture()
        self.source.write_text("print('committed')\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "implementation")
        self.assertIn("HEAD_CHANGED", self.resume(expected=1)["reasons"])

    def test_branch_switch_even_on_same_head_marks_stale(self) -> None:
        self.capture()
        git(self.repo, "switch", "-c", "feature")
        self.assertIn("BRANCH_CHANGED", self.resume(expected=1)["reasons"])

    def test_new_untracked_file_marks_stale(self) -> None:
        self.capture()
        (self.repo / "new.txt").write_text("new", encoding="utf-8")
        got = self.resume(expected=1)
        self.assertIn("WORKTREE_STATUS_CHANGED", got["reasons"])

    def test_existing_untracked_file_bytes_are_observed(self) -> None:
        untracked = self.repo / "new.txt"
        untracked.write_text("first", encoding="utf-8")
        self.capture()
        untracked.write_text("second", encoding="utf-8")
        self.assertIn("OBSERVED_BYTES_CHANGED", self.resume(expected=1)["reasons"])

    def test_explicit_clean_path_is_hash_bound(self) -> None:
        self.capture("--path", "src/main.py")
        record = json.loads(self.output.read_text())
        self.assertEqual(record["repository"]["observed_files"][0]["path"], "src/main.py")
        self.source.write_text("changed", encoding="utf-8")
        self.assertEqual(self.resume(expected=1)["verification"], "stale")

    def test_rename_preserves_source_and_destination_paths(self) -> None:
        git(self.repo, "mv", "src/main.py", "src/renamed.py")
        record = self.capture(output=False)
        names = [r["path"] for r in record["repository"]["observed_files"]]
        self.assertEqual(names, ["src/main.py", "src/renamed.py"])
        self.assertEqual(record["repository"]["changes"][0]["previous_path"], "src/main.py")

    def test_symlink_is_hashed_without_following_external_target(self) -> None:
        external = self.base / "secret.txt"
        external.write_text("private", encoding="utf-8")
        (self.repo / "shortcut").symlink_to(external)
        record = self.capture(output=False)
        obj = next(x for x in record["repository"]["observed_files"] if x["path"] == "shortcut")
        self.assertEqual(obj["kind"], "symlink")
        self.assertNotEqual(obj["sha256"], hashlib.sha256(external.read_bytes()).hexdigest())

    def test_symlink_parent_in_explicit_path_is_rejected(self) -> None:
        (self.repo / "alias").symlink_to(self.base, target_is_directory=True)
        self.cli("capture", "--task", "x", "--next-action", "y",
                 "--path", "alias/secret.txt", expected=2)

    def test_repo_traversal_and_noncanonical_paths_are_rejected(self) -> None:
        for value in ("../secret", "/tmp/secret", "src//main.py", "src/./main.py"):
            with self.subTest(path=value):
                self.cli("capture", "--task", "x", "--next-action", "y",
                         "--path", value, expected=2)
        self.assertFalse(self.output.exists())

    def test_subdirectory_cannot_impersonate_worktree_root(self) -> None:
        p = subprocess.run([sys.executable, "-B", str(CLI), "--repo",
                            str(self.repo / "src"), "capture", "--task", "x",
                            "--next-action", "y"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_corrupted_or_duplicate_record_is_rejected(self) -> None:
        self.capture()
        record = json.loads(self.output.read_text(encoding="utf-8"))
        record["next_action"] = "fabricated"
        self.output.write_text(json.dumps(record), encoding="utf-8")
        self.cli("resume", "--input", str(self.output), expected=2)
        self.output.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        self.cli("resume", "--input", str(self.output), expected=2)

    def test_unexpected_schema_field_is_rejected_even_with_matching_digest(self) -> None:
        self.capture()
        record = json.loads(self.output.read_text())
        record["privileged"] = True
        payload = {k: v for k, v in record.items() if k != "payload_sha256"}
        record["payload_sha256"] = hashlib.sha256(
            (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False) + "\n").encode()).hexdigest()
        self.output.write_text(json.dumps(record), encoding="utf-8")
        self.cli("resume", "--input", str(self.output), expected=2)

    def test_symlink_input_and_output_are_rejected(self) -> None:
        record = self.base / "real.json"
        record.write_text("not a record", encoding="utf-8")
        self.output.symlink_to(record)
        self.cli("resume", "--input", str(self.output), expected=2)
        self.cli("capture", "--task", "x", "--next-action", "y",
                 "--output", str(self.output), expected=2)
        self.assertEqual(record.read_text(), "not a record")

    def test_oversized_input_and_no_parent_directory_fail_without_writes(self) -> None:
        self.output.write_bytes(b"x" * (129 * 1024))
        self.cli("resume", "--input", str(self.output), expected=2)
        self.cli("capture", "--task", "x", "--next-action", "y",
                 "--output", str(self.base / "missing" / "handoff.json"), expected=2)
        self.assertFalse((self.base / "missing").exists())

    def test_observed_file_size_limit_fails_closed(self) -> None:
        huge = self.repo / "large.bin"
        with huge.open("wb") as out:
            out.truncate(64 * 1024 * 1024 + 1)
        self.cli("capture", "--task", "x", "--next-action", "y", expected=2)
        self.assertFalse(self.output.exists())

    def test_output_inside_worktree_is_rejected_before_any_write(self) -> None:
        local = self.repo / "handoff.json"
        self.cli("capture", "--task", "x", "--next-action", "y",
                 "--output", str(local), expected=2)
        self.assertFalse(local.exists())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_nonstring_sha_and_nonfinite_json_fail_as_input_errors(self) -> None:
        self.capture()
        record = json.loads(self.output.read_text())
        record["repository"]["head"] = 123
        payload = {k: v for k, v in record.items() if k != "payload_sha256"}
        record["payload_sha256"] = hashlib.sha256(
            (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False) + "\n").encode()).hexdigest()
        self.output.write_text(json.dumps(record), encoding="utf-8")
        self.cli("resume", "--input", str(self.output), expected=2)
        self.output.write_text('{"invalid":NaN}', encoding="utf-8")
        self.cli("resume", "--input", str(self.output), expected=2)

    def test_resume_can_read_scoped_verification_without_claiming_task_completion(self) -> None:
        self.capture()
        receipt = self.base / "checks.json"
        checks = ROOT / "scripts" / "verification_receipt.py"
        run = subprocess.run(
            [sys.executable, "-B", str(checks), "--repo", str(self.repo),
             "run", "--output", str(receipt), "--", sys.executable, "-c", "pass"],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        response = json.loads(self.cli(
            "resume", "--input", str(self.output),
            "--receipt", str(receipt),
        ).stdout)
        self.assertEqual(response["state"], "matching_snapshot")
        self.assertEqual(response["verification"], "unknown")
        self.assertEqual(response["verification_receipt"]["outcome"], "passed")
        self.source.write_text("print('changed')\n")
        invalid = json.loads(self.cli(
            "resume", "--input", str(self.output),
            "--receipt", str(receipt), expected=1,
        ).stdout)
        self.assertEqual(invalid["state"], "stale")
        self.assertEqual(invalid["verification_receipt"]["outcome"], "stale")

    def test_resume_rejects_invalid_receipt(self) -> None:
        self.capture()
        bad = self.base / "bad.json"
        bad.write_text("not json")
        self.cli("resume", "--input", str(self.output),
                 "--receipt", str(bad), expected=2)

    def test_record_remains_local_without_git_or_ep_mutations(self) -> None:
        self.capture()
        self.resume()
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertFalse((self.repo / "docs" / "exec-plans").exists())
        self.assertFalse((self.repo / ".repo-foundry").exists())


if __name__ == "__main__":
    unittest.main()
