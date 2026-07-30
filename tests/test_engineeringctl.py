from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINEERINGCTL = ROOT / "scripts" / "engineeringctl.py"
EPCTL = (
    ROOT
    / "engineering-execution-plan"
    / "scripts"
    / "epctl.py"
)


class EngineeringctlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ENGINEERINGCTL),
                "--repo",
                str(self.repo),
                *arguments,
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def run_ep_cli(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(EPCTL),
                "--repo",
                str(self.repo),
                *arguments,
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def test_codex_bootstrap_dry_run_does_not_write(self) -> None:
        payload = json.loads(
            self.run_cli("bootstrap", "--profile", "codex").stdout
        )

        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(
            payload["components"],
            ["engineering-execution-plan"],
        )
        self.assertIn(
            {"action": "create_file", "path": "AGENTS.md"},
            payload["actions"],
        )
        self.assertIn(
            {"action": "register", "path": "docs/design-docs"},
            payload["actions"],
        )
        self.assertEqual(payload["created"], [])
        self.assertEqual(payload["updated"], [])
        self.assertEqual(list(self.repo.iterdir()), [])

        explicit = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--dry-run",
            ).stdout
        )
        self.assertEqual(explicit, payload)
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_codex_bootstrap_apply_is_idempotent_and_validated(self) -> None:
        first = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            ).stdout
        )

        self.assertEqual(first["mode"], "apply")
        required = (
            "AGENTS.md",
            "ARCHITECTURE.md",
            "docs/index.md",
            "docs/QUALITY_SCORE.md",
            "docs/RELIABILITY.md",
            "docs/SECURITY.md",
            "docs/design-docs/index.md",
        )
        for relative in required:
            self.assertTrue((self.repo / relative).is_file(), relative)
        agents = self.repo / "AGENTS.md"
        self.assertLessEqual(
            len(agents.read_text(encoding="utf-8").splitlines()),
            80,
        )

        manifest = json.loads(
            (
                self.repo / "docs" / ".engineering" / "harness.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["owner"], "engineering-workflow")
        self.assertEqual(manifest["profile"], "codex")
        self.assertEqual(
            manifest["instruction_files"],
            [{"path": "AGENTS.md", "max_lines": 100}],
        )
        config = json.loads(
            (
                self.repo / "docs" / ".epctl" / "config.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("docs/design-docs", config["architecture_roots"])
        self.run_cli("validate", "--harness")
        self.run_ep_cli("validate")

        before = {
            relative: (self.repo / relative).read_bytes()
            for relative in (
                *required,
                "docs/.engineering/harness.json",
                "docs/.epctl/config.json",
            )
        }
        second = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            ).stdout
        )
        after = {
            relative: (self.repo / relative).read_bytes()
            for relative in before
        }

        self.assertEqual(second["created"], [])
        self.assertEqual(second["updated"], [])
        self.assertEqual(after, before)

    def test_codex_bootstrap_preserves_existing_files_at_line_limit(
        self,
    ) -> None:
        self.run_ep_cli("init")
        plans = self.repo / "docs" / "PLANS.md"
        original_plans = (
            plans.read_text(encoding="utf-8") + "\nRepository-owned note.\n"
        )
        plans.write_text(original_plans, encoding="utf-8")
        agents = self.repo / "AGENTS.md"
        original_agents = "".join(
            f"line {number:03d}\n" for number in range(1, 101)
        )
        agents.write_text(original_agents, encoding="utf-8")
        architecture = self.repo / "ARCHITECTURE.md"
        architecture.write_text("# Human architecture\n", encoding="utf-8")

        result = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            ).stdout
        )

        self.assertEqual(agents.read_text(encoding="utf-8"), original_agents)
        self.assertEqual(
            architecture.read_text(encoding="utf-8"),
            "# Human architecture\n",
        )
        self.assertEqual(plans.read_text(encoding="utf-8"), original_plans)
        self.assertTrue(
            any(
                "hard limit is 100" in warning
                for warning in result["warnings"]
            )
        )
        self.run_cli("validate", "--harness")

    def test_codex_bootstrap_rejects_101_line_agents_without_writing(
        self,
    ) -> None:
        agents = self.repo / "AGENTS.md"
        agents.write_text(
            "".join(f"line {number:03d}\n" for number in range(1, 102)),
            encoding="utf-8",
        )

        result = self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--apply",
            expected=2,
        )

        self.assertIn("HARNESS_AGENTS_LINE_LIMIT", result.stderr)
        self.assertFalse((self.repo / "docs").exists())
        self.assertEqual(
            len(agents.read_text(encoding="utf-8").splitlines()),
            101,
        )

    def test_harness_validation_rejects_agents_growth(self) -> None:
        self.run_cli("bootstrap", "--profile", "codex", "--apply")
        agents = self.repo / "AGENTS.md"
        agents.write_text(
            "".join(f"line {number:03d}\n" for number in range(1, 102)),
            encoding="utf-8",
        )

        result = self.run_cli("validate", "--harness", expected=1)

        self.assertIn("HARNESS_AGENTS_LINE_LIMIT", result.stderr)
        self.assertIn("actual 101 physical lines", result.stderr)

    def test_harness_validation_can_require_bootstrap(self) -> None:
        self.run_ep_cli("init")

        result = self.run_cli("validate", "--harness", expected=1)

        self.assertIn("HARNESS_MANIFEST_MISSING", result.stderr)

    def test_codex_bootstrap_path_conflict_is_non_destructive(self) -> None:
        docs = self.repo / "docs"
        docs.write_text("reserved by user\n", encoding="utf-8")

        result = self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--apply",
            expected=2,
        )

        self.assertIn("parent is not a directory", result.stderr)
        self.assertEqual(
            docs.read_text(encoding="utf-8"),
            "reserved by user\n",
        )
        self.assertFalse((self.repo / "AGENTS.md").exists())

    def test_execution_plan_cli_does_not_own_harness_commands(self) -> None:
        help_result = subprocess.run(
            [sys.executable, "-B", str(EPCTL), "--help"],
            text=True,
            capture_output=True,
            timeout=30,
        )

        self.assertEqual(help_result.returncode, 0)
        self.assertNotIn("bootstrap", help_result.stdout)
        self.assertNotIn("--harness", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
