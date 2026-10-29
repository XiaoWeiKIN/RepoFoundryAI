from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import memory_maintenance as maintenance  # noqa: E402
import memory_review as review  # noqa: E402

AS_OF = "2026-10-29T00:00:00Z"
RELEASED_AT = "2026-09-03T08:50:04Z"
RELEASE_VERSION = "0.8.3"


def adr_action(identity: str, resolved: list[str], *, consumer="EP-006",
               digest="a" * 64):
    return {
        "action_id": "adr:" + identity + ":preview_adr_consolidation",
        "artifact_id": identity,
        "kind": "adr",
        "type": "preview_adr_consolidation",
        "preview_command": "epctl adr-consolidation-plan --adr " + identity + " --json",
        "source": {"path": "docs/adr/" + identity + ".md", "sha256": digest},
        "impact": {"resolver_preview": {
            "resolved_adrs": sorted(resolved),
            "amendment_edges": [],
            "active_plan_impact": [{"id": consumer, "adr_refs": ["ADR-001"]}],
            "proposed_overlap": [],
            "source_digests": [
                {"adr_id": value, "document_sha256": digest, "payload_sha256": ""}
                for value in sorted(resolved)
            ],
            "recommendation": "defer_while_active_or_proposed_work_depends_on_context",
        }},
    }


class ReviewPacketTests(unittest.TestCase):
    def test_exact_closure_and_impact_are_grouped_without_losing_sources(self):
        actions = [
            adr_action("ADR-008", ["ADR-001", "ADR-008"]),
            adr_action("ADR-001", ["ADR-001", "ADR-008"]),
            adr_action("ADR-007", ["ADR-007"]),
        ]
        packets = maintenance.group_adr_review_packets(actions)
        self.assertEqual(len(packets), 2)
        pair = next(x for x in packets if len(x["member_artifact_ids"]) == 2)
        self.assertEqual(pair["member_artifact_ids"], ["ADR-001", "ADR-008"])
        self.assertEqual(pair["primary_artifact_id"], "ADR-001")
        self.assertEqual(len(pair["member_sources"]), 2)
        self.assertTrue(pair["preview_only"])
        self.assertFalse(pair["semantic_equivalence_proven"])
        self.assertFalse(pair["automatic_mutation_allowed"])
        self.assertNotIn("--apply", pair["preview_command"])
        self.assertEqual(sum(x["review_packet_primary"] for x in actions), 2)
        self.assertEqual({x["review_packet_id"] for x in actions},
                         {x["packet_id"] for x in packets})

    def test_same_closure_but_different_impact_is_not_merged(self):
        actions = [
            adr_action("ADR-001", ["ADR-001", "ADR-002"], consumer="EP-100"),
            adr_action("ADR-002", ["ADR-001", "ADR-002"], consumer="EP-200"),
        ]
        self.assertEqual(len(maintenance.group_adr_review_packets(actions)), 2)

    def test_same_closure_but_changed_source_is_not_merged(self):
        actions = [
            adr_action("ADR-001", ["ADR-001", "ADR-002"], digest="a" * 64),
            adr_action("ADR-002", ["ADR-001", "ADR-002"], digest="b" * 64),
        ]
        self.assertEqual(len(maintenance.group_adr_review_packets(actions)), 2)

    def test_stable_packet_identity_across_orderings(self):
        actions = [
            adr_action("ADR-008", ["ADR-001", "ADR-008"]),
            adr_action("ADR-001", ["ADR-001", "ADR-008"]),
            adr_action("ADR-007", ["ADR-007"]),
        ]
        first = maintenance.group_adr_review_packets(copy.deepcopy(actions))
        second = maintenance.group_adr_review_packets(copy.deepcopy(list(reversed(actions))))
        self.assertEqual(review.canonical(first), review.canonical(second))

    def test_invalid_empty_closure_fails_closed(self):
        with self.assertRaisesRegex(maintenance.MaintenanceError, "CLOSURE_INVALID"):
            maintenance.group_adr_review_packets([adr_action("ADR-001", [])])

    def test_no_amendments_no_packets(self):
        self.assertEqual(maintenance.group_adr_review_packets([]), [])
        self.assertEqual(maintenance.group_adr_review_packets([
            {"type": "review_adr_effect"}
        ]), [])


