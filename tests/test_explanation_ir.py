"""Deterministic explanation projections and safe, optional rendering exports."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import explanation_ir as model
import explain


def preview_fixture():
    """Explicit synthetic test data, not a repository observation."""
    sources = {"metadata": {}, "specs": [{"path": "test-only/go.md", "sha256": "a" * 64, "bytes": 200}]}
    text = "# Synthetic test capsule\n\n保留条件。Names MUST expose behavior.\n"
    return {"kind": "read-only-preview", "authority": "none", "receipt_created": False,
        "paths": ["test-only/main.go"], "direct": ["GO-NAME-001"], "whole_specs": [],
        "specs": [{"id": "languages/go"}],
        "resolved": [
            {"id": "SEM-NAME-001", "spec_id": "core/semantic-naming", "source": "context_dependency", "context_dependencies": []},
            {"id": "GO-NAME-001", "spec_id": "languages/go", "source": "direct", "context_dependencies": ["SEM-NAME-001"]}],
        "edges": [{"from": "GO-NAME-001", "to": "SEM-NAME-001"}],
        "capsule": {"text": text, "mode": "requirements", "bytes": len(text.encode()),
                    "budget_bytes": 32768, "sha256": model.sha256(text.encode())},
        "provenance": {"checked_at": "Synthetic fixture; not a live source check", "git": {"head": None, "dirty": None},
            "sources": sources, "source_set_sha256": model.sha256(json.dumps(sources, ensure_ascii=False, sort_keys=True).encode()),
            "catalog": {"id": "test-only", "version": "0.1.0", "revision": "synthetic"}}}


class IRTests(unittest.TestCase):
    def test_reproducible_projection_keeps_exact_source_and_capsule(self):
        source = preview_fixture()
        before = copy.deepcopy(source)
        ir = model.from_preview(source)
        self.assertEqual(ir, model.from_preview(source))
        self.assertEqual(ir["source"]["snapshot"], before)
        self.assertEqual(source, before)
        self.assertIs(model.validate(ir), ir)
        self.assertEqual(ir["authority"], "none")
        self.assertEqual(ir["timeline"]["duration_frames"], 1080)
        for s in ir["statements"]:
            for ref in s["refs"]:
                model.pointer(source, ref)

    def test_modified_claims_limits_timing_or_hash_are_rejected(self):
        ir = model.from_preview(preview_fixture())
        for mutate in [lambda v: v["statements"].pop(), lambda v: v.update(authority="approved"),
                       lambda v: v["scenes"][0].update(duration_frames=1),
                       lambda v: v["statements"][0].update(text="Measured performance improved."),
                       lambda v: v.update(sha256="a" * 64)]:
            value = copy.deepcopy(ir)
            mutate(value)
            with self.assertRaises(model.IRError):
                model.validate(value)

    def test_rejects_unsupported_schema_and_duplicate_keys_and_nonfinite(self):
        for raw in [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff']:
            with self.subTest(raw=raw), self.assertRaises(model.IRError):
                model.parse(raw)
        with self.assertRaises(model.IRError):
            model.validate({"schema": "repofoundry.explanation/v2"})
        with self.assertRaises(model.IRError):
            model.parse(b" " * (model.MAX_BYTES + 1))

    def test_digest_byte_and_budget_failures_are_not_truncated(self):
        for key, value in [("sha256", "a" * 64), ("bytes", 1), ("budget_bytes", 1), ("bytes", True)]:
            p = preview_fixture()
            p["capsule"][key] = value
            with self.subTest(key=key), self.assertRaises(model.IRError):
                model.from_preview(p)
        p = preview_fixture()
        p["provenance"]["sources"]["specs"][0]["bytes"] = 201
        with self.assertRaisesRegex(model.IRError, "Source-set"):
            model.from_preview(p)

    def test_graph_closure_edges_and_cycles_are_checked(self):
        cases = []
        p = preview_fixture(); p["edges"] = []; cases.append(p)
        p = preview_fixture(); p["resolved"][0]["source"] = "direct"; cases.append(p)
        p = preview_fixture(); p["resolved"][1]["context_dependencies"] = ["MISSING"]; cases.append(p)
        p = preview_fixture(); p["resolved"][0]["context_dependencies"] = ["GO-NAME-001"]
        p["edges"].append({"from": "SEM-NAME-001", "to": "GO-NAME-001"}); cases.append(p)
        p = preview_fixture(); p["resolved"].append({"id": "UNREACHABLE", "source": "context_dependency", "context_dependencies": []}); cases.append(p)
        for p in cases:
            with self.assertRaises(model.IRError):
                model.from_preview(p)

    def test_empty_and_legacy_selections_do_not_claim_activation(self):
        p = preview_fixture()
        p.update(direct=[], resolved=[], edges=[], capsule=None)
        ir = model.from_preview(p)
        self.assertIn("not a formal", ir["statements"][4]["text"])
        self.assertIn(b"No Requirement dependency graph", explain.mermaid(ir))
        p["whole_specs"] = ["languages/typescript", "core/semantic-naming"]
        p["capsule"] = preview_fixture()["capsule"]
        ir = model.from_preview(p)
        self.assertIn("2 Specs", ir["statements"][2]["text"])
        self.assertEqual(ir["graph"]["nodes"], [])

    def test_input_shape_and_missing_evidence_are_rejected(self):
        for p in [[], {}, {"kind": "read-only-preview", "authority": "none", "receipt_created": False},
                  {**preview_fixture(), "receipt_created": True}]:
            with self.assertRaises(model.IRError):
                model.from_preview(p)
        with self.assertRaises(model.IRError):
            model.pointer(preview_fixture(), "/missing")


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.ir = model.from_preview(preview_fixture())

    def test_every_backend_retains_identical_ir_and_output_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "p5-test.js"
            runtime.write_text("/* Packaging fixture only; not a p5 runtime. */\n")
            for kind in explain.FORMATS:
                files = explain.render_files(self.ir, kind, runtime if kind == "p5" else None)
                self.assertEqual(model.parse(files["explanation.json"]), self.ir)
                manifest = model.parse(files["render-manifest.json"])
                self.assertEqual(manifest["ir_sha256"], self.ir["sha256"])
                for name, expected in manifest["files"].items():
                    self.assertEqual(model.sha256(files[name]), expected)
                self.assertIn(b"No activation", files["README.txt"])
                if kind == "remotion":
                    self.assertIn(b"No dependencies are installed and no MP4", files["README.txt"])
                    self.assertNotIn("package.json", files)

    def test_html_data_is_inert_and_csp_matches_actual_module(self):
        p = preview_fixture()
        p["paths"] = ['</script><img id="injected" onerror="alert(1)">@@CSP@@']
        ir = model.from_preview(p)
        page = explain.story_html(ir).decode()
        self.assertNotIn('<img id="injected"', page)
        self.assertIn('\\u003c/script>', page)
        self.assertNotIn("innerHTML", page)
        self.assertIn("connect-src &#x27;none&#x27;", page)
        script = page.split('<script type="module">')[1].split('</script>')[0]
        import base64
        expected = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn(expected, page)

    def test_mermaid_labels_cannot_inject_directives(self):
        p = preview_fixture()
        name = '\"]\nclick N0 "https://bad.invalid"\n%%{init:{}}%%'
        p["direct"] = [name]
        p["resolved"][1]["id"] = name
        p["edges"][0]["from"] = name
        text = explain.mermaid(model.from_preview(p)).decode()
        self.assertNotIn('\nclick ', text)
        self.assertNotIn('%%{init:', text)
        self.assertIn('#34;', text)

    def test_optional_p5_is_explicit_and_does_not_install_or_fetch(self):
        with self.assertRaisesRegex(model.IRError, "No CDN"):
            explain.render_files(self.ir, "p5")
        with self.assertRaises(model.IRError):
            explain.render_files(self.ir, "html", Path("/unread"))
        for goal in ("overview", "exploration", "sequence"):
            self.assertEqual(explain.choose_format("auto", goal)[0], "html")
        self.assertEqual(explain.choose_format("auto", "relationships")[0], "mermaid")
        for template in ("frame-model.mjs", "remotion-entry.mjs"):
            src = (explain.ASSETS / template).read_text()
            self.assertNotIn("Date.now", src)
            self.assertNotIn("Math.random", src)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "preview.json"
        self.source.write_bytes(model.canonical(preview_fixture()))

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/explain.py"), *args],
                              capture_output=True, text=True, timeout=30)

    def test_dry_run_then_apply_and_overwrite_refusal(self):
        output = self.base / "view"
        args = ["from-preview", "--input", str(self.source), "--output", str(output)]
        before = self.source.read_bytes()
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "dry-run")
        self.assertFalse(output.exists())
        result = self.cli(*args, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        inventory = {p.name: p.read_bytes() for p in output.iterdir()}
        result = self.cli(*args, "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(inventory, {p.name: p.read_bytes() for p in output.iterdir()})
        self.assertEqual(before, self.source.read_bytes())
        out2 = self.base / "diagram"
        result = self.cli("render", "--input", str(output / "explanation.json"), "--format", "mermaid", "--output", str(out2), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((output / "explanation.json").read_bytes(), (out2 / "explanation.json").read_bytes())

    def test_bad_input_missing_dependency_and_unsafe_output_write_nothing(self):
        output = self.base / "output"
        result = self.cli("from-preview", "--input", str(self.source), "--format", "p5", "--output", str(output), "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())
        for dest in (ROOT / "forbidden-output", self.base / ".git" / "view"):
            result = self.cli("from-preview", "--input", str(self.source), "--output", str(dest), "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertFalse(dest.exists())
        self.source.write_text('{"a":1,"a":2}')
        result = self.cli("from-preview", "--input", str(self.source), "--output", str(output), "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_symlinks_and_nonregular_sources_are_rejected(self):
        link = self.base / "linked"
        link.symlink_to(self.source)
        with self.assertRaises(model.IRError):
            explain.read_regular(link, 1000)
        link.unlink()
        link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(model.IRError):
            explain.destination(link / "view", ())
        with self.assertRaises(model.IRError):
            explain.read_regular(self.base, 1000)

    def test_publication_preflights_names_before_creating_any_output(self):
        output = self.base / "view"
        with self.assertRaises(model.IRError):
            explain.publish(output, {"explanation.json": b"{}", "../bad.txt": b"bad",
                                     "render-manifest.json": b"{}"})
        self.assertFalse(output.exists())
        self.assertFalse((self.base / "bad.txt").exists())

    def test_publication_leaves_incomplete_output_and_does_not_delete_on_failure(self):
        output = self.base / "view"
        files = explain.render_files(model.from_preview(preview_fixture()), "html")
        original_open = explain.os.open
        def fail_second_file(path, flags, mode=0o777, **kwargs):
            if Path(path).name == "index.html":
                raise OSError("simulated full disk")
            return original_open(path, flags, mode, **kwargs)
        with mock.patch.object(explain.os, "open", side_effect=fail_second_file):
            with self.assertRaisesRegex(OSError, "simulated full disk"):
                explain.publish(output, files)
        self.assertEqual((output / "explanation.json").read_bytes(), files["explanation.json"])
        self.assertFalse((output / "render-manifest.json").exists())
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        with self.assertRaises(model.IRError):
            explain.publish(output, files)
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_publication_uses_private_permissions_and_manifest_last(self):
        output = self.base / "view"
        # Order supplied by a renderer cannot put the completion manifest first.
        files = {"render-manifest.json": b"{}", "README.txt": b"read", "explanation.json": b"{}"}
        observed = []
        original_open = explain.os.open
        def record(path, flags, mode=0o777, **kwargs):
            observed.append(Path(path).name)
            return original_open(path, flags, mode, **kwargs)
        with mock.patch.object(explain.os, "open", side_effect=record):
            explain.publish(output, files)
        self.assertEqual(observed, ["README.txt", "explanation.json", "render-manifest.json"])
        if sys.platform != "win32":
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            for name in files:
                self.assertEqual((output / name).stat().st_mode & 0o777, 0o600)


class CanonicalExplanationTests(unittest.TestCase):
    """Uses #56's real fixture setup; this is not satisfied by the synthetic data."""
    @classmethod
    def setUpClass(cls):
        # Import the module, not the TestCase symbol, to avoid duplicate discovery.
        from tests import test_spec_activation_explainer as lab_tests
        cls.lab = lab_tests.CanonicalRouterTests
        cls.lab.setUpClass()
        cls.addClassCleanup(cls.lab.doClassCleanups)
        cls.case = cls.lab(methodName="test_canonical_capsule_equals_router_and_writes_nothing")
        cls.case.setUp()
        cls.addClassCleanup(cls.case.doCleanups)

    def test_real_preview_preserves_canonical_capsule_and_source(self):
        preview = self.case.preview()
        ir = model.from_preview(preview)
        model.validate(ir)
        for kind in ("json", "mermaid", "html", "remotion"):
            stored = model.parse(explain.render_files(ir, kind)["explanation.json"])
            self.assertEqual(stored["source"]["snapshot"]["capsule"], preview["capsule"])

    def test_live_cli_reads_without_modifying_target(self):
        from tests.test_spec_activation_explainer import inventory
        before = inventory(self.case.repo)
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/explain.py"), "spec",
                "--repo", str(self.case.repo), "--path", "main.go", "--requirement", "GO-NAME-001",
                "--format", "html", "--output", str(Path(tmp) / "view"), "--apply"],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["mode"], "apply")
        self.assertEqual(inventory(self.case.repo), before)


if __name__ == "__main__":
    unittest.main()
