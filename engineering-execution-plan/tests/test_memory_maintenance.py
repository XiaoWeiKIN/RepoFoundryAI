from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/memory_maintenance.py"
REVIEW_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/memory_review.py"
sys.path.insert(0, str(SCRIPT.parent))
import memory_maintenance as maintenance  # noqa: E402
import memory_review as review  # noqa: E402

AS_OF = "2026-10-29T00:00:00Z"


def item(kind="exec-plan", identity="EP-001", status="active",
         assessment="review_due", **updates):
    value = {
        "artifact_id": identity, "kind": kind, "status": status,
        "assessment": assessment, "current_effect": None,
        "source": {"path": "docs/example.md", "sha256": "a" * 64},
        "consumers": [], "dependencies": [], "coverage": {
            "consumers": "declared_artifact_relationships_only",
            "code_and_test_consumers": "unknown"},
        "reason_codes": ["EP_IDLE_REVIEW_DUE"],
        "open_blockers": 0, "amended_by": [], "next_action_known": True,
        "automatic_mutation_allowed": False,
    }
    value.update(updates)
    return value


def report(items):
    return {
        "schema_version": 1, "input_integrity": "validated",
        "read_only": True, "items": items,
    }


def rows(*ids, working_set="bounded"):
    return {
        "plans": [{
            "id": identity, "completion": "archive_blocked",
            "completion_blockers": ["open_blocker"],
            "working_set": working_set,
        } for identity in ids],
        "adrs": [],
    }


def adr_maintenance(actions=()):
    return {"actions": list(actions)}