class MilestoneEvidenceIntegrationTests(unittest.TestCase):
    def setUp(self):
        from test_epctl import EpctlTestCase
        self.fixture = EpctlTestCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.init()
        self.root = self.fixture.repo
        self.plan = self.fixture.new_ep()
        self.fixture.prepare_checkpoint_plan(self.plan)
        self.data_root = self.root / ".memory-pilot"
        self.data_root.mkdir()
        self.release_source = self.data_root / "release.json"
        self.records_file = self.data_root / "milestones.json"
        self.next_action("Publish v0.8.3 and validate the external deployment.")

    def next_action(self, action):
        self.fixture.replace_section_body(self.plan, "Current Snapshot",
            "\n".join((
                "- Latest checkpoint: none.",
                "- Current milestone: Milestone 2.",
                "- Current state: Completing external release checks.",
                "- Next action: " + action,
                "- Open blockers: BLK-002.",
            )))

    def release(self, *, version=RELEASE_VERSION, published=RELEASED_AT,
                draft=False, prerelease=False):
        data = {
            "tag_name": "v" + version,
            "published_at": published,
            "draft": draft,
            "prerelease": prerelease,
            "html_url": "https://github.com/example/sample/releases/tag/v" + version,
        }
        self.release_source.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        return {
            "artifact_id": "EP-001", "event": "release_published",
            "version": version, "at": published,
            "source": {"path": ".memory-pilot/release.json",
                       "sha256": review.file_digest(self.release_source),
                       "revision": "release:v" + version},
        }

    def ci(self):
        sha = "a" * 40
        finished = "2026-10-20T00:00:00Z"
        self.release_source.write_text(json.dumps({
            "head_sha": sha, "completed_at": finished,
            "conclusion": "success", "name": "contract checks integration",
        }, sort_keys=True), encoding="utf-8")
        return {
            "artifact_id": "EP-001", "event": "ci_succeeded",
            "match_text": "contract checks", "at": finished,
            "source": {"path": ".memory-pilot/release.json",
                       "sha256": review.file_digest(self.release_source),
                       "revision": "git:" + sha},
        }

    def records(self, *rows):
        self.records_file.write_text(json.dumps({
            "schema_version": 1, "records": list(rows),
        }, sort_keys=True), encoding="utf-8")

    def snapshot(self):
        return {
            p.relative_to(self.root).as_posix(): p.read_bytes()
            for p in self.root.rglob("*") if p.is_file()
        }

    def preview(self):
        return maintenance.build_plan(
            self.root, as_of=AS_OF, milestones_path=".memory-pilot/milestones.json",
        )

    def test_offline_release_observation_requests_review_not_completion(self):
        self.records(self.release())
        before = self.snapshot()
        first = self.preview()
        second = self.preview()
        self.assertEqual(review.canonical(first), review.canonical(second))
        self.assertEqual(self.snapshot(), before)
        actions = [x for x in first["actions"]
                   if x["type"] == "review_milestone_evidence"]
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["artifact_id"], "EP-001")
        self.assertEqual(action["assessment"], "insufficient_evidence")
        self.assertEqual(action["reason_codes"], [
            "EP_NEXT_ACTION_EVIDENCE_REVIEW_CANDIDATE",
        ])
        self.assertFalse(action["completion_inferred"])
        self.assertFalse(action["progress_observation_created"])
        self.assertFalse(action["automatic_mutation_allowed"])
        self.assertEqual(action["authorization_before_mutation"], "plan_owner")
        self.assertEqual(action["milestone_evidence"]["external_authenticity"],
                         "not_verified_offline")
        self.assertEqual(first["summary"]["milestone_review_actions"], 1)
        self.assertEqual(first["summary"]["ep_actions"], 1)
        self.assertIsNotNone(first["milestone_source_snapshot_sha256"])

    def test_no_optional_milestones_preserves_prior_actions(self):
        self.records(self.release())
        regular = maintenance.build_plan(self.root, as_of=AS_OF)
        self.assertFalse(any(a["type"] == "review_milestone_evidence"
                             for a in regular["actions"]))
        self.assertIsNone(regular["milestone_source_snapshot_sha256"])

    def test_unrelated_release_does_not_claim_stale_next_action(self):
        self.next_action("Review the decision owner's approval of the design.")
        self.records(self.release())
        value = self.preview()
        self.assertFalse(any(x["type"] == "review_milestone_evidence"
                             for x in value["actions"]))
        self.assertEqual(value["summary"]["milestone_review_actions"], 0)

    def test_ci_success_requires_named_next_action_and_pinned_revision(self):
        self.next_action("Run contract checks on the module before publishing.")
        self.records(self.ci())
        value = self.preview()
        review_actions = [x for x in value["actions"]
                          if x["type"] == "review_milestone_evidence"]
        self.assertEqual(len(review_actions), 1)
        self.assertEqual(review_actions[0]["milestone_evidence"]["event"],
                         "ci_succeeded")
        self.assertFalse(review_actions[0]["completion_inferred"])

    def test_stale_or_unrelated_ci_not_matched(self):
        self.next_action("Review unrelated deployment materials.")
        self.records(self.ci())
        self.assertEqual(self.preview()["summary"]["milestone_review_actions"], 0)

    def test_draft_and_prerelease_do_not_count_as_published(self):
        for flags in ({"draft": True}, {"prerelease": True}):
            with self.subTest(flags=flags):
                self.records(self.release(**flags))
                with self.assertRaisesRegex(RuntimeError, "RELEASE_IDENTITY"):
                    self.preview()

    def test_broken_digest_fails_with_no_partial_output(self):
        record = self.release()
        record["source"]["sha256"] = "0" * 64
        self.records(record)
        result = subprocess.run([
            sys.executable, "-B", str(SCRIPTS / "memory_maintenance.py"),
            "--repo", str(self.root), "--as-of", AS_OF,
            "--milestones", ".memory-pilot/milestones.json", "--json",
        ], text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 2)
        failure = json.loads(result.stdout)
        self.assertEqual(failure["actions"], [])
        self.assertEqual(failure["input_integrity"], "incomplete")

    def test_future_timestamp_fails_closed(self):
        self.records(self.release(published="2099-01-01T00:00:00Z"))
        with self.assertRaisesRegex(RuntimeError, "MILESTONE_FUTURE_TIME"):
            self.preview()

    def test_duplicate_release_records_fails_closed(self):
        record = self.release()
        self.records(record, record)
        with self.assertRaisesRegex(RuntimeError, "MILESTONE_DUPLICATE_EVENT"):
            self.preview()

    def test_symlink_source_rejected(self):
        record = self.release()
        target = self.data_root / "actual.json"
        self.release_source.rename(target)
        self.release_source.symlink_to(target)
        self.records(record)
        with self.assertRaisesRegex(RuntimeError, "SYMLINK"):
            self.preview()

    def test_unauthorized_unknown_ep_rejected(self):
        event = self.release()
        event["artifact_id"] = "EP-999"
        self.records(event)
        with self.assertRaisesRegex(RuntimeError, "MILESTONE_ACTIVE_EP_REQUIRED"):
            self.preview()


if __name__ == "__main__":
    unittest.main()
