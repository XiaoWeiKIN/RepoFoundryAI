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
EPCTL = (
    ROOT
    / "engineering-execution-plan"
    / "scripts"
    / "epctl.py"
)
RESEARCHCTL = ROOT / "engineering-research" / "scripts" / "researchctl.py"
BENCHCTL = ROOT / "engineering-benchmark" / "scripts" / "benchctl.py"
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
        chinese_readme = (ROOT / "README.zh-CN.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(readme.startswith("# EngineeringWorkflow\n"))
        self.assertTrue(
            chinese_readme.startswith("# EngineeringWorkflow\n")
        )
        self.assertIn(
            "[简体中文](README.zh-CN.md) | English",
            readme.splitlines()[:5],
        )
        self.assertIn(
            "简体中文 | [English](README.md)",
            chinese_readme.splitlines()[:5],
        )
        self.assertIn(
            "https://github.com/XiaoWeiKIN/EngineeringWorkflow.git",
            readme,
        )
        self.assertIn(
            "https://github.com/XiaoWeiKIN/EngineeringWorkflow.git",
            chinese_readme,
        )
        self.assertNotIn("XiaoWeiKIN/ExecutionPlan", readme)
        self.assertNotIn("XiaoWeiKIN/ExecutionPlan", chinese_readme)
        self.assertIn(
            "name: engineering-workflow",
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "name: engineering-execution-plan",
            (
                ROOT
                / "engineering-execution-plan"
                / "SKILL.md"
            ).read_text(encoding="utf-8"),
        )
        self.assertIn(
            "name: engineering-research",
            (ROOT / "engineering-research" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn(
            "name: engineering-benchmark",
            (ROOT / "engineering-benchmark" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn(
            "name: engineering-case-study",
            (ROOT / "engineering-case-study" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_codex_agents_bootstrap_template_has_reserved_line_budget(self) -> None:
        template = ROOT / "assets" / "harness-agents.md"
        line_count = len(template.read_text(encoding="utf-8").splitlines())

        self.assertLessEqual(line_count, 80)
        self.assertIn(
            "at or below 100 physical lines",
            template.read_text(encoding="utf-8"),
        )

    def test_execplan_consumes_sealed_benchmark_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.run_cli(BENCHCTL, repository, "init")
            suite = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-suite",
                    "--slug",
                    "final-acceptance",
                    "--title",
                    "Final acceptance benchmark",
                    "--owner",
                    "Performance Owner",
                ).stdout.strip()
            )
            self.complete_placeholders(suite)
            scenario = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-scenario",
                    "B-001",
                    "--slug",
                    "p95",
                    "--title",
                    "Final revision p95",
                ).stdout.strip()
            )
            self.complete_placeholders(scenario)
            result = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-run",
                    "BS-001",
                    "--slug",
                    "verified-revision",
                    "--title",
                    "Verified revision",
                    "--subject-revision",
                    "git:verified-revision",
                    "--harness-revision",
                    "git:benchmark-harness",
                ).stdout.strip()
            )
            self.complete_placeholders(result)
            artifact = result.parent / "artifacts" / "latency.json"
            artifact.write_text('{"p95_ms":91}\n', encoding="utf-8")
            manifest_path = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "seal-run",
                    "BR-001",
                    "--outcome",
                    "passed",
                    "--executed-by",
                    "Contract Test Operator",
                ).stdout.strip()
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            evidence = (
                "benchmark:BR-001@sha256:"
                + manifest["payload_sha256"]
            )

            self.run_cli(EPCTL, repository, "init")
            plan = Path(
                self.run_cli(
                    EPCTL,
                    repository,
                    "new-ep",
                    "--slug",
                    "benchmark-acceptance",
                    "--title",
                    "Benchmark acceptance",
                    "--research-not-required-reason",
                    "The accepted route is already fixed.",
                    "--architecture-not-required-reason",
                    "This plan only verifies the fixed route.",
                ).stdout.strip()
            )
            self.complete_placeholders(plan)
            mismatched = self.run_cli(
                EPCTL,
                repository,
                "archive-ep",
                "EP-001",
                "--verified-revision",
                "git:different-revision",
                "--evidence",
                evidence,
                expected=2,
            )
            self.assertIn(
                "does not match ExecPlan verified_revision",
                mismatched.stderr,
            )
            self.assertTrue(plan.is_file())
            archived = Path(
                self.run_cli(
                    EPCTL,
                    repository,
                    "archive-ep",
                    "EP-001",
                    "--verified-revision",
                    "git:verified-revision",
                    "--evidence",
                    evidence,
                ).stdout.strip()
            )
            archived_text = archived.read_text(encoding="utf-8")
            self.assertIn(evidence, archived_text)
            self.run_cli(EPCTL, repository, "validate")

            artifact.write_text('{"p95_ms":191}\n', encoding="utf-8")
            drift = self.run_cli(
                EPCTL,
                repository,
                "validate",
                expected=1,
            )
            self.assertIn(
                "Benchmark evidence inventory or digest drift",
                drift.stderr,
            )

    def test_skills_work_when_installed_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            workflow_skill = base / "engineering-workflow"
            workflow_skill.mkdir()
            for name in (
                "SKILL.md",
                "agents",
                "assets",
                "references",
                "scripts",
            ):
                source = ROOT / name
                destination = workflow_skill / name
                if source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
            shutil.copytree(
                ROOT / "engineering-execution-plan",
                workflow_skill / "engineering-execution-plan",
            )

            execution_skill = base / "engineering-execution-plan"
            shutil.copytree(
                ROOT / "engineering-execution-plan",
                execution_skill,
            )

            research_skill = base / "engineering-research"
            shutil.copytree(ROOT / "engineering-research", research_skill)
            benchmark_skill = base / "engineering-benchmark"
            shutil.copytree(ROOT / "engineering-benchmark", benchmark_skill)
            case_study_skill = base / "engineering-case-study"
            shutil.copytree(
                ROOT / "engineering-case-study",
                case_study_skill,
            )

            case_study_text = (case_study_skill / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("name: engineering-case-study", case_study_text)
            for relative in (
                "references/source-evidence.md",
                "references/article-patterns.md",
                "references/language.md",
                "references/review.md",
                "assets/case-study.zh-CN.md",
                "assets/case-study.en.md",
                "agents/openai.yaml",
            ):
                self.assertTrue((case_study_skill / relative).is_file())

            benchmark_text = (benchmark_skill / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("name: engineering-benchmark", benchmark_text)
            for relative in (
                "references/contract.md",
                "references/examples.md",
                "assets/benchmark-index.md",
                "assets/suite.md",
                "assets/scenario.md",
                "assets/result.md",
                "scripts/benchctl.py",
                "agents/openai.yaml",
            ):
                self.assertTrue((benchmark_skill / relative).is_file())

            workflow_repo = base / "workflow-repo"
            workflow_repo.mkdir()
            workflow_script = workflow_skill / "scripts" / "engineeringctl.py"
            self.run_cli(
                workflow_script,
                workflow_repo,
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            )
            self.run_cli(
                workflow_script,
                workflow_repo,
                "validate",
                "--harness",
            )

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

            benchmark_repo = base / "benchmark-repo"
            benchmark_repo.mkdir()
            benchmark_script = benchmark_skill / "scripts" / "benchctl.py"
            self.run_cli(benchmark_script, benchmark_repo, "init")
            self.run_cli(
                benchmark_script,
                benchmark_repo,
                "new-suite",
                "--slug",
                "portable-install",
                "--title",
                "Portable install",
            )
            self.run_cli(benchmark_script, benchmark_repo, "validate")

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
