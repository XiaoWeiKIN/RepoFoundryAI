"""Exercise mechanical hints and read-only behavior, not semantic conformance."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_writing.py"
SPEC = importlib.util.spec_from_file_location("writing_check", SCRIPT)
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class WritingCheckTests(unittest.TestCase):
    def hints(self, text: str, lang: str = "zh", **kwargs):
        return CHECK.review(text, lang, kwargs.get("ranges", []), kwargs.get("length", False))

    def cli(self, *args: str):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                              text=True, encoding="utf-8", capture_output=True, timeout=10)

    def test_chinese_wrapper_and_vague_words_are_candidates(self):
        found = self.hints("缓存模块进行检查。\n性能显著提升。")
        self.assertEqual([f["rule"] for f in found], ["CW-ZH-VERB", "CW-ZH-VAGUE"])
        self.assertTrue(all(f["kind"] == "review" for f in found))
        self.assertEqual(found[0]["line"], 1)
        self.assertEqual(found[0]["column"], 5)

    def test_english_candidates(self):
        found = self.hints("Perform a validation before reading various files.", "en")
        self.assertEqual({f["rule"] for f in found}, {"CW-EN-VERB", "CW-EN-VAGUE"})

    def test_domain_terms_and_normative_keywords_are_not_banned(self):
        text = "建议面板不具有统计显著性。\nThe service MUST retain the SHOULD clause."
        self.assertEqual(self.hints(text, "auto"), [])

    def test_quoted_examples_are_protected(self):
        self.assertEqual(self.hints('“进行检查”与「显著提升」是原文。\n"various"', "auto"), [])

    def test_inline_code_including_multiple_backticks_is_protected(self):
        self.assertEqual(self.hints('`进行检查` 与 ``a ` 显著提升``。'), [])

    def test_multiline_code_span_is_protected(self):
        self.assertEqual(self.hints('`开始\n进行检查\n结束`'), [])

    def test_fence_length_and_type_are_respected(self):
        text = "````text\n进行检查\n```\n显著提升\n~~~~\n````\n进行检查。"
        found = self.hints(text)
        self.assertEqual([(f["line"], f["rule"]) for f in found], [(7, "CW-ZH-VERB")])

    def test_tilde_fence_is_protected(self):
        self.assertEqual(self.hints("~~~log\n进行检查\n~~~"), [])

    def test_frontmatter_and_indented_code_are_protected(self):
        self.assertEqual(self.hints("---\nlabel: 进行检查\n---\n    进行检查\n\t显著提升"), [])

    def test_blockquotes_and_link_definitions_are_protected(self):
        self.assertEqual(self.hints("> 进行检查。\n[ref]: ./进行检查.md\n[other]: https://example.invalid/显著提升"), [])

    def test_links_keep_label_and_ignore_nested_destination(self):
        found = self.hints('[进行检查](./topic(显著提升).md "进行检查")')
        self.assertEqual([(f["rule"], f["column"]) for f in found], [("CW-ZH-VERB", 2)])

    def test_comments_html_and_raw_urls_are_protected(self):
        text = "<!-- 进行检查\n显著提升 -->\n\n<div>进行检查</div>\n\nhttps://example.invalid/进行检查"
        self.assertEqual(self.hints(text), [])

    def test_masking_preserves_line_and_column(self):
        found = self.hints("首行\n`代码` 进行检查。")
        self.assertEqual([(f["line"], f["column"]) for f in found], [(2, 6)])

    def test_line_range_still_reads_prior_fence_context(self):
        found = self.hints("```\n进行检查\n```\n进行检查", ranges=[(2, 4)])
        self.assertEqual([f["line"] for f in found], [4])

    def test_nonselected_lines_do_not_produce_hints(self):
        found = self.hints("进行检查\n执行检查\n显著提升", ranges=[(2, 2)])
        self.assertEqual(found, [])

    def test_length_hints_are_opt_in_not_limits(self):
        text = "甲" * 51 + "。"
        self.assertEqual(self.hints(text), [])
        self.assertEqual(self.hints(text, length=True)[0]["kind"], "info")

    def test_step_length_and_table_exception(self):
        text = "1. " + "甲" * 41 + "。\n| " + "甲" * 60 + " |"
        found = self.hints(text, length=True)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["threshold"], 40)

    def test_english_length_hint(self):
        text = " ".join(["word"] * 26) + "."
        self.assertEqual(self.hints(text, "en", length=True)[0]["units"], 26)

    def test_language_auto_is_per_line(self):
        found = self.hints("进行检查。\nPerform a validation.", "auto")
        self.assertEqual({f["rule"] for f in found}, {"CW-ZH-VERB", "CW-EN-VERB"})

    def test_spacing_and_punctuation_are_reviewable(self):
        found = self.hints("使用Redis,请重试。")
        self.assertIn("CW-ZH-SPACING", [f["rule"] for f in found])
        self.assertIn("CW-ZH-PUNCT", [f["rule"] for f in found])

    def test_conditional_loss_is_outside_mechanical_verification(self):
        # Both scan clean: this demonstrates why a semantic reviewer is required.
        original = "如果没有当前项，向下键选择首项。否则选择下一项。"
        lossy = "向下键选择首项。"
        self.assertEqual(self.hints(original), [])
        self.assertEqual(self.hints(lossy), [])

    def test_findings_return_zero_with_source_digest_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            original = "进行检查。\r\n".encode()
            path.write_bytes(original)
            before = path.stat().st_mtime_ns
            result = self.cli(str(path), "--lang", "zh", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "review_hints_only")
            self.assertEqual(data["semantic_verification"], "not_performed")
            self.assertFalse(data["source_files_modified"])
            self.assertEqual(data["documents"][0]["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(len(data["documents"][0]["findings"]), 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(path.stat().st_mtime_ns, before)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_clean_scan_does_not_claim_compliance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            path.write_text("缓存模块恢复条目。", encoding="utf-8")
            result = self.cli(str(path), "--json")
            data = json.loads(result.stdout)
            self.assertEqual(data["documents"][0]["findings"], [])
            self.assertEqual(data["semantic_verification"], "not_performed")
            self.assertNotIn("passed", result.stdout)

    def test_multiple_files_and_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            path.write_text("进行检查\n执行检查\n显著提升", encoding="utf-8")
            data = json.loads(self.cli(str(path), "--line-range", "1:1",
                                       "--line-range", "3:3", "--json").stdout)
            self.assertEqual([f["line"] for f in data["documents"][0]["findings"]], [1, 3])
            data = json.loads(self.cli(str(path), str(path), "--json").stdout)
            self.assertEqual(len(data["documents"]), 2)
            self.assertEqual(self.cli(str(path), str(path), "--line-range", "1:1").returncode, 2)

    def test_invalid_ranges_and_unsupported_mutation_flag(self):
        for value in ("0:1", "2:1", "1", "-1:2"):
            with self.subTest(value=value):
                self.assertEqual(self.cli("not-read.md", "--line-range=" + value).returncode, 2)
        self.assertEqual(self.cli("not-read.md", "--fix").returncode, 2)
        self.assertEqual(self.cli().returncode, 2)

    def test_missing_file_is_input_error_not_clean_scan(self):
        result = self.cli("/nonexistent/rf-writing-fixture.md", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["status"], "input_error")

    def test_directory_invalid_utf8_oversize_and_excess_range_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.cli(directory).returncode, 2)
            path = Path(directory) / "draft.md"
            path.write_bytes(b"\xff")
            self.assertEqual(self.cli(str(path)).returncode, 2)
            path.write_bytes(b"x" * (CHECK.MAX_BYTES + 1))
            self.assertEqual(self.cli(str(path)).returncode, 2)
            path.write_text("one line", encoding="utf-8")
            self.assertEqual(self.cli(str(path), "--line-range", "1:2").returncode, 2)

    def test_any_failed_input_prevents_partial_success_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            path.write_text("进行检查", encoding="utf-8")
            result = self.cli(str(path), str(path.with_name("missing.md")), "--json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.md"
            path.write_bytes(b"")
            result = self.cli(str(path), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["documents"][0]["findings"], [])


if __name__ == "__main__":
    unittest.main()
