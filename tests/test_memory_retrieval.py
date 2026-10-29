from __future__ import annotations

import copy
import importlib.util
import itertools
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


memory = load(ROOT / "assets/core/engineering-specs/memory_retrieval.py", "test_memory_retrieval_core")
AS_OF = "2026-10-29T00:00:00Z"


def candidate(identity="ADR-001", **values):
    fields = dict(kind="adr", artifact_id=identity,
                  source=f"docs/adr/{identity.lower()}.md", source_sha256="a" * 64,
                  content=f"Current navigation for {identity}.", current_effect=True)
    fields.update(values)
    return memory.MemoryCandidate(**fields)


def report(items=(), **values):
    result = {"schema_version": 1, "engine_version": "memory-review-v1",
              "input_integrity": "validated", "read_only": True, "as_of": AS_OF,
              "items": list(items)}
    result.update(values)
    result["report_sha256"] = memory.sha256(memory.canonical(result))
    return result


def hint_item(c, assessment="review_due"):
    return {"kind": c.kind, "artifact_id": c.artifact_id, "assessment": assessment,
            "source": {"path": c.source.split("#", 1)[0], "sha256": c.source_sha256}}


class SelectionTests(unittest.TestCase):
    def test_direct_current_authority_not_expired_by_review_due(self):
        c = candidate(relation="direct")
        hints = memory.review_hints(report([hint_item(c)]), [c], as_of=AS_OF)
        row = memory.select_memory([c], hints)[0]
        self.assertEqual(row["proposed_action"], "include")
        self.assertTrue(row["current_effect"])
        self.assertIn("REVIEW_DUE_IS_NOT_EXPIRY", row["reason_codes"])

    def test_required_overrides_background(self):
        c = candidate(relation="background", mandatory=True)
        row = memory.select_memory([c])[0]
        self.assertEqual(row["tier"], "required")
        self.assertEqual(row["proposed_action"], "include")

    def test_related_current_constraint_navigation_stays(self):
        row = memory.select_memory([candidate(relation="related")])[0]
        self.assertEqual(row["proposed_action"], "include")
        self.assertIn("DECLARED_TASK_RELATION", row["reason_codes"])

    def test_unknown_relevance_never_implies_irrelevant(self):
        c = candidate(relation="unknown")
        hints = memory.review_hints(report([hint_item(c, "historical")]), [c], as_of=AS_OF)
        row = memory.select_memory([c], hints)[0]
        self.assertEqual(row["proposed_action"], "include")
        self.assertFalse(row["historical"])

    def test_only_declared_background_navigation_is_cooled(self):
        c = candidate(relation="background")
        row = memory.select_memory([c])[0]
        self.assertEqual(row["proposed_action"], "reference")
        self.assertTrue(row["current_effect"])

    def test_explicit_history_is_retrievable_not_reactivated(self):
        c = candidate(relation="direct", current_effect=False, historical=True)
        row = memory.select_memory([c])[0]
        self.assertEqual(row["proposed_action"], "include")
        self.assertFalse(row["current_effect"])
        self.assertIn("HISTORICAL_NOT_CURRENT_AUTHORITY", row["reason_codes"])

    def test_insufficient_evidence_does_not_demote(self):
        c = candidate(relation="related")
        hints = memory.review_hints(report([hint_item(c, "insufficient_evidence")]), [c], as_of=AS_OF)
        row = memory.select_memory([c], hints)[0]
        self.assertEqual(row["proposed_action"], "include")
        self.assertIn("INSUFFICIENT_EVIDENCE_IS_NOT_IDLE", row["reason_codes"])

    def test_all_orderings_are_deterministic(self):
        values = [candidate("ADR-003", relation="direct"), candidate("ADR-001"),
                  candidate("ADR-002", relation="background")]
        expected = memory.select_memory(values)
        for order in itertools.permutations(values):
            self.assertEqual(memory.select_memory(order), expected)

    def test_unique_identity_and_source(self):
        for values in ([candidate(), candidate()],
                       [candidate(), candidate("ADR-002", source=candidate().source)]):
            with self.assertRaisesRegex(memory.RetrievalError, "DUPLICATE"):
                memory.select_memory(values)

    def test_source_boundaries_and_types(self):
        for values in ({"source": "../escape.md"}, {"source": "/etc/passwd"},
                       {"source": "docs//double.md"}, {"source": "docs/./dot.md"},
                       {"source": "docs/x\n.md"}, {"source_sha256": "wrong"},
                       {"mandatory": 1}, {"priority": True}, {"relation": []},
                       {"kind": []}, {"current_effect": 1}, {"historical": True},
                       {"content": ""}):
            with self.subTest(values=values), self.assertRaises(memory.RetrievalError):
                memory.select_memory([candidate(**values)])

    def test_candidate_and_byte_limits_fail_without_truncation(self):
        with self.assertRaisesRegex(memory.RetrievalError, "CANDIDATE_LIMIT"):
            memory.select_memory([candidate(f"ADR-{n:03d}") for n in range(129)])
        with self.assertRaisesRegex(memory.RetrievalError, "CONTEXT_INPUT_TOO_LARGE"):
            memory.select_memory([candidate(content="中" * (memory.MAX_CONTENT_BYTES // 3 + 1))])

    def test_authority_invariants_for_all_policy_combinations(self):
        for mandatory, relation, effect, assessment in itertools.product(
            [False, True], ["direct", "related", "background", "unknown"],
            [None, False, True], sorted(memory.ASSESSMENTS)
        ):
            c = candidate(mandatory=mandatory, relation=relation, current_effect=effect)
            hints = memory.review_hints(report([hint_item(c, assessment)]), [c], as_of=AS_OF)
            row = memory.select_memory([c], hints)[0]
            self.assertEqual(row["current_effect"], effect)
            if mandatory or relation != "background":
                self.assertEqual(row["proposed_action"], "include")


class HintTests(unittest.TestCase):
    def check(self, value, c=None, **kwargs):
        return memory.review_hints(value, [c or candidate()], as_of=AS_OF, **kwargs)

    def test_absent_report_is_optional(self):
        self.assertEqual(self.check(None)["reason"], "REPORT_ABSENT")

    def test_invalid_report_falls_back(self):
        for value in ([], "bad", {}, report(schema_version=True),
                      report(schema_version=2), report(input_integrity="incomplete"),
                      report(engine_version="future"), report(read_only=False)):
            self.assertEqual(self.check(value)["status"], "unavailable")

    def test_digest_mismatch(self):
        value = report()
        value["as_of"] = "2001-01-01T00:00:00Z"
        self.assertEqual(self.check(value)["reason"], "REPORT_DIGEST_MISMATCH")

    def test_future_and_exact_age_boundary(self):
        self.assertEqual(self.check(report(as_of="2026-10-30T00:00:00Z"))["reason"], "REPORT_FROM_FUTURE")
        boundary = report(as_of="2026-10-28T00:00:00Z")
        self.assertEqual(self.check(boundary)["status"], "available")
        older = report(as_of="2026-10-27T23:59:59Z")
        self.assertEqual(self.check(older)["reason"], "REPORT_TOO_OLD")

    def test_timezone_normalization(self):
        value = report(as_of="2026-10-29T09:00:00+09:00")
        self.assertEqual(self.check(value)["status"], "available")

    def test_changed_source_ignores_annotation(self):
        c = candidate()
        item = hint_item(c)
        item["source"]["sha256"] = "b" * 64
        result = self.check(report([item]))
        self.assertEqual(result["items"][c.key]["reason"], "SOURCE_CHANGED")

    def test_different_path_same_bytes_is_not_a_match(self):
        c = candidate()
        item = hint_item(c)
        item["source"]["path"] = "docs/other.md"
        self.assertEqual(self.check(report([item]))["items"][c.key]["status"], "ignored")

    def test_packed_logical_source_matches_container(self):
        c = candidate(source="docs/.epctl/adr-packs/pack.json#ADR-001",
                      current_effect=False, historical=True)
        result = self.check(report([hint_item(c, "historical")]), c)
        self.assertEqual(result["items"][c.key]["status"], "source_matched")
        self.assertFalse(result["items"][c.key]["authority_verified"])

    def test_duplicate_report_identity_rejects_all_hints(self):
        item = hint_item(candidate())
        self.assertEqual(self.check(report([item, item]))["reason"], "REPORT_ITEM_DUPLICATE")

    def test_report_does_not_inject_new_candidates(self):
        result = self.check(report([hint_item(candidate("ADR-999"))]))
        self.assertEqual(result["items"], {})

    def test_invalid_age_and_as_of_are_explicit_input_errors(self):
        for value in (-1, True, "7", 366 * 86400):
            with self.assertRaises(memory.RetrievalError):
                self.check(None, max_age_seconds=value)
        with self.assertRaises(memory.RetrievalError):
            memory.review_hints(None, [], as_of="2026-10-29")


class ExistingPlannerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = load(ROOT / "assets/core/engineering-specs/spec_router.py", "retrieval_existing_router")

    def test_shadow_keeps_actual_effective_context_and_mandatory_content(self):
        values = [candidate("ADR-001", relation="background", mandatory=True, content="Required 原文 " * 20),
                  candidate("ADR-002", relation="background", content="Optional background " * 150)]
        original = copy.deepcopy(values)
        result = memory.shadow_context(self.router, values)
        self.assertEqual(result["effective_context"], result["baseline"]["text"])
        self.assertFalse(result["effective_changed"])
        self.assertIn(values[0].content, result["proposal"]["text"])
        self.assertNotIn(values[1].content, result["proposal"]["text"])
        self.assertIn(values[1].source, result["proposal"]["text"])
        self.assertEqual(values, original)
        self.assertLess(result["byte_delta"], 0)

    def test_empty_selection_is_zero_cost(self):
        result = memory.shadow_context(self.router, [])
        self.assertEqual(result["effective_context"], "")
        self.assertEqual(result["byte_delta"], 0)

    def test_budget_is_existing_utf8_contract(self):
        c = candidate(content="中文内容" * 500)
        result = memory.shadow_context(self.router, [c], budget_bytes=150)
        self.assertLessEqual(result["baseline"]["used_bytes"], 150)
        self.assertEqual(result["baseline"]["used_bytes"], len(result["effective_context"].encode("utf-8")))
        with self.assertRaises(self.router.RouterError):
            memory.shadow_context(self.router, [replace(c, mandatory=True)], budget_bytes=150)


if __name__ == "__main__":
    unittest.main()
