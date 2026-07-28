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
SCRIPT = SKILL_DIR / "scripts" / "researchctl.py"


def find_epctl() -> Path | None:
    configured = os.environ.get("EXECUTION_PLAN_EPCTL")
    candidates = [
        Path(configured).expanduser() if configured else None,
        SKILL_DIR.parent / "scripts" / "epctl.py",
        SKILL_DIR.parent / "execution-plan" / "scripts" / "epctl.py",
    ]
    return next(
        (candidate for candidate in candidates if candidate and candidate.is_file()),
        None,
    )


EPCTL = find_epctl()


class ResearchctlTestCase(unittest.TestCase):
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
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *arguments],
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

    def run_epctl(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        if EPCTL is None:
            self.skipTest(
                "execution-plan consumer is not installed; "
                "set EXECUTION_PLAN_EPCTL to run contract tests"
            )
        result = subprocess.run(
            [sys.executable, str(EPCTL), "--repo", str(self.repo), *arguments],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected epctl exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def new_research(
        self,
        slug: str = "sample",
        *extra: str,
    ) -> Path:
        result = self.run_cli(
            "new-research",
            "--slug",
            slug,
            "--title",
            slug.replace("-", " ").title(),
            *extra,
        )
        return Path(result.stdout.strip())

    @staticmethod
    def replace_section(path: Path, heading: str, body: str) -> None:
        text = path.read_text(encoding="utf-8")
        pattern = rf"(?ms)^## {re.escape(heading)}\s*$.*?(?=^## |\Z)"
        replacement = f"## {heading}\n\n{body.strip()}\n\n"
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count != 1:
            raise AssertionError(f"section not found: {heading}")
        path.write_text(updated, encoding="utf-8")

    @staticmethod
    def complete_placeholders(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
            "Recorded evidence.",
            text,
        )
        path.write_text(text, encoding="utf-8")

    def prepare_for_conclusion(self, research: Path) -> None:
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
                    "| RQ-001 | answered | Which contract works? | "
                    "The manifest contract works. | `notes/result.md` |",
                )
            ),
        )

    def test_init_and_managed_manifest_are_idempotent(self) -> None:
        first = json.loads(self.run_cli("init").stdout)
        self.assertIn("docs/RESEARCH.md", first["created"])
        second = json.loads(self.run_cli("init").stdout)
        self.assertEqual(second["created"], [])

        research = self.new_research("managed")
        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["mode"], "managed")
        self.assertEqual(manifest["documents"], [])
        self.assertEqual(manifest["roots"][0]["base"], "package")
        self.assertEqual(manifest["roots"][0]["path"], "notes")

    def test_managed_sync_and_drift_detection(self) -> None:
        research = self.new_research("managed-drift")
        notes = research.parent / "notes"
        (notes / "one.md").write_text("# One\n", encoding="utf-8")
        synced = json.loads(self.run_cli("sync-research", "R-001").stdout)
        self.assertEqual(synced["documents"], 1)
        self.run_cli("validate")

        (notes / "two.md").write_text("# Two\n", encoding="utf-8")
        drift = self.run_cli("validate", expected=1)
        self.assertIn("manifest drift", drift.stderr)

        self.run_cli("sync-research", "R-001")
        self.run_cli("validate")

    def test_controller_contract_paths_cannot_traverse(self) -> None:
        research = self.new_research("unsafe-controller")
        text = research.read_text(encoding="utf-8")
        research.write_text(
            text.replace(
                "manifest: RESEARCH_MANIFEST.json",
                "manifest: ../../escape.json",
            ),
            encoding="utf-8",
        )

        validated = self.run_cli("validate", expected=1)
        archived = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "cancelled",
            "--reason",
            "Unsafe fixture.",
            expected=2,
        )

        self.assertIn("manifest must be RESEARCH_MANIFEST.json", validated.stderr)
        self.assertIn("manifest must be RESEARCH_MANIFEST.json", archived.stderr)

    def test_linked_corpus_keeps_entrypoint_and_source_in_place(self) -> None:
        corpus = self.repo / "existing" / "research"
        corpus.mkdir(parents=True)
        index = corpus / "index.md"
        topic = corpus / "topic.md"
        index.write_text("# Index\n\n[Topic](./topic.md)\n", encoding="utf-8")
        topic.write_text("# Topic\n", encoding="utf-8")

        research = self.new_research(
            "linked",
            "--corpus-root",
            str(corpus),
            "--entrypoint",
            "existing/research/index.md",
        )
        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["mode"], "linked")
        self.assertEqual(len(manifest["documents"]), 2)
        entrypoints = [
            item for item in manifest["documents"] if item["role"] == "entrypoint"
        ]
        self.assertEqual(entrypoints[0]["path"], "existing/research/index.md")
        self.assertTrue(index.exists())
        self.run_cli("validate")

    def test_linked_corpus_supports_multiple_roots_and_entrypoints(self) -> None:
        first = self.repo / "research" / "request"
        second = self.repo / "research" / "storage"
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        (first / "index.md").write_text("# Request\n", encoding="utf-8")
        (first / "contract.md").write_text("# Contract\n", encoding="utf-8")
        (second / "index.md").write_text("# Storage\n", encoding="utf-8")

        research = self.new_research(
            "multi-root",
            "--corpus-root",
            "research/request",
            "--corpus-root",
            "research/storage",
            "--entrypoint",
            "research/request/index.md",
            "--entrypoint",
            "research/storage/index.md",
        )
        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(len(manifest["roots"]), 2)
        self.assertEqual(len(manifest["entrypoints"]), 2)
        self.assertEqual(len(manifest["documents"]), 3)
        self.assertEqual(
            sum(item["role"] == "entrypoint" for item in manifest["documents"]),
            2,
        )
        self.run_cli("validate")

    def test_missing_markdown_and_input_document_references_are_errors(self) -> None:
        corpus = self.repo / "corpus"
        corpus.mkdir()
        (corpus / "index.md").write_text(
            "---\n"
            "inputDocuments:\n"
            "  - corpus/missing-input.md\n"
            "---\n\n"
            "# Index\n\n[Missing](./missing-link.md)\n",
            encoding="utf-8",
        )
        self.new_research(
            "broken",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )

        result = self.run_cli("validate", expected=1)

        self.assertIn("missing Markdown target", result.stderr)
        self.assertIn("missing inputDocuments target", result.stderr)

    def test_absolute_input_document_is_a_portability_warning(self) -> None:
        corpus = self.repo / "corpus"
        corpus.mkdir()
        source = self.repo / "source.md"
        source.write_text("# Source\n", encoding="utf-8")
        (corpus / "index.md").write_text(
            "---\n"
            "inputDocuments:\n"
            f"  - {source}\n"
            "---\n\n# Index\n",
            encoding="utf-8",
        )
        self.new_research(
            "portable",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )

        result = self.run_cli("validate")

        self.assertIn("not portable", result.stderr)
        self.assertIn('"warnings": 3', result.stdout)

    def test_linked_conclusion_snapshots_and_detects_tampering(self) -> None:
        corpus = self.repo / "corpus"
        corpus.mkdir()
        source = corpus / "index.md"
        source.write_text("# Stable evidence\n", encoding="utf-8")
        research = self.new_research(
            "snapshot",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )
        self.prepare_for_conclusion(research)

        result = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "concluded",
        )
        completed = Path(result.stdout.strip())
        manifest_path = completed.parent / "RESEARCH_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        snapshot = completed.parent / manifest["documents"][0]["path"]

        self.assertEqual(manifest["status"], "sealed")
        self.assertEqual(manifest["mode"], "snapshot")
        self.assertRegex(manifest["payload_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(snapshot.is_file())
        self.assertTrue(source.is_file())
        self.run_cli("validate")

        snapshot.write_text("# Tampered\n", encoding="utf-8")
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("sealed document digest changed", tampered.stderr)

    def test_sealed_snapshot_replaced_by_symlink_is_rejected_by_both_tools(
        self,
    ) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unsupported")
        corpus = self.repo / "corpus"
        corpus.mkdir()
        source = corpus / "index.md"
        source.write_text("# Stable evidence\n", encoding="utf-8")
        research = self.new_research(
            "snapshot-symlink",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )
        self.prepare_for_conclusion(research)
        completed = Path(
            self.run_cli(
                "archive-research",
                "R-001",
                "--outcome",
                "concluded",
            ).stdout.strip()
        )
        manifest = json.loads(
            (completed.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        snapshot = completed.parent / manifest["documents"][0]["path"]
        replacement = self.repo / "replacement.md"
        replacement.write_bytes(snapshot.read_bytes())
        snapshot.unlink()
        os.symlink(replacement, snapshot)

        producer = self.run_cli("validate", expected=1)
        consumer = self.run_epctl("validate", expected=1)

        self.assertIn("symbolic link", producer.stderr)
        self.assertIn("symbolic link", consumer.stderr)

    def test_managed_conclusion_seals_in_place(self) -> None:
        research = self.new_research("managed-conclusion")
        note = research.parent / "notes" / "result.md"
        note.write_text("# Result\n", encoding="utf-8")
        self.run_cli("sync-research", "R-001")
        self.prepare_for_conclusion(research)

        completed = Path(
            self.run_cli(
                "archive-research",
                "R-001",
                "--outcome",
                "concluded",
            ).stdout.strip()
        )
        manifest = json.loads(
            (completed.parent / "RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["mode"], "managed")
        self.assertEqual(manifest["status"], "sealed")
        self.assertTrue((completed.parent / "notes" / "result.md").is_file())
        self.run_cli("validate")

    def test_outside_repository_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            result = self.run_cli(
                "new-research",
                "--slug",
                "outside",
                "--title",
                "Outside",
                "--corpus-root",
                outside,
                expected=2,
            )
            self.assertIn("escapes repository", result.stderr)

        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unsupported")
        corpus = self.repo / "corpus"
        corpus.mkdir()
        target = self.repo / "target.md"
        target.write_text("# Target\n", encoding="utf-8")
        os.symlink(target, corpus / "linked.md")
        result = self.run_cli(
            "new-research",
            "--slug",
            "symlink",
            "--title",
            "Symlink",
            "--corpus-root",
            "corpus",
            expected=2,
        )
        self.assertIn("symbolic link", result.stderr)

    def test_cancelled_research_requires_reason(self) -> None:
        research = self.new_research("cancelled")
        missing = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "cancelled",
            expected=2,
        )
        self.assertIn("requires --reason", missing.stderr)

        completed = Path(
            self.run_cli(
                "archive-research",
                "R-001",
                "--outcome",
                "cancelled",
                "--reason",
                "The premise was withdrawn.",
            ).stdout.strip()
        )
        self.assertTrue(completed.is_file())
        self.assertFalse(research.exists())
        self.run_cli("validate")

    def test_epctl_consumes_researchctl_conclusion(self) -> None:
        research = self.new_research("contract")
        note = research.parent / "notes" / "result.md"
        note.write_text("# Result\n", encoding="utf-8")
        self.run_cli("sync-research", "R-001")
        self.prepare_for_conclusion(research)
        completed = Path(
            self.run_cli(
                "archive-research",
                "R-001",
                "--outcome",
                "concluded",
            ).stdout.strip()
        )

        adr = Path(
            self.run_epctl(
                "new-adr",
                "--slug",
                "contract-choice",
                "--title",
                "Contract choice",
                "--research",
                "R-001",
            ).stdout.strip()
        )
        self.complete_placeholders(adr)
        self.run_epctl(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
        )
        plan = Path(
            self.run_epctl(
                "new-ep",
                "--slug",
                "implement-contract",
                "--title",
                "Implement contract",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )

        self.assertTrue(adr.is_file())
        self.assertTrue(plan.is_file())

        manifest_path = completed.parent / "RESEARCH_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["documents"][0]["bytes"] += 1
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tampered = self.run_epctl("validate", expected=1)
        self.assertIn("sealed Research manifest payload changed", tampered.stderr)

    def test_epctl_rejects_unsealed_manifest_for_concluded_research(self) -> None:
        research = self.new_research("unsealed-contract")
        note = research.parent / "notes" / "result.md"
        note.write_text("# Result\n", encoding="utf-8")
        self.run_cli("sync-research", "R-001")
        self.prepare_for_conclusion(research)
        completed = Path(
            self.run_cli(
                "archive-research",
                "R-001",
                "--outcome",
                "concluded",
            ).stdout.strip()
        )
        manifest_path = completed.parent / "RESEARCH_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "active"
        manifest["payload_sha256"] = ""
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        rejected = self.run_epctl(
            "new-adr",
            "--slug",
            "unsealed-choice",
            "--title",
            "Unsealed choice",
            "--research",
            "R-001",
            expected=2,
        )

        self.assertIn("must be valid and concluded", rejected.stderr)

    def test_researchctl_accepts_legacy_package_without_manifest(self) -> None:
        legacy = self.run_epctl(
            "new-research",
            "--slug",
            "legacy",
            "--title",
            "Legacy research",
        )

        self.assertTrue(Path(legacy.stdout.strip()).is_file())
        validated = self.run_cli("validate")
        self.assertNotIn("Missing Research manifest", validated.stderr)


if __name__ == "__main__":
    unittest.main()
