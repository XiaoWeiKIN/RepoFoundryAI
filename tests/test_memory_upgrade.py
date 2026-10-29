from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

from tests.harness_legacy_fixture import CORE_MEMORY_PATHS, strip_memory_assets


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import foundryctl  # noqa: E402


class MemoryUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Import inside setUp: unittest must not rediscover the fixture's tests.
        from tests.test_foundryctl import FoundryctlTestCase
        self.fixture = FoundryctlTestCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.repo = self.fixture.repo
        self.fixture.run_cli("bootstrap", "--all-adapters", "--apply")
        self.manifest_path = self.repo / foundryctl.HARNESS_MANIFEST

    def read_manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, manifest: dict) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def inventory(self) -> dict[str, bytes | str]:
        return {
            path.relative_to(self.repo).as_posix(): (
                "symlink:" + str(path.readlink()) if path.is_symlink() else path.read_bytes()
            )
            for path in self.repo.rglob("*") if path.is_file() or path.is_symlink()
        }

    def legacy_fixture(self) -> dict:
        manifest = self.read_manifest()
        manifest["core"]["version"] = "1.5.6"
        strip_memory_assets(self.repo, manifest)
        for record in manifest["files"]:
            if record["owner_kind"] == "core":
                record["template_version"] = "1.5.6"
        self.write_manifest(manifest)
        return manifest

    def upgrade(self, *, apply: bool = False, expected: int = 0):
        args = ["upgrade", "--to", foundryctl.REPO_FOUNDRY_VERSION]
        if apply:
            args.append("--apply")
        return self.fixture.run_cli(*args, expected=expected)

    def test_old_contract_remains_readable_without_memory_modules(self) -> None:
        self.legacy_fixture()
        before = self.inventory()
        foundryctl.load_harness_manifest(self.repo)
        self.fixture.run_cli("validate", "--harness")
        self.assertEqual(self.inventory(), before)
        self.assertTrue(all(not (self.repo / path).exists() for path in CORE_MEMORY_PATHS))

    def test_preview_apply_and_repeat_preserve_specs_and_leave_cooling_off(self) -> None:
        self.legacy_fixture()
        before = self.inventory()
        preview = json.loads(self.upgrade().stdout)
        self.assertEqual(self.inventory(), before)
        self.assertEqual(
            {row["path"] for row in preview["actions"] if row["action"] == "create_file"},
            CORE_MEMORY_PATHS,
        )
        applied = json.loads(self.upgrade(apply=True).stdout)
        self.assertEqual(set(applied["created"]), CORE_MEMORY_PATHS)
        manifest = self.read_manifest()
        self.assertEqual(manifest["core"]["version"], foundryctl.CORE_HARNESS_VERSION)
        records = {record["path"]: record for record in manifest["files"]}
        for relative in CORE_MEMORY_PATHS:
            record = records[relative]
            self.assertEqual(record["owner_kind"], "core")
            self.assertIsNone(record.get("owner_id"))
            self.assertEqual(record["template_version"], foundryctl.CORE_HARNESS_VERSION)
            self.assertEqual(
                record["installed_sha256"], hashlib.sha256((self.repo / relative).read_bytes()).hexdigest()
            )
        after = self.inventory()
        for relative, raw in before.items():
            if relative.startswith("docs/agent-guides/managed/") or relative in {
                "docs/.engineering/specs.json", "docs/.engineering/specs.lock.json"
            }:
                self.assertEqual(after[relative], raw)
        self.assertFalse((self.repo / ".repo-foundry/memory-context.json").exists())
        self.fixture.run_cli("validate", "--harness")
        repeated = json.loads(self.upgrade(apply=True).stdout)
        self.assertEqual(repeated["created"], [])
        self.assertEqual(repeated["updated"], [])
        self.assertEqual(self.inventory(), after)

    def test_existing_off_configuration_is_preserved_byte_for_byte(self) -> None:
        self.legacy_fixture()
        config = self.repo / ".repo-foundry/memory-context.json"
        raw = b'{"schema_version": 1, "mode": "off", "background_ep": []}\n'
        config.write_bytes(raw)
        self.upgrade(apply=True)
        self.assertEqual(config.read_bytes(), raw)

    def test_modified_versioned_seed_blocks_all_upgrade_writes(self) -> None:
        self.legacy_fixture()
        router = self.repo / ".repo-foundry/engineering-specs/spec_router.py"
        router.write_bytes(router.read_bytes() + b"\n# Repository-owned customization.\n")
        before = self.inventory()
        preview = json.loads(self.upgrade().stdout)
        self.assertIn(
            router.relative_to(self.repo).as_posix(),
            {row["path"] for row in preview["actions"] if row["action"] == "conflict"},
        )
        self.assertEqual(self.inventory(), before)
        self.upgrade(apply=True, expected=2)
        self.assertEqual(self.inventory(), before)
        self.assertTrue(all(not (self.repo / path).exists() for path in CORE_MEMORY_PATHS))

    def test_unregistered_custom_memory_path_is_not_overwritten(self) -> None:
        self.legacy_fixture()
        target = self.repo / ".repo-foundry/engineering-specs/memory_runtime.py"
        target.write_bytes(b"# Local module: not a managed RepoHarnessKit seed.\n")
        before = self.inventory()
        preview = json.loads(self.upgrade().stdout)
        self.assertIn(
            target.relative_to(self.repo).as_posix(),
            {row["path"] for row in preview["actions"] if row["action"] == "conflict"},
        )
        self.assertEqual(self.inventory(), before)
        self.upgrade(apply=True, expected=2)
        self.assertEqual(self.inventory(), before)

    def test_symlink_at_new_managed_path_blocks_all_upgrade_writes(self) -> None:
        self.legacy_fixture()
        outside = self.fixture.base / "outside-runtime.py"
        outside.write_bytes(b"# External bytes must not be read or overwritten.\n")
        target = self.repo / ".repo-foundry/engineering-specs/memory_runtime.py"
        target.symlink_to(outside)
        before = self.inventory()
        outside_bytes = outside.read_bytes()
        self.upgrade(apply=True, expected=2)
        self.assertEqual(self.inventory(), before)
        self.assertEqual(outside.read_bytes(), outside_bytes)

    def test_old_version_with_new_file_records_is_still_rejected(self) -> None:
        manifest = self.read_manifest()
        manifest["core"]["version"] = "1.5.6"
        for record in manifest["files"]:
            if record["owner_kind"] == "core":
                record["template_version"] = "1.5.6"
        self.write_manifest(manifest)
        before = self.inventory()
        with self.assertRaisesRegex(foundryctl.FoundryctlError, "files path and ownership contract"):
            foundryctl.load_harness_manifest(self.repo)
        self.assertEqual(self.inventory(), before)

    def test_current_version_missing_memory_record_is_still_rejected(self) -> None:
        manifest = self.read_manifest()
        manifest["files"] = [
            record for record in manifest["files"]
            if record["path"] != ".repo-foundry/engineering-specs/memory_runtime.py"
        ]
        self.write_manifest(manifest)
        before = self.inventory()
        with self.assertRaisesRegex(foundryctl.FoundryctlError, "files path and ownership contract"):
            foundryctl.load_harness_manifest(self.repo)
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    unittest.main()
