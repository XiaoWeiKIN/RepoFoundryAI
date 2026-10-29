from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/memory_review.py"
SPEC = importlib.util.spec_from_file_location("test_memory_review_module", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
memory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = memory
SPEC.loader.exec_module(memory)
AS_OF = "2026-10-28T00:00:00Z"


def node(kind="exec-plan", identity="EP-001", status="active", **values):
    return {
        "artifact_id": identity, "kind": kind, "status": status,
        "current_effect": None, "source": {"path": "docs/example.md", "sha256": "a" * 64},
        "consumers": [], "dependencies": [], "next_action_known": True,
        "dependency_review": False, "open_blockers": 0,
        "verification_revision": None, "verification_evidence": [], **values,
    }


def observation(kind="exec-plan", identity="EP-001", event="progress", at="2026-09-28T00:00:00Z", **values):
    return {"artifact_id": identity, "kind": kind, "event": event, "at": at,
            "recorded_by": "Explicit Test Owner", "reason": "Fixture observation", **values}


class MemoryPolicyTests(unittest.TestCase):
    def assess(self, value=None, records=None, **thresholds):
        policy = memory.policy_from({"schema_version": 1, "id": "test-v1", **thresholds})
        return memory.assess(value or node(), records or [], policy, memory.instant(AS_OF))

    def test_default_policy_never_assigns_age_based_expiry(self):
        policy = memory.policy_from(None)
        self.assertTrue(all(v is None for k, v in policy.items() if k.endswith("days")))
        result = self.assess(records=[observation(at="2001-01-01T00:00:00Z")])
        self.assertEqual(result["assessment"], "retain_active")
        self.assertFalse(result["automatic_mutation_allowed"])

    def test_unknown_progress_is_not_declared_idle(self):
        result = self.assess(ep_idle_days=30)
        self.assertEqual(result["assessment"], "insufficient_evidence")
        self.assertIn("PROGRESS_TIME_UNKNOWN", result["reason_codes"])
        self.assertNotIn("EP_IDLE_REVIEW_DUE", result["reason_codes"])

    def test_exact_day_boundary(self):
        old = self.assess(records=[observation()], ep_idle_days=30)
        new = self.assess(records=[observation(at="2026-09-28T00:00:01Z")], ep_idle_days=30)
        self.assertEqual(old["assessment"], "review_due")
        self.assertEqual(new["assessment"], "retain_active")

    def test_timezone_and_fractional_order(self):
        self.assertEqual(memory.instant(AS_OF), memory.instant("2026-10-28T09:00:00+09:00"))
        records = [observation(at="2026-09-28T00:00:00Z"), observation(at="2026-09-28T00:00:00.001Z")]
        self.assertEqual(self.assess(records=records)["last_progress_at"], "2026-09-28T00:00:00.001Z")

    def test_future_observation_does_not_reset_existing_clock(self):
        result = self.assess(records=[observation(), observation(at="2099-01-01T00:00:00Z")], ep_idle_days=30)
        self.assertEqual(result["last_progress_at"], "2026-09-28T00:00:00Z")
        self.assertIn("FUTURE_OBSERVATION_IGNORED", result["reason_codes"])
        self.assertIn("EP_IDLE_REVIEW_DUE", result["reason_codes"])

    def test_authorized_hold_defers_time_not_broken_dependencies(self):
        records = [observation(), observation(event="pause", next_review_at="2026-12-01T00:00:00Z")]
        result = self.assess(node(status="blocked", open_blockers=1), records, ep_idle_days=30)
        self.assertIn("TIME_REVIEW_DEFERRED", result["reason_codes"])
        self.assertNotIn("EP_IDLE_REVIEW_DUE", result["reason_codes"])
        self.assertEqual(result["status"], "blocked")
        changed = self.assess(node(dependency_review=True), records, ep_idle_days=30)
        self.assertEqual(changed["assessment"], "review_due")
        self.assertIn("EP_DEPENDENCY_REVIEW_REQUIRED", changed["reason_codes"])

    def test_scheduled_review_deadline(self):
        result = self.assess(records=[observation(event="retain", next_review_at=AS_OF)])
        self.assertIn("SCHEDULED_REVIEW_DUE", result["reason_codes"])
        self.assertEqual(result["assessment"], "review_due")

    def test_later_review_satisfies_expired_hold(self):
        adr = node("adr", "ADR-001", "accepted", current_effect=True)
        records = [
            observation("adr", "ADR-001", "retain", "2026-09-01T00:00:00Z",
                        next_review_at="2026-10-01T00:00:00Z"),
            observation("adr", "ADR-001", "review", "2026-10-15T00:00:00Z"),
        ]
        result = self.assess(adr, records, adr_review_days=30)
        self.assertEqual(result["assessment"], "retain_active")
        self.assertEqual(result["last_review_at"], "2026-10-15T00:00:00Z")
        self.assertIn("REVIEW_HOLD_SATISFIED", result["reason_codes"])
        self.assertNotIn("SCHEDULED_REVIEW_DUE", result["reason_codes"])

    def test_old_review_does_not_clear_newer_hold(self):
        adr = node("adr", "ADR-001", "accepted", current_effect=True)
        records = [
            observation("adr", "ADR-001", "review", "2026-08-15T00:00:00Z"),
            observation("adr", "ADR-001", "retain", "2026-09-01T00:00:00Z",
                        next_review_at="2026-10-01T00:00:00Z"),
        ]
        result = self.assess(adr, records)
        self.assertEqual(result["assessment"], "review_due")
        self.assertIn("SCHEDULED_REVIEW_DUE", result["reason_codes"])

    def test_new_hold_after_review_requires_another_review(self):
        adr = node("adr", "ADR-001", "accepted", current_effect=True)
        records = [
            observation("adr", "ADR-001", "retain", "2026-09-01T00:00:00Z",
                        next_review_at="2026-10-01T00:00:00Z"),
            observation("adr", "ADR-001", "review", "2026-10-15T00:00:00Z"),
            observation("adr", "ADR-001", "retain", "2026-10-20T00:00:00Z",
                        next_review_at="2026-10-25T00:00:00Z"),
        ]
        result = self.assess(adr, records)
        self.assertEqual(result["assessment"], "review_due")
        self.assertIn("SCHEDULED_REVIEW_DUE", result["reason_codes"])
        self.assertNotIn("REVIEW_HOLD_SATISFIED", result["reason_codes"])

    def test_ep_review_satisfies_hold_without_resetting_progress_clock(self):
        records = [
            observation(at="2026-09-28T00:00:00Z"),
            observation(event="pause", at="2026-09-29T00:00:00Z",
                        next_review_at="2026-10-05T00:00:00Z"),
            observation(event="review", at="2026-10-15T00:00:00Z"),
        ]
        result = self.assess(records=records, ep_idle_days=30)
        self.assertEqual(result["assessment"], "review_due")
        self.assertIn("EP_IDLE_REVIEW_DUE", result["reason_codes"])
        self.assertNotIn("SCHEDULED_REVIEW_DUE", result["reason_codes"])
        self.assertEqual(result["last_progress_at"], "2026-09-28T00:00:00Z")

    def test_current_old_adr_remains_authoritative(self):
        adr = node("adr", "ADR-001", "accepted", current_effect=True,
                   consumers=[{"kind": "exec-plan", "artifact_id": "EP-001"}])
        old = observation("adr", "ADR-001", "review", "2001-01-01T00:00:00Z")
        result = self.assess(adr, [old], adr_review_days=365)
        self.assertEqual(result["assessment"], "review_due")
        self.assertTrue(result["current_effect"])
        self.assertIn("CURRENT_AUTHORITY_NOT_AGED_OUT", result["reason_codes"])
        self.assertIn("CURRENT_ARTIFACT_CONSUMERS", result["reason_codes"])
        self.assertFalse(result["automatic_mutation_allowed"])

    def test_zero_declared_consumers_is_not_retirement_evidence(self):
        result = self.assess(node("adr", "ADR-001", "accepted", current_effect=True))
        self.assertEqual(result["assessment"], "retain_active")
        self.assertEqual(result["coverage"]["code_and_test_consumers"], "unknown")
        self.assertEqual(result["recommended_actions"], [])

    def test_amendment_is_preview_candidate_not_automatic_merge(self):
        result = self.assess(node("adr", "ADR-001", "accepted", current_effect=True, amended_by=["ADR-002"]))
        self.assertIn("AMENDMENT_CONSOLIDATION_CANDIDATE", result["reason_codes"])
        self.assertEqual(result["recommended_actions"][0]["action"], "preview_adr_consolidation")
        self.assertFalse(result["automatic_mutation_allowed"])

    def test_noncurrent_accepted_and_under_review_need_review(self):
        for status in ("accepted", "under_review"):
            result = self.assess(node("adr", "ADR-001", status, current_effect=False))
            self.assertIn("ADR_EFFECT_REVIEW_REQUIRED", result["reason_codes"])

    def test_historical_evidence_is_not_current_head_verification(self):
        result = self.assess(node(status="completed", verification_revision="git:old", verification_evidence=["ci:old"]))
        self.assertEqual(result["assessment"], "historical")
        self.assertFalse(result["current_code_verified"])
        self.assertEqual(result["verification_revision"], "git:old")

    def test_version_difference_is_review_only(self):
        spec = node("spec", "languages/go", "locked", version="1.0.0")
        record = observation("spec", "languages/go", "spec_version", "2026-10-20T00:00:00Z",
                             available_version="2.0.0", disposition="published")
        result = self.assess(spec, [record])
        self.assertIn("SPEC_VERSION_REVIEW_CANDIDATE", result["reason_codes"])
        self.assertEqual(result["version"], "1.0.0")
        stale = self.assess(spec, [record], version_snapshot_days=7)
        self.assertIn("VERSION_SNAPSHOT_STALE", stale["reason_codes"])
        self.assertNotIn("SPEC_VERSION_REVIEW_CANDIDATE", stale["reason_codes"])

    def test_absent_external_snapshot_is_unknown(self):
        result = self.assess(node("spec", "core/test", "locked", version="1"))
        self.assertIn("EXTERNAL_VERSION_UNKNOWN", result["reason_codes"])
        self.assertEqual(result["assessment"], "insufficient_evidence")

    def test_invalid_policies_and_dates(self):
        for days in (True, 0, -1, 1.5, "30", 36501):
            with self.subTest(days=days), self.assertRaises(memory.ReviewError):
                memory.policy_from({"schema_version": 1, "id": "x", "ep_idle_days": days})
        for value in ({"schema_version": 2, "id": "x"}, {"schema_version": True, "id": "x"},
                      {"schema_version": 1, "id": "x", "unexpected": 1}):
            with self.assertRaises(memory.ReviewError):
                memory.policy_from(value)
        for timestamp in ("2026-10-28", "2026-10-28T00:00:00", "2026-13-01T00:00:00Z"):
            with self.assertRaises(memory.ReviewError):
                memory.instant(timestamp)


class MemoryInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.proof = self.root / "proof.txt"
        self.proof.write_text("actual existing evidence\n", encoding="utf-8")
        self.record = observation(evidence={"path": "proof.txt", "sha256": memory.file_digest(self.proof),
                                            "revision": "git:recorded-revision"})

    def load(self, records):
        return memory.observations_from(self.root, {"schema_version": 1, "observations": records}, [node()])

    def test_evidence_digest_and_identity(self):
        result, extra = self.load([self.record])
        self.assertEqual(extra, ["proof.txt"])
        self.assertEqual(result[0]["at"], "2026-09-28T00:00:00Z")
        self.proof.write_text("drift", encoding="utf-8")
        with self.assertRaisesRegex(memory.ReviewError, "DIGEST_MISMATCH"):
            self.load([self.record])

    def test_observation_typo_and_duplicates_fail(self):
        with self.assertRaisesRegex(memory.ReviewError, "TARGET_INVALID"):
            self.load([{**self.record, "artifact_id": "EP-999"}])
        with self.assertRaisesRegex(memory.ReviewError, "DUPLICATE"):
            self.load([self.record, self.record])
        with self.assertRaisesRegex(memory.ReviewError, "FIELDS_INVALID"):
            self.load([{**self.record, "last_used": AS_OF}])

    def test_path_escape_absolute_and_symlink_fail(self):
        for path in ("../outside", "/etc/passwd", "docs/../proof.txt", "docs//x", "C:\\file"):
            with self.subTest(path=path), self.assertRaises(memory.ReviewError):
                memory.safe_path(self.root, path)
        link = self.root / "link.txt"
        link.symlink_to(self.proof)
        with self.assertRaisesRegex(memory.ReviewError, "SYMLINK"):
            memory.safe_path(self.root, "link.txt")
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "bad").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(memory.ReviewError, "SYMLINK"):
            memory.inventory(self.root, [])

    def test_duplicate_json_keys_and_nonfinite_numbers_fail(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}'):
            (self.root / "bad.json").write_text(text, encoding="utf-8")
            with self.assertRaises(memory.ReviewError):
                memory.read_json(self.root, "bad.json")

    def test_review_hold_requires_actor_reason_and_deadline(self):
        hold = observation(event="pause", next_review_at="2026-12-01T00:00:00Z")
        self.load([hold])
        for invalid in ({**hold, "recorded_by": ""}, {**hold, "reason": ""},
                        {**hold, "next_review_at": "2026-01-01T00:00:00Z"}):
            with self.assertRaises(memory.ReviewError):
                self.load([invalid])

    def test_source_addition_during_review_fails_without_partial_items(self):
        docs = self.root / "docs"
        docs.mkdir()
        def mutate(root):
            (root / "docs/new.md").write_text("concurrent input", encoding="utf-8")
            return [node()], {}, []
        with patch.object(memory, "collect", side_effect=mutate):
            with self.assertRaisesRegex(memory.ReviewError, "INPUT_CHANGED"):
                memory.build_report(self.root, as_of=AS_OF)

    def test_fixed_inputs_are_byte_deterministic_and_no_writes(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with patch.object(memory, "collect", return_value=([node()], {}, [])):
            first = memory.build_report(self.root, as_of=AS_OF)
            second = memory.build_report(self.root, as_of="2026-10-28T09:00:00+09:00")
        self.assertEqual(memory.canonical(first), memory.canonical(second))
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)


