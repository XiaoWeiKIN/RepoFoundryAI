from __future__ import annotations

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
    def complete_all_placeholders(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
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
        blocked = self.run_cli("archive-ep", "EP-001", expected=2)
        self.assertIn("incomplete acceptance", blocked.stderr)
        self.assertTrue(plan.exists())

        self.complete_all_placeholders(plan)
        archived = Path(self.run_cli("archive-ep", "EP-001").stdout.strip())

        self.assertTrue(archived.exists())
        self.assertFalse(plan.exists())
        self.assertIn("status: completed", archived.read_text(encoding="utf-8"))
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
        self.assertFalse(plan.exists())

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

        archived = Path(self.run_cli("archive-ep", "EP-001").stdout.strip())

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


if __name__ == "__main__":
    unittest.main()
