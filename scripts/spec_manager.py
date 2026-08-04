#!/usr/bin/env python3
"""Resolve, materialize, and validate Engineering Specs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable


CATALOG_SCHEMA_VERSION = 1
SPEC_MANIFEST_VERSION = 1
SPEC_LOCK_VERSION = 1
SPEC_OWNER = "repo-foundry"
LEGACY_SPEC_OWNERS = frozenset({"engineering-workflow"})
SUPPORTED_SPEC_OWNERS = frozenset({SPEC_OWNER, *LEGACY_SPEC_OWNERS})

SPEC_MANIFEST = "docs/.engineering/specs.json"
SPEC_LOCK = "docs/.engineering/specs.lock.json"
MANAGED_ROOT = "docs/agent-guides/managed"
MANAGED_INDEX = f"{MANAGED_ROOT}/index.md"

SPEC_ID_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?"
    r"(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)*$"
)
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
RELEASE_REF_RE = re.compile(
    r"^refs/tags/v([0-9]+\.[0-9]+\.[0-9]+)$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

MAX_CATALOG_BYTES = 1024 * 1024
MAX_SPEC_BYTES = 1024 * 1024
MAX_SPEC_COUNT = 256
MAX_TOTAL_SPEC_BYTES = 16 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 60

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


def release_ref(version: str) -> str:
    """Return the canonical immutable Git ref for a Catalog SemVer."""

    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        raise SpecError(
            "SPEC_VERSION_INVALID: expected MAJOR.MINOR.PATCH"
        )
    return f"refs/tags/v{version}"


def release_version_from_ref(ref: str) -> str | None:
    """Extract a Catalog SemVer from an exact canonical release ref."""

    match = RELEASE_REF_RE.fullmatch(ref)
    return match.group(1) if match is not None else None


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
    catalog_version: str
    digest: str
    source: dict[str, str]
    resolved_revision: str
    contents: dict[str, bytes]
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
    owner: str = SPEC_OWNER


@dataclass(frozen=True)
class SpecLock:
    catalog_id: str
    catalog_version: str
    catalog_digest: str
    source: dict[str, str]
    resolved_revision: str
    specs: tuple[CatalogSpec, ...]
    owner: str = SPEC_OWNER


@dataclass(frozen=True)
class PlannedWrite:
    path: str
    content: bytes
    role: str


@dataclass(frozen=True)
class PlannedDelete:
    path: str
    sha256: str


@dataclass(frozen=True)
class SpecPlan:
    operation: str
    catalog_id: str
    catalog_version: str
    catalog_digest: str
    catalog_source: dict[str, str]
    resolved_revision: str
    detected_spec_ids: tuple[str, ...]
    configured_spec_ids: tuple[str, ...]
    selected_spec_ids: tuple[str, ...]
    available_specs: tuple[CatalogSpec, ...]
    actions: tuple[dict[str, str], ...]
    warnings: tuple[str, ...]
    writes: tuple[PlannedWrite, ...]
    deletes: tuple[PlannedDelete, ...]

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
    if ":" in text or "\x00" in text or any(
        ord(character) < 32 for character in text
    ):
        raise SpecError(f"{label}: unsafe path characters are not allowed")
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


def _load_json_bytes(value: bytes, label: str) -> object:
    try:
        return json.loads(value.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"{label}: invalid UTF-8 JSON: {exc}") from exc


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


def _parse_catalog(
    raw_bytes: bytes,
    read_content: Callable[[str, int], bytes],
    *,
    source: dict[str, str],
    resolved_revision: str,
) -> Catalog:
    if len(raw_bytes) > MAX_CATALOG_BYTES:
        raise SpecError(
            f"SPEC_CATALOG_TOO_LARGE: catalog.json exceeds "
            f"{MAX_CATALOG_BYTES} bytes"
        )
    data = _expect_object(
        _load_json_bytes(raw_bytes, "SPEC_CATALOG_INVALID"),
        "SPEC_CATALOG_INVALID",
    )
    _expect_exact_keys(
        data,
        required={
            "schema_version",
            "catalog_id",
            "catalog_version",
            "specs",
        },
        label="SPEC_CATALOG_INVALID",
    )
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != CATALOG_SCHEMA_VERSION
    ):
        raise SpecError(
            "SPEC_CATALOG_INVALID.schema_version: must be "
            f"{CATALOG_SCHEMA_VERSION}"
        )
    catalog_id = _expect_string(
        data["catalog_id"],
        "SPEC_CATALOG_INVALID.catalog_id",
    )
    catalog_version = _expect_string(
        data["catalog_version"],
        "SPEC_CATALOG_INVALID.catalog_version",
    )
    if not SEMVER_RE.fullmatch(catalog_version):
        raise SpecError(
            "SPEC_CATALOG_INVALID.catalog_version: expected "
            f"MAJOR.MINOR.PATCH: {catalog_version!r}"
        )
    raw_specs = data["specs"]
    if not isinstance(raw_specs, list) or not raw_specs:
        raise SpecError(
            "SPEC_CATALOG_INVALID.specs: expected a non-empty array"
        )
    if len(raw_specs) > MAX_SPEC_COUNT:
        raise SpecError(
            f"SPEC_CATALOG_TOO_LARGE: {len(raw_specs)} Specs exceeds "
            f"{MAX_SPEC_COUNT}"
        )

    ordered: list[CatalogSpec] = []
    by_id: dict[str, CatalogSpec] = {}
    contents: dict[str, bytes] = {}
    source_paths: set[str] = set()
    total_content_bytes = 0
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
        if source_path in source_paths:
            raise SpecError(f"{label}.path: duplicate path: {source_path}")
        source_paths.add(source_path)
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
        content = read_content(source_path, MAX_SPEC_BYTES)
        total_content_bytes += len(content)
        if total_content_bytes > MAX_TOTAL_SPEC_BYTES:
            raise SpecError(
                "SPEC_CATALOG_TOO_LARGE: total Spec content exceeds "
                f"{MAX_TOTAL_SPEC_BYTES} bytes"
            )
        actual_digest = _sha256_bytes(content)
        if actual_digest != declared_digest:
            raise SpecError(
                f"SPEC_CATALOG_DIGEST_MISMATCH: {source_path}: "
                f"declared {declared_digest}; actual {actual_digest}"
            )
        contents[source_path] = content
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
        catalog_version=catalog_version,
        digest=_sha256_bytes(raw_bytes),
        source=dict(source),
        resolved_revision=resolved_revision,
        contents=contents,
        ordered_specs=tuple(ordered),
        by_id=by_id,
    )


def load_catalog(root: Path) -> Catalog:
    """Validate a local Catalog directory for repository authoring checks."""

    if root.is_symlink() or not root.is_dir():
        raise SpecError(
            f"SPEC_CATALOG_INVALID: expected a non-symlink directory: {root}"
        )
    catalog_path = _catalog_file(
        root,
        "catalog.json",
        "SPEC_CATALOG_INVALID",
    )
    try:
        raw_bytes = catalog_path.read_bytes()
    except OSError as exc:
        raise SpecError(
            f"SPEC_CATALOG_INVALID: cannot read {catalog_path}: {exc}"
        ) from exc

    def read_content(relative: str, maximum: int) -> bytes:
        path = _catalog_file(root, relative, "SPEC_CATALOG_INVALID")
        try:
            size = path.stat().st_size
            if size > maximum:
                raise SpecError(
                    f"SPEC_CATALOG_FILE_TOO_LARGE: {relative}: "
                    f"{size} bytes exceeds {maximum}"
                )
            return path.read_bytes()
        except OSError as exc:
            raise SpecError(
                f"SPEC_CATALOG_INVALID: cannot read {relative}: {exc}"
            ) from exc

    return _parse_catalog(
        raw_bytes,
        read_content,
        source={"kind": "directory", "path": str(root)},
        resolved_revision="local",
    )


def _validate_git_url(value: object, label: str) -> str:
    url = _expect_string(value, label)
    if url != url.strip() or len(url) > 2048:
        raise SpecError(f"{label}: invalid Git URL")
    if url.startswith("-") or any(ord(character) < 32 for character in url):
        raise SpecError(f"{label}: unsafe Git URL")
    if re.match(r"^[A-Za-z0-9._-]+@[^:\s]+:.+$", url):
        return url
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"https", "http", "ssh", "git", "file"}:
        raise SpecError(
            f"{label}: expected https, http, ssh, git, file, or SCP-style URL"
        )
    if parsed.scheme != "file" and not parsed.hostname:
        raise SpecError(f"{label}: Git URL must include a host")
    try:
        parsed.port
    except ValueError as exc:
        raise SpecError(f"{label}: invalid Git URL port") from exc
    if parsed.scheme in {"https", "http"} and (
        parsed.username is not None or parsed.password is not None
    ):
        raise SpecError(
            f"{label}: embedded credentials are not supported; "
            "configure a Git credential helper"
        )
    return url


def _validate_git_ref(value: object, label: str) -> str:
    ref = _expect_string(value, label)
    if ref != ref.strip() or len(ref) > 255 or ref.startswith("-"):
        raise SpecError(f"{label}: invalid Git ref")
    if (
        any(ord(character) < 32 or character.isspace() for character in ref)
        or "\\" in ref
        or ":" in ref
        or ".." in ref
        or "@{" in ref
        or ref.endswith(("/", "."))
        or any(character in ref for character in "~^?*[")
    ):
        raise SpecError(f"{label}: unsafe Git ref: {ref!r}")
    return ref


def _redact_git_url(url: str) -> str:
    if re.match(r"^[A-Za-z0-9._-]+@[^:\s]+:.+$", url):
        user, remainder = url.split("@", 1)
        return f"{user}@{remainder}"
    parsed = urllib.parse.urlsplit(url)
    if parsed.username is None and parsed.password is None:
        return url
    host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        host += f":{port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)
    )


def _run_git(
    repository: Path,
    arguments: list[str],
    *,
    label: str,
    source_url: str,
    maximum_output: int = 4 * 1024 * 1024,
) -> bytes:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SpecError(
            "SPEC_GIT_UNAVAILABLE: install Git and ensure it is on PATH"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SpecError(
            f"{label}: Git command timed out after "
            f"{GIT_TIMEOUT_SECONDS} seconds"
        ) from exc
    if len(result.stdout) > maximum_output:
        raise SpecError(
            f"{label}: Git output exceeds {maximum_output} bytes"
        )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        redacted = _redact_git_url(source_url)
        if source_url:
            stderr = stderr.replace(source_url, redacted)
        if len(stderr) > 2000:
            stderr = stderr[-2000:]
        detail = f": {stderr}" if stderr else ""
        raise SpecError(f"{label}{detail}")
    return result.stdout


def _read_git_blob(
    repository: Path,
    commit: str,
    relative: str,
    maximum: int,
    *,
    source_url: str,
) -> bytes:
    object_name = f"{commit}:{relative}"
    tree_entry = _run_git(
        repository,
        ["ls-tree", "-z", commit, "--", relative],
        label=f"SPEC_GIT_PATH_MISSING: {relative}",
        source_url=source_url,
        maximum_output=4096,
    )
    entries = [entry for entry in tree_entry.split(b"\x00") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise SpecError(
            f"SPEC_GIT_PATH_INVALID: {relative}: expected one tree entry"
        )
    metadata, raw_path = entries[0].split(b"\t", 1)
    try:
        decoded_path = raw_path.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise SpecError(
            f"SPEC_GIT_PATH_INVALID: {relative}: path is not UTF-8"
        ) from exc
    if decoded_path != relative:
        raise SpecError(
            f"SPEC_GIT_PATH_INVALID: {relative}: tree path mismatch"
        )
    parts = metadata.split()
    if len(parts) != 3 or parts[0] not in {b"100644", b"100755"}:
        raise SpecError(
            f"SPEC_GIT_PATH_INVALID: {relative}: "
            "expected a regular Git blob, not a symbolic link"
        )
    size_bytes = _run_git(
        repository,
        ["cat-file", "-s", object_name],
        label=f"SPEC_GIT_PATH_INVALID: {relative}",
        source_url=source_url,
        maximum_output=128,
    )
    try:
        size = int(size_bytes.decode("ascii").strip())
    except (UnicodeError, ValueError) as exc:
        raise SpecError(
            f"SPEC_GIT_PATH_INVALID: {relative}: invalid blob size"
        ) from exc
    if size > maximum:
        raise SpecError(
            f"SPEC_CATALOG_FILE_TOO_LARGE: {relative}: "
            f"{size} bytes exceeds {maximum}"
        )
    content = _run_git(
        repository,
        ["show", object_name],
        label=f"SPEC_GIT_READ_FAILED: {relative}",
        source_url=source_url,
        maximum_output=maximum,
    )
    if len(content) != size:
        raise SpecError(
            f"SPEC_GIT_READ_FAILED: {relative}: "
            f"expected {size} bytes; read {len(content)}"
        )
    return content


def resolve_git_catalog(
    source: dict[str, str],
    revision: str,
) -> Catalog:
    parsed_source = _parse_catalog_source(
        source,
        "SPEC_CATALOG_SOURCE_INVALID",
    )
    resolved_input = _validate_git_ref(
        revision,
        "SPEC_CATALOG_SOURCE_INVALID.revision",
    )
    source_url = parsed_source["url"]
    with tempfile.TemporaryDirectory(
        prefix="engineering-specifications-"
    ) as temporary:
        repository = Path(temporary)
        _run_git(
            repository,
            ["init", "--bare", "--quiet"],
            label="SPEC_GIT_INIT_FAILED",
            source_url=source_url,
        )
        _run_git(
            repository,
            ["remote", "add", "origin", source_url],
            label="SPEC_GIT_REMOTE_FAILED",
            source_url=source_url,
        )
        _run_git(
            repository,
            [
                "fetch",
                "--quiet",
                "--depth=1",
                "--no-tags",
                "origin",
                resolved_input,
            ],
            label=(
                "SPEC_GIT_FETCH_FAILED: "
                f"{_redact_git_url(source_url)}#{resolved_input}"
            ),
            source_url=source_url,
        )
        commit_bytes = _run_git(
            repository,
            ["rev-parse", "--verify", "FETCH_HEAD^{commit}"],
            label="SPEC_GIT_REVISION_INVALID",
            source_url=source_url,
            maximum_output=128,
        )
        commit = commit_bytes.decode("ascii", errors="strict").strip()
        if not GIT_COMMIT_RE.fullmatch(commit):
            raise SpecError(
                f"SPEC_GIT_REVISION_INVALID: expected full commit; got "
                f"{commit!r}"
            )
        raw_catalog = _read_git_blob(
            repository,
            commit,
            "catalog.json",
            MAX_CATALOG_BYTES,
            source_url=source_url,
        )

        def read_content(relative: str, maximum: int) -> bytes:
            return _read_git_blob(
                repository,
                commit,
                relative,
                maximum,
                source_url=source_url,
            )

        catalog = _parse_catalog(
            raw_catalog,
            read_content,
            source=parsed_source,
            resolved_revision=commit,
        )
        expected_version = release_version_from_ref(parsed_source["ref"])
        if (
            expected_version is not None
            and catalog.catalog_version != expected_version
        ):
            raise SpecError(
                "SPEC_CATALOG_VERSION_MISMATCH: release ref "
                f"{parsed_source['ref']} requires Catalog "
                f"{expected_version}; found {catalog.catalog_version}"
            )
        return catalog


def _parse_catalog_source(value: object, label: str) -> dict[str, str]:
    data = _expect_object(value, label)
    _expect_exact_keys(
        data,
        required={"kind", "url", "ref"},
        label=label,
    )
    kind = _expect_string(data["kind"], f"{label}.kind")
    if kind != "git":
        raise SpecError(
            f"{label}.kind: only 'git' is supported; "
            "migrate bundled/path sources to EngineeringSpecifications"
        )
    return {
        "kind": "git",
        "url": _validate_git_url(data["url"], f"{label}.url"),
        "ref": _validate_git_ref(data["ref"], f"{label}.ref"),
    }


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
    owner = _expect_string(data["owner"], "SPEC_MANIFEST_INVALID.owner")
    if owner not in SUPPORTED_SPEC_OWNERS:
        raise SpecError(
            "SPEC_MANIFEST_INVALID.owner: must be one of "
            f"{sorted(SUPPORTED_SPEC_OWNERS)!r}"
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
        owner=owner,
    )


def manifest_data(manifest: SpecManifest) -> dict[str, object]:
    return {
        "version": SPEC_MANIFEST_VERSION,
        "owner": manifest.owner,
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


def configured_spec_ids(
    catalog: Catalog,
    requested_spec_ids: tuple[str, ...],
) -> tuple[str, ...]:
    """Build the direct project selection from required and requested IDs."""

    if len(requested_spec_ids) != len(set(requested_spec_ids)):
        raise SpecError(
            "SPEC_SELECTION_DUPLICATE: duplicate Spec IDs are not allowed"
        )
    for spec_id in requested_spec_ids:
        if not SPEC_ID_RE.fullmatch(spec_id):
            raise SpecError(
                f"SPEC_SELECTION_INVALID: invalid Spec ID: {spec_id!r}"
            )
        if spec_id not in catalog.by_id:
            raise SpecError(f"SPEC_SELECTION_UNKNOWN: {spec_id}")

    configured = [
        spec.spec_id for spec in catalog.ordered_specs if spec.required
    ]
    configured.extend(
        spec_id
        for spec_id in requested_spec_ids
        if spec_id not in configured
    )
    return tuple(configured)


def _initial_manifest(
    repo: Path,
    catalog: Catalog,
    source: dict[str, str],
    requested_spec_ids: tuple[str, ...] | None,
) -> tuple[
    SpecManifest,
    tuple[str, ...],
]:
    detected = detect_specs(repo, catalog)
    selected = configured_spec_ids(
        catalog,
        requested_spec_ids or (),
    )
    return (
        SpecManifest(
            catalog=dict(source),
            spec_ids=selected,
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
        "owner": manifest.owner,
        "catalog": {
            "catalog_id": catalog.catalog_id,
            "catalog_version": catalog.catalog_version,
            "sha256": catalog.digest,
            "source": dict(manifest.catalog),
            "resolved_revision": catalog.resolved_revision,
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


def parse_lock(path: Path) -> SpecLock:
    data = _expect_object(
        _load_json(path, "SPEC_LOCK_INVALID"),
        "SPEC_LOCK_INVALID",
    )
    _expect_exact_keys(
        data,
        required={"version", "owner", "catalog", "specs"},
        label="SPEC_LOCK_INVALID",
    )
    if type(data["version"]) is not int or data["version"] != SPEC_LOCK_VERSION:
        raise SpecError(
            f"SPEC_LOCK_INVALID.version: must be {SPEC_LOCK_VERSION}"
        )
    owner = _expect_string(data["owner"], "SPEC_LOCK_INVALID.owner")
    if owner not in SUPPORTED_SPEC_OWNERS:
        raise SpecError(
            "SPEC_LOCK_INVALID.owner: must be one of "
            f"{sorted(SUPPORTED_SPEC_OWNERS)!r}"
        )
    raw_catalog = _expect_object(
        data["catalog"],
        "SPEC_LOCK_INVALID.catalog",
    )
    _expect_exact_keys(
        raw_catalog,
        required={
            "catalog_id",
            "catalog_version",
            "sha256",
            "source",
            "resolved_revision",
        },
        label="SPEC_LOCK_INVALID.catalog",
    )
    catalog_id = _expect_string(
        raw_catalog["catalog_id"],
        "SPEC_LOCK_INVALID.catalog.catalog_id",
    )
    catalog_version = _expect_string(
        raw_catalog["catalog_version"],
        "SPEC_LOCK_INVALID.catalog.catalog_version",
    )
    if not SEMVER_RE.fullmatch(catalog_version):
        raise SpecError(
            "SPEC_LOCK_INVALID.catalog.catalog_version: "
            "expected MAJOR.MINOR.PATCH"
        )
    catalog_digest = _expect_string(
        raw_catalog["sha256"],
        "SPEC_LOCK_INVALID.catalog.sha256",
    )
    if not SHA256_RE.fullmatch(catalog_digest):
        raise SpecError(
            "SPEC_LOCK_INVALID.catalog.sha256: expected lowercase SHA-256"
        )
    source = _parse_catalog_source(
        raw_catalog["source"],
        "SPEC_LOCK_INVALID.catalog.source",
    )
    resolved_revision = _expect_string(
        raw_catalog["resolved_revision"],
        "SPEC_LOCK_INVALID.catalog.resolved_revision",
    )
    if not GIT_COMMIT_RE.fullmatch(resolved_revision):
        raise SpecError(
            "SPEC_LOCK_INVALID.catalog.resolved_revision: "
            "expected a full lowercase Git commit"
        )

    raw_specs = data["specs"]
    if not isinstance(raw_specs, list) or not raw_specs:
        raise SpecError("SPEC_LOCK_INVALID.specs: expected a non-empty array")
    if len(raw_specs) > MAX_SPEC_COUNT:
        raise SpecError(
            f"SPEC_LOCK_INVALID.specs: exceeds {MAX_SPEC_COUNT} entries"
        )
    specs: list[CatalogSpec] = []
    by_id: dict[str, CatalogSpec] = {}
    installed_paths: set[str] = set()
    source_paths: set[str] = set()
    for index, raw_spec in enumerate(raw_specs):
        label = f"SPEC_LOCK_INVALID.specs[{index}]"
        item = _expect_object(raw_spec, label)
        _expect_exact_keys(
            item,
            required={
                "id",
                "version",
                "source_path",
                "installed_path",
                "sha256",
                "requires",
                "applies_to",
                "description",
            },
            label=label,
        )
        spec_id = _expect_string(item["id"], f"{label}.id")
        if not SPEC_ID_RE.fullmatch(spec_id):
            raise SpecError(f"{label}.id: invalid Spec ID: {spec_id!r}")
        if spec_id in by_id:
            raise SpecError(f"{label}.id: duplicate Spec ID: {spec_id}")
        version = _expect_string(item["version"], f"{label}.version")
        if not SEMVER_RE.fullmatch(version):
            raise SpecError(f"{label}.version: expected MAJOR.MINOR.PATCH")
        source_path = _safe_relative(
            item["source_path"],
            f"{label}.source_path",
        )
        if not source_path.endswith(".md"):
            raise SpecError(f"{label}.source_path: expected Markdown")
        if source_path in source_paths:
            raise SpecError(
                f"{label}.source_path: duplicate path: {source_path}"
            )
        source_paths.add(source_path)
        installed_path = _safe_relative(
            item["installed_path"],
            f"{label}.installed_path",
        )
        expected_installed = _managed_path(spec_id)
        if installed_path != expected_installed:
            raise SpecError(
                f"{label}.installed_path: expected {expected_installed!r}"
            )
        if installed_path in installed_paths:
            raise SpecError(
                f"{label}.installed_path: duplicate path: {installed_path}"
            )
        installed_paths.add(installed_path)
        digest = _expect_string(item["sha256"], f"{label}.sha256")
        if not SHA256_RE.fullmatch(digest):
            raise SpecError(f"{label}.sha256: expected lowercase SHA-256")
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
        spec = CatalogSpec(
            spec_id=spec_id,
            version=version,
            source_path=source_path,
            sha256=digest,
            required=False,
            requires=requires,
            applies_to=applies_to,
            description=_expect_string(
                item["description"],
                f"{label}.description",
            ),
            detection=None,
        )
        specs.append(spec)
        by_id[spec_id] = spec
    for spec in specs:
        missing = sorted(set(spec.requires) - set(by_id))
        if missing:
            raise SpecError(
                f"SPEC_LOCK_DEPENDENCY_MISSING: {spec.spec_id}: "
                f"{', '.join(missing)}"
            )
    return SpecLock(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        catalog_digest=catalog_digest,
        source=source,
        resolved_revision=resolved_revision,
        specs=tuple(specs),
        owner=owner,
    )


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_index(
    catalog_id: str,
    catalog_version: str,
    catalog_digest: str,
    resolved_revision: str,
    selected: tuple[CatalogSpec, ...],
    project_specs: tuple[ProjectSpec, ...],
    owner: str = SPEC_OWNER,
) -> bytes:
    lines = [
        "# Engineering Specs",
        "",
        f"<!-- Generated by {owner}. Do not edit this file. -->",
        "",
        "Before implementation or review, read every entry whose scope matches",
        "the files being changed. More specific project guidance takes precedence",
        "only when it explicitly declares the override.",
        "",
        f"Catalog: `{catalog_id}@{catalog_version}` "
        f"(`git:{resolved_revision}`, `sha256:{catalog_digest}`)",
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
    initial_source: dict[str, str],
    operation: str,
    update_source: dict[str, str] | None,
    requested_spec_ids: tuple[str, ...] | None,
) -> tuple[
    SpecManifest,
    Catalog,
    tuple[str, ...],
    bytes | None,
    SpecLock | None,
]:
    manifest_path = repo / SPEC_MANIFEST
    lock_path = repo / SPEC_LOCK
    if manifest_path.exists():
        manifest = parse_manifest(manifest_path)
        manifest_write: bytes | None = None
        if operation == "update" and update_source is not None:
            source = _parse_catalog_source(
                update_source,
                "SPEC_CATALOG_SOURCE_INVALID",
            )
            if source != manifest.catalog:
                manifest = SpecManifest(
                    catalog=source,
                    spec_ids=manifest.spec_ids,
                    project_specs=manifest.project_specs,
                    owner=manifest.owner,
                )
                manifest_write = _json_bytes(manifest_data(manifest))
    else:
        if lock_path.exists():
            raise SpecError(
                f"SPEC_MANIFEST_MISSING: {SPEC_MANIFEST}: "
                "a lock exists without its project manifest"
            )
        source = _parse_catalog_source(
            initial_source,
            "SPEC_CATALOG_SOURCE_INVALID",
        )
        catalog = resolve_git_catalog(source, source["ref"])
        manifest, detected = _initial_manifest(
            repo,
            catalog,
            source,
            requested_spec_ids,
        )
        return (
            manifest,
            catalog,
            detected,
            _json_bytes(manifest_data(manifest)),
            None,
        )

    locked: SpecLock | None = None
    if lock_path.exists():
        locked = parse_lock(lock_path)
    if operation == "sync" and locked is not None:
        if locked.source != manifest.catalog:
            raise SpecError(
                "SPEC_LOCK_SOURCE_MISMATCH: manifest source differs from "
                "the lock; run foundryctl spec update after review"
            )
        revision = locked.resolved_revision
    else:
        revision = manifest.catalog["ref"]
    catalog = resolve_git_catalog(manifest.catalog, revision)
    if (
        operation == "sync"
        and locked is not None
        and catalog.resolved_revision != locked.resolved_revision
    ):
        raise SpecError(
            "SPEC_LOCK_REVISION_MISMATCH: fetched revision differs from "
            "the locked commit"
        )
    detected = detect_specs(repo, catalog)
    if requested_spec_ids is not None:
        if operation != "update":
            raise SpecError(
                "SPEC_SELECTION_REQUIRES_UPDATE: an existing manifest may "
                "change selection only through spec update"
            )
        selected_ids = configured_spec_ids(catalog, requested_spec_ids)
        if selected_ids != manifest.spec_ids:
            manifest = SpecManifest(
                catalog=manifest.catalog,
                spec_ids=selected_ids,
                project_specs=manifest.project_specs,
                owner=manifest.owner,
            )
            manifest_write = _json_bytes(manifest_data(manifest))
    return (
        manifest,
        catalog,
        detected,
        manifest_write,
        locked,
    )


def _stale_managed_warnings(
    repo: Path,
    selected: tuple[CatalogSpec, ...],
    planned_removals: Iterable[str] = (),
) -> list[str]:
    root = repo / MANAGED_ROOT
    if not root.is_dir() or root.is_symlink():
        return []
    expected = {
        PurePosixPath(_managed_path(spec.spec_id))
        for spec in selected
    }
    expected.add(PurePosixPath(MANAGED_INDEX))
    expected.update(PurePosixPath(path) for path in planned_removals)
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
    initial_source: dict[str, str],
    *,
    operation: str,
    allow_replace: bool,
    update_source: dict[str, str] | None = None,
    requested_spec_ids: tuple[str, ...] | None = None,
) -> SpecPlan:
    if operation not in {"plan", "sync", "update"}:
        raise SpecError(f"SPEC_OPERATION_INVALID: {operation}")
    effective_operation = "sync" if operation == "plan" else operation
    manifest, catalog, detected, manifest_write, previous_lock = (
        _prepare_manifest(
            repo,
            initial_source,
            effective_operation,
            update_source,
            requested_spec_ids,
        )
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
        writes.append(
            PlannedWrite(
                path=_managed_path(spec.spec_id),
                content=catalog.contents[spec.source_path],
                role="managed_spec",
            )
        )
    writes.append(
        PlannedWrite(
            path=MANAGED_INDEX,
            content=render_index(
                catalog.catalog_id,
                catalog.catalog_version,
                catalog.digest,
                catalog.resolved_revision,
                selected,
                manifest.project_specs,
                manifest.owner,
            ),
            role="index",
        )
    )

    selected_ids = {spec.spec_id for spec in selected}
    deletes: list[PlannedDelete] = []
    delete_conflicts: list[dict[str, str]] = []
    if previous_lock is not None:
        for previous_spec in previous_lock.specs:
            if previous_spec.spec_id in selected_ids:
                continue
            relative = _managed_path(previous_spec.spec_id)
            reason = _path_conflict(repo, relative)
            if reason:
                delete_conflicts.append(
                    {
                        "action": "conflict",
                        "path": relative,
                        "reason": reason,
                    }
                )
                continue
            path = repo / relative
            if not path.exists():
                continue
            try:
                actual = _sha256_file(path)
            except OSError as exc:
                delete_conflicts.append(
                    {
                        "action": "conflict",
                        "path": relative,
                        "reason": (
                            "SPEC_MANAGED_REMOVAL_UNREADABLE: " + str(exc)
                        ),
                    }
                )
                continue
            if actual != previous_spec.sha256:
                delete_conflicts.append(
                    {
                        "action": "conflict",
                        "path": relative,
                        "reason": (
                            "SPEC_MANAGED_REMOVAL_DRIFT: current bytes do "
                            "not match the previous lock"
                        ),
                    }
                )
                continue
            deletes.append(
                PlannedDelete(
                    path=relative,
                    sha256=previous_spec.sha256,
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
                        "run foundryctl spec sync --apply after review"
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

    actions.extend(delete_conflicts)
    actions.extend(
        {"action": "remove_file", "path": item.path}
        for item in deletes
    )

    warnings = _stale_managed_warnings(
        repo,
        selected,
        (item.path for item in deletes),
    )
    return SpecPlan(
        operation=operation,
        catalog_id=catalog.catalog_id,
        catalog_version=catalog.catalog_version,
        catalog_digest=catalog.digest,
        catalog_source=dict(manifest.catalog),
        resolved_revision=catalog.resolved_revision,
        detected_spec_ids=detected,
        configured_spec_ids=manifest.spec_ids,
        selected_spec_ids=tuple(spec.spec_id for spec in selected),
        available_specs=catalog.ordered_specs,
        actions=tuple(actions),
        warnings=tuple(warnings),
        writes=tuple(writes),
        deletes=tuple(deletes),
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
) -> tuple[list[str], list[str], list[str]]:
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
    removed: list[str] = []
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
    managed_root = repo / MANAGED_ROOT
    for delete in plan.deletes:
        action = action_by_path.get(delete.path)
        if action != "remove_file":
            raise SpecError(
                f"SPEC_PLAN_INVALID: no remove action for {delete.path}"
            )
        reason = _path_conflict(repo, delete.path)
        if reason:
            raise SpecError(
                f"SPEC_PREFLIGHT_CHANGED: {delete.path}: {reason}"
            )
        path = repo / delete.path
        if not path.is_file():
            raise SpecError(
                f"SPEC_PREFLIGHT_CHANGED: {delete.path}: file is missing"
            )
        try:
            actual = _sha256_file(path)
        except OSError as exc:
            raise SpecError(
                f"SPEC_PREFLIGHT_CHANGED: {delete.path}: {exc}"
            ) from exc
        if actual != delete.sha256:
            raise SpecError(
                f"SPEC_PREFLIGHT_CHANGED: {delete.path}: current bytes no "
                "longer match the previous lock"
            )
        path.unlink()
        removed.append(delete.path)
        parent = path.parent
        while parent != managed_root and managed_root in parent.parents:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return created, updated, removed


def validate_spec_state(
    repo: Path,
    *,
    require_manifest: bool,
) -> tuple[list[str], list[str]]:
    manifest_path = repo / SPEC_MANIFEST
    if not manifest_path.exists():
        if require_manifest:
            return [
                f"SPEC_MANIFEST_MISSING: {SPEC_MANIFEST}: "
                "run foundryctl spec sync --apply"
            ], []
        return [], [
            f"SPEC_MANIFEST_MISSING: {SPEC_MANIFEST}: "
            "run foundryctl bootstrap --profile codex --apply"
        ]
    try:
        manifest = parse_manifest(manifest_path)
    except SpecError as exc:
        return [str(exc)], []

    errors: list[str] = []
    warnings: list[str] = []
    if manifest.owner in LEGACY_SPEC_OWNERS:
        warnings.append(
            f"SPEC_LEGACY_OWNER: {SPEC_MANIFEST}: "
            f"{manifest.owner!r} remains readable; new manifests use "
            f"{SPEC_OWNER!r}"
        )
    lock_path = repo / SPEC_LOCK
    if not lock_path.exists():
        return [
            f"SPEC_LOCK_MISSING: {SPEC_LOCK}: "
            "run foundryctl spec sync --apply"
        ], warnings
    try:
        lock = parse_lock(lock_path)
        _validate_project_specs(repo, manifest.project_specs)
    except SpecError as exc:
        return [str(exc)], warnings
    if lock.owner in LEGACY_SPEC_OWNERS:
        warnings.append(
            f"SPEC_LEGACY_OWNER: {SPEC_LOCK}: "
            f"{lock.owner!r} remains readable; new locks use {SPEC_OWNER!r}"
        )
    if lock.owner != manifest.owner:
        errors.append(
            "SPEC_LOCK_OWNER_MISMATCH: specs.lock.json owner differs from "
            "specs.json"
        )

    if lock.source != manifest.catalog:
        errors.append(
            "SPEC_LOCK_SOURCE_MISMATCH: lock source differs from specs.json; "
            "run foundryctl spec update after review"
        )
    by_id = {spec.spec_id: spec for spec in lock.specs}
    missing = sorted(set(manifest.spec_ids) - set(by_id))
    if missing:
        errors.append(
            "SPEC_LOCK_SELECTION_MISSING: " + ", ".join(missing)
        )
    reachable: set[str] = set()
    visiting: list[str] = []

    def visit(spec_id: str) -> None:
        if spec_id in reachable:
            return
        if spec_id in visiting:
            cycle = " -> ".join((*visiting, spec_id))
            raise SpecError(f"SPEC_LOCK_DEPENDENCY_CYCLE: {cycle}")
        spec = by_id.get(spec_id)
        if spec is None:
            raise SpecError(f"SPEC_LOCK_DEPENDENCY_MISSING: {spec_id}")
        visiting.append(spec_id)
        for dependency in spec.requires:
            visit(dependency)
        visiting.pop()
        reachable.add(spec_id)

    try:
        for spec_id in manifest.spec_ids:
            if spec_id in by_id:
                visit(spec_id)
    except SpecError as exc:
        errors.append(str(exc))
    stale_lock_ids = sorted(set(by_id) - reachable)
    if stale_lock_ids:
        errors.append(
            "SPEC_LOCK_SELECTION_EXTRA: " + ", ".join(stale_lock_ids)
        )

    for spec in lock.specs:
        relative = _managed_path(spec.spec_id)
        reason = _path_conflict(repo, relative)
        if reason:
            errors.append(f"SPEC_PATH_CONFLICT: {relative}: {reason}")
            continue
        path = repo / relative
        if not path.is_file():
            errors.append(
                f"SPEC_MANAGED_FILE_MISSING: {relative}: "
                "run foundryctl spec sync --apply"
            )
            continue
        try:
            actual = _sha256_file(path)
        except OSError as exc:
            errors.append(
                f"SPEC_MANAGED_FILE_UNREADABLE: {relative}: {exc}"
            )
            continue
        if actual != spec.sha256:
            errors.append(
                f"SPEC_MANAGED_CONTENT_DRIFT: {relative}: "
                f"lock {spec.sha256}; actual {actual}; "
                "run foundryctl spec sync --apply after review"
            )

    expected_index = render_index(
        lock.catalog_id,
        lock.catalog_version,
        lock.catalog_digest,
        lock.resolved_revision,
        lock.specs,
        manifest.project_specs,
        manifest.owner,
    )
    index_reason = _path_conflict(repo, MANAGED_INDEX)
    if index_reason:
        errors.append(
            f"SPEC_PATH_CONFLICT: {MANAGED_INDEX}: {index_reason}"
        )
    else:
        index_path = repo / MANAGED_INDEX
        if not index_path.is_file():
            errors.append(
                f"SPEC_INDEX_MISSING: {MANAGED_INDEX}: "
                "run foundryctl spec sync --apply"
            )
        else:
            try:
                actual_index = index_path.read_bytes()
            except OSError as exc:
                errors.append(
                    f"SPEC_INDEX_UNREADABLE: {MANAGED_INDEX}: {exc}"
                )
            else:
                if actual_index != expected_index:
                    errors.append(
                        f"SPEC_INDEX_DRIFT: {MANAGED_INDEX}: "
                        "run foundryctl spec sync --apply after review"
                    )

    warnings.extend(_stale_managed_warnings(repo, lock.specs))
    return errors, warnings


def plan_payload(
    plan: SpecPlan,
    *,
    mode: str,
    created: Iterable[str] = (),
    updated: Iterable[str] = (),
    removed: Iterable[str] = (),
) -> dict[str, object]:
    required = {
        spec.spec_id for spec in plan.available_specs if spec.required
    }
    detected = set(plan.detected_spec_ids)
    configured = set(plan.configured_spec_ids)
    selected = set(plan.selected_spec_ids)
    return {
        "operation": plan.operation,
        "mode": mode,
        "catalog": {
            "catalog_id": plan.catalog_id,
            "catalog_version": plan.catalog_version,
            "sha256": plan.catalog_digest,
            "source": dict(plan.catalog_source),
            "resolved_revision": plan.resolved_revision,
        },
        "detected_specs": list(plan.detected_spec_ids),
        "recommended_specs": [
            spec.spec_id
            for spec in plan.available_specs
            if spec.spec_id in detected and spec.spec_id not in required
        ],
        "required_specs": [
            spec.spec_id
            for spec in plan.available_specs
            if spec.spec_id in required
        ],
        "configured_specs": list(plan.configured_spec_ids),
        "selected_specs": list(plan.selected_spec_ids),
        "available_specs": [
            {
                "id": spec.spec_id,
                "version": spec.version,
                "description": spec.description,
                "required": spec.required,
                "requires": list(spec.requires),
                "recommended": spec.spec_id in detected,
                "configured": spec.spec_id in configured,
                "selected": spec.spec_id in selected,
            }
            for spec in plan.available_specs
        ],
        "actions": list(plan.actions),
        "warnings": list(plan.warnings),
        "created": list(created),
        "updated": list(updated),
        "removed": list(removed),
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
                "catalog_version": catalog.catalog_version,
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
