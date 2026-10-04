"""Reading-language tests, not translation of normative source or video renders."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import explain
import explanation_ir as model
import explanation_i18n as i18n
from test_explanation_ir import preview_fixture


def embedded(page: bytes, element_id: str) -> dict:
    match = re.search(r'<script type="application/json" id="' + element_id + r'">(.*?)</script>', page.decode(), re.S)
    if match is None:
        raise AssertionError(f"Missing {element_id} data")
    return json.loads(match[1])


class ReadingLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = model.from_preview(preview_fixture())

    def test_dictionaries_cover_the_same_nonempty_labels(self) -> None:
        self.assertEqual(set(i18n.LABELS), set(i18n.LANGUAGES))
        self.assertEqual(set(i18n.LABELS["en"]), set(i18n.LABELS["zh-CN"]))
        for lang in i18n.LANGUAGES:
            self.assertTrue(all(isinstance(x, str) and x.strip() for x in i18n.LABELS[lang].values()))
            reading = i18n.presentation(self.ir, lang)
            self.assertEqual(set(reading["scenes"]), {s["id"] for s in self.ir["scenes"]})
            self.assertEqual(set(reading["statements"]), {s["id"] for s in self.ir["statements"]})

    def test_all_formats_preserve_exact_v1_ir_and_source_in_both_languages(self) -> None:
        before = copy.deepcopy(self.ir)
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "p5.js"
            runtime.write_text("/* Packaging fixture, not a real p5 runtime. */\n")
            for lang in i18n.LANGUAGES:
                for kind in explain.FORMATS:
                    with self.subTest(language=lang, format=kind):
                        files = explain.render_files(self.ir, kind, runtime if kind == "p5" else None, lang=lang)
                        self.assertEqual(files["explanation.json"], model.canonical(before) + b"\n")
                        self.assertEqual(json.loads(files["presentation.json"]), i18n.presentation(before, lang))
                        manifest = json.loads(files["render-manifest.json"])
                        self.assertEqual(manifest["language"], lang)
                        self.assertEqual(manifest["ir_sha256"], before["sha256"])
                        self.assertEqual(manifest["source_sha256"], before["source"]["sha256"])
                        self.assertEqual(manifest["authority"], "none")
                        for name, digest in manifest["files"].items():
                            self.assertEqual(model.sha256(files[name]), digest)
        self.assertEqual(self.ir, before)

    def test_english_default_retains_original_statement_and_scene_text(self) -> None:
        reading = i18n.presentation(self.ir)
        self.assertEqual(reading["language"], "en")
        self.assertEqual(reading["title"], self.ir["subject"]["title"])
        for s in self.ir["statements"]:
            self.assertEqual(reading["statements"][s["id"]], s["text"])
        for s in self.ir["scenes"]:
            self.assertEqual(reading["scenes"][s["id"]], s["title"])
        self.assertEqual(explain.render_files(self.ir, "html"), explain.render_files(self.ir, "html", lang="en"))

    def test_chinese_counts_limits_and_source_binding_are_explicit(self) -> None:
        reading = i18n.presentation(self.ir, "zh-CN")
        self.assertEqual(reading["ir_sha256"], self.ir["sha256"])
        self.assertEqual(reading["source_sha256"], self.ir["source"]["sha256"])
        self.assertEqual(reading["statements"]["closure"], "所选要求及其依赖共包含 2 条要求、1 条依赖关系。")
        capsule = self.ir["source"]["snapshot"]["capsule"]
        self.assertIn(f"{capsule['bytes']} 个 UTF-8 字节", reading["statements"]["capsule"])
        self.assertIn("32768 字节", reading["statements"]["capsule"])
        self.assertIn("不构成批准", reading["statements"]["authority"])
        self.assertIn("不代表语义上适用", reading["statements"]["applicability"])
        self.assertIn("不是实时视图", reading["statements"]["freshness"])
        self.assertIn("不替代原始要求", reading["labels"]["source_note"])

    def test_empty_and_whole_spec_choices_do_not_claim_activation_in_chinese(self) -> None:
        p = preview_fixture()
        p.update(direct=[], resolved=[], edges=[], capsule=None)
        ir = model.from_preview(p)
        self.assertIn("空选择不构成正式", i18n.presentation(ir, "zh-CN")["statements"]["capsule"])
        self.assertIn("没有要求依赖图", explain.mermaid(ir, "zh-CN").decode())
        p["whole_specs"] = ["languages/typescript"]
        p["capsule"] = preview_fixture()["capsule"]
        self.assertIn("包含 1 份规范", i18n.presentation(model.from_preview(p), "zh-CN")["statements"]["selection"])

    def test_mixed_unicode_sources_and_template_markers_are_preserved_as_data(self) -> None:
        p = preview_fixture()
        p["paths"] = ['docs/架构😀@@IR@@@@PRESENTATION@@@@UI_play@@@@CSP@@</script><img src=x>\u2028.md']
        ir = model.from_preview(p)
        for lang in i18n.LANGUAGES:
            page = explain.story_html(ir, lang=lang)
            self.assertEqual(embedded(page, "ir"), ir)
            self.assertEqual(embedded(page, "presentation"), i18n.presentation(ir, lang))
            self.assertNotIn(b"<img src=x>", page)
            self.assertNotIn(b"innerHTML", page)

    def test_both_html_modes_have_matching_csp_and_localized_accessible_controls(self) -> None:
        for lang in i18n.LANGUAGES:
            for p5 in (False, True):
                with self.subTest(language=lang, p5=p5):
                    page = explain.story_html(self.ir, lang=lang, p5=p5).decode()
                    ui = i18n.LABELS[lang]
                    self.assertIn(f'<html lang="{lang}">', page)
                    self.assertIn(f'aria-label="{ui["frame"]}"', page)
                    self.assertIn(f'>{ui["play"]}</button>', page)
                    self.assertIn(ui["relationships"], page)
                    module = page.split('<script type="module">')[1].split('</script>')[0]
                    digest = base64.b64encode(hashlib.sha256(module.encode()).digest()).decode()
                    self.assertIn(digest, page)
                    self.assertIn("connect-src &#x27;none&#x27;", page)
                    self.assertIn("Noto Sans CJK SC", page)

    def test_mermaid_roles_are_localized_but_ids_and_edges_are_exact(self) -> None:
        english = explain.mermaid(self.ir).decode()
        chinese = explain.mermaid(self.ir, "zh-CN").decode()
        self.assertIn("直接选择", chinese)
        self.assertIn("上下文依赖", chinese)
        for text in (english, chinese):
            self.assertIn("GO-NAME-001", text)
            self.assertIn("SEM-NAME-001", text)
        self.assertEqual([s for s in english.splitlines() if '-->' in s], [s for s in chinese.splitlines() if '-->' in s])

    def test_invalid_locale_and_tampered_ir_fail_without_fallback(self) -> None:
        for lang in ("zh", "fr", "auto", "zh_CN", "../zh-CN"):
            with self.subTest(lang=lang), self.assertRaises(model.IRError):
                explain.render_files(self.ir, "html", lang=lang)
        bad = copy.deepcopy(self.ir)
        bad["statements"][0]["text"] = "Invented evidence"
        for lang in i18n.LANGUAGES:
            with self.assertRaises(model.IRError):
                i18n.presentation(bad, lang)

    def test_remotion_reads_same_presentation_without_claiming_mp4(self) -> None:
        files = explain.render_files(self.ir, "remotion", lang="zh-CN")
        self.assertIn(b"./presentation.json", files["index.mjs"])
        self.assertIn(b"atPresentedFrame", files["index.mjs"])
        self.assertIn("未生成 MP4", files["README.txt"].decode())
        self.assertNotIn("out.mp4", files)
        self.assertIn("本地字体含中文字形", files["README.txt"].decode())

    def test_cli_can_rerender_old_ir_in_chinese_without_modifying_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "legacy-v1.json"
            original = model.canonical(self.ir)
            source.write_bytes(original)
            dest = root / "中文阅读"
            command = [sys.executable, "-B", str(ROOT / "scripts/explain.py"), "render", "--input", str(source), "--format", "html", "--lang", "zh-CN", "--output", str(dest)]
            planned = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertEqual(json.loads(planned.stdout)["language"], "zh-CN")
            self.assertFalse(dest.exists())
            applied = subprocess.run(command + ["--apply"], capture_output=True, text=True, timeout=30)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(embedded((dest / "index.html").read_bytes(), "ir"), self.ir)
            saved = {p.name: p.read_bytes() for p in dest.iterdir()}
            again = subprocess.run(command + ["--apply"], capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(saved, {p.name: p.read_bytes() for p in dest.iterdir()})

    def test_cli_rejects_unknown_language_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_bytes(model.canonical(preview_fixture()))
            dest = root / "not-created"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/explain.py"), "from-preview", "--input", str(source), "--lang", "zh", "--output", str(dest), "--apply"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(dest.exists())


class CanonicalLanguageTests(unittest.TestCase):
    """Installed real Router with the existing locked fixture, not a mock."""
    @classmethod
    def setUpClass(cls) -> None:
        from tests import test_spec_activation_explainer as lab_tests
        cls.lab = lab_tests.CanonicalRouterTests
        cls.lab.setUpClass()
        cls.addClassCleanup(cls.lab.doClassCleanups)
        cls.case = cls.lab(methodName="test_canonical_capsule_equals_router_and_writes_nothing")
        cls.case.setUp()
        cls.addClassCleanup(cls.case.doCleanups)

    def test_real_router_source_is_exact_in_every_localized_output(self) -> None:
        preview = self.case.preview()
        ir = model.from_preview(preview)
        for lang in i18n.LANGUAGES:
            for kind in ("json", "mermaid", "html", "remotion"):
                files = explain.render_files(ir, kind, lang=lang)
                self.assertEqual(json.loads(files["explanation.json"])["source"]["snapshot"], preview)

    def test_live_chinese_cli_preserves_target_repository(self) -> None:
        from tests.test_spec_activation_explainer import inventory
        before = inventory(self.case.repo)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "中文解释"
            result = subprocess.run([
                sys.executable, "-B", str(ROOT / "scripts/explain.py"), "spec",
                "--repo", str(self.case.repo), "--path", "main.go",
                "--requirement", "GO-NAME-001", "--format", "html",
                "--lang", "zh-CN", "--output", str(output), "--apply",
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["language"], "zh-CN")
            self.assertEqual(embedded((output / "index.html").read_bytes(), "presentation")["language"], "zh-CN")
        self.assertEqual(inventory(self.case.repo), before)


if __name__ == "__main__":
    unittest.main()
