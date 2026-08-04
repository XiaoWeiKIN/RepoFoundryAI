from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "epctl.py"
FAST_TRACK_ARGS = (
    "--research-not-required-reason",
    "Test fixture uses fixed, already-known inputs.",
    "--architecture-not-required-reason",
    "Test fixture has no durable architecture choice.",
)
CHECKPOINT_REVISION_ARGS = ("--revision", "test:workspace-revision")
COMPLETION_ATTESTATION_ARGS = (
    "--verified-revision",
    "test:verified-revision",
    "--evidence",
    "test:ep-integrity",
)


class EpctlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(
        self,
        *arguments: str,
        expected: int = 0,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *arguments],
            text=True,
            capture_output=True,
            env=env,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def init(self) -> None:
        self.run_cli("init")

    def new_ep(self, slug: str = "sample-plan") -> Path:
        result = self.run_cli(
            "new-ep",
            "--slug",
            slug,
            "--title",
            slug.replace("-", " ").title(),
            *FAST_TRACK_ARGS,
        )
        return Path(result.stdout.strip())

    def new_research(self, slug: str = "sample-research") -> Path:
        result = self.run_cli(
            "new-research",
            "--slug",
            slug,
            "--title",
            slug.replace("-", " ").title(),
        )
        return Path(result.stdout.strip())

    def prepare_research_for_conclusion(self, research: Path) -> None:
        synthesis = research.parent / "SYNTHESIS.md"
        self.complete_all_placeholders(research)
        self.complete_all_placeholders(synthesis)
        self.replace_section_body(
            research,
            "Research Questions",
            "\n".join(
                (
                    "| ID | Status | Question | Answer or disposition | Evidence |",
                    "|---|---|---|---|---|",
                    "| RQ-001 | answered | Which option meets the contract? | "
                    "Option A preserves the contract. | `notes/options.md` |",
                )
            ),
        )

    def conclude_research(self, research: Path) -> Path:
        self.prepare_research_for_conclusion(research)
        result = self.run_cli(
            "archive-research",
            self.artifact_id(research),
            "--outcome",
            "concluded",
        )
        return Path(result.stdout.strip())

    def new_adr(
        self,
        slug: str = "sample-decision",
        research_id: str = "R-001",
    ) -> Path:
        result = self.run_cli(
            "new-adr",
            "--slug",
            slug,
            "--title",
            slug.replace("-", " ").title(),
            "--research",
            research_id,
        )
        return Path(result.stdout.strip())

    def accept_adr(self, adr: Path, adr_id: str = "ADR-001") -> Path:
        self.complete_all_placeholders(adr)
        result = self.run_cli(
            "decide-adr",
            adr_id,
            "--outcome",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
        )
        return Path(result.stdout.strip())

    def new_bugfix(self, slug: str = "sample-bug") -> Path:
        result = self.run_cli(
            "new-bugfix",
            "--slug",
            slug,
            "--title",
            slug.replace("-", " ").title(),
        )
        return Path(result.stdout.strip())

    @staticmethod
    def replace_frontmatter(path: Path, key: str, value: str) -> None:
        text = path.read_text(encoding="utf-8")
        updated, count = re.subn(
            rf"(?m)^{re.escape(key)}:.*$",
            f"{key}: {value}",
            text,
            count=1,
        )
        if count != 1:
            raise AssertionError(f"frontmatter field not found: {key}")
        path.write_text(updated, encoding="utf-8")

    @staticmethod
    def artifact_id(path: Path) -> str:
        match = re.search(
            r"(?m)^id:\s+((?:EP|R|ADR|BF)-\d+)\s*$",
            path.read_text(encoding="utf-8"),
        )
        if not match:
            raise AssertionError(f"artifact id not found: {path}")
        return match.group(1)

    @staticmethod
    def complete_all_placeholders(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        replacements = {
            "REPLACE_WITH_SCOPE": "test architecture boundary",
            "REPLACE_WITH_CONSTRAINT": "The implementation must preserve the test boundary.",
            "REPLACE_WITH_CONFIRMATION": "Run the architecture contract test.",
        }
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        text = re.sub(
            r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
            "Recorded evidence.",
            text,
        )
        text = re.sub(r"(?m)^-\s+\[ \]", "- [x]", text)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def replace_section_body(path: Path, heading: str, body: str) -> None:
        text = path.read_text(encoding="utf-8")
        pattern = (
            rf"(?ms)^## {re.escape(heading)}\s*$"
            rf".*?(?=^## |\Z)"
        )
        replacement = f"## {heading}\n\n{body.strip()}\n\n"
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count != 1:
            raise AssertionError(f"section not found: {heading}")
        path.write_text(updated, encoding="utf-8")

    def prepare_checkpoint_plan(self, plan: Path) -> None:
        self.complete_all_placeholders(plan)
        self.replace_section_body(
            plan,
            "Current Snapshot",
            "\n".join(
                (
                    "- Latest checkpoint: none.",
                    "- Current milestone: Milestone 2.",
                    "- Current state: Milestone 1 is complete.",
                    "- Next action: edit `service/handler.py`.",
                    "- Open blockers: `BLK-002`.",
                )
            ),
        )
        self.replace_section_body(
            plan,
            "Progress",
            "\n".join(
                (
                    "- [x] (2026-07-28T01:00:00Z) Milestone 1 completed.",
                    "  Evidence: `artifacts/m1.txt`.",
                    "- [ ] (2026-07-28T02:00:00Z) Implement Milestone 2.",
                )
            ),
        )
        self.replace_section_body(
            plan,
            "Surprises & Discoveries",
            "- 2026-07-28 — The adapter already normalizes IDs.",
        )
        self.replace_section_body(
            plan,
            "Decision Log",
            "- 2026-07-28 — Keep compatibility at the boundary.",
        )
        self.replace_section_body(
            plan,
            "Blockers",
            "\n".join(
                (
                    "| ID | Status | Opened | Resolved | Missing capability | "
                    "Impact | Unblock or resolution |",
                    "|---|---|---|---|---|---|---|",
                    "| BLK-001 | resolved | 2026-07-27 | 2026-07-28 | "
                    "Schema | Milestone 1 | Contract confirmed |",
                    "| BLK-002 | open | 2026-07-28 |  | Credential | "
                    "Milestone 2 | External team grants access |",
                )
            ),
        )
        self.replace_section_body(
            plan,
            "Revision Notes",
            "- 2026-07-28T01:00:00Z — Milestone 1 route revised.",
        )
        self.replace_frontmatter(plan, "status", "blocked")

    def test_init_is_idempotent_and_does_not_overwrite(self) -> None:
        first = json.loads(self.run_cli("init").stdout)
        self.assertIn("docs/PLANS.md", first["created"])
        plans = self.repo / "docs" / "PLANS.md"
        plans.write_text(
            plans.read_text(encoding="utf-8") + "\nHuman note.\n",
            encoding="utf-8",
        )

        second = json.loads(self.run_cli("init").stdout)

        self.assertEqual(second["created"], [])
        self.assertIn("Human note.", plans.read_text(encoding="utf-8"))
        self.assertTrue((self.repo / "docs" / ".epctl" / "state.json").is_file())
        self.assertTrue((self.repo / "docs" / "RESEARCH.md").is_file())
        self.assertTrue((self.repo / "docs" / "DECISIONS.md").is_file())
        self.assertTrue((self.repo / "docs" / "research" / "active").is_dir())
        self.assertTrue((self.repo / "docs" / "research" / "completed").is_dir())
        self.assertTrue((self.repo / "docs" / "adr").is_dir())

    def test_research_conclusion_seals_synthesis_and_detects_tampering(
        self,
    ) -> None:
        self.init()
        research = self.new_research("storage-options")
        synthesis = research.parent / "SYNTHESIS.md"
        status = json.loads(self.run_cli("status", "--json").stdout)
        self.assertEqual(status["research"][0]["open_questions"], 1)
        self.assertEqual(status["research"][0]["synthesis_status"], "draft")
        blocked = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "concluded",
            expected=2,
        )
        self.assertIn("open questions", blocked.stderr)

        concluded = self.conclude_research(research)
        sealed = concluded.parent / "SYNTHESIS.md"

        self.assertTrue(concluded.exists())
        self.assertFalse(research.exists())
        self.assertIn("status: concluded", concluded.read_text(encoding="utf-8"))
        sealed_text = sealed.read_text(encoding="utf-8")
        self.assertIn("status: sealed", sealed_text)
        self.assertRegex(sealed_text, r"payload_sha256: [0-9a-f]{64}")
        clean = self.run_cli("validate")
        self.assertIn('"errors": 0', clean.stdout)
        self.assertIn(
            "| R-001 |",
            (self.repo / "docs" / "RESEARCH.md").read_text(encoding="utf-8"),
        )

        sealed.write_text(sealed_text + "\nTampered conclusion.\n", encoding="utf-8")
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("sealed Synthesis payload changed", tampered.stderr)

    def test_cancelled_research_requires_reason_and_cannot_satisfy_gate(
        self,
    ) -> None:
        self.init()
        research = self.new_research("abandoned-spike")
        missing_reason = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "cancelled",
            expected=2,
        )
        self.assertIn("requires --reason", missing_reason.stderr)

        cancelled = Path(
            self.run_cli(
                "archive-research",
                "R-001",
                "--outcome",
                "cancelled",
                "--reason",
                "The upstream contract was withdrawn.",
            ).stdout.strip()
        )

        self.assertTrue(cancelled.exists())
        self.assertFalse(research.exists())
        self.assertIn("status: cancelled", cancelled.read_text(encoding="utf-8"))
        rejected = self.run_cli(
            "new-ep",
            "--slug",
            "invalid-gate",
            "--title",
            "Invalid gate",
            "--research",
            "R-001",
            "--architecture-not-required-reason",
            "No architecture choice exists.",
            expected=2,
        )
        self.assertIn("must be valid and concluded", rejected.stderr)

    def test_adr_requires_concluded_research_and_explicit_decision(
        self,
    ) -> None:
        self.init()
        research = self.new_research("queue-options")
        premature = self.run_cli(
            "new-adr",
            "--slug",
            "queue-choice",
            "--title",
            "Queue choice",
            "--research",
            "R-001",
            expected=2,
        )
        self.assertIn("Research package", premature.stderr)
        self.conclude_research(research)
        adr = self.new_adr("queue-choice")

        missing_authority = self.run_cli(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            expected=2,
        )
        self.assertIn("--decision-maker", missing_authority.stderr)
        unresolved = self.run_cli(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            "--decision-maker",
            "Architecture Council",
            expected=2,
        )
        self.assertIn("required placeholders", unresolved.stderr)

        accepted = self.accept_adr(adr)
        accepted_text = accepted.read_text(encoding="utf-8")
        self.assertIn("status: accepted", accepted_text)
        self.assertIn('decision_maker: "Test Decision Owner"', accepted_text)
        self.assertRegex(accepted_text, r"payload_sha256: [0-9a-f]{64}")
        self.run_cli("validate")

        accepted.write_text(
            accepted_text + "\nChanged after acceptance.\n",
            encoding="utf-8",
        )
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("decided ADR payload changed", tampered.stderr)

    def test_execplan_gates_require_concluded_research_and_accepted_adr(
        self,
    ) -> None:
        self.init()
        no_inputs = self.run_cli(
            "new-ep",
            "--slug",
            "ungated",
            "--title",
            "Ungated",
            expected=2,
        )
        self.assertIn("concluded --research", no_inputs.stderr)
        research = self.new_research("cache-options")
        self.conclude_research(research)
        adr = self.new_adr("cache-topology")
        proposed = self.run_cli(
            "new-ep",
            "--slug",
            "proposed-decision",
            "--title",
            "Proposed decision",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
            expected=2,
        )
        self.assertIn("accepted and current", proposed.stderr)

        self.accept_adr(adr)
        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "gated-plan",
                "--title",
                "Gated plan",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        content = plan.read_text(encoding="utf-8")
        self.assertIn('schema_version: "2.6"', content)
        self.assertIn("required_benchmark_scenarios: []", content)
        self.assertIn("verified_revision:", content)
        self.assertIn("verification_evidence: []", content)
        self.assertIn("archive_sha256:", content)
        self.assertIn("research_gate: satisfied", content)
        self.assertIn("architecture_decision_gate: satisfied", content)
        self.assertIn("architecture_compliance: applicable", content)
        self.assertIn('adr_constraint_refs: ["ADR-001#C-001"]', content)
        self.assertRegex(
            content,
            r'adr_evidence: \["ADR-001@sha256:[0-9a-f]{64}"\]',
        )
        self.assertIn("## Architecture Compliance Matrix", content)
        self.assertIn("R-001", content)
        self.assertIn("ADR-001", content)
        validation = self.run_cli("validate")
        self.assertIn('"errors": 0', validation.stdout)
        status = json.loads(self.run_cli("status", "--json").stdout)
        self.assertEqual(status["plans"][0]["research_gate"], "satisfied")
        self.assertEqual(status["plans"][0]["architecture_gate"], "satisfied")
        self.assertEqual(
            status["plans"][0]["architecture_compliance"],
            "applicable",
        )

    def test_existing_architecture_can_apply_without_a_new_decision(self) -> None:
        self.init()
        research = self.new_research("existing-architecture")
        self.conclude_research(research)
        adr = self.new_adr("existing-boundary")
        self.accept_adr(adr)

        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "apply-existing-boundary",
                "--title",
                "Apply existing boundary",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
                "--decision-not-required-reason",
                "The accepted decision already covers this implementation.",
            ).stdout.strip()
        )
        content = plan.read_text(encoding="utf-8")

        self.assertIn("architecture_decision_gate: not_required", content)
        self.assertIn("architecture_compliance: applicable", content)
        self.assertIn('adr_constraint_refs: ["ADR-001#C-001"]', content)
        self.run_cli("validate")

    def test_schema_12_amendments_are_scoped_to_existing_constraints(self) -> None:
        self.init()
        research = self.new_research("scoped-amendment")
        self.conclude_research(research)
        base = self.new_adr("base-boundary")
        self.accept_adr(base)

        missing_scope = self.run_cli(
            "new-adr",
            "--slug",
            "unscoped-change",
            "--title",
            "Unscoped change",
            "--research",
            "R-001",
            "--amends",
            "ADR-001",
            expected=2,
        )
        self.assertIn("missing constraint references for ADR-001", missing_scope.stderr)

        unknown_scope = self.run_cli(
            "new-adr",
            "--slug",
            "unknown-scope",
            "--title",
            "Unknown scope",
            "--research",
            "R-001",
            "--amends",
            "ADR-001",
            "--amends-constraint",
            "ADR-001#C-999",
            expected=2,
        )
        self.assertIn("does not identify a structured constraint", unknown_scope.stderr)

        amendment = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "scoped-change",
                "--title",
                "Scoped change",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        self.assertIn(
            'amends_constraints: ["ADR-001#C-001"]',
            amendment.read_text(encoding="utf-8"),
        )
        self.accept_adr(amendment, "ADR-002")

        stale = self.run_cli(
            "new-ep",
            "--slug",
            "stale-amendment-input",
            "--title",
            "Stale amendment input",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
            expected=2,
        )
        self.assertIn("omits current scoped amendments", stale.stderr)

        current = self.run_cli(
            "new-ep",
            "--slug",
            "current-amendment-input",
            "--title",
            "Current amendment input",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
            "--adr",
            "ADR-002",
        )
        self.assertIn("ep-001_current-amendment-input", current.stdout)
        self.run_cli("validate")

    def test_ep_architecture_mapping_and_adr_evidence_fail_closed(self) -> None:
        self.init()
        research = self.new_research("architecture-evidence")
        self.conclude_research(research)
        adr = self.new_adr("architecture-evidence")
        self.accept_adr(adr)
        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "architecture-evidence",
                "--title",
                "Architecture evidence",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        original = plan.read_text(encoding="utf-8")

        self.replace_section_body(
            plan,
            "Architecture Compliance Matrix",
            "\n".join(
                (
                    "| ADR constraint or architecture input | Implementation or preservation | Verification |",
                    "|---|---|---|",
                    "| ADR-001#C-999 | Preserve another boundary. | Run another test. |",
                )
            ),
        )
        mapping_error = self.run_cli("validate", expected=1)
        self.assertIn(
            "Architecture Compliance Matrix does not match architecture inputs",
            mapping_error.stderr,
        )

        plan.write_text(original, encoding="utf-8")
        self.replace_frontmatter(
            plan,
            "adr_evidence",
            '["ADR-001@sha256:' + ("0" * 64) + '"]',
        )
        digest_error = self.run_cli("validate", expected=1)
        self.assertIn("ADR evidence digest changed for ADR-001", digest_error.stderr)

    def test_completed_ep_retains_superseded_adr_evidence(self) -> None:
        self.init()
        research = self.new_research("historical-architecture")
        self.conclude_research(research)
        old_adr = self.new_adr("historical-v1")
        self.accept_adr(old_adr, "ADR-001")

        completed_plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "historical-completed",
                "--title",
                "Historical completed",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        self.complete_all_placeholders(completed_plan)
        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )
        active_plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "historical-active",
                "--title",
                "Historical active",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        replacement = self.new_adr("historical-v2")
        self.accept_adr(replacement, "ADR-002")
        self.run_cli("supersede-adr", "ADR-001", "--by", "ADR-002")

        stale = self.run_cli("validate", expected=1)
        error_lines = [
            line for line in stale.stderr.splitlines() if line.startswith("ERROR:")
        ]
        self.assertTrue(any(str(active_plan) in line for line in error_lines))
        self.assertFalse(any(str(archived) in line for line in error_lines))

        cancelled = Path(
            self.run_cli(
                "archive-ep",
                "EP-002",
                "--outcome",
                "cancelled",
                "--reason",
                "The governing architecture was superseded.",
            ).stdout.strip()
        )
        self.assertIn("status: cancelled", cancelled.read_text(encoding="utf-8"))
        self.run_cli("validate")

    def test_linked_multi_adr_and_design_doc_corpus_is_dependency_closed(
        self,
    ) -> None:
        self.init()
        design_root = self.repo / "docs" / "design-docs"
        design_root.mkdir()
        (design_root / "index.md").write_text(
            "# Architecture entrypoint\n",
            encoding="utf-8",
        )
        design_ref = "docs/design-docs/spans-env-placement-routing.md"
        (self.repo / design_ref).write_text(
            """---
doc_type: design
status: draft
owner: platform
last_verified: 2026-07-20
relates_to:
  - ADR-010
  - ADR-011
---

# Spans environment placement routing
""",
            encoding="utf-8",
        )
        (design_root / "ADR-010-Spans-Storage-Substrate.md").write_text(
            """---
doc_type: adr
title: Spans storage substrate
status: accepted
created: 2026-07-18
last_verified: 2026-07-20
relates_to:
  - docs/design-docs/spans-env-placement-routing.md
---

# ADR-010: Spans storage substrate
""",
            encoding="utf-8",
        )
        (design_root / "ADR-011-Spans-Placement-Routing.md").write_text(
            f"""---
doc_type: adr
title: Spans placement routing
status: accepted
created: 2026-07-20
last_verified: 2026-07-20
depends_on: ["ADR-010"]
amends: []
design_refs: ["{design_ref}"]
relates_to:
  - ADR-010
  - {design_ref}
---

# ADR-011: Spans placement routing
""",
            encoding="utf-8",
        )

        registered = self.run_cli(
            "register-architecture-root",
            "docs/design-docs",
        )
        self.assertIn("docs/design-docs", registered.stdout)
        config = json.loads(
            (self.repo / "docs" / ".epctl" / "config.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            config["architecture_roots"],
            ["docs/adr", "docs/design-docs"],
        )
        validation = self.run_cli("validate")
        self.assertIn('"errors": 0', validation.stdout)
        self.assertIn("legacy linked ADR", validation.stderr)
        self.assertIn("still draft", validation.stderr)
        status = json.loads(self.run_cli("status", "--json").stdout)
        self.assertEqual(len(status["adrs"]), 2)
        self.assertEqual(status["adrs"][1]["depends_on"], ["ADR-010"])
        self.assertEqual(status["adrs"][1]["contract"], "legacy-linked")

        missing_dependency = self.run_cli(
            "new-ep",
            "--slug",
            "missing-dependency",
            "--title",
            "Missing dependency",
            "--research-not-required-reason",
            "Existing operational evidence is sufficient.",
            "--adr",
            "ADR-011",
            "--design",
            design_ref,
            expected=2,
        )
        self.assertIn("dependency-closed", missing_dependency.stderr)
        missing_design = self.run_cli(
            "new-ep",
            "--slug",
            "missing-design",
            "--title",
            "Missing design",
            "--research-not-required-reason",
            "Existing operational evidence is sufficient.",
            "--adr",
            "ADR-010",
            "--adr",
            "ADR-011",
            expected=2,
        )
        self.assertIn("requires Design Doc references", missing_design.stderr)

        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "spans-routing",
                "--title",
                "Implement spans routing",
                "--research-not-required-reason",
                "Existing operational evidence is sufficient.",
                "--adr",
                "ADR-010",
                "--adr",
                "ADR-011",
                "--design",
                design_ref,
                "--architecture-entrypoint",
                "docs/design-docs/index.md",
            ).stdout.strip()
        )
        plan_text = plan.read_text(encoding="utf-8")
        self.assertIn('schema_version: "2.6"', plan_text)
        self.assertIn('adr_refs: ["ADR-010", "ADR-011"]', plan_text)
        self.assertIn("architecture_decision_gate: satisfied", plan_text)
        self.assertIn("architecture_compliance: applicable", plan_text)
        self.assertIn(f'design_refs: ["{design_ref}"]', plan_text)
        self.assertIn(
            'architecture_entrypoint: "docs/design-docs/index.md"',
            plan_text,
        )
        self.run_cli("validate")

    def test_adr_dependency_cycles_and_duplicate_ids_are_rejected(self) -> None:
        self.init()
        design_root = self.repo / "docs" / "design-docs"
        design_root.mkdir()
        for number, dependency in ((10, "ADR-011"), (11, "ADR-010")):
            (design_root / f"ADR-{number:03d}-cycle.md").write_text(
                f"""---
doc_type: adr
title: Cycle {number}
status: accepted
depends_on: ["{dependency}"]
---

# ADR-{number:03d}
""",
                encoding="utf-8",
            )
        self.run_cli("register-architecture-root", "docs/design-docs")
        cycle = self.run_cli("validate", expected=1)
        self.assertIn("ADR dependency cycle", cycle.stderr)

        duplicate_root = self.repo / "docs" / "other-decisions"
        duplicate_root.mkdir()
        (duplicate_root / "ADR-010-duplicate.md").write_text(
            """---
doc_type: adr
title: Duplicate
status: accepted
---

# Duplicate ADR-010
""",
            encoding="utf-8",
        )
        self.run_cli("register-architecture-root", "docs/other-decisions")
        duplicate = self.run_cli("validate", expected=1)
        self.assertIn("duplicate ADR id ADR-010", duplicate.stderr)

    def test_architecture_roots_and_design_refs_stay_under_registered_docs(
        self,
    ) -> None:
        self.init()
        docs_root = self.run_cli(
            "register-architecture-root",
            "docs",
            expected=2,
        )
        self.assertIn("below docs", docs_root.stderr)
        traversal = self.run_cli(
            "register-architecture-root",
            "../outside",
            expected=2,
        )
        self.assertIn("escapes repository", traversal.stderr)

        design_root = self.repo / "docs" / "design-docs"
        design_root.mkdir()
        outside_design = self.repo / "docs" / "outside.md"
        outside_design.write_text("# Outside\n", encoding="utf-8")
        (design_root / "ADR-010-invalid-design.md").write_text(
            """---
doc_type: adr
title: Invalid design reference
status: accepted
design_refs: ["docs/outside.md"]
---

# ADR-010
""",
            encoding="utf-8",
        )
        self.run_cli("register-architecture-root", "docs/design-docs")
        invalid_design = self.run_cli("validate", expected=1)
        self.assertIn(
            "must be inside a registered architecture root",
            invalid_design.stderr,
        )

    def test_declared_unknown_adr_schema_fails_closed(self) -> None:
        self.init()
        (self.repo / "docs" / "adr" / "adr-001_unknown.md").write_text(
            """---
schema_version: "9"
id: ADR-001
title: Unknown schema
status: accepted
created: 2026-07-28
updated: 2026-07-28
---

# Unknown schema
""",
            encoding="utf-8",
        )
        self.run_cli("reindex")
        result = self.run_cli("validate", expected=1)
        self.assertIn("ADR schema_version must be 1, 1.1 or 1.2", result.stderr)

    def test_accepted_adr_can_supersede_an_accepted_adr(self) -> None:
        self.init()
        research = self.new_research("protocol-options")
        self.conclude_research(research)
        old_adr = self.new_adr("protocol-v1")
        self.accept_adr(old_adr, "ADR-001")
        new_adr = self.new_adr("protocol-v2")
        self.accept_adr(new_adr, "ADR-002")

        superseded = Path(
            self.run_cli(
                "supersede-adr",
                "ADR-001",
                "--by",
                "ADR-002",
            ).stdout.strip()
        )

        self.assertIn("status: superseded", superseded.read_text(encoding="utf-8"))
        self.assertIn("superseded_by: ADR-002", superseded.read_text(encoding="utf-8"))
        self.assertIn(
            'supersedes: ["ADR-001"]',
            new_adr.read_text(encoding="utf-8"),
        )
        self.run_cli("validate")
        stale = self.run_cli(
            "new-ep",
            "--slug",
            "stale-decision",
            "--title",
            "Stale decision",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
            expected=2,
        )
        self.assertIn("accepted and current", stale.stderr)
        current = self.run_cli(
            "new-ep",
            "--slug",
            "current-decision",
            "--title",
            "Current decision",
            "--research",
            "R-001",
            "--adr",
            "ADR-002",
        )
        self.assertIn("ep-001_current-decision", current.stdout)

    def test_schema_12_adr_seals_typed_inputs_and_decision_outcome(self) -> None:
        self.init()
        research = self.new_research("sealed-inputs")
        self.conclude_research(research)
        first = self.new_adr("base-decision")
        self.accept_adr(first, "ADR-001")
        second = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "dependent-decision",
                "--title",
                "Dependent decision",
                "--research",
                "R-001",
                "--depends-on",
                "ADR-001",
            ).stdout.strip()
        )
        self.accept_adr(second, "ADR-002")
        accepted_text = second.read_text(encoding="utf-8")

        self.replace_frontmatter(second, "depends_on", "[]")
        relation_tamper = self.run_cli("validate", expected=1)
        self.assertIn("decided ADR payload changed", relation_tamper.stderr)

        second.write_text(accepted_text, encoding="utf-8")
        self.replace_frontmatter(second, "status", "rejected")
        outcome_tamper = self.run_cli("validate", expected=1)
        self.assertIn("decided ADR payload changed", outcome_tamper.stderr)

    def test_schema_11_adr_remains_a_valid_ep_input(self) -> None:
        self.init()
        research = self.new_research("schema-11-compatible")
        self.conclude_research(research)
        adr = self.new_adr("schema-11-compatible")
        text = adr.read_text(encoding="utf-8").replace(
            'schema_version: "1.2"',
            'schema_version: "1.1"',
            1,
        )
        text = re.sub(
            r"(?m)^amends_constraints:.*\n",
            "",
            text,
            count=1,
        )
        text = re.sub(
            r"(?ms)^## Decision Statement\s*$.*?"
            r"(?=^## Consequences\s*$)",
            "",
            text,
            count=1,
        )
        adr.write_text(text, encoding="utf-8")
        self.accept_adr(adr)

        accepted_text = adr.read_text(encoding="utf-8")

        def scalar(key: str) -> str:
            match = re.search(
                rf"(?m)^{re.escape(key)}:\s*(.*)$",
                accepted_text,
            )
            if not match:
                raise AssertionError(f"missing ADR field: {key}")
            value = match.group(1).strip()
            return json.loads(value) if value.startswith('"') else value

        frontmatter_end = accepted_text.find("\n---\n", 4)
        legacy_payload = {
            "schema_version": scalar("schema_version"),
            "id": scalar("id"),
            "title": scalar("title"),
            "research_refs": scalar("research_refs"),
            "depends_on": scalar("depends_on"),
            "amends": scalar("amends"),
            "design_refs": scalar("design_refs"),
            "decision_maker": scalar("decision_maker"),
            "decided": scalar("decided"),
            "decision_outcome": "accepted",
            "body": accepted_text[frontmatter_end + 5 :],
        }
        expected_legacy_digest = hashlib.sha256(
            json.dumps(
                legacy_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(scalar("payload_sha256"), expected_legacy_digest)

        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "consume-schema-11",
                "--title",
                "Consume schema 11",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        plan_text = plan.read_text(encoding="utf-8")
        self.assertIn("adr_constraint_refs: []", plan_text)
        self.assertRegex(
            plan_text,
            r'adr_evidence: \["ADR-001@sha256:[0-9a-f]{64}"\]',
        )
        self.assertIn("| ADR-001 |", plan_text)
        self.run_cli("validate")

    def test_v25_execplan_remains_archive_compatible(self) -> None:
        self.init()
        plan = self.new_ep("v25-compatible")
        text = plan.read_text(encoding="utf-8").replace(
            'schema_version: "2.6"',
            'schema_version: "2.5"',
            1,
        )
        text = text.replace(
            "architecture_decision_gate:",
            "architecture_gate:",
            1,
        ).replace(
            "architecture_decision_gate_reason:",
            "architecture_gate_reason:",
            1,
        )
        text = re.sub(
            r"(?m)^(?:adr_constraint_refs|adr_evidence|"
            r"architecture_compliance|architecture_compliance_reason):.*\n",
            "",
            text,
        )
        text = re.sub(
            r"(?ms)^## Architecture Compliance Matrix\s*$.*?"
            r"(?=^## Benchmark Gate Set\s*$)",
            "",
            text,
            count=1,
        )
        plan.write_text(text, encoding="utf-8")
        self.complete_all_placeholders(plan)

        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )
        self.assertIn(
            'schema_version: "2.5"',
            archived.read_text(encoding="utf-8"),
        )
        self.run_cli("validate")

    def test_v24_execplan_remains_archive_compatible(self) -> None:
        self.init()
        plan = self.new_ep("v24-compatible")
        text = plan.read_text(encoding="utf-8").replace(
            'schema_version: "2.6"',
            'schema_version: "2.4"',
            1,
        )
        text = text.replace(
            "architecture_decision_gate:",
            "architecture_gate:",
            1,
        ).replace(
            "architecture_decision_gate_reason:",
            "architecture_gate_reason:",
            1,
        )
        text = re.sub(
            r"(?m)^(?:adr_constraint_refs|adr_evidence|"
            r"architecture_compliance|architecture_compliance_reason|"
            r"required_benchmark_scenarios):.*\n",
            "",
            text,
        )
        text = re.sub(
            r"(?ms)^## Architecture Compliance Matrix\s*$.*?"
            r"(?=^## Benchmark Gate Set\s*$)",
            "",
            text,
            count=1,
        )
        text = re.sub(
            r"(?ms)^## Benchmark Gate Set\s*$.*?"
            r"(?=^## Plan of Work\s*$)",
            "",
            text,
            count=1,
        )
        plan.write_text(text, encoding="utf-8")
        self.complete_all_placeholders(plan)

        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )
        archived_text = archived.read_text(encoding="utf-8")
        self.assertIn('schema_version: "2.4"', archived_text)
        self.assertNotIn("required_benchmark_scenarios:", archived_text)
        self.run_cli("validate")

    def test_v21_execplan_remains_readable_and_valid(self) -> None:
        self.init()
        plan = self.new_ep("legacy-compatible")
        text = plan.read_text(encoding="utf-8").replace(
            'schema_version: "2.6"',
            'schema_version: "2.1"',
            1,
        )
        text = re.sub(
            r"(?m)^(?:research_refs|research_gate|research_gate_reason|"
            r"adr_refs|adr_constraint_refs|adr_evidence|design_refs|"
            r"architecture_entrypoint|architecture_decision_gate|"
            r"architecture_decision_gate_reason|architecture_compliance|"
            r"architecture_compliance_reason|"
            r"required_benchmark_scenarios|"
            r"verified_revision|verification_evidence|archive_sha256):.*\n",
            "",
            text,
        )
        text = re.sub(
            r"(?ms)^## Research and Architecture Inputs\s*$.*?"
            r"(?=^## Benchmark Gate Set\s*$)",
            "",
            text,
            count=1,
        )
        text = re.sub(
            r"(?ms)^## Benchmark Gate Set\s*$.*?"
            r"(?=^## Plan of Work\s*$)",
            "",
            text,
            count=1,
        )
        plan.write_text(text, encoding="utf-8")
        (self.repo / "docs" / "RESEARCH.md").unlink()
        (self.repo / "docs" / "DECISIONS.md").unlink()

        result = self.run_cli("validate")

        self.assertIn('"errors": 0', result.stdout)
        self.assertIn("RESEARCH.md: missing; run init", result.stderr)
        self.assertIn("DECISIONS.md: missing; run init", result.stderr)

    def test_v22_execplan_remains_archive_compatible(self) -> None:
        self.init()
        plan = self.new_ep("v22-compatible")
        text = plan.read_text(encoding="utf-8").replace(
            'schema_version: "2.6"',
            'schema_version: "2.2"',
            1,
        )
        text = text.replace(
            "architecture_decision_gate:",
            "architecture_gate:",
            1,
        ).replace(
            "architecture_decision_gate_reason:",
            "architecture_gate_reason:",
            1,
        )
        text = re.sub(
            r"(?m)^(?:verified_revision|verification_evidence|"
            r"archive_sha256|design_refs|architecture_entrypoint|"
            r"adr_constraint_refs|adr_evidence|architecture_compliance|"
            r"architecture_compliance_reason|required_benchmark_scenarios):.*\n",
            "",
            text,
        )
        text = re.sub(
            r"(?ms)^## Architecture Compliance Matrix\s*$.*?"
            r"(?=^## Benchmark Gate Set\s*$)",
            "",
            text,
            count=1,
        )
        text = re.sub(
            r"(?ms)^## Benchmark Gate Set\s*$.*?"
            r"(?=^## Plan of Work\s*$)",
            "",
            text,
            count=1,
        )
        plan.write_text(text, encoding="utf-8")
        self.complete_all_placeholders(plan)

        archived = Path(self.run_cli("archive-ep", "EP-001").stdout.strip())
        archived_text = archived.read_text(encoding="utf-8")
        self.assertIn('schema_version: "2.2"', archived_text)
        self.assertNotIn("verified_revision:", archived_text)
        self.assertNotIn("verification_evidence:", archived_text)
        self.assertNotIn("archive_sha256:", archived_text)
        self.run_cli("validate")

    def test_v20_execplan_remains_readable_and_valid(self) -> None:
        self.init()
        plan = self.new_ep("v20-compatible")
        text = plan.read_text(encoding="utf-8").replace(
            'schema_version: "2.6"',
            'schema_version: "2.0"',
            1,
        )
        text = re.sub(
            r"(?m)^(?:latest_checkpoint|research_refs|research_gate|"
            r"research_gate_reason|adr_refs|adr_constraint_refs|adr_evidence|"
            r"architecture_decision_gate|architecture_decision_gate_reason|"
            r"architecture_compliance|architecture_compliance_reason|"
            r"design_refs|architecture_entrypoint|"
            r"required_benchmark_scenarios|"
            r"verified_revision|"
            r"verification_evidence|archive_sha256):.*\n",
            "",
            text,
        )
        for heading, next_heading in (
            ("Current Snapshot", "Context and Orientation"),
            ("Research and Architecture Inputs", "Benchmark Gate Set"),
            ("Benchmark Gate Set", "Plan of Work"),
        ):
            text = re.sub(
                rf"(?ms)^## {re.escape(heading)}\s*$.*?"
                rf"(?=^## {re.escape(next_heading)}\s*$)",
                "",
                text,
                count=1,
            )
        plan.write_text(text, encoding="utf-8")

        result = self.run_cli("validate")

        self.assertIn('"errors": 0', result.stdout)
        self.assertIn("v2.0 plan has no bounded checkpoint model", result.stderr)

    def test_high_water_prevents_id_reuse_and_supports_four_digits(self) -> None:
        self.init()
        state_path = self.repo / "docs" / ".epctl" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["high_water"]["EP"] = 999
        state_path.write_text(json.dumps(state), encoding="utf-8")

        plan = self.new_ep("thousandth-plan")

        self.assertEqual(plan.parent.name, "ep-1000_thousandth-plan")
        self.assertIn("id: EP-1000", plan.read_text(encoding="utf-8"))

    def test_concurrent_creation_allocates_unique_ids(self) -> None:
        self.init()
        processes: list[subprocess.Popen[str]] = []
        for number in range(12):
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--repo",
                        str(self.repo),
                        "new-ep",
                        "--slug",
                        f"plan-{number}",
                        "--title",
                        f"Plan {number}",
                        *FAST_TRACK_ARGS,
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            )
        outputs: list[str] = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, stderr)
            outputs.append(stdout)

        ids = {
            re.search(r"ep-(\d+)_", output).group(1)
            for output in outputs
        }
        self.assertEqual(len(ids), 12)
        plans = list(
            (self.repo / "docs" / "exec-plans" / "active").glob(
                "ep-*/EXECPLAN.md"
            )
        )
        self.assertEqual(len(plans), 12)
        result = self.run_cli("validate")
        self.assertIn('"errors": 0', result.stdout)

    def test_stale_index_is_detected_and_fixable(self) -> None:
        self.init()
        plan = self.new_ep()
        plans_index = self.repo / "docs" / "PLANS.md"
        text = plans_index.read_text(encoding="utf-8")
        text = "\n".join(
            line for line in text.splitlines() if "| EP-001 |" not in line
        ) + "\n\n## Human notes\n\nKeep this paragraph.\n"
        plans_index.write_text(text, encoding="utf-8")

        failed = self.run_cli("validate", expected=1)
        self.assertIn("EP-001 missing from active; run reindex", failed.stderr)
        repaired = self.run_cli("validate", "--fix-index")

        self.assertIn('"errors": 0', repaired.stdout)
        self.assertIn("| EP-001 |", plans_index.read_text(encoding="utf-8"))
        self.assertIn(
            "Keep this paragraph.",
            plans_index.read_text(encoding="utf-8"),
        )
        self.assertTrue(plan.exists())

    def test_fix_index_repairs_all_artifact_projections(self) -> None:
        self.init()
        research = self.new_research("index-research")
        self.conclude_research(research)
        adr = self.new_adr("index-decision")
        self.accept_adr(adr)
        self.run_cli(
            "new-ep",
            "--slug",
            "index-plan",
            "--title",
            "Index plan",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
        )
        self.new_bugfix("index-bug")
        projections = (
            (self.repo / "docs" / "RESEARCH.md", "R-001"),
            (self.repo / "docs" / "DECISIONS.md", "ADR-001"),
            (self.repo / "docs" / "PLANS.md", "EP-001"),
            (self.repo / "docs" / "BUGFIXES.md", "BF-001"),
        )
        for index, item_id in projections:
            text = "\n".join(
                line
                for line in index.read_text(encoding="utf-8").splitlines()
                if f"| {item_id} |" not in line
            )
            index.write_text(
                text + f"\n\nHuman note for {item_id}.\n",
                encoding="utf-8",
            )

        broken = self.run_cli("validate", expected=1)
        for _, item_id in projections:
            self.assertIn(f"{item_id} missing", broken.stderr)
        repaired = self.run_cli("validate", "--fix-index")

        self.assertIn('"errors": 0', repaired.stdout)
        for index, item_id in projections:
            content = index.read_text(encoding="utf-8")
            self.assertIn(f"| {item_id} |", content)
            self.assertIn(f"Human note for {item_id}.", content)

    def test_markdown_parser_ignores_fenced_fake_sections(self) -> None:
        self.init()
        plan = self.new_ep()
        plan.write_text(
            plan.read_text(encoding="utf-8")
            + "\n```markdown\n## Validation and Acceptance\n- [x] fake\n```\n",
            encoding="utf-8",
        )

        clean = self.run_cli("validate")
        self.assertNotIn("duplicate ## Validation and Acceptance", clean.stderr)
        plan.write_text(
            plan.read_text(encoding="utf-8")
            + "\n## Validation and Acceptance\n- [ ] real duplicate\n",
            encoding="utf-8",
        )
        duplicate = self.run_cli("validate", expected=1)
        self.assertIn("duplicate ## Validation and Acceptance", duplicate.stderr)

    def test_duplicate_frontmatter_key_is_rejected(self) -> None:
        self.init()
        plan = self.new_ep()
        text = plan.read_text(encoding="utf-8")
        text = text.replace("status: active\n", "status: active\nstatus: blocked\n")
        plan.write_text(text, encoding="utf-8")

        result = self.run_cli("validate", expected=1)

        self.assertIn("Duplicate frontmatter key 'status'", result.stderr)

    def test_completed_ep_requires_acceptance_and_archives_atomically(self) -> None:
        self.init()
        plan = self.new_ep()
        blocked = self.run_cli(
            "archive-ep",
            "EP-001",
            *COMPLETION_ATTESTATION_ARGS,
            expected=2,
        )
        self.assertIn("incomplete acceptance", blocked.stderr)
        self.assertTrue(plan.exists())

        self.complete_all_placeholders(plan)
        unattested = self.run_cli("archive-ep", "EP-001", expected=2)
        self.assertIn("requires --verified-revision", unattested.stderr)
        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )

        self.assertTrue(archived.exists())
        self.assertFalse(plan.exists())
        archived_text = archived.read_text(encoding="utf-8")
        self.assertIn("status: completed", archived_text)
        self.assertIn('verified_revision: "test:verified-revision"', archived_text)
        self.assertIn(
            'verification_evidence: ["test:ep-integrity"]',
            archived_text,
        )
        self.assertRegex(archived_text, r"(?m)^archive_sha256: [0-9a-f]{64}$")
        self.run_cli("validate")
        archived.write_text(
            archived_text.replace(
                '"test:verified-revision"',
                '"test:tampered-revision"',
                1,
            ),
            encoding="utf-8",
        )
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("archived v2.6 plan changed", tampered.stderr)
        plans_index = (self.repo / "docs" / "PLANS.md").read_text(
            encoding="utf-8"
        )
        active = plans_index.split("<!-- EPCTL:ACTIVE:END -->", 1)[0]
        self.assertNotIn("| EP-001 |", active)
        self.assertIn("| EP-001 |", plans_index)

    def test_cancelled_ep_requires_reason_and_terminal_tasks(self) -> None:
        self.init()
        plan = self.new_ep()
        task_result = self.run_cli(
            "new-task",
            "EP-001",
            "--slug",
            "inspect-contract",
            "--title",
            "Inspect contract",
        )
        task = Path(task_result.stdout.strip())
        no_reason = self.run_cli(
            "archive-ep",
            "EP-001",
            "--outcome",
            "cancelled",
            expected=2,
        )
        self.assertIn("requires --reason", no_reason.stderr)
        blocked = self.run_cli(
            "archive-ep",
            "EP-001",
            "--outcome",
            "cancelled",
            "--reason",
            "Product direction changed",
            expected=2,
        )
        self.assertIn("task status", blocked.stderr)

        self.replace_frontmatter(task, "status", "cancelled")
        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                "--outcome",
                "cancelled",
                "--reason",
                "Product direction changed",
            ).stdout.strip()
        )

        self.assertTrue(archived.exists())
        content = archived.read_text(encoding="utf-8")
        self.assertIn("status: cancelled", content)
        self.assertIn("Product direction changed", content)
        self.assertRegex(content, r"(?m)^archive_sha256: [0-9a-f]{64}$")
        self.assertFalse(plan.exists())
        self.run_cli("validate")

    def test_fixed_bugfix_requires_verification(self) -> None:
        self.init()
        bugfix = self.new_bugfix()
        blocked = self.run_cli(
            "archive-bugfix",
            "BF-001",
            "--outcome",
            "fixed",
            expected=2,
        )
        self.assertIn("incomplete verification", blocked.stderr)

        self.complete_all_placeholders(bugfix)
        archived = Path(
            self.run_cli(
                "archive-bugfix",
                "BF-001",
                "--outcome",
                "fixed",
            ).stdout.strip()
        )

        self.assertTrue(archived.exists())
        self.assertIn("status: fixed", archived.read_text(encoding="utf-8"))

    def test_bugfix_can_escalate_to_existing_ep(self) -> None:
        self.init()
        self.new_ep("contract-redesign")
        bugfix = self.new_bugfix("login-regression")
        content = bugfix.read_text(encoding="utf-8")
        content = re.sub(
            r"<!--\s*REQUIRED\s*:[\s\S]*?-->",
            "Recorded symptom and scope.",
            content,
        )
        bugfix.write_text(content, encoding="utf-8")

        archived = Path(
            self.run_cli(
                "archive-bugfix",
                "BF-001",
                "--outcome",
                "escalated",
                "--linked-ep",
                "EP-001",
                "--reason",
                "The public token contract spans three clients",
            ).stdout.strip()
        )

        text = archived.read_text(encoding="utf-8")
        self.assertIn("status: escalated", text)
        self.assertIn("linked_ep: EP-001", text)
        self.assertIn("public token contract", text)
        self.assertIn("REQUIRED_FOR_FIXED", text)

    def test_blocked_state_and_open_blocker_must_agree(self) -> None:
        self.init()
        plan = self.new_ep()
        self.replace_frontmatter(plan, "status", "blocked")
        no_blocker = self.run_cli("validate", expected=1)
        self.assertIn("blocked status requires an open blocker", no_blocker.stderr)

        text = plan.read_text(encoding="utf-8")
        blocker = (
            "| BLK-001 | open | 2026-07-28 |  | API decision | "
            "Contract work | Product owner selects the field name |"
        )
        text = text.replace(
            "|---|---|---|---|---|---|---|\n",
            "|---|---|---|---|---|---|---|\n" + blocker + "\n",
            1,
        )
        plan.write_text(text, encoding="utf-8")
        consistent = self.run_cli("validate")
        self.assertIn('"errors": 0', consistent.stdout)

        self.replace_frontmatter(plan, "status", "active")
        inconsistent = self.run_cli("validate", expected=1)
        self.assertIn("open blockers require blocked status", inconsistent.stderr)

        text = plan.read_text(encoding="utf-8").replace(
            "| BLK-001 | open | 2026-07-28 |  |",
            "| BLK-001 | resolved | 2026-07-28 | 2026-07-28 |",
        )
        plan.write_text(text, encoding="utf-8")
        resolved = self.run_cli("validate")
        self.assertIn('"errors": 0', resolved.stdout)

    def test_task_dependency_cycle_is_rejected(self) -> None:
        self.init()
        self.new_ep()
        first = Path(
            self.run_cli(
                "new-task",
                "EP-001",
                "--slug",
                "add-interface",
                "--title",
                "Add interface",
            ).stdout.strip()
        )
        second = Path(
            self.run_cli(
                "new-task",
                "EP-001",
                "--slug",
                "wire-interface",
                "--title",
                "Wire interface",
            ).stdout.strip()
        )
        self.replace_frontmatter(first, "depends_on", '["TASK-002"]')
        self.replace_frontmatter(second, "depends_on", '["TASK-001"]')

        result = self.run_cli("validate", expected=1)

        self.assertIn("task dependency cycle detected", result.stderr)

    def test_task_blocked_by_matches_open_blockers(self) -> None:
        self.init()
        self.new_ep()
        task = Path(
            self.run_cli(
                "new-task",
                "EP-001",
                "--slug",
                "request-credential",
                "--title",
                "Request credential",
            ).stdout.strip()
        )
        self.replace_frontmatter(task, "status", "blocked")
        text = task.read_text(encoding="utf-8")
        blocker = (
            "| BLK-001 | open | 2026-07-28 |  | Test credential | "
            "Integration test | External team grants access |"
        )
        text = text.replace(
            "|---|---|---|---|---|---|---|\n",
            "|---|---|---|---|---|---|---|\n" + blocker + "\n",
            1,
        )
        task.write_text(text, encoding="utf-8")

        mismatch = self.run_cli("validate", expected=1)
        self.assertIn("blocked_by must exactly list open blockers", mismatch.stderr)
        self.replace_frontmatter(task, "blocked_by", '["BLK-001"]')
        consistent = self.run_cli("validate")

        self.assertIn('"errors": 0', consistent.stdout)

    def test_index_location_mismatch_is_detected(self) -> None:
        self.init()
        self.new_ep()
        plans_index = self.repo / "docs" / "PLANS.md"
        text = plans_index.read_text(encoding="utf-8")
        row = re.search(r"(?m)^\| EP-001 \|.*$", text).group(0)
        text = text.replace(row + "\n", "", 1)
        text = text.replace(
            "<!-- EPCTL:COMPLETED:END -->",
            row + "\n<!-- EPCTL:COMPLETED:END -->",
        )
        plans_index.write_text(text, encoding="utf-8")

        result = self.run_cli("validate", expected=1)

        self.assertIn("EP-001 missing from active", result.stderr)
        self.assertIn("stale EP-001 in completed", result.stderr)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_managed_symlink_is_rejected(self) -> None:
        self.init()
        active = self.repo / "docs" / "exec-plans" / "active"
        outside = self.repo / "outside"
        outside.mkdir()
        active.rmdir()
        active.symlink_to(outside, target_is_directory=True)

        result = self.run_cli(
            "new-ep",
            "--slug",
            "unsafe",
            "--title",
            "Unsafe",
            *FAST_TRACK_ARGS,
            expected=2,
        )

        self.assertIn("symbolic link", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_does_not_depend_on_git_or_path_lookup(self) -> None:
        self.init()
        environment = os.environ.copy()
        environment["PATH"] = ""

        result = self.run_cli(
            "new-ep",
            "--slug",
            "without-git",
            "--title",
            "Without Git",
            *FAST_TRACK_ARGS,
            env=environment,
        )

        self.assertIn("ep-001_without-git", result.stdout)

    def test_checkpoint_dry_run_does_not_mutate_plan_or_state(self) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)
        before_plan = plan.read_text(encoding="utf-8")
        state_path = self.repo / "docs" / ".epctl" / "state.json"
        before_state = state_path.read_text(encoding="utf-8")

        result = self.run_cli(
            "checkpoint",
            "EP-001",
            "--slug",
            "milestone-one",
            "--title",
            "Milestone 1 complete",
            "--current-milestone",
            "Milestone 2",
            "--summary",
            "Milestone 1 is complete; Milestone 2 is blocked on a credential.",
            "--next-action",
            "Request the credential, then edit service/handler.py.",
            *CHECKPOINT_REVISION_ARGS,
            "--dry-run",
        )
        payload = json.loads(result.stdout)

        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["checkpoint_id"], "CP-001")
        self.assertEqual(plan.read_text(encoding="utf-8"), before_plan)
        self.assertEqual(state_path.read_text(encoding="utf-8"), before_state)
        self.assertFalse((plan.parent / "history").exists())

    def test_checkpoint_seals_history_and_preserves_live_work(self) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)

        result = self.run_cli(
            "checkpoint",
            "EP-001",
            "--slug",
            "milestone-one",
            "--title",
            "Milestone 1 complete",
            "--current-milestone",
            "Milestone 2",
            "--summary",
            "Milestone 1 is complete; Milestone 2 is blocked on a credential.",
            "--next-action",
            "Request the credential, then edit service/handler.py.",
            *CHECKPOINT_REVISION_ARGS,
        )
        payload = json.loads(result.stdout)
        checkpoint = self.repo / payload["path"]

        self.assertTrue(checkpoint.is_file())
        self.assertEqual(payload["archived"]["progress_blocks"], 1)
        self.assertEqual(payload["archived"]["resolved_blockers"], 1)
        root = plan.read_text(encoding="utf-8")
        sealed = checkpoint.read_text(encoding="utf-8")
        self.assertIn("latest_checkpoint: CP-001", root)
        self.assertIn("[CP-001](history/cp-001_milestone-one.md)", root)
        self.assertIn("Current milestone: Milestone 2", root)
        self.assertNotIn("Milestone 1 completed", root)
        self.assertIn("Implement Milestone 2", root)
        self.assertIn("BLK-002 | open", root)
        self.assertNotIn("BLK-001 | resolved", root)
        self.assertIn("Milestone 1 completed", sealed)
        self.assertIn("BLK-001 | resolved", sealed)
        self.assertIn("Keep compatibility at the boundary", sealed)
        self.assertIn("status: sealed", sealed)
        self.assertIn('schema_version: "1.1"', sealed)
        self.assertIn(
            'repository_revision: "test:workspace-revision"',
            sealed,
        )
        validation = self.run_cli("validate")
        self.assertIn('"errors": 0', validation.stdout)

        status = json.loads(self.run_cli("status", "--json").stdout)
        plan_status = status["plans"][0]
        self.assertEqual(plan_status["latest_checkpoint"], "CP-001")
        self.assertEqual(plan_status["checkpoints"], 1)
        self.assertLess(plan_status["live_history_events"], 6)

    def test_checkpoint_chain_and_archive_move_history_together(self) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)
        self.run_cli(
            "checkpoint",
            "EP-001",
            "--slug",
            "milestone-one",
            "--title",
            "Milestone 1 complete",
            "--current-milestone",
            "Milestone 2",
            "--summary",
            "Milestone 1 is complete.",
            "--next-action",
            "Implement Milestone 2.",
            *CHECKPOINT_REVISION_ARGS,
        )
        text = plan.read_text(encoding="utf-8")
        text = text.replace("- [ ]", "- [x]")
        text = text.replace(
            "| BLK-002 | open | 2026-07-28 |  |",
            "| BLK-002 | resolved | 2026-07-28 | 2026-07-28 |",
        )
        plan.write_text(text, encoding="utf-8")
        self.replace_frontmatter(plan, "status", "active")
        self.replace_section_body(
            plan,
            "Decision Log",
            "- 2026-07-28 — Milestone 2 uses the stable adapter.",
        )

        second = json.loads(
            self.run_cli(
                "checkpoint",
                "EP-001",
                "--slug",
                "milestone-two",
                "--title",
                "Milestone 2 complete",
                "--current-milestone",
                "Final acceptance",
                "--summary",
                "All implementation milestones are complete.",
                "--next-action",
                "Run final acceptance and archive the plan.",
                *CHECKPOINT_REVISION_ARGS,
            ).stdout
        )
        second_path = self.repo / second["path"]
        self.assertIn(
            "previous_checkpoint: CP-001",
            second_path.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "latest_checkpoint: CP-002",
            plan.read_text(encoding="utf-8"),
        )

        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )

        self.assertTrue(archived.exists())
        self.assertTrue((archived.parent / "history").is_dir())
        self.assertEqual(
            len(list((archived.parent / "history").glob("cp-*.md"))),
            2,
        )

    def test_checkpoint_payload_tampering_is_detected(self) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)
        payload = json.loads(
            self.run_cli(
                "checkpoint",
                "EP-001",
                "--slug",
                "milestone-one",
                "--title",
                "Milestone 1 complete",
                "--current-milestone",
                "Milestone 2",
                "--summary",
                "Milestone 1 is complete.",
                "--next-action",
                "Implement Milestone 2.",
                *CHECKPOINT_REVISION_ARGS,
            ).stdout
        )
        checkpoint = self.repo / payload["path"]
        checkpoint.write_text(
            checkpoint.read_text(encoding="utf-8") + "\nTampered.\n",
            encoding="utf-8",
        )

        result = self.run_cli("validate", expected=1)

        self.assertIn("sealed checkpoint payload changed", result.stderr)

    def test_checkpoint_refuses_unresolved_template(self) -> None:
        self.init()
        self.new_ep()

        result = self.run_cli(
            "checkpoint",
            "EP-001",
            "--slug",
            "too-early",
            "--title",
            "Too early",
            "--current-milestone",
            "Plan authoring",
            "--summary",
            "The plan is not authored yet.",
            "--next-action",
            "Author the plan.",
            *CHECKPOINT_REVISION_ARGS,
            expected=2,
        )

        self.assertIn("required placeholders remain", result.stderr)

    def test_large_root_emits_checkpoint_warning(self) -> None:
        self.init()
        plan = self.new_ep()
        self.complete_all_placeholders(plan)
        text = plan.read_text(encoding="utf-8")
        text += "\n".join(f"line {number}" for number in range(900))
        plan.write_text(text, encoding="utf-8")

        result = self.run_cli("validate")

        self.assertIn("root working set is", result.stderr)

    def test_status_recommends_checkpoint_before_hard_limit(self) -> None:
        self.init()
        plan = self.new_ep()
        text = plan.read_text(encoding="utf-8")
        text += "\n" + "\n".join(
            f"working-set line {number}" for number in range(400)
        )
        plan.write_text(text, encoding="utf-8")

        result = self.run_cli("validate")
        status = json.loads(self.run_cli("status", "--json").stdout)
        plan_status = status["plans"][0]

        self.assertIn("checkpoint recommended", result.stderr)
        self.assertEqual(plan_status["working_set"], "checkpoint_recommended")
        self.assertLessEqual(plan_status["root_lines"], 800)

    def test_status_reports_scope_review_and_split_signals(self) -> None:
        self.init()
        plan = self.new_ep()
        self.replace_section_body(
            plan,
            "Milestones",
            "\n\n".join(
                f"### Milestone {number}: Outcome {number}\n\nDefined outcome."
                for number in range(1, 7)
            ),
        )

        review = json.loads(self.run_cli("status", "--json").stdout)["plans"][0]
        self.assertEqual(review["milestones"], 6)
        self.assertEqual(review["scope"], "scope_review")

        self.replace_section_body(
            plan,
            "Milestones",
            "\n\n".join(
                f"### Milestone {number}: Outcome {number}\n\nDefined outcome."
                for number in range(1, 10)
            ),
        )
        split = json.loads(self.run_cli("status", "--json").stdout)["plans"][0]

        self.assertEqual(split["milestones"], 9)
        self.assertEqual(split["scope"], "split_recommended")

    def test_status_distinguishes_archive_readiness_from_blockers(self) -> None:
        self.init()
        plan = self.new_ep()
        initial = json.loads(self.run_cli("status", "--json").stdout)["plans"][0]
        self.assertEqual(initial["completion"], "in_progress")

        self.complete_all_placeholders(plan)
        ready = json.loads(self.run_cli("status", "--json").stdout)["plans"][0]
        self.assertEqual(ready["completion"], "ready_to_archive")
        self.assertEqual(
            ready["archive_inputs_required"],
            ["verified_revision", "verification_evidence"],
        )

        self.run_cli(
            "new-task",
            "EP-001",
            "--slug",
            "late-task",
            "--title",
            "Late task",
        )
        blocked = json.loads(self.run_cli("status", "--json").stdout)["plans"][0]

        self.assertEqual(blocked["completion"], "archive_blocked")
        self.assertEqual(blocked["completion_blockers"], ["unfinished_tasks"])
        self.assertEqual(blocked["unfinished_tasks"], 1)


if __name__ == "__main__":
    unittest.main()
