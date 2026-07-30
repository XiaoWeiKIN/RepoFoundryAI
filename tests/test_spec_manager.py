from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import spec_manager  # noqa: E402


class SpecManagerBoundaryTestCase(unittest.TestCase):
    def test_catalog_rejects_dependency_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog_root = Path(temporary) / "catalog"
            shutil.copytree(ROOT / "engineering-specs", catalog_root)
            catalog_path = catalog_root / "catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["specs"][0]["requires"] = ["languages/go"]
            catalog_path.write_text(
                json.dumps(catalog, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                spec_manager.SpecError,
                "SPEC_CATALOG_DEPENDENCY_CYCLE",
            ):
                spec_manager.load_catalog(catalog_root)

    def test_manifest_rejects_project_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "specs.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "owner": "engineering-workflow",
                        "catalog": {"kind": "bundled"},
                        "specs": ["core/semantic-naming"],
                        "project_specs": [
                            {
                                "path": "../outside.md",
                                "applies_to": ["**/*"],
                                "description": "unsafe",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                spec_manager.SpecError,
                "path traversal is not allowed",
            ):
                spec_manager.parse_manifest(manifest)

    def test_detection_ignores_dependencies_and_catalog_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            catalog_root = repo / "catalog"
            shutil.copytree(ROOT / "engineering-specs", catalog_root)
            dependency = repo / "node_modules" / "fixture"
            dependency.mkdir(parents=True)
            (dependency / "ignored.ts").write_text("", encoding="utf-8")
            (catalog_root / "tool.py").write_text("", encoding="utf-8")
            catalog = spec_manager.load_catalog(catalog_root)

            self.assertEqual(spec_manager.detect_specs(repo, catalog), ())

            source = repo / "service"
            source.mkdir()
            (source / "main.go").write_text("package service\n", encoding="utf-8")
            self.assertEqual(
                spec_manager.detect_specs(repo, catalog),
                ("languages/go",),
            )

    def test_required_spec_must_be_explicit_in_manifest(self) -> None:
        catalog = spec_manager.load_catalog(ROOT / "engineering-specs")
        manifest = spec_manager.SpecManifest(
            catalog={"kind": "bundled"},
            spec_ids=("languages/go",),
            project_specs=(),
        )

        with self.assertRaisesRegex(
            spec_manager.SpecError,
            "SPEC_REQUIRED_SELECTION_MISSING",
        ):
            spec_manager.resolve_selection(manifest, catalog)


if __name__ == "__main__":
    unittest.main()
