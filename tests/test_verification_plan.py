"""Contract coverage for the read-only Spec-aware verification planner."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.spec_git_fixture import create_git_catalog, git

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "verification_plan.py"
FOUNDRYCTL = ROOT / "scripts" / "foundryctl.py"


class VerificationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture.cleanup)
        base = Path(cls.fixture.name)
        cls.template = base / "target-template"
        cls.template.mkdir()
        catalog, _ = create_git_catalog(base)
        git(cls.template, "init", "-b", "main")
        (cls.template / "go.mod").write_text(
            "module example.test/verification-plan\n", encoding="utf-8"
        )
        source = cls.template / "service" / "main.go"
        source.parent.mkdir()
        source.write_text("package service\n", encoding="utf-8")
        git(cls.template, "add", ".")
        git(cls.template, "-c", "user.name=Plan Tests",
            "-c", "user.email=plan@example.invalid",
            "commit", "-m", "baseline")
        result = subprocess.run(
            [sys.executable, "-B", str(FOUNDRYCTL), "--repo",
             str(cls.template), "bootstrap", "--profile", "codex",
             "--governance-profile", "strict",
             "--spec-repository", catalog.resolve().as_uri(),
             "--spec-version", "0.1.0", "--spec", "languages/go", "--apply"],
            capture_output=True, text=True, timeout=90,
        )
        if result.returncode:
            raise AssertionError(result.stdout + "\n" + result.stderr)
        git(cls.template, "add", ".")
        git(cls.template, "-c", "user.name=Plan Tests",
            "-c", "user.email=plan@example.invalid",
            "commit", "-m", "install locked specs")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "target"
        subprocess.run(["git", "clone", "-q", str(self.template), str(self.repo)],
                       check=True, capture_output=True, timeout=25)
        git(self.repo, "config", "user.name", "Plan Tests")
        git(self.repo, "config", "user.email", "plan@example.invalid")
        self.source = self.repo / "service" / "main.go"

    def cli(self, *args, expected=0):
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "--repo", str(self.repo), *args],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, expected,
                         result.stdout + "\n" + result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    def test_go_source_diff_routes_specs_and_verification_rows(self):
        self.source.write_text("package service\n// change\n", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["mode"], "shadow")
        self.assertEqual(result["status"], "advisory")
        self.assertEqual(result["revision"]["changed_paths"], ["service/main.go"])
        self.assertEqual(result["specs"]["state"], "validated")
        specs = {x["id"] for x in result["specs"]["candidate_specs"]}
        self.assertIn("languages/go", specs)
        self.assertIn("core/semantic-naming", specs)
        named = {r["id"]: r for r in result["specs"]["candidate_requirements"]}
        self.assertIn("GO-TEST-001", named)
        requirement = named["GO-TEST-001"]
        self.assertIn("Focused Go tests", requirement["published_verification_row"])
        self.assertEqual(requirement["applicability"], "requires_agent_review")
        self.assertEqual(requirement["execution"], "not_executed")
        self.assertTrue(requirement["source"]["sha256"])
        self.assertEqual(result["executed_checks"], [])
        self.assertEqual(result["verification_outcome"], "not_executed")
        self.assertIn("REQUIREMENT_ACTIVATION_NOT_ATTESTED", result["evidence_gaps"])

    def test_repeat_is_deterministic_and_read_only(self):
        self.source.write_text("package service\n// changed\n", encoding="utf-8")
        first = self.cli()
        second = self.cli()
        self.assertEqual(first, second)
        self.assertEqual(git(self.repo, "status", "--porcelain=v1").stdout.strip(),
                         " M service/main.go")

    def test_no_changes_is_not_evidence_of_success(self):
        result = self.cli()
        self.assertEqual(result["revision"]["changed_paths"], [])
        self.assertEqual(result["suggested_checks"], [])
        self.assertEqual(result["executed_checks"], [])
        self.assertEqual(result["verification_outcome"], "not_executed")

    def test_staged_and_untracked_and_explicit_paths_are_collected(self):
        self.source.write_text("package service\n// modified\n", encoding="utf-8")
        git(self.repo, "add", "service/main.go")
        new = self.repo / "service" / "new.go"
        new.write_text("package service\n", encoding="utf-8")
        ignored = self.repo / "local.secret"
        ignored.write_text("example\n", encoding="utf-8")
        (self.repo / ".git/info/exclude").write_text("local.secret\n")
        result = self.cli("--path", "local.secret")
        self.assertEqual(
            result["revision"]["changed_paths"],
            ["local.secret", "service/main.go", "service/new.go"],
        )
        observed = {r["path"]: r for r in result["revision"]["observed_files"]}
        self.assertEqual(observed["local.secret"]["kind"], "regular")
        self.assertEqual(observed["service/new.go"]["kind"], "regular")

    def test_staged_only_bytes_remain_routed_if_worktree_was_reverted(self):
        original = self.source.read_text(encoding="utf-8")
        self.source.write_text("package service\n// staged different bytes\n")
        git(self.repo, "add", "service/main.go")
        self.source.write_text(original, encoding="utf-8")
        result = self.cli()
        self.assertIn("service/main.go", result["revision"]["changed_paths"])
        self.assertEqual(result["verification_outcome"], "not_executed")

    def test_internal_git_path_is_not_a_verification_input(self):
        self.cli("--path", ".git/config", expected=2)

    def test_rename_routing_sees_both_ends(self):
        renamed = self.repo / "service" / "main.py"
        self.source.rename(renamed)
        changed = self.cli()["revision"]["changed_paths"]
        self.assertEqual(changed, ["service/main.go", "service/main.py"])

    def test_dependency_file_requires_full_suite_review(self):
        (self.repo / "go.mod").write_text("module example.test/new\n")
        result = self.cli()
        self.assertTrue(result["requires_full_suite_review"])
        self.assertIn("full_suite", {r["id"] for r in result["suggested_checks"]})
        self.assertNotIn("passed", str(result["verification_outcome"]))

    def test_unknown_extension_requires_full_suite_review(self):
        (self.repo / "opaque.bin").write_bytes(b"\x00\x01")
        result = self.cli()
        self.assertTrue(result["requires_full_suite_review"])

    def test_prose_doc_stays_advisory_without_claiming_irrelevance(self):
        (self.repo / "README.md").write_text("# Notes\n", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result["status"], "advisory")
        self.assertIn("documentation_consumer_review",
                      {row["id"] for row in result["suggested_checks"]})
        self.assertEqual(result["verification_outcome"], "not_executed")

    def test_corrupt_managed_spec_fails_closed_to_full_suite(self):
        file = self.repo / "docs/agent-guides/managed/languages/go.md"
        file.write_text("# CORRUPTED\n", encoding="utf-8")
        result = self.cli(expected=1)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["specs"]["state"], "invalid")
        self.assertTrue(result["requires_full_suite_review"])
        self.assertEqual(result["executed_checks"], [])

    def test_missing_spec_installation_is_incomplete(self):
        root = Path(self.tmp.name) / "plain"
        root.mkdir()
        git(root, "init", "-b", "main")
        (root / "file.py").write_text("print(1)\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "-c", "user.name=Plan Tests",
            "-c", "user.email=plan@example.invalid",
            "commit", "-m", "plain")
        self.repo = root
        (root / "file.py").write_text("print(2)\n")
        result = self.cli(expected=1)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["specs"]["gaps"], ["SPECS_NOT_INSTALLED"])
        self.assertTrue(result["requires_full_suite_review"])

    def test_invalid_base_and_path_are_rejected(self):
        self.cli("--base=--malicious", expected=2)
        self.cli("--path", "../outside", expected=2)
        self.cli("--base", "missingBranchName", expected=2)

    def test_diff_against_older_base_commit_includes_committed_changes(self):
        original = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.source.write_text("package service\n// committed\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "change")
        result = self.cli("--base", original)
        self.assertEqual(result["revision"]["base_sha"], original)
        self.assertIn("service/main.go", result["revision"]["changed_paths"])
        self.assertEqual(result["verification_outcome"], "not_executed")


if __name__ == "__main__":
    unittest.main()
