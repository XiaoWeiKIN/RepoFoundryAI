from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FOUNDRYCTL = ROOT / "scripts" / "foundryctl.py"
sys.path.insert(0, str(ROOT / "scripts"))
import foundryctl  # noqa: E402

EPCTL = (
    ROOT
    / "engineering-execution-plan"
    / "scripts"
    / "epctl.py"
)
from tests.spec_git_fixture import (  # noqa: E402
    commit_all,
    create_git_catalog,
    update_go_spec,
)


class FoundryctlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repo = self.base / "target"
        self.repo.mkdir()
        (
            self.catalog_repository,
            self.catalog_commit,
        ) = create_git_catalog(self.base)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_default_source_is_a_fixed_catalog_release(self) -> None:
        source = foundryctl.spec_source(
            foundryctl.DEFAULT_SPEC_REPOSITORY,
            version=None,
            ref=None,
        )
        self.assertIsNotNone(source)
        assert source is not None
        self.assertEqual(source["ref"], "refs/tags/v1.2.0")

    def run_cli(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        selected_arguments = list(arguments)
        needs_source = (
            selected_arguments
            and selected_arguments[0] == "bootstrap"
        ) or (
            len(selected_arguments) >= 2
            and selected_arguments[0] == "spec"
            and selected_arguments[1] in {"plan", "sync", "update"}
        )
        manifest_exists = (
            self.repo / "docs" / ".engineering" / "specs.json"
        ).exists()
        if needs_source and not manifest_exists:
            if "--spec-repository" not in selected_arguments:
                selected_arguments.extend(
                    [
                        "--spec-repository",
                        self.catalog_repository.resolve().as_uri(),
                    ]
                )
            if (
                "--spec-ref" not in selected_arguments
                and "--spec-version" not in selected_arguments
            ):
                selected_arguments.extend(["--spec-ref", "main"])
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FOUNDRYCTL),
                "--repo",
                str(self.repo),
                *selected_arguments,
            ],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != expected:
            self.fail(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def run_ep_cli(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(EPCTL),
                "--repo",
                str(self.repo),
                *arguments,
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def test_codex_bootstrap_dry_run_does_not_write(self) -> None:
        payload = json.loads(
            self.run_cli("bootstrap", "--profile", "codex").stdout
        )

        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(
            payload["components"],
            ["engineering-execution-plan"],
        )
        self.assertIn(
            {"action": "create_file", "path": "AGENTS.md"},
            payload["actions"],
        )
        self.assertIn(
            {"action": "register", "path": "docs/design-docs"},
            payload["actions"],
        )
        self.assertEqual(payload["specs"], ["core/semantic-naming"])
        self.assertIn(
            {
                "action": "create_file",
                "path": "docs/.engineering/specs.json",
            },
            payload["actions"],
        )
        self.assertEqual(payload["created"], [])
        self.assertEqual(payload["updated"], [])
        self.assertEqual(list(self.repo.iterdir()), [])

        explicit = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--dry-run",
            ).stdout
        )
        self.assertEqual(explicit, payload)
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_codex_bootstrap_apply_is_idempotent_and_validated(self) -> None:
        first = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            ).stdout
        )

        self.assertEqual(first["mode"], "apply")
        required = (
            "AGENTS.md",
            "ARCHITECTURE.md",
            "docs/index.md",
            "docs/QUALITY_SCORE.md",
            "docs/RELIABILITY.md",
            "docs/SECURITY.md",
            "docs/design-docs/index.md",
        )
        for relative in required:
            self.assertTrue((self.repo / relative).is_file(), relative)
        agents = self.repo / "AGENTS.md"
        self.assertLessEqual(
            len(agents.read_text(encoding="utf-8").splitlines()),
            80,
        )

        manifest = json.loads(
            (
                self.repo / "docs" / ".engineering" / "harness.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["owner"], "repo-foundry")
        self.assertEqual(manifest["profile"], "codex")
        self.assertEqual(
            manifest["instruction_files"],
            [{"path": "AGENTS.md", "max_lines": 100}],
        )
        spec_manifest = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(spec_manifest["owner"], "repo-foundry")
        self.assertEqual(spec_manifest["specs"], ["core/semantic-naming"])
        spec_lock = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.lock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(spec_lock["owner"], "repo-foundry")
        self.assertEqual(
            [item["id"] for item in spec_lock["specs"]],
            ["core/semantic-naming"],
        )
        self.assertEqual(
            spec_lock["catalog"]["resolved_revision"],
            self.catalog_commit,
        )
        self.assertEqual(
            spec_lock["catalog"]["source"],
            {
                "kind": "git",
                "url": self.catalog_repository.resolve().as_uri(),
                "ref": "main",
            },
        )
        self.assertTrue(
            (
                self.repo
                / "docs"
                / "agent-guides"
                / "managed"
                / "core"
                / "semantic-naming.md"
            ).is_file()
        )
        self.assertIn(
            "docs/agent-guides/managed/index.md",
            agents.read_text(encoding="utf-8"),
        )
        config = json.loads(
            (
                self.repo / "docs" / ".epctl" / "config.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("docs/design-docs", config["architecture_roots"])
        self.run_cli("validate", "--harness")
        self.run_cli("spec", "validate")
        self.run_ep_cli("validate")

        before = {
            relative: (self.repo / relative).read_bytes()
            for relative in (
                *required,
                "docs/.engineering/harness.json",
                "docs/.engineering/specs.json",
                "docs/.engineering/specs.lock.json",
                "docs/agent-guides/managed/index.md",
                "docs/agent-guides/managed/core/semantic-naming.md",
                "docs/.epctl/config.json",
            )
        }
        second = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            ).stdout
        )
        after = {
            relative: (self.repo / relative).read_bytes()
            for relative in before
        }

        self.assertEqual(second["created"], [])
        self.assertEqual(second["updated"], [])
        self.assertEqual(after, before)

    def test_legacy_manifest_owners_remain_readable(self) -> None:
        self.run_cli("bootstrap", "--profile", "codex", "--apply")
        state = self.repo / "docs" / ".engineering"
        for name in ("harness.json", "specs.json", "specs.lock.json"):
            path = state / name
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["owner"] = "engineering-workflow"
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        index = (
            self.repo / "docs" / "agent-guides" / "managed" / "index.md"
        )
        index.write_text(
            index.read_text(encoding="utf-8").replace(
                "Generated by repo-foundry",
                "Generated by engineering-workflow",
            ),
            encoding="utf-8",
        )

        validation = self.run_cli("validate", "--harness")
        self.assertIn("HARNESS_LEGACY_OWNER", validation.stderr)
        self.assertIn("SPEC_LEGACY_OWNER", validation.stderr)
        spec_validation = self.run_cli("spec", "validate")
        self.assertIn("SPEC_LEGACY_OWNER", spec_validation.stderr)

        preview = json.loads(
            self.run_cli("bootstrap", "--profile", "codex").stdout
        )
        conflicts = [
            action
            for action in preview["actions"]
            if action["action"] == "conflict"
        ]
        self.assertEqual(conflicts, [])

    def test_codex_bootstrap_preserves_existing_files_at_line_limit(
        self,
    ) -> None:
        self.run_ep_cli("init")
        plans = self.repo / "docs" / "PLANS.md"
        original_plans = (
            plans.read_text(encoding="utf-8") + "\nRepository-owned note.\n"
        )
        plans.write_text(original_plans, encoding="utf-8")
        agents = self.repo / "AGENTS.md"
        original_agents = (
            "$engineering-specs\n"
            "docs/agent-guides/managed/index.md\n"
            + "".join(f"line {number:03d}\n" for number in range(3, 101))
        )
        agents.write_text(original_agents, encoding="utf-8")
        architecture = self.repo / "ARCHITECTURE.md"
        architecture.write_text("# Human architecture\n", encoding="utf-8")

        result = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--apply",
            ).stdout
        )

        self.assertEqual(agents.read_text(encoding="utf-8"), original_agents)
        self.assertEqual(
            architecture.read_text(encoding="utf-8"),
            "# Human architecture\n",
        )
        self.assertEqual(plans.read_text(encoding="utf-8"), original_plans)
        self.assertTrue(
            any(
                "hard limit is 100" in warning
                for warning in result["warnings"]
            )
        )
        self.run_cli("validate", "--harness")

    def test_codex_bootstrap_rejects_101_line_agents_without_writing(
        self,
    ) -> None:
        agents = self.repo / "AGENTS.md"
        agents.write_text(
            "".join(f"line {number:03d}\n" for number in range(1, 102)),
            encoding="utf-8",
        )

        result = self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--apply",
            expected=2,
        )

        self.assertIn("HARNESS_AGENTS_LINE_LIMIT", result.stderr)
        self.assertFalse((self.repo / "docs").exists())
        self.assertEqual(
            len(agents.read_text(encoding="utf-8").splitlines()),
            101,
        )

    def test_harness_validation_rejects_agents_growth(self) -> None:
        self.run_cli("bootstrap", "--profile", "codex", "--apply")
        agents = self.repo / "AGENTS.md"
        agents.write_text(
            "".join(f"line {number:03d}\n" for number in range(1, 102)),
            encoding="utf-8",
        )

        result = self.run_cli("validate", "--harness", expected=1)

        self.assertIn("HARNESS_AGENTS_LINE_LIMIT", result.stderr)
        self.assertIn("actual 101 physical lines", result.stderr)

    def test_harness_validation_can_require_bootstrap(self) -> None:
        self.run_ep_cli("init")

        result = self.run_cli("validate", "--harness", expected=1)

        self.assertIn("HARNESS_MANIFEST_MISSING", result.stderr)

    def test_codex_bootstrap_path_conflict_is_non_destructive(self) -> None:
        docs = self.repo / "docs"
        docs.write_text("reserved by user\n", encoding="utf-8")

        result = self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--apply",
            expected=2,
        )

        self.assertIn("parent is not a directory", result.stderr)
        self.assertEqual(
            docs.read_text(encoding="utf-8"),
            "reserved by user\n",
        )
        self.assertFalse((self.repo / "AGENTS.md").exists())

    def test_spec_detection_recommends_and_explicit_ids_select(self) -> None:
        (self.repo / "go.mod").write_text(
            "module example.test/polyglot\n",
            encoding="utf-8",
        )
        (self.repo / "tsconfig.json").write_text("{}\n", encoding="utf-8")
        (self.repo / "pyproject.toml").write_text(
            "[project]\nname = \"polyglot\"\n",
            encoding="utf-8",
        )

        preview = json.loads(self.run_cli("spec", "plan").stdout)

        optional = [
            "languages/go",
            "languages/typescript",
            "languages/python",
        ]
        expected = [
            "core/semantic-naming",
            *optional,
        ]
        self.assertEqual(
            preview["selected_specs"],
            ["core/semantic-naming"],
        )
        self.assertEqual(
            preview["configured_specs"],
            ["core/semantic-naming"],
        )
        self.assertEqual(
            preview["detected_specs"],
            optional,
        )
        self.assertEqual(preview["recommended_specs"], optional)
        self.assertEqual(
            [item["id"] for item in preview["available_specs"]],
            expected,
        )
        self.assertEqual(list(self.repo.glob("docs/**")), [])

        applied = json.loads(
            self.run_cli(
                "bootstrap",
                "--profile",
                "codex",
                "--spec",
                "languages/go",
                "--spec",
                "languages/typescript",
                "--spec",
                "languages/python",
                "--apply",
            ).stdout
        )
        self.assertEqual(applied["specs"], expected)
        self.assertEqual(applied["configured_specs"], expected)
        self.assertEqual(applied["recommended_specs"], optional)
        lock = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.lock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            [item["id"] for item in lock["specs"]],
            expected,
        )
        for item in lock["specs"]:
            installed = self.repo / item["installed_path"]
            source = self.catalog_repository / item["source_path"]
            self.assertEqual(installed.read_bytes(), source.read_bytes())
        index = (
            self.repo / "docs" / "agent-guides" / "managed" / "index.md"
        ).read_text(encoding="utf-8")
        for spec_id in expected:
            self.assertIn(spec_id, index)
        self.run_cli("spec", "validate")

    def test_spec_sync_and_update_preserve_or_replace_selection(self) -> None:
        (self.repo / "go.mod").write_text(
            "module example.test/update\n",
            encoding="utf-8",
        )
        self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec",
            "languages/go",
            "--apply",
        )
        (self.repo / "tsconfig.json").write_text("{}\n", encoding="utf-8")

        synced = json.loads(
            self.run_cli("spec", "sync", "--apply").stdout
        )
        self.assertEqual(
            synced["selected_specs"],
            ["core/semantic-naming", "languages/go"],
        )
        self.assertIn(
            "languages/typescript",
            synced["detected_specs"],
        )

        preserved = json.loads(self.run_cli("spec", "update").stdout)
        self.assertEqual(
            preserved["selected_specs"],
            ["core/semantic-naming", "languages/go"],
        )
        self.assertIn(
            "languages/typescript",
            preserved["recommended_specs"],
        )
        self.assertNotIn(
            {
                "action": "update_file",
                "path": "docs/.engineering/specs.json",
            },
            preserved["actions"],
        )

        preview = json.loads(
            self.run_cli(
                "spec",
                "update",
                "--spec",
                "languages/go",
                "--spec",
                "languages/typescript",
            ).stdout
        )
        self.assertEqual(
            preview["configured_specs"],
            [
                "core/semantic-naming",
                "languages/go",
                "languages/typescript",
            ],
        )
        self.assertIn(
            {
                "action": "update_file",
                "path": "docs/.engineering/specs.json",
            },
            preview["actions"],
        )
        updated = json.loads(
            self.run_cli(
                "spec",
                "update",
                "--spec",
                "languages/go",
                "--spec",
                "languages/typescript",
                "--apply",
            ).stdout
        )
        self.assertIn(
            "docs/.engineering/specs.json",
            updated["updated"],
        )
        manifest = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["specs"],
            [
                "core/semantic-naming",
                "languages/go",
                "languages/typescript",
            ],
        )
        self.run_cli("spec", "validate")

    def test_required_only_update_removes_locked_managed_copy(self) -> None:
        (self.repo / "go.mod").write_text(
            "module example.test/remove\n",
            encoding="utf-8",
        )
        self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec",
            "languages/go",
            "--apply",
        )
        managed = (
            self.repo
            / "docs"
            / "agent-guides"
            / "managed"
            / "languages"
            / "go.md"
        )
        self.assertTrue(managed.is_file())

        preview = json.loads(
            self.run_cli("spec", "update", "--required-only").stdout
        )
        self.assertEqual(
            preview["configured_specs"],
            ["core/semantic-naming"],
        )
        self.assertIn(
            {
                "action": "remove_file",
                "path": "docs/agent-guides/managed/languages/go.md",
            },
            preview["actions"],
        )

        applied = json.loads(
            self.run_cli(
                "spec",
                "update",
                "--required-only",
                "--apply",
            ).stdout
        )
        self.assertEqual(
            applied["removed"],
            ["docs/agent-guides/managed/languages/go.md"],
        )
        self.assertFalse(managed.exists())
        manifest = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["specs"], ["core/semantic-naming"])
        self.run_cli("spec", "validate")

    def test_deselection_refuses_to_remove_drifted_managed_copy(self) -> None:
        self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec",
            "languages/go",
            "--apply",
        )
        manifest_path = (
            self.repo / "docs" / ".engineering" / "specs.json"
        )
        original_manifest = manifest_path.read_bytes()
        managed = (
            self.repo
            / "docs"
            / "agent-guides"
            / "managed"
            / "languages"
            / "go.md"
        )
        managed.write_text("# repository-owned edit\n", encoding="utf-8")

        result = self.run_cli(
            "spec",
            "update",
            "--required-only",
            "--apply",
            expected=2,
        )

        self.assertIn("SPEC_MANAGED_REMOVAL_DRIFT", result.stderr)
        self.assertEqual(manifest_path.read_bytes(), original_manifest)
        self.assertEqual(
            managed.read_text(encoding="utf-8"),
            "# repository-owned edit\n",
        )

    def test_explicit_selection_rejects_unknown_and_duplicate_ids(self) -> None:
        unknown = self.run_cli(
            "bootstrap",
            "--spec",
            "languages/unknown",
            "--apply",
            expected=2,
        )
        self.assertIn("SPEC_SELECTION_UNKNOWN", unknown.stderr)
        self.assertEqual(list(self.repo.iterdir()), [])

        duplicate = self.run_cli(
            "bootstrap",
            "--spec",
            "languages/go",
            "--spec",
            "languages/go",
            "--apply",
            expected=2,
        )
        self.assertIn("SPEC_SELECTION_DUPLICATE", duplicate.stderr)
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_spec_sync_pins_commit_and_update_moves_to_ref_head(self) -> None:
        (self.repo / "go.mod").write_text(
            "module example.test/pinned\n",
            encoding="utf-8",
        )
        self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec",
            "languages/go",
            "--apply",
        )
        managed = (
            self.repo
            / "docs"
            / "agent-guides"
            / "managed"
            / "languages"
            / "go.md"
        )
        original = managed.read_bytes()
        new_commit = update_go_spec(self.catalog_repository)
        self.assertNotEqual(new_commit, self.catalog_commit)

        sync_preview = json.loads(self.run_cli("spec", "sync").stdout)
        self.assertEqual(
            sync_preview["catalog"]["resolved_revision"],
            self.catalog_commit,
        )
        self.run_cli("spec", "sync", "--apply")
        self.assertEqual(managed.read_bytes(), original)
        locked = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.lock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            locked["catalog"]["resolved_revision"],
            self.catalog_commit,
        )

        update_preview = json.loads(self.run_cli("spec", "update").stdout)
        self.assertEqual(
            update_preview["catalog"]["resolved_revision"],
            new_commit,
        )
        self.assertIn(
            {
                "action": "replace_file",
                "path": "docs/agent-guides/managed/languages/go.md",
            },
            update_preview["actions"],
        )
        self.run_cli("spec", "update", "--apply")
        self.assertEqual(
            managed.read_bytes(),
            (
                self.catalog_repository
                / "specification"
                / "languages"
                / "go.md"
            ).read_bytes(),
        )
        locked = json.loads(
            (
                self.repo / "docs" / ".engineering" / "specs.lock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            locked["catalog"]["resolved_revision"],
            new_commit,
        )

    def test_spec_version_pins_tag_and_explicit_update_changes_release(
        self,
    ) -> None:
        (self.repo / "go.mod").write_text(
            "module example.test/versioned\n",
            encoding="utf-8",
        )
        self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec-version",
            "0.1.0",
            "--apply",
        )
        manifest_path = (
            self.repo / "docs" / ".engineering" / "specs.json"
        )
        lock_path = (
            self.repo / "docs" / ".engineering" / "specs.lock.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        locked = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["catalog"]["ref"],
            "refs/tags/v0.1.0",
        )
        self.assertEqual(
            locked["catalog"]["resolved_revision"],
            self.catalog_commit,
        )

        new_commit = update_go_spec(self.catalog_repository)
        sync = json.loads(self.run_cli("spec", "sync").stdout)
        self.assertEqual(
            sync["catalog"]["resolved_revision"],
            self.catalog_commit,
        )

        preview = json.loads(
            self.run_cli(
                "spec",
                "update",
                "--spec-version",
                "0.2.0",
            ).stdout
        )
        self.assertEqual(
            preview["catalog"]["source"]["ref"],
            "refs/tags/v0.2.0",
        )
        self.assertEqual(
            preview["catalog"]["resolved_revision"],
            new_commit,
        )
        self.assertIn(
            {
                "action": "update_file",
                "path": "docs/.engineering/specs.json",
            },
            preview["actions"],
        )

        self.run_cli(
            "spec",
            "update",
            "--spec-version",
            "0.2.0",
            "--apply",
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        locked = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["catalog"]["ref"],
            "refs/tags/v0.2.0",
        )
        self.assertEqual(
            locked["catalog"]["resolved_revision"],
            new_commit,
        )

    def test_spec_validation_is_offline(self) -> None:
        self.run_cli("bootstrap", "--profile", "codex", "--apply")
        unavailable = self.base / "specification-source-unavailable"
        self.catalog_repository.rename(unavailable)

        self.run_cli("spec", "validate")
        self.run_cli("validate", "--harness")

    def test_unreachable_initial_ref_is_non_destructive(self) -> None:
        result = self.run_cli(
            "spec",
            "plan",
            "--spec-ref",
            "refs/heads/missing",
            expected=2,
        )

        self.assertIn("SPEC_GIT_FETCH_FAILED", result.stderr)
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_invalid_or_ambiguous_version_selector_is_non_destructive(
        self,
    ) -> None:
        invalid = self.run_cli(
            "spec",
            "plan",
            "--spec-version",
            "main",
            expected=2,
        )
        self.assertIn("SPEC_VERSION_INVALID", invalid.stderr)

        ambiguous = self.run_cli(
            "spec",
            "plan",
            "--spec-version",
            "0.1.0",
            "--spec-ref",
            "main",
            expected=2,
        )
        self.assertIn("not allowed with argument", ambiguous.stderr)
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_existing_source_changes_require_explicit_update(self) -> None:
        self.run_cli("bootstrap", "--profile", "codex", "--apply")
        manifest_path = (
            self.repo / "docs" / ".engineering" / "specs.json"
        )
        original = manifest_path.read_bytes()

        sync = self.run_cli(
            "spec",
            "sync",
            "--spec-version",
            "0.1.0",
            expected=2,
        )
        self.assertIn("SPEC_SOURCE_OVERRIDE_REQUIRES_UPDATE", sync.stderr)

        bootstrap = self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec-version",
            "0.1.0",
            expected=2,
        )
        self.assertIn(
            "SPEC_BOOTSTRAP_OVERRIDE_REQUIRES_UPDATE",
            bootstrap.stderr,
        )

        repository_only = self.run_cli(
            "spec",
            "update",
            "--spec-repository",
            self.catalog_repository.resolve().as_uri(),
            expected=2,
        )
        self.assertIn(
            "SPEC_SOURCE_SELECTOR_REQUIRED",
            repository_only.stderr,
        )
        self.assertEqual(manifest_path.read_bytes(), original)

    def test_spec_drift_requires_explicit_sync(self) -> None:
        (self.repo / "go.mod").write_text(
            "module example.test/drift\n",
            encoding="utf-8",
        )
        self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--spec",
            "languages/go",
            "--apply",
        )
        managed = (
            self.repo
            / "docs"
            / "agent-guides"
            / "managed"
            / "languages"
            / "go.md"
        )
        managed.write_text("# locally modified\n", encoding="utf-8")

        bootstrap = self.run_cli(
            "bootstrap",
            "--profile",
            "codex",
            "--apply",
            expected=2,
        )
        self.assertIn("SPEC_MANAGED_CONTENT_DRIFT", bootstrap.stderr)
        self.assertEqual(
            managed.read_text(encoding="utf-8"),
            "# locally modified\n",
        )
        validation = self.run_cli("spec", "validate", expected=1)
        self.assertIn("SPEC_MANAGED_CONTENT_DRIFT", validation.stderr)

        preview = json.loads(self.run_cli("spec", "sync").stdout)
        self.assertIn(
            {
                "action": "replace_file",
                "path": (
                    "docs/agent-guides/managed/languages/go.md"
                ),
            },
            preview["actions"],
        )
        self.run_cli("spec", "sync", "--apply")
        self.assertEqual(
            managed.read_bytes(),
            (
                self.catalog_repository
                / "specification"
                / "languages"
                / "go.md"
            ).read_bytes(),
        )
        self.run_cli("spec", "validate")

    def test_project_spec_is_routed_without_becoming_managed(self) -> None:
        self.run_cli("bootstrap", "--profile", "codex", "--apply")
        project_spec = (
            self.repo / "docs" / "agent-guides" / "handler-pattern.md"
        )
        project_spec.parent.mkdir(parents=True, exist_ok=True)
        original = "# Project Handler Pattern\n"
        project_spec.write_text(original, encoding="utf-8")
        manifest_path = (
            self.repo / "docs" / ".engineering" / "specs.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["project_specs"] = [
            {
                "path": "docs/agent-guides/handler-pattern.md",
                "applies_to": ["internal/http/**"],
                "description": "Project HTTP Handler pattern",
            }
        ]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        self.run_cli("spec", "sync", "--apply")

        index = (
            self.repo / "docs" / "agent-guides" / "managed" / "index.md"
        ).read_text(encoding="utf-8")
        self.assertIn("internal/http/**", index)
        self.assertIn("handler-pattern.md", index)
        self.assertEqual(project_spec.read_text(encoding="utf-8"), original)
        self.run_cli("spec", "validate")

    def test_git_catalog_digest_failure_is_non_destructive(self) -> None:
        (
            self.catalog_repository
            / "specification"
            / "core"
            / "semantic-naming.md"
        ).write_text("# drifted catalog\n", encoding="utf-8")
        commit_all(self.catalog_repository, "commit invalid catalog drift")
        state = self.repo / "docs" / ".engineering"
        state.mkdir(parents=True)
        (state / "specs.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "owner": "repo-foundry",
                    "catalog": {
                        "kind": "git",
                        "url": self.catalog_repository.resolve().as_uri(),
                        "ref": "main",
                    },
                    "specs": ["core/semantic-naming"],
                    "project_specs": [],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli("spec", "plan", expected=2)

        self.assertIn("SPEC_CATALOG_DIGEST_MISMATCH", result.stderr)
        self.assertFalse((state / "specs.lock.json").exists())
        self.assertFalse(
            (self.repo / "docs" / "agent-guides" / "managed").exists()
        )

    def test_execution_plan_cli_does_not_own_harness_commands(self) -> None:
        help_result = subprocess.run(
            [sys.executable, "-B", str(EPCTL), "--help"],
            text=True,
            capture_output=True,
            timeout=30,
        )

        self.assertEqual(help_result.returncode, 0)
        self.assertNotIn("bootstrap", help_result.stdout)
        self.assertNotIn("--harness", help_result.stdout)
        self.assertNotIn(" spec ", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
