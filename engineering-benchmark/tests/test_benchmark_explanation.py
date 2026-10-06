"""Tests for progressive Benchmark explanation views."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "engineering-benchmark" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import benchctl

SPEC = importlib.util.spec_from_file_location(
    "explain_benchmark", SCRIPT_DIR / "explain_benchmark.py"
)
assert SPEC and SPEC.loader
EXPLAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPLAIN)


def sealed_fixture(root: Path):
    run_dir = root / "benchmarks" / "suites" / "b-001_demo" / "runs" / "br-001_candidate"
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True)
    (run_dir / "SCENARIO.md").write_text("# Scenario\n", encoding="utf-8")
    (run_dir / "RESULT.md").write_text("# Result\n", encoding="utf-8")
    (artifacts / "measurements.json").write_text('{"baseline":120,"candidate":74}\n', encoding="utf-8")
    (artifacts / "profile.txt").write_text("allocs/op 18 -> 6\n", encoding="utf-8")
    (artifacts / "source.txt").write_text("candidate reuses the buffer\n", encoding="utf-8")
    metadata = {
        "schema_version": "1.1",
        "metadata_schema": "1",
        "artifact_type": "benchmark-result",
        "id": "BR-001",
        "suite_id": "B-001",
        "scenario_id": "BS-001",
        "status": "sealed",
        "outcome": "passed",
        "title": "Synthetic candidate",
        "author": "Test Author",
        "owner": "Test Owner",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-01-01T00:10:00Z",
        "completed": "2026-01-01T00:10:00Z",
        "executed_by": "Test Runner",
        "subject_revision": "git:subject",
        "harness_revision": "git:harness",
        "supersedes": [],
        "manifest": "EVIDENCE_MANIFEST.json",
    }
    run = benchctl.Record("BR", "BR-001", run_dir / "RESULT.md", metadata)
    manifest = benchctl.build_manifest(
        run, metadata, metadata["completed"], metadata["executed_by"]
    )
    (run_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return run, manifest


def explanation(run, manifest):
    document = {
        "schema": EXPLAIN.SCHEMA,
        "authority": "none",
        "language": "en",
        "source": {
            "run_id": run.identifier,
            "suite_id": run.metadata["suite_id"],
            "scenario_id": run.metadata["scenario_id"],
            "outcome": run.metadata["outcome"],
            "subject_revision": run.metadata["subject_revision"],
            "harness_revision": run.metadata["harness_revision"],
            "manifest_payload_sha256": manifest["payload_sha256"],
        },
        "subject": {
            "title": "Synthetic latency comparison",
            "question": "Does buffer reuse reduce latency under the fixed workload?",
            "summary": "The candidate is faster in this synthetic fixture.",
        },
        "evidence": [
            {
                "id": "m1",
                "kind": "measurement",
                "label": "Latency samples",
                "path": "artifacts/measurements.json",
            },
            {
                "id": "d1",
                "kind": "diagnostic",
                "label": "Allocation profile",
                "path": "artifacts/profile.txt",
            },
            {
                "id": "s1",
                "kind": "source",
                "label": "Version-matched source excerpt",
                "path": "artifacts/source.txt",
            },
            {
                "id": "scenario",
                "kind": "scenario",
                "label": "Predeclared scenario",
                "path": "SCENARIO.md",
            },
            {
                "id": "result",
                "kind": "result",
                "label": "Sealed result",
                "path": "RESULT.md",
            },
        ],
        "claims": [
            {
                "id": "obs",
                "kind": "observation",
                "text": "The candidate latency is lower in the measured fixture.",
                "evidence_ids": ["m1"],
            },
            {
                "id": "delta",
                "kind": "derived",
                "text": "The measured median decreases by 46 ms.",
                "derivation": "120 ms - 74 ms = 46 ms",
                "evidence_ids": ["m1"],
            },
            {
                "id": "hyp",
                "kind": "hypothesis",
                "text": "Lower allocation pressure may contribute to the latency reduction.",
                "evidence_ids": ["scenario", "m1"],
            },
            {
                "id": "mechanism",
                "kind": "mechanism",
                "text": "The measured allocation reduction is consistent with buffer reuse in this revision.",
                "evidence_ids": ["m1", "d1", "s1"],
            },
        ],
        "metrics": [
            {
                "id": "latency",
                "title": "Median latency",
                "unit": "ms",
                "baseline": {
                    "label": "Baseline",
                    "value": 120,
                    "samples": 8,
                    "uncertainty": "synthetic dispersion: ±4 ms",
                    "evidence_id": "m1",
                },
                "candidate": {
                    "label": "Candidate",
                    "value": 74,
                    "samples": 8,
                    "uncertainty": "synthetic dispersion: ±3 ms",
                    "evidence_id": "m1",
                },
            }
        ],
        "mechanism_steps": [
            {
                "label": "Buffer lifecycle",
                "baseline": "allocate and copy",
                "candidate": "reuse existing buffer",
                "claim_id": "mechanism",
            }
        ],
        "limitations": [
            "Synthetic fixture only; it does not establish production causality."
        ],
    }
    document["sha256"] = EXPLAIN.sha256(EXPLAIN.canonical(document))
    return document


class BenchmarkExplanationTests(unittest.TestCase):
    def test_validates_sealed_source_and_three_evidence_chains(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            self.assertIs(EXPLAIN.validate(document, run, manifest), document)
            self.assertEqual(benchctl.verify_manifest(run), [])

    def test_mechanism_claim_requires_measurement_diagnostic_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            mechanism = next(c for c in document["claims"] if c["id"] == "mechanism")
            mechanism["evidence_ids"] = ["m1", "s1"]
            document.pop("sha256")
            with self.assertRaisesRegex(EXPLAIN.ExplanationError, "diagnostic"):
                EXPLAIN.validate(document, run, manifest)

    def test_hypothesis_stays_permitted_without_mechanism_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            document["claims"] = [c for c in document["claims"] if c["kind"] != "mechanism"]
            document["mechanism_steps"][0]["claim_id"] = "hyp"
            document.pop("sha256")
            self.assertIs(EXPLAIN.validate(document, run, manifest), document)

    def test_evidence_must_be_in_the_sealed_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            document["evidence"][0]["path"] = "artifacts/not-sealed.csv"
            document.pop("sha256")
            with self.assertRaisesRegex(EXPLAIN.ExplanationError, "not sealed"):
                EXPLAIN.validate(document, run, manifest)

    def test_source_identity_must_match_the_run(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            document["source"]["outcome"] = "failed"
            document.pop("sha256")
            with self.assertRaisesRegex(EXPLAIN.ExplanationError, "source.outcome"):
                EXPLAIN.validate(document, run, manifest)

    def test_manifest_drift_is_rejected_before_explanation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, manifest = sealed_fixture(root)
            self.assertEqual(benchctl.verify_manifest(run), [])
            (run.path.parent / "artifacts" / "profile.txt").write_text(
                "changed after seal\n", encoding="utf-8"
            )
            errors = benchctl.verify_manifest(run)
            self.assertTrue(any("drift" in error for error in errors))

    def test_html_is_offline_source_bound_and_uses_hashed_script_csp(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            page = EXPLAIN.html_page(document).decode("utf-8")
            self.assertIn("connect-src &#x27;none&#x27;", page)
            self.assertIn("script-src &#x27;sha256-", page)
            self.assertNotIn("script-src &#x27;unsafe-inline&#x27;", page)
            self.assertNotIn("fetch(", page)
            self.assertIn(document["source"]["manifest_payload_sha256"], page)
            self.assertIn("Hypothesis", page)

    def test_untrusted_text_is_inert_json_data(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            document["subject"]["summary"] = '</script><img src=x onerror=alert(1)>'
            document.pop("sha256")
            page = EXPLAIN.html_page(document).decode("utf-8")
            self.assertNotIn("<img src=x", page)
            self.assertIn("\\u003c/script>", page)

    def test_publish_stays_outside_sealed_run_and_manifest_is_last_fact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, manifest = sealed_fixture(root)
            document = explanation(run, manifest)
            files = EXPLAIN.output_files(document)
            output = root / "reading-view"
            before = {
                path.relative_to(run.path.parent).as_posix(): path.read_bytes()
                for path in run.path.parent.rglob("*")
                if path.is_file()
            }
            EXPLAIN.publish(output, files, run.path.parent)
            after = {
                path.relative_to(run.path.parent).as_posix(): path.read_bytes()
                for path in run.path.parent.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            rendered = json.loads((output / "render-manifest.json").read_text())
            self.assertEqual(
                rendered["benchmark_manifest_payload_sha256"],
                manifest["payload_sha256"],
            )
            for name, expected in rendered["files"].items():
                self.assertEqual(
                    hashlib.sha256((output / name).read_bytes()).hexdigest(), expected
                )
            with self.assertRaises(EXPLAIN.ExplanationError):
                EXPLAIN.publish(run.path.parent / "derived", files, run.path.parent)

    def test_document_digest_detects_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            run, manifest = sealed_fixture(Path(directory))
            document = explanation(run, manifest)
            modified = copy.deepcopy(document)
            modified["subject"]["summary"] = "Changed"
            with self.assertRaisesRegex(EXPLAIN.ExplanationError, "digest"):
                EXPLAIN.validate(modified, run, manifest)


if __name__ == "__main__":
    unittest.main()
