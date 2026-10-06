"""Tests for the source-bound architecture HTML renderer."""
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

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/explain_architecture.py"
SPEC = importlib.util.spec_from_file_location("explain_architecture", SCRIPT)
assert SPEC and SPEC.loader
ARCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCH)


def fixture():
    document = {
        "schema": ARCH.SCHEMA,
        "authority": "none",
        "language": "en",
        "subject": {
            "title": "Synthetic editor architecture",
            "summary": "A test-only source-bound explanation.",
        },
        "source": {
            "repository": "example/test",
            "revision": "abc123",
            "files": [
                {"path": "src/caller.py", "digest_algorithm": "sha256", "digest": "1" * 64},
                {"path": "src/editor.py", "digest_algorithm": "sha256", "digest": "2" * 64},
                {"path": "tests/editor.py", "digest_algorithm": "sha256", "digest": "3" * 64},
            ],
            "source_set_sha256": "",
        },
        "components": [
            {
                "id": "caller",
                "label": "Caller",
                "responsibility": "Owns controlled state.",
                "paths": ["src/caller.py"],
            },
            {
                "id": "editor",
                "label": "Editor",
                "responsibility": "Owns the editing surface.",
                "paths": ["src/editor.py"],
            },
        ],
        "flows": [
            {
                "id": "edit",
                "title": "Edit flow",
                "steps": [
                    {"actor": "caller", "action": "Provides controlled state."},
                    {
                        "actor": "editor",
                        "action": "Emits an edit.",
                        "condition": "Only after an input event.",
                    },
                ],
            }
        ],
        "invariants": [
            {"text": "Caller remains the state owner.", "refs": ["src/caller.py:10"]}
        ],
        "limitations": [
            {"text": "No browser behavior was measured.", "refs": ["tests/editor.py"]}
        ],
        "evidence": [
            {
                "id": "source-editor",
                "kind": "source",
                "label": "Editor source",
                "locator": "src/editor.py",
            },
            {
                "id": "test-editor",
                "kind": "test",
                "label": "Editor test",
                "locator": "tests/editor.py",
            },
        ],
    }
    normalized = sorted(document["source"]["files"], key=lambda item: item["path"])
    document["source"]["source_set_sha256"] = ARCH.sha256(ARCH.canonical(normalized))
    document["sha256"] = ARCH.sha256(ARCH.canonical(document))
    return document


class ArchitectureTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_validates_source_bound_document_and_digest(self):
        document = fixture()
        before = copy.deepcopy(document)
        self.assertIs(ARCH.validate(document), document)
        self.assertEqual(document, before)

        bad = copy.deepcopy(document)
        bad["flows"][0]["steps"][0]["actor"] = "missing"
        with self.assertRaisesRegex(ARCH.ArchitectureError, "Unknown flow actor"):
            ARCH.validate(bad)

        bad = copy.deepcopy(document)
        bad["subject"]["summary"] = "edited"
        with self.assertRaisesRegex(ARCH.ArchitectureError, "Document digest"):
            ARCH.validate(bad)

        bad = copy.deepcopy(document)
        bad["source"]["files"][0]["digest"] = "9" * 64
        with self.assertRaisesRegex(ARCH.ArchitectureError, "source_set"):
            ARCH.validate(bad)

        reordered = copy.deepcopy(document)
        reordered.pop("sha256")
        reordered["source"]["files"].reverse()
        reordered["sha256"] = ARCH.sha256(ARCH.canonical(reordered))
        self.assertIs(ARCH.validate(reordered), reordered)

        bad = copy.deepcopy(document)
        bad["components"][0]["paths"] = ["src/missing.py"]
        with self.assertRaisesRegex(ARCH.ArchitectureError, "not in source.files"):
            ARCH.validate(bad)

        bad = copy.deepcopy(document)
        bad["evidence"][0]["locator"] = "tests/missing.py"
        with self.assertRaisesRegex(ARCH.ArchitectureError, "not in source.files"):
            ARCH.validate(bad)

    def test_duplicate_json_and_nonfinite_values_are_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ARCH.ArchitectureError):
                ARCH.parse(raw)

    def test_html_keeps_untrusted_text_inert_offline_and_localized(self):
        document = fixture()
        document.pop("sha256")
        document["subject"]["summary"] = '</script><img src=x onerror=alert(1)>'
        document["sha256"] = ARCH.sha256(ARCH.canonical(document))
        page = ARCH.html_page(document).decode()
        self.assertNotIn("<img src=x", page)
        self.assertIn("\\u003c/script>", page)
        self.assertIn("connect-src &#x27;none&#x27;", page)
        self.assertIn("script-src &#x27;sha256-", page)
        self.assertNotIn("script-src &#x27;unsafe-inline&#x27;", page)
        self.assertNotIn("fetch(", page)
        self.assertIn('<html lang="en">', page)

        zh = fixture()
        zh.pop("sha256")
        zh["language"] = "zh-CN"
        zh["subject"]["title"] = "合成架构"
        zh["sha256"] = ARCH.sha256(ARCH.canonical(zh))
        page = ARCH.html_page(zh).decode()
        self.assertIn('<html lang="zh-CN">', page)
        self.assertIn("限制", page)
        self.assertIn("来源标识", page)
        self.assertIn("系统模型", page)

    def test_dry_run_then_apply_preserves_input_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "architecture.json"
            output = root / "view"
            raw = ARCH.canonical(fixture())
            source.write_bytes(raw)

            dry = self.cli("--input", str(source), "--output", str(output))
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(output.exists())

            run = self.cli("--input", str(source), "--output", str(output), "--apply")
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(source.read_bytes(), raw)
            self.assertTrue((output / "index.html").is_file())

            manifest = json.loads((output / "render-manifest.json").read_text())
            self.assertEqual(manifest["authority"], "none")
            self.assertEqual(
                manifest["files"]["index.html"],
                hashlib.sha256((output / "index.html").read_bytes()).hexdigest(),
            )

            again = self.cli("--input", str(source), "--output", str(output), "--apply")
            self.assertEqual(again.returncode, 2)

    def test_no_repository_inference_or_network_client(self):
        source = SCRIPT.read_text()
        self.assertNotIn("subprocess", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)
        self.assertIn("source-bound architecture JSON", source)


if __name__ == "__main__":
    unittest.main()