class ActionSelectionTests(unittest.TestCase):
    def plan(self, nodes, plans=None, actions=()):
        return maintenance.plan_actions(
            report(nodes), plans if plans is not None else rows("EP-001"),
            adr_maintenance(actions),
        )

    def test_idle_ep_proposes_owner_review_not_cancellation(self):
        node = item(status="blocked", open_blockers=2, dependencies=["ADR-001"],
                    consumers=[], reason_codes=["EP_IDLE_REVIEW_DUE", "EP_HAS_OPEN_BLOCKERS"])
        action, = self.plan([node])
        self.assertEqual(action["type"], "review_continuation")
        self.assertEqual(action["preview_command"], "epctl status --json")
        self.assertEqual(action["impact"]["declared_dependencies"], ["ADR-001"])
        self.assertEqual(action["impact"]["open_blockers"], 2)
        self.assertEqual(action["authorization_before_mutation"],
                         "plan_owner_for_any_completion_or_cancellation")
        self.assertFalse(action["automatic_mutation_allowed"])
        self.assertTrue(action["preview_only"])
        self.assertNotIn("--apply", action["preview_command"])

    def test_explicit_hold_without_due_does_not_force_review_or_cancel(self):
        node = item(assessment="retain_active", reason_codes=[
            "EXPLICIT_REVIEW_HOLD", "TIME_REVIEW_DEFERRED",
        ], status="blocked")
        self.assertEqual(self.plan([node]), [])

    def test_unknown_activity_is_not_idle_or_abandoned(self):
        node = item(assessment="insufficient_evidence",
                    reason_codes=["PROGRESS_TIME_UNKNOWN"])
        self.assertEqual(self.plan([node]), [])

    def test_large_workset_only_suggests_existing_checkpoint_preview(self):
        node = item(assessment="retain_active", reason_codes=[])
        action, = self.plan([node], rows("EP-001", working_set="checkpoint_required"))
        self.assertEqual(action["type"], "preview_ep_compaction")
        self.assertEqual(action["preview_command"], "epctl auto-checkpoint EP-001")
        self.assertEqual(action["checkpoint_eligibility"], "requires_existing_cli_preview")
        self.assertFalse(action["automatic_mutation_allowed"])

    def test_large_due_ep_has_two_distinct_review_actions(self):
        actions = self.plan([item()], rows("EP-001", working_set="checkpoint_recommended"))
        self.assertEqual({a["type"] for a in actions},
                         {"review_continuation", "preview_ep_compaction"})
        self.assertEqual(len(set(a["action_id"] for a in actions)), len(actions))

    def test_historical_ep_and_adrs_cause_no_mutations_or_actions(self):
        self.assertEqual(self.plan([
            item(status="completed", assessment="historical"),
            item("adr", "ADR-001", "superseded", "historical",
                 reason_codes=["TERMINAL_HISTORY_RETAINED"]),
        ]), [])

    def test_current_old_adr_never_automatically_retired(self):
        adr = item("adr", "ADR-009", "accepted", "review_due",
                   current_effect=True,
                   reason_codes=["PERIODIC_REVIEW_DUE",
                                 "CURRENT_AUTHORITY_NOT_AGED_OUT"],
                   consumers=[{"kind": "exec-plan", "artifact_id": "EP-001"}])
        action, = self.plan([adr], rows())
        self.assertEqual(action["type"], "review_adr_effect")
        self.assertTrue(action["impact"]["current_effect"])
        self.assertEqual(action["impact"]["declared_consumers"][0]["artifact_id"], "EP-001")
        self.assertIn("decision_owner", action["authorization_before_mutation"])
        self.assertNotIn("transition-adr", action["preview_command"])
        self.assertFalse(action["automatic_mutation_allowed"])

    def test_amendment_relation_only_proposes_preview(self):
        adr = item("adr", "ADR-009", "accepted", "retain_active",
                   current_effect=True, amended_by=["ADR-011"],
                   reason_codes=["AMENDMENT_CONSOLIDATION_CANDIDATE"])
        action, = self.plan([adr], rows())
        self.assertEqual(action["type"], "preview_adr_consolidation")
        self.assertEqual(action["preview_command"],
                         "epctl adr-consolidation-plan --adr ADR-009 --json")
        self.assertEqual(action["impact"]["amended_by"], ["ADR-011"])
        self.assertEqual(action["consolidation_is_semantic"],
                         "not_proven_by_amendment_edges")

    def test_amendment_on_noncurrent_adr_does_not_claim_consolidation(self):
        adr = item("adr", "ADR-009", "under_review", "review_due",
                   current_effect=False, amended_by=["ADR-011"],
                   reason_codes=["ADR_EFFECT_REVIEW_REQUIRED",
                                 "AMENDMENT_CONSOLIDATION_CANDIDATE"])
        actions = self.plan([adr], rows())
        self.assertEqual([x["type"] for x in actions], ["review_adr_effect"])

    def test_spec_version_observation_is_only_review(self):
        spec = item("spec", "languages/go", "locked", "review_due",
                    reason_codes=["SPEC_VERSION_REVIEW_CANDIDATE"],
                    version="1.9.0", catalog_revision="a" * 40)
        action, = self.plan([spec], rows())
        self.assertEqual(action["type"], "review_spec_version")
        self.assertEqual(action["impact"]["locked_version"], "1.9.0")
        self.assertEqual(action["preview_command"], "foundryctl --repo . spec validate")
        self.assertTrue(action["never_auto_update_spec_lock"])

    def test_missing_spec_version_observation_is_not_upgrade_evidence(self):
        spec = item("spec", "languages/go", "locked", "insufficient_evidence",
                    reason_codes=["EXTERNAL_VERSION_UNKNOWN"])
        self.assertEqual(self.plan([spec], rows()), [])

    def test_adaptive_maintenance_pack_action_needs_actor_and_reason(self):
        group = {
            "type": "pack_history", "affected": {
                "adrs": ["ADR-100", "ADR-101", "ADR-102"],
                "plans": [], "views": []},
            "reason_dimensions": ["eligible_terminal_adrs"], "severity": "action_required",
            "next_command": 'epctl pack-historical-adrs ADR-100 ADR-101 ADR-102 --packed-by "$ACTOR" --reason "$WHY" --json',
            "authority_required": "explicit actor, reason, preview and apply authorization",
        }
        action, = self.plan([], rows(), actions=[group])
        self.assertTrue(action["preview_only"])
        self.assertEqual(action["impact"]["affected"]["adrs"],
                         ["ADR-100", "ADR-101", "ADR-102"])
        self.assertNotIn("--apply", action["preview_command"])
        self.assertFalse(action["automatic_mutation_allowed"])

    def test_invalid_review_or_duplicate_is_rejected(self):
        with self.assertRaisesRegex(maintenance.MaintenanceError, "NOT_VALIDATED"):
            maintenance.plan_actions({"schema_version": 1, "items": []}, rows(),
                                     adr_maintenance())
        duplicate = [item(), item()]
        with self.assertRaisesRegex(maintenance.MaintenanceError, "DUPLICATE"):
            self.plan(duplicate)

    def test_actions_are_deterministic_without_authority_scores(self):
        a = item("spec", "languages/go", "locked", "review_due",
                 reason_codes=["SPEC_VERSION_REVIEW_CANDIDATE"])
        b = item()
        c = item("adr", "ADR-001", "accepted", "review_due",
                 reason_codes=["ADR_EFFECT_REVIEW_REQUIRED"], current_effect=False)
        first = self.plan([a, b, c])
        second = self.plan([c, a, b])
        self.assertEqual(review.canonical(first), review.canonical(second))
        self.assertFalse(any("memory_score" in x or "authority_score" in x
                             for x in first))

    def test_consolidation_uses_actual_resolver_impact(self):
        adr = item("adr", "ADR-007", "accepted", "retain_active",
                   current_effect=True,
                   reason_codes=["AMENDMENT_CONSOLIDATION_CANDIDATE"])
        actions = self.plan([adr], rows())
        response = {
            "preview_only": True, "non_normative": True,
            "resolved_adrs": ["ADR-007"], "amendment_edges": [],
            "active_plan_impact": [{"id": "EP-001", "adr_refs": ["ADR-007"]}],
            "proposed_overlap": [], "source_digests": [],
            "recommendation": "defer_while_active_or_proposed_work_depends_on_context",
        }
        with patch.object(maintenance, "_load", return_value=None):
            class Fake:
                def adr_consolidation_plan(self, repo, view, refs):
                    self.args = (view, refs)
                    return response
            fake = Fake()
            maintenance._decorate_consolidations(fake, Path("/tmp"), actions)
            self.assertEqual(fake.args, ("", ["ADR-007"]))
        impact = actions[0]["impact"]["resolver_preview"]
        self.assertEqual(impact["active_plan_impact"][0]["id"], "EP-001")

    def test_resolver_error_never_becomes_verified_preview(self):
        adr = item("adr", "ADR-007", "accepted", "retain_active",
                   current_effect=True,
                   reason_codes=["AMENDMENT_CONSOLIDATION_CANDIDATE"])
        actions = self.plan([adr], rows())
        class Bad:
            def adr_consolidation_plan(self, *args):
                raise RuntimeError("invalid source")
        with self.assertRaisesRegex(maintenance.MaintenanceError, "PREVIEW_UNAVAILABLE"):
            maintenance._decorate_consolidations(Bad(), Path("/tmp"), actions)


