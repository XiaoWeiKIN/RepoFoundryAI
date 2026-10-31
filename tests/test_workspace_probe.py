"""Regression tests for the fixed-schema Work workspace isolation checker."""

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
PROBE = ROOT / "tests" / "agent_handoff_eval" / "workspace_probe.py"


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args],
                            check=True, capture_output=True)
    return result.stdout


class WorkspaceProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.work = base / "control"
        self.work.mkdir()
        self.expected = base / "expected.json"
        self.source = self.work / "source.py"
        self.source.write_text("def f():\n    return 1\n", encoding="utf-8")
        git(self.work, "init", "-b", "main")
        git(self.work, "config", "user.email", "probe@example.invalid")
        git(self.work, "config", "user.name", "Probe Tests")
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", "initial")

    def run_probe(self, command: str, *args: str, expected_exit: int = 0) -> dict:
        process = subprocess.run(
            [sys.executable, "-B", str(PROBE), "--repo", str(self.work),
             command, *map(str, args)],
            capture_output=True, text=True, timeout=25,
        )
        self.assertEqual(process.returncode, expected_exit,
                         process.stdout + "\n" + process.stderr)
        self.assertEqual(process.stderr, "")
        return json.loads(process.stdout)

    def capture(self) -> dict:
        value = self.run_probe("capture", "--output", self.expected)
        self.assertEqual(value["status"], "captured")
        return json.loads(self.expected.read_text(encoding="utf-8"))

    def check(self, expected_exit=0) -> dict:
        return self.run_probe(
            "check", "--expected", self.expected, expected_exit=expected_exit
        )

    def test_archive_schema_exact_index_field_and_raw_nul_round_trip(self):
        # Reproduces the failed control probe's input contract: the key is
        # 'index', not 'ls_files_stage'. The two hashes are present as well.
        git(self.work, "add", ".")
        expected = self.capture()
        self.assertEqual(set(expected), {
            "root", "head", "index", "status", "files",
            "index_sha256", "status_sha256",
        })
        self.assertIn("\x00", expected["index"])
        self.assertEqual(
            expected["index"], git(self.work, "ls-files", "--stage", "-z").decode()
        )
        self.assertEqual(
            expected["index_sha256"],
            hashlib.sha256(git(self.work, "ls-files", "--stage", "-z")).hexdigest(),
        )
        self.assertEqual(self.check()["status"], "matching")
        self.assertEqual(self.check()["checks"]["index"], True)

    def test_missing_index_is_checker_error_not_environment_drift(self):
        manifest = self.capture()
        del manifest["index"]
        self.expected.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.check(expected_exit=2)
        self.assertEqual(result["status"], "checker_error")
        self.assertIn("schema", result["error"])

    def test_missing_auxiliary_hash_is_checker_error(self):
        manifest = self.capture()
        del manifest["index_sha256"]
        self.expected.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(self.check(expected_exit=2)["status"], "checker_error")

    def test_index_changed_with_same_file_bytes_is_real_drift(self):
        self.source.write_text("def f():\n    return 2\n", encoding="utf-8")
        git(self.work, "add", ".")
        self.source.write_text("def f():\n    return 1\n", encoding="utf-8")
        self.capture()
        git(self.work, "add", ".")
        result = self.check(expected_exit=1)
        self.assertEqual(result["status"], "environment_drift")
        self.assertFalse(result["checks"]["index"])
        self.assertFalse(result["checks"]["index_sha256"])
        self.assertTrue(result["checks"]["files"])

    def test_dirty_status_unchanged_but_bytes_drift(self):
        self.source.write_text("# version one\n")
        self.capture()
        self.source.write_text("# version two\n")
        result = self.check(expected_exit=1)
        self.assertEqual(result["status"], "environment_drift")
        self.assertTrue(result["checks"]["status"])
        self.assertFalse(result["checks"]["files"])
        self.assertEqual(result["mismatched_paths"], ["source.py"])

    def test_head_advance_is_drift(self):
        self.capture()
        self.source.write_text("def f():\n    return 3\n", encoding="utf-8")
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", "later")
        result = self.check(expected_exit=1)
        self.assertEqual(result["status"], "environment_drift")
        self.assertFalse(result["checks"]["head"])

    def test_untracked_probe_must_be_outside_worktree(self):
        self.capture()
        (self.work / "isolation-control.txt").write_text("probe", encoding="utf-8")
        result = self.check(expected_exit=1)
        self.assertIn("isolation-control.txt", result["mismatched_paths"])

    def test_ignored_file_bytes_are_still_part_of_worktree_fingerprint(self):
        (self.work / ".gitignore").write_text("ignored.secret\n")
        git(self.work, "add", ".gitignore")
        git(self.work, "commit", "-m", "ignore a local input")
        hidden = self.work / "ignored.secret"
        hidden.write_text("first", encoding="utf-8")
        self.capture()
        hidden.write_text("second", encoding="utf-8")
        mismatch = self.check(expected_exit=1)
        self.assertEqual(mismatch["status"], "environment_drift")
        self.assertTrue(mismatch["checks"]["status"])
        self.assertEqual(mismatch["mismatched_paths"], ["ignored.secret"])

    def test_expected_path_and_capture_output_must_be_outside_checkout(self):
        path = self.work / "unsafe.json"
        result = self.run_probe("capture", "--output", path, expected_exit=2)
        self.assertEqual(result["status"], "checker_error")
        self.assertFalse(path.exists())
        self.capture()
        result = self.run_probe("check", "--expected", self.work / "source.py",
                                expected_exit=2)
        self.assertEqual(result["status"], "checker_error")

    def test_corrupt_or_inconsistent_expected_hash_is_checker_error(self):
        manifest = self.capture()
        manifest["index_sha256"] = "0" * 64
        self.expected.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.check(expected_exit=2)
        self.assertEqual(result["status"], "checker_error")
        self.assertIn("digest", result["error"])

    def test_malformed_json_and_duplicate_key_fail_closed(self):
        self.capture()
        self.expected.write_text('{"index":1,"index":2}', encoding="utf-8")
        self.assertEqual(self.check(expected_exit=2)["status"], "checker_error")
        self.expected.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.check(expected_exit=2)["status"], "checker_error")

    def test_git_read_failure_is_checker_error(self):
        self.capture()
        git(self.work, "remote", "add", "origin", "invalid")
        # Root exists, but Git no longer offers the expected observations.
        (self.work / ".git").rename(self.work / ".git.saved")
        result = self.check(expected_exit=2)
        self.assertEqual(result["status"], "checker_error")

    def test_no_manifest_overwrite_and_read_only_check(self):
        self.capture()
        content = self.expected.read_bytes()
        self.assertEqual(self.run_probe(
            "capture", "--output", self.expected, expected_exit=2
        )["status"], "checker_error")
        self.assertEqual(self.expected.read_bytes(), content)
        before = git(self.work, "status", "--porcelain=v1", "-z",
                     "--untracked-files=all")
        self.check()
        after = git(self.work, "status", "--porcelain=v1", "-z",
                    "--untracked-files=all")
        self.assertEqual(before, after)

    def test_unrecognized_alias_rejected_instead_of_guessed(self):
        manifest = self.capture()
        manifest["ls_files_stage"] = manifest.pop("index")
        self.expected.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(self.check(expected_exit=2)["status"], "checker_error")

    def test_manifest_symlink_parent_cannot_escape_inside_observed_checkout(self):
        link = Path(self.temp.name) / "alias-into-checkout"
        link.symlink_to(self.work, target_is_directory=True)
        unsafe = link / "expected.json"
        self.assertEqual(
            self.run_probe(
                "capture", "--output", unsafe, expected_exit=2
            )["status"], "checker_error"
        )
        self.assertFalse((self.work / "expected.json").exists())

        self.capture()
        # Accessing a manifest through a parent that resolves to the checkout
        # must not disguise a path located inside the measured worktree.
        (self.work / "expected.json").write_bytes(self.expected.read_bytes())
        result = self.run_probe(
            "check", "--expected", unsafe, expected_exit=2
        )
        self.assertEqual(result["status"], "checker_error")

    def test_two_independent_check_processes_match_same_snapshot(self):
        self.capture()
        first = self.check()
        second = self.check()
        self.assertEqual(first["status"], "matching")
        self.assertEqual(second["status"], "matching")
        self.assertEqual(first["index_sha256"], second["index_sha256"])
        self.assertEqual(first["status_sha256"], second["status_sha256"])

    def test_linked_git_worktree_metadata_file_is_not_a_source(self):
        linked = Path(self.temp.name) / "linked"
        git(self.work, "worktree", "add", "-b", "probe-linked", str(linked))
        self.work = linked
        manifest = self.capture()
        self.assertNotIn(".git", manifest["files"])
        self.assertIn("source.py", manifest["files"])
        self.assertEqual(self.check()["status"], "matching")

    def test_symlink_and_invalid_manifest_path_fail_closed(self):
        other = Path(self.temp.name) / "other.txt"
        other.write_text("sensitive", encoding="utf-8")
        (self.work / "shortcut").symlink_to(other)
        self.assertEqual(self.run_probe(
            "capture", "--output", self.expected, expected_exit=2
        )["status"], "checker_error")
        self.assertFalse(self.expected.exists())
        (self.work / "shortcut").unlink()
        manifest = self.capture()
        manifest["files"]["../other.txt"] = "0" * 64
        self.expected.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(self.check(expected_exit=2)["status"], "checker_error")


if __name__ == "__main__":
    unittest.main()
