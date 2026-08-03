#!/usr/bin/env python3
"""Bootstrap and validate the RepoFoundry AI project Harness."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
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
VERSION_FILE = SKILL_DIR / "VERSION"
EXECUTION_PLAN_CTL = (
    SKILL_DIR / "engineering-execution-plan" / "scripts" / "epctl.py"
)
DEFAULT_SPEC_REPOSITORY = (
    "https://github.com/XiaoWeiKIN/EngineeringSpecifications.git"
)
DEFAULT_SPEC_VERSION = "1.2.0"

LEGACY_HARNESS_SCHEMA_VERSION = 1
HARNESS_SCHEMA_VERSION = 2
HARNESS_OWNER = "repo-foundry"
LEGACY_HARNESS_OWNERS = frozenset({"engineering-workflow"})
CODEX_HARNESS_PROFILE = "codex"
CODEX_HARNESS_PROFILE_VERSION = "1.0.0"
CODEX_AGENT_MAX_LINES = 100
CODEX_AGENT_TEMPLATE_TARGET_LINES = 80
BOOTSTRAP_TODO_MARKER = "BOOTSTRAP_TODO"
LEGACY_UNVERSIONED = "legacy-unversioned"
HARNESS_V1_TO_V2_MIGRATION = "harness-schema-v1-to-v2"

HARNESS_STATE_DIRECTORY = "docs/.engineering"
HARNESS_MANIFEST = f"{HARNESS_STATE_DIRECTORY}/harness.json"
CODEX_BOOTSTRAP_DIRECTORIES = (
    HARNESS_STATE_DIRECTORY,
    "docs/design-docs",
    ".agents/skills/engineering-specs/agents",
    ".agents/skills/engineering-specs/scripts",
    ".codex",
)
CODEX_DOCUMENT_FILE_ASSETS = (
    ("AGENTS.md", "harness-agents.md"),
    ("ARCHITECTURE.md", "harness-architecture.md"),
    ("docs/index.md", "harness-docs-index.md"),
    ("docs/QUALITY_SCORE.md", "harness-quality-score.md"),
    ("docs/RELIABILITY.md", "harness-reliability.md"),
    ("docs/SECURITY.md", "harness-security.md"),
    ("docs/design-docs/index.md", "harness-design-docs-index.md"),
)
CODEX_ROUTER_FILE_ASSETS = (
    (
        ".agents/skills/engineering-specs/SKILL.md",
        "engineering-specs-router/SKILL.md",
    ),
    (
        ".agents/skills/engineering-specs/agents/openai.yaml",
        "engineering-specs-router/agents/openai.yaml",
    ),
    (
        ".agents/skills/engineering-specs/scripts/spec_router.py",
        "engineering-specs-router/scripts/spec_router.py",
    ),
    (".codex/hooks.json", "harness-hooks.json"),
)
CODEX_BOOTSTRAP_FILE_ASSETS = (
    *CODEX_DOCUMENT_FILE_ASSETS,
    *CODEX_ROUTER_FILE_ASSETS,
)
CODEX_TEMPLATE_IDS = {
    "AGENTS.md": "codex/agents",
    "ARCHITECTURE.md": "codex/architecture",
    "docs/index.md": "codex/docs-index",
    "docs/QUALITY_SCORE.md": "codex/quality-score",
    "docs/RELIABILITY.md": "codex/reliability",
    "docs/SECURITY.md": "codex/security",
    "docs/design-docs/index.md": "codex/design-docs-index",
    ".agents/skills/engineering-specs/SKILL.md": (
        "codex/engineering-specs-router-skill"
    ),
    ".agents/skills/engineering-specs/agents/openai.yaml": (
        "codex/engineering-specs-router-agent"
    ),
    ".agents/skills/engineering-specs/scripts/spec_router.py": (
        "codex/engineering-specs-router-script"
    ),
    ".codex/hooks.json": "codex/engineering-specs-hooks",
}
CODEX_REQUIRED_FILES = tuple(
    relative for relative, _ in CODEX_DOCUMENT_FILE_ASSETS
)
CODEX_SEEDED_FILES = tuple(
    relative for relative, _ in CODEX_BOOTSTRAP_FILE_ASSETS
)
CODEX_GENERATED_FILES = frozenset(
    relative for relative, _ in CODEX_ROUTER_FILE_ASSETS
)
CODEX_ROUTER_SKILL_FILES = frozenset(
    relative
    for relative, _ in CODEX_ROUTER_FILE_ASSETS
    if relative != ".codex/hooks.json"
)
CODEX_HOOKS_FILE = ".codex/hooks.json"
CODEX_ROUTER_SCRIPT = (
    ".agents/skills/engineering-specs/scripts/spec_router.py"
)
CODEX_ROUTER_COMMAND_FRAGMENT = (
    ".agents/skills/engineering-specs/scripts/spec_router.py\" hook"
)
CODEX_ROUTER_AGENTS_ROUTES = (
    "$engineering-specs",
    "docs/agent-guides/managed/index.md",
)
CODEX_REQUIRED_HOOK_EVENTS = (
    "UserPromptSubmit",
    "SubagentStart",
    "PreToolUse",
    "Stop",
)


class FoundryctlError(RuntimeError):
    pass


def distribution_version() -> str:
    if not VERSION_FILE.is_file():
        raise FoundryctlError(
            f"RepoFoundry VERSION file is missing: {VERSION_FILE}"
        )
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not specctl.SEMVER_RE.fullmatch(value):
        raise FoundryctlError(
            "RepoFoundry VERSION must use MAJOR.MINOR.PATCH"
        )
    return value


REPO_FOUNDRY_VERSION = distribution_version()


def semver_tuple(value: str, label: str) -> tuple[int, int, int]:
    if not specctl.SEMVER_RE.fullmatch(value):
        raise FoundryctlError(f"{label}: expected MAJOR.MINOR.PATCH")
    major, minor, patch = (int(part) for part in value.split("."))
    return major, minor, patch


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def spec_source(
    repository: str,
    *,
    version: str | None,
    ref: str | None,
    use_default_version: bool = True,
) -> dict[str, str] | None:
    if version is not None and ref is not None:
        raise FoundryctlError(
            "--spec-version and --spec-ref are mutually exclusive"
        )
    if version is None and ref is None:
        if not use_default_version:
            return None
        version = DEFAULT_SPEC_VERSION
    try:
        selected_ref = specctl.release_ref(version) if version else ref
    except specctl.SpecError as exc:
        raise FoundryctlError(str(exc)) from exc
    if selected_ref is None:  # pragma: no cover - guarded above
        raise FoundryctlError("A Specification version or ref is required")
    return {
        "kind": "git",
        "url": repository,
        "ref": selected_ref,
    }


def selected_spec_repository(
    repo: Path,
    requested: str | None,
    *,
    preserve_manifest_source: bool,
) -> str:
    if requested is not None:
        return requested
    manifest = repo / specctl.SPEC_MANIFEST
    if preserve_manifest_source and manifest.exists():
        try:
            return specctl.parse_manifest(manifest).catalog["url"]
        except specctl.SpecError as exc:
            raise FoundryctlError(str(exc)) from exc
    return DEFAULT_SPEC_REPOSITORY


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


def router_asset_by_target(relative: str) -> str | None:
    for target, asset in CODEX_ROUTER_FILE_ASSETS:
        if target == relative:
            return asset
    return None


def validate_hook_config_data(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["HARNESS_SPEC_HOOKS_INVALID: expected a JSON object"]
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return ["HARNESS_SPEC_HOOKS_INVALID: hooks must be an object"]
    for event in CODEX_REQUIRED_HOOK_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list) or not groups:
            errors.append(
                f"HARNESS_SPEC_HOOK_MISSING: {event}: add the RepoFoundry "
                "Engineering Spec Hook group"
            )
            continue
        matched = False
        for group in groups:
            if not isinstance(group, dict):
                continue
            if event == "PreToolUse":
                matcher = group.get("matcher")
                if not isinstance(matcher, str) or not all(
                    value in matcher for value in ("Bash", "apply_patch")
                ):
                    continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict):
                    continue
                if (
                    handler.get("type") == "command"
                    and isinstance(handler.get("command"), str)
                    and CODEX_ROUTER_COMMAND_FRAGMENT in handler["command"]
                ):
                    matched = True
                    break
            if matched:
                break
        if not matched:
            errors.append(
                f"HARNESS_SPEC_HOOK_MISSING: {event}: no command handler "
                f"routes to {CODEX_ROUTER_SCRIPT}"
            )
    return errors


def validate_hook_config_file(repo: Path) -> list[str]:
    path = repo / CODEX_HOOKS_FILE
    reason = managed_path_conflict(repo, path, "file")
    if reason:
        return [f"HARNESS_SPEC_HOOKS_INVALID: {CODEX_HOOKS_FILE}: {reason}"]
    if not path.is_file():
        return [
            f"HARNESS_SPEC_HOOKS_MISSING: {CODEX_HOOKS_FILE}: rerun "
            "foundryctl bootstrap --profile codex --apply"
        ]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"HARNESS_SPEC_HOOKS_INVALID: {CODEX_HOOKS_FILE}: {exc}"]
    return validate_hook_config_data(data)


def validate_spec_router(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for relative in sorted(CODEX_ROUTER_SKILL_FILES):
        target = repo / relative
        reason = managed_path_conflict(repo, target, "file")
        if reason:
            errors.append(
                f"HARNESS_SPEC_ROUTER_INVALID: {relative}: {reason}"
            )
            continue
        if not target.is_file():
            errors.append(
                f"HARNESS_SPEC_ROUTER_MISSING: {relative}: rerun "
                "foundryctl bootstrap --profile codex --apply"
            )
            continue
        asset = router_asset_by_target(relative)
        if asset is None:  # pragma: no cover - constant contract
            errors.append(f"HARNESS_SPEC_ROUTER_INVALID: {relative}: no asset")
            continue
        try:
            actual = target.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(
                f"HARNESS_SPEC_ROUTER_INVALID: {relative}: {exc}"
            )
            continue
        if actual != asset_text(asset):
            errors.append(
                f"HARNESS_SPEC_ROUTER_DRIFT: {relative}: generated Router "
                "bytes differ from this RepoFoundry release"
            )
    errors.extend(validate_hook_config_file(repo))
    agents = repo / "AGENTS.md"
    if not agents.is_file() or agents.is_symlink():
        errors.append(
            "HARNESS_SPEC_ROUTE_MISSING: AGENTS.md: expected a non-symlink "
            "regular file"
        )
    else:
        try:
            text = agents.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"HARNESS_SPEC_ROUTE_INVALID: AGENTS.md: {exc}")
        else:
            missing = [
                value for value in CODEX_ROUTER_AGENTS_ROUTES if value not in text
            ]
            if missing:
                errors.append(
                    "HARNESS_SPEC_ROUTE_MISSING: AGENTS.md: add the mandatory "
                    "Router route for " + ", ".join(missing)
                )
    return errors, warnings


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


def legacy_codex_harness_manifest(
    *,
    owner: str = HARNESS_OWNER,
) -> dict[str, object]:
    """Return the schema-v1 contract kept only for compatibility checks."""
    return {
        "version": LEGACY_HARNESS_SCHEMA_VERSION,
        "owner": owner,
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


def codex_file_record(
    relative: str,
    asset: str,
    *,
    installed_path: Path | None = None,
) -> dict[str, object]:
    template_digest = sha256_text(asset_text(asset))
    if (
        installed_path is None
        or (
            installed_path.is_file()
            and not installed_path.is_symlink()
            and sha256_file(installed_path) == template_digest
        )
    ):
        return {
            "path": relative,
            "ownership": "seeded",
            "template_id": CODEX_TEMPLATE_IDS[relative],
            "template_version": CODEX_HARNESS_PROFILE_VERSION,
            "template_sha256": template_digest,
            "installed_sha256": template_digest,
        }
    return {
        "path": relative,
        "ownership": "seeded",
        "template_id": CODEX_TEMPLATE_IDS[relative],
        "template_version": LEGACY_UNVERSIONED,
        "template_sha256": None,
        "installed_sha256": None,
    }


def codex_harness_manifest(
    repo: Path | None = None,
    *,
    applied_migrations: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    assets = dict(CODEX_BOOTSTRAP_FILE_ASSETS)
    return {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "owner": HARNESS_OWNER,
        "producer": {
            "name": HARNESS_OWNER,
            "version": REPO_FOUNDRY_VERSION,
        },
        "profile": {
            "id": CODEX_HARNESS_PROFILE,
            "version": CODEX_HARNESS_PROFILE_VERSION,
        },
        "components": ["engineering-execution-plan"],
        "instruction_files": [
            {
                "path": "AGENTS.md",
                "max_lines": CODEX_AGENT_MAX_LINES,
            }
        ],
        "required_files": list(CODEX_REQUIRED_FILES),
        "files": [
            codex_file_record(
                relative,
                assets[relative],
                installed_path=(repo / relative) if repo else None,
            )
            for relative in CODEX_SEEDED_FILES
        ],
        "applied_migrations": list(applied_migrations or []),
    }


def harness_schema_version(data: dict[str, object]) -> int:
    if "schema_version" in data:
        value = data["schema_version"]
    elif "version" in data:
        value = data["version"]
    else:
        raise FoundryctlError(
            "Harness manifest does not declare schema_version"
        )
    if not isinstance(value, int) or isinstance(value, bool):
        raise FoundryctlError("Harness schema version must be an integer")
    return value


def validate_codex_harness_manifest_data(
    path: Path,
    data: object,
) -> dict[str, object]:
    prefix = f"HARNESS_MANIFEST_INVALID: {path}:"
    if not isinstance(data, dict):
        raise FoundryctlError(f"{prefix} expected a JSON object")
    try:
        schema_version = harness_schema_version(data)
    except FoundryctlError as exc:
        raise FoundryctlError(f"{prefix} {exc}") from exc
    supported_owners = {HARNESS_OWNER, *LEGACY_HARNESS_OWNERS}

    if schema_version == LEGACY_HARNESS_SCHEMA_VERSION:
        owner = data.get("owner")
        if owner not in supported_owners:
            raise FoundryctlError(f"{prefix} unsupported owner {owner!r}")
        if data != legacy_codex_harness_manifest(owner=str(owner)):
            raise FoundryctlError(
                f"{prefix} expected the Codex Harness schema version 1 "
                f"contract with AGENTS.md max_lines "
                f"{CODEX_AGENT_MAX_LINES}"
            )
        return data

    if schema_version > HARNESS_SCHEMA_VERSION:
        raise FoundryctlError(
            f"HARNESS_SCHEMA_TOO_NEW: {path}: schema {schema_version}; "
            f"this RepoFoundry supports up to {HARNESS_SCHEMA_VERSION}"
        )
    if schema_version != HARNESS_SCHEMA_VERSION:
        raise FoundryctlError(
            f"{prefix} unsupported schema version {schema_version}"
        )

    expected_keys = {
        "schema_version",
        "owner",
        "producer",
        "profile",
        "components",
        "instruction_files",
        "required_files",
        "files",
        "applied_migrations",
    }
    if set(data) != expected_keys:
        raise FoundryctlError(
            f"{prefix} schema 2 keys must be "
            + ", ".join(sorted(expected_keys))
        )
    owner = data["owner"]
    if owner not in supported_owners:
        raise FoundryctlError(f"{prefix} unsupported owner {owner!r}")

    producer = data["producer"]
    if not isinstance(producer, dict) or set(producer) != {
        "name",
        "version",
    }:
        raise FoundryctlError(f"{prefix} producer contract")
    if producer["name"] not in supported_owners:
        raise FoundryctlError(
            f"{prefix} unsupported producer {producer['name']!r}"
        )
    producer_version = producer["version"]
    if not isinstance(producer_version, str):
        raise FoundryctlError(f"{prefix} producer.version")
    try:
        parsed_producer = semver_tuple(
            producer_version,
            "producer.version",
        )
    except FoundryctlError as exc:
        raise FoundryctlError(f"{prefix} {exc}") from exc
    if parsed_producer > semver_tuple(
        REPO_FOUNDRY_VERSION,
        "RepoFoundry version",
    ):
        raise FoundryctlError(
            f"HARNESS_PRODUCER_TOO_NEW: {path}: produced by "
            f"RepoFoundry {producer_version}; installed version is "
            f"{REPO_FOUNDRY_VERSION}"
        )

    profile = data["profile"]
    if not isinstance(profile, dict) or set(profile) != {"id", "version"}:
        raise FoundryctlError(f"{prefix} profile contract")
    if profile["id"] != CODEX_HARNESS_PROFILE:
        raise FoundryctlError(
            f"{prefix} unsupported profile {profile['id']!r}"
        )
    profile_version = profile["version"]
    if not isinstance(profile_version, str):
        raise FoundryctlError(f"{prefix} profile.version")
    try:
        parsed_profile = semver_tuple(profile_version, "profile.version")
    except FoundryctlError as exc:
        raise FoundryctlError(f"{prefix} {exc}") from exc
    if parsed_profile > semver_tuple(
        CODEX_HARNESS_PROFILE_VERSION,
        "Codex profile version",
    ):
        raise FoundryctlError(
            f"HARNESS_PROFILE_TOO_NEW: {path}: Codex profile "
            f"{profile_version}; installed profile is "
            f"{CODEX_HARNESS_PROFILE_VERSION}"
        )

    expected_static = codex_harness_manifest()
    for key in ("components", "instruction_files", "required_files"):
        if data[key] != expected_static[key]:
            raise FoundryctlError(f"{prefix} {key} contract")

    files = data["files"]
    if not isinstance(files, list):
        raise FoundryctlError(f"{prefix} files contract")
    file_paths = [
        item.get("path") if isinstance(item, dict) else None
        for item in files
    ]
    if any(not isinstance(relative, str) for relative in file_paths):
        raise FoundryctlError(f"{prefix} files path contract")
    if (
        len(set(file_paths)) != len(file_paths)
        or any(relative not in CODEX_SEEDED_FILES for relative in file_paths)
        or file_paths
        != [
            relative
            for relative in CODEX_SEEDED_FILES
            if relative in file_paths
        ]
        or any(relative not in file_paths for relative in CODEX_REQUIRED_FILES)
        or (
            parsed_profile
            == semver_tuple(
                CODEX_HARNESS_PROFILE_VERSION,
                "Codex profile version",
            )
            and file_paths != list(CODEX_SEEDED_FILES)
        )
    ):
        raise FoundryctlError(f"{prefix} files path contract")
    assets = dict(CODEX_BOOTSTRAP_FILE_ASSETS)
    for index, item in enumerate(files):
        label = f"files[{index}]"
        if not isinstance(item, dict) or set(item) != {
            "path",
            "ownership",
            "template_id",
            "template_version",
            "template_sha256",
            "installed_sha256",
        }:
            raise FoundryctlError(f"{prefix} {label} contract")
        relative = item["path"]
        assert isinstance(relative, str)
        if item["ownership"] != "seeded":
            raise FoundryctlError(f"{prefix} {label}.ownership")
        if item["template_id"] != CODEX_TEMPLATE_IDS[relative]:
            raise FoundryctlError(f"{prefix} {label}.template_id")
        template_version = item["template_version"]
        template_digest = item["template_sha256"]
        installed_digest = item["installed_sha256"]
        if template_version == LEGACY_UNVERSIONED:
            if template_digest is not None or installed_digest is not None:
                raise FoundryctlError(
                    f"{prefix} {label}: legacy-unversioned hashes must be null"
                )
            continue
        if not isinstance(template_version, str):
            raise FoundryctlError(f"{prefix} {label}.template_version")
        try:
            parsed_template = semver_tuple(
                template_version,
                f"{label}.template_version",
            )
        except FoundryctlError as exc:
            raise FoundryctlError(f"{prefix} {exc}") from exc
        if parsed_template > semver_tuple(
            CODEX_HARNESS_PROFILE_VERSION,
            "Codex profile version",
        ):
            raise FoundryctlError(
                f"HARNESS_TEMPLATE_TOO_NEW: {path}: {relative} uses "
                f"template {template_version}"
            )
        if (
            not isinstance(template_digest, str)
            or not specctl.SHA256_RE.fullmatch(template_digest)
            or not isinstance(installed_digest, str)
            or not specctl.SHA256_RE.fullmatch(installed_digest)
        ):
            raise FoundryctlError(
                f"{prefix} {label}: expected lowercase SHA-256 hashes"
            )
        if template_version == CODEX_HARNESS_PROFILE_VERSION:
            current_digest = sha256_text(asset_text(assets[relative]))
            if template_digest != current_digest:
                raise FoundryctlError(
                    f"{prefix} {label}.template_sha256 does not match "
                    "the installed RepoFoundry template"
                )

    migrations = data["applied_migrations"]
    if not isinstance(migrations, list):
        raise FoundryctlError(f"{prefix} applied_migrations contract")
    seen_migrations: set[str] = set()
    for index, migration in enumerate(migrations):
        label = f"applied_migrations[{index}]"
        if not isinstance(migration, dict) or set(migration) != {
            "id",
            "kind",
            "from",
            "to",
            "applied_by_version",
        }:
            raise FoundryctlError(f"{prefix} {label} contract")
        if not all(
            isinstance(migration[key], str) and migration[key]
            for key in migration
        ):
            raise FoundryctlError(f"{prefix} {label} values")
        migration_id = migration["id"]
        if migration_id in seen_migrations:
            raise FoundryctlError(f"{prefix} duplicate migration {migration_id}")
        seen_migrations.add(migration_id)
        try:
            applied_by = semver_tuple(
                migration["applied_by_version"],
                f"{label}.applied_by_version",
            )
        except FoundryctlError as exc:
            raise FoundryctlError(f"{prefix} {exc}") from exc
        if applied_by > semver_tuple(
            REPO_FOUNDRY_VERSION,
            "RepoFoundry version",
        ):
            raise FoundryctlError(
                f"HARNESS_MIGRATION_TOO_NEW: {path}: {migration_id}"
            )
    return data


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
    return validate_codex_harness_manifest_data(path, data)


def harness_manifest_warnings(
    manifest: dict[str, object],
) -> list[str]:
    warnings: list[str] = []
    owner = manifest["owner"]
    if owner in LEGACY_HARNESS_OWNERS:
        warnings.append(
            f"HARNESS_LEGACY_OWNER: {HARNESS_MANIFEST}: {owner!r} remains "
            f"readable; upgrade rewrites it as {HARNESS_OWNER!r}"
        )
    schema = harness_schema_version(manifest)
    if schema == LEGACY_HARNESS_SCHEMA_VERSION:
        warnings.append(
            f"HARNESS_SCHEMA_UPGRADE_AVAILABLE: {HARNESS_MANIFEST}: "
            f"schema 1 remains readable; preview `foundryctl --repo . "
            f"upgrade --to {REPO_FOUNDRY_VERSION}`"
        )
        return warnings

    producer = manifest["producer"]
    profile = manifest["profile"]
    assert isinstance(producer, dict)
    assert isinstance(profile, dict)
    if producer["version"] != REPO_FOUNDRY_VERSION:
        warnings.append(
            f"HARNESS_PRODUCT_UPGRADE_AVAILABLE: {HARNESS_MANIFEST}: "
            f"{producer['version']} -> {REPO_FOUNDRY_VERSION}"
        )
    if profile["version"] != CODEX_HARNESS_PROFILE_VERSION:
        warnings.append(
            f"HARNESS_PROFILE_UPGRADE_AVAILABLE: {HARNESS_MANIFEST}: "
            f"{profile['version']} -> {CODEX_HARNESS_PROFILE_VERSION}"
        )
    files = manifest["files"]
    assert isinstance(files, list)
    legacy_paths = [
        str(item["path"])
        for item in files
        if isinstance(item, dict)
        and item.get("template_version") == LEGACY_UNVERSIONED
    ]
    if legacy_paths:
        warnings.append(
            "HARNESS_CUSTOMIZED_SEEDS_PRESERVED: template provenance is "
            "unknown for " + ", ".join(legacy_paths)
        )
    return warnings


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
    requested_spec_ids: tuple[str, ...] | None,
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
            if not reason:
                try:
                    agents_text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    reason = f"HARNESS_SPEC_ROUTE_INVALID: {exc}"
                else:
                    missing_routes = [
                        value
                        for value in CODEX_ROUTER_AGENTS_ROUTES
                        if value not in agents_text
                    ]
                    if missing_routes:
                        reason = (
                            "HARNESS_SPEC_ROUTE_MISSING: add the mandatory "
                            "Router route for " + ", ".join(missing_routes)
                        )
        if not reason and relative in CODEX_ROUTER_SKILL_FILES and path.is_file():
            asset = router_asset_by_target(relative)
            try:
                current_router_text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                reason = f"HARNESS_SPEC_ROUTER_INVALID: {exc}"
            if (
                not reason
                and (
                    asset is None
                    or current_router_text != asset_text(asset)
                )
            ):
                reason = (
                    "HARNESS_SPEC_ROUTER_DRIFT: generated Router bytes differ "
                    "from this RepoFoundry release"
                )
        if not reason and relative == CODEX_HOOKS_FILE and path.is_file():
            hook_errors = validate_hook_config_file(repo)
            if hook_errors:
                reason = (
                    "; ".join(hook_errors)
                    + "; preserve existing Hooks and merge the RepoFoundry "
                    "groups explicitly"
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
            loaded_manifest = load_codex_harness_manifest(repo)
        except FoundryctlError as exc:
            reason = str(exc)
        else:
            warnings.extend(harness_manifest_warnings(loaded_manifest))
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
    configured_specs: list[str] = []
    required_specs: list[str] = []
    recommended_specs: list[str] = []
    available_specs: list[dict[str, object]] = []
    try:
        spec_plan = specctl.plan_spec_state(
            repo,
            initial_spec_source,
            operation="sync",
            allow_replace=False,
            requested_spec_ids=requested_spec_ids,
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
        spec_payload = specctl.plan_payload(spec_plan, mode="dry-run")
        configured_specs.extend(spec_payload["configured_specs"])
        required_specs.extend(spec_payload["required_specs"])
        recommended_specs.extend(spec_payload["recommended_specs"])
        available_specs.extend(spec_payload["available_specs"])

    return {
        "profile": profile,
        "components": ["engineering-execution-plan"],
        "specs": selected_specs,
        "configured_specs": configured_specs,
        "required_specs": required_specs,
        "recommended_specs": recommended_specs,
        "available_specs": available_specs,
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
    warnings.extend(harness_manifest_warnings(manifest))

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
    router_errors, router_warnings = validate_spec_router(repo)
    errors.extend(router_errors)
    warnings.extend(router_warnings)
    return errors, warnings


def migration_record(
    migration_id: str,
    kind: str,
    from_value: str,
    to_value: str,
) -> dict[str, str]:
    return {
        "id": migration_id,
        "kind": kind,
        "from": from_value,
        "to": to_value,
        "applied_by_version": REPO_FOUNDRY_VERSION,
    }


def append_migration(
    manifest: dict[str, object],
    migration: dict[str, str],
) -> None:
    migrations = manifest["applied_migrations"]
    if not isinstance(migrations, list):  # pragma: no cover - validated
        raise FoundryctlError("Harness applied_migrations is invalid")
    if not any(
        isinstance(item, dict) and item.get("id") == migration["id"]
        for item in migrations
    ):
        migrations.append(migration)


def plan_harness_upgrade(
    repo: Path,
    target_version: str,
) -> tuple[
    dict[str, object],
    dict[str, str],
    dict[str, object],
    bool,
]:
    try:
        semver_tuple(target_version, "--to")
    except FoundryctlError as exc:
        raise FoundryctlError(f"UPGRADE_TARGET_INVALID: {exc}") from exc
    if target_version != REPO_FOUNDRY_VERSION:
        raise FoundryctlError(
            f"UPGRADE_TARGET_UNAVAILABLE: installed RepoFoundry contains "
            f"only migration target {REPO_FOUNDRY_VERSION}; requested "
            f"{target_version}"
        )

    manifest = load_codex_harness_manifest(repo)
    schema = harness_schema_version(manifest)
    actions: list[dict[str, object]] = []
    warnings: list[str] = []
    file_writes: dict[str, str] = {}
    assets = dict(CODEX_BOOTSTRAP_FILE_ASSETS)

    conflict_paths: set[str] = set()
    for relative in CODEX_SEEDED_FILES:
        target = repo / relative
        reason = managed_path_conflict(repo, target, "file")
        if (
            not reason
            and relative in CODEX_REQUIRED_FILES
            and not target.is_file()
        ):
            reason = "required seeded file is missing"
        if reason:
            conflict_paths.add(relative)
            actions.append(
                {"action": "conflict", "path": relative, "reason": reason}
            )

    if schema == LEGACY_HARNESS_SCHEMA_VERSION:
        candidate = codex_harness_manifest(
            repo,
            applied_migrations=[
                migration_record(
                    HARNESS_V1_TO_V2_MIGRATION,
                    "schema",
                    "1",
                    str(HARNESS_SCHEMA_VERSION),
                )
            ],
        )
        records = candidate["files"]
        assert isinstance(records, list)
        for record in records:
            assert isinstance(record, dict)
            relative = str(record["path"])
            if relative in conflict_paths:
                continue
            if relative in CODEX_GENERATED_FILES:
                if record["template_version"] == LEGACY_UNVERSIONED:
                    target = repo / relative
                    if not target.exists():
                        file_writes[relative] = asset_text(assets[relative])
                        record.clear()
                        record.update(
                            codex_file_record(relative, assets[relative])
                        )
                        actions.append(
                            {
                                "action": "create_file",
                                "path": relative,
                                "reason": "new generated profile seed",
                            }
                        )
                    else:
                        conflict_paths.add(relative)
                        actions.append(
                            {
                                "action": "conflict",
                                "path": relative,
                                "reason": (
                                    "generated profile path differs from "
                                    "the bundled seed; merge explicitly"
                                ),
                            }
                        )
                else:
                    actions.append(
                        {
                            "action": "record_provenance",
                            "path": relative,
                            "template_version": (
                                CODEX_HARNESS_PROFILE_VERSION
                            ),
                        }
                    )
                continue
            if record["template_version"] == LEGACY_UNVERSIONED:
                actions.append(
                    {
                        "action": "preserve",
                        "path": relative,
                        "reason": "legacy file differs from the current seed",
                    }
                )
                warnings.append(
                    f"HARNESS_CUSTOMIZED_SEED_PRESERVED: {relative}: "
                    "template provenance is unknown; future upgrades will "
                    "not overwrite it automatically"
                )
            else:
                actions.append(
                    {
                        "action": "record_provenance",
                        "path": relative,
                        "template_version": CODEX_HARNESS_PROFILE_VERSION,
                    }
                )
        actions.append(
            {
                "action": "update_manifest",
                "path": HARNESS_MANIFEST,
                "from_schema": LEGACY_HARNESS_SCHEMA_VERSION,
                "to_schema": HARNESS_SCHEMA_VERSION,
            }
        )
        from_state: dict[str, object] = {
            "distribution": LEGACY_UNVERSIONED,
            "schema": LEGACY_HARNESS_SCHEMA_VERSION,
            "profile": f"{CODEX_HARNESS_PROFILE}@{LEGACY_UNVERSIONED}",
        }
    else:
        candidate = json.loads(json.dumps(manifest))
        producer = manifest["producer"]
        profile = manifest["profile"]
        records = candidate["files"]
        assert isinstance(producer, dict)
        assert isinstance(profile, dict)
        assert isinstance(records, list)
        from_state = {
            "distribution": producer["version"],
            "schema": schema,
            "profile": (
                f"{profile['id']}@{profile['version']}"
            ),
        }
        old_profile_version = str(profile["version"])
        changed_templates = False
        records_by_path = {
            str(record["path"]): record
            for record in records
            if isinstance(record, dict)
        }
        next_records: list[dict[str, object]] = []
        for relative in CODEX_SEEDED_FILES:
            target = repo / relative
            record = records_by_path.get(relative)
            current_record = codex_file_record(relative, assets[relative])
            current_digest = str(current_record["template_sha256"])
            if relative in conflict_paths:
                next_records.append(
                    record
                    if record is not None
                    else codex_file_record(
                        relative,
                        assets[relative],
                        installed_path=target,
                    )
                )
                continue

            if record is None:
                changed_templates = True
                if not target.exists() and relative in CODEX_GENERATED_FILES:
                    file_writes[relative] = asset_text(assets[relative])
                    next_records.append(current_record)
                    actions.append(
                        {
                            "action": "create_file",
                            "path": relative,
                            "reason": "new generated profile seed",
                        }
                    )
                    continue
                inferred = codex_file_record(
                    relative,
                    assets[relative],
                    installed_path=target,
                )
                if inferred["template_version"] != LEGACY_UNVERSIONED:
                    next_records.append(inferred)
                    actions.append(
                        {
                            "action": "update_metadata",
                            "path": relative,
                            "template_version": (
                                CODEX_HARNESS_PROFILE_VERSION
                            ),
                        }
                    )
                elif relative in CODEX_GENERATED_FILES:
                    conflict_paths.add(relative)
                    next_records.append(inferred)
                    actions.append(
                        {
                            "action": "conflict",
                            "path": relative,
                            "reason": (
                                "generated profile path differs from the "
                                "bundled seed; merge explicitly"
                            ),
                        }
                    )
                else:
                    next_records.append(inferred)
                    actions.append(
                        {
                            "action": "preserve",
                            "path": relative,
                            "reason": "customized seed has no safe base",
                        }
                    )
                    warnings.append(
                        f"HARNESS_CUSTOMIZED_SEED_PRESERVED: {relative}: "
                        "manual reconciliation is required to adopt the "
                        "current template"
                    )
                continue

            if not target.is_file() or target.is_symlink():
                if not target.exists() and relative in CODEX_GENERATED_FILES:
                    file_writes[relative] = asset_text(assets[relative])
                    next_records.append(current_record)
                    changed_templates = True
                    actions.append(
                        {
                            "action": "create_file",
                            "path": relative,
                            "reason": "restore generated profile seed",
                        }
                    )
                else:
                    next_records.append(record)
                continue

            actual_digest = sha256_file(target)
            template_version = record["template_version"]
            if template_version == CODEX_HARNESS_PROFILE_VERSION:
                if (
                    relative in CODEX_GENERATED_FILES
                    and actual_digest != current_digest
                ):
                    conflict_paths.add(relative)
                    actions.append(
                        {
                            "action": "conflict",
                            "path": relative,
                            "reason": (
                                "generated profile bytes drifted from the "
                                "current template"
                            ),
                        }
                    )
                next_records.append(record)
                continue
            if template_version == LEGACY_UNVERSIONED:
                if actual_digest == current_digest:
                    record.clear()
                    record.update(current_record)
                    changed_templates = True
                    actions.append(
                        {
                            "action": "update_metadata",
                            "path": relative,
                            "template_version": (
                                CODEX_HARNESS_PROFILE_VERSION
                            ),
                        }
                    )
                    next_records.append(record)
                elif relative in CODEX_GENERATED_FILES:
                    conflict_paths.add(relative)
                    next_records.append(record)
                    actions.append(
                        {
                            "action": "conflict",
                            "path": relative,
                            "reason": (
                                "generated profile path has unknown "
                                "provenance; merge explicitly"
                            ),
                        }
                    )
                else:
                    next_records.append(record)
                    actions.append(
                        {
                            "action": "preserve",
                            "path": relative,
                            "reason": "customized seed has no safe base",
                        }
                    )
                    warnings.append(
                        f"HARNESS_CUSTOMIZED_SEED_PRESERVED: {relative}: "
                        "manual reconciliation is required to adopt the "
                        "current template"
                    )
                continue

            installed_digest = record["installed_sha256"]
            if actual_digest == current_digest:
                record.clear()
                record.update(current_record)
                changed_templates = True
                actions.append(
                    {
                        "action": "update_metadata",
                        "path": relative,
                        "template_version": CODEX_HARNESS_PROFILE_VERSION,
                    }
                )
                next_records.append(record)
            elif actual_digest == installed_digest:
                file_writes[relative] = asset_text(assets[relative])
                record.clear()
                record.update(current_record)
                changed_templates = True
                actions.append(
                    {
                        "action": "replace_file",
                        "path": relative,
                        "reason": "seed is unchanged from its recorded base",
                        "template_version": CODEX_HARNESS_PROFILE_VERSION,
                    }
                )
                next_records.append(record)
            else:
                conflict_paths.add(relative)
                next_records.append(record)
                actions.append(
                    {
                        "action": "conflict",
                        "path": relative,
                        "reason": (
                            "file changed since its recorded template was "
                            "installed; merge manually"
                        ),
                    }
                )

        candidate["files"] = next_records

        candidate["owner"] = HARNESS_OWNER
        candidate_producer = candidate["producer"]
        candidate_profile = candidate["profile"]
        assert isinstance(candidate_producer, dict)
        assert isinstance(candidate_profile, dict)
        candidate_producer["name"] = HARNESS_OWNER
        candidate_producer["version"] = REPO_FOUNDRY_VERSION
        candidate_profile["id"] = CODEX_HARNESS_PROFILE
        candidate_profile["version"] = CODEX_HARNESS_PROFILE_VERSION
        if old_profile_version != CODEX_HARNESS_PROFILE_VERSION:
            append_migration(
                candidate,
                migration_record(
                    (
                        f"codex-profile-{old_profile_version}-to-"
                        f"{CODEX_HARNESS_PROFILE_VERSION}"
                    ),
                    "profile",
                    old_profile_version,
                    CODEX_HARNESS_PROFILE_VERSION,
                ),
            )
        elif changed_templates:
            append_migration(
                candidate,
                migration_record(
                    f"codex-templates-to-{CODEX_HARNESS_PROFILE_VERSION}",
                    "templates",
                    "mixed",
                    CODEX_HARNESS_PROFILE_VERSION,
                ),
            )
        if candidate != manifest:
            actions.append(
                {
                    "action": "update_manifest",
                    "path": HARNESS_MANIFEST,
                    "from_schema": schema,
                    "to_schema": HARNESS_SCHEMA_VERSION,
                }
            )

    write_manifest = candidate != manifest
    payload: dict[str, object] = {
        "mode": "dry-run",
        "from": from_state,
        "to": {
            "distribution": target_version,
            "schema": HARNESS_SCHEMA_VERSION,
            "profile": (
                f"{CODEX_HARNESS_PROFILE}@"
                f"{CODEX_HARNESS_PROFILE_VERSION}"
            ),
        },
        "actions": actions,
        "warnings": list(dict.fromkeys(warnings)),
        "created": [],
        "updated": [],
    }
    return payload, file_writes, candidate, write_manifest


def upgrade_harness(
    repo: Path,
    target_version: str,
    *,
    apply_changes: bool,
) -> dict[str, object]:
    planned, file_writes, candidate, write_manifest = plan_harness_upgrade(
        repo,
        target_version,
    )
    conflicts = [
        item
        for item in planned["actions"]
        if isinstance(item, dict) and item.get("action") == "conflict"
    ]
    if not apply_changes:
        return planned
    if conflicts:
        details = "; ".join(
            f"{item.get('path')}: {item.get('reason')}"
            for item in conflicts
        )
        raise FoundryctlError(f"Harness upgrade preflight failed: {details}")

    created: list[str] = []
    updated: list[str] = []
    with repo_lock(repo):
        locked = plan_harness_upgrade(repo, target_version)
        if locked != (planned, file_writes, candidate, write_manifest):
            raise FoundryctlError(
                "Harness upgrade preflight changed while acquiring the "
                "lock; rerun the dry-run"
            )
        touched = [*(repo / relative for relative in file_writes)]
        manifest_path = harness_path(repo)
        if write_manifest:
            touched.append(manifest_path)
        originals: dict[Path, str | None] = {
            path: (
                path.read_text(encoding="utf-8")
                if path.exists()
                else None
            )
            for path in touched
        }
        try:
            for relative, content in file_writes.items():
                target = repo / relative
                existed = target.exists()
                reject_symlink_path(repo, target)
                atomic_write(target, content)
                if existed:
                    updated.append(relative)
                else:
                    created.append(relative)
            if write_manifest:
                reject_symlink_path(repo, manifest_path)
                atomic_write(
                    manifest_path,
                    json.dumps(
                        candidate,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                )
                updated.append(HARNESS_MANIFEST)
            errors, validation_warnings = validate_codex_harness(
                repo,
                require_manifest=True,
            )
            if errors:
                raise FoundryctlError(
                    "Harness validation failed after upgrade: "
                    + "; ".join(errors)
                )
        except Exception as exc:
            rollback_errors: list[str] = []
            for path, content in originals.items():
                try:
                    if content is None:
                        if path.exists():
                            path.unlink()
                    else:
                        atomic_write(path, content)
                except Exception as rollback_exc:  # pragma: no cover
                    rollback_errors.append(f"{path}: {rollback_exc}")
            if rollback_errors:
                raise FoundryctlError(
                    f"{exc}; rollback also failed: "
                    + "; ".join(rollback_errors)
                ) from exc
            if isinstance(exc, FoundryctlError):
                raise
            raise FoundryctlError(f"Harness upgrade failed: {exc}") from exc

    result = dict(planned)
    result["mode"] = "apply"
    result["created"] = created
    result["updated"] = updated
    result["warnings"] = list(
        dict.fromkeys(
            [*list(planned["warnings"]), *validation_warnings]
        )
    )
    return result


def bootstrap_repo(
    repo: Path,
    profile: str,
    *,
    apply_changes: bool,
    initial_spec_source: dict[str, str],
    requested_spec_ids: tuple[str, ...] | None,
) -> dict[str, object]:
    planned = bootstrap_plan(
        repo,
        profile,
        initial_spec_source,
        requested_spec_ids,
    )
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
        "configured_specs": list(planned["configured_specs"]),
        "required_specs": list(planned["required_specs"]),
        "recommended_specs": list(planned["recommended_specs"]),
        "available_specs": list(planned["available_specs"]),
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
        second_plan = bootstrap_plan(
            repo,
            profile,
            initial_spec_source,
            requested_spec_ids,
        )
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
                            codex_harness_manifest(repo),
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
                    requested_spec_ids=requested_spec_ids,
                )
                spec_created, spec_updated, spec_removed = (
                    specctl.apply_spec_plan(repo, spec_plan)
                )
                created.extend(spec_created)
                updated.extend(spec_updated)
                if spec_removed:
                    raise FoundryctlError(
                        "Bootstrap unexpectedly planned Spec removals"
                    )
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
    update_spec_source: dict[str, str] | None,
    requested_spec_ids: tuple[str, ...] | None,
) -> dict[str, object]:
    try:
        planned = specctl.plan_spec_state(
            repo,
            initial_spec_source,
            operation=operation,
            allow_replace=True,
            update_source=update_spec_source,
            requested_spec_ids=requested_spec_ids,
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
                update_source=update_spec_source,
                requested_spec_ids=requested_spec_ids,
            )
        except specctl.SpecError as exc:
            raise FoundryctlError(str(exc)) from exc
        if locked_plan != planned:
            raise FoundryctlError(
                "Spec preflight changed while acquiring the Harness lock; "
                "rerun the dry-run"
            )
        try:
            created, updated, removed = specctl.apply_spec_plan(
                repo,
                locked_plan,
            )
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
        removed=removed,
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
        help=(
            "Initial Git specification repository when specs.json is absent "
            f"(default: {DEFAULT_SPEC_REPOSITORY})"
        ),
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--spec-version",
        help=(
            "Released Catalog version MAJOR.MINOR.PATCH; normalized to "
            "refs/tags/vMAJOR.MINOR.PATCH "
            f"(initial default: {DEFAULT_SPEC_VERSION})"
        ),
    )
    source.add_argument(
        "--spec-ref",
        help=(
            "Explicit development Git branch, tag, or commit; production "
            "use should select --spec-version"
        ),
    )


def add_spec_selection_arguments(parser: argparse.ArgumentParser) -> None:
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--spec",
        dest="spec_ids",
        action="append",
        metavar="ID",
        help=(
            "Select an optional Specification by stable ID; repeat to set "
            "the complete desired optional direct selection"
        ),
    )
    selection.add_argument(
        "--required-only",
        action="store_true",
        help="Select no optional Specifications; required Specs remain",
    )


def requested_spec_ids(args: argparse.Namespace) -> tuple[str, ...] | None:
    if getattr(args, "required_only", False):
        return ()
    values = getattr(args, "spec_ids", None)
    return tuple(values) if values is not None else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        action="version",
        version=f"RepoFoundry AI {REPO_FOUNDRY_VERSION}",
    )
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
    add_spec_selection_arguments(bootstrap)
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

    upgrade_parser = sub.add_parser(
        "upgrade",
        help="Preview or apply a versioned Harness migration",
    )
    upgrade_parser.add_argument(
        "--to",
        required=True,
        metavar="VERSION",
        help=(
            "Target RepoFoundry release bundled with this installation "
            f"(available: {REPO_FOUNDRY_VERSION})"
        ),
    )
    upgrade_mode = upgrade_parser.add_mutually_exclusive_group()
    upgrade_mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the conflict-free migration after a locked recheck",
    )
    upgrade_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without writing; this is the default",
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
            "Replace explicit selection or refresh selected Specs",
        ),
    ):
        command_parser = spec_commands.add_parser(command, help=help_text)
        add_spec_source_arguments(command_parser)
        if command == "update":
            add_spec_selection_arguments(command_parser)
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
            selection = requested_spec_ids(args)
            source_override = any(
                value is not None
                for value in (
                    args.spec_repository,
                    args.spec_version,
                    args.spec_ref,
                )
            )
            if (
                (repo / specctl.SPEC_MANIFEST).exists()
                and (source_override or selection is not None)
            ):
                raise FoundryctlError(
                    "SPEC_BOOTSTRAP_OVERRIDE_REQUIRES_UPDATE: specs.json "
                    "already exists; use spec update to change source or "
                    "selection"
                )
            initial_source = spec_source(
                selected_spec_repository(
                    repo,
                    args.spec_repository,
                    preserve_manifest_source=False,
                ),
                version=args.spec_version,
                ref=args.spec_ref,
            )
            if initial_source is None:  # pragma: no cover - default enabled
                raise FoundryctlError("Initial Spec source is missing")
            print(
                json.dumps(
                    bootstrap_repo(
                        repo,
                        args.profile,
                        apply_changes=args.apply,
                        initial_spec_source=initial_source,
                        requested_spec_ids=selection,
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
        elif args.command == "upgrade":
            print(
                json.dumps(
                    upgrade_harness(
                        repo,
                        args.to,
                        apply_changes=args.apply,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "spec":
            if args.spec_command == "validate":
                errors, warnings = specctl.validate_spec_state(
                    repo,
                    require_manifest=True,
                )
                if harness_path(repo).exists():
                    router_errors, router_warnings = validate_spec_router(repo)
                    errors.extend(router_errors)
                    warnings.extend(router_warnings)
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
            selection = (
                requested_spec_ids(args)
                if operation == "update"
                else None
            )
            manifest_exists = (repo / specctl.SPEC_MANIFEST).exists()
            source_override = any(
                value is not None
                for value in (
                    args.spec_repository,
                    args.spec_version,
                    args.spec_ref,
                )
            )
            if (
                manifest_exists
                and operation != "update"
                and source_override
            ):
                raise FoundryctlError(
                    "SPEC_SOURCE_OVERRIDE_REQUIRES_UPDATE: specs.json "
                    "already exists; preview spec update instead"
                )
            if (
                operation == "update"
                and manifest_exists
                and args.spec_repository is not None
                and args.spec_version is None
                and args.spec_ref is None
            ):
                raise FoundryctlError(
                    "SPEC_SOURCE_SELECTOR_REQUIRED: --spec-repository on an "
                    "existing project requires --spec-version or --spec-ref"
                )
            apply_changes = bool(
                args.spec_command != "plan" and args.apply
            )
            initial_repository = selected_spec_repository(
                repo,
                args.spec_repository,
                preserve_manifest_source=False,
            )
            initial_source = spec_source(
                initial_repository,
                version=args.spec_version,
                ref=args.spec_ref,
            )
            if initial_source is None:  # pragma: no cover - default enabled
                raise FoundryctlError("Initial Spec source is missing")
            update_source = (
                spec_source(
                    selected_spec_repository(
                        repo,
                        args.spec_repository,
                        preserve_manifest_source=True,
                    ),
                    version=args.spec_version,
                    ref=args.spec_ref,
                    use_default_version=False,
                )
                if operation == "update"
                else None
            )
            print(
                json.dumps(
                    manage_specs(
                        repo,
                        operation,
                        apply_changes=apply_changes,
                        initial_spec_source=initial_source,
                        update_spec_source=update_source,
                        requested_spec_ids=selection,
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
