#!/usr/bin/env python3
"""Run RepoFoundry's product-neutral local Engineering Spec activation engine."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ROUTER_VERSION = 2
PROTOCOL_VERSION = 1
MANIFEST_PATH = "docs/.engineering/specs.json"
LOCK_PATH = "docs/.engineering/specs.lock.json"
INDEX_PATH = "docs/agent-guides/managed/index.md"
MAX_JSON_BYTES = 1024 * 1024
MAX_CONTEXT_BYTES = 128 * 1024
MAX_ENTRIES = 256
SPEC_ID_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?"
    r"(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)*$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIREMENT_RE = re.compile(
    r"^###\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\s+[—-]\s+",
    re.MULTILINE,
)
ADAPTER_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
HANDOFF_LABELS = (
    "Activated specifications:",
    "Activated requirements:",
    "Verification:",
    "Exceptions:",
    "Compatibility or migration:",
)
DISALLOWED_BROAD_GLOBS = frozenset({"*", "**", "**/*"})
NORMALIZED_EVENTS = frozenset(
    {"session_start", "subagent_start", "before_mutation", "stop"}
)
TOOL_CATEGORIES = frozenset({"read", "file_write", "command_write"})


class RouterError(RuntimeError):
    """Raised when local routing state violates its boundary contract."""


@dataclass(frozen=True)
class SpecEntry:
    key: str
    version: str
    path: str
    sha256: str | None
    requires: tuple[str, ...]
    applies_to: tuple[str, ...]
    description: str
    project_owned: bool


@dataclass(frozen=True)
class SpecState:
    catalog_id: str
    catalog_version: str
    revision: str
    entries: tuple[SpecEntry, ...]
    by_key: dict[str, SpecEntry]


def _json_output(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bytes(path: Path, label: str, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RouterError(f"{label}: expected a non-symlink regular file: {path}")
    try:
        value = path.read_bytes()
    except OSError as exc:
        raise RouterError(f"{label}: {path}: {exc}") from exc
    if len(value) > maximum:
        raise RouterError(f"{label}: {path}: exceeds {maximum} bytes")
    return value


def _load_json(path: Path, label: str) -> dict[str, object]:
    raw = _read_bytes(path, label, MAX_JSON_BYTES)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RouterError(f"{label}: {path}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RouterError(f"{label}: {path}: expected an object")
    return value


def _git(root: Path, *arguments: str, check: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if check:
            raise RouterError(f"ROUTER_GIT_FAILED: git {' '.join(arguments)}: {exc}") from exc
        return ""
    if result.returncode:
        if check:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RouterError(
                f"ROUTER_GIT_FAILED: git {' '.join(arguments)}: {detail}"
            )
        return ""
    return result.stdout


def repository_root(value: str | Path) -> Path:
    start = Path(value).expanduser().resolve()
    if start.is_file():
        start = start.parent
    output = _git(start, "rev-parse", "--show-toplevel", check=False).strip()
    if output:
        return Path(output).resolve()
    current = start
    while True:
        if (current / MANIFEST_PATH).is_file():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise RouterError(f"ROUTER_REPOSITORY_NOT_FOUND: {start}")


def _safe_relative(value: object, label: str, *, allow_glob: bool = False) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < 32 for character in value)
    ):
        raise RouterError(f"{label}: expected a non-empty string")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RouterError(f"{label}: path must be repository-relative: {value!r}")
    if not allow_glob and any(char in normalized for char in "*?["):
        raise RouterError(f"{label}: globs are not allowed: {value!r}")
    return path.as_posix()


def _resolve_regular(root: Path, relative: str, label: str) -> Path:
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RouterError(f"{label}: symbolic links are not supported: {relative}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RouterError(f"{label}: path escapes repository: {relative}") from exc
    if not path.is_file():
        raise RouterError(f"{label}: file is missing: {relative}")
    return path


def _strings(value: object, label: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RouterError(f"{label}: expected an array of strings")
    result = tuple(value)
    if nonempty and not result:
        raise RouterError(f"{label}: expected at least one entry")
    if len(result) != len(set(result)):
        raise RouterError(f"{label}: duplicate entries")
    return result


def load_state(root: Path) -> SpecState:
    manifest = _load_json(root / MANIFEST_PATH, "ROUTER_MANIFEST_INVALID")
    lock = _load_json(root / LOCK_PATH, "ROUTER_LOCK_INVALID")
    project_specs = manifest.get("project_specs")
    raw_specs = lock.get("specs")
    catalog = lock.get("catalog")
    if not isinstance(project_specs, list):
        raise RouterError("ROUTER_MANIFEST_INVALID.project_specs: expected an array")
    if not isinstance(raw_specs, list) or not raw_specs or len(raw_specs) > MAX_ENTRIES:
        raise RouterError("ROUTER_LOCK_INVALID.specs: expected a bounded non-empty array")
    if not isinstance(catalog, dict):
        raise RouterError("ROUTER_LOCK_INVALID.catalog: expected an object")
    for field in ("catalog_id", "catalog_version", "resolved_revision"):
        if not isinstance(catalog.get(field), str) or not catalog[field]:
            raise RouterError(f"ROUTER_LOCK_INVALID.catalog.{field}: expected string")

    entries: list[SpecEntry] = []
    by_key: dict[str, SpecEntry] = {}
    for index, raw in enumerate(raw_specs):
        label = f"ROUTER_LOCK_INVALID.specs[{index}]"
        if not isinstance(raw, dict):
            raise RouterError(f"{label}: expected an object")
        key = raw.get("id")
        if not isinstance(key, str) or not SPEC_ID_RE.fullmatch(key):
            raise RouterError(f"{label}.id: invalid Spec ID")
        if key in by_key:
            raise RouterError(f"{label}.id: duplicate Spec ID: {key}")
        version = raw.get("version")
        digest = raw.get("sha256")
        if not isinstance(version, str) or not version:
            raise RouterError(f"{label}.version: expected string")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise RouterError(f"{label}.sha256: expected lowercase SHA-256")
        path = _safe_relative(raw.get("installed_path"), f"{label}.installed_path")
        expected = f"docs/agent-guides/managed/{key}.md"
        if path != expected:
            raise RouterError(f"{label}.installed_path: expected {expected}")
        requires = _strings(raw.get("requires"), f"{label}.requires")
        applies_to = _strings(
            raw.get("applies_to"), f"{label}.applies_to", nonempty=True
        )
        description = raw.get("description")
        if not isinstance(description, str) or not description.strip():
            raise RouterError(f"{label}.description: expected non-empty string")
        managed_path = _resolve_regular(root, path, "ROUTER_MANAGED_FILE_INVALID")
        actual = _sha256(_read_bytes(managed_path, "ROUTER_MANAGED_FILE_INVALID", MAX_CONTEXT_BYTES))
        if actual != digest:
            raise RouterError(
                f"ROUTER_MANAGED_CONTENT_DRIFT: {path}: lock {digest}; actual {actual}"
            )
        entry = SpecEntry(
            key=key,
            version=version,
            path=path,
            sha256=digest,
            requires=requires,
            applies_to=applies_to,
            description=description,
            project_owned=False,
        )
        entries.append(entry)
        by_key[key] = entry

    for entry in entries:
        missing = sorted(set(entry.requires) - set(by_key))
        if missing:
            raise RouterError(
                f"ROUTER_DEPENDENCY_MISSING: {entry.key}: {', '.join(missing)}"
            )

    for index, raw in enumerate(project_specs):
        label = f"ROUTER_MANIFEST_INVALID.project_specs[{index}]"
        if not isinstance(raw, dict):
            raise RouterError(f"{label}: expected an object")
        path = _safe_relative(raw.get("path"), f"{label}.path")
        if not path.endswith(".md"):
            raise RouterError(f"{label}.path: expected Markdown")
        _resolve_regular(root, path, "ROUTER_PROJECT_FILE_INVALID")
        key = f"project:{path}"
        if key in by_key:
            raise RouterError(f"{label}.path: duplicate: {path}")
        applies_to = _strings(
            raw.get("applies_to"), f"{label}.applies_to", nonempty=True
        )
        description = raw.get("description")
        if not isinstance(description, str) or not description.strip():
            raise RouterError(f"{label}.description: expected non-empty string")
        entry = SpecEntry(
            key=key,
            version="project",
            path=path,
            sha256=None,
            requires=(),
            applies_to=applies_to,
            description=description,
            project_owned=True,
        )
        entries.append(entry)
        by_key[key] = entry

    return SpecState(
        catalog_id=str(catalog["catalog_id"]),
        catalog_version=str(catalog["catalog_version"]),
        revision=str(catalog["resolved_revision"]),
        entries=tuple(entries),
        by_key=by_key,
    )


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:])
    )


def candidate_entries(state: SpecState, paths: Iterable[str]) -> tuple[SpecEntry, ...]:
    selected_paths = tuple(paths)
    return tuple(
        entry
        for entry in state.entries
        if any(
            _matches(path, scope)
            for path in selected_paths
            for scope in entry.applies_to
        )
    )


def dependency_closure(state: SpecState, keys: Iterable[str]) -> tuple[SpecEntry, ...]:
    result: list[SpecEntry] = []
    done: set[str] = set()
    visiting: list[str] = []

    def visit(key: str) -> None:
        if key in done:
            return
        if key in visiting:
            raise RouterError("ROUTER_DEPENDENCY_CYCLE: " + " -> ".join((*visiting, key)))
        entry = state.by_key.get(key)
        if entry is None:
            raise RouterError(f"ROUTER_SPEC_UNKNOWN: {key}")
        visiting.append(key)
        for dependency in entry.requires:
            visit(dependency)
        visiting.pop()
        done.add(key)
        result.append(entry)

    for key in keys:
        visit(key)
    return tuple(result)


def entry_payload(root: Path, entry: SpecEntry) -> dict[str, object]:
    content = _read_bytes(
        _resolve_regular(root, entry.path, "ROUTER_SPEC_FILE_INVALID"),
        "ROUTER_SPEC_FILE_INVALID",
        MAX_CONTEXT_BYTES,
    )
    text = content.decode("utf-8", errors="strict")
    return {
        "id": entry.key,
        "version": entry.version,
        "path": entry.path,
        "sha256": entry.sha256 or _sha256(content),
        "requires": list(entry.requires),
        "applies_to": list(entry.applies_to),
        "description": entry.description,
        "requirements": sorted(set(REQUIREMENT_RE.findall(text))),
        "project_owned": entry.project_owned,
    }


def _state_base(root: Path) -> Path:
    git_dir = _git(root, "rev-parse", "--git-dir", check=False).strip()
    if git_dir:
        path = Path(git_dir)
        if not path.is_absolute():
            path = root / path
        return path.resolve() / "repo-foundry" / "spec-activation-v1"
    digest = _sha256(str(root.resolve()).encode("utf-8"))
    return Path(tempfile.gettempdir()) / "repo-foundry-spec-activation-v1" / digest


def _state_path(
    root: Path,
    adapter_id: str,
    session_id: str,
    turn_id: str,
) -> Path:
    digest = _sha256(
        f"{adapter_id}\x00{session_id}\x00{turn_id}".encode("utf-8")
    )
    return _state_base(root) / f"{digest}.json"


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _load_runtime(
    root: Path,
    adapter_id: str,
    session_id: str,
    turn_id: str,
) -> dict[str, object] | None:
    path = _state_path(root, adapter_id, session_id, turn_id)
    if not path.exists():
        return None
    return _load_json(path, "ROUTER_RUNTIME_INVALID")


def _changed_file_state(root: Path) -> dict[str, str]:
    paths: set[str] = set()
    for arguments in (
        ("diff", "--name-only", "--no-renames", "-z"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        output = _git(root, *arguments, check=False)
        paths.update(item for item in output.split("\x00") if item)
    state: dict[str, str] = {}
    for raw in sorted(paths):
        try:
            relative = _safe_relative(raw, "ROUTER_GIT_PATH")
        except RouterError:
            continue
        path = root / relative
        if path.is_symlink():
            state[relative] = "symlink"
        elif path.is_file():
            try:
                state[relative] = _sha256(path.read_bytes())
            except OSError:
                state[relative] = "unreadable"
        else:
            state[relative] = "missing"
    return state


def _baseline(root: Path) -> dict[str, object]:
    return {
        "head": _git(root, "rev-parse", "HEAD", check=False).strip(),
        "worktree": _changed_file_state(root),
    }


def _paths_changed_since(root: Path, baseline: object) -> tuple[str, ...]:
    if not isinstance(baseline, dict):
        raise RouterError("ROUTER_RUNTIME_INVALID.baseline: expected object")
    old_state = baseline.get("worktree")
    if not isinstance(old_state, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in old_state.items()
    ):
        raise RouterError("ROUTER_RUNTIME_INVALID.baseline.worktree: expected string map")
    current = _changed_file_state(root)
    changed = {
        path
        for path in set(old_state) | set(current)
        if old_state.get(path) != current.get(path)
    }
    old_head = baseline.get("head")
    new_head = _git(root, "rev-parse", "HEAD", check=False).strip()
    if isinstance(old_head, str) and old_head and new_head and old_head != new_head:
        output = _git(
            root,
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            f"{old_head}..{new_head}",
            check=False,
        )
        changed.update(item for item in output.split("\x00") if item)
    return tuple(sorted(changed))


def _initialize_turn(root: Path, payload: dict[str, object]) -> dict[str, object]:
    adapter_id = payload.get("adapter_id")
    session_id = payload.get("session_id")
    turn_id = payload.get("turn_id")
    if not isinstance(adapter_id, str) or not ADAPTER_ID_RE.fullmatch(adapter_id):
        raise RouterError("ROUTER_EVENT_INVALID.adapter_id")
    if not isinstance(session_id, str) or not session_id:
        raise RouterError("ROUTER_EVENT_INVALID.session_id")
    if not isinstance(turn_id, str) or not turn_id:
        raise RouterError("ROUTER_EVENT_INVALID.turn_id")
    existing = _load_runtime(root, adapter_id, session_id, turn_id)
    if existing is not None:
        return existing
    value: dict[str, object] = {
        "version": ROUTER_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "adapter_id": adapter_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "prompt_sha256": _sha256(str(payload.get("prompt", "")).encode("utf-8")),
        "baseline": _baseline(root),
        "activation": None,
        "context_injected": False,
    }
    _atomic_json(_state_path(root, adapter_id, session_id, turn_id), value)
    return value


def _normalize_planned_path(root: Path, raw: str) -> str:
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            raw = candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise RouterError(f"ROUTER_PATH_OUTSIDE_REPOSITORY: {candidate}") from exc
    normalized = _safe_relative(raw, "ROUTER_PLANNED_PATH", allow_glob=True)
    if normalized in DISALLOWED_BROAD_GLOBS:
        raise RouterError(
            "ROUTER_PLANNED_PATH_TOO_BROAD: use exact paths or a bounded "
            f"subtree glob instead of {normalized!r}"
        )
    return normalized


def command_candidates(args: argparse.Namespace) -> int:
    root = repository_root(args.repo)
    state = load_state(root)
    paths = tuple(_normalize_planned_path(root, value) for value in args.path)
    candidates = candidate_entries(state, paths)
    _json_output(
        {
            "router_version": ROUTER_VERSION,
            "catalog": {
                "id": state.catalog_id,
                "version": state.catalog_version,
                "revision": state.revision,
            },
            "paths": list(paths),
            "candidates": [entry_payload(root, item) for item in candidates],
            "next": "Read each candidate Applicability section, then run activate.",
        }
    )
    return 0


def command_begin(args: argparse.Namespace) -> int:
    root = repository_root(args.repo)
    runtime = _initialize_turn(
        root,
        {
            "adapter_id": args.adapter_id,
            "session_id": args.session_id,
            "turn_id": args.turn_id,
            "prompt": args.prompt or "",
        },
    )
    _json_output(
        {
            "router_version": ROUTER_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "adapter_id": runtime["adapter_id"],
            "session_id": runtime["session_id"],
            "turn_id": runtime["turn_id"],
            "initialized": True,
            "next": "Run candidates, decide Applicability, then activate before any write.",
        }
    )
    return 0


def command_activate(args: argparse.Namespace) -> int:
    root = repository_root(args.repo)
    runtime = _load_runtime(
        root,
        args.adapter_id,
        args.session_id,
        args.turn_id,
    )
    if runtime is None:
        raise RouterError(
            "ROUTER_TURN_NOT_INITIALIZED: no lifecycle adapter initialized "
            "this turn; run begin before any write"
        )
    state = load_state(root)
    paths = tuple(dict.fromkeys(_normalize_planned_path(root, value) for value in args.path))
    if not paths:
        raise RouterError("ROUTER_PATHS_REQUIRED: provide at least one --path")
    candidates = {entry.key for entry in candidate_entries(state, paths)}
    requested = tuple(dict.fromkeys(args.spec or ()))
    if args.none:
        if requested:
            raise RouterError("ROUTER_DECISION_INVALID: --none cannot be combined with --spec")
        if not isinstance(args.reason, str) or not args.reason.strip():
            raise RouterError("ROUTER_NONE_REASON_REQUIRED: --none requires --reason")
        selected: tuple[SpecEntry, ...] = ()
        decision = "none"
        reason = args.reason.strip()
    else:
        if not requested:
            raise RouterError("ROUTER_SPEC_REQUIRED: use --spec or --none")
        unknown = sorted(set(requested) - set(state.by_key))
        if unknown:
            raise RouterError("ROUTER_SPEC_UNKNOWN: " + ", ".join(unknown))
        irrelevant = sorted(set(requested) - candidates)
        if irrelevant:
            raise RouterError(
                "ROUTER_SPEC_NOT_CANDIDATE: " + ", ".join(irrelevant)
            )
        selected = dependency_closure(state, requested)
        decision = "activated"
        reason = ""

    activation = {
        "decision": decision,
        "reason": reason,
        "planned_paths": list(paths),
        "requested_specs": list(requested),
        "activated_specs": [entry_payload(root, item) for item in selected],
    }
    runtime["activation"] = activation
    runtime["context_injected"] = False
    _atomic_json(
        _state_path(root, args.adapter_id, args.session_id, args.turn_id),
        runtime,
    )
    _json_output(
        {
            "adapter_id": args.adapter_id,
            "session_id": args.session_id,
            "turn_id": args.turn_id,
            **activation,
            "next": "Read every activated path. Trusted Hooks will inject the same content before the first write.",
        }
    )
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = repository_root(args.repo)
    runtime = _load_runtime(
        root,
        args.adapter_id,
        args.session_id,
        args.turn_id,
    )
    if runtime is None:
        raise RouterError("ROUTER_ACTIVATION_MISSING")
    _json_output(runtime)
    return 0


def _covered(path: str, planned: Iterable[str]) -> bool:
    return any(_matches(path, pattern) for pattern in planned)


def _activation(runtime: dict[str, object]) -> dict[str, object]:
    activation = runtime.get("activation")
    if not isinstance(activation, dict):
        raise RouterError("ROUTER_ACTIVATION_MISSING")
    planned = activation.get("planned_paths")
    specs = activation.get("activated_specs")
    decision = activation.get("decision")
    if decision not in {"activated", "none"}:
        raise RouterError("ROUTER_ACTIVATION_INVALID.decision")
    if not isinstance(planned, list) or not planned or any(not isinstance(item, str) for item in planned):
        raise RouterError("ROUTER_ACTIVATION_INVALID.planned_paths")
    if not isinstance(specs, list):
        raise RouterError("ROUTER_ACTIVATION_INVALID.activated_specs")
    return activation


def _audit(
    root: Path,
    runtime: dict[str, object],
    message: str | None,
) -> dict[str, object]:
    activation = _activation(runtime)
    changed = _paths_changed_since(root, runtime.get("baseline"))
    planned = tuple(str(item) for item in activation["planned_paths"])
    uncovered = tuple(path for path in changed if not _covered(path, planned))
    missing_labels = tuple(
        label for label in HANDOFF_LABELS if message is not None and label not in message
    )
    errors: list[str] = []
    if uncovered:
        errors.append("ROUTER_CHANGED_PATH_UNCOVERED: " + ", ".join(uncovered))
    if missing_labels:
        errors.append("ROUTER_HANDOFF_INCOMPLETE: " + ", ".join(missing_labels))
    return {
        "ok": not errors,
        "changed_paths": list(changed),
        "uncovered_paths": list(uncovered),
        "missing_handoff_labels": list(missing_labels),
        "errors": errors,
    }


def command_audit(args: argparse.Namespace) -> int:
    root = repository_root(args.repo)
    runtime = _load_runtime(
        root,
        args.adapter_id,
        args.session_id,
        args.turn_id,
    )
    if runtime is None:
        raise RouterError("ROUTER_ACTIVATION_MISSING")
    message = args.message
    if args.message_file:
        message = _read_bytes(
            Path(args.message_file), "ROUTER_MESSAGE_INVALID", MAX_CONTEXT_BYTES
        ).decode("utf-8", errors="strict")
    result = _audit(root, runtime, message)
    _json_output(result)
    return 0 if result["ok"] else 1


def _router_command(adapter_id: str, session_id: str, turn_id: str) -> str:
    relative = ".repo-foundry/engineering-specs/spec_router.py"
    return (
        f"python3 {relative} candidates --path <planned-path>\n"
        f"python3 {relative} activate --adapter-id {adapter_id} "
        f"--session-id {session_id} --turn-id {turn_id} "
        "--path <planned-path> "
        "(--spec <id> ... | --none --reason <reason>)"
    )


def _route_context(root: Path, payload: dict[str, object]) -> str:
    runtime = _initialize_turn(root, payload)
    adapter_id = str(runtime["adapter_id"])
    session_id = str(runtime["session_id"])
    turn_id = str(runtime["turn_id"])
    index = _read_bytes(
        root / INDEX_PATH,
        "ROUTER_INDEX_INVALID",
        MAX_CONTEXT_BYTES,
    ).decode("utf-8", errors="strict")
    return (
        "Engineering Specification routing is mandatory before implementation "
        "or review. File scope creates candidates, but Applicability and task "
        "intent decide activation. Record either applicable Spec IDs or an "
        "explicit no-Spec reason before any write.\n\n"
        f"Adapter ID: `{adapter_id}`\nSession ID: `{session_id}`\n"
        f"Turn ID: `{turn_id}`\n\n"
        f"Commands:\n{_router_command(adapter_id, session_id, turn_id)}\n\n"
        "Current locked routing index:\n\n" + index
    )


def _context_for_activation(root: Path, activation: dict[str, object]) -> str:
    specs = activation.get("activated_specs")
    if not isinstance(specs, list):
        raise RouterError("ROUTER_ACTIVATION_INVALID.activated_specs")
    if not specs:
        reason = activation.get("reason", "")
        return f"Engineering Spec activation decision: none. Reason: {reason}"
    chunks = ["Activated Engineering Specifications follow. Apply them before retrying the edit."]
    total = len(chunks[0].encode("utf-8"))
    for item in specs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise RouterError("ROUTER_ACTIVATION_INVALID.activated_specs entry")
        path = _safe_relative(item["path"], "ROUTER_ACTIVATED_PATH")
        content = _read_bytes(
            _resolve_regular(root, path, "ROUTER_ACTIVATED_FILE_INVALID"),
            "ROUTER_ACTIVATED_FILE_INVALID",
            MAX_CONTEXT_BYTES,
        )
        digest = item.get("sha256")
        if digest is not None and _sha256(content) != digest:
            raise RouterError(f"ROUTER_MANAGED_CONTENT_DRIFT: {path}")
        header = f"\n\n--- BEGIN {item.get('id')} ({path}) ---\n"
        footer = f"\n--- END {item.get('id')} ---"
        chunk = header + content.decode("utf-8", errors="strict") + footer
        total += len(chunk.encode("utf-8"))
        if total > MAX_CONTEXT_BYTES:
            raise RouterError(
                f"ROUTER_CONTEXT_TOO_LARGE: activated content exceeds {MAX_CONTEXT_BYTES} bytes"
            )
        chunks.append(chunk)
    return "".join(chunks)


def _deny(reason: str, *, context: str | None = None) -> dict[str, object]:
    output: dict[str, object] = {"decision": "deny", "reason": reason}
    if context is not None:
        output["context"] = context
    return output


def _event_identity(payload: dict[str, object]) -> tuple[str, str, str]:
    adapter_id = payload.get("adapter_id")
    session_id = payload.get("session_id")
    turn_id = payload.get("turn_id")
    if not isinstance(adapter_id, str) or not ADAPTER_ID_RE.fullmatch(adapter_id):
        raise RouterError("ROUTER_EVENT_INVALID.adapter_id")
    if not isinstance(session_id, str) or not session_id:
        raise RouterError("ROUTER_EVENT_INVALID.session_id")
    if not isinstance(turn_id, str) or not turn_id:
        raise RouterError("ROUTER_EVENT_INVALID.turn_id")
    return adapter_id, session_id, turn_id


def _before_mutation(
    root: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    adapter_id, session_id, turn_id = _event_identity(payload)
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        return _deny("Engineering Spec gate received an invalid normalized tool.")
    category = tool.get("category")
    if category not in TOOL_CATEGORIES:
        return _deny("Engineering Spec gate received an unsupported tool category.")
    if category == "read":
        return {"decision": "allow"}
    runtime = _load_runtime(root, adapter_id, session_id, turn_id)
    if runtime is None or not isinstance(runtime.get("activation"), dict):
        return _deny(
            "Record this turn's Engineering Spec activation before editing.\n"
            + _router_command(adapter_id, session_id, turn_id)
        )
    try:
        activation = _activation(runtime)
        if category == "file_write":
            raw_paths = tool.get("paths")
            if not isinstance(raw_paths, list) or not raw_paths or any(
                not isinstance(item, str) for item in raw_paths
            ):
                return _deny(
                    "Engineering Spec gate could not resolve mutation target paths."
                )
            targets = tuple(
                dict.fromkeys(_normalize_planned_path(root, item) for item in raw_paths)
            )
            planned = tuple(str(item) for item in activation["planned_paths"])
            uncovered = tuple(path for path in targets if not _covered(path, planned))
            if uncovered:
                return _deny(
                    "Extend Engineering Spec activation before editing uncovered paths: "
                    + ", ".join(uncovered)
                )
        if not bool(runtime.get("context_injected")):
            context = _context_for_activation(root, activation)
            runtime["context_injected"] = True
            _atomic_json(
                _state_path(root, adapter_id, session_id, turn_id),
                runtime,
            )
            return _deny(
                "Activated Engineering Specs were injected. Re-evaluate and retry the edit.",
                context=context,
            )
    except RouterError as exc:
        return _deny(str(exc))
    return {"decision": "allow"}


def _stop(root: Path, payload: dict[str, object]) -> dict[str, object]:
    adapter_id, session_id, turn_id = _event_identity(payload)
    runtime = _load_runtime(root, adapter_id, session_id, turn_id)
    if runtime is None:
        return {"decision": "allow"}
    changed = _paths_changed_since(root, runtime.get("baseline"))
    if not changed:
        return {"decision": "allow"}
    if not isinstance(runtime.get("activation"), dict):
        return {
            "decision": "deny",
            "reason": "Repository files changed without an Engineering Spec activation decision; activate and complete the required handoff.",
        }
    message = payload.get("message")
    result = _audit(root, runtime, message if isinstance(message, str) else "")
    if not result["ok"]:
        return {
            "decision": "deny",
            "reason": "Engineering Spec audit failed:\n- " + "\n- ".join(result["errors"]),
        }
    return {"decision": "allow"}


def process_event(root: Path, payload: dict[str, object]) -> dict[str, object]:
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise RouterError(
            "ROUTER_PROTOCOL_UNSUPPORTED: expected protocol_version "
            f"{PROTOCOL_VERSION}"
        )
    event = payload.get("event")
    if event not in NORMALIZED_EVENTS:
        raise RouterError(f"ROUTER_EVENT_UNSUPPORTED: {event!r}")
    _event_identity(payload)
    if event in {"session_start", "subagent_start"}:
        return {"decision": "allow", "context": _route_context(root, payload)}
    if event == "before_mutation":
        return _before_mutation(root, payload)
    return _stop(root, payload)


def command_event(args: argparse.Namespace) -> int:
    raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise RouterError("ROUTER_EVENT_TOO_LARGE")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RouterError(f"ROUTER_EVENT_INVALID: {exc}") from exc
    if not isinstance(payload, dict):
        raise RouterError("ROUTER_EVENT_INVALID: expected object")
    root = repository_root(args.repo)
    _json_output(process_event(root, payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root or child directory")
    commands = parser.add_subparsers(dest="command", required=True)

    begin = commands.add_parser(
        "begin",
        help="Establish a manual turn baseline when lifecycle Hooks are unavailable",
    )
    begin.add_argument("--adapter-id", required=True)
    begin.add_argument("--session-id", required=True)
    begin.add_argument("--turn-id", required=True)
    begin.add_argument("--prompt")
    begin.set_defaults(handler=command_begin)

    candidates = commands.add_parser("candidates", help="List scope-matched task candidates")
    candidates.add_argument("--path", action="append", required=True)
    candidates.set_defaults(handler=command_candidates)

    activate = commands.add_parser("activate", help="Record this turn's activation decision")
    activate.add_argument("--adapter-id", required=True)
    activate.add_argument("--session-id", required=True)
    activate.add_argument("--turn-id", required=True)
    activate.add_argument("--path", action="append", required=True)
    activate.add_argument("--spec", action="append")
    activate.add_argument("--none", action="store_true")
    activate.add_argument("--reason")
    activate.set_defaults(handler=command_activate)

    status = commands.add_parser("status", help="Show the current turn receipt")
    status.add_argument("--adapter-id", required=True)
    status.add_argument("--session-id", required=True)
    status.add_argument("--turn-id", required=True)
    status.set_defaults(handler=command_status)

    audit = commands.add_parser("audit", help="Audit changed paths and optional handoff")
    audit.add_argument("--adapter-id", required=True)
    audit.add_argument("--session-id", required=True)
    audit.add_argument("--turn-id", required=True)
    audit_message = audit.add_mutually_exclusive_group()
    audit_message.add_argument("--message")
    audit_message.add_argument("--message-file")
    audit.set_defaults(handler=command_audit)

    event = commands.add_parser(
        "event",
        help="Handle one normalized RepoFoundry activation event from stdin",
    )
    event.set_defaults(handler=command_event)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except RouterError as exc:
        print(f"spec-router: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
