from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


CORE = (
    Path(__file__).resolve().parents[1]
    / "assets/core/engineering-specs/spec_router.py"
)
module_spec = importlib.util.spec_from_file_location("session_context_test_core", CORE)
assert module_spec is not None and module_spec.loader is not None
core = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = core
module_spec.loader.exec_module(core)


class SessionContextBudgetTestCase(unittest.TestCase):
    def section(
        self,
        name: str,
        content: str,
        *,
        priority: int = 10,
        mandatory: bool = False,
        source: str | None = None,
    ):
        return core.SessionContextSection(
            id=name,
            priority=priority,
            content=content,
            source=source or f"docs/{name}.md",
            mandatory=mandatory,
        )

    def test_budget_keeps_mandatory_content_and_references_large_optional(self) -> None:
        sections = (
            self.section("rules", "Mandatory rules", priority=0, mandatory=True),
            self.section("index", "large content" * 2000),
        )
        result = core.plan_session_context(sections, budget_bytes=120)
        self.assertIn("Mandatory rules", result["text"])
        self.assertIn("[ContextRef:index] docs/index.md", result["text"])
        self.assertNotIn("large content", result["text"])
        self.assertEqual(
            [item["selection"] for item in result["selections"]],
            ["content", "reference"],
        )
        self.assertEqual(result["used_bytes"], len(result["text"].encode("utf-8")))
        self.assertLessEqual(result["used_bytes"], 120)

    def test_priority_and_id_ties_produce_deterministic_order(self) -> None:
        values = (
            self.section("zeta", "Z"),
            self.section("alpha", "A"),
            self.section("first", "First", priority=0, mandatory=True),
        )
        first = core.plan_session_context(values, budget_bytes=100)
        reversed_plan = core.plan_session_context(reversed(values), budget_bytes=100)
        self.assertEqual(first, reversed_plan)
        self.assertEqual([item["id"] for item in first["selections"]],
                         ["first", "alpha", "zeta"])

    def test_source_pointers_are_reserved_for_later_optional_sections(self) -> None:
        sections = (
            self.section("first", "X" * 1000, priority=0),
            self.section("second", "Y" * 1000, priority=1),
            self.section("third", "Z" * 1000, priority=2),
        )
        baseline = "\n\n".join(
            f"[ContextRef:{item.id}] {item.source}" for item in sections
        )
        result = core.plan_session_context(
            sections, budget_bytes=len(baseline.encode("utf-8"))
        )
        self.assertEqual(result["text"], baseline)
        self.assertEqual(
            [item["selection"] for item in result["selections"]],
            ["reference", "reference", "reference"],
        )

    def test_exact_byte_boundary_and_unicode(self) -> None:
        section = self.section("unicode", "中文日本語", source="docs/unicode.md")
        full = len(section.content.encode("utf-8"))
        self.assertGreater(full, len(section.content))
        selected = core.plan_session_context([section], budget_bytes=full)
        self.assertEqual(selected["text"], section.content)
        self.assertEqual(selected["used_bytes"], full)
        with self.assertRaisesRegex(core.RouterError, "BUDGET_EXCEEDED"):
            core.plan_session_context(
                [self.section("required", "中文日本語", mandatory=True)],
                budget_bytes=full - 1,
            )

    def test_mandatory_and_pointers_over_budget_fail_explicitly(self) -> None:
        with self.assertRaisesRegex(core.RouterError, "BUDGET_EXCEEDED"):
            core.plan_session_context(
                (
                    self.section("must", "M" * 64, mandatory=True),
                    self.section("optional", "O" * 500),
                ),
                budget_bytes=80,
            )

    def test_duplicate_id_and_duplicate_source_fail_closed(self) -> None:
        with self.assertRaisesRegex(core.RouterError, "SECTION_INVALID"):
            core.plan_session_context([
                self.section("same", "A"),
                self.section("same", "B"),
            ])
        with self.assertRaisesRegex(core.RouterError, "SOURCE_DUPLICATE"):
            core.plan_session_context([
                self.section("first", "A", source="docs/one.md"),
                self.section("second", "B", source="docs/one.md"),
            ])

    def test_invalid_inputs_fail_closed(self) -> None:
        for budget in (0, True, -1, core.MAX_SESSION_CONTEXT_BUDGET_BYTES + 1):
            with self.subTest(budget=budget):
                with self.assertRaisesRegex(core.RouterError, "BUDGET_INVALID"):
                    core.plan_session_context([], budget_bytes=budget)
        for value in (
            self.section("Bad Name", "A"),
            self.section("ok", ""),
            self.section("ok", "A", source="docs/x.md\ninjection"),
            core.SessionContextSection("ok", True, "A", "docs/x.md"),
            core.SessionContextSection("ok", 1, "A", "docs/x.md", mandatory=1),
            object(),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(core.RouterError, "SECTION_INVALID"):
                    core.plan_session_context([value])


    def test_ep_snapshot_is_reference_when_context_overflows(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "docs/exec-plans/active/ep-001_large"
            directory.mkdir(parents=True)
            (directory / "EXECPLAN.md").write_text(
                "---\nid: EP-001\nstatus: active\nadr_refs: []\n---\n"
                "## Current Snapshot\n\n" + "LONG_SNAPSHOT\n" * 2000
                + "\n## Progress\n\nNot in snapshot\n",
                encoding="utf-8",
            )
            values = core._session_artifact_sections(
                root,
                {"context_ep_ref": "EP-001", "context_adr_refs": []},
            )
            self.assertEqual([v.id for v in values], ["ep-snapshot"])
            result = core.plan_session_context(values, budget_bytes=100)
            self.assertIn("[ContextRef:ep-snapshot]", result["text"])
            self.assertNotIn("LONG_SNAPSHOT", result["text"])

    def test_absent_symlink_and_ambiguous_ep_are_safe(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "docs/exec-plans/active"
            base.mkdir(parents=True)
            one = base / "ep-003_valid"
            one.mkdir()
            external = root / "outside.md"
            external.write_text("secret data", encoding="utf-8")
            (one / "EXECPLAN.md").symlink_to(external)
            snapshot, refs = core._session_ep_snapshot(root, "EP-003")
            self.assertEqual(refs, [])
            self.assertIn("unavailable", snapshot.content)
            self.assertNotIn("secret data", snapshot.content)
            self.assertEqual(
                core._session_requested_refs("Compare EP-003 to EP-004")[0],
                [],
            )
            self.assertEqual(
                core._session_requested_refs("Implement ADR-012 with EP-003"),
                (["EP-003"], ["ADR-012"]),
            )

    def test_unavailable_decision_index_never_claims_currentness(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            section = core._session_adr_navigation(root, ["ADR-012"])
            self.assertIsNotNone(section)
            self.assertIn("unavailable", section.content)
            self.assertNotIn("accepted", section.content)


    def test_blocked_ep_current_snapshot_is_allowed(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "docs/exec-plans/active/ep-007_waiting"
            folder.mkdir(parents=True)
            (folder / "EXECPLAN.md").write_text(
                "---\nid: EP-007\nstatus: blocked\nadr_refs: []\n---\n"
                "## Current Snapshot\n\n"
                "- Current milestone: Waiting for a required approval.\n"
                "- Next action: Resume after authorization.\n\n"
                "## Blockers\n\nOpen blocker retained.\n",
                encoding="utf-8",
            )
            section, refs = core._session_ep_snapshot(root, "EP-007")
            self.assertEqual(refs, [])
            self.assertIn("Waiting for a required approval", section.content)
            self.assertNotIn("Open blocker retained", section.content)

    def test_many_adr_references_remain_discoverable_via_index(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs/DECISIONS.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "<!-- ADRCTL:CURRENT:START -->\n"
                "<!-- ADRCTL:CURRENT:END -->\n",
                encoding="utf-8",
            )
            ids = [f"ADR-{number:03d}" for number in range(1, 16)]
            section = core._session_adr_navigation(root, ids)
            self.assertIsNotNone(section)
            self.assertIn("3 additional ADR references", section.content)
            self.assertIn("docs/DECISIONS.md", section.content)

    def test_explicit_adr_is_not_evicted_by_many_ep_dependencies(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_refs = [f"ADR-{number:03d}" for number in range(1, 13)]
            refs_json = "[" + ",".join(f'"{ref}"' for ref in plan_refs) + "]"
            plan = root / "docs/exec-plans/active/ep-001_scope/EXECPLAN.md"
            plan.parent.mkdir(parents=True)
            plan.write_text(
                f"---\nid: EP-001\nstatus: active\nadr_refs: {refs_json}\n---\n"
                "## Current Snapshot\n\n- Next action: Continue scoped work.\n",
                encoding="utf-8",
            )
            decision_index = root / "docs/DECISIONS.md"
            decision_index.parent.mkdir(parents=True, exist_ok=True)
            rows = []
            for identity in [*plan_refs, "ADR-099"]:
                name = identity.lower() + ".md"
                artifact = root / "docs/adr" / name
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text(f"# {identity}\n", encoding="utf-8")
                rows.append(
                    f"| {identity} | Decision | accepted | current | "
                    f"[ADR](adr/{name}) |"
                )
            decision_index.write_text(
                "<!-- ADRCTL:CURRENT:START -->\n"
                + "\n".join(rows)
                + "\n<!-- ADRCTL:CURRENT:END -->\n",
                encoding="utf-8",
            )
            sections = core._session_artifact_sections(
                root, {"context_ep_ref": "EP-001", "context_adr_refs": ["ADR-099"]}
            )
            nav = next(section for section in sections if section.id == "adr-navigation")
            self.assertIn("ADR-099: docs/adr/adr-099.md", nav.content)
            self.assertNotIn("- ADR-012:", nav.content)
            self.assertIn("1 additional ADR references", nav.content)

    def test_adr_navigation_supports_custom_roots_and_rejects_escape(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs/DECISIONS.md"
            source.parent.mkdir(parents=True)
            custom = root / "docs/architecture/decision-current.md"
            custom.parent.mkdir(parents=True)
            custom.write_text(
                "---\nid: ADR-023\nstatus: accepted\n---\n"
                "# Architecture decision\n",
                encoding="utf-8",
            )
            source.write_text(
                "<!-- ADRCTL:CURRENT:START -->\n"
                "| ADR-023 | Decision | accepted | current | — | — | — | "
                "[ADR](architecture/decision-current.md) |\n"
                "<!-- ADRCTL:CURRENT:END -->\n",
                encoding="utf-8",
            )
            current = core._session_adr_navigation(root, ["ADR-023"])
            self.assertIsNotNone(current)
            self.assertIn(
                "ADR-023: docs/architecture/decision-current.md",
                current.content,
            )
            source.write_text(
                "<!-- ADRCTL:CURRENT:START -->\n"
                "| ADR-023 | Decision | accepted | current | — | — | — | "
                "[ADR](../outside.md) |\n"
                "<!-- ADRCTL:CURRENT:END -->\n",
                encoding="utf-8",
            )
            unsafe = core._session_adr_navigation(root, ["ADR-023"])
            self.assertIsNotNone(unsafe)
            self.assertIn("unavailable", unsafe.content)
            self.assertNotIn("docs/../", unsafe.content)

    def test_empty_plan_is_deterministic(self) -> None:
        self.assertEqual(
            core.plan_session_context([], budget_bytes=40),
            {"text": "", "budget_bytes": 40, "used_bytes": 0, "selections": []},
        )

    def test_optional_shorter_than_pointer_can_free_more_budget(self) -> None:
        sections = (
            self.section("short", "S", priority=0),
            self.section("next", "Next", priority=1),
        )
        full = "S\n\nNext"
        chosen = core.plan_session_context(
            sections, budget_bytes=len(full.encode("utf-8"))
        )
        self.assertEqual(chosen["text"], full)
        self.assertEqual(
            [item["selection"] for item in chosen["selections"]],
            ["content", "content"],
        )


if __name__ == "__main__":
    unittest.main()
