#!/usr/bin/env python3
"""Resolve, materialize, and validate Engineering Specs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


CATALOG_SCHEMA_VERSION = 1
SPEC_MANIFEST_VERSION = 1
SPEC_LOCK_VERSION = 1
SPEC_OWNER = "engineering-workflow"

SPEC_MANIFEST = "docs/.engineering/specs.json"
SPEC_LOCK = "docs/.engineering/specs.lock.json"
MANAGED_ROOT = "docs/agent-guides/managed"
MANAGED_INDEX = f"{MANAGED_ROOT}/index.md"
AGENTS_ROUTE = MANAGED_INDEX

SPEC_ID_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?"
    r"(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)*$"
)
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}


class SpecError(RuntimeError):
    """Raised when external Spec data does not satisfy its contract."""


@dataclass(frozen=True)
class DetectionRule:
    filenames: tuple[str, ...]
    extensions: tuple[str, ...]


@dataclass(frozen=True)
class CatalogSpec:
    spec_id: str
    version: str
    source_path: str
    sha256: str
    required: bool
    requires: tuple[str, ...]
    applies_to: tuple[str, ...]
    description: str
    detection: DetectionRule | None


@dataclass(frozen=True)
class Catalog:
    catalog_id: str
    digest: str
    root: Path
    ordered_specs: tuple[CatalogSpec, ...]
    by_id: dict[str, CatalogSpec]


@dataclass(frozen=True)
class ProjectSpec:
    path: str
    applies_to: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SpecManifest:
    catalog: dict[str, str]
    spec_ids: tuple[str, ...]
    project_specs: tuple[ProjectSpec, ...]


@dataclass(frozen=True)
class PlannedWrite:
    path: str
    content: bytes
    role: str


@dataclass(frozen=True)
class SpecPlan:
    operation: str
    catalog_id: str
    catalog_digest: str
    detected_spec_ids: tuple[str, ...]
    selected_spec_ids: tuple[str, ...]
    actions: tuple[dict[str, str], ...]
    warnings: tuple[str, ...]
    writes: tuple[PlannedWrite, ...]

    @property
    def conflicts(self) -> tuple[dict[str, str], ...]:
        return tuple(
            action
            for action in self.actions
            if action.get("action") == "conflict"
        )


def _expect_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SpecError(f"{label}: expected an object")
    return value


def _expect_exact_keys(
    value: dict[str, object],
    *,
    required: set[str],
    optional: set[str] | None = None,
    label: str,
) -> None:
    allowed = required | (optional or set())
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise SpecError(f"{label}: missing keys: {', '.join(missing)}")
    if unknown:
        raise SpecError(f"{label}: unknown keys: {', '.join(unknown)}")


def _expect_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{label}: expected a non-empty string")
    return value


def _expect_string_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SpecError(f"{label}: expected an array")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_expect_string(item, f"{label}[{index}]"))
    if len(result) != len(set(result)):
        raise SpecError(f"{label}: duplicate values are not allowed")
    return tuple(result)


def _safe_relative(value: object, label: str) -> str:
    text = _expect_string(value, label)
    if "\\" in text:
        raise SpecError(f"{label}: backslashes are not portable")
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts:
        raise SpecError(f"{label}: expected a repository-relative path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise SpecError(f"{label}: path traversal is not allowed")
    return path.as_posix()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _load_json(path: Path, label: str) -> object:
    if path.is_symlink():
        raise SpecError(f"{label}: symbolic links are not supported: {path}")
    if not path.is_file():
        raise SpecError(f"{label}: expected a regular file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"{label}: invalid JSON: {path}: {exc}") from exc


def _reject_symlink_components(root: Path, relative: str, label: str) -> Path:
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise SpecError(
                f"{label}: symbolic links are not supported: {path}"
            )
    return path


def _catalog_file(root: Path, relative: str, label: str) -> Path:
    path = _reject_symlink_components(root, relative, label)
    if not path.is_file():
        raise SpecError(f"{label}: expected a regular file: {path}")
    return path


def _parse_detection(value: object, label: str) -> DetectionRule:
    data = _expect_object(value, label)
    _expect_exact_keys(
        data,
        required={"filenames", "extensions"},
        label=label,
    )
    filenames = _expect_string_list(data["filenames"], f"{label}.filenames")
    extensions = _expect_string_list(
        data["extensions"],
        f"{label}.extensions",
    )
    if not filenames and not extensions:
        raise SpecError(f"{label}: at least one detection rule is required")
    for filename in filenames:
        if "/" in filename or "\\" in filename or filename in {".", ".."}:
            raise SpecError(
                f"{label}.filenames: expected base filenames: {filename!r}"
            )
    for extension in extensions:
        if not extension.startswith(".") or extension != extension.lower():
            raise SpecError(
                f"{label}.extensions: expected lowercase suffix: "
                f"{extension!r}"
            )
    return DetectionRule(filenames=filenames, extensions=extensions)


def load_catalog(root: Path) -> Catalog:
    if root.is_symlink() or not root.is_dir():
        raise SpecError(
            f"SPEC_CATALOG_INVALID: expected a non-symlink directory: {root}"
        )
    catalog_path = root / "catalog.json"
    raw_bytes: bytes
    try:
        raw_bytes = catalog_path.read_bytes()
    except OSError as exc:
        raise SpecError(
            f"SPEC_CATALOG_INVALID: cannot read {catalog_path}: {exc}"
        ) from exc
    data = _expect_object(
        _load_json(catalog_path, "SPEC_CATALOG_INVALID"),
        "SPEC_CATALOG_INVALID",
    )
    _expect_exact_keys(
        data,
        required={"schema_version", "catalog_id", "specs"},
        label="SPEC_CATALOG_INVALID",
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise SpecError(
            "SPEC_CATALOG_INVALID: schema_version must be 1"
        )
    catalog_id = _expect_string(
        data["catalog_id"],
        "SPEC_CATALOG_INVALID.catalog_id",
    )
    raw_specs = data["specs"]
    if not isinstance(raw_specs, list) or not raw_specs:
        raise SpecError(
            "SPEC_CATALOG_INVALID.specs: expected a non-empty array"
        )

    ordered: list[CatalogSpec] = []
    by_id: dict[str, CatalogSpec] = {}
    for index, raw_spec in enumerate(raw_specs):
        label = f"SPEC_CATALOG_INVALID.specs[{index}]"
        item = _expect_object(raw_spec, label)
        _expect_exact_keys(
            item,
            required={
                "id",
                "version",
                "path",
                "sha256",
                "required",
                "requires",
                "applies_to",
                "description",
            },
            optional={"detection"},
            label=label,
        )
        spec_id = _expect_string(item["id"], f"{label}.id")
        if not SPEC_ID_RE.fullmatch(spec_id):
            raise SpecError(f"{label}.id: invalid Spec ID: {spec_id!r}")
        if spec_id in by_id:
            raise SpecError(f"{label}.id: duplicate Spec ID: {spec_id}")
        version = _expect_string(item["version"], f"{label}.version")
        if not SEMVER_RE.fullmatch(version):
            raise SpecError(
                f"{label}.version: expected MAJOR.MINOR.PATCH: {version!r}"
            )
        source_path = _safe_relative(item["path"], f"{label}.path")
        if not source_path.endswith(".md"):
            raise SpecError(f"{label}.path: expected a Markdown file")
        declared_digest = _expect_string(item["sha256"], f"{label}.sha256")
        if not SHA256_RE.fullmatch(declared_digest):
            raise SpecError(f"{label}.sha256: expected lowercase SHA-256")
        required = item["required"]
        if type(required) is not bool:
            raise SpecError(f"{label}.required: expected a Boolean")
        requires = _expect_string_list(item["requires"], f"{label}.requires")
        for dependency in requires:
            if not SPEC_ID_RE.fullmatch(dependency):
                raise SpecError(
                    f"{label}.requires: invalid Spec ID: {dependency!r}"
                )
        applies_to = _expect_string_list(
            item["applies_to"],
            f"{label}.applies_to",
        )
        if not applies_to:
            raise SpecError(f"{label}.applies_to: at least one scope is required")
        description = _expect_string(
            item["description"],
            f"{label}.description",
        )
        detection = (
            _parse_detection(item["detection"], f"{label}.detection")
            if "detection" in item
            else None
        )
        source = _catalog_file(root, source_path, f"{label}.path")
        actual_digest = _sha256_file(source)
        if actual_digest != declared_digest:
            raise SpecError(
                f"SPEC_CATALOG_DIGEST_MISMATCH: {source_path}: "
                f"declared {declared_digest}; actual {actual_digest}"
            )
        spec = CatalogSpec(
            spec_id=spec_id,
            version=version,
            source_path=source_path,
            sha256=declared_digest,
            required=required,
            requires=requires,
            applies_to=applies_to,
            description=description,
            detection=detection,
        )
        ordered.append(spec)
        by_id[spec_id] = spec

    for spec in ordered:
        missing = sorted(set(spec.requires) - set(by_id))
        if missing:
            raise SpecError(
                f"SPEC_CATALOG_DEPENDENCY_MISSING: {spec.spec_id}: "
                f"{', '.join(missing)}"
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(spec_id: str, chain: tuple[str, ...]) -> None:
        if spec_id in visited:
            return
        if spec_id in visiting:
            cycle = " -> ".join((*chain, spec_id))
            raise SpecError(f"SPEC_CATALOG_DEPENDENCY_CYCLE: {cycle}")
        visiting.add(spec_id)
        for dependency in by_id[spec_id].requires:
            visit(dependency, (*chain, spec_id))
        visiting.remove(spec_id)
        visited.add(spec_id)

    for spec in ordered:
        visit(spec.spec_id, ())

    return Catalog(
        catalog_id=catalog_id,
        digest=_sha256_bytes(raw_bytes),
        root=root,
        ordered_specs=tuple(ordered),
        by_id=by_id,
    )


def _parse_catalog_source(value: object, label: str) -> dict[str, str]:
    data = _expect_object(value, label)
    kind = _expect_string(data.get("kind"), f"{label}.kind")
    if kind == "bundled":
        _expect_exact_keys(data, required={"kind"}, label=label)
        return {"kind": "bundled"}
    if kind == "path":
        _expect_exact_keys(data, required={"kind", "path"}, label=label)
        return {
            "kind": "path",
            "path": _safe_relative(data["path"], f"{label}.path"),
        }
    raise SpecError(
        f"{label}.kind: supported values are 'bundled' and 'path'"
    )


def _parse_project_spec(value: object, index: int) -> ProjectSpec:
    label = f"SPEC_MANIFEST_INVALID.project_specs[{index}]"
    data = _expect_object(value, label)
    _expect_exact_keys(
        data,
        required={"path", "applies_to", "description"},
        label=label,
    )
    path = _safe_relative(data["path"], f"{label}.path")
    if not path.endswith(".md"):
        raise SpecError(f"{label}.path: expected a Markdown file")
    applies_to = _expect_string_list(
        data["applies_to"],
        f"{label}.applies_to",
    )
    if not applies_to:
        raise SpecError(f"{label}.applies_to: at least one scope is required")
    return ProjectSpec(
        path=path,
        applies_to=applies_to,
        description=_expect_string(
            data["description"],
            f"{label}.description",
        ),
    )


def parse_manifest(path: Path) -> SpecManifest:
    data = _expect_object(
        _load_json(path, "SPEC_MANIFEST_INVALID"),
        "SPEC_MANIFEST_INVALID",
    )
    _expect_exact_keys(
        data,
        required={"version", "owner", "catalog", "specs", "project_specs"},
        label="SPEC_MANIFEST_INVALID",
    )
    if type(data["version"]) is not int or data["version"] != 1:
        raise SpecError("SPEC_MANIFEST_INVALID.version: must be 1")
    if data["owner"] != SPEC_OWNER:
        raise SpecError(
            f"SPEC_MANIFEST_INVALID.owner: must be {SPEC_OWNER!r}"
        )
    spec_ids = _expect_string_list(
        data["specs"],
        "SPEC_MANIFEST_INVALID.specs",
    )
    for spec_id in spec_ids:
        if not SPEC_ID_RE.fullmatch(spec_id):
            raise SpecError(
                f"SPEC_MANIFEST_INVALID.specs: invalid Spec ID: {spec_id!r}"
            )
    raw_project_specs = data["project_specs"]
    if not isinstance(raw_project_specs, list):
        raise SpecError(
            "SPEC_MANIFEST_INVALID.project_specs: expected an array"
        )
    project_specs = tuple(
        _parse_project_spec(item, index)
        for index, item in enumerate(raw_project_specs)
    )
    project_paths = [item.path for item in project_specs]
    if len(project_paths) != len(set(project_paths)):
        raise SpecError(
            "SPEC_MANIFEST_INVALID.project_specs: duplicate paths"
        )
    return SpecManifest(
        catalog=_parse_catalog_source(
            data["catalog"],
            "SPEC_MANIFEST_INVALID.catalog",
        ),
        spec_ids=spec_ids,
        project_specs=project_specs,
    )


def manifest_data(manifest: SpecManifest) -> dict[str, object]:
    return {
        "version": SPEC_MANIFEST_VERSION,
        "owner": SPEC_OWNER,
        "catalog": dict(manifest.catalog),
        "specs": list(manifest.spec_ids),
        "project_specs": [
            {
                "path": item.path,
                "applies_to": list(item.applies_to),
                "description": item.description,
            }
            for item in manifest.project_specs
        ],
    }


def resolve_catalog_root(
    repo: Path,
    bundled_catalog: Path,
    source: dict[str, str],
) -> Path:
    if source["kind"] == "bundled":
        return bundled_catalog
    relative = source["path"]
    path = _reject_symlink_components(
        repo,
        relative,
        "SPEC_CATALOG_INVALID",
    )
    if not path.is_dir():
        raise SpecError(
            f"SPEC_CATALOG_INVALID: path catalog does not exist: {relative}"
        )
    return path


def detect_specs(repo: Path, catalog: Catalog) -> tuple[str, ...]:
    candidates = tuple(
        spec for spec in catalog.ordered_specs if spec.detection is not None
    )
    if not candidates:
        return ()
    detected: set[str] = set()
    managed_prefixes = {
        PurePosixPath("docs/.engineering"),
        PurePosixPath(MANAGED_ROOT),
    }
    try:
        catalog_relative = catalog.root.relative_to(repo)
    except ValueError:
        pass
    else:
        managed_prefixes.add(PurePosixPath(catalog_relative.as_posix()))

    for root_text, directory_names, filenames in os.walk(
        repo,
        topdown=True,
        followlinks=False,
    ):
        root = Path(root_text)
        try:
            relative_root = root.relative_to(repo)
        except ValueError:  # pragma: no cover - os.walk starts at repo
            continue
        relative_parts = PurePosixPath(relative_root.as_posix())
        if any(
            relative_parts == prefix or prefix in relative_parts.parents
            for prefix in managed_prefixes
        ):
            directory_names[:] = []
            continue
        kept_directories: list[str] = []
        for name in directory_names:
            child = root / name
            child_relative = PurePosixPath(
                child.relative_to(repo).as_posix()
            )
            if name in EXCLUDED_DIRECTORY_NAMES or child.is_symlink():
                continue
            if any(
                child_relative == prefix or prefix in child_relative.parents
                for prefix in managed_prefixes
            ):
                continue
            kept_directories.append(name)
        directory_names[:] = kept_directories

        filename_set = set(filenames)
        suffixes = {Path(name).suffix.lower() for name in filenames}
        for spec in candidates:
            if spec.spec_id in detected or spec.detection is None:
                continue
            rule = spec.detection
            if filename_set.intersection(rule.filenames) or suffixes.intersection(
                rule.extensions
            ):
                detected.add(spec.spec_id)
        if len(detected) == len(candidates):
            break

    return tuple(
        spec.spec_id
        for spec in catalog.ordered_specs
        if spec.spec_id in detected
    )


def resolve_selection(
    manifest: SpecManifest,
    catalog: Catalog,
) -> tuple[CatalogSpec, ...]:
    missing = sorted(set(manifest.spec_ids) - set(catalog.by_id))
    if missing:
        raise SpecError(
            "SPEC_SELECTION_UNKNOWN: " + ", ".join(missing)
        )
    required = {
        spec.spec_id for spec in catalog.ordered_specs if spec.required
    }
    missing_required = sorted(required - set(manifest.spec_ids))
    if missing_required:
        raise SpecError(
            "SPEC_REQUIRED_SELECTION_MISSING: "
            + ", ".join(missing_required)
        )
    selected = set(manifest.spec_ids)

    def add_dependencies(spec_id: str) -> None:
        for dependency in catalog.by_id[spec_id].requires:
            if dependency not in selected:
                selected.add(dependency)
                add_dependencies(dependency)

    for spec_id in tuple(selected):
        add_dependencies(spec_id)
    return tuple(
        spec
        for spec in catalog.ordered_specs
        if spec.spec_id in selected
    )


def _initial_manifest(repo: Path, catalog: Catalog) -> tuple[
    SpecManifest,
    tuple[str, ...],
]:
    detected = detect_specs(repo, catalog)
    selected = [
        spec.spec_id for spec in catalog.ordered_specs if spec.required
    ]
    selected.extend(
        spec_id for spec_id in detected if spec_id not in selected
    )
    return (
        SpecManifest(
            catalog={"kind": "bundled"},
            spec_ids=tuple(selected),
            project_specs=(),
        ),
        detected,
    )


def _validate_project_specs(
    repo: Path,
    project_specs: tuple[ProjectSpec, ...],
) -> None:
    for item in project_specs:
        path = _reject_symlink_components(
            repo,
            item.path,
            "SPEC_PROJECT_FILE_INVALID",
        )
        if not path.is_file():
            raise SpecError(
                f"SPEC_PROJECT_FILE_MISSING: {item.path}: "
                "create the file or remove it from specs.json"
            )


def _managed_path(spec_id: str) -> str:
    return f"{MANAGED_ROOT}/{spec_id}.md"


def lock_data(
    manifest: SpecManifest,
    catalog: Catalog,
    selected: tuple[CatalogSpec, ...],
) -> dict[str, object]:
    return {
        "version": SPEC_LOCK_VERSION,
        "owner": SPEC_OWNER,
        "catalog": {
            "catalog_id": catalog.catalog_id,
            "sha256": catalog.digest,
            "source": dict(manifest.catalog),
        },
        "specs": [
            {
                "id": spec.spec_id,
                "version": spec.version,
                "source_path": spec.source_path,
                "installed_path": _managed_path(spec.spec_id),
                "sha256": spec.sha256,
                "requires": list(spec.requires),
                "applies_to": list(spec.applies_to),
                "description": spec.description,
            }
            for spec in selected
        ],
    }


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_index(
    catalog: Catalog,
    selected: tuple[CatalogSpec, ...],
    project_specs: tuple[ProjectSpec, ...],
) -> bytes:
    lines = [
        "# Engineering Specs",
        "",
        "<!-- Generated by engineering-workflow. Do not edit this file. -->",
        "",
        "Before implementation or review, read every entry whose scope matches",
        "the files being changed. More specific project guidance takes precedence",
        "only when it explicitly declares the override.",
        "",
        f"Catalog: `{catalog.catalog_id}` (`sha256:{catalog.digest}`)",
        "",
        "## Managed Specs",
        "",
        "| Scope | Spec | Version | Purpose |",
        "|---|---|---:|---|",
    ]
    for spec in selected:
        relative_link = posixpath.relpath(
            _managed_path(spec.spec_id),
            posixpath.dirname(MANAGED_INDEX),
        )
        scopes = "<br>".join(
            f"`{_markdown_cell(scope)}`" for scope in spec.applies_to
        )
        lines.append(
            f"| {scopes} | [{spec.spec_id}]({relative_link}) | "
            f"`{spec.version}` | {_markdown_cell(spec.description)} |"
        )

    lines.extend(["", "## Project Specs", ""])
    if project_specs:
        lines.extend(
            [
                "| Scope | Spec | Purpose |",
                "|---|---|---|",
            ]
        )
        for item in project_specs:
            relative_link = posixpath.relpath(
                item.path,
                posixpath.dirname(MANAGED_INDEX),
            )
            scopes = "<br>".join(
                f"`{_markdown_cell(scope)}`" for scope in item.applies_to
            )
            lines.append(
                f"| {scopes} | [{item.path}]({relative_link}) | "
                f"{_markdown_cell(item.description)} |"
            )
    else:
        lines.append("No project-specific Specs are registered.")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _path_conflict(repo: Path, relative: str) -> str:
    try:
        path = _reject_symlink_components(
            repo,
            relative,
            "SPEC_PATH_CONFLICT",
        )
    except SpecError as exc:
        return str(exc)
    current = repo
    parts = PurePosixPath(relative).parts
    for part in parts[:-1]:
        current = current / part
        if current.exists() and not current.is_dir():
            return (
                "parent is not a directory: "
                + current.relative_to(repo).as_posix()
            )
    if path.exists() and not path.is_file():
        return "expected a regular file"
    return ""


def _prepare_manifest(
    repo: Path,
    bundled_catalog: Path,
    operation: str,
) -> tuple[SpecManifest, Catalog, tuple[str, ...], bytes | None]:
    manifest_path = repo / SPEC_MANIFEST
    if manifest_path.exists():
        manifest = parse_manifest(manifest_path)
        catalog_root = resolve_catalog_root(
            repo,
            bundled_catalog,
            manifest.catalog,
        )
        catalog = load_catalog(catalog_root)
        detected = detect_specs(repo, catalog)
        manifest_write: bytes | None = None
        if operation == "update":
            updated_ids = list(manifest.spec_ids)
            for spec_id in detected:
                if spec_id not in updated_ids:
                    updated_ids.append(spec_id)
            if tuple(updated_ids) != manifest.spec_ids:
                manifest = SpecManifest(
                    catalog=manifest.catalog,
                    spec_ids=tuple(updated_ids),
                    project_specs=manifest.project_specs,
                )
                manifest_write = _json_bytes(manifest_data(manifest))
        return manifest, catalog, detected, manifest_write

    catalog = load_catalog(bundled_catalog)
    manifest, detected = _initial_manifest(repo, catalog)
    return (
        manifest,
        catalog,
        detected,
        _json_bytes(manifest_data(manifest)),
    )


def _stale_managed_warnings(
    repo: Path,
    selected: tuple[CatalogSpec, ...],
) -> list[str]:
    root = repo / MANAGED_ROOT
    if not root.is_dir() or root.is_symlink():
        return []
    expected = {
        PurePosixPath(_managed_path(spec.spec_id))
        for spec in selected
    }
    expected.add(PurePosixPath(MANAGED_INDEX))
    warnings: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = PurePosixPath(path.relative_to(repo).as_posix())
        if relative not in expected:
            warnings.append(
                f"SPEC_STALE_MANAGED_FILE: {relative.as_posix()}: "
                "not selected; retained for non-destructive cleanup"
            )
    return warnings


def plan_spec_state(
    repo: Path,
    bundled_catalog: Path,
    *,
    operation: str,
    allow_replace: bool,
) -> SpecPlan:
    if operation not in {"plan", "sync", "update"}:
        raise SpecError(f"SPEC_OPERATION_INVALID: {operation}")
    effective_operation = "sync" if operation == "plan" else operation
    manifest, catalog, detected, manifest_write = _prepare_manifest(
        repo,
        bundled_catalog,
        effective_operation,
    )
    _validate_project_specs(repo, manifest.project_specs)
    selected = resolve_selection(manifest, catalog)

    writes: list[PlannedWrite] = []
    if manifest_write is not None:
        writes.append(
            PlannedWrite(
                path=SPEC_MANIFEST,
                content=manifest_write,
                role="manifest",
            )
        )
    writes.append(
        PlannedWrite(
            path=SPEC_LOCK,
            content=_json_bytes(lock_data(manifest, catalog, selected)),
            role="lock",
        )
    )
    for spec in selected:
        source = _catalog_file(
            catalog.root,
            spec.source_path,
            "SPEC_CATALOG_INVALID",
        )
        writes.append(
            PlannedWrite(
                path=_managed_path(spec.spec_id),
                content=source.read_bytes(),
                role="managed_spec",
            )
        )
    writes.append(
        PlannedWrite(
            path=MANAGED_INDEX,
            content=render_index(catalog, selected, manifest.project_specs),
            role="index",
        )
    )

    actions: list[dict[str, str]] = []
    if manifest_write is None:
        actions.append({"action": "preserve", "path": SPEC_MANIFEST})
    for write in writes:
        reason = _path_conflict(repo, write.path)
        if reason:
            actions.append(
                {
                    "action": "conflict",
                    "path": write.path,
                    "reason": reason,
                }
            )
            continue
        path = repo / write.path
        if not path.exists():
            actions.append({"action": "create_file", "path": write.path})
            continue
        current = path.read_bytes()
        if current == write.content:
            actions.append({"action": "preserve", "path": write.path})
            continue
        if not allow_replace:
            actions.append(
                {
                    "action": "conflict",
                    "path": write.path,
                    "reason": (
                        "SPEC_MANAGED_CONTENT_DRIFT: existing bytes differ; "
                        "run engineeringctl spec sync --apply after review"
                    ),
                }
            )
            continue
        actions.append(
            {
                "action": (
                    "update_file"
                    if write.role == "manifest"
                    else "replace_file"
                ),
                "path": write.path,
            }
        )

    warnings = _stale_managed_warnings(repo, selected)
    agents = repo / "AGENTS.md"
    if agents.is_file() and not agents.is_symlink():
        try:
            agents_text = agents.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            warnings.append(
                f"SPEC_AGENTS_ROUTE_UNREADABLE: AGENTS.md: {exc}"
            )
        else:
            if AGENTS_ROUTE not in agents_text:
                warnings.append(
                    f"SPEC_AGENTS_ROUTE_MISSING: AGENTS.md: add a short route "
                    f"to {AGENTS_ROUTE}"
                )

    return SpecPlan(
        operation=operation,
        catalog_id=catalog.catalog_id,
        catalog_digest=catalog.digest,
        detected_spec_ids=detected,
        selected_spec_ids=tuple(spec.spec_id for spec in selected),
        actions=tuple(actions),
        warnings=tuple(warnings),
        writes=tuple(writes),
    )


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = ""
    with tempfile.NamedTemporaryFile(
        "wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    try:
        os.replace(temporary, path)
        if hasattr(os, "O_DIRECTORY"):
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def apply_spec_plan(
    repo: Path,
    plan: SpecPlan,
) -> tuple[list[str], list[str]]:
    if plan.conflicts:
        details = "; ".join(
            f"{item.get('path')}: {item.get('reason')}"
            for item in plan.conflicts
        )
        raise SpecError(f"Spec preflight failed: {details}")
    action_by_path = {
        action["path"]: action["action"]
        for action in plan.actions
        if "path" in action and "action" in action
    }
    created: list[str] = []
    updated: list[str] = []
    for write in plan.writes:
        action = action_by_path.get(write.path)
        if action == "preserve":
            continue
        if action not in {"create_file", "replace_file", "update_file"}:
            raise SpecError(
                f"SPEC_PLAN_INVALID: no write action for {write.path}"
            )
        reason = _path_conflict(repo, write.path)
        if reason:
            raise SpecError(
                f"SPEC_PREFLIGHT_CHANGED: {write.path}: {reason}"
            )
        _atomic_write(repo / write.path, write.content)
        if action == "create_file":
            created.append(write.path)
        else:
            updated.append(write.path)
    return created, updated


def validate_spec_state(
    repo: Path,
    bundled_catalog: Path,
    *,
    require_manifest: bool,
) -> tuple[list[str], list[str]]:
    manifest_path = repo / SPEC_MANIFEST
    if not manifest_path.exists():
        if require_manifest:
            return [
                f"SPEC_MANIFEST_MISSING: {SPEC_MANIFEST}: "
                "run engineeringctl spec sync --apply"
            ], []
        return [], [
            f"SPEC_MANIFEST_MISSING: {SPEC_MANIFEST}: "
            "run engineeringctl bootstrap --profile codex --apply"
        ]
    try:
        plan = plan_spec_state(
            repo,
            bundled_catalog,
            operation="sync",
            allow_replace=True,
        )
    except SpecError as exc:
        return [str(exc)], []

    errors: list[str] = []
    warnings = list(plan.warnings)
    for action in plan.actions:
        kind = action.get("action")
        path = action.get("path", "")
        if kind == "preserve":
            continue
        if kind == "create_file":
            if path == SPEC_LOCK:
                label = "SPEC_LOCK_MISSING"
            elif path == MANAGED_INDEX:
                label = "SPEC_INDEX_MISSING"
            elif path == SPEC_MANIFEST:
                label = "SPEC_MANIFEST_MISSING"
            else:
                label = "SPEC_MANAGED_FILE_MISSING"
            errors.append(
                f"{label}: {path}: run engineeringctl spec sync --apply"
            )
        elif kind in {"replace_file", "update_file"}:
            if path == SPEC_LOCK:
                label = "SPEC_LOCK_DRIFT"
            elif path == MANAGED_INDEX:
                label = "SPEC_INDEX_DRIFT"
            elif path == SPEC_MANIFEST:
                label = "SPEC_MANIFEST_DRIFT"
            else:
                label = "SPEC_MANAGED_CONTENT_DRIFT"
            errors.append(
                f"{label}: {path}: run engineeringctl spec sync --apply "
                "after reviewing the plan"
            )
        elif kind == "conflict":
            errors.append(
                f"SPEC_PATH_CONFLICT: {path}: {action.get('reason', '')}"
            )
    return errors, warnings


def plan_payload(
    plan: SpecPlan,
    *,
    mode: str,
    created: Iterable[str] = (),
    updated: Iterable[str] = (),
) -> dict[str, object]:
    return {
        "operation": plan.operation,
        "mode": mode,
        "catalog": {
            "catalog_id": plan.catalog_id,
            "sha256": plan.catalog_digest,
        },
        "detected_specs": list(plan.detected_spec_ids),
        "selected_specs": list(plan.selected_spec_ids),
        "actions": list(plan.actions),
        "warnings": list(plan.warnings),
        "created": list(created),
        "updated": list(updated),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an Engineering Spec catalog"
    )
    parser.add_argument(
        "--check-catalog",
        metavar="DIRECTORY",
        help="Validate one catalog directory and print its summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.check_catalog:
        build_parser().print_help()
        return 0
    try:
        catalog = load_catalog(Path(args.check_catalog).expanduser().resolve())
    except SpecError as exc:
        print(f"spec_manager: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "catalog_id": catalog.catalog_id,
                "sha256": catalog.digest,
                "specs": [spec.spec_id for spec in catalog.ordered_specs],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