class MaintenanceIntegrationTests(unittest.TestCase):
    def setUp(self):
        from test_epctl import EpctlTestCase
        self.fixture = EpctlTestCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.init()
        self.root = self.fixture.repo

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT),
                                 "--repo", str(self.root), "--as-of", AS_OF,
                                 *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def prep_ep(self):
        plan = self.fixture.new_ep()
        self.fixture.prepare_checkpoint_plan(plan)
        return plan

    def test_cli_is_read_only_without_git_or_policy(self):
        self.prep_ep()
        before = self.snapshot()
        env = {**os.environ, "PATH": ""}
        result = subprocess.run([sys.executable, "-B", str(SCRIPT),
                                 "--repo", str(self.root), "--as-of", AS_OF, "--json"],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["authority_changed"])
        self.assertEqual(payload["summary"]["review_due_artifacts"], 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(payload["coverage"]["git_history"], "not_collected")

    def test_verified_idle_evidence_routes_to_plan_owner_without_writes(self):
        self.prep_ep()
        proof = self.root / "proof.txt"
        proof.write_text("auditable progress\n", encoding="utf-8")
        (self.root / "policy.json").write_text(json.dumps({
            "schema_version": 1, "id": "owner-review-v1",
            "ep_idle_days": 30,
        }), encoding="utf-8")
        (self.root / "observations.json").write_text(json.dumps({
            "schema_version": 1, "observations": [{
                "kind": "exec-plan", "artifact_id": "EP-001", "event": "progress",
                "at": "2026-08-01T00:00:00Z", "recorded_by": "Fixture Owner",
                "reason": "Last verified milestone",
                "evidence": {"path": "proof.txt", "sha256": review.file_digest(proof),
                             "revision": "test:old-revision"},
            }]
        }), encoding="utf-8")
        kwargs = {"as_of": AS_OF, "policy_path": "policy.json",
                  "observations_path": "observations.json"}
        before = self.snapshot()
        first = maintenance.build_plan(self.root, **kwargs)
        second = maintenance.build_plan(self.root, **kwargs)
        self.assertEqual(review.canonical(first), review.canonical(second))
        self.assertEqual(self.snapshot(), before)
        actions = [a for a in first["actions"] if a["kind"] == "exec-plan"]
        self.assertEqual([a["type"] for a in actions], ["review_continuation"])
        self.assertIn("EP_IDLE_REVIEW_DUE", actions[0]["reason_codes"])
        self.assertFalse(actions[0]["automatic_mutation_allowed"])
        self.assertFalse(first["current_code_verified"])


    def test_real_adr_amendment_uses_existing_consolidation_resolver(self):
        research = self.fixture.new_research("maintenance-review")
        self.fixture.conclude_research(research)
        base = self.fixture.new_adr("current-decision")
        self.fixture.accept_adr(base)
        amendment = Path(
            self.fixture.run_cli(
                "new-adr", "--slug", "current-amendment",
                "--title", "Current amendment", "--research", "R-001",
                "--amends", "ADR-001", "--amends-constraint", "ADR-001#C-001",
            ).stdout.strip()
        )
        self.fixture.accept_adr(amendment, "ADR-002")
        before = self.snapshot()
        plan = maintenance.build_plan(self.root, as_of=AS_OF)
        previews = [a for a in plan["actions"]
                    if a["type"] == "preview_adr_consolidation"]
        self.assertTrue(previews)
        self.assertTrue(all(a["preview_only"] for a in previews))
        self.assertTrue(all(not a["automatic_mutation_allowed"]
                            for a in previews))
        for candidate in previews:
            resolver = candidate["impact"]["resolver_preview"]
            self.assertIn("source_digests", resolver)
            self.assertIn("amendment_edges", resolver)
            self.assertIn("resolved_adrs", resolver)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_artifact_produces_no_partial_action_plan(self):
        plan = self.prep_ep()
        self.fixture.replace_frontmatter(plan, "status", "invalid")
        before = self.snapshot()
        result = self.cli("--json", expected=2)
        value = json.loads(result.stdout)
        self.assertEqual(value["input_integrity"], "incomplete")
        self.assertEqual(value["actions"], [])
        self.assertEqual(self.snapshot(), before)

    def test_historical_ep_is_not_autocancelled(self):
        plan = self.prep_ep()
        before = self.snapshot()
        result = maintenance.build_plan(self.root, as_of=AS_OF)
        self.assertFalse(any(a.get("mutation_route_after_approval", "").endswith("--apply")
                             for a in result["actions"]))
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
