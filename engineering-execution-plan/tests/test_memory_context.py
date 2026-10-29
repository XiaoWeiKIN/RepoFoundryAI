from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/memory_context.py"
AS_OF = "2026-10-29T00:00:00Z"


class MemoryContextIntegrationTests(unittest.TestCase):
    def setUp(self):
        from test_epctl import EpctlTestCase
        self.fixture = EpctlTestCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.init()
        self.root = self.fixture.repo

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}

    def cli(self, *args, expected=0):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--repo", str(self.root),
             "--as-of", AS_OF, "--json", *args],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": ""},
        )
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def plan(self, slug="test-plan"):
        path = self.fixture.new_ep(slug)
        self.fixture.prepare_checkpoint_plan(path)
        return path

    def adr(self):
        path = Path(self.fixture.run_cli("new-adr", "--slug", "current-rule", "--title", "Current rule").stdout.strip())
        self.fixture.complete_all_placeholders(path)
        self.fixture.run_cli("decide-adr", "ADR-001", "--outcome", "accepted", "--decision-maker", "Test Owner")
        return path

    def test_empty_scope_has_no_auto_corpus_context_or_writes(self):
        self.plan()
        before = self.snapshot()
        result = self.cli()
        self.assertEqual(result["selection"], [])
        self.assertEqual(result["effective_context"], "")
        self.assertEqual(result["sources"], {})
        self.assertEqual(self.snapshot(), before)

    def test_explicit_ep_snapshot_and_background_shadow(self):
        direct = self.plan("direct-plan")
        background = self.plan("background-plan")
        snapshot = self.fixture.load_epctl().section(background.read_text(encoding="utf-8"), "Current Snapshot")
        self.fixture.replace_section_body(background, "Current Snapshot", snapshot + "\nBackground details " * 100)
        before = self.snapshot()
        result = self.cli("--ep", "EP-001", "--background-ep", "EP-002")
        by_id = {row["artifact_id"]: row for row in result["selection"]}
        self.assertEqual(by_id["EP-001"]["tier"], "direct")
        self.assertEqual(by_id["EP-002"]["proposed_action"], "reference")
        self.assertEqual(result["effective_context"], result["baseline"]["text"])
        self.assertIn("Background details", result["effective_context"])
        self.assertNotIn("Background details", result["proposal"]["text"])
        self.assertIn(background.relative_to(self.root).as_posix(), result["proposal"]["text"])
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(direct.is_file())

    def test_current_adr_and_constraint_refs_use_existing_resolver(self):
        self.adr()
        ep = self.fixture.load_epctl()
        baseline = ep.resolve_decision_context(self.root, ["ADR-001"])
        before = self.snapshot()
        result = self.cli("--adr", "ADR-001")
        self.assertEqual(result["resolved_constraint_refs"], baseline["constraint_refs"])
        self.assertTrue(result["selection"][0]["current_effect"])
        self.assertFalse(result["authority_changed"])
        self.assertEqual(self.snapshot(), before)

    def test_view_uses_current_closure(self):
        self.adr()
        self.fixture.run_cli("set-decision-view", "test-domain", "--title", "Test domain", "--adr", "ADR-001", "--apply")
        result = self.cli("--view", "test-domain")
        self.assertEqual(result["selection"][0]["tier"], "related")
        self.assertTrue(result["selection"][0]["current_effect"])

    def test_historical_adr_requires_explicit_intent_and_stays_noncurrent(self):
        self.adr()
        self.fixture.run_cli("transition-adr", "ADR-001", "--to", "retired",
                             "--decision-maker", "Test Owner", "--reason", "Fixture retirement", "--apply")
        failed = self.cli("--adr", "ADR-001", expected=2)
        self.assertEqual(failed["selection"], [])
        self.assertIn("HISTORY", failed["error"])
        before = self.snapshot()
        result = self.cli("--adr", "ADR-001", "--history")
        self.assertTrue(result["selection"][0]["historical"])
        self.assertFalse(result["selection"][0]["current_effect"])
        self.assertEqual(self.snapshot(), before)

    def test_invalid_ep_not_hidden_by_missing_optional_report(self):
        plan = self.plan()
        self.fixture.replace_frontmatter(plan, "status", "invalid")
        before = self.snapshot()
        result = self.cli("--ep", "EP-001", "--review-report", "missing.json", expected=2)
        self.assertEqual(result["input_integrity"], "incomplete")
        self.assertEqual(result["selection"], [])
        self.assertEqual(self.snapshot(), before)

    def test_optional_report_failures_do_not_block_valid_sources(self):
        self.plan()
        baseline = self.cli("--ep", "EP-001")
        for path, content in (("missing.json", None), ("broken.json", "{"),
                              ("unsupported.json", '{"schema_version": 999}')):
            if content is not None:
                (self.root / path).write_text(content, encoding="utf-8")
            result = self.cli("--ep", "EP-001", "--review-report", path)
            self.assertEqual(result["effective_context"], baseline["effective_context"])
            self.assertEqual(result["hint_status"]["status"], "unavailable")

    def test_real_review_annotations_never_replace_current_authority(self):
        self.adr()
        review = SCRIPT.with_name("memory_review.py")
        completed = subprocess.run([sys.executable, "-B", str(review), "--repo", str(self.root),
                                    "--as-of", AS_OF, "--json"], capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        (self.root / "review.json").write_text(completed.stdout, encoding="utf-8")
        result = self.cli("--adr", "ADR-001", "--review-report", "review.json")
        row = result["selection"][0]
        self.assertEqual(row["review_hint"]["status"], "source_matched")
        self.assertTrue(row["current_effect"])
        self.assertFalse(row["review_hint"]["authority_verified"])

    def test_spec_path_match_is_only_a_navigation_candidate(self):
        folder = self.root / "docs/.engineering"
        folder.mkdir()
        spec = self.root / "docs/agent-guides/managed/core/test.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# Test spec\nUse scoped checks.\n", encoding="utf-8")
        (folder / "specs.json").write_text('{"project_specs": []}', encoding="utf-8")
        lock = {"catalog": {"catalog_id": "test", "catalog_version": "1.0.0", "sha256": "a" * 64,
                            "resolved_revision": "b" * 40},
                "specs": [{"id": "core/test", "version": "1.0.0", "sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
                           "installed_path": "docs/agent-guides/managed/core/test.md", "requires": [],
                           "applies_to": ["**/*.py"], "description": "Test source"}]}
        (folder / "specs.lock.json").write_text(json.dumps(lock), encoding="utf-8")
        before = self.snapshot()
        result = self.cli("--path", "service/test.py")
        self.assertEqual(result["selection"][0]["kind"], "spec")
        self.assertEqual(result["coverage"]["code_to_adr"], "unknown")
        self.assertEqual(self.snapshot(), before)
        spec.write_text("tampered", encoding="utf-8")
        self.assertIn("DRIFT", self.cli("--path", "service/test.py", expected=2)["error"])

    def test_unsafe_task_path_and_symlink_source_are_rejected(self):
        self.assertIn("PATH", self.cli("--path", "../escape.py", expected=2)["error"])
        plan = self.plan()
        content = plan.read_bytes()
        plan.unlink()
        outside = self.root / "outside.md"
        outside.write_bytes(content)
        plan.symlink_to(outside)
        result = self.cli("--ep", "EP-001", expected=2)
        self.assertIn("SYMLINK", result["error"])
        self.assertEqual(outside.read_bytes(), content)

    def test_repeat_is_deterministic_and_explicit_overrides_background(self):
        self.plan()
        first = self.cli("--ep", "EP-001", "--background-ep", "EP-001")
        second = self.cli("--ep", "EP-001", "--background-ep", "EP-001")
        self.assertEqual(first, second)
        self.assertEqual(first["selection"][0]["tier"], "direct")
        self.assertEqual(len(first["selection"]), 1)


if __name__ == "__main__":
    unittest.main()
