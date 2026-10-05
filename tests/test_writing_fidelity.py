"""Static distribution/eval checks; does not run a model or certify its prose."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = Path("references/controlled-writing.md")
SKILLS = ("detailed-design", "engineering-benchmark", "engineering-research",
          "engineering-design", "engineering-execution-plan", "engineering-case-study")
SECTIONS = ("Rewrite scope and fidelity review", "Chinese precision in practice",
            "Optional mechanical writing check", "Separate document and author handoff")
EXPECTED_ASSERTIONS = {
    10: {"branch-preservation", "no-shortening-loss", "polish-scope"},
    11: {"term-over-linter", "no-registry-mutation"},
    12: {"modal-fidelity", "protected-bytes", "no-action-authority"},
    13: {"execution-evidence", "no-invented-counts"},
    14: {"critical-conditions-inline", "no-invented-recovery", "handoff-separation"},
    15: {"no-causal-quality-claim", "prospective-protocol", "not-yet-run"},
}


class WritingFidelityTests(unittest.TestCase):
    def test_review_sections_reach_every_independent_skill(self):
        source = (ROOT / GUIDE).read_bytes()
        for skill in SKILLS:
            with self.subTest(skill=skill):
                text = (ROOT / skill / GUIDE).read_text(encoding="utf-8")
                self.assertEqual(text.encode(), source)
                for heading in SECTIONS:
                    self.assertEqual(text.count("## " + heading + "\n"), 1)
                    self.assertLess(text.index("## " + heading), text.index("## Documentation maintenance"))
                self.assertEqual(re.findall(r"\]\(([^)]+)\)", text), [])

    def test_attribution_and_noncommercial_boundary_travel_with_copies(self):
        for relative in [GUIDE, *(Path(skill) / GUIDE for skill in SKILLS)]:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for phrase in ("Copyright (c) 2026 hylarucoder", "CC BY-NC 4.0",
                           "https://creativecommons.org/licenses/by-nc/4.0/",
                           "a6c7ed23aee5fe9a3d9cb7e162cd8a6c0862ce8c",
                           "RF changes:", "does not relicense unrelated RF code"):
                self.assertIn(phrase, " ".join(text.split()))

    def test_fidelity_and_editorial_scope_are_distinct(self):
        text = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
        for phrase in ("not a percentage score", "Fidelity: branches", "Fidelity: actors",
                       "Fidelity: strength", "Fidelity: status", "Fidelity: protected bytes",
                       "Review-only work returns findings, not edits",
                       "not new Spec Requirement IDs or lifecycle gates",
                       "A linter match never overrides a term",
                       "without flattening the surrounding narrative"):
            self.assertIn(phrase, text)

    def test_checker_is_optional_nonblocking_and_has_no_model_verdict(self):
        text = " ".join((ROOT / GUIDE).read_text(encoding="utf-8").split())
        for phrase in ("Skills do not require this script", "Findings return exit status 0",
                       "Tool errors must not be reported as a clean scan",
                       "No `--fix`, recursive scan or blocking style mode",
                       "Same-session reconstructions are demonstrations",
                       "reading its source is not execution"):
            self.assertIn(phrase, text)

    def test_checker_imports_no_execution_or_network_client(self):
        tree = ast.parse((ROOT / "scripts/check_writing.py").read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
        self.assertLessEqual(imports, {"__future__", "argparse", "hashlib", "json", "pathlib",
                                       "re", "stat", "sys", "typing"})

    def test_self_contained_eval_catalog_extends_existing_cases(self):
        catalog = json.loads((ROOT / "detailed-design/evals/evals.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["skill_name"], "detailed-design")
        cases = catalog["evals"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(range(1, 16)).issubset(ids))
        by_id = {case["id"]: case for case in cases}
        for identifier, names in EXPECTED_ASSERTIONS.items():
            with self.subTest(identifier=identifier):
                case = by_id[identifier]
                self.assertEqual(case["files"], [])
                self.assertTrue(case["prompt"].strip())
                self.assertTrue(case["expected_output"].strip())
                self.assertEqual({a["name"] for a in case["assertions"]}, names)
                self.assertTrue(all(a["description"].strip() for a in case["assertions"]))
                self.assertNotIn("score", case)
                self.assertNotIn("result", case)


if __name__ == "__main__":
    unittest.main()
