#!/usr/bin/env python3
"""Bootstrap and validate the RepoFoundry AI project Harness."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import spec_manager as specctl

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None


SKILL_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = SKILL_DIR / "assets"
EXECUTION_PLAN_CTL = (
    SKILL_DIR / "engineering-execution-plan" / "scripts" / "epctl.py"
)
DEFAULT_SPEC_REPOSITORY = (
    "https://github.com/XiaoWeiKIN/EngineeringSpecifications.git"
)
DEFAULT_SPEC_REF = "main"

HARNESS_VERSION = 1
HARNESS_OWNER = "repo-foundry"
LEGACY_HARNESS_OWNERS = frozenset({"engineering-workflow"})
CODEX_HARNESS_PROFILE = "codex"
CODEX_AGENT_MAX_LINES = 100
CODEX_AGENT_TEMPLATE_TARGET_LINES = 80
BOOTSTRAP_TODO_MARKER = "BOOTSTRAP_TODO"

HARNESS_STATE_DIRECTORY = "docs/.engineering"
HARNESS_MANIFEST = f"{HARNESS_STATE_DIRECTORY}/harness.json"
CODEX_BOOTSTRAP_DIRECTORIES = (
    HARNESS_STATE_DIRECTORY,
    "docs/design-docs",
)
CODEX_BOOTSTRAP_FILE_ASSETS = (
    ("AGENTS.md", "harness-agents.md"),
    ("ARCHITECTURE.md", "harness-architecture.md"),
    ("docs/index.md", "harness-docs-index.md"),
    ("docs/QUALITY_SCORE.md", "harness-quality-score.md"),
    ("docs/RELIABILITY.md", "harness-reliability.md"),
    ("docs/SECURITY.md", "harness-security.md"),
    ("docs/design-docs/index.md", "harness-design-docs-index.md"),
)
CODEX_REQUIRED_FILES = tuple(
    relative for relative, _ in CODEX_BOOTSTRAP_FILE_ASSETS
)


class FoundryctlError(RuntimeError):
    pass


def spec_source(repository: str, ref: str) -> dict[str, str]:
    return {
        "kind": "git",
        "url": repository,
        "ref": ref,
    }


def normalize_repo(value: str) -> Path:
    repo = Path(value).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        raise FoundryctlError(
            f"Repository directory does not exist: {repo}"
        )
    return repo


def load_execution_plan_ctl() -> ModuleType:
    if not EXECUTION_PLAN_CTL.is_file():
        raise FoundryctlError(
            "Bundled engineering-execution-plan component is missing: "
            f"{EXECUTION_PLAN_CTL}"
        )
    spec = importlib.util.spec_from_file_location(
        "_repo_foundry_epctl",
        EXECUTION_PLAN_CTL,
    )
    if spec is None or spec.loader is None:
        raise FoundryctlError(
            f"Unable to load engineering-execution-plan: {EXECUTION_PLAN_CTL}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for attribute in (
        "INIT_DIRECTORIES",
        "INIT_FILE_ASSETS",
        "config_path",
        "init_repo",
        "load_config",
        "repo_lock",
        "save_config",
    ):
        if not hasattr(module, attribute):
            raise FoundryctlError(
                "engineering-execution-plan component does not expose "
                f"the required bootstrap contract: {attribute}"
            )
    return module


def reject_symlink_path(repo: Path, path: Path) -> None:
    try:
        relative = path.relative_to(repo)
    except ValueError as exc:
        raise FoundryctlError(
            f"Managed path escapes repository: {path}"
        ) from exc
    current = repo
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise FoundryctlError(
                f"Refusing to manage symbolic link: {current}"
            )


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    try:
        os.replace(temp_name, path)
        if hasattr(os, "O_DIRECTORY"):
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def asset_text(name: str) -> str:
    path = ASSET_DIR / name
    if not path.is_file():
        raise FoundryctlError(f"Missing bundled asset: {path}")
    return path.read_text(encoding="utf-8")


def ensure_file(path: Path, asset: str) -> bool:
    if path.exists():
        return False
    atomic_write(path, asset_text(asset))
    return True


@contextlib.contextmanager
def repo_lock(repo: Path):
    lock_path = repo / HARNESS_STATE_DIRECTORY / "lock"
    reject_symlink_path(repo, lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:  # pragma: no cover - Windows
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write("\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:  # pragma: no cover - Windows
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def harness_path(repo: Path) -> Path:
    return repo / HARNESS_MANIFEST


def codex_harness_manifest() -> dict[str, object]:
    return {
        "version": HARNESS_VERSION,
        "owner": HARNESS_OWNER,
        "profile": CODEX_HARNESS_PROFILE,
        "components": ["engineering-execution-plan"],
        "instruction_files": [
            {
                "path": "AGENTS.md",
                "max_lines": CODEX_AGENT_MAX_LINES,
            }
        ],
        "required_files": list(CODEX_REQUIRED_FILES),
    }


def load_codex_harness_manifest(repo: Path) -> dict[str, object]:
    path = harness_path(repo)
    if not path.exists():
        raise FoundryctlError(
            f"HARNESS_MANIFEST_MISSING: {path}: "
            "run foundryctl bootstrap --profile codex --apply"
        )
    reject_symlink_path(repo, path)
    if not path.is_file():
        raise FoundryctlError(
            f"HARNESS_MANIFEST_INVALID: {path}: expected a regular file"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FoundryctlError(
            f"HARNESS_MANIFEST_INVALID: {path}: {exc}"
        ) from exc
    owner = data.get("owner") if isinstance(data, dict) else None
    supported_owners = {HARNESS_OWNER, *LEGACY_HARNESS_OWNERS}
    normalized = dict(data) if isinstance(data, dict) else {}
    normalized["owner"] = HARNESS_OWNER
    if owner not in supported_owners or normalized != codex_harness_manifest():
        raise FoundryctlError(
            f"HARNESS_MANIFEST_INVALID: {path}: expected Codex Harness "
            f"schema version {HARNESS_VERSION} owned by {HARNESS_OWNER} "
            f"with AGENTS.md max_lines {CODEX_AGENT_MAX_LINES}"
        )
    return data


def physical_line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def managed_path_conflict(
    repo: Path,
    path: Path,
    expected: str,
) -> str:
    try:
        relative = path.relative_to(repo)
    except ValueError:
        return "path escapes repository"
    current = repo
    for component in relative.parts[:-1]:
        current = current / component
        if current.is_symlink():
            return f"parent is a symbolic link: {current.relative_to(repo)}"
        if current.exists() and not current.is_dir():
            return f"parent is not a directory: {current.relative_to(repo)}"
    if path.is_symlink():
        return "symbolic links are not supported"
    if path.exists():
        if expected == "directory" and not path.is_dir():
            return "expected a directory"
        if expected == "file" and not path.is_file():
            return "expected a regular file"
    return ""


def execution_plan_contract(
    epctl: ModuleType,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    directories = tuple(str(item) for item in epctl.INIT_DIRECTORIES)
    files = tuple(
        str(relative) for relative, _ in epctl.INIT_FILE_ASSETS
    ) + ("docs/.epctl/state.json",)
    return directories, files


def bootstrap_plan(
    repo: Path,
    profile: str,
    initial_spec_source: dict[str, str],
) -> dict[str, object]:
    if profile != CODEX_HARNESS_PROFILE:
        raise FoundryctlError(
            f"Unsupported bootstrap profile {profile!r}; "
            f"supported profiles: {CODEX_HARNESS_PROFILE}"
        )

    epctl = load_execution_plan_ctl()
    ep_directories, ep_files = execution_plan_contract(epctl)
    actions: list[dict[str, object]] = []
    warnings: list[str] = []

    directories = tuple(
        dict.fromkeys((*ep_directories, *CODEX_BOOTSTRAP_DIRECTORIES))
    )
    for relative in directories:
        path = repo / relative
        reason = managed_path_conflict(repo, path, "directory")
        if reason:
            actions.append(
                {
                    "action": "conflict",
                    "path": relative,
                    "reason": reason,
                }
            )
        elif path.is_dir():
            actions.append({"action": "preserve", "path": relative + "/"})
        else:
            actions.append(
                {"action": "create_directory", "path": relative + "/"}
            )

    expected_files = (
        *ep_files,
        *(relative for relative, _ in CODEX_BOOTSTRAP_FILE_ASSETS),
    )
    for relative in expected_files:
        path = repo / relative
        reason = managed_path_conflict(repo, path, "file")
        if not reason and relative == "AGENTS.md" and path.is_file():
            line_count = physical_line_count(path)
            if line_count > CODEX_AGENT_MAX_LINES:
                reason = (
                    f"HARNESS_AGENTS_LINE_LIMIT: actual {line_count} physical "
                    f"lines; required <= {CODEX_AGENT_MAX_LINES}"
                )
            elif line_count > CODEX_AGENT_TEMPLATE_TARGET_LINES:
                warnings.append(
                    f"HARNESS_AGENTS_LINE_BUDGET: AGENTS.md: actual "
                    f"{line_count} physical lines; hard limit is "
                    f"{CODEX_AGENT_MAX_LINES}"
                )
        if reason:
            actions.append(
                {
                    "action": "conflict",
                    "path": relative,
                    "reason": reason,
                }
            )
        elif path.is_file():
            actions.append({"action": "preserve", "path": relative})
        else:
            actions.append({"action": "create_file", "path": relative})

    manifest = harness_path(repo)
    reason = managed_path_conflict(repo, manifest, "file")
    if not reason and manifest.is_file():
        try:
            load_codex_harness_manifest(repo)
        except FoundryctlError as exc:
            reason = str(exc)
    if reason:
        actions.append(
            {
                "action": "conflict",
                "path": HARNESS_MANIFEST,
                "reason": reason,
            }
        )
    elif manifest.is_file():
        actions.append({"action": "preserve", "path": HARNESS_MANIFEST})
    else:
        actions.append({"action": "create_file", "path": HARNESS_MANIFEST})

    config = epctl.config_path(repo)
    reason = managed_path_conflict(repo, config, "file")
    roots: list[str] = []
    if not reason:
        try:
            loaded_config = epctl.load_config(repo)
            loaded_roots = loaded_config["architecture_roots"]
            if not isinstance(loaded_roots, list):
                raise FoundryctlError(
                    "engineering-execution-plan returned an invalid "
                    "architecture_roots contract"
                )
            roots = [str(item) for item in loaded_roots]
        except Exception as exc:
            reason = str(exc)
    if reason:
        actions.append(
            {
                "action": "conflict",
                "path": config.relative_to(repo).as_posix(),
                "reason": reason,
            }
        )
    elif "docs/design-docs" in roots:
        actions.append(
            {
                "action": "preserve",
                "path": config.relative_to(repo).as_posix(),
            }
        )
    else:
        actions.append({"action": "register", "path": "docs/design-docs"})

    selected_specs: list[str] = []
    try:
        spec_plan = specctl.plan_spec_state(
            repo,
            initial_spec_source,
            operation="sync",
            allow_replace=False,
        )
    except specctl.SpecError as exc:
        actions.append(
            {
                "action": "conflict",
                "path": specctl.SPEC_MANIFEST,
                "reason": str(exc),
            }
        )
    else:
        actions.extend(spec_plan.actions)
        warnings.extend(spec_plan.warnings)
        selected_specs.extend(spec_plan.selected_spec_ids)

    return {
        "profile": profile,
        "components": ["engineering-execution-plan"],
        "specs": selected_specs,
        "actions": actions,
        "warnings": warnings,
    }


def validate_codex_harness(
    repo: Path,
    *,
    require_manifest: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = harness_path(repo)
    if not path.exists():
        if require_manifest:
            errors.append(
                f"HARNESS_MANIFEST_MISSING: {path}: "
                "run foundryctl bootstrap --profile codex --apply"
            )
        return errors, warnings
    try:
        manifest = load_codex_harness_manifest(repo)
    except FoundryctlError as exc:
        return [str(exc)], warnings
    if manifest["owner"] in LEGACY_HARNESS_OWNERS:
        warnings.append(
            f"HARNESS_LEGACY_OWNER: {HARNESS_MANIFEST}: "
            f"{manifest['owner']!r} remains readable; new manifests use "
            f"{HARNESS_OWNER!r}"
        )

    required_files = manifest["required_files"]
    if not isinstance(required_files, list):
        return [f"HARNESS_MANIFEST_INVALID: {path}: required_files"], warnings
    for relative in required_files:
        if not isinstance(relative, str):
            errors.append(
                f"HARNESS_MANIFEST_INVALID: {path}: non-string required file"
            )
            continue
        target = repo / relative
        reason = managed_path_conflict(repo, target, "file")
        if reason:
            errors.append(
                f"HARNESS_REQUIRED_FILE_INVALID: {relative}: {reason}"
            )
            continue
        if not target.is_file():
            errors.append(
                f"HARNESS_REQUIRED_FILE_MISSING: {relative}: "
                "run foundryctl bootstrap --profile codex --apply"
            )
            continue
        todo_count = target.read_text(encoding="utf-8").count(
            BOOTSTRAP_TODO_MARKER
        )
        if todo_count:
            warnings.append(
                f"HARNESS_BOOTSTRAP_TODO: {relative}: "
                f"{todo_count} bootstrap TODO marker(s) remain"
            )

    instruction_files = manifest["instruction_files"]
    if not isinstance(instruction_files, list):
        return [
            f"HARNESS_MANIFEST_INVALID: {path}: instruction_files"
        ], warnings
    for item in instruction_files:
        if not isinstance(item, dict):
            errors.append(
                f"HARNESS_MANIFEST_INVALID: {path}: instruction file entry"
            )
            continue
        relative = item.get("path")
        maximum = item.get("max_lines")
        if not isinstance(relative, str) or not isinstance(maximum, int):
            errors.append(
                f"HARNESS_MANIFEST_INVALID: {path}: instruction file contract"
            )
            continue
        target = repo / relative
        if not target.is_file() or target.is_symlink():
            continue
        actual = physical_line_count(target)
        if actual > maximum:
            errors.append(
                f"HARNESS_AGENTS_LINE_LIMIT: {relative}: actual {actual} "
                f"physical lines; required <= {maximum}"
            )
        elif actual > CODEX_AGENT_TEMPLATE_TARGET_LINES:
            warnings.append(
                f"HARNESS_AGENTS_LINE_BUDGET: {relative}: actual {actual} "
                f"physical lines; hard limit is {maximum}"
            )

    try:
        epctl = load_execution_plan_ctl()
        roots = epctl.load_config(repo)["architecture_roots"]
        if not isinstance(roots, list):
            raise FoundryctlError("architecture_roots is not a list")
    except Exception as exc:
        errors.append(f"HARNESS_ARCHITECTURE_ROOT_INVALID: {exc}")
    else:
        if "docs/design-docs" not in roots:
            errors.append(
                "HARNESS_ARCHITECTURE_ROOT_MISSING: docs/design-docs: "
                "run foundryctl bootstrap --profile codex --apply"
            )
    spec_errors, spec_warnings = specctl.validate_spec_state(
        repo,
        require_manifest=False,
    )
    errors.extend(spec_errors)
    warnings.extend(spec_warnings)
    return errors, warnings


def bootstrap_repo(
    repo: Path,
    profile: str,
    *,
    apply_changes: bool,
    initial_spec_source: dict[str, str],
) -> dict[str, object]:
    planned = bootstrap_plan(repo, profile, initial_spec_source)
    actions = planned["actions"]
    if not isinstance(actions, list):
        raise FoundryctlError("Bootstrap plan returned invalid actions")
    conflicts = [
        action
        for action in actions
        if isinstance(action, dict) and action.get("action") == "conflict"
    ]
    payload: dict[str, object] = {
        "profile": profile,
        "mode": "apply" if apply_changes else "dry-run",
        "components": list(planned["components"]),
        "specs": list(planned["specs"]),
        "actions": actions,
        "warnings": list(planned["warnings"]),
        "created": [],
        "updated": [],
    }
    if not apply_changes:
        return payload
    if conflicts:
        details = "; ".join(
            f"{item.get('path')}: {item.get('reason')}" for item in conflicts
        )
        raise FoundryctlError(
            f"Bootstrap preflight failed: {details}"
        )

    epctl = load_execution_plan_ctl()
    created: list[str] = []
    updated: list[str] = []
    harness_state_existed = (repo / HARNESS_STATE_DIRECTORY).is_dir()
    with repo_lock(repo):
        second_plan = bootstrap_plan(repo, profile, initial_spec_source)
        second_actions = second_plan["actions"]
        if not isinstance(second_actions, list):
            raise FoundryctlError(
                "Bootstrap locked plan returned invalid actions"
            )
        second_conflicts = [
            action
            for action in second_actions
            if isinstance(action, dict) and action.get("action") == "conflict"
        ]
        if second_conflicts:
            details = "; ".join(
                f"{item.get('path')}: {item.get('reason')}"
                for item in second_conflicts
            )
            raise FoundryctlError(
                f"Bootstrap preflight changed while locking: {details}"
            )

        if not harness_state_existed:
            created.append(HARNESS_STATE_DIRECTORY + "/")
        try:
            with epctl.repo_lock(repo):
                created.extend(epctl.init_repo(repo))
                for relative in CODEX_BOOTSTRAP_DIRECTORIES:
                    directory = repo / relative
                    reject_symlink_path(repo, directory)
                    if not directory.exists():
                        directory.mkdir(parents=True)
                        created.append(relative + "/")
                for relative, asset in CODEX_BOOTSTRAP_FILE_ASSETS:
                    target = repo / relative
                    reject_symlink_path(repo, target)
                    if ensure_file(target, asset):
                        created.append(relative)

                manifest = harness_path(repo)
                reject_symlink_path(repo, manifest)
                if not manifest.exists():
                    atomic_write(
                        manifest,
                        json.dumps(
                            codex_harness_manifest(),
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                    )
                    created.append(HARNESS_MANIFEST)

                config = epctl.config_path(repo)
                config_existed = config.exists()
                loaded_config = epctl.load_config(repo)
                roots = loaded_config["architecture_roots"]
                if not isinstance(roots, list):
                    raise FoundryctlError(
                        "engineering-execution-plan returned invalid "
                        "architecture_roots"
                    )
                if "docs/design-docs" not in roots:
                    roots.append("docs/design-docs")
                    epctl.save_config(repo, loaded_config)
                    if config_existed:
                        updated.append(config.relative_to(repo).as_posix())
                    else:
                        created.append(config.relative_to(repo).as_posix())

                spec_plan = specctl.plan_spec_state(
                    repo,
                    initial_spec_source,
                    operation="sync",
                    allow_replace=False,
                )
                spec_created, spec_updated = specctl.apply_spec_plan(
                    repo,
                    spec_plan,
                )
                created.extend(spec_created)
                updated.extend(spec_updated)
        except FoundryctlError:
            raise
        except specctl.SpecError as exc:
            raise FoundryctlError(str(exc)) from exc
        except Exception as exc:
            raise FoundryctlError(
                f"engineering-execution-plan initialization failed: {exc}"
            ) from exc

    harness_errors, harness_warnings = validate_codex_harness(
        repo,
        require_manifest=True,
    )
    if harness_errors:
        raise FoundryctlError(
            "Bootstrap Harness validation failed: "
            + "; ".join(harness_errors)
        )
    payload["warnings"] = list(
        dict.fromkeys(
            [
                *list(planned["warnings"]),
                *harness_warnings,
            ]
        )
    )
    payload["created"] = list(dict.fromkeys(created))
    payload["updated"] = list(dict.fromkeys(updated))
    return payload


def manage_specs(
    repo: Path,
    operation: str,
    *,
    apply_changes: bool,
    initial_spec_source: dict[str, str],
) -> dict[str, object]:
    try:
        planned = specctl.plan_spec_state(
            repo,
            initial_spec_source,
            operation=operation,
            allow_replace=True,
        )
    except specctl.SpecError as exc:
        raise FoundryctlError(str(exc)) from exc
    if planned.conflicts:
        details = "; ".join(
            f"{item.get('path')}: {item.get('reason')}"
            for item in planned.conflicts
        )
        if apply_changes:
            raise FoundryctlError(f"Spec preflight failed: {details}")
    if not apply_changes:
        return specctl.plan_payload(planned, mode="dry-run")

    with repo_lock(repo):
        try:
            locked_plan = specctl.plan_spec_state(
                repo,
                initial_spec_source,
                operation=operation,
                allow_replace=True,
            )
        except specctl.SpecError as exc:
            raise FoundryctlError(str(exc)) from exc
        if locked_plan != planned:
            raise FoundryctlError(
                "Spec preflight changed while acquiring the Harness lock; "
                "rerun the dry-run"
            )
        try:
            created, updated = specctl.apply_spec_plan(repo, locked_plan)
        except specctl.SpecError as exc:
            raise FoundryctlError(str(exc)) from exc

    errors, validation_warnings = specctl.validate_spec_state(
        repo,
        require_manifest=True,
    )
    if errors:
        raise FoundryctlError(
            "Spec validation failed after apply: " + "; ".join(errors)
        )
    payload = specctl.plan_payload(
        planned,
        mode="apply",
        created=created,
        updated=updated,
    )
    payload["warnings"] = list(
        dict.fromkeys(
            [
                *list(planned.warnings),
                *validation_warnings,
            ]
        )
    )
    return payload


def add_spec_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--spec-repository",
        default=DEFAULT_SPEC_REPOSITORY,
        help=(
            "Initial Git specification repository when specs.json is absent "
            f"(default: {DEFAULT_SPEC_REPOSITORY})"
        ),
    )
    parser.add_argument(
        "--spec-ref",
        default=DEFAULT_SPEC_REF,
        help=(
            "Initial Git branch, tag, or commit when specs.json is absent "
            f"(default: {DEFAULT_SPEC_REF})"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Target repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser(
        "bootstrap",
        help="Preview or create an Agent-first project documentation Harness",
    )
    bootstrap.add_argument(
        "--profile",
        choices=(CODEX_HARNESS_PROFILE,),
        default=CODEX_HARNESS_PROFILE,
    )
    add_spec_source_arguments(bootstrap)
    bootstrap_mode = bootstrap.add_mutually_exclusive_group()
    bootstrap_mode.add_argument(
        "--apply",
        action="store_true",
        help="Create only missing paths after a conflict-free preflight",
    )
    bootstrap_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without writing; this is the default",
    )

    validate_parser = sub.add_parser(
        "validate",
        help="Validate the RepoFoundry AI project Harness",
    )
    validate_parser.add_argument(
        "--harness",
        action="store_true",
        help="Require a bootstrapped Harness manifest",
    )

    spec_parser = sub.add_parser(
        "spec",
        help="Plan, synchronize, update, or validate Engineering Specs",
    )
    spec_commands = spec_parser.add_subparsers(
        dest="spec_command",
        required=True,
    )
    plan_parser = spec_commands.add_parser(
        "plan",
        help="Preview the current or inferred Spec selection",
    )
    add_spec_source_arguments(plan_parser)
    for command, help_text in (
        ("sync", "Materialize the explicit Spec selection"),
        (
            "update",
            "Add newly detected languages and refresh selected Specs",
        ),
    ):
        command_parser = spec_commands.add_parser(command, help=help_text)
        add_spec_source_arguments(command_parser)
        command_mode = command_parser.add_mutually_exclusive_group()
        command_mode.add_argument(
            "--apply",
            action="store_true",
            help="Apply the conflict-free preview",
        )
        command_mode.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview actions without writing; this is the default",
        )
    spec_commands.add_parser(
        "validate",
        help="Validate the Spec manifest, lock, local content, and routing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = normalize_repo(args.repo)
        if args.command == "bootstrap":
            print(
                json.dumps(
                    bootstrap_repo(
                        repo,
                        args.profile,
                        apply_changes=args.apply,
                        initial_spec_source=spec_source(
                            args.spec_repository,
                            args.spec_ref,
                        ),
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "validate":
            errors, warnings = validate_codex_harness(
                repo,
                require_manifest=args.harness,
            )
            for warning in warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            print(
                json.dumps(
                    {"errors": len(errors), "warnings": len(warnings)},
                    ensure_ascii=False,
                )
            )
            return 1 if errors else 0
        elif args.command == "spec":
            if args.spec_command == "validate":
                errors, warnings = specctl.validate_spec_state(
                    repo,
                    require_manifest=True,
                )
                for warning in warnings:
                    print(f"WARNING: {warning}", file=sys.stderr)
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                print(
                    json.dumps(
                        {"errors": len(errors), "warnings": len(warnings)},
                        ensure_ascii=False,
                    )
                )
                return 1 if errors else 0
            operation = (
                "plan"
                if args.spec_command == "plan"
                else args.spec_command
            )
            apply_changes = bool(
                args.spec_command != "plan" and args.apply
            )
            print(
                json.dumps(
                    manage_specs(
                        repo,
                        operation,
                        apply_changes=apply_changes,
                        initial_spec_source=spec_source(
                            args.spec_repository,
                            args.spec_ref,
                        ),
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:  # pragma: no cover - argparse guarantees a command
            raise FoundryctlError(f"Unknown command: {args.command}")
    except FoundryctlError as exc:
        print(f"foundryctl: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
