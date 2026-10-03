"""Static authoring-contract tests, not readability or LLM-behavior evaluation.

These checks keep routing, packaged policy boundaries, and review scenarios
available. Actual prose, command behavior, and accessibility need separate review.
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = Path("references/controlled-writing.md")
SKILLS = (
    "detailed-design", "engineering-benchmark", "engineering-research",
    "engineering-design", "engineering-execution-plan", "engineering-case-study",
)


def normalized(value: str) -> str:
    return " ".join(value.split())


def sections(value: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## (.+)$", value, re.MULTILINE))
    return {match.group(1): normalized(value[match.end():matches[i + 1].start()
            if i + 1 < len(matches) else len(value)]) for i, match in enumerate(matches)}


class DocumentationGuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guide = (ROOT / GUIDE).read_text(encoding="utf-8")
        self.parts = sections(self.guide)

    def test_every_independent_package_contains_the_complete_local_guide(self) -> None:
        expected = (ROOT / GUIDE).read_bytes()
        for skill in SKILLS:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as tmp:
                copied = Path(tmp) / "skill" / GUIDE
                copied.parent.mkdir(parents=True)
                shutil.copyfile(ROOT / skill / GUIDE, copied)
                self.assertEqual(copied.read_bytes(), expected)
                for heading in ("Reader and document structure", "Procedures and examples",
                                "Headings, code, and links", "Accessible explanation surfaces"):
                    self.assertTrue(sections(copied.read_text(encoding="utf-8"))[heading])
        # External URLs are source attribution, not includes or required loads.
        self.assertEqual(re.findall(r"\]\(([^)]+)\)", self.guide), [])
        self.assertIn("self-contained: do not fetch external guides", normalized(self.guide))
        self.assertIn("optional references, not task-time dependencies", self.parts["Sources and local adaptations"])

    def test_project_contracts_and_semantic_fidelity_override_editorial_defaults(self) -> None:
        text = normalized(self.guide)
        for boundary in (
            "not a Catalog Specification", "claim full ASD-STE100 conformance",
            "Project-specific writing conventions take precedence",
            "This guide adds no approval step or lifecycle gate",
            "Preserve the defined meanings of `MUST`, `SHOULD`, and `MAY`",
            "not to turn a proposed feature into current behavior",
            "Do not rewrite accepted ADRs", "sealed Checkpoints",
            "without imposing English vocabulary, grammar, capitalization, or word-count rules",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text)

    def test_reader_procedure_and_accessibility_review_guards_remain_explicit(self) -> None:
        contracts = {
            "Reader and document structure": (
                "does not require a separate brief", "directory inventory",
                "Historical design records remain history",
            ),
            "Procedures and examples": (
                "working directory", "placeholders", "Documenting a command does not authorize executing it",
                "Never label an unexecuted example as tested",
            ),
            "Accessible explanation surfaces": (
                "Mermaid source alone is not a text alternative", "keyboard-accessible actions",
                "captions or a transcript", "not certify existing renderers",
            ),
            "Review before handoff": (
                "Review technical correctness first",
            ),
        }
        for title, phrases in contracts.items():
            for phrase in phrases:
                with self.subTest(title=title, phrase=phrase):
                    self.assertIn(phrase, self.parts[title])
        self.assertIn("existing validators", self.parts["Review before handoff"])
        self.assertIn("not label a heuristic pass as semantic verification", self.parts["Review before handoff"])

    def test_detailed_design_reads_common_rules_and_reviews_every_delivery(self) -> None:
        text = (ROOT / "detailed-design/SKILL.md").read_text(encoding="utf-8")
        link = "[受控技术写作](references/controlled-writing.md)"
        self.assertEqual(text.count(link), 1)
        self.assertLess(text.index(link), text.index("\n## "))
        self.assertIn("写作和修订交付前，以及 review 模式下，都读取", text)
        self.assertIn("[review.md](references/review.md)", text)
        self.assertIn("不另行复制通用文风规则", text)
        self.assertIn("本 skill 不直接修改受 `engineering-design` 管理的 Design Package", text)
        self.assertIn("只评审时不改文件", text)

    def test_updated_review_references_work_in_an_isolated_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            refs = Path(tmp) / "references"
            refs.mkdir()
            for name in ("controlled-writing.md", "architecture.md", "review.md"):
                shutil.copyfile(ROOT / "detailed-design/references" / name, refs / name)
            for name in ("architecture.md", "review.md"):
                text = (refs / name).read_text(encoding="utf-8")
                targets = re.findall(r"\]\(([^)]+)\)", text)
                self.assertIn("controlled-writing.md", targets)
                for target in targets:
                    path = (refs / target).resolve()
                    self.assertTrue(path.is_relative_to(Path(tmp).resolve()))
                    self.assertTrue(path.is_file())
            review = normalized((refs / "review.md").read_text(encoding="utf-8"))
            self.assertIn("Review engineering risk before prose quality", review)
            self.assertIn("For review-only requests, return findings without rewriting files", review)
            self.assertIn("Do not claim checks that were unavailable", review)

    def test_eval_catalog_covers_new_failure_modes_without_claiming_execution(self) -> None:
        catalog = json.loads((ROOT / "detailed-design/evals/evals.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["skill_name"], "detailed-design")
        cases = {case["id"]: case for case in catalog["evals"]}
        self.assertEqual(len(cases), len(catalog["evals"]))
        self.assertTrue(set(range(1, 11)).issubset(cases))
        required = {
            6: {"reader-task-and-flow", "chinese-and-uncertainty", "no-extra-artifacts"},
            7: {"modal-and-quote-fidelity", "project-heading-and-status", "no-conformance-claim"},
            8: {"procedure-order", "authority-and-stop", "no-false-execution"},
            9: {"accessible-reading-path", "risk-before-style", "review-not-render"},
            10: {"offline-local-guidance", "no-historical-rewrite", "no-invented-baseline"},
        }
        for case_id, names in required.items():
            with self.subTest(case=case_id):
                case = cases[case_id]
                self.assertTrue(case["prompt"].strip())
                self.assertTrue(case["expected_output"].strip())
                self.assertEqual(case["files"], [])  # The new prompts contain their own facts.
                actual = [assertion["name"] for assertion in case["assertions"]]
                self.assertEqual(len(actual), len(set(actual)))
                self.assertTrue(names.issubset(actual))
                self.assertTrue(all(a["description"].strip() for a in case["assertions"]))


if __name__ == "__main__":
    unittest.main()
