from __future__ import annotations

import hashlib
import importlib.util
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

    def init_git(self) -> None:
        subprocess.run(
            ["git", "init", "-q", str(self.repo)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test User"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "config",
                "user.email",
                "test@example.com",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def commit_all(self, message: str) -> str:
        subprocess.run(
            ["git", "-C", str(self.repo), "add", "--all"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", message],
            check=True,
            capture_output=True,
            text=True,
        )
        return subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

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

    def write_single_design(
        self,
        design_id: str,
        slug: str,
        *,
        status: str = "current",
        dependencies: list[str] | None = None,
    ) -> tuple[str, str]:
        number = int(design_id.split("-", 1)[1])
        design_root = self.repo / "docs" / "design-docs"
        design_root.mkdir(parents=True, exist_ok=True)
        relative = f"docs/design-docs/dd-{number:03d}_{slug}.md"
        path = self.repo / relative
        published = 1 if status == "current" else 0
        approval = (
            (
                'approved_by: "Design Authority"\n'
                'approved_at: "2026-08-17T00:00:00Z"\n'
                'approval_ref: "test:explicit-design-approval"\n'
            )
            if published
            else 'approved_by: ""\napproved_at: ""\napproval_ref: ""\n'
        )
        title = f"{slug.replace('-', ' ').title()} design"
        root_text = (
            "---\n"
            'schema_version: "1.1"\n'
            'metadata_schema: "1"\n'
            "artifact_type: design-doc\n"
            f"id: {design_id}\n"
            "doc_type: design\n"
            "layout: single\n"
            f'title: "{title}"\n'
            f"status: {status}\n"
            'working_revision: "1"\n'
            f'published_revision: "{published}"\n'
            "research_refs: []\n"
            'research_not_required_reason: "Existing accepted architecture fixes this test input"\n'
            "adr_refs: []\n"
            f"design_dependencies: {json.dumps(dependencies or [])}\n"
            'decision_not_required_reason: "The fixture introduces no durable architecture decision"\n'
            f"{approval}"
            'superseded_by: ""\n'
            'terminal_reason: ""\n'
            'revision_reason: ""\n'
            'author: "Design Author"\n'
            'owner: "Design Owner"\n'
            "created: 2026-08-17\n"
            "updated: 2026-08-17\n"
            "---\n\n"
            f"# {title}\n\nThe complete technical contract is recorded here.\n"
        )
        path.write_text(root_text, encoding="utf-8")
        if not published:
            return relative, ""
        snapshot = (
            self.repo
            / "docs/.designctl/snapshots"
            / design_id
            / "rev-001"
        )
        snapshot.mkdir(parents=True)
        snapshot_design = snapshot / "DESIGN.md"
        snapshot_design.write_text(root_text, encoding="utf-8")
        payload = root_text.encode("utf-8")
        manifest = {
            "schema_version": "1",
            "metadata_schema": "1",
            "artifact_type": "design-revision-manifest",
            "id": f"{design_id}-REV-001",
            "design_id": design_id,
            "title": f"{title} — approved revision 1",
            "status": "current",
            "layout": "single",
            "author": "Design Author",
            "owner": "Design Owner",
            "created": "2026-08-17",
            "updated": "2026-08-17",
            "revision": 1,
            "approved_by": "Design Authority",
            "approved_at": "2026-08-17T00:00:00Z",
            "approval_ref": "test:explicit-design-approval",
            "entrypoint": "DESIGN.md",
            "documents": [
                {
                    "id": design_id,
                    "role": "entrypoint",
                    "path": "DESIGN.md",
                    "title": title,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            ],
        }
        (snapshot / "DESIGN_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return relative, f"{design_id}@rev:1@sha256:{digest}"

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
    def reseal_adr(path: Path) -> str:
        text = path.read_text(encoding="utf-8")

        def scalar(field: str) -> str:
            match = re.search(
                rf"(?m)^{re.escape(field)}:\s*(.*?)\s*$",
                text.split("---", 2)[1],
            )
            if not match:
                raise AssertionError(f"ADR field not found: {field}")
            value = match.group(1)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
                value = value[1:-1]
            return value

        frontmatter_end = text.find("\n---\n", 4)
        status = scalar("status")
        schema_version = scalar("schema_version")
        payload = {
            "schema_version": scalar("schema_version"),
            "id": scalar("id"),
            "title": scalar("title"),
            "research_refs": scalar("research_refs"),
            "depends_on": scalar("depends_on"),
            "amends": scalar("amends"),
            "design_refs": scalar("design_refs"),
            "decision_maker": scalar("decision_maker"),
            "decided": scalar("decided"),
            "decision_outcome": (
                scalar("decision_outcome")
                if schema_version == "1.4"
                else "accepted"
                if status in {"accepted", "under_review", "retired", "superseded"}
                else status
            ),
            "body": text[frontmatter_end + 5 :],
        }
        if schema_version in {"1.2", "1.3", "1.4"}:
            payload["amends_constraints"] = scalar("amends_constraints")
        if schema_version in {"1.3", "1.4"}:
            for field in (
                "metadata_schema",
                "artifact_type",
                "author",
                "owner",
                "created",
            ):
                payload[field] = scalar(field)
        if schema_version == "1.3":
            payload["updated"] = scalar("updated")
        digest = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        EpctlTestCase.replace_frontmatter(path, "payload_sha256", digest)
        return digest

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

    @staticmethod
    def managed_index_body(text: str, table: str) -> str:
        match = re.search(
            rf"<!-- ADRCTL:{re.escape(table)}:START -->([\s\S]*?)"
            rf"<!-- ADRCTL:{re.escape(table)}:END -->",
            text,
        )
        if not match:
            raise AssertionError(f"managed ADR table not found: {table}")
        return match.group(1)

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

    def test_current_artifacts_share_the_metadata_contract(self) -> None:
        self.init()
        adr = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "metadata-decision",
                "--title",
                "Metadata decision",
                "--author",
                "Architecture Writer",
                "--owner",
                "Architecture Owner",
            ).stdout.strip()
        )
        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "metadata-plan",
                "--title",
                "Metadata plan",
                "--author",
                "Plan Writer",
                "--owner",
                "Plan Owner",
                *FAST_TRACK_ARGS,
            ).stdout.strip()
        )
        task = Path(
            self.run_cli(
                "new-task",
                "EP-001",
                "--slug",
                "metadata-task",
                "--title",
                "Metadata task",
            ).stdout.strip()
        )
        bugfix = Path(
            self.run_cli(
                "new-bugfix",
                "--slug",
                "metadata-bug",
                "--title",
                "Metadata bug",
                "--author",
                "Bug Writer",
                "--owner",
                "Bug Owner",
            ).stdout.strip()
        )

        expected_profiles = (
            (adr, 'schema_version: "1.4"', "artifact_type: adr"),
            (plan, 'schema_version: "2.8"', "artifact_type: exec-plan"),
            (task, 'schema_version: "1"', "artifact_type: task"),
            (bugfix, 'schema_version: "1"', "artifact_type: bugfix"),
        )
        for path, schema, artifact_type in expected_profiles:
            text = path.read_text(encoding="utf-8")
            self.assertIn(schema, text)
            self.assertIn('metadata_schema: "1"', text)
            self.assertIn(artifact_type, text)
            for field in ("id", "title", "status", "author", "owner", "created", "updated"):
                self.assertRegex(text, rf"(?m)^{field}:\s+\S")
        task_text = task.read_text(encoding="utf-8")
        self.assertIn('author: "Plan Writer"', task_text)
        self.assertIn('owner: "Plan Owner"', task_text)

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
        self.assertIn('schema_version: "2.8"', content)
        self.assertIn('metadata_schema: "1"', content)
        self.assertIn("artifact_type: exec-plan", content)
        self.assertIn('author: "Unassigned"', content)
        self.assertIn('owner: "Unassigned"', content)
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
        preview = json.loads(
            self.run_cli(
                "supersede-adr",
                "ADR-001",
                "--by",
                "ADR-002",
                "--decision-maker",
                "Test Decision Owner",
                "--reason",
                "The old boundary is no longer fit.",
            ).stdout
        )
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(preview["affected_active_plans"], ["EP-002"])
        self.run_cli(
            "supersede-adr",
            "ADR-001",
            "--by",
            "ADR-002",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "The old boundary is no longer fit.",
            "--apply",
        )

        stale = self.run_cli("validate")
        self.assertIn("architecture_review_required", stale.stderr)
        self.assertNotIn(f"ERROR: {active_plan}", stale.stderr)
        self.assertNotIn(f"ERROR: {archived}", stale.stderr)

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
    def test_adr_review_transition_preserves_history_and_pauses_active_work(
        self,
    ) -> None:
        self.init()
        research = self.new_research("reversible-effect")
        self.conclude_research(research)
        base = self.new_adr("reversible-base")
        self.accept_adr(base, "ADR-001")
        amendment = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "reversible-amendment",
                "--title",
                "Reversible amendment",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        self.accept_adr(amendment, "ADR-002")
        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "reversible-plan",
                "--title",
                "Reversible plan",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
                "--adr",
                "ADR-002",
            ).stdout.strip()
        )
        original_digest = re.search(
            r"(?m)^payload_sha256:\s*([0-9a-f]{64})$",
            base.read_text(encoding="utf-8"),
        ).group(1)

        preview = json.loads(
            self.run_cli(
                "transition-adr",
                "ADR-001",
                "--to",
                "under_review",
                "--decision-maker",
                "Test Decision Owner",
                "--reason",
                "Production evidence questions the decision.",
            ).stdout
        )
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(preview["affected_adrs"], ["ADR-002"])
        self.assertEqual(preview["affected_active_plans"], ["EP-001"])
        self.assertIn("status: accepted", base.read_text(encoding="utf-8"))

        self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "under_review",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "Production evidence questions the decision.",
            "--apply",
        )
        reviewed_text = base.read_text(encoding="utf-8")
        self.assertIn("status: under_review", reviewed_text)
        self.assertIn(f"payload_sha256: {original_digest}", reviewed_text)
        validation = self.run_cli("validate")
        self.assertIn("architecture_review_required", validation.stderr)
        status = json.loads(self.run_cli("status", "--json").stdout)
        plan_status = next(row for row in status["plans"] if row["id"] == "EP-001")
        self.assertTrue(plan_status["architecture_review_required"])
        self.assertIn(
            "architecture_review_required",
            plan_status["completion_blockers"],
        )
        self.complete_all_placeholders(plan)
        blocked = self.run_cli(
            "archive-ep",
            "EP-001",
            *COMPLETION_ATTESTATION_ARGS,
            expected=2,
        )
        self.assertIn("architecture_review_required", blocked.stderr)
        stale = self.run_cli(
            "new-ep",
            "--slug",
            "stale-reviewed-input",
            "--title",
            "Stale reviewed input",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
            "--adr",
            "ADR-002",
            expected=2,
        )
        self.assertIn("accepted and current", stale.stderr)

        self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "The decision was reaffirmed after review.",
            "--apply",
        )
        self.assertIn("status: accepted", base.read_text(encoding="utf-8"))
        self.assertIn(
            f"payload_sha256: {original_digest}",
            base.read_text(encoding="utf-8"),
        )
        self.run_cli("validate")

    def test_adr_index_projects_effective_review_and_history(self) -> None:
        self.init()
        research = self.new_research("effect-projection")
        self.conclude_research(research)
        base = self.new_adr("effect-base")
        self.accept_adr(base, "ADR-001")
        amendment = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "effect-amendment",
                "--title",
                "Effect amendment",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        self.accept_adr(amendment, "ADR-002")

        decision_index = self.repo / "docs" / "DECISIONS.md"
        projected = decision_index.read_text(encoding="utf-8")
        for table in ("CURRENT", "AMENDMENTS", "REVIEW"):
            self.assertIn(f"<!-- ADRCTL:{table}:START -->", projected)
        current = self.managed_index_body(projected, "CURRENT")
        amendments = self.managed_index_body(projected, "AMENDMENTS")
        historical = self.managed_index_body(projected, "COMPLETED")
        self.assertIn("| ADR-001 |", current)
        self.assertIn("| ADR-002 |", current)
        self.assertIn("partially amended", current)
        self.assertIn("amended by ADR-002", current)
        self.assertIn("| ADR-001#C-001 | ADR-002 | Effect amendment |", amendments)
        self.assertNotIn("| ADR-001 |", historical)

        status = json.loads(self.run_cli("status", "--json").stdout)
        base_status = next(row for row in status["adrs"] if row["id"] == "ADR-001")
        self.assertEqual(base_status["decision_outcome"], "accepted")
        self.assertEqual(base_status["projection"], "effective")
        self.assertEqual(base_status["effect"], "partially_amended")
        self.assertEqual(base_status["amended_by"], ["ADR-002"])
        self.assertTrue(base_status["current"])
        human_status = self.run_cli("status").stdout
        self.assertIn("| Decision | Effect | Current | Amended by |", human_status)
        self.assertIn("partially amended", human_status)

        self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "under_review",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "Production evidence questions the base decision.",
            "--apply",
        )
        projected = decision_index.read_text(encoding="utf-8")
        current = self.managed_index_body(projected, "CURRENT")
        review = self.managed_index_body(projected, "REVIEW")
        amendments = self.managed_index_body(projected, "AMENDMENTS")
        self.assertNotIn("| ADR-001 |", current)
        self.assertNotIn("| ADR-002 |", current)
        self.assertIn("| ADR-001 |", review)
        self.assertIn("under review", review)
        self.assertIn("| ADR-002 |", review)
        self.assertIn("review required", review)
        self.assertNotIn("ADR-001#C-001", amendments)

        self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "retired",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "The base constraint is no longer required.",
            "--apply",
        )
        projected = decision_index.read_text(encoding="utf-8")
        review = self.managed_index_body(projected, "REVIEW")
        historical = self.managed_index_body(projected, "COMPLETED")
        self.assertIn("| ADR-001 |", historical)
        self.assertIn("retired", historical)
        self.assertIn("| ADR-002 |", review)
        self.run_cli("validate")

    def test_reindex_upgrades_legacy_adr_layout_without_losing_human_notes(
        self,
    ) -> None:
        self.init()
        research = self.new_research("legacy-index")
        self.conclude_research(research)
        adr = self.new_adr("legacy-index")
        self.accept_adr(adr)
        relative = f"adr/{adr.name}"
        decision_index = self.repo / "docs" / "DECISIONS.md"
        legacy = (
            "# Architecture Decisions\n\n"
            "Human introduction that must survive projection upgrades.\n\n"
            "## Proposed\n\n"
            "<!-- ADRCTL:ACTIVE:START -->\n"
            "| ID | Title | Status | Updated | Research | Superseded By | Path |\n"
            "|---|---|---|---|---|---|---|\n"
            "<!-- ADRCTL:ACTIVE:END -->\n\n"
            "## Decided\n\n"
            "<!-- ADRCTL:COMPLETED:START -->\n"
            "| ID | Title | Status | Updated | Research | Superseded By | Path |\n"
            "|---|---|---|---|---|---|---|\n"
            f"| ADR-001 | Legacy Index | accepted | 2026-08-26 | "
            f"[\"R-001\"] |  | [ADR]({relative}) |\n"
            "<!-- ADRCTL:COMPLETED:END -->\n\n"
            "Human appendix that must also survive projection upgrades.\n"
        )
        decision_index.write_text(legacy, encoding="utf-8")

        validation = self.run_cli("validate")
        self.assertIn("legacy ADR index projection", validation.stderr)
        self.assertIn("run reindex", validation.stderr)

        self.run_cli("reindex")
        upgraded = decision_index.read_text(encoding="utf-8")
        self.assertIn("Human introduction that must survive", upgraded)
        self.assertIn("Human appendix that must also survive", upgraded)
        self.assertIn("## Effective", upgraded)
        self.assertIn("## Historical", upgraded)
        self.assertIn(
            "## Historical\n\n<!-- ADRCTL:COMPLETED:START -->",
            upgraded,
        )
        self.assertNotIn("## Decided", upgraded)
        self.assertIn(
            "| ADR-001 |",
            self.managed_index_body(upgraded, "CURRENT"),
        )
        self.assertNotIn(
            "| ADR-001 |",
            self.managed_index_body(upgraded, "COMPLETED"),
        )
        self.run_cli("validate")

        self.run_cli("reindex")
        self.assertEqual(upgraded, decision_index.read_text(encoding="utf-8"))

    def test_rejected_adr_is_projected_as_historical(self) -> None:
        self.init()
        research = self.new_research("rejected-projection")
        self.conclude_research(research)
        adr = self.new_adr("rejected-projection")
        self.complete_all_placeholders(adr)
        self.run_cli(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "rejected",
            "--decision-maker",
            "Test Decision Owner",
        )

        decision_index = (self.repo / "docs" / "DECISIONS.md").read_text(
            encoding="utf-8"
        )
        historical = self.managed_index_body(decision_index, "COMPLETED")
        self.assertIn("| ADR-001 |", historical)
        self.assertIn("| rejected | rejected |", historical)
        status = json.loads(self.run_cli("status", "--json").stdout)
        row = next(item for item in status["adrs"] if item["id"] == "ADR-001")
        self.assertEqual(row["projection"], "historical")
        self.assertEqual(row["effect"], "rejected")
        self.assertFalse(row["current"])
        self.run_cli("validate")

    def test_retired_adr_is_terminal_without_a_replacement(self) -> None:
        self.init()
        research = self.new_research("retired-effect")
        self.conclude_research(research)
        adr = self.new_adr("retired-effect")
        self.accept_adr(adr)

        retired = json.loads(
            self.run_cli(
                "transition-adr",
                "ADR-001",
                "--to",
                "retired",
                "--decision-maker",
                "Test Decision Owner",
                "--reason",
                "The constraint is no longer required.",
                "--apply",
            ).stdout
        )
        self.assertEqual(retired["replacement"], None)
        self.assertIn("status: retired", adr.read_text(encoding="utf-8"))
        illegal = self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "Attempt to reuse a terminal decision.",
            expected=2,
        )
        self.assertIn("Illegal ADR effect transition", illegal.stderr)
        self.run_cli("validate")

    def test_schema_13_effect_transition_keeps_legacy_digest(self) -> None:
        self.init()
        research = self.new_research("legacy-effect-digest")
        self.conclude_research(research)
        adr = self.new_adr("legacy-effect-digest")
        text = adr.read_text(encoding="utf-8").replace(
            'schema_version: "1.4"',
            'schema_version: "1.3"',
            1,
        )
        for field in (
            "decision_outcome",
            "effect_changed_by",
            "effect_changed",
            "effect_reason",
        ):
            text = re.sub(rf"(?m)^{field}:.*\n", "", text, count=1)
        adr.write_text(text, encoding="utf-8")
        self.accept_adr(adr)
        accepted = adr.read_text(encoding="utf-8")
        digest = re.search(
            r"(?m)^payload_sha256:\s*([0-9a-f]{64})$",
            accepted,
        ).group(1)
        updated = re.search(r"(?m)^updated:\s*(\S+)$", accepted).group(1)

        self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "under_review",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "Question the legacy decision effect.",
            "--apply",
        )
        reviewed = adr.read_text(encoding="utf-8")
        self.assertIn(f"payload_sha256: {digest}", reviewed)
        self.assertRegex(reviewed, rf"(?m)^updated:\s*{re.escape(updated)}$")
        self.run_cli("validate")

    def test_completed_ep_resolves_registered_historical_adr_revision(self) -> None:
        self.init()
        research = self.new_research("historical-byte-revision")
        self.conclude_research(research)
        adr = self.new_adr("historical-byte-revision")
        self.complete_all_placeholders(adr)
        adr.write_text(
            adr.read_text(encoding="utf-8").replace(
                "Recorded evidence.\n",
                "Recorded evidence. \n",
                1,
            ),
            encoding="utf-8",
        )
        self.run_cli(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
        )
        historical_text = adr.read_text(encoding="utf-8")
        historical_digest = re.search(
            r"(?m)^payload_sha256:\s*([0-9a-f]{64})$",
            historical_text,
        ).group(1)

        historical_plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "historical-byte-plan",
                "--title",
                "Historical byte plan",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        self.complete_all_placeholders(historical_plan)
        archived_historical = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )

        source = self.repo / "evidence" / "adr-001-historical.md"
        source.parent.mkdir()
        source.write_text(historical_text, encoding="utf-8")
        preview = json.loads(
            self.run_cli(
                "register-adr-revision",
                "ADR-001",
                "--from-file",
                "evidence/adr-001-historical.md",
            ).stdout
        )
        target = self.repo / preview["target"]
        self.assertEqual(preview["action"], "create")
        self.assertFalse(preview["applied"])
        self.assertFalse(target.exists())
        applied = json.loads(
            self.run_cli(
                "register-adr-revision",
                "ADR-001",
                "--from-file",
                "evidence/adr-001-historical.md",
                "--apply",
            ).stdout
        )
        self.assertTrue(applied["applied"])
        self.assertTrue(target.is_file())

        normalized = adr.read_text(encoding="utf-8").replace(
            "Recorded evidence. \n",
            "Recorded evidence.\n",
            1,
        )
        adr.write_text(normalized, encoding="utf-8")
        current_digest = self.reseal_adr(adr)
        self.assertNotEqual(historical_digest, current_digest)

        current_plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "current-byte-plan",
                "--title",
                "Current byte plan",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        self.complete_all_placeholders(current_plan)
        self.run_cli(
            "archive-ep",
            "EP-002",
            *COMPLETION_ATTESTATION_ARGS,
        )
        clean = self.run_cli("validate")
        self.assertIn('"errors": 0', clean.stdout)

        target.unlink()
        missing = self.run_cli("validate", expected=1)
        self.assertIn("ADR evidence digest changed for ADR-001", missing.stderr)
        self.run_cli(
            "register-adr-revision",
            "ADR-001",
            "--from-file",
            "evidence/adr-001-historical.md",
            "--apply",
        )

        active = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "active-must-use-current",
                "--title",
                "Active must use current",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )
        self.replace_frontmatter(
            active,
            "adr_evidence",
            f'["ADR-001@sha256:{historical_digest}"]',
        )
        stale_active = self.run_cli("validate", expected=1)
        active_errors = [
            line
            for line in stale_active.stderr.splitlines()
            if line.startswith("ERROR:") and str(active) in line
        ]
        self.assertTrue(
            any("ADR evidence digest changed for ADR-001" in line for line in active_errors)
        )
        self.assertFalse(
            any(str(archived_historical) in line for line in stale_active.stderr.splitlines())
        )

    def test_register_adr_revision_git_blob_and_store_fail_closed(self) -> None:
        self.init()
        research = self.new_research("git-revision-source")
        self.conclude_research(research)
        adr = self.new_adr("git-revision-source")
        self.accept_adr(adr)
        subprocess.run(
            ["git", "init", "-q", str(self.repo)],
            check=True,
            capture_output=True,
            text=True,
        )
        object_id = subprocess.run(
            ["git", "-C", str(self.repo), "hash-object", "-w", str(adr)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        preview = json.loads(
            self.run_cli(
                "register-adr-revision",
                "ADR-001",
                "--from-git-blob",
                object_id,
            ).stdout
        )
        self.assertEqual(preview["source"]["kind"], "git-blob")
        self.assertEqual(preview["source"]["locator"], object_id)
        target = self.repo / preview["target"]
        self.assertFalse(target.exists())
        self.run_cli(
            "register-adr-revision",
            "ADR-001",
            "--from-git-blob",
            object_id,
            "--apply",
        )
        preserved = json.loads(
            self.run_cli(
                "register-adr-revision",
                "ADR-001",
                "--from-git-blob",
                object_id,
                "--apply",
            ).stdout
        )
        self.assertEqual(preserved["action"], "preserve")

        invalid_object = self.run_cli(
            "register-adr-revision",
            "ADR-001",
            "--from-git-blob",
            "abc123",
            expected=2,
        )
        self.assertIn("full 40- or 64-character", invalid_object.stderr)
        wrong_id = self.run_cli(
            "register-adr-revision",
            "ADR-002",
            "--from-git-blob",
            object_id,
            expected=2,
        )
        self.assertIn("does not match ADR-002", wrong_id.stderr)

        source_link = self.repo / "adr-source-link.md"
        os.symlink(adr, source_link)
        linked_source = self.run_cli(
            "register-adr-revision",
            "ADR-001",
            "--from-file",
            "adr-source-link.md",
            expected=2,
        )
        self.assertIn("symbolic link", linked_source.stderr)

        target.write_text(
            target.read_text(encoding="utf-8") + "\nTampered revision.\n",
            encoding="utf-8",
        )
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("decided ADR payload changed", tampered.stderr)
        conflict = self.run_cli(
            "register-adr-revision",
            "ADR-001",
            "--from-git-blob",
            object_id,
            "--apply",
            expected=2,
        )
        self.assertIn("immutable bytes differ", conflict.stderr)

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
        self.assertIn("unpublished (draft)", validation.stderr)
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
        self.assertIn('schema_version: "2.8"', plan_text)
        self.assertIn('adr_refs: ["ADR-010", "ADR-011"]', plan_text)
        self.assertIn("architecture_decision_gate: satisfied", plan_text)
        self.assertIn("architecture_compliance: applicable", plan_text)
        self.assertIn(f'design_refs: ["{design_ref}"]', plan_text)
        self.assertIn(
            'architecture_entrypoint: "docs/design-docs/index.md"',
            plan_text,
        )
        self.run_cli("validate")

    def test_legacy_linked_adr_retirement_preserves_block_frontmatter(self) -> None:
        self.init()
        design_root = self.repo / "docs" / "design-docs"
        design_root.mkdir()
        (design_root / "index.md").write_text(
            "# Architecture entrypoint\n",
            encoding="utf-8",
        )
        adr = design_root / "ADR-010-Historical-API.md"
        adr.write_text(
            """---
doc_type: adr
title: Historical API design
status: accepted
last_verified: 2026-08-26
owner: platform
relates_to:
  - docs/current-api.md
  - pkg/api/
---

# ADR-010: Historical API design
""",
            encoding="utf-8",
        )
        self.run_cli(
            "register-architecture-root",
            "docs/design-docs",
        )

        preview = json.loads(
            self.run_cli(
                "transition-adr",
                "ADR-010",
                "--to",
                "retired",
                "--decision-maker",
                "Test Decision Owner",
                "--reason",
                "Current specifications own the contract.",
            ).stdout
        )
        self.assertEqual(preview["affected_adrs"], [])
        self.assertEqual(preview["affected_active_plans"], [])

        self.run_cli(
            "transition-adr",
            "ADR-010",
            "--to",
            "retired",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "Current specifications own the contract.",
            "--apply",
        )
        retired = adr.read_text(encoding="utf-8")
        self.assertIn("status: retired", retired)
        self.assertIn(
            "relates_to:\n  - docs/current-api.md\n  - pkg/api/",
            retired,
        )
        self.assertIn('effect_changed_by: "Test Decision Owner"', retired)
        self.assertIn(
            'effect_reason: "Current specifications own the contract."',
            retired,
        )
        decision_index = (self.repo / "docs" / "DECISIONS.md").read_text(
            encoding="utf-8"
        )
        historical = self.managed_index_body(decision_index, "COMPLETED")
        self.assertIn("| ADR-010 |", historical)
        self.assertIn("| accepted | retired |", historical)
        validation = self.run_cli("validate")
        self.assertIn('{"errors": 0', validation.stdout)

    def test_v28_execplan_pins_approved_design_revision(self) -> None:
        self.init()
        design_ref, design_evidence = self.write_single_design(
            "DD-001", "approved-service"
        )
        self.run_cli("register-architecture-root", "docs/design-docs")
        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "approved-design",
                "--title",
                "Implement approved design",
                "--research-not-required-reason",
                "The approved Design already carries the required evidence input",
                "--decision-not-required-reason",
                "The accepted Design introduces no additional architecture choice",
                "--design",
                design_ref,
            ).stdout.strip()
        )
        text = plan.read_text(encoding="utf-8")
        self.assertIn('schema_version: "2.8"', text)
        self.assertIn(
            f'design_evidence: ["{design_evidence}"]',
            text,
        )
        self.assertIn(
            f"Approved Design revision evidence: [\"{design_evidence}\"]",
            text,
        )
        self.complete_all_placeholders(plan)
        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )
        self.assertTrue(archived.is_file())
        self.run_cli("validate")

        snapshot = self.repo / "docs/.designctl/snapshots/DD-001/rev-001/DESIGN.md"
        snapshot.write_text(
            snapshot.read_text(encoding="utf-8") + "\nTampered.\n",
            encoding="utf-8",
        )
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("SHA-256 drift", tampered.stderr)

    def test_v28_completion_rejects_unpublished_design(self) -> None:
        self.init()
        design_ref, _ = self.write_single_design(
            "DD-001",
            "draft-service",
            status="draft",
        )
        self.run_cli("register-architecture-root", "docs/design-docs")
        created = self.run_cli(
            "new-ep",
            "--slug",
            "draft-design",
            "--title",
            "Inspect draft design",
            "--research-not-required-reason",
            "The draft Design already carries the required evidence input",
            "--decision-not-required-reason",
            "The draft introduces no additional architecture choice yet",
            "--design",
            design_ref,
        )
        self.assertIn("unpublished (draft)", created.stderr)
        plan = Path(created.stdout.strip())
        self.assertIn("design_evidence: []", plan.read_text(encoding="utf-8"))
        self.complete_all_placeholders(plan)
        status = json.loads(self.run_cli("status", "--json").stdout)["plans"][0]
        self.assertEqual(status["completion"], "archive_blocked")
        self.assertEqual(
            status["completion_blockers"],
            ["design_evidence_missing:DD-001"],
        )
        blocked = self.run_cli(
            "archive-ep",
            "EP-001",
            *COMPLETION_ATTESTATION_ARGS,
            expected=2,
        )
        self.assertIn(
            "EP completion requires approved revision evidence for DD-001",
            blocked.stderr,
        )

    def test_design_dependency_closure_is_required(self) -> None:
        self.init()
        caller_ref, _ = self.write_single_design(
            "DD-001",
            "caller",
            dependencies=["uses:DD-002"],
        )
        dependency_ref, dependency_evidence = self.write_single_design(
            "DD-002",
            "identity-service",
        )
        self.run_cli("register-architecture-root", "docs/design-docs")
        missing = self.run_cli(
            "new-ep",
            "--slug",
            "missing-design-dependency",
            "--title",
            "Missing Design dependency",
            "--research-not-required-reason",
            "The approved Designs already carry the required evidence input",
            "--decision-not-required-reason",
            "The Designs introduce no additional architecture choice",
            "--design",
            caller_ref,
            expected=2,
        )
        self.assertIn("requires a design_ref for DD-002", missing.stderr)

        plan = Path(
            self.run_cli(
                "new-ep",
                "--slug",
                "closed-design-dependency",
                "--title",
                "Closed Design dependency",
                "--research-not-required-reason",
                "The approved Designs already carry the required evidence input",
                "--decision-not-required-reason",
                "The Designs introduce no additional architecture choice",
                "--design",
                caller_ref,
                "--design",
                dependency_ref,
            ).stdout.strip()
        )
        self.assertIn(
            dependency_evidence,
            plan.read_text(encoding="utf-8"),
        )

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

    def test_current_design_doc_metadata_ids_are_unique(self) -> None:
        self.init()
        design_root = self.repo / "docs" / "design-docs"
        design_root.mkdir()
        for name in ("one", "two"):
            (design_root / f"{name}.md").write_text(
                f"""---
schema_version: "1"
metadata_schema: "1"
artifact_type: design-doc
id: DD-001
doc_type: design
title: "Design {name}"
status: current
author: "Design Writer"
owner: "Design Owner"
created: 2026-08-04
updated: 2026-08-04
---

# Design {name}
""",
                encoding="utf-8",
            )
        self.run_cli("register-architecture-root", "docs/design-docs")

        result = self.run_cli("validate", expected=1)

        self.assertIn("duplicate Design Doc id DD-001", result.stderr)

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
        self.assertIn(
            "ADR schema_version must be 1, 1.1, 1.2, 1.3 or 1.4",
            result.stderr,
        )

    def test_accepted_adr_can_supersede_an_accepted_adr(self) -> None:
        self.init()
        research = self.new_research("protocol-options")
        self.conclude_research(research)
        old_adr = self.new_adr("protocol-v1")
        self.accept_adr(old_adr, "ADR-001")
        new_adr = self.new_adr("protocol-v2")
        self.accept_adr(new_adr, "ADR-002")

        preview = json.loads(
            self.run_cli(
                "supersede-adr",
                "ADR-001",
                "--by",
                "ADR-002",
                "--decision-maker",
                "Test Decision Owner",
                "--reason",
                "Protocol v2 replaces v1.",
            ).stdout
        )
        self.assertEqual(preview["mode"], "preview")
        self.assertIn("status: accepted", old_adr.read_text(encoding="utf-8"))
        applied = json.loads(
            self.run_cli(
                "supersede-adr",
                "ADR-001",
                "--by",
                "ADR-002",
                "--decision-maker",
                "Test Decision Owner",
                "--reason",
                "Protocol v2 replaces v1.",
                "--apply",
            ).stdout
        )
        self.assertEqual(applied["mode"], "apply")

        self.assertIn("status: superseded", old_adr.read_text(encoding="utf-8"))
        self.assertIn("superseded_by: ADR-002", old_adr.read_text(encoding="utf-8"))
        self.assertIn(
            'supersedes: ["ADR-001"]',
            new_adr.read_text(encoding="utf-8"),
        )
        self.assertIn(
            'effect_changed_by: "Test Decision Owner"',
            new_adr.read_text(encoding="utf-8"),
        )
        decision_index = (self.repo / "docs" / "DECISIONS.md").read_text(
            encoding="utf-8"
        )
        historical = self.managed_index_body(decision_index, "COMPLETED")
        current_projection = self.managed_index_body(decision_index, "CURRENT")
        self.assertIn("| ADR-001 |", historical)
        self.assertIn("superseded by ADR-002", historical)
        self.assertIn("| ADR-002 |", current_projection)
        self.assertIn("supersedes ADR-001", current_projection)
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

    def test_current_adr_seals_metadata_typed_inputs_and_outcome(self) -> None:
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
        self.assertIn("decision_outcome must be 'rejected'", outcome_tamper.stderr)

        second.write_text(accepted_text, encoding="utf-8")
        self.replace_frontmatter(second, "author", '"Tampered Writer"')
        metadata_tamper = self.run_cli("validate", expected=1)
        self.assertIn("decided ADR payload changed", metadata_tamper.stderr)

    def test_schema_11_adr_remains_a_valid_ep_input(self) -> None:
        self.init()
        research = self.new_research("schema-11-compatible")
        self.conclude_research(research)
        adr = self.new_adr("schema-11-compatible")
        text = adr.read_text(encoding="utf-8").replace(
            'schema_version: "1.4"',
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
            'schema_version: "2.8"',
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
            'schema_version: "2.8"',
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
            'schema_version: "2.8"',
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
            'schema_version: "2.8"',
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
            'schema_version: "2.8"',
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
        self.assertIn("archived v2.8 plan changed", tampered.stderr)
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
        self.assertIn('schema_version: "1.2"', sealed)
        self.assertIn('metadata_schema: "1"', sealed)
        self.assertIn("artifact_type: checkpoint", sealed)
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
        original = checkpoint.read_text(encoding="utf-8")
        checkpoint.write_text(
            original + "\nTampered.\n",
            encoding="utf-8",
        )

        result = self.run_cli("validate", expected=1)

        self.assertIn("sealed checkpoint payload changed", result.stderr)

        checkpoint.write_text(original, encoding="utf-8")
        self.replace_frontmatter(checkpoint, "author", '"Tampered Writer"')
        metadata_result = self.run_cli("validate", expected=1)
        self.assertIn("sealed checkpoint payload changed", metadata_result.stderr)

    def test_register_checkpoint_recovery_is_preview_first_and_offline(self) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)
        payload = json.loads(
            self.run_cli(
                "checkpoint",
                "EP-001",
                "--slug",
                "born-invalid",
                "--title",
                "Born invalid checkpoint",
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
        self.replace_frontmatter(checkpoint, "payload_sha256", "0" * 64)
        checkpoint_bytes = checkpoint.read_bytes()
        mismatch = self.run_cli("validate", expected=1)
        self.assertIn("sealed checkpoint payload changed", mismatch.stderr)

        self.init_git()
        introducing_commit = self.commit_all("introduce invalid checkpoint")
        recovery_root = self.repo / "docs/.epctl/checkpoint-recoveries"
        preview = json.loads(
            self.run_cli(
                "register-checkpoint-recovery",
                "EP-001",
                "CP-001",
                "--from-git-commit",
                introducing_commit,
                "--attested-by",
                "Test Repository Owner",
                "--reason",
                "The checkpoint was introduced with the invalid seal.",
            ).stdout
        )
        target = self.repo / preview["target"]
        self.assertEqual(preview["action"], "create")
        self.assertFalse(preview["applied"])
        self.assertFalse(recovery_root.exists())
        self.assertFalse(target.exists())
        self.assertEqual(checkpoint.read_bytes(), checkpoint_bytes)
        self.assertEqual(preview["source"]["commit"], introducing_commit)
        self.assertRegex(preview["source"]["blob"], r"^[0-9a-f]{40}$")

        applied = json.loads(
            self.run_cli(
                "register-checkpoint-recovery",
                "EP-001",
                "CP-001",
                "--from-git-commit",
                introducing_commit,
                "--attested-by",
                "Test Repository Owner",
                "--reason",
                "The checkpoint was introduced with the invalid seal.",
                "--apply",
            ).stdout
        )
        self.assertTrue(applied["applied"])
        self.assertEqual(applied["receipt_sha256"], preview["receipt_sha256"])
        self.assertTrue(target.is_file())
        self.assertEqual(checkpoint.read_bytes(), checkpoint_bytes)
        receipt_bytes = target.read_bytes()

        validated = self.run_cli("validate")
        self.assertIn('"errors": 0', validated.stdout)
        self.assertIn("registered birth-time recovery", validated.stderr)
        environment = os.environ.copy()
        environment["PATH"] = ""
        offline = self.run_cli("validate", env=environment)
        self.assertIn('"errors": 0', offline.stdout)

        preserved = json.loads(
            self.run_cli(
                "register-checkpoint-recovery",
                "EP-001",
                "CP-001",
                "--from-git-commit",
                introducing_commit,
                "--attested-by",
                "Test Repository Owner",
                "--reason",
                "The checkpoint was introduced with the invalid seal.",
                "--apply",
            ).stdout
        )
        self.assertEqual(preserved["action"], "preserve")
        self.assertEqual(target.read_bytes(), receipt_bytes)

        plan_text = plan.read_text(encoding="utf-8")
        plan_text = plan_text.replace("- [ ]", "- [x]")
        plan_text = plan_text.replace(
            "| BLK-002 | open | 2026-07-28 |  |",
            "| BLK-002 | resolved | 2026-07-28 | 2026-09-03 |",
        )
        plan.write_text(plan_text, encoding="utf-8")
        self.replace_frontmatter(plan, "status", "active")
        archived = Path(
            self.run_cli(
                "archive-ep",
                "EP-001",
                *COMPLETION_ATTESTATION_ARGS,
            ).stdout.strip()
        )
        checkpoint = archived.parent / "history" / checkpoint.name
        self.assertTrue(checkpoint.is_file())
        archived_validation = self.run_cli("validate")
        self.assertIn('"errors": 0', archived_validation.stdout)

        receipt = json.loads(target.read_text(encoding="utf-8"))
        receipt["reason"] = "Tampered reason"
        target.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tampered_receipt = self.run_cli("validate", expected=1)
        self.assertIn("receipt_sha256 mismatch", tampered_receipt.stderr)
        self.assertIn("sealed checkpoint payload changed", tampered_receipt.stderr)
        target.write_bytes(receipt_bytes)

        checkpoint.write_bytes(checkpoint_bytes + b"\nLater change.\n")
        changed_checkpoint = self.run_cli("validate", expected=1)
        self.assertIn("checkpoint document_sha256", changed_checkpoint.stderr)
        self.assertIn("sealed checkpoint payload changed", changed_checkpoint.stderr)

    def test_register_checkpoint_recovery_rejects_later_or_unrelated_git_evidence(
        self,
    ) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)
        payload = json.loads(
            self.run_cli(
                "checkpoint",
                "EP-001",
                "--slug",
                "later-corruption",
                "--title",
                "Later corruption",
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
        self.init_git()
        original_commit = self.commit_all("introduce valid checkpoint")
        self.replace_frontmatter(checkpoint, "payload_sha256", "0" * 64)
        later_commit = self.commit_all("corrupt existing checkpoint")

        later = self.run_cli(
            "register-checkpoint-recovery",
            "EP-001",
            "CP-001",
            "--from-git-commit",
            later_commit,
            "--attested-by",
            "Test Repository Owner",
            "--reason",
            "This is not actually a birth-time defect.",
            expected=2,
        )
        self.assertIn("did not introduce checkpoint path", later.stderr)
        wrong_bytes = self.run_cli(
            "register-checkpoint-recovery",
            "EP-001",
            "CP-001",
            "--from-git-commit",
            original_commit,
            "--attested-by",
            "Test Repository Owner",
            "--reason",
            "The original bytes do not match.",
            expected=2,
        )
        self.assertIn("do not match current checkpoint bytes", wrong_bytes.stderr)

        tree = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD^{tree}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        orphan = subprocess.run(
            ["git", "-C", str(self.repo), "commit-tree", tree, "-m", "orphan"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        non_ancestor = self.run_cli(
            "register-checkpoint-recovery",
            "EP-001",
            "CP-001",
            "--from-git-commit",
            orphan,
            "--attested-by",
            "Test Repository Owner",
            "--reason",
            "An unrelated commit cannot authorize recovery.",
            expected=2,
        )
        self.assertIn("is not an ancestor of HEAD", non_ancestor.stderr)

    def test_register_checkpoint_recovery_requires_seal_mismatch_as_only_error(
        self,
    ) -> None:
        self.init()
        plan = self.new_ep()
        self.prepare_checkpoint_plan(plan)
        payload = json.loads(
            self.run_cli(
                "checkpoint",
                "EP-001",
                "--slug",
                "structurally-invalid",
                "--title",
                "Structurally invalid checkpoint",
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
        self.replace_frontmatter(checkpoint, "payload_sha256", "0" * 64)
        self.replace_frontmatter(checkpoint, "status", "open")
        self.init_git()
        introducing_commit = self.commit_all("introduce invalid checkpoint")

        result = self.run_cli(
            "register-checkpoint-recovery",
            "EP-001",
            "CP-001",
            "--from-git-commit",
            introducing_commit,
            "--attested-by",
            "Test Repository Owner",
            "--reason",
            "A receipt cannot hide structural errors.",
            expected=2,
        )

        self.assertIn("only validation error is its payload mismatch", result.stderr)
        self.assertIn("checkpoint status must be sealed", result.stderr)

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

    def test_decision_view_preview_apply_reindex_and_remove_are_safe(self) -> None:
        self.init()
        self.assertEqual(
            json.loads(
                (self.repo / "docs/.epctl/decision-views.json").read_text(
                    encoding="utf-8"
                )
            ),
            {"version": 1, "views": []},
        )
        self.assertTrue((self.repo / "docs/DECISION-VIEWS.md").is_file())
        research = self.new_research("view-source")
        self.conclude_research(research)
        adr = self.new_adr("view-source")
        self.accept_adr(adr)
        adr_bytes = adr.read_bytes()
        registry = self.repo / "docs/.epctl/decision-views.json"
        registry_before = registry.read_bytes()
        view = self.repo / "docs/decision-views/runtime.md"

        preview = json.loads(
            self.run_cli(
                "set-decision-view",
                "runtime",
                "--title",
                "Runtime decisions",
                "--adr",
                "ADR-001",
            ).stdout
        )
        self.assertFalse(preview["applied"])
        self.assertEqual(preview["resolved_adrs"], ["ADR-001"])
        self.assertEqual(registry.read_bytes(), registry_before)
        self.assertFalse(view.exists())

        applied = json.loads(
            self.run_cli(
                "set-decision-view",
                "runtime",
                "--title",
                "Runtime decisions",
                "--adr",
                "ADR-001",
                "--apply",
            ).stdout
        )
        self.assertTrue(applied["applied"])
        self.assertIn("Status: `current`", view.read_text(encoding="utf-8"))
        managed = {
            path: path.read_bytes()
            for path in (
                registry,
                self.repo / "docs/DECISION-VIEWS.md",
                view,
            )
        }
        self.run_cli(
            "set-decision-view",
            "runtime",
            "--title",
            "Runtime decisions",
            "--adr",
            "ADR-001",
            "--apply",
        )
        self.run_cli("reindex")
        self.assertEqual(
            managed,
            {path: path.read_bytes() for path in managed},
        )

        view.write_text(view.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        drift = self.run_cli("validate", expected=1)
        self.assertIn("generated Decision View drift", drift.stderr)
        self.run_cli("validate", "--fix-index")
        self.assertEqual(view.read_bytes(), managed[view])
        self.assertEqual(adr.read_bytes(), adr_bytes)

        remove_preview = json.loads(
            self.run_cli("remove-decision-view", "runtime").stdout
        )
        self.assertFalse(remove_preview["applied"])
        self.assertTrue(view.exists())
        self.run_cli("remove-decision-view", "runtime", "--apply")
        self.assertFalse(view.exists())
        self.assertEqual(adr.read_bytes(), adr_bytes)
        self.run_cli("validate")

        orphan = self.repo / "docs/decision-views/orphan.md"
        orphan.write_text("unregistered\n", encoding="utf-8")
        orphaned = self.run_cli("validate", expected=1)
        self.assertIn("unregistered Decision View projection", orphaned.stderr)
        orphan.unlink()

        registry.unlink()
        (self.repo / "docs/DECISION-VIEWS.md").unlink()
        (self.repo / "docs/decision-views/.gitkeep").unlink()
        (self.repo / "docs/decision-views").rmdir()
        missing_preview = json.loads(
            self.run_cli(
                "set-decision-view",
                "runtime",
                "--title",
                "Runtime decisions",
                "--adr",
                "ADR-001",
            ).stdout
        )
        self.assertFalse(missing_preview["applied"])
        missing_apply = self.run_cli(
            "set-decision-view",
            "runtime",
            "--title",
            "Runtime decisions",
            "--adr",
            "ADR-001",
            "--apply",
            expected=2,
        )
        self.assertIn("infrastructure is missing", missing_apply.stderr)
        self.assertFalse(registry.exists())
        self.assertFalse((self.repo / "docs/DECISION-VIEWS.md").exists())
        self.assertFalse((self.repo / "docs/decision-views").exists())

    def test_decision_view_expands_amendment_and_survives_retirement_as_review(self) -> None:
        self.init()
        research = self.new_research("view-amendment")
        self.conclude_research(research)
        base = self.new_adr("view-base")
        self.accept_adr(base)
        amendment = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "view-amendment",
                "--title",
                "View amendment",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        self.accept_adr(amendment, "ADR-002")

        applied = json.loads(
            self.run_cli(
                "set-decision-view",
                "amended",
                "--title",
                "Amended context",
                "--adr",
                "ADR-001",
                "--apply",
            ).stdout
        )
        self.assertEqual(applied["resolved_adrs"], ["ADR-001", "ADR-002"])
        view = self.repo / "docs/decision-views/amended.md"
        self.assertIn("ADR-001#C-001", view.read_text(encoding="utf-8"))

        self.run_cli(
            "transition-adr",
            "ADR-001",
            "--to",
            "retired",
            "--decision-maker",
            "Test Decision Owner",
            "--reason",
            "The source boundary no longer applies.",
            "--apply",
        )
        reviewed = view.read_text(encoding="utf-8")
        self.assertIn("Status: `review_required`", reviewed)
        validation = self.run_cli("validate")
        self.assertIn("Decision View requires owner review", validation.stderr)
        self.assertIn("status: retired", base.read_text(encoding="utf-8"))

    def test_decision_capsule_is_exact_selected_and_budgeted(self) -> None:
        self.init()
        research = self.new_research("capsule-source")
        self.conclude_research(research)
        base = self.new_adr("capsule-base")
        self.complete_all_placeholders(base)
        self.replace_section_body(
            base,
            "Decision Statement",
            "Base decision statement: preserve exact UTF-8 字节。",
        )
        base.write_text(
            base.read_text(encoding="utf-8").replace(
                "The implementation must preserve the test boundary.",
                "Base exact constraint text.",
            ),
            encoding="utf-8",
        )
        self.run_cli(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
        )
        base.write_bytes(base.read_bytes().replace(b"\n", b"\r\n"))
        amendment = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "capsule-amendment",
                "--title",
                "Capsule amendment",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        self.accept_adr(amendment, "ADR-002")
        source_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (base, amendment)}

        capsule = json.loads(
            self.run_cli(
                "decision-capsule",
                "--adr",
                "ADR-001",
                "--constraint",
                "ADR-001#C-001",
                "--json",
            ).stdout
        )
        self.assertEqual(capsule["resolved_adrs"], ["ADR-001", "ADR-002"])
        self.assertEqual(
            capsule["selected_constraints"],
            ["ADR-001#C-001", "ADR-002#C-001"],
        )
        self.assertIn(
            "Base decision statement: preserve exact UTF-8 字节。",
            capsule["context"],
        )
        self.assertIn("Base exact constraint text.", capsule["context"])
        self.assertIn(
            "## Decision Statement\r\n\r\n"
            "Base decision statement: preserve exact UTF-8 字节。\r\n",
            capsule["context"],
        )
        exact_constraint_line = next(
            line
            for line in base.read_bytes().decode("utf-8").splitlines(keepends=True)
            if "Base exact constraint text." in line
        )
        self.assertTrue(exact_constraint_line.endswith("\r\n"))
        self.assertIn(exact_constraint_line, capsule["context"])
        base_source = next(
            source for source in capsule["sources"] if source["adr_id"] == "ADR-001"
        )
        self.assertEqual(
            hashlib.sha256(base.read_bytes()).hexdigest(),
            base_source["document_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(capsule["context"].encode("utf-8")).hexdigest(),
            capsule["sha256"],
        )
        self.assertEqual(len(capsule["context"].encode("utf-8")), capsule["bytes"])

        overflow = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-001",
            "--budget-bytes",
            "1",
            expected=2,
        )
        self.assertIn("DECISION_CONTEXT_BUDGET_EXCEEDED", overflow.stderr)
        self.assertIn("ADR-001:", overflow.stderr)
        unjustified = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-001",
            "--budget-bytes",
            "32769",
            expected=2,
        )
        self.assertIn("requires --budget-reason", unjustified.stderr)
        outside = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-001",
            "--constraint",
            "ADR-999#C-001",
            expected=2,
        )
        self.assertIn("outside the resolved context", outside.stderr)
        duplicate = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-001",
            "--constraint",
            "ADR-001#C-001",
            "--constraint",
            "ADR-001#C-001",
            expected=2,
        )
        self.assertIn("duplicate", duplicate.stderr)
        self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-001",
            "--budget-bytes",
            "100000",
            "--budget-reason",
            "Reviewed integration context.",
        )
        self.assertEqual(
            source_hashes,
            {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_hashes},
        )

    def test_complete_capsule_matches_frozen_080_contract(self) -> None:
        module_name = "epctl_complete_compatibility_test"
        spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        epctl = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = epctl
        spec.loader.exec_module(epctl)

        headers = [
            "| ID | Constraint | Confirmation |\r\n",
            "|---|---|---|\r\n",
        ]
        context = {
            "direct_adrs": ["ADR-001"],
            "resolved_adrs": ["ADR-001", "ADR-002"],
            "constraint_refs": ["ADR-001#C-001", "ADR-002#C-001"],
            "amendment_targets": {"ADR-001#C-001": ["ADR-002"]},
            "sources": [
                {
                    "id": "ADR-001",
                    "title": "Base",
                    "path": "docs/adr/adr-001_base.md",
                    "text": "",
                    "data": {
                        "depends_on": "[]",
                        "amends": "[]",
                        "amends_constraints": "[]",
                    },
                    "contract": "strict-structured",
                    "document_sha256": "a" * 64,
                    "payload_sha256": "b" * 64,
                    "decision_source": (
                        "## Decision Statement\r\n\r\nBase exact.\r\n"
                    ),
                    "constraint_headers": headers,
                    "constraint_rows": [
                        {
                            "ref": "ADR-001#C-001",
                            "line": (
                                "| C-001 | Preserve base. | Verify base. |\r\n"
                            ),
                        }
                    ],
                },
                {
                    "id": "ADR-002",
                    "title": "Amender",
                    "path": "docs/adr/adr-002_amender.md",
                    "text": "",
                    "data": {
                        "depends_on": "[]",
                        "amends": '["ADR-001"]',
                        "amends_constraints": '["ADR-001#C-001"]',
                    },
                    "contract": "strict-structured",
                    "document_sha256": "c" * 64,
                    "payload_sha256": "d" * 64,
                    "decision_source": (
                        "## Decision Statement\n\nAmender exact.\n"
                    ),
                    "constraint_headers": [
                        "| ID | Constraint | Confirmation |\n",
                        "|---|---|---|\n",
                    ],
                    "constraint_rows": [
                        {
                            "ref": "ADR-002#C-001",
                            "line": (
                                "| C-001 | Preserve amendment. | "
                                "Verify amendment. |\n"
                            ),
                        }
                    ],
                },
            ],
        }

        default = epctl.compile_decision_capsule(
            context,
            ["ADR-001#C-001"],
            budget_bytes=None,
        )
        explicit = epctl.compile_decision_capsule(
            context,
            ["ADR-001#C-001"],
            budget_bytes=None,
            materialization="complete",
        )
        self.assertEqual(default, explicit)
        self.assertNotIn("focus", default)
        self.assertNotIn("validated_sources", default)
        self.assertEqual(default["bytes"], 1776)
        self.assertEqual(
            default["sha256"],
            "b4f7437d33cbae4234154abe437c7b10acf662be2ca9b93250019bc58aa51b6c",
        )
        self.assertEqual(
            hashlib.sha256(
                json.dumps(
                    default,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "95eb91ab322551c5d1e8540e8055f7a5bd94e33c3585153d9243d90c3fb3c496",
        )

    def test_focused_capsule_is_directional_exact_and_auditable(self) -> None:
        self.init()
        research = self.new_research("focused-capsule")
        self.conclude_research(research)

        origin = self.new_adr("historical-origin")
        self.complete_all_placeholders(origin)
        self.replace_section_body(
            origin,
            "Decision Statement",
            "Historical origin must stay outside the focused body.",
        )
        self.run_cli(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
        )

        def scoped_adr(
            slug: str,
            adr_id: str,
            target: str,
            decision: str,
            constraints: list[tuple[str, str]],
        ) -> Path:
            path = Path(
                self.run_cli(
                    "new-adr",
                    "--slug",
                    slug,
                    "--title",
                    slug.replace("-", " ").title(),
                    "--research",
                    "R-001",
                    "--amends",
                    target.split("#", 1)[0],
                    "--amends-constraint",
                    target,
                ).stdout.strip()
            )
            self.complete_all_placeholders(path)
            self.replace_section_body(path, "Decision Statement", decision)
            rows = [
                "| ID | Strength | Scope | Constraint | Confirmation |",
                "|---|---|---|---|---|",
                *[
                    f"| {constraint_id} | must | task boundary | {text} | "
                    f"Verify {constraint_id}. |"
                    for constraint_id, text in constraints
                ],
            ]
            self.replace_section_body(path, "Normative Constraints", "\n".join(rows))
            self.run_cli(
                "decide-adr",
                adr_id,
                "--outcome",
                "accepted",
                "--decision-maker",
                "Test Decision Owner",
            )
            return path

        base = scoped_adr(
            "focused-base",
            "ADR-002",
            "ADR-001#C-001",
            "Focused base decision preserves exact UTF-8 字节。",
            [
                ("C-001", "Selected base constraint."),
                ("C-002", "Unselected base constraint."),
            ],
        )
        base.write_bytes(base.read_bytes().replace(b"\n", b"\r\n"))
        first_amender = scoped_adr(
            "focused-amender",
            "ADR-003",
            "ADR-002#C-001",
            "First downstream amendment.",
            [
                ("C-001", "First downstream constraint."),
                ("C-002", "Second downstream constraint."),
            ],
        )
        second_amender = scoped_adr(
            "focused-recursive-amender",
            "ADR-004",
            "ADR-003#C-002",
            "Recursive downstream amendment.",
            [("C-001", "Recursive downstream constraint.")],
        )
        source_paths = (origin, base, first_amender, second_amender)
        source_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        }

        focused = json.loads(
            self.run_cli(
                "decision-capsule",
                "--adr",
                "ADR-002",
                "--constraint",
                "ADR-002#C-001",
                "--materialization",
                "focused",
                "--focus-reason",
                "Implement only the selected request boundary.",
                "--json",
            ).stdout
        )
        complete = json.loads(
            self.run_cli(
                "decision-capsule",
                "--adr",
                "ADR-002",
                "--constraint",
                "ADR-002#C-001",
                "--json",
            ).stdout
        )
        self.assertEqual(
            focused["resolved_adrs"],
            ["ADR-001", "ADR-002", "ADR-003", "ADR-004"],
        )
        self.assertEqual(focused["resolved_adrs"], complete["resolved_adrs"])
        self.assertEqual(focused["validated_sources"], complete["sources"])
        self.assertEqual(
            focused["selected_constraints"],
            [
                "ADR-002#C-001",
                "ADR-003#C-001",
                "ADR-003#C-002",
                "ADR-004#C-001",
            ],
        )
        self.assertEqual(
            focused["focus"]["materialized_adrs"],
            ["ADR-002", "ADR-003", "ADR-004"],
        )
        self.assertEqual(focused["focus"]["omitted_adrs"], ["ADR-001"])
        self.assertEqual(
            focused["focus"]["unmaterialized_relation_refs"],
            ["ADR-002 amends_constraint ADR-001#C-001"],
        )
        self.assertEqual(
            [source["adr_id"] for source in focused["sources"]],
            ["ADR-002", "ADR-003", "ADR-004"],
        )
        self.assertEqual(
            [source["adr_id"] for source in focused["validated_sources"]],
            ["ADR-001", "ADR-002", "ADR-003", "ADR-004"],
        )
        self.assertEqual(
            focused["focus"]["context_completeness"],
            "focused_partial",
        )
        self.assertIn("Materialization: `focused_partial`", focused["context"])
        self.assertIn("not a complete Architecture Input Set", focused["context"])
        self.assertNotIn(
            "Historical origin must stay outside the focused body.",
            focused["context"],
        )
        self.assertNotIn("Unselected base constraint.", focused["context"])
        self.assertIn("First downstream constraint.", focused["context"])
        self.assertIn("Second downstream constraint.", focused["context"])
        self.assertIn("Recursive downstream constraint.", focused["context"])
        exact_base_line = next(
            line
            for line in base.read_bytes().decode("utf-8").splitlines(keepends=True)
            if "Selected base constraint." in line
        )
        self.assertTrue(exact_base_line.endswith("\r\n"))
        self.assertIn(exact_base_line, focused["context"])
        self.assertEqual(
            hashlib.sha256(focused["context"].encode("utf-8")).hexdigest(),
            focused["sha256"],
        )
        closure_manifest = {
            "direct_adrs": focused["direct_adrs"],
            "resolved_adrs": focused["resolved_adrs"],
            "sources": [
                {
                    "adr_id": source["adr_id"],
                    "path": source["path"],
                    "document_sha256": source["document_sha256"],
                    "payload_sha256": source["payload_sha256"],
                }
                for source in focused["validated_sources"]
            ],
        }
        closure_bytes = json.dumps(
            closure_manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(closure_bytes).hexdigest(),
            focused["focus"]["validated_closure_sha256"],
        )
        changed_manifest = json.loads(closure_bytes)
        changed_manifest["sources"][0]["document_sha256"] = "0" * 64
        changed_digest = hashlib.sha256(
            json.dumps(
                changed_manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertNotEqual(
            changed_digest,
            focused["focus"]["validated_closure_sha256"],
        )

        missing_reason = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-002",
            "--constraint",
            "ADR-002#C-001",
            "--materialization",
            "focused",
            expected=2,
        )
        self.assertIn("requires --focus-reason", missing_reason.stderr)
        missing_constraint = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-002",
            "--materialization",
            "focused",
            "--focus-reason",
            "A reviewed focus.",
            expected=2,
        )
        self.assertIn("requires at least one --constraint", missing_constraint.stderr)
        overflow = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-002",
            "--constraint",
            "ADR-002#C-001",
            "--materialization",
            "focused",
            "--focus-reason",
            "A reviewed focus.",
            "--budget-bytes",
            "1",
            expected=2,
        )
        self.assertEqual(overflow.stdout, "")
        self.assertIn("DECISION_CONTEXT_BUDGET_EXCEEDED", overflow.stderr)
        self.assertEqual(
            source_hashes,
            {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source_paths
            },
        )

    def test_focused_capsule_fails_closed_on_broad_amendment(self) -> None:
        self.init()
        research = self.new_research("broad-amendment")
        self.conclude_research(research)
        base = self.new_adr("broad-base")
        self.accept_adr(base)
        legacy = self.repo / "docs/adr/adr-010_broad-amendment.md"
        legacy.write_text(
            """---
doc_type: adr
title: Broad amendment
status: accepted
created: 2026-01-01
last_verified: 2026-01-02
depends_on: []
amends: ["ADR-001"]
---

# ADR-010: Broad amendment

This current whole-ADR amendment has no stable row-level scope.
""",
            encoding="utf-8",
        )
        self.run_cli("reindex")
        result = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-001",
            "--constraint",
            "ADR-001#C-001",
            "--materialization",
            "focused",
            "--focus-reason",
            "Test an ambiguous boundary.",
            expected=2,
        )
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "FOCUSED_CONTEXT_AMENDMENT_SCOPE_UNPROVABLE",
            result.stderr,
        )

    def test_legacy_capsule_health_and_consolidation_are_lossless(self) -> None:
        self.init()
        legacy = self.repo / "docs/adr/adr-010_legacy-runtime.md"
        legacy_text = """---
doc_type: adr
title: Legacy runtime
status: accepted
created: 2026-01-01
last_verified: 2026-01-02
depends_on: []
amends: []
---

# ADR-010: Legacy runtime

The whole legacy document is normative, including this unique sentence.
"""
        legacy.write_text(legacy_text, encoding="utf-8")
        self.run_cli("reindex")
        before = hashlib.sha256(legacy.read_bytes()).hexdigest()

        capsule = json.loads(
            self.run_cli(
                "decision-capsule",
                "--adr",
                "ADR-010",
                "--json",
            ).stdout
        )
        self.assertEqual(capsule["sources"][0]["contract"], "whole-document")
        self.assertIn(legacy_text, capsule["context"])
        focused = self.run_cli(
            "decision-capsule",
            "--adr",
            "ADR-010",
            "--constraint",
            "ADR-010#C-001",
            "--materialization",
            "focused",
            "--focus-reason",
            "Test a legacy boundary.",
            expected=2,
        )
        self.assertEqual(focused.stdout, "")
        self.assertIn("FOCUSED_CONTEXT_LEGACY_BOUNDARY", focused.stderr)
        health = json.loads(self.run_cli("adr-health", "--json").stdout)
        self.assertEqual(health["contracts"]["whole_document_current_adrs"], 1)
        self.assertNotIn("score", json.dumps(health))

        self.run_cli(
            "set-decision-view",
            "legacy-runtime",
            "--title",
            "Legacy runtime",
            "--adr",
            "ADR-010",
            "--apply",
        )
        preview = json.loads(
            self.run_cli(
                "adr-consolidation-plan",
                "--view",
                "legacy-runtime",
                "--json",
            ).stdout
        )
        self.assertTrue(preview["preview_only"])
        self.assertEqual(preview["whole_document_legacy_adrs"], ["ADR-010"])
        self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), before)

    def test_health_and_consolidation_expose_plan_and_proposal_impact(self) -> None:
        self.init()
        research = self.new_research("consolidation-impact")
        self.conclude_research(research)
        base = self.new_adr("impact-base")
        self.accept_adr(base)
        amendment = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "impact-amendment",
                "--title",
                "Impact amendment",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        self.accept_adr(amendment, "ADR-002")
        self.run_cli(
            "new-ep",
            "--slug",
            "consume-impact",
            "--title",
            "Consume impact",
            "--research",
            "R-001",
            "--adr",
            "ADR-001",
            "--adr",
            "ADR-002",
        )
        proposed = Path(
            self.run_cli(
                "new-adr",
                "--slug",
                "proposed-overlap",
                "--title",
                "Proposed overlap",
                "--research",
                "R-001",
                "--amends",
                "ADR-001",
                "--amends-constraint",
                "ADR-001#C-001",
            ).stdout.strip()
        )
        non_current = self.run_cli(
            "set-decision-view",
            "proposed",
            "--title",
            "Proposed context",
            "--adr",
            "ADR-003",
            expected=2,
        )
        self.assertIn("accepted and current", non_current.stderr)
        self.run_cli(
            "set-decision-view",
            "impact",
            "--title",
            "Impact context",
            "--adr",
            "ADR-001",
            "--apply",
        )
        health = json.loads(self.run_cli("adr-health", "--json").stdout)
        self.assertEqual(health["corpus"]["total_adrs"], 3)
        self.assertEqual(health["corpus"]["effective_adrs"], 2)
        self.assertEqual(health["amendments"]["partially_amended_adrs"], 1)
        self.assertEqual(health["active_plans"]["max_adr_refs"], 2)
        self.assertEqual(health["views"]["covered_current_adrs"], 2)
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (base, amendment, proposed)
        }
        preview = json.loads(
            self.run_cli(
                "adr-consolidation-plan",
                "--view",
                "impact",
                "--json",
            ).stdout
        )
        self.assertTrue(preview["preview_only"])
        self.assertEqual(preview["active_plan_impact"][0]["id"], "EP-001")
        self.assertEqual(preview["proposed_overlap"][0]["id"], "ADR-003")
        self.assertEqual(
            preview["recommendation"],
            "defer_while_active_or_proposed_work_depends_on_context",
        )
        self.assertEqual(
            before,
            {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in before
            },
        )

    def test_decision_view_registry_and_symlinks_fail_closed(self) -> None:
        self.init()
        research = self.new_research("view-path-safety")
        self.conclude_research(research)
        self.accept_adr(self.new_adr("view-path-safety"))
        registry = self.repo / "docs/.epctl/decision-views.json"
        registry.write_text('{"version": 999, "views": []}\n', encoding="utf-8")
        invalid = self.run_cli("validate", expected=1)
        self.assertIn("Unsupported Decision View registry", invalid.stderr)
        registry.write_text('{"version": 1, "views": []}\n', encoding="utf-8")
        link = self.repo / "docs/decision-views/escape.md"
        link.symlink_to(self.repo / "outside.md")
        rejected = self.run_cli("validate", expected=1)
        self.assertIn("symbolic links are not supported", rejected.stderr)
        rejected_preview = self.run_cli(
            "set-decision-view",
            "escape",
            "--title",
            "Escaping view",
            "--adr",
            "ADR-001",
            expected=2,
        )
        self.assertIn("Refusing to manage symbolic link", rejected_preview.stderr)


if __name__ == "__main__":
    unittest.main()
