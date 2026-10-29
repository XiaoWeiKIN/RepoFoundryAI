from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tests.harness_legacy_fixture import CORE_MEMORY_PATHS, strip_memory_assets


class LegacyFixtureBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = {"core": {"version": "1.5.6"}, "files": [
            {"path": path, "owner_kind": "core", "owner_id": None}
            for path in sorted(CORE_MEMORY_PATHS)
        ] + [{"path": "AGENTS.md", "owner_kind": "adapter", "owner_id": "codex"}]}
        for row in self.manifest["files"]:
            path = self.root / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture bytes\n")

    def test_only_new_memory_assets_are_removed(self) -> None:
        original_agents = (self.root / "AGENTS.md").read_bytes()
        original_record = self.manifest["files"][-1]
        strip_memory_assets(self.root, self.manifest)
        self.assertEqual(self.manifest["files"], [original_record])
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), original_agents)
        self.assertTrue(all(not (self.root / path).exists() for path in CORE_MEMORY_PATHS))

    def test_repeated_fixture_construction_is_idempotent(self) -> None:
        strip_memory_assets(self.root, self.manifest)
        expected = copy.deepcopy(self.manifest)
        strip_memory_assets(self.root, self.manifest)
        self.assertEqual(self.manifest, expected)
        self.assertTrue((self.root / "AGENTS.md").is_file())

    def test_current_or_future_core_cannot_be_stripped(self) -> None:
        for version in ("1.6.0", "1.6.1", "2.0.0"):
            with self.subTest(version=version):
                self.manifest["core"]["version"] = version
                expected = copy.deepcopy(self.manifest)
                with self.assertRaisesRegex(AssertionError, "before 1.6.0"):
                    strip_memory_assets(self.root, self.manifest)
                self.assertEqual(self.manifest, expected)
                self.assertTrue(all((self.root / path).is_file() for path in CORE_MEMORY_PATHS))

    def test_wrong_ownership_is_rejected_before_any_file_is_removed(self) -> None:
        self.manifest["files"][0]["owner_kind"] = "adapter"
        expected = copy.deepcopy(self.manifest)
        with self.assertRaisesRegex(AssertionError, "ownership"):
            strip_memory_assets(self.root, self.manifest)
        self.assertEqual(self.manifest, expected)
        self.assertTrue(all((self.root / path).is_file() for path in CORE_MEMORY_PATHS))


if __name__ == "__main__":
    unittest.main()
