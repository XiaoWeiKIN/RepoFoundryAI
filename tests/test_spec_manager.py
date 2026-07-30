from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import spec_manager  # noqa: E402
from tests.spec_git_fixture import (  # noqa: E402
    commit_all,
    create_git_catalog,
    write_catalog,
)


class SpecManagerBoundaryTestCase(unittest.TestCase):
    def test_manifest_rejects_unknown_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "specs.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "owner": "another-product",
                        "catalog": {
                            "kind": "git",
                            "url": "https://example.com/specifications.git",
                            "ref": "main",
                        },
                        "specs": ["core/semantic-naming"],
                        "project_specs": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                spec_manager.SpecError,
                "SPEC_MANIFEST_INVALID.owner",
            ):
                spec_manager.parse_manifest(manifest)

    def test_catalog_rejects_dependency_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog_root = Path(temporary) / "catalog"
            catalog_root.mkdir()
            write_catalog(catalog_root)
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
                        "catalog": {
                            "kind": "git",
                            "url": "https://example.com/specifications.git",
                            "ref": "main",
                        },
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

    def test_detection_ignores_dependencies_and_managed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            catalog_root = repo / "catalog"
            catalog_root.mkdir()
            write_catalog(catalog_root)
            dependency = repo / "node_modules" / "fixture"
            dependency.mkdir(parents=True)
            (dependency / "ignored.ts").write_text("", encoding="utf-8")
            managed = repo / "docs" / "agent-guides" / "managed"
            managed.mkdir(parents=True)
            (managed / "ignored.py").write_text("", encoding="utf-8")
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
        with tempfile.TemporaryDirectory() as temporary:
            catalog_root = Path(temporary) / "catalog"
            catalog_root.mkdir()
            write_catalog(catalog_root)
            catalog = spec_manager.load_catalog(catalog_root)
            manifest = spec_manager.SpecManifest(
                catalog={
                    "kind": "git",
                    "url": "https://example.com/specifications.git",
                    "ref": "main",
                },
                spec_ids=("languages/go",),
                project_specs=(),
            )

            with self.assertRaisesRegex(
                spec_manager.SpecError,
                "SPEC_REQUIRED_SELECTION_MISSING",
            ):
                spec_manager.resolve_selection(manifest, catalog)

    def test_git_catalog_resolves_full_commit_without_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source, expected_commit = create_git_catalog(Path(temporary))
            catalog = spec_manager.resolve_git_catalog(
                {
                    "kind": "git",
                    "url": source.resolve().as_uri(),
                    "ref": "main",
                },
                "main",
            )

            self.assertEqual(catalog.resolved_revision, expected_commit)
            self.assertEqual(
                catalog.catalog_id,
                "test.engineering-specifications",
            )
            self.assertEqual(catalog.catalog_version, "0.1.0")
            self.assertIn(
                "specification/languages/go.md",
                catalog.contents,
            )

    def test_git_catalog_rejects_symbolic_link_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source, _ = create_git_catalog(Path(temporary))
            go_spec = source / "specification" / "languages" / "go.md"
            go_spec.unlink()
            go_spec.symlink_to("../core/semantic-naming.md")
            commit_all(source, "replace Go specification with symlink")

            with self.assertRaisesRegex(
                spec_manager.SpecError,
                "expected a regular Git blob",
            ):
                spec_manager.resolve_git_catalog(
                    {
                        "kind": "git",
                        "url": source.resolve().as_uri(),
                        "ref": "main",
                    },
                    "main",
                )

    def test_manifest_rejects_embedded_git_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "specs.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "owner": "engineering-workflow",
                        "catalog": {
                            "kind": "git",
                            "url": "https://token@example.com/specs.git",
                            "ref": "main",
                        },
                        "specs": ["core/semantic-naming"],
                        "project_specs": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                spec_manager.SpecError,
                "embedded credentials are not supported",
            ):
                spec_manager.parse_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