class MemoryIntegrationTests(unittest.TestCase):
    """Use the real epctl fixture and validators in the canonical test suite."""
    def setUp(self):
        from test_epctl import EpctlTestCase
        self.fixture = EpctlTestCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.init()
        self.root = self.fixture.repo

    def report(self, **kwargs):
        return memory.build_report(self.root, as_of=AS_OF, **kwargs)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def prepare(self):
        plan = self.fixture.new_ep()
        self.fixture.prepare_checkpoint_plan(plan)
        return plan

    def write_observations(self):
        proof = self.root / "proof.txt"
        proof.write_text("existing validation evidence", encoding="utf-8")
        payload = {"schema_version": 1, "observations": [observation(evidence={
            "path": "proof.txt", "sha256": memory.file_digest(proof), "revision": "test:old-workspace"})]}
        (self.root / "observations.json").write_text(json.dumps(payload), encoding="utf-8")
        (self.root / "policy.json").write_text(json.dumps({
            "schema_version": 1, "id": "team-v1", "ep_idle_days": 30}), encoding="utf-8")

    def test_cli_reads_without_git_or_writes(self):
        self.prepare()
        before = self.snapshot()
        env = {**os.environ, "PATH": ""}
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--repo", str(self.root),
                                 "--as-of", AS_OF, "--json"], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["items"][0]["assessment"], "insufficient_evidence")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(report["coverage"]["git_history"], "not_collected")

    def test_invalid_artifact_fails_and_never_emits_success(self):
        plan = self.prepare()
        self.fixture.replace_frontmatter(plan, "status", "invalid")
        before = self.snapshot()
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--repo", str(self.root),
                                 "--as-of", AS_OF, "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["input_integrity"], "incomplete")
        self.assertEqual(json.loads(result.stdout)["items"], [])
        self.assertEqual(self.snapshot(), before)

    def test_checkpoint_reindex_and_updated_do_not_rejuvenate_progress(self):
        plan = self.prepare()
        self.write_observations()
        kwargs = {"policy_path": "policy.json", "observations_path": "observations.json"}
        before = self.report(**kwargs)["items"][0]
        self.fixture.run_cli("checkpoint", "EP-001", "--slug", "maintenance", "--title", "Maintenance",
                             "--current-milestone", "Milestone 2", "--summary", "Milestone 1 is complete.",
                             "--next-action", "Edit service/handler.py", "--revision", "test:workspace")
        self.fixture.replace_frontmatter(plan, "updated", "2026-10-28")
        self.fixture.run_cli("reindex")
        after = self.report(**kwargs)["items"][0]
        self.assertEqual(before["last_progress_at"], after["last_progress_at"])
        self.assertIn("EP_IDLE_REVIEW_DUE", after["reason_codes"])
        self.assertEqual(after["status"], "blocked")
        self.assertFalse(after["current_code_verified"])

    def test_sealed_checkpoint_drift_blocks_review(self):
        self.prepare()
        cp = json.loads(self.fixture.run_cli("checkpoint", "EP-001", "--slug", "history", "--title", "History",
                                             "--current-milestone", "M2", "--summary", "Existing state",
                                             "--next-action", "Run tests", "--revision", "test:workspace").stdout)
        path = self.root / cp["path"]
        path.write_text(path.read_text(encoding="utf-8") + "\nChanged sealed history.\n", encoding="utf-8")
        with self.assertRaisesRegex(memory.ReviewError, "VALIDATION_FAILED"):
            self.report()

    def test_real_current_adr_is_retained_without_access_history(self):
        path = Path(self.fixture.run_cli("new-adr", "--slug", "current-rule", "--title", "Current rule").stdout.strip())
        self.fixture.complete_all_placeholders(path)
        self.fixture.run_cli("decide-adr", "ADR-001", "--outcome", "accepted", "--decision-maker", "Test Owner")
        before = self.snapshot()
        report = self.report()
        item = next(n for n in report["items"] if n["artifact_id"] == "ADR-001")
        self.assertEqual(item["assessment"], "retain_active")
        self.assertTrue(item["current_effect"])
        self.assertEqual(self.snapshot(), before)

    def test_spec_lock_and_digest_checked_external_snapshot(self):
        folder = self.root / "docs/.engineering"
        folder.mkdir()
        spec_path = self.root / "docs/agent-guides/managed/core/test.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text("# Locked test spec\nUse scoped checks.\n", encoding="utf-8")
        (folder / "specs.json").write_text('{"project_specs": []}', encoding="utf-8")
        lock = {
            "catalog": {"catalog_id": "test", "catalog_version": "1.0.0", "sha256": "a" * 64,
                        "resolved_revision": "b" * 40},
            "specs": [{"id": "core/test", "version": "1.0.0", "sha256": memory.file_digest(spec_path),
                       "installed_path": "docs/agent-guides/managed/core/test.md", "requires": [],
                       "applies_to": ["**/*.py"], "description": "Test source"}],
        }
        (folder / "specs.lock.json").write_text(json.dumps(lock), encoding="utf-8")
        item = self.report()["items"][0]
        self.assertEqual(item["kind"], "spec")
        self.assertEqual(item["version"], "1.0.0")
        self.assertIn("EXTERNAL_VERSION_UNKNOWN", item["reason_codes"])
        spec_path.write_text("drift", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "DRIFT"):
            self.report()


if __name__ == "__main__":
    unittest.main()
