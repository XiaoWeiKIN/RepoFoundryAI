from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPCTL = ROOT / "scripts" / "epctl.py"
RESEARCHCTL = ROOT / "engineering-research" / "scripts" / "researchctl.py"
EXAMPLE = ROOT / "examples" / "cache-topology"


class RepositoryContractTestCase(unittest.TestCase):
    def run_cli(
        self,
        script: Path,
        repository: Path,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(script),
                "--repo",
                str(repository),
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

    @staticmethod
    def complete_placeholders(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
            "Recorded contract-test evidence.",
            text,
        )
        text = re.sub(r"(?m)^-\s+\[ \]", "- [x]", text)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def replace_section(path: Path, heading: str, body: str) -> None:
        text = path.read_text(encoding="utf-8")
        pattern = rf"(?ms)^## {re.escape(heading)}\s*$.*?(?=^## |\Z)"
        replacement = f"## {heading}\n\n{body.strip()}\n\n"
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count != 1:
            raise AssertionError(f"section not found: {heading}")
        path.write_text(updated, encoding="utf-8")

    def test_cache_topology_example_is_an_executable_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            corpus = repository / "research-input" / "cache-topology"
            shutil.copytree(EXAMPLE / "corpus", corpus)
            self.run_cli(RESEARCHCTL, repository, "init")
            self.run_cli(EPCTL, repository, "init")
            research = Path(
                self.run_cli(
                    RESEARCHCTL,
                    repository,
                    "new-research",
                    "--slug",
                    "cache-topology",
                    "--title",
                    "Research tenant settings cache topology",
                    "--owner",
                    "Cache Platform Owner",
                    "--author",
                    "Example Researcher",
                    "--corpus-root",
                    "research-input/cache-topology",
                    "--entrypoint",
                    "research-input/cache-topology/index.md",
                ).stdout.strip()
            )
            active_manifest = json.loads(
                (research.parent / "RESEARCH_MANIFEST.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(active_manifest["documents"]), 5)
            self.assertEqual(
                sum(
                    item["role"] == "entrypoint"
                    for item in active_manifest["documents"]
                ),
                1,
            )
            for document in active_manifest["documents"]:
                source = (
                    repository
                    if document["base"] == "repo"
                    else research.parent
                ) / document["path"]
                self.assertEqual(document["bytes"], source.stat().st_size)

            synthesis = research.parent / "SYNTHESIS.md"
            self.complete_placeholders(research)
            self.complete_placeholders(synthesis)
            self.replace_section(
                research,
                "Research Questions",
                "\n".join(
                    (
                        "| ID | Status | Question | Answer or disposition | Evidence |",
                        "|---|---|---|---|---|",
                        "| RQ-001 | answered | What dominates latency? | "
                        "Database reads dominate. | `research-input/cache-topology/current-state.md` |",
                        "| RQ-002 | answered | Which topology meets the targets? | "
                        "L1 plus Redis. | `research-input/cache-topology/benchmark.md` |",
                        "| RQ-003 | answered | Which constraints enter the ADR? | "
                        "Tenant-safe keys and independent kill switches. | "
                        "`research-input/cache-topology/options.md` |",
                    )
                ),
            )
            self.run_cli(RESEARCHCTL, repository, "sync-research", "R-001")
            self.run_cli(
                RESEARCHCTL,
                repository,
                "mark-review-ready",
                "R-001",
            )
            completed_research = Path(
                self.run_cli(
                    RESEARCHCTL,
                    repository,
                    "conclude-research",
                    "R-001",
                    "--approved-by",
                    "Cache Platform Owner",
                    "--approval-ref",
                    "example:explicit-owner-approval",
                ).stdout.strip()
            )
            sealed_manifest = json.loads(
                (
                    completed_research.parent / "RESEARCH_MANIFEST.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(sealed_manifest["status"], "sealed")
            self.assertEqual(sealed_manifest["mode"], "snapshot")
            self.assertEqual(len(sealed_manifest["documents"]), 6)
            self.assertTrue(
                (
                    completed_research.parent
                    / "snapshots"
                    / "synthesis-v001.md"
                ).is_file()
            )

            adr = Path(
                self.run_cli(
                    EPCTL,
                    repository,
                    "new-adr",
                    "--slug",
                    "cache-topology",
                    "--title",
                    "Choose tenant settings cache topology",
                    "--research",
                    "R-001",
                ).stdout.strip()
            )
            self.complete_placeholders(adr)
            self.run_cli(
                EPCTL,
                repository,
                "decide-adr",
                "ADR-001",
                "--outcome",
                "accepted",
                "--decision-maker",
                "Contract Test Decision Owner",
            )
            plan = Path(
                self.run_cli(
                    EPCTL,
                    repository,
                    "new-ep",
                    "--slug",
                    "implement-cache-topology",
                    "--title",
                    "Implement tenant settings cache topology",
                    "--research",
                    "R-001",
                    "--adr",
                    "ADR-001",
                ).stdout.strip()
            )
            plan_text = plan.read_text(encoding="utf-8")
            self.assertIn('schema_version: "2.4"', plan_text)
            self.assertIn("research_gate: satisfied", plan_text)
            self.assertIn("architecture_gate: satisfied", plan_text)
            self.complete_placeholders(plan)
            archived_plan = Path(
                self.run_cli(
                    EPCTL,
                    repository,
                    "archive-ep",
                    "EP-001",
                    "--verified-revision",
                    "test:cache-topology-revision",
                    "--evidence",
                    "test:cache-topology-contract",
                ).stdout.strip()
            )
            archived_text = archived_plan.read_text(encoding="utf-8")
            self.assertIn(
                'verified_revision: "test:cache-topology-revision"',
                archived_text,
            )
            self.assertIn(
                'verification_evidence: ["test:cache-topology-contract"]',
                archived_text,
            )
            self.assertRegex(
                archived_text,
                r"(?m)^archive_sha256: [0-9a-f]{64}$",
            )
            self.run_cli(RESEARCHCTL, repository, "validate")
            self.run_cli(EPCTL, repository, "validate")

    def test_project_brand_and_skill_names_are_independent(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# EngineeringPlan\n"))
        self.assertIn(
            "https://github.com/XiaoWeiKIN/EngineeringPlan.git",
            readme,
        )
        self.assertNotIn("XiaoWeiKIN/ExecutionPlan", readme)
        self.assertIn(
            "name: execution-plan",
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "name: engineering-research",
            (ROOT / "engineering-research" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_skills_work_when_installed_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            execution_skill = base / "execution-plan"
            execution_skill.mkdir()
            for name in ("SKILL.md", "agents", "assets", "references", "scripts"):
                source = ROOT / name
                destination = execution_skill / name
                if source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)

            research_skill = base / "engineering-research"
            shutil.copytree(ROOT / "engineering-research", research_skill)

            execution_repo = base / "execution-repo"
            execution_repo.mkdir()
            execution_script = execution_skill / "scripts" / "epctl.py"
            self.run_cli(execution_script, execution_repo, "init")
            self.run_cli(
                execution_script,
                execution_repo,
                "new-ep",
                "--slug",
                "portable-install",
                "--title",
                "Portable install",
                "--research-not-required-reason",
                "The fixture has fixed inputs.",
                "--architecture-not-required-reason",
                "The fixture introduces no durable choice.",
            )
            self.run_cli(execution_script, execution_repo, "validate")

            research_repo = base / "research-repo"
            research_repo.mkdir()
            research_script = research_skill / "scripts" / "researchctl.py"
            self.run_cli(research_script, research_repo, "init")
            research = Path(
                self.run_cli(
                    research_script,
                    research_repo,
                    "new-research",
                    "--slug",
                    "portable-install",
                    "--title",
                    "Portable install",
                ).stdout.strip()
            )
            topic = Path(
                self.run_cli(
                    research_script,
                    research_repo,
                    "new-topic",
                    "R-001",
                    "--slug",
                    "portable-topic",
                    "--title",
                    "Portable topic",
                    "--question",
                    "RQ-001",
                ).stdout.strip()
            )
            self.assertEqual(topic.parent, research.parent / "notes")
            self.run_cli(
                research_script,
                research_repo,
                "validate",
            )

    def test_ci_adapters_only_call_the_canonical_check(self) -> None:
        github = (ROOT / ".github" / "workflows" / "integrity.yml").read_text(
            encoding="utf-8"
        )
        gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
        command = "python3 -B scripts/check.py"
        self.assertIn(command, github)
        self.assertIn(command, gitlab)
        self.assertNotIn("unittest discover", github)
        self.assertNotIn("unittest discover", gitlab)

    def test_example_does_not_copy_generated_manifest_sizes(self) -> None:
        readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
        self.assertNotRegex(readme, r'"bytes"\s*:\s*\d+')


if __name__ == "__main__":
    unittest.main()
