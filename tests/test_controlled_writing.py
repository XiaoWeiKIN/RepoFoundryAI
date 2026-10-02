"""Check writing-guide distribution, not linguistic or STE conformance."""

from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "sync_controlled_writing", ROOT / "scripts/sync_controlled_writing.py"
)
assert SPEC is not None and SPEC.loader is not None
GUIDES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUIDES)
READ_LINK = "[受控技术写作](references/controlled-writing.md)"


class ControlledWritingTests(unittest.TestCase):
    def test_repository_copies_are_current(self) -> None:
        self.assertEqual(GUIDES.sync(ROOT), {"mode": "check", "changed": [], "ok": True})

    def test_every_skill_reads_the_guide_before_its_workflow(self) -> None:
        for skill in GUIDES.SKILLS:
            with self.subTest(skill=skill):
                text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertEqual(text.count(READ_LINK), 1)
                self.assertIn("撰写、改写或评审文档正文前", text)
                self.assertLess(text.index(READ_LINK), text.index("\n## "))

    def test_independent_skill_has_a_self_contained_guide(self) -> None:
        expected = (ROOT / GUIDES.GUIDE).read_bytes()
        for skill in GUIDES.SKILLS:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as directory:
                isolated = Path(directory) / skill
                (isolated / "references").mkdir(parents=True)
                shutil.copyfile(ROOT / skill / "SKILL.md", isolated / "SKILL.md")
                shutil.copyfile(ROOT / skill / GUIDES.GUIDE, isolated / GUIDES.GUIDE)
                self.assertEqual((isolated / GUIDES.GUIDE).read_bytes(), expected)
                # The guide must not depend on another installed Skill, root
                # source-checkout file, or network-loaded Markdown reference.
                text = (isolated / GUIDES.GUIDE).read_text(encoding="utf-8")
                self.assertEqual(re.findall(r"\]\(([^)]+)\)", text), [])

    def fixture(self, root: Path) -> None:
        (root / GUIDES.GUIDE).parent.mkdir(parents=True)
        shutil.copyfile(ROOT / GUIDES.GUIDE, root / GUIDES.GUIDE)
        for skill in GUIDES.SKILLS:
            (root / skill / "references").mkdir(parents=True)
            (root / skill / "SKILL.md").write_text("# Fixture\n", encoding="utf-8")

    def test_preview_is_read_only_and_apply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            sentinel = root / "docs/adr/accepted.md"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_bytes(b"sealed history\n")
            preview = GUIDES.sync(root)
            self.assertFalse(preview["ok"])
            self.assertEqual(len(preview["changed"]), 6)
            for skill in GUIDES.SKILLS:
                self.assertFalse((root / skill / GUIDES.GUIDE).exists())
            self.assertTrue(GUIDES.sync(root, apply=True)["ok"])
            self.assertEqual(GUIDES.sync(root)["changed"], [])
            self.assertEqual(GUIDES.sync(root, apply=True)["changed"], [])
            self.assertEqual(sentinel.read_bytes(), b"sealed history\n")

    def test_drift_is_detected_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            GUIDES.sync(root, apply=True)
            target = root / GUIDES.SKILLS[0] / GUIDES.GUIDE
            target.write_bytes(b"modified guide\n")
            self.assertEqual(GUIDES.sync(root)["changed"], [target.relative_to(root).as_posix()])
            self.assertEqual(target.read_bytes(), b"modified guide\n")

    def test_missing_skill_aborts_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / GUIDES.SKILLS[-1] / "SKILL.md").unlink()
            with self.assertRaises(ValueError):
                GUIDES.sync(root, apply=True)
            for skill in GUIDES.SKILLS:
                self.assertFalse((root / skill / GUIDES.GUIDE).exists())

    def test_symlink_target_aborts_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            outside = root / "untouched.md"
            outside.write_bytes(b"original\n")
            target = root / GUIDES.SKILLS[-1] / GUIDES.GUIDE
            try:
                target.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaises(ValueError):
                GUIDES.sync(root, apply=True)
            self.assertEqual(outside.read_bytes(), b"original\n")
            for skill in GUIDES.SKILLS[:-1]:
                self.assertFalse((root / skill / GUIDES.GUIDE).exists())

    def test_invalid_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / GUIDES.GUIDE).write_bytes(b"\xff")
            with self.assertRaises(UnicodeError):
                GUIDES.sync(root, apply=True)


if __name__ == "__main__":
    unittest.main()
