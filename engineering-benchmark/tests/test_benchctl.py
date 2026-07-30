from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCHCTL = ROOT / "engineering-benchmark" / "scripts" / "benchctl.py"


class BenchctlTestCase(unittest.TestCase):
    def run_cli(
        self,
        repository: Path,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(BENCHCTL),
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
    def complete_document(path: Path, statement: str = "Recorded test evidence.") -> None:
        text = path.read_text(encoding="utf-8")
        text, count = re.subn(
            r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
            statement,
            text,
        )
        if count == 0:
            raise AssertionError(f"no REQUIRED markers found in {path}")
        path.write_text(text, encoding="utf-8")

    def create_scenario(
        self,
        repository: Path,
    ) -> tuple[Path, Path]:
        self.run_cli(repository, "init")
        suite = Path(
            self.run_cli(
                repository,
                "new-suite",
                "--slug",
                "placement",
                "--title",
                "Placement benchmark",
                "--owner",
                "Performance Owner",
            ).stdout.strip()
        )
        self.complete_document(suite)
        scenario = Path(
            self.run_cli(
                repository,
                "new-scenario",
                "B-001",
                "--slug",
                "order-key",
                "--title",
                "Order-key comparison",
            ).stdout.strip()
        )
        self.complete_document(scenario)
        return suite, scenario

    def create_run(
        self,
        repository: Path,
        *,
        slug: str = "baseline",
        title: str = "Baseline run",
        supersedes: str | None = None,
    ) -> Path:
        arguments = [
            "new-run",
            "BS-001",
            "--slug",
            slug,
            "--title",
            title,
            "--subject-revision",
            f"git:subject-{slug}",
            "--harness-revision",
            "git:harness-abc",
        ]
        if supersedes:
            arguments.extend(("--supersedes", supersedes))
        return Path(self.run_cli(repository, *arguments).stdout.strip())

    def test_complete_lifecycle_seals_native_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            _, scenario = self.create_scenario(repository)
            scenario_at_creation = scenario.read_bytes()
            result = self.create_run(repository)
            snapshot = result.parent / "SCENARIO.md"
            self.assertEqual(snapshot.read_bytes(), scenario_at_creation)

            self.complete_document(
                result,
                "Executed as declared; measurements and boundaries recorded.",
            )
            artifacts = result.parent / "artifacts"
            (artifacts / "latency.csv").write_text(
                "sample,p95_ms\n1,91.2\n2,93.0\n",
                encoding="utf-8",
            )
            (artifacts / "summary.json").write_text(
                '{"requests":20000,"errors":0}\n',
                encoding="utf-8",
            )
            (artifacts / "trace.bin").write_bytes(b"\x00trace-native-format\xff")

            manifest_path = Path(
                self.run_cli(
                    repository,
                    "seal-run",
                    "BR-001",
                    "--outcome",
                    "passed",
                    "--executed-by",
                    "Benchmark Operator",
                ).stdout.strip()
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "sealed")
            self.assertEqual(manifest["outcome"], "passed")
            self.assertEqual(manifest["run_id"], "BR-001")
            self.assertRegex(manifest["payload_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                [item["path"] for item in manifest["files"]],
                [
                    "RESULT.md",
                    "SCENARIO.md",
                    "artifacts/latency.csv",
                    "artifacts/summary.json",
                    "artifacts/trace.bin",
                ],
            )
            trace = next(
                item
                for item in manifest["files"]
                if item["path"] == "artifacts/trace.bin"
            )
            self.assertEqual(
                trace["sha256"],
                hashlib.sha256(b"\x00trace-native-format\xff").hexdigest(),
            )
            sealed_result = result.read_text(encoding="utf-8")
            self.assertIn('status: "sealed"', sealed_result)
            self.assertIn('outcome: "passed"', sealed_result)
            evidence = self.run_cli(
                repository,
                "evidence-ref",
                "BR-001",
            ).stdout.strip()
            self.assertEqual(
                evidence,
                "benchmark:BR-001@sha256:"
                + manifest["payload_sha256"],
            )
            self.run_cli(repository, "validate")
            status = self.run_cli(repository, "status").stdout
            self.assertIn("Runs: 1 (0 draft, 1 sealed)", status)
            self.assertIn("passed=1", status)

    def test_run_requires_predeclared_scenario_and_complete_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.run_cli(repository, "init")
            suite = Path(
                self.run_cli(
                    repository,
                    "new-suite",
                    "--slug",
                    "incomplete",
                    "--title",
                    "Incomplete suite",
                    "--owner",
                    "Performance Owner",
                ).stdout.strip()
            )
            self.complete_document(suite)
            self.run_cli(
                repository,
                "new-scenario",
                "B-001",
                "--slug",
                "incomplete",
                "--title",
                "Incomplete scenario",
            )
            rejected = self.run_cli(
                repository,
                "new-run",
                "BS-001",
                "--slug",
                "must-fail",
                "--title",
                "Must fail",
                "--subject-revision",
                "git:subject",
                "--harness-revision",
                "git:harness",
                expected=2,
            )
            self.assertIn("unresolved REQUIRED marker", rejected.stderr)

            scenario = next(
                (repository / "benchmarks" / "suites").glob(
                    "*/scenarios/bs-001_*.md"
                )
            )
            self.complete_document(scenario)
            result = self.create_run(repository)
            rejected_seal = self.run_cli(
                repository,
                "seal-run",
                "BR-001",
                "--outcome",
                "passed",
                "--executed-by",
                "Operator",
                expected=2,
            )
            self.assertIn("unresolved REQUIRED marker", rejected_seal.stderr)
            self.assertIn('status: "draft"', result.read_text(encoding="utf-8"))
            self.assertFalse(
                (result.parent / "EVIDENCE_MANIFEST.json").exists()
            )

    def test_scenario_requires_an_accountable_suite_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.run_cli(repository, "init")
            suite = Path(
                self.run_cli(
                    repository,
                    "new-suite",
                    "--slug",
                    "unowned",
                    "--title",
                    "Unowned suite",
                ).stdout.strip()
            )
            self.complete_document(suite)
            rejected = self.run_cli(
                repository,
                "new-scenario",
                "B-001",
                "--slug",
                "must-wait",
                "--title",
                "Must wait for an owner",
                expected=2,
            )
            self.assertIn("requires an accountable owner", rejected.stderr)

    def test_scenario_snapshot_does_not_drift_with_reusable_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            _, scenario = self.create_scenario(repository)
            result = self.create_run(repository)
            snapshot = result.parent / "SCENARIO.md"
            before = snapshot.read_bytes()
            scenario.write_text(
                scenario.read_text(encoding="utf-8")
                + "\nFuture-run clarification.\n",
                encoding="utf-8",
            )
            self.assertEqual(snapshot.read_bytes(), before)
            self.run_cli(repository, "validate")

    def test_sealed_bundle_detects_changed_and_added_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.create_scenario(repository)
            result = self.create_run(repository)
            self.complete_document(result)
            artifact = result.parent / "artifacts" / "measurements.json"
            artifact.write_text('{"p95":91}\n', encoding="utf-8")
            self.run_cli(
                repository,
                "seal-run",
                "BR-001",
                "--outcome",
                "passed",
                "--executed-by",
                "Operator",
            )

            artifact.write_text('{"p95":191}\n', encoding="utf-8")
            changed = self.run_cli(repository, "validate", expected=1)
            self.assertIn("evidence inventory or file digest drift", changed.stderr)

            artifact.write_text('{"p95":91}\n', encoding="utf-8")
            added = result.parent / "artifacts" / "late.log"
            added.write_text("added after seal\n", encoding="utf-8")
            changed = self.run_cli(repository, "validate", expected=1)
            self.assertIn("evidence inventory or file digest drift", changed.stderr)

    def test_symlinked_artifact_cannot_be_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.create_scenario(repository)
            result = self.create_run(repository)
            self.complete_document(result)
            source = repository / "outside.log"
            source.write_text("outside bundle\n", encoding="utf-8")
            link = result.parent / "artifacts" / "outside.log"
            try:
                link.symlink_to(source)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            rejected = self.run_cli(
                repository,
                "seal-run",
                "BR-001",
                "--outcome",
                "passed",
                "--executed-by",
                "Operator",
                expected=2,
            )
            self.assertIn("symlinked artifacts are not allowed", rejected.stderr)
            self.assertFalse(
                (result.parent / "EVIDENCE_MANIFEST.json").exists()
            )

    def test_errored_run_is_preserved_and_superseded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            suite, _ = self.create_scenario(repository)
            first = self.create_run(repository, slug="harness-crash")
            self.complete_document(first, "Harness failed; partial evidence retained.")
            first_manifest = Path(
                self.run_cli(
                    repository,
                    "seal-run",
                    "BR-001",
                    "--outcome",
                    "errored",
                    "--executed-by",
                    "Operator",
                ).stdout.strip()
            )
            first_manifest_bytes = first_manifest.read_bytes()

            second = self.create_run(
                repository,
                slug="harness-fixed",
                title="Fixed harness run",
                supersedes="BR-001",
            )
            self.complete_document(second, "Harness completed and rule passed.")
            self.run_cli(
                repository,
                "seal-run",
                "BR-002",
                "--outcome",
                "passed",
                "--executed-by",
                "Operator",
            )
            self.assertEqual(first_manifest.read_bytes(), first_manifest_bytes)
            self.assertIn(
                'supersedes: ["BR-001"]',
                second.read_text(encoding="utf-8"),
            )

            other_scenario = Path(
                self.run_cli(
                    repository,
                    "new-scenario",
                    "B-001",
                    "--slug",
                    "different-protocol",
                    "--title",
                    "Different protocol",
                ).stdout.strip()
            )
            self.complete_document(other_scenario)
            cross_protocol = self.run_cli(
                repository,
                "new-run",
                "BS-002",
                "--slug",
                "invalid-supersession",
                "--title",
                "Invalid supersession",
                "--subject-revision",
                "git:subject",
                "--harness-revision",
                "git:harness",
                "--supersedes",
                "BR-001",
                expected=2,
            )
            self.assertIn("different Scenario", cross_protocol.stderr)
            self.assertTrue(suite.is_file())
            self.run_cli(repository, "validate")

    def test_init_is_idempotent_and_index_is_rebuildable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.run_cli(repository, "init")
            self.run_cli(repository, "init")
            first = Path(
                self.run_cli(
                    repository,
                    "new-suite",
                    "--slug",
                    "first",
                    "--title",
                    "First suite",
                ).stdout.strip()
            )
            self.run_cli(repository, "init")
            second = Path(
                self.run_cli(
                    repository,
                    "new-suite",
                    "--slug",
                    "second",
                    "--title",
                    "Second suite",
                ).stdout.strip()
            )
            self.assertIn("b-001_first", first.as_posix())
            self.assertIn("b-002_second", second.as_posix())
            state = json.loads(
                (
                    repository
                    / "benchmarks"
                    / ".benchctl"
                    / "state.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(state["high_water"]["B"], 2)

            index = repository / "benchmarks" / "BENCHMARKS.md"
            index.write_text("# stale\n", encoding="utf-8")
            stale = self.run_cli(repository, "validate", expected=1)
            self.assertIn("generated index is stale", stale.stderr)
            self.run_cli(repository, "reindex")
            self.run_cli(repository, "validate")
            rebuilt = index.read_text(encoding="utf-8")
            self.assertIn("A Suite (`B-NNN`)", rebuilt)
            self.assertIn("flowchart LR", rebuilt)
            self.assertIn("[B-001]", rebuilt)
            self.assertIn("[B-002]", rebuilt)


if __name__ == "__main__":
    unittest.main()
