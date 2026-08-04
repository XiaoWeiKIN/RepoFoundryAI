from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.spec_git_fixture import create_git_catalog


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
            self.assertIn('schema_version: "2.5"', plan_text)
            self.assertIn("required_benchmark_scenarios: []", plan_text)
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

    def test_repofoundry_ai_project_and_skill_names_are_aligned(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese_readme = (ROOT / "README.zh-CN.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(readme.startswith("# RepoFoundry AI\n"))
        self.assertTrue(
            chinese_readme.startswith("# RepoFoundry AI\n")
        )
        self.assertIn(
            "[简体中文](README.zh-CN.md) | English",
            readme.splitlines()[:5],
        )
        self.assertIn(
            "简体中文 | [English](README.md)",
            chinese_readme.splitlines()[:5],
        )
        self.assertIn("<repo-url>", readme)
        self.assertIn("<repo-url>", chinese_readme)
        self.assertNotIn(
            "https://github.com/XiaoWeiKIN/RepoFoundry.git",
            readme,
        )
        self.assertNotIn(
            "https://github.com/XiaoWeiKIN/RepoFoundry.git",
            chinese_readme,
        )
        self.assertNotIn("XiaoWeiKIN/ExecutionPlan", readme)
        self.assertNotIn("XiaoWeiKIN/ExecutionPlan", chinese_readme)
        self.assertIn(
            "The Agent-Native Engineering System",
            readme,
        )
        self.assertIn(
            "Turn any repository into an AI-ready engineering system.",
            readme,
        )
        self.assertIn(
            "The Agent-Native Engineering System",
            chinese_readme,
        )
        self.assertIn(
            "把任何代码仓库锻造成 AI Agent 可以可靠工作的工程系统。",
            chinese_readme,
        )
        for text in (readme, chinese_readme):
            self.assertIn("target-repository/", text)
            self.assertIn("benchmarks/", text)
            self.assertIn("scripts/bench/", text)
            self.assertIn(
                "./engineering-benchmark/references/contract.md",
                text,
            )
            self.assertIn(
                "./engineering-execution-plan/references/benchmark.md",
                text,
            )
        self.assertIn(
            "name: repo-foundry-ai",
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "# RepoFoundry AI",
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            'display_name: "RepoFoundry AI"',
            (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "$repo-foundry-ai",
            (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
            "0.2.0",
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

    def test_repofoundry_ai_brand_assets_are_valid(self) -> None:
        brand = ROOT / "assets" / "brand"
        for name in ("repofoundry-mark.svg", "repofoundry-icon.svg"):
            path = brand / name
            root = ET.parse(path).getroot()
            self.assertTrue(root.tag.endswith("svg"))
            self.assertEqual(root.attrib.get("viewBox"), "0 0 256 256")
            text = path.read_text(encoding="utf-8")
            self.assertIn("#17202A", text)
            self.assertIn("#FF6B2C", text)

        icon_svg = (brand / "repofoundry-icon.svg").read_text(
            encoding="utf-8"
        )
        self.assertIn("#F7F4ED", icon_svg)

        png = (brand / "repofoundry-icon.png").read_bytes()
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(png[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">II", png[16:24]), (256, 256))
        self.assertIn(png[25], (4, 6))

        guide = (brand / "README.md").read_text(encoding="utf-8")
        self.assertIn("RepoFoundry AI Brand Assets", guide)
        self.assertIn("repository braces", guide)
        self.assertIn("AI spark", guide)

    def test_prompt_catalog_covers_every_distributed_skill(self) -> None:
        skill_files = [
            ROOT / "SKILL.md",
            *sorted(ROOT.glob("engineering-*/SKILL.md")),
        ]
        skill_names: list[str] = []
        for skill_file in skill_files:
            match = re.search(
                r"(?m)^name:\s*([a-z0-9-]+)\s*$",
                skill_file.read_text(encoding="utf-8"),
            )
            self.assertIsNotNone(match, msg=str(skill_file))
            skill_names.append(match.group(1))

        self.assertGreaterEqual(len(skill_names), 5)
        catalogs = (
            ROOT / "examples" / "README.md",
            ROOT / "examples" / "README.zh-CN.md",
        )
        for catalog in catalogs:
            text = catalog.read_text(encoding="utf-8")
            self.assertNotIn("python3 ", text)
            for skill_name in skill_names:
                self.assertIn(
                    f"${skill_name}",
                    text,
                    msg=f"{catalog} does not cover {skill_name}",
                )

        self.assertIn(
            "./examples/README.md",
            (ROOT / "README.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "./examples/README.zh-CN.md",
            (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"),
        )

    def test_codex_agents_bootstrap_template_has_reserved_line_budget(self) -> None:
        template = ROOT / "assets" / "adapters" / "codex" / "AGENTS.md"
        line_count = len(template.read_text(encoding="utf-8").splitlines())

        self.assertLessEqual(line_count, 80)
        self.assertIn(
            "at or below 100 physical lines",
            template.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "docs/agent-guides/managed/index.md",
            template.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "$engineering-specs",
            template.read_text(encoding="utf-8"),
        )

        router = (
            ROOT
            / "assets"
            / "adapters"
            / "codex"
            / "engineering-specs"
        )
        router_skill = (router / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: engineering-specs", router_skill)
        self.assertIn("task Applicability", router_skill)
        self.assertTrue((router / "agents" / "openai.yaml").is_file())
        self.assertTrue((router / "scripts" / "spec_router.py").is_file())

    def test_core_and_adapter_assets_have_product_neutral_boundaries(self) -> None:
        core = ROOT / "assets" / "core"
        core_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(core.rglob("*"))
            if path.is_file() and path.suffix in {".md", ".py", ".json"}
        )
        for product_token in (
            "Codex",
            "UserPromptSubmit",
            "SubagentStart",
            "PreToolUse",
            "hookSpecificOutput",
            "permissionDecision",
            ".codex",
            ".agents",
            "openai",
        ):
            self.assertNotIn(product_token, core_text)

        codex_adapter = (
            ROOT
            / "assets"
            / "adapters"
            / "codex"
            / "engineering-specs"
            / "scripts"
            / "spec_router.py"
        ).read_text(encoding="utf-8")
        for event in (
            "UserPromptSubmit",
            "SubagentStart",
            "PreToolUse",
            "Stop",
        ):
            self.assertIn(event, codex_adapter)

        spec_manager = (ROOT / "scripts" / "spec_manager.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("AGENTS.md", spec_manager)
        self.assertNotIn(".codex/hooks.json", spec_manager)
        self.assertTrue(
            (ROOT / "assets/adapters/portable/agent-guide.md").is_file()
        )

    def test_workflow_has_no_bundled_engineering_spec_content(self) -> None:
        self.assertFalse((ROOT / "engineering-specs").exists())
        foundryctl = (
            ROOT / "scripts" / "foundryctl.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://github.com/XiaoWeiKIN/EngineeringSpecifications.git",
            foundryctl,
        )
        self.assertIn('DEFAULT_SPEC_VERSION = "1.2.0"', foundryctl)
        self.assertNotIn('DEFAULT_SPEC_REF = "main"', foundryctl)
        self.assertIn("--spec-version", foundryctl)
        self.assertIn('"upgrade"', foundryctl)
        self.assertIn("VERSION_FILE", foundryctl)
        self.assertNotIn("SPEC_CATALOG_DIR", foundryctl)

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
            second_scenario = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-scenario",
                    "B-001",
                    "--slug",
                    "throughput",
                    "--title",
                    "Final revision throughput",
                ).stdout.strip()
            )
            self.complete_placeholders(second_scenario)

            self.run_cli(EPCTL, repository, "init")
            missing_scenario = self.run_cli(
                EPCTL,
                repository,
                "new-ep",
                "--slug",
                "missing-benchmark",
                "--title",
                "Missing benchmark",
                "--research-not-required-reason",
                "The accepted route is already fixed.",
                "--architecture-not-required-reason",
                "This plan only verifies the fixed route.",
                "--benchmark-scenario",
                "BS-999",
                expected=2,
            )
            self.assertIn("expected exactly one local", missing_scenario.stderr)
            duplicate_scenario = self.run_cli(
                EPCTL,
                repository,
                "new-ep",
                "--slug",
                "duplicate-benchmark",
                "--title",
                "Duplicate benchmark",
                "--research-not-required-reason",
                "The accepted route is already fixed.",
                "--architecture-not-required-reason",
                "This plan only verifies the fixed route.",
                "--benchmark-scenario",
                "BS-001",
                "--benchmark-scenario",
                "BS-001",
                expected=2,
            )
            self.assertIn("must be unique", duplicate_scenario.stderr)
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
                    "--benchmark-scenario",
                    "BS-001",
                    "--benchmark-scenario",
                    "BS-002",
                ).stdout.strip()
            )
            plan_text = plan.read_text(encoding="utf-8")
            self.assertIn('schema_version: "2.5"', plan_text)
            self.assertIn(
                'required_benchmark_scenarios: ["BS-001", "BS-002"]',
                plan_text,
            )
            status = json.loads(
                self.run_cli(EPCTL, repository, "status", "--json").stdout
            )
            self.assertEqual(
                status["plans"][0]["benchmark_scenarios"],
                ["BS-001", "BS-002"],
            )

            first_result = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-run",
                    "BS-001",
                    "--slug",
                    "verified-latency",
                    "--title",
                    "Verified latency",
                    "--subject-revision",
                    "git:verified-revision",
                    "--harness-revision",
                    "git:benchmark-harness",
                ).stdout.strip()
            )
            self.complete_placeholders(first_result)
            first_artifact = (
                first_result.parent / "artifacts" / "latency.json"
            )
            first_artifact.write_text('{"p95_ms":91}\n', encoding="utf-8")
            first_manifest_path = Path(
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
            first_manifest = json.loads(
                first_manifest_path.read_text(encoding="utf-8")
            )
            first_evidence = (
                "benchmark:BR-001@sha256:"
                + first_manifest["payload_sha256"]
            )
            second_result = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-run",
                    "BS-002",
                    "--slug",
                    "verified-throughput",
                    "--title",
                    "Verified throughput",
                    "--subject-revision",
                    "git:verified-revision",
                    "--harness-revision",
                    "git:benchmark-harness",
                ).stdout.strip()
            )
            self.complete_placeholders(second_result)
            second_artifact = (
                second_result.parent / "artifacts" / "throughput.json"
            )
            second_artifact.write_text('{"rps":12000}\n', encoding="utf-8")
            second_manifest_path = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "seal-run",
                    "BR-002",
                    "--outcome",
                    "passed",
                    "--executed-by",
                    "Contract Test Operator",
                ).stdout.strip()
            )
            second_manifest = json.loads(
                second_manifest_path.read_text(encoding="utf-8")
            )
            second_evidence = (
                "benchmark:BR-002@sha256:"
                + second_manifest["payload_sha256"]
            )
            duplicate_result = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "new-run",
                    "BS-001",
                    "--slug",
                    "verified-latency-rerun",
                    "--title",
                    "Verified latency rerun",
                    "--subject-revision",
                    "git:verified-revision",
                    "--harness-revision",
                    "git:benchmark-harness",
                ).stdout.strip()
            )
            self.complete_placeholders(duplicate_result)
            duplicate_manifest_path = Path(
                self.run_cli(
                    BENCHCTL,
                    repository,
                    "seal-run",
                    "BR-003",
                    "--outcome",
                    "passed",
                    "--executed-by",
                    "Contract Test Operator",
                ).stdout.strip()
            )
            duplicate_manifest = json.loads(
                duplicate_manifest_path.read_text(encoding="utf-8")
            )
            duplicate_evidence = (
                "benchmark:BR-003@sha256:"
                + duplicate_manifest["payload_sha256"]
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
                first_evidence,
                "--evidence",
                second_evidence,
                expected=2,
            )
            self.assertIn(
                "does not match ExecPlan verified_revision",
                mismatched.stderr,
            )
            self.assertTrue(plan.is_file())
            incomplete_gate_set = self.run_cli(
                EPCTL,
                repository,
                "archive-ep",
                "EP-001",
                "--verified-revision",
                "git:verified-revision",
                "--evidence",
                first_evidence,
                expected=2,
            )
            self.assertIn(
                "Required Benchmark Scenario BS-002 has no valid",
                incomplete_gate_set.stderr,
            )
            self.assertTrue(plan.is_file())
            ambiguous_gate = self.run_cli(
                EPCTL,
                repository,
                "archive-ep",
                "EP-001",
                "--verified-revision",
                "git:verified-revision",
                "--evidence",
                first_evidence,
                "--evidence",
                duplicate_evidence,
                "--evidence",
                second_evidence,
                expected=2,
            )
            self.assertIn(
                "BS-001 must have exactly one accepted Run",
                ambiguous_gate.stderr,
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
                    first_evidence,
                    "--evidence",
                    second_evidence,
                ).stdout.strip()
            )
            archived_text = archived.read_text(encoding="utf-8")
            self.assertIn(first_evidence, archived_text)
            self.assertIn(second_evidence, archived_text)
            self.run_cli(EPCTL, repository, "validate")

            first_artifact.write_text('{"p95_ms":191}\n', encoding="utf-8")
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
            workflow_skill = base / "repo-foundry-ai"
            workflow_skill.mkdir()
            for name in (
                "VERSION",
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
            catalog_repository, _ = create_git_catalog(base)
            workflow_script = workflow_skill / "scripts" / "foundryctl.py"
            self.run_cli(
                workflow_script,
                workflow_repo,
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
                "--spec-repository",
                catalog_repository.resolve().as_uri(),
                "--spec-ref",
                "main",
            )
            self.run_cli(
                workflow_script,
                workflow_repo,
                "validate",
                "--harness",
            )
            self.run_cli(
                workflow_script,
                workflow_repo,
                "spec",
                "validate",
            )
            self.assertTrue(
                (
                    workflow_repo
                    / "docs"
                    / "agent-guides"
                    / "managed"
                    / "core"
                    / "semantic-naming.md"
                ).is_file()
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
