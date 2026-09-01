#!/usr/bin/env python3
"""Deterministic repository operations for engineering-execution-plan."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

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
STATE_VERSION = 1
CONFIG_VERSION = 1
DEFAULT_ARCHITECTURE_ROOT = "docs/adr"
ADR_REVISION_ROOT = Path("docs/.epctl/adr-revisions")
ADR_REVISION_MAX_BYTES = 1024 * 1024
DECISION_VIEW_REGISTRY = Path("docs/.epctl/decision-views.json")
DECISION_VIEW_ROOT = Path("docs/decision-views")
DECISION_VIEW_INDEX = Path("docs/DECISION-VIEWS.md")
DECISION_VIEW_SCHEMA_VERSION = 1
DECISION_CAPSULE_SCHEMA_VERSION = 1
DECISION_CAPSULE_DEFAULT_BUDGET_BYTES = 32 * 1024
ADR_HEALTH_SCHEMA_VERSION = 1
ADR_CONSOLIDATION_SCHEMA_VERSION = 1
ADR_HEALTH_EFFECTIVE_TARGET = 24
ADR_HEALTH_COMPONENT_TARGET = 12
ADR_HEALTH_ACTIVE_PLAN_TARGET = 12
ADR_HEALTH_ACTIVE_PLAN_CONSTRAINT_TARGET = 96
ADR_HEALTH_PARTIAL_AMENDMENT_TARGET = 8

INIT_DIRECTORIES = (
    "docs/.epctl",
    "docs/exec-plans/active",
    "docs/exec-plans/completed",
    "docs/research/active",
    "docs/research/completed",
    "docs/adr",
    "docs/decision-views",
    "docs/bugfixes/active",
    "docs/bugfixes/completed",
)
INIT_FILE_ASSETS = (
    ("docs/PLANS.md", "plans-index.md"),
    ("docs/RESEARCH.md", "research-index.md"),
    ("docs/DECISIONS.md", "decisions-index.md"),
    ("docs/DECISION-VIEWS.md", "decision-views-index.md"),
    ("docs/.epctl/decision-views.json", "decision-views-registry.json"),
    ("docs/decision-views/.gitkeep", "decision-views-gitkeep"),
    ("docs/BUGFIXES.md", "bugfixes-index.md"),
    ("docs/exec-plans/tech-debt-tracker.md", "tech-debt-tracker.md"),
)
UPGRADE_ADDITIVE_DIRECTORIES = ("docs/decision-views",)
UPGRADE_ADDITIVE_FILE_ASSETS = (
    ("docs/DECISION-VIEWS.md", "decision-views-index.md"),
    ("docs/.epctl/decision-views.json", "decision-views-registry.json"),
    ("docs/decision-views/.gitkeep", "decision-views-gitkeep"),
)

EXECPLAN_SECTIONS = (
    "Purpose / Big Picture",
    "Context and Orientation",
    "Constraints and References",
    "Plan of Work",
    "Milestones",
    "Concrete Steps",
    "Validation and Acceptance",
    "Idempotence and Recovery",
    "Progress",
    "Surprises & Discoveries",
    "Decision Log",
    "Blockers",
    "Outcomes & Retrospective",
    "Interfaces and Dependencies",
    "Artifacts and Notes",
    "Revision Notes",
)
EXECPLAN_V21_SECTIONS = ("Current Snapshot",)
EXECPLAN_V22_SECTIONS = ("Research and Architecture Inputs",)
EXECPLAN_V25_SECTIONS = ("Benchmark Gate Set",)
EXECPLAN_V26_SECTIONS = ("Architecture Compliance Matrix",)
BENCHMARK_SUITE_SECTIONS = (
    "Purpose and Scope",
    "Subject Under Test",
    "Consumers",
    "Ownership and Lifecycle",
    "Non-goals",
    "Safety and Data Policy",
)
BENCHMARK_SCENARIO_SECTIONS = (
    "Question and Hypothesis",
    "Subject, Control, and Variants",
    "Variables",
    "Dataset and Traffic Model",
    "Environment and Isolation",
    "Procedure and Commands",
    "Metrics and Correctness Checks",
    "Decision Rule",
    "Evidence Requirements",
    "Safety, Cleanup, and Recovery",
    "Boundaries and Extrapolation",
)
CHECKPOINT_SECTIONS = (
    "Handoff Summary",
    "Next Action At Checkpoint",
    "Archived Progress",
    "Archived Surprises & Discoveries",
    "Archived Decision Log",
    "Archived Resolved Blockers",
    "Archived Revision Notes",
)
RESEARCH_SECTIONS = (
    "Purpose and Decision to Enable",
    "Current Snapshot",
    "Scope and Non-goals",
    "Research Questions",
    "Method and Sources",
    "Experiments and Prototypes",
    "Findings",
    "Contradictions and Uncertainty",
    "Decision Drivers and Options",
    "Blockers",
    "Progress",
    "Outcome",
    "Artifacts and Notes",
    "Revision Notes",
)
SYNTHESIS_SECTIONS = (
    "Executive Conclusion",
    "Supported Findings",
    "Rejected Hypotheses",
    "Remaining Unknowns",
    "Options Comparison",
    "Recommendation and Preconditions",
    "Handoff to ADR and ExecPlan",
    "Revision Notes",
)
ADR_SECTIONS = (
    "Context and Problem Statement",
    "Decision Drivers",
    "Research Evidence",
    "Considered Options",
    "Decision Outcome",
    "Consequences",
    "Confirmation",
    "Revisit Triggers",
    "More Information",
    "Revision Notes",
)
ADR_V12_SECTIONS = (
    "Decision Statement",
    "Normative Constraints",
)
TASK_SECTIONS = ("Context", "Change", "Constraints", "Validation", "Blockers", "Notes")
BUGFIX_SECTIONS = (
    "Symptom",
    "Scope",
    "Reproduction",
    "Root Cause",
    "Fix",
    "Verification",
    "Blockers",
    "Notes",
    "Outcome",
)

PLAN_ACTIVE_STATUSES = {"active", "blocked"}
PLAN_COMPLETED_STATUSES = {"completed", "cancelled"}
RESEARCH_ACTIVE_STATUSES = {"active", "blocked"}
RESEARCH_COMPLETED_STATUSES = {"concluded", "cancelled"}
ADR_STATUSES = {
    "proposed",
    "accepted",
    "rejected",
    "under_review",
    "retired",
    "superseded",
}
ADR_ACCEPTED_ORIGIN_STATUSES = {
    "accepted",
    "under_review",
    "retired",
    "superseded",
}
ADR_HISTORICAL_STATUSES = ADR_ACCEPTED_ORIGIN_STATUSES | {"rejected"}
ADR_TRANSITIONS = {
    "accepted": {"under_review", "retired"},
    "under_review": {"accepted", "retired"},
}
RESEARCH_QUESTION_STATUSES = {"open", "answered", "deferred", "invalidated"}
TASK_STATUSES = {"todo", "in_progress", "blocked", "done", "cancelled"}
BUGFIX_ACTIVE_STATUSES = {"open", "in_progress", "blocked"}
BUGFIX_COMPLETED_STATUSES = {"fixed", "escalated", "cancelled"}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BLOCKER_ID_RE = re.compile(r"\bBLK-(\d{3,})\b", re.IGNORECASE)
RESEARCH_QUESTION_ID_RE = re.compile(r"RQ-(\d{3,})", re.IGNORECASE)
ROOT_LINE_RECOMMENDATION = 500
ROOT_BYTE_RECOMMENDATION = 48 * 1024
HISTORY_EVENT_RECOMMENDATION = 30
ROOT_LINE_WARNING = 800
ROOT_BYTE_WARNING = 64 * 1024
HISTORY_EVENT_WARNING = 50
MILESTONE_REVIEW_THRESHOLD = 5
MILESTONE_SPLIT_THRESHOLD = 8
UNFINISHED_TASK_REVIEW_THRESHOLD = 10
UNFINISHED_TASK_SPLIT_THRESHOLD = 15
ID_RE = {
    "EP": re.compile(r"\bEP-(\d{3,})\b", re.IGNORECASE),
    "BF": re.compile(r"\bBF-(\d{3,})\b", re.IGNORECASE),
    "TD": re.compile(r"\bTD-(\d{3,})\b", re.IGNORECASE),
    "TASK": re.compile(r"\bTASK-(\d{3,})\b", re.IGNORECASE),
    "CP": re.compile(r"\bCP-(\d{3,})\b", re.IGNORECASE),
    "R": re.compile(r"\bR-(\d{3,})\b", re.IGNORECASE),
    "ADR": re.compile(r"\bADR-(\d{3,})\b", re.IGNORECASE),
    "DD": re.compile(r"\bDD-(\d{3,})\b", re.IGNORECASE),
    "BS": re.compile(r"\bBS-(\d{3,})\b", re.IGNORECASE),
}
BENCHMARK_EVIDENCE_RE = re.compile(
    r"^benchmark:(BR-\d{3,})@sha256:([0-9a-f]{64})$"
)
ADR_CONSTRAINT_RE = re.compile(
    r"^(ADR-\d{3,})#(C-\d{3,})$",
    re.IGNORECASE,
)
LOCAL_CONSTRAINT_RE = re.compile(r"^C-(\d{3,})$", re.IGNORECASE)
ADR_EVIDENCE_RE = re.compile(
    r"^(ADR-\d{3,})@sha256:([0-9a-f]{64})$",
    re.IGNORECASE,
)
DESIGN_EVIDENCE_RE = re.compile(
    r"^(DD-\d{3,})@rev:([1-9][0-9]*)@sha256:([0-9a-f]{64})$",
    re.IGNORECASE,
)
ADR_REVISION_FILE_RE = re.compile(r"^sha256-([0-9a-f]{64})\.md$")
GIT_OBJECT_ID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.IGNORECASE)
ADR_CONSTRAINT_STRENGTHS = {"must", "must_not", "should", "may"}
CURRENT_METADATA_SCHEMA = "1"


class EpctlError(RuntimeError):
    pass


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def date_string() -> str:
    return utc_now().date().isoformat()


def timestamp_string() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def normalize_repo(value: str) -> Path:
    repo = Path(value).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        raise EpctlError(f"Repository directory does not exist: {repo}")
    return repo


def repository_from_artifact(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == "docs":
            return parent.parent
    raise EpctlError(f"Artifact is not under a docs directory: {path}")


def validate_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug):
        raise EpctlError("Slug must be lowercase kebab-case, for example unify-token-refresh")
    return slug


def md_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ").strip()


def yaml_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", " ")
        .replace("\n", " ")
    )


def metadata_actor(value: str) -> str:
    return value.strip() or "Unassigned"


def validate_metadata_contract(
    path: Path,
    data: dict[str, str],
    artifact_type: str,
    expected_id: str,
) -> list[str]:
    errors: list[str] = []
    if data.get("metadata_schema") != CURRENT_METADATA_SCHEMA:
        errors.append(
            f"{path}: metadata_schema must be {CURRENT_METADATA_SCHEMA!r}"
        )
    if data.get("artifact_type") != artifact_type:
        errors.append(f"{path}: artifact_type must be {artifact_type!r}")
    if data.get("id") != expected_id:
        errors.append(f"{path}: metadata id must be {expected_id!r}")
    for field in ("title", "status", "author", "owner", "created", "updated"):
        if not data.get(field, "").strip():
            errors.append(f"{path}: metadata field {field} must be non-empty")
    for field in ("created", "updated"):
        value = data.get(field, "")
        if value:
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                try:
                    dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(
                        f"{path}: metadata field {field} must be an ISO date or timestamp"
                    )
    return errors


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
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
        raise EpctlError(f"Missing bundled asset: {path}")
    return path.read_text(encoding="utf-8")


def render_asset(name: str, values: dict[str, str]) -> str:
    text = asset_text(name)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftovers = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
    if leftovers:
        raise EpctlError(f"Unresolved template values in {name}: {', '.join(leftovers)}")
    return text


@contextlib.contextmanager
def repo_lock(repo: Path):
    lock_path = repo / "docs" / ".epctl" / "lock"
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


def state_path(repo: Path) -> Path:
    return repo / "docs" / ".epctl" / "state.json"


def config_path(repo: Path) -> Path:
    return repo / "docs" / ".epctl" / "config.json"


def empty_config() -> dict[str, object]:
    return {
        "version": CONFIG_VERSION,
        "architecture_roots": [DEFAULT_ARCHITECTURE_ROOT],
    }


def repository_relative_path(
    repo: Path,
    value: str,
    field: str,
    *,
    require_directory: bool = False,
    require_file: bool = False,
) -> tuple[str, Path]:
    repo = repo.resolve()
    candidate = Path(value.strip())
    if not value.strip() or candidate.is_absolute():
        raise EpctlError(f"{field} must be a non-empty repository-relative path")
    lexical = repo / candidate
    reject_symlink_path(repo, lexical)
    resolved = lexical.resolve(strict=False)
    try:
        relative = resolved.relative_to(repo)
    except ValueError as exc:
        raise EpctlError(f"{field} escapes repository: {value!r}") from exc
    if require_directory and not resolved.is_dir():
        raise EpctlError(f"{field} directory does not exist: {relative.as_posix()}")
    if require_file and not resolved.is_file():
        raise EpctlError(f"{field} file does not exist: {relative.as_posix()}")
    return relative.as_posix(), resolved


def load_config(repo: Path) -> dict[str, object]:
    path = config_path(repo)
    if not path.exists():
        return empty_config()
    reject_symlink_path(repo, path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EpctlError(f"Invalid epctl config file {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != CONFIG_VERSION:
        raise EpctlError(f"Unsupported epctl config in {path}")
    roots = data.get("architecture_roots")
    if (
        not isinstance(roots, list)
        or not roots
        or not all(isinstance(item, str) for item in roots)
        or len(set(roots)) != len(roots)
    ):
        raise EpctlError(f"Invalid architecture_roots in {path}")
    normalized: list[str] = []
    for value in roots:
        relative, _ = repository_relative_path(
            repo,
            value,
            "architecture_roots",
            require_directory=False,
        )
        if not relative.startswith("docs/"):
            raise EpctlError(
                f"architecture_roots must be a directory below docs/: {value!r}"
            )
        normalized.append(relative)
    if len(set(normalized)) != len(normalized):
        raise EpctlError(f"architecture_roots normalize to duplicates in {path}")
    if DEFAULT_ARCHITECTURE_ROOT not in normalized:
        normalized.insert(0, DEFAULT_ARCHITECTURE_ROOT)
    return {"version": CONFIG_VERSION, "architecture_roots": normalized}


def save_config(repo: Path, data: dict[str, object]) -> None:
    atomic_write(
        config_path(repo),
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def decision_view_registry_path(repo: Path) -> Path:
    return repo / DECISION_VIEW_REGISTRY


def decision_view_index_path(repo: Path) -> Path:
    return repo / DECISION_VIEW_INDEX


def decision_view_path(repo: Path, view_id: str) -> Path:
    validate_slug(view_id)
    return repo / DECISION_VIEW_ROOT / f"{view_id}.md"


def empty_decision_view_registry() -> dict[str, object]:
    return {"version": DECISION_VIEW_SCHEMA_VERSION, "views": []}


def normalize_decision_view_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"id", "title", "adr_refs"}:
        raise EpctlError(
            "Decision View records must contain exactly id, title, and adr_refs"
        )
    view_id = value.get("id")
    title = value.get("title")
    raw_refs = value.get("adr_refs")
    if not isinstance(view_id, str):
        raise EpctlError("Decision View id must be a string")
    validate_slug(view_id)
    if not isinstance(title, str) or not inline_text(title):
        raise EpctlError(f"Decision View {view_id} title must be non-empty")
    normalized_title = inline_text(title)
    if title != normalized_title:
        raise EpctlError(
            f"Decision View {view_id} title must be a single normalized line"
        )
    if (
        not isinstance(raw_refs, list)
        or not raw_refs
        or not all(isinstance(item, str) for item in raw_refs)
    ):
        raise EpctlError(
            f"Decision View {view_id} adr_refs must be a non-empty string array"
        )
    normalized_refs = normalize_reference_ids(raw_refs, "ADR")
    if len(normalized_refs) != len(raw_refs):
        raise EpctlError(f"Decision View {view_id} adr_refs contains duplicates")
    normalized_refs.sort()
    if raw_refs != normalized_refs:
        raise EpctlError(
            f"Decision View {view_id} adr_refs must be canonical and sorted"
        )
    return {"id": view_id, "title": title, "adr_refs": normalized_refs}


def load_decision_view_registry(repo: Path) -> dict[str, object]:
    path = decision_view_registry_path(repo)
    if not path.exists():
        return empty_decision_view_registry()
    reject_symlink_path(repo, path)
    if not path.is_file():
        raise EpctlError(f"Decision View registry must be a regular file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EpctlError(f"Invalid Decision View registry {path}: {exc}") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "views"}
        or data.get("version") != DECISION_VIEW_SCHEMA_VERSION
        or not isinstance(data.get("views"), list)
    ):
        raise EpctlError(f"Unsupported Decision View registry in {path}")
    normalized = [
        normalize_decision_view_record(item) for item in data["views"]
    ]
    view_ids = [str(item["id"]) for item in normalized]
    if len(set(view_ids)) != len(view_ids):
        raise EpctlError(f"Decision View registry contains duplicate ids: {path}")
    if view_ids != sorted(view_ids):
        raise EpctlError(f"Decision View registry must be sorted by id: {path}")
    return {"version": DECISION_VIEW_SCHEMA_VERSION, "views": normalized}


def save_decision_view_registry(repo: Path, data: dict[str, object]) -> None:
    views = data.get("views")
    if not isinstance(views, list):
        raise EpctlError("Decision View registry views must be an array")
    normalized = [normalize_decision_view_record(item) for item in views]
    normalized.sort(key=lambda item: str(item["id"]))
    atomic_write(
        decision_view_registry_path(repo),
        json.dumps(
            {"version": DECISION_VIEW_SCHEMA_VERSION, "views": normalized},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def find_decision_view(repo: Path, view_id: str) -> dict[str, object]:
    validate_slug(view_id)
    registry = load_decision_view_registry(repo)
    views = registry["views"]
    assert isinstance(views, list)
    for item in views:
        assert isinstance(item, dict)
        if item.get("id") == view_id:
            return item
    raise EpctlError(f"Decision View does not exist: {view_id}")


def require_decision_view_infrastructure(repo: Path) -> None:
    required = (
        decision_view_registry_path(repo),
        decision_view_index_path(repo),
        repo / DECISION_VIEW_ROOT,
    )
    for path in required:
        reject_symlink_path(repo, path)
    if not required[0].is_file() or not required[1].is_file() or not required[2].is_dir():
        raise EpctlError(
            "Decision View infrastructure is missing; run epctl init or an "
            "explicit RepoFoundry Harness upgrade"
        )


def architecture_roots(repo: Path, *, existing_only: bool = False) -> tuple[Path, ...]:
    roots: list[Path] = []
    for value in load_config(repo)["architecture_roots"]:
        assert isinstance(value, str)
        _, path = repository_relative_path(
            repo,
            value,
            "architecture_roots",
            require_directory=False,
        )
        if not existing_only or path.is_dir():
            roots.append(path)
    return tuple(roots)


def register_architecture_root(repo: Path, value: str) -> Path:
    with repo_lock(repo):
        init_repo(repo)
        relative, path = repository_relative_path(
            repo,
            value,
            "architecture root",
            require_directory=True,
        )
        if not relative.startswith("docs/"):
            raise EpctlError(
                "Architecture roots must be directories below docs/"
            )
        config = load_config(repo)
        roots = config["architecture_roots"]
        assert isinstance(roots, list)
        if relative not in roots:
            roots.append(relative)
            save_config(repo, config)
        rebuild_indexes(repo)
        return path


def empty_state() -> dict[str, object]:
    return {"version": STATE_VERSION, "high_water": {}}


def load_state(repo: Path) -> dict[str, object]:
    path = state_path(repo)
    if not path.exists():
        return empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EpctlError(f"Invalid epctl state file {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
        raise EpctlError(f"Unsupported epctl state in {path}")
    high_water = data.get("high_water")
    if not isinstance(high_water, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, int)
        or value < 0
        for key, value in high_water.items()
    ):
        raise EpctlError(f"Invalid high_water map in {path}")
    return data


def save_state(repo: Path, data: dict[str, object]) -> None:
    atomic_write(
        state_path(repo),
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def reject_symlink_path(repo: Path, path: Path) -> None:
    try:
        relative = path.relative_to(repo)
    except ValueError as exc:
        raise EpctlError(f"Managed path escapes repository: {path}") from exc
    current = repo
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise EpctlError(f"Refusing to manage symbolic link: {current}")


def ensure_file(path: Path, asset: str, values: dict[str, str] | None = None) -> bool:
    if path.exists():
        return False
    values = values or {}
    atomic_write(path, render_asset(asset, values) if values else asset_text(asset))
    return True


def init_repo(repo: Path) -> list[str]:
    created: list[str] = []
    for relative in INIT_DIRECTORIES:
        path = repo / relative
        reject_symlink_path(repo, path)
        if not path.exists():
            path.mkdir(parents=True)
            created.append(relative + "/")

    for relative, asset in INIT_FILE_ASSETS:
        path = repo / relative
        reject_symlink_path(repo, path)
        if ensure_file(path, asset, {"DATE": date_string()}):
            created.append(relative)
    reject_symlink_path(repo, state_path(repo))
    if not state_path(repo).exists():
        save_state(repo, empty_state())
        created.append("docs/.epctl/state.json")
    return created


def id_roots(repo: Path, prefix: str, scope: Path | None = None) -> tuple[Path, ...]:
    if scope is not None:
        return (scope,)
    if prefix == "EP":
        return (repo / "docs" / "exec-plans", repo / "docs" / "PLANS.md")
    if prefix == "R":
        return (repo / "docs" / "research", repo / "docs" / "RESEARCH.md")
    if prefix == "ADR":
        return (*architecture_roots(repo), repo / "docs" / "DECISIONS.md")
    if prefix == "BF":
        return (repo / "docs" / "bugfixes", repo / "docs" / "BUGFIXES.md")
    if prefix == "TD":
        return (
            repo / "docs" / "exec-plans" / "tech-debt-tracker.md",
            repo / "docs" / "tech-debt-tracker.md",
        )
    return (repo / "docs",)


def scan_ids(repo: Path, prefix: str, scope: Path | None = None) -> set[int]:
    pattern = ID_RE[prefix]
    values: set[int] = set()
    for root in id_roots(repo, prefix, scope):
        if not root.exists():
            continue
        paths: Iterable[Path]
        if root.is_file():
            paths = (root,)
        else:
            paths = root.rglob("*")
        for path in paths:
            for match in pattern.finditer(path.name):
                values.add(int(match.group(1)))
            if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
                try:
                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for match in pattern.finditer(content):
                    values.add(int(match.group(1)))
    return values


def next_id_number(
    repo: Path,
    prefix: str,
    scope: Path | None = None,
    state_key: str | None = None,
) -> tuple[int, dict[str, object], str]:
    state = load_state(repo)
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    key = state_key or prefix
    values = scan_ids(repo, prefix, scope)
    number = max(max(values, default=0), int(high_water.get(key, 0))) + 1
    return number, state, key


def peek_next_id(
    repo: Path,
    prefix: str,
    scope: Path | None = None,
    state_key: str | None = None,
) -> str:
    number, _, _ = next_id_number(repo, prefix, scope, state_key)
    return f"{prefix}-{number:03d}"


def next_id(
    repo: Path,
    prefix: str,
    scope: Path | None = None,
    state_key: str | None = None,
) -> str:
    number, state, key = next_id_number(repo, prefix, scope, state_key)
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    high_water[key] = number
    save_state(repo, state)
    return f"{prefix}-{number:03d}"


def parse_frontmatter(text: str) -> tuple[dict[str, str], int, int]:
    if not text.startswith("---\n"):
        raise EpctlError("Missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise EpctlError("Unclosed YAML frontmatter")
    data: dict[str, str] = {}
    for line_number, raw in enumerate(text[4:end].splitlines(), start=2):
        if "\t" in raw:
            raise EpctlError(f"Tabs are not allowed in frontmatter (line {line_number})")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isspace() or ":" not in raw:
            raise EpctlError(
                f"Only top-level key: value fields are supported (line {line_number})"
            )
        key, value = raw.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise EpctlError(f"Invalid frontmatter key {key!r} (line {line_number})")
        if key in data:
            raise EpctlError(f"Duplicate frontmatter key {key!r} (line {line_number})")
        value = value.strip()
        if value.startswith('"'):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise EpctlError(
                    f"Invalid quoted scalar for {key!r} (line {line_number})"
                ) from exc
            if not isinstance(parsed, str):
                raise EpctlError(f"{key!r} must be a scalar (line {line_number})")
            value = parsed
        elif value.startswith("'"):
            if len(value) < 2 or not value.endswith("'"):
                raise EpctlError(
                    f"Invalid single-quoted scalar for {key!r} (line {line_number})"
                )
            value = value[1:-1].replace("''", "'")
        elif value.startswith("["):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise EpctlError(
                    f"Arrays must use JSON syntax for {key!r} (line {line_number})"
                ) from exc
            if not isinstance(parsed, list) or not all(
                isinstance(item, str) for item in parsed
            ):
                raise EpctlError(
                    f"{key!r} supports only a flat string array (line {line_number})"
                )
        elif value[:1] in {"{", "|", ">", "&", "*", "!"}:
            raise EpctlError(
                f"Unsupported YAML construct for {key!r} (line {line_number})"
            )
        data[key] = value
    return data, 4, end


def parse_legacy_frontmatter(text: str) -> tuple[dict[str, str], int, int]:
    """Read the small YAML subset commonly used by linked design-doc corpora."""
    if not text.startswith("---\n"):
        raise EpctlError("Missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise EpctlError("Unclosed YAML frontmatter")
    data: dict[str, str] = {}
    current_array: str | None = None
    array_values: list[str] = []

    def finish_array() -> None:
        nonlocal current_array, array_values
        if current_array is not None:
            data[current_array] = json.dumps(array_values, ensure_ascii=False)
        current_array = None
        array_values = []

    for line_number, raw in enumerate(text[4:end].splitlines(), start=2):
        if "\t" in raw:
            raise EpctlError(f"Tabs are not allowed in frontmatter (line {line_number})")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isspace():
            match = re.match(r"^\s*-\s+(.+?)\s*$", raw)
            if current_array is None or not match:
                raise EpctlError(
                    f"Unsupported legacy YAML construct (line {line_number})"
                )
            item = match.group(1).strip()
            if (
                len(item) >= 2
                and item[0] == item[-1]
                and item[0] in {'"', "'"}
            ):
                item = item[1:-1]
            array_values.append(item)
            continue
        finish_array()
        if ":" not in raw:
            raise EpctlError(f"Expected key: value (line {line_number})")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", key):
            raise EpctlError(f"Invalid frontmatter key {key!r} (line {line_number})")
        key = key.replace("-", "_")
        value = value.strip()
        if not value and key in {
            "relates_to",
            "research_refs",
            "depends_on",
            "amends",
            "amends_constraints",
            "supersedes",
            "design_refs",
        }:
            current_array = key
            continue
        if value.startswith("["):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise EpctlError(
                    f"Arrays must use JSON syntax for {key!r} (line {line_number})"
                ) from exc
            if not isinstance(parsed, list) or not all(
                isinstance(item, str) for item in parsed
            ):
                raise EpctlError(
                    f"{key!r} supports only a flat string array (line {line_number})"
                )
        elif (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]
        data[key] = value
    finish_array()
    return data, 4, end


def adr_document_data_from_text(
    path: Path,
    text: str,
) -> tuple[dict[str, str], bool]:
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as strict_error:
        data, _, _ = parse_legacy_frontmatter(text)
        if data.get("schema_version"):
            raise strict_error
    strict = bool(data.get("schema_version"))
    if not strict:
        inferred_match = re.search(
            r"(?i)(?:^|/)adr-(\d{3,})(?=[_.-]|$)",
            path.as_posix(),
        )
        if not data.get("id") and inferred_match:
            data["id"] = f"ADR-{int(inferred_match.group(1)):03d}"
        data["schema_version"] = "legacy-linked"
        data.setdefault("title", path.stem)
        data.setdefault("status", "")
        data.setdefault("created", data.get("last_verified", ""))
        data.setdefault("updated", data.get("last_verified", data.get("created", "")))
        for field in (
            "research_refs",
            "depends_on",
            "amends",
            "amends_constraints",
            "supersedes",
            "design_refs",
        ):
            data.setdefault(field, "[]")
        data.setdefault("superseded_by", "")
    return data, strict


def adr_document_data(path: Path) -> tuple[dict[str, str], bool]:
    return adr_document_data_from_text(path, path.read_text(encoding="utf-8"))


def update_frontmatter(text: str, updates: dict[str, str]) -> str:
    _, start, end = parse_frontmatter(text)
    lines = text[start:end].splitlines()
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key in remaining:
            output.append(f"{key}: {remaining.pop(key)}")
        else:
            output.append(line)
    for key, value in remaining.items():
        output.append(f"{key}: {value}")
    return "---\n" + "\n".join(output) + "\n---\n" + text[end + 5 :]


def update_adr_frontmatter(
    text: str,
    data: dict[str, str],
    updates: dict[str, str],
) -> str:
    """Update ADR lifecycle fields while preserving linked legacy YAML.

    Strict RepoFoundry artifacts intentionally use only top-level scalar and
    JSON-array fields, so ``update_frontmatter`` remains fail-closed for every
    other caller. Registered legacy ADRs may contain the block-style string
    arrays accepted by ``parse_legacy_frontmatter``. Effect transitions only
    replace or append top-level lifecycle fields and must leave those owned
    legacy fields byte-for-byte intact.
    """
    if data.get("schema_version") != "legacy-linked":
        return update_frontmatter(text, updates)

    _, start, end = parse_legacy_frontmatter(text)
    lines = text[start:end].splitlines()
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        key = ""
        if line and not line[:1].isspace() and ":" in line:
            key = line.split(":", 1)[0].strip().replace("-", "_")
        if key in remaining:
            original_key = line.split(":", 1)[0].strip()
            output.append(f"{original_key}: {remaining.pop(key)}")
        else:
            output.append(line)
    for key, value in remaining.items():
        output.append(f"{key}: {value}")
    return "---\n" + "\n".join(output) + "\n---\n" + text[end + 5 :]


def visible_markdown_lines(text: str) -> Iterable[str]:
    fence: str | None = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            continue
        if fence is None:
            yield line


def markdown_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            if current_heading is not None:
                current_lines.append(line)
            continue
        match = re.match(r"^##\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if match:
            if current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = match.group(1).strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, current_lines))
    return sections


def section_values(text: str, heading: str) -> list[str]:
    return [
        "\n".join(lines).strip()
        for name, lines in markdown_sections(text)
        if name == heading
    ]


def section(text: str, heading: str) -> str | None:
    values = section_values(text, heading)
    return values[0] if values else None


def markdown_section_spans(text: str) -> list[tuple[str, int, int, int]]:
    headings: list[tuple[str, int, int]] = []
    fence: str | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
        elif fence is None:
            match = re.match(r"^##\s+(.+?)\s*#*\s*(?:\r?\n)?$", line)
            if match:
                headings.append((match.group(1).strip(), offset, offset + len(line)))
        offset += len(line)
    result: list[tuple[str, int, int, int]] = []
    for index, (heading, start, body_start) in enumerate(headings):
        end = headings[index + 1][1] if index + 1 < len(headings) else len(text)
        result.append((heading, start, body_start, end))
    return result


def markdown_section_source(text: str, heading: str) -> str:
    matches = [
        span for span in markdown_section_spans(text) if span[0] == heading
    ]
    if len(matches) != 1:
        raise EpctlError(
            f"Expected exactly one ## {heading}, found {len(matches)}"
        )
    _, start, _, end = matches[0]
    return text[start:end]


def adr_constraint_source_rows(
    text: str,
    adr_id: str,
) -> tuple[list[str], list[dict[str, object]]]:
    source = markdown_section_source(text, "Normative Constraints")
    header_lines: list[str] = []
    rows: list[dict[str, object]] = []
    for line in source.splitlines(keepends=True):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells:
            continue
        if cells[0].lower() == "id" or set(cells[0]) == {"-"}:
            header_lines.append(line)
            continue
        match = LOCAL_CONSTRAINT_RE.fullmatch(cells[0].upper())
        if not match:
            continue
        constraint_id = f"C-{int(match.group(1)):03d}"
        rows.append(
            {
                "ref": f"{adr_id}#{constraint_id}",
                "constraint_id": constraint_id,
                "line": line,
                "cells": cells,
            }
        )
    if len(header_lines) < 2:
        raise EpctlError(
            f"{adr_id} Normative Constraints table has no exact header/divider"
        )
    return header_lines[:2], rows


def replace_section(text: str, heading: str, body: str) -> str:
    matches = [
        span for span in markdown_section_spans(text) if span[0] == heading
    ]
    if len(matches) != 1:
        raise EpctlError(
            f"Expected exactly one ## {heading}, found {len(matches)}"
        )
    _, _, body_start, end = matches[0]
    replacement = "\n" + body.strip() + "\n\n"
    return text[:body_start] + replacement + text[end:]


def markdown_list_blocks(body: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in body.splitlines():
        if re.match(r"^-\s+", line) and current:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(block).strip() for block in blocks if any(block)]


def partition_completed_progress(body: str) -> tuple[str, str]:
    archived: list[str] = []
    remaining: list[str] = []
    for block in markdown_list_blocks(body):
        first = block.splitlines()[0] if block else ""
        if re.match(r"^-\s+\[[xX]\]", first):
            archived.append(block)
        else:
            remaining.append(block)
    return "\n\n".join(archived).strip(), "\n\n".join(remaining).strip()


def is_empty_history_body(body: str) -> bool:
    normalized = " ".join(body.strip().lower().split())
    return (
        not normalized
        or normalized in {"none yet.", "- none yet.", "none.", "- none."}
        or normalized.startswith("- none since cp-")
    )


def partition_blockers(body: str) -> tuple[str, str]:
    root_lines: list[str] = []
    archived_rows: list[str] = []
    table_header: list[str] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            root_lines.append(line)
            continue
        cells = split_table_row(line)
        if (
            not cells
            or cells[0] == "ID"
            or set(cells[0]) == {"-"}
        ):
            table_header.append(line)
            root_lines.append(line)
            continue
        status = cells[1].lower() if len(cells) > 1 else ""
        if status in {"resolved", "dismissed"}:
            archived_rows.append(line)
        else:
            root_lines.append(line)
    archived = (
        "\n".join((*table_header, *archived_rows))
        if archived_rows
        else ""
    )
    return archived.strip(), "\n".join(root_lines).strip()


def checkboxes(text: str) -> list[bool]:
    result: list[bool] = []
    for line in visible_markdown_lines(text):
        match = re.match(r"^\s*-\s+\[([ xX])\]", line)
        if match:
            result.append(match.group(1).lower() == "x")
    return result


def split_table_row(line: str) -> list[str]:
    body = line.strip().strip("|")
    return [
        cell.replace(r"\|", "|").strip()
        for cell in re.split(r"(?<!\\)\|", body)
    ]


def blocker_rows(text: str) -> list[list[str]]:
    body = section(text, "Blockers") or ""
    result: list[list[str]] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if len(cells) < 2 or cells[0] in {"ID", "---"} or set(cells[0]) == {"-"}:
            continue
        result.append(cells)
    return result


def unresolved_blockers(text: str) -> list[str]:
    return [
        cells[0]
        for cells in blocker_rows(text)
        if cells[1].lower() == "open"
    ]


def parse_inline_ids(value: str, prefix: str) -> list[str]:
    return [f"{prefix}-{int(number):03d}" for number in ID_RE[prefix].findall(value)]


def normalize_reference_ids(values: Iterable[str], prefix: str) -> list[str]:
    normalized: list[str] = []
    for value in values:
        candidate = value.strip().upper()
        match = ID_RE[prefix].fullmatch(candidate)
        if not match:
            raise EpctlError(f"Invalid {prefix} reference: {value!r}")
        item_id = f"{prefix}-{int(match.group(1)):03d}"
        if item_id not in normalized:
            normalized.append(item_id)
    return normalized


def parse_reference_array(value: str, prefix: str, field: str) -> list[str]:
    raw = parse_string_array(value, field)
    normalized = normalize_reference_ids(raw, prefix)
    if len(normalized) != len(raw):
        raise EpctlError(f"{field} contains duplicate references")
    return normalized


def parse_string_array(value: str, field: str) -> list[str]:
    try:
        raw = json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise EpctlError(f"{field} must be a JSON string array") from exc
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise EpctlError(f"{field} must be a JSON string array")
    if any(not inline_text(item) for item in raw):
        raise EpctlError(f"{field} cannot contain empty values")
    if len(set(raw)) != len(raw):
        raise EpctlError(f"{field} contains duplicate values")
    return raw


def normalize_adr_constraint_refs(
    values: Iterable[str],
    field: str,
) -> list[str]:
    normalized: list[str] = []
    for value in values:
        candidate = inline_text(value).upper()
        match = ADR_CONSTRAINT_RE.fullmatch(candidate)
        if not match:
            raise EpctlError(
                f"Invalid {field} reference {value!r}; expected ADR-NNN#C-NNN"
            )
        adr_match = ID_RE["ADR"].fullmatch(match.group(1))
        constraint_match = LOCAL_CONSTRAINT_RE.fullmatch(match.group(2))
        if not adr_match or not constraint_match:  # defensive; regexes agree
            raise EpctlError(f"Invalid {field} reference: {value!r}")
        canonical = (
            f"ADR-{int(adr_match.group(1)):03d}#"
            f"C-{int(constraint_match.group(1)):03d}"
        )
        if canonical in normalized:
            raise EpctlError(f"{field} contains duplicate references")
        normalized.append(canonical)
    return normalized


def parse_adr_constraint_array(value: str, field: str) -> list[str]:
    return normalize_adr_constraint_refs(parse_string_array(value, field), field)


def adr_constraint_rows(text: str) -> list[list[str]]:
    body = section(text, "Normative Constraints") or ""
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells or cells[0].lower() == "id" or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


def adr_constraint_refs(text: str, adr_id: str) -> list[str]:
    refs: list[str] = []
    for cells in adr_constraint_rows(text):
        if not cells:
            continue
        match = LOCAL_CONSTRAINT_RE.fullmatch(cells[0].upper())
        if match:
            refs.append(f"{adr_id}#C-{int(match.group(1)):03d}")
    return refs


def unresolved_contract_cell(value: str) -> bool:
    normalized = inline_text(value).strip().lower()
    return (
        not normalized
        or normalized.startswith("replace_with_")
        or normalized in {"tbd", "todo", "unknown", "<replace>"}
    )


def architecture_compliance_rows(text: str) -> list[list[str]]:
    body = section(text, "Architecture Compliance Matrix") or ""
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if (
            not cells
            or cells[0].lower() == "adr constraint or architecture input"
            or set(cells[0]) == {"-"}
            or cells[0] == "—"
        ):
            continue
        rows.append(cells)
    return rows


def render_architecture_compliance_rows(
    adr_refs: Iterable[str],
    repo: Path,
    design_refs: Iterable[str],
    architecture_entrypoint: str,
) -> tuple[list[str], str]:
    structured_refs: list[str] = []
    row_refs: list[str] = []
    for adr_id in adr_refs:
        adr_path = find_adr(repo, adr_id)
        constraints = adr_constraint_refs(
            adr_path.read_text(encoding="utf-8"),
            adr_id,
        )
        if constraints:
            structured_refs.extend(constraints)
            row_refs.extend(constraints)
        else:
            row_refs.append(adr_id)
    if not row_refs:
        row_refs.extend(design_refs)
    if not row_refs and architecture_entrypoint:
        row_refs.append(architecture_entrypoint)
    if not row_refs:
        return [], "| — | No architecture input applies to this EP. | — |"
    rows = "\n".join(
        f"| {reference} | <!-- REQUIRED: State how this plan implements or "
        f"preserves {reference}. --> | <!-- REQUIRED: State the test, lint, "
        f"schema check, or observable evidence for {reference}. --> |"
        for reference in row_refs
    )
    return structured_refs, rows


def adr_evidence_values(
    adr_refs: Iterable[str],
    adr_data_by_id: dict[str, dict[str, str]],
) -> list[str]:
    evidence: list[str] = []
    for adr_id in adr_refs:
        digest = inline_text(adr_data_by_id[adr_id].get("payload_sha256", ""))
        if re.fullmatch(r"[0-9a-f]{64}", digest):
            evidence.append(f"{adr_id}@sha256:{digest}")
    return evidence


def parse_adr_evidence(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in parse_string_array(value, "adr_evidence"):
        match = ADR_EVIDENCE_RE.fullmatch(item)
        if not match:
            raise EpctlError(
                "adr_evidence entries must use ADR-NNN@sha256:<64-hex>"
            )
        adr_id = normalize_reference_ids((match.group(1),), "ADR")[0]
        if adr_id in result:
            raise EpctlError("adr_evidence contains duplicate ADR references")
        result[adr_id] = match.group(2).lower()
    return result


def current_constraint_amendments(
    repo: Path,
    constraint_refs: Iterable[str],
) -> dict[str, list[str]]:
    applicable = set(constraint_refs)
    amendments: dict[str, list[str]] = {}
    corpus = adr_corpus_data(repo)
    if not applicable:
        return amendments
    for path in adr_files(repo):
        data, _ = adr_document_data(path)
        if data.get("status") != "accepted":
            continue
        current, _ = adr_currentness(
            repo,
            data.get("id", ""),
            data_by_id=corpus,
        )
        if not current:
            continue
        amended = parse_adr_constraint_array(
            data.get("amends_constraints", "[]"),
            "amends_constraints",
        )
        matching = sorted(applicable & set(amended))
        if matching:
            amendments[data.get("id", "")] = matching
    return amendments


def normalize_benchmark_scenario_ids(values: Iterable[str]) -> list[str]:
    raw = list(values)
    normalized = normalize_reference_ids(raw, "BS")
    if len(normalized) != len(raw):
        raise EpctlError("--benchmark-scenario values must be unique")
    return normalized


def benchmark_gate_rows(scenario_ids: Iterable[str]) -> str:
    values = list(scenario_ids)
    if not values:
        return "| — | No Benchmark Scenario gate declared for this EP. | — |"
    return "\n".join(
        f"| {scenario_id} | <!-- REQUIRED: State the development decision or "
        "milestone gated by this Scenario. --> | Exactly one passed sealed Run "
        "at `verified_revision` |"
        for scenario_id in values
    )


def benchmark_acceptance_items(scenario_ids: Iterable[str]) -> str:
    values = list(scenario_ids)
    if not values:
        return "- No required Benchmark Scenario gates."
    return "\n".join(
        f"- [ ] `{scenario_id}` has exactly one passed sealed Run attached through "
        "`--evidence` at the final `verified_revision`."
        for scenario_id in values
    )


def marker_block(kind: str) -> str:
    if kind == "EP":
        return (
            "\n\n## epctl v2 managed index\n\n### Active\n\n"
            "<!-- EPCTL:ACTIVE:START -->\n"
            "| ID | Title | Status | Updated | Path |\n"
            "|---|---|---|---|---|\n"
            "<!-- EPCTL:ACTIVE:END -->\n\n"
            "### Completed\n\n"
            "<!-- EPCTL:COMPLETED:START -->\n"
            "| ID | Title | Status | Updated | Path |\n"
            "|---|---|---|---|---|\n"
            "<!-- EPCTL:COMPLETED:END -->\n"
        )
    if kind == "BF":
        return (
            "\n\n## epctl v2 managed index\n\n### Active\n\n"
            "<!-- BFCTL:ACTIVE:START -->\n"
            "| ID | Title | Area | Severity | Status | Updated | Linked EP | Path |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "<!-- BFCTL:ACTIVE:END -->\n\n"
            "### Completed\n\n"
            "<!-- BFCTL:COMPLETED:START -->\n"
            "| ID | Title | Area | Severity | Status | Updated | Linked EP | Path |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "<!-- BFCTL:COMPLETED:END -->\n"
        )
    if kind == "R":
        return (
            "\n\n## epctl managed Research index\n\n### Active\n\n"
            "<!-- RCTL:ACTIVE:START -->\n"
            "| ID | Title | Type | Status | Maturity | Owner | Updated | Synthesis | Path |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "<!-- RCTL:ACTIVE:END -->\n\n"
            "### Completed\n\n"
            "<!-- RCTL:COMPLETED:START -->\n"
            "| ID | Title | Type | Status | Maturity | Owner | Updated | Synthesis | Path |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "<!-- RCTL:COMPLETED:END -->\n"
        )
    if kind == "ADR":
        return (
            "\n\n## epctl managed ADR index\n\n### Proposed\n\n"
            "<!-- ADRCTL:ACTIVE:START -->\n"
            "| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "<!-- ADRCTL:ACTIVE:END -->\n\n"
            "### Effective\n\n"
            "<!-- ADRCTL:CURRENT:START -->\n"
            "| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "<!-- ADRCTL:CURRENT:END -->\n\n"
            "### Current constraint amendments\n\n"
            "<!-- ADRCTL:AMENDMENTS:START -->\n"
            "| Constraint | Amended By | Amendment | Path |\n"
            "|---|---|---|---|\n"
            "<!-- ADRCTL:AMENDMENTS:END -->\n\n"
            "### Review required\n\n"
            "<!-- ADRCTL:REVIEW:START -->\n"
            "| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "<!-- ADRCTL:REVIEW:END -->\n\n"
            "### Historical\n\n"
            "<!-- ADRCTL:COMPLETED:START -->\n"
            "| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "<!-- ADRCTL:COMPLETED:END -->\n"
        )
    if kind == "TD":
        return (
            "\n\n## epctl v2 managed debt\n\n"
            "<!-- TDCTL:ACTIVE:START -->\n"
            "| ID | Description | Area | Priority | Target | Status | Created |\n"
            "|---|---|---|---|---|---|---|\n"
            "<!-- TDCTL:ACTIVE:END -->\n\n"
            "<!-- TDCTL:COMPLETED:START -->\n"
            "| ID | Description | Area | Priority | Resolved | Status | Created |\n"
            "|---|---|---|---|---|---|---|\n"
            "<!-- TDCTL:COMPLETED:END -->\n"
        )
    raise EpctlError(f"Unknown index kind: {kind}")


def ensure_adr_index_layout(text: str) -> str:
    active_start = "<!-- ADRCTL:ACTIVE:START -->"
    active_end = "<!-- ADRCTL:ACTIVE:END -->"
    completed_start = "<!-- ADRCTL:COMPLETED:START -->"
    completed_end = "<!-- ADRCTL:COMPLETED:END -->"
    if active_start not in text:
        return text.rstrip() + marker_block("ADR")
    if any(marker not in text for marker in (active_end, completed_start, completed_end)):
        raise EpctlError("Malformed ADR index compatibility markers")

    added_tables = ("CURRENT", "AMENDMENTS", "REVIEW")
    marker_presence = {
        table: (
            f"<!-- ADRCTL:{table}:START -->" in text
            and f"<!-- ADRCTL:{table}:END -->" in text
        )
        for table in added_tables
    }
    if all(marker_presence.values()):
        return text
    if any(marker_presence.values()):
        raise EpctlError(
            "Malformed ADR effect projection markers; run reindex after restoring "
            "the managed layout"
        )

    active_marker_end = text.find(active_end) + len(active_end)
    completed_marker_start = text.find(completed_start, active_marker_end)
    if completed_marker_start < 0:
        raise EpctlError("Malformed ADR index compatibility markers")
    heading_matches = list(
        re.finditer(
            r"(?m)^(#{2,6})[ \t]+[^\n]+?[ \t]*$",
            text[: text.find(active_start)],
        )
    )
    heading_prefix = heading_matches[-1].group(1) if heading_matches else "###"
    middle = text[active_marker_end:completed_marker_start]
    decided_heading = re.search(
        r"(?m)^(#{2,6})[ \t]+Decided[ \t]*$",
        middle,
    )
    if decided_heading:
        middle = (
            middle[: decided_heading.start()]
            + f"{decided_heading.group(1)} Historical"
            + middle[decided_heading.end() :]
        )
    else:
        middle = middle.rstrip() + f"\n\n{heading_prefix} Historical\n\n"

    regular_header, regular_divider = index_header("ADR", "CURRENT")
    amendment_header, amendment_divider = index_header("ADR", "AMENDMENTS")
    inserted = (
        f"\n\n{heading_prefix} Effective\n\n"
        "<!-- ADRCTL:CURRENT:START -->\n"
        f"{regular_header}\n{regular_divider}\n"
        "<!-- ADRCTL:CURRENT:END -->\n\n"
        f"{heading_prefix} Current constraint amendments\n\n"
        "<!-- ADRCTL:AMENDMENTS:START -->\n"
        f"{amendment_header}\n{amendment_divider}\n"
        "<!-- ADRCTL:AMENDMENTS:END -->\n\n"
        f"{heading_prefix} Review required\n\n"
        "<!-- ADRCTL:REVIEW:START -->\n"
        f"{regular_header}\n{regular_divider}\n"
        "<!-- ADRCTL:REVIEW:END -->"
    )
    return (
        text[:active_marker_end]
        + inserted
        + middle
        + text[completed_marker_start:]
    )


def ensure_markers(text: str, kind: str) -> str:
    if kind == "ADR":
        return ensure_adr_index_layout(text)
    start = f"<!-- {kind}CTL:ACTIVE:START -->"
    return text if start in text else text.rstrip() + marker_block(kind)


def upsert_index_row(
    text: str, kind: str, table: str, item_id: str, row: str | None
) -> str:
    text = ensure_markers(text, kind)
    start_marker = f"<!-- {kind}CTL:{table}:START -->"
    end_marker = f"<!-- {kind}CTL:{table}:END -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end < start:
        raise EpctlError(f"Malformed {kind} index markers for {table}")
    body_start = start + len(start_marker)
    body = text[body_start:end]
    lines = [
        line
        for line in body.splitlines()
        if not line.strip().startswith(f"| {item_id} |")
    ]
    if row is not None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines.append(row)
    replacement = "\n" + "\n".join(lines).strip("\n") + "\n"
    return text[:body_start] + replacement + text[end:]


def index_header(kind: str, table: str = "") -> tuple[str, str]:
    if kind == "EP":
        return (
            "| ID | Title | Status | Updated | Path |",
            "|---|---|---|---|---|",
        )
    if kind == "BF":
        return (
            "| ID | Title | Area | Severity | Status | Updated | Linked EP | Path |",
            "|---|---|---|---|---|---|---|---|",
        )
    if kind == "R":
        return (
            "| ID | Title | Type | Status | Maturity | Owner | Updated | Synthesis | Path |",
            "|---|---|---|---|---|---|---|---|---|",
        )
    if kind == "ADR":
        if table == "AMENDMENTS":
            return (
                "| Constraint | Amended By | Amendment | Path |",
                "|---|---|---|---|",
            )
        return (
            "| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |",
            "|---|---|---|---|---|---|---|---|",
        )
    raise EpctlError(f"Unsupported index kind: {kind}")


def replace_index_rows(
    text: str,
    kind: str,
    table: str,
    rows: Iterable[str],
) -> str:
    text = ensure_markers(text, kind)
    start_marker = f"<!-- {kind}CTL:{table}:START -->"
    end_marker = f"<!-- {kind}CTL:{table}:END -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end < start:
        raise EpctlError(f"Malformed {kind} index markers for {table}")
    body_start = start + len(start_marker)
    replacement = rendered_index_body(kind, table, rows)
    return text[:body_start] + replacement + text[end:]


def rendered_index_body(
    kind: str,
    table: str,
    rows: Iterable[str],
) -> str:
    header, divider = index_header(kind, table)
    if kind == "ADR" and table == "AMENDMENTS":
        ordered_rows = sorted(rows)
    else:
        ordered_rows = sorted(
            rows,
            key=lambda row: int(ID_RE[kind].search(row).group(1)),
        )
    return "\n" + "\n".join((header, divider, *ordered_rows)) + "\n"


def managed_index_body(text: str, kind: str, table: str) -> str:
    start_marker = f"<!-- {kind}CTL:{table}:START -->"
    end_marker = f"<!-- {kind}CTL:{table}:END -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end < start:
        return ""
    return text[start + len(start_marker) : end]


def managed_table_ids(text: str, kind: str, table: str) -> set[str]:
    return {
        f"{kind}-{int(number):03d}"
        for number in re.findall(
            rf"(?mi)^\|\s*{re.escape(kind)}-(\d{{3,}})\s*\|",
            managed_index_body(text, kind, table),
        )
    }


def legacy_metadata(path: Path, prefix: str) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = ID_RE[prefix].search(path.as_posix())
    item_id = f"{prefix}-{int(match.group(1)):03d}" if match else ""
    title_match = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    return {
        "id": item_id,
        "title": title_match.group(1).strip() if title_match else item_id,
        "status": (
            "completed"
            if "/completed/" in path.as_posix()
            else ("active" if prefix == "EP" else "open")
        ),
        "updated": "",
        "area": "",
        "severity": "",
        "linked_ep": "",
    }


def artifact_metadata(path: Path, prefix: str) -> dict[str, str]:
    if prefix == "ADR":
        try:
            data, _ = adr_document_data(path)
            return data
        except EpctlError:
            return legacy_metadata(path, prefix)
    try:
        data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        return data
    except EpctlError:
        return legacy_metadata(path, prefix)


def plan_index_row(repo: Path, path: Path) -> str:
    data = artifact_metadata(path, "EP")
    item_id = data.get("id", "")
    relative = path.relative_to(repo / "docs").as_posix()
    return (
        f"| {item_id} | {md_cell(data.get('title', item_id))} | "
        f"{md_cell(data.get('status', ''))} | {md_cell(data.get('updated', ''))} | "
        f"[EXECPLAN]({relative}) |"
    )


def bugfix_index_row(repo: Path, path: Path) -> str:
    data = artifact_metadata(path, "BF")
    item_id = data.get("id", "")
    relative = path.relative_to(repo / "docs").as_posix()
    return (
        f"| {item_id} | {md_cell(data.get('title', item_id))} | "
        f"{md_cell(data.get('area', ''))} | {md_cell(data.get('severity', ''))} | "
        f"{md_cell(data.get('status', ''))} | {md_cell(data.get('updated', ''))} | "
        f"{md_cell(data.get('linked_ep', ''))} | [record]({relative}) |"
    )


def research_index_row(repo: Path, path: Path) -> str:
    data = artifact_metadata(path, "R")
    item_id = data.get("id", "")
    relative = path.relative_to(repo / "docs").as_posix()
    synthesis = (path.parent / data.get("synthesis", "SYNTHESIS.md")).relative_to(
        repo / "docs"
    ).as_posix()
    research_type = data.get("research_type", "legacy").replace("_", " ").title()
    owner = data.get("owner", "") or "Unassigned"
    return (
        f"| {item_id} | {md_cell(data.get('title', item_id))} | "
        f"{md_cell(research_type)} | {md_cell(data.get('status', ''))} | "
        f"{md_cell(data.get('maturity', 'legacy'))} | {md_cell(owner)} | "
        f"{md_cell(data.get('updated', ''))} | "
        f"[Synthesis]({synthesis}) | [Research]({relative}) |"
    )


def adr_effect_projection(
    repo: Path,
    paths: Iterable[Path] | None = None,
) -> list[dict[str, object]]:
    adr_paths = list(paths) if paths is not None else adr_files(repo)
    corpus: dict[str, dict[str, str]] = {}
    paths_by_id: dict[str, Path] = {}
    for path in adr_paths:
        data = artifact_metadata(path, "ADR")
        item_id = data.get("id", "")
        if item_id:
            corpus[item_id] = data
            paths_by_id[item_id] = path

    currentness: dict[str, tuple[bool, list[str]]] = {}
    currentness_memo: dict[str, tuple[bool, list[str]]] = {}
    for item_id in corpus:
        try:
            currentness[item_id] = adr_currentness(
                repo,
                item_id,
                data_by_id=corpus,
                _memo=currentness_memo,
            )
        except EpctlError as exc:
            currentness[item_id] = (False, [str(exc)])

    current_amenders: dict[str, list[str]] = {}
    for item_id, data in corpus.items():
        if data.get("status") != "accepted" or not currentness[item_id][0]:
            continue
        for amended_id in parse_inline_ids(data.get("amends", ""), "ADR"):
            current_amenders.setdefault(amended_id, []).append(item_id)
    for amended_ids in current_amenders.values():
        amended_ids.sort()

    projection: list[dict[str, object]] = []
    for item_id in sorted(corpus):
        data = corpus[item_id]
        path = paths_by_id[item_id]
        status = data.get("status", "")
        current, review_reasons = currentness[item_id]
        amended_by = current_amenders.get(item_id, [])
        if status == "proposed":
            table = "ACTIVE"
            projection_name = "proposed"
            effect = "proposed"
        elif status == "accepted" and current:
            table = "CURRENT"
            projection_name = "effective"
            effect = "partially_amended" if amended_by else "current"
        elif status in {"accepted", "under_review"}:
            table = "REVIEW"
            projection_name = "review_required"
            effect = "under_review" if status == "under_review" else "review_required"
        else:
            table = "COMPLETED"
            projection_name = "historical"
            effect = status or "unknown"

        related: list[str] = []
        related.extend(
            f"depends on {related_id}"
            for related_id in parse_inline_ids(data.get("depends_on", ""), "ADR")
        )
        related.extend(
            f"amends {related_id}"
            for related_id in parse_inline_ids(data.get("amends", ""), "ADR")
        )
        related.extend(
            f"supersedes {related_id}"
            for related_id in parse_inline_ids(data.get("supersedes", ""), "ADR")
        )
        related.extend(f"amended by {related_id}" for related_id in amended_by)
        if data.get("superseded_by", ""):
            related.append(f"superseded by {data['superseded_by']}")
        if table == "REVIEW":
            related.extend(f"review: {reason}" for reason in review_reasons)
        projection.append(
            {
                "id": item_id,
                "data": data,
                "path": path,
                "table": table,
                "projection": projection_name,
                "effect": effect,
                "current": current,
                "amended_by": amended_by,
                "review_reasons": review_reasons,
                "related": list(dict.fromkeys(related)),
            }
        )
    return projection


def adr_index_row(repo: Path, item: dict[str, object]) -> str:
    data = item["data"]
    path = item["path"]
    assert isinstance(data, dict)
    assert isinstance(path, Path)
    item_id = str(item["id"])
    relative = path.relative_to(repo / "docs").as_posix()
    decision = adr_decision_outcome(data) or "pending"
    related = item.get("related", [])
    assert isinstance(related, list)
    return (
        f"| {item_id} | {md_cell(data.get('title', item_id))} | "
        f"{md_cell(decision)} | "
        f"{md_cell(str(item.get('effect', '')).replace('_', ' '))} | "
        f"{md_cell('; '.join(str(value) for value in related) or '—')} | "
        f"{md_cell(data.get('updated', ''))} | "
        f"{md_cell(data.get('research_refs', ''))} | [ADR]({relative}) |"
    )


def adr_amendment_index_rows(
    repo: Path,
    projection: Iterable[dict[str, object]],
) -> list[str]:
    rows: list[str] = []
    for item in projection:
        if item.get("table") != "CURRENT":
            continue
        data = item["data"]
        path = item["path"]
        assert isinstance(data, dict)
        assert isinstance(path, Path)
        try:
            constraints = parse_adr_constraint_array(
                data.get("amends_constraints", "[]"),
                "amends_constraints",
            )
        except EpctlError:
            constraints = []
        relative = path.relative_to(repo / "docs").as_posix()
        for constraint_ref in constraints:
            rows.append(
                f"| {constraint_ref} | {item['id']} | "
                f"{md_cell(data.get('title', str(item['id'])))} | "
                f"[ADR]({relative}) |"
            )
    return rows


def rebuild_adr_index_text(
    repo: Path,
    text: str,
    paths: Iterable[Path] | None = None,
) -> str:
    projection = adr_effect_projection(repo, paths)
    updated = text
    for table in ("ACTIVE", "CURRENT"):
        updated = replace_index_rows(
            updated,
            "ADR",
            table,
            (
                adr_index_row(repo, item)
                for item in projection
                if item.get("table") == table
            ),
        )
    updated = replace_index_rows(
        updated,
        "ADR",
        "AMENDMENTS",
        adr_amendment_index_rows(repo, projection),
    )
    for table in ("REVIEW", "COMPLETED"):
        updated = replace_index_rows(
            updated,
            "ADR",
            table,
            (
                adr_index_row(repo, item)
                for item in projection
                if item.get("table") == table
            ),
        )
    return updated


def managed_index_snapshots(repo: Path) -> dict[Path, str | None]:
    paths = {
        repo / "docs" / "PLANS.md",
        repo / "docs" / "RESEARCH.md",
        repo / "docs" / "DECISIONS.md",
        repo / "docs" / "DECISION-VIEWS.md",
        repo / "docs" / "BUGFIXES.md",
        repo / "docs" / ".epctl" / "state.json",
        decision_view_registry_path(repo),
    }
    view_root = repo / DECISION_VIEW_ROOT
    if view_root.is_dir() and not view_root.is_symlink():
        paths.update(view_root.glob("*.md"))
    return {
        path: path.read_text(encoding="utf-8") if path.is_file() else None
        for path in paths
    }


def restore_managed_indexes(snapshots: dict[Path, str | None]) -> None:
    restore_file_snapshots(snapshots)


def rebuild_indexes(repo: Path) -> dict[str, int]:
    init_repo(repo)
    plan_index = repo / "docs" / "PLANS.md"
    research_index = repo / "docs" / "RESEARCH.md"
    decision_index = repo / "docs" / "DECISIONS.md"
    bugfix_index = repo / "docs" / "BUGFIXES.md"
    active_plans = plan_files(repo, "active")
    completed_plans = plan_files(repo, "completed")
    active_research = research_files(repo, "active")
    completed_research = research_files(repo, "completed")
    adrs = adr_files(repo)
    active_bugfixes = bugfix_files(repo, "active")
    completed_bugfixes = bugfix_files(repo, "completed")

    plans_text = plan_index.read_text(encoding="utf-8")
    plans_text = replace_index_rows(
        plans_text,
        "EP",
        "ACTIVE",
        (plan_index_row(repo, path) for path in active_plans),
    )
    plans_text = replace_index_rows(
        plans_text,
        "EP",
        "COMPLETED",
        (plan_index_row(repo, path) for path in completed_plans),
    )
    atomic_write(plan_index, plans_text)

    research_text = research_index.read_text(encoding="utf-8")
    research_text = replace_index_rows(
        research_text,
        "R",
        "ACTIVE",
        (research_index_row(repo, path) for path in active_research),
    )
    research_text = replace_index_rows(
        research_text,
        "R",
        "COMPLETED",
        (research_index_row(repo, path) for path in completed_research),
    )
    atomic_write(research_index, research_text)

    decision_text = rebuild_adr_index_text(
        repo,
        decision_index.read_text(encoding="utf-8"),
        adrs,
    )
    atomic_write(decision_index, decision_text)

    bugfix_text = bugfix_index.read_text(encoding="utf-8")
    bugfix_text = replace_index_rows(
        bugfix_text,
        "BF",
        "ACTIVE",
        (bugfix_index_row(repo, path) for path in active_bugfixes),
    )
    bugfix_text = replace_index_rows(
        bugfix_text,
        "BF",
        "COMPLETED",
        (bugfix_index_row(repo, path) for path in completed_bugfixes),
    )
    atomic_write(bugfix_index, bugfix_text)

    decision_views = rebuild_decision_views(repo)

    state = load_state(repo)
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    for prefix in ("EP", "R", "ADR", "BF", "TD"):
        high_water[prefix] = max(
            int(high_water.get(prefix, 0)),
            max(scan_ids(repo, prefix), default=0),
        )
    save_state(repo, state)
    return {
        "plans": len(active_plans) + len(completed_plans),
        "research": len(active_research) + len(completed_research),
        "adrs": len(adrs),
        "decision_views": len(decision_views),
        "bugfixes": len(active_bugfixes) + len(completed_bugfixes),
    }


def plan_files(repo: Path, state: str | None = None) -> list[Path]:
    roots = (
        [repo / "docs" / "exec-plans" / state]
        if state
        else [
            repo / "docs" / "exec-plans" / "active",
            repo / "docs" / "exec-plans" / "completed",
        ]
    )
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        found.extend(root.glob("ep-*/EXECPLAN.md"))
        found.extend(root.glob("ep-*/README.md"))
        found.extend(root.glob("ep-*.md"))
    return sorted(set(found))


def research_files(repo: Path, state: str | None = None) -> list[Path]:
    roots = (
        [repo / "docs" / "research" / state]
        if state
        else [
            repo / "docs" / "research" / "active",
            repo / "docs" / "research" / "completed",
        ]
    )
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(root.glob("r-*/RESEARCH.md"))
    return sorted(set(found))


def adr_files(repo: Path) -> list[Path]:
    found: set[Path] = set()
    for root in architecture_roots(repo, existing_only=True):
        for path in root.rglob("*.md"):
            if re.search(r"(?i)^adr-\d{3,}(?=[_.-]|$)", path.name):
                found.add(path)
                continue
            try:
                data, _ = adr_document_data(path)
            except (EpctlError, OSError, UnicodeDecodeError):
                continue
            if data.get("doc_type", "").lower() == "adr":
                found.add(path)
    return sorted(found)


def bugfix_files(repo: Path, state: str | None = None) -> list[Path]:
    roots = (
        [repo / "docs" / "bugfixes" / state]
        if state
        else [
            repo / "docs" / "bugfixes" / "active",
            repo / "docs" / "bugfixes" / "completed",
        ]
    )
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(root.glob("bf-*.md"))
    return sorted(set(found))


def find_plan(repo: Path, plan_id: str, state: str | None = None) -> Path:
    target = plan_id.upper()
    id_match = ID_RE["EP"].fullmatch(target)
    target_number = int(id_match.group(1)) if id_match else -1
    matches: list[Path] = []
    for path in plan_files(repo, state):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except EpctlError:
            data = {}
        path_numbers = {
            int(number) for number in ID_RE["EP"].findall(path.as_posix())
        }
        if data.get("id", "").upper() == target or target_number in path_numbers:
            matches.append(path)
    if len(matches) != 1:
        raise EpctlError(f"Expected one {target} plan, found {len(matches)}")
    return matches[0]


def find_bugfix(repo: Path, bugfix_id: str, state: str | None = None) -> Path:
    target = bugfix_id.upper()
    id_match = ID_RE["BF"].fullmatch(target)
    target_number = int(id_match.group(1)) if id_match else -1
    matches: list[Path] = []
    for path in bugfix_files(repo, state):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except EpctlError:
            data = {}
        path_numbers = {int(number) for number in ID_RE["BF"].findall(path.name)}
        if data.get("id", "").upper() == target or target_number in path_numbers:
            matches.append(path)
    if len(matches) != 1:
        raise EpctlError(f"Expected one {target} bugfix, found {len(matches)}")
    return matches[0]


def find_research(repo: Path, research_id: str, state: str | None = None) -> Path:
    target = research_id.upper()
    id_match = ID_RE["R"].fullmatch(target)
    target_number = int(id_match.group(1)) if id_match else -1
    matches: list[Path] = []
    for path in research_files(repo, state):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except EpctlError:
            data = {}
        path_numbers = {
            int(number) for number in ID_RE["R"].findall(path.as_posix())
        }
        if data.get("id", "").upper() == target or target_number in path_numbers:
            matches.append(path)
    if len(matches) != 1:
        raise EpctlError(f"Expected one {target} Research package, found {len(matches)}")
    return matches[0]


def find_adr(repo: Path, adr_id: str) -> Path:
    target = adr_id.upper()
    id_match = ID_RE["ADR"].fullmatch(target)
    target_number = int(id_match.group(1)) if id_match else -1
    matches: list[Path] = []
    for path in adr_files(repo):
        path_number = path_id_number(path, "ADR")
        if path.is_symlink():
            if path_number == target_number:
                reject_symlink_path(repo, path)
            continue
        try:
            data, _ = adr_document_data(path)
        except EpctlError:
            data = {}
        path_numbers = {path_number} if path_number is not None else set()
        if data.get("id", "").upper() == target or target_number in path_numbers:
            reject_symlink_path(repo, path)
            matches.append(path)
    if len(matches) != 1:
        raise EpctlError(f"Expected one {target} ADR, found {len(matches)}")
    return matches[0]


def adr_revision_root(repo: Path) -> Path:
    return repo / ADR_REVISION_ROOT


def adr_revision_path(repo: Path, adr_id: str, digest: str) -> Path:
    normalized_id = normalize_reference_ids((adr_id,), "ADR")[0]
    normalized_digest = digest.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized_digest):
        raise EpctlError("ADR revision digest must be 64 lowercase hexadecimal characters")
    return (
        adr_revision_root(repo)
        / normalized_id
        / f"sha256-{normalized_digest}.md"
    )


def normalized_utf8_document(raw: bytes, source: str) -> str:
    if len(raw) > ADR_REVISION_MAX_BYTES:
        raise EpctlError(
            f"ADR revision source exceeds {ADR_REVISION_MAX_BYTES} bytes: {source}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EpctlError(f"ADR revision source is not UTF-8: {source}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_adr_revision_file(repo: Path, value: str) -> tuple[str, str]:
    relative, path = repository_relative_path(
        repo,
        value,
        "ADR revision source",
        require_file=True,
    )
    if path.stat().st_size > ADR_REVISION_MAX_BYTES:
        raise EpctlError(
            f"ADR revision source exceeds {ADR_REVISION_MAX_BYTES} bytes: {relative}"
        )
    return normalized_utf8_document(path.read_bytes(), relative), relative


def git_blob(repo: Path, object_id: str) -> tuple[str, str]:
    normalized = object_id.strip().lower()
    if not GIT_OBJECT_ID_RE.fullmatch(normalized):
        raise EpctlError(
            "--from-git-blob requires a full 40- or 64-character hexadecimal object ID"
        )

    def run_git(*arguments: str, text: bool = True) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                ["git", "-C", str(repo), *arguments],
                capture_output=True,
                text=text,
                timeout=30,
                check=False,
            )
        except FileNotFoundError as exc:
            raise EpctlError(
                "Git is unavailable; use --from-file with a repository-relative source"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise EpctlError(f"Git timed out while reading object {normalized}") from exc

    object_type = run_git("cat-file", "-t", normalized)
    if object_type.returncode != 0:
        details = object_type.stderr.strip() or "object not found"
        raise EpctlError(f"Cannot read Git object {normalized}: {details}")
    if object_type.stdout.strip() != "blob":
        raise EpctlError(f"Git object {normalized} is not a blob")
    size_result = run_git("cat-file", "-s", normalized)
    try:
        size = int(size_result.stdout.strip()) if size_result.returncode == 0 else -1
    except ValueError:
        size = -1
    if size < 0:
        details = size_result.stderr.strip() or "invalid object size"
        raise EpctlError(f"Cannot size Git blob {normalized}: {details}")
    if size > ADR_REVISION_MAX_BYTES:
        raise EpctlError(
            f"ADR revision source exceeds {ADR_REVISION_MAX_BYTES} bytes: {normalized}"
        )
    content = run_git("cat-file", "blob", normalized, text=False)
    if content.returncode != 0:
        details = content.stderr.decode("utf-8", errors="replace").strip()
        raise EpctlError(f"Cannot read Git blob {normalized}: {details}")
    return normalized_utf8_document(content.stdout, normalized), normalized


def normalize_document_refs(
    repo: Path,
    values: Iterable[str],
    field: str,
) -> list[str]:
    normalized: list[str] = []
    roots = architecture_roots(repo, existing_only=True)
    for value in values:
        relative, path = repository_relative_path(
            repo,
            value,
            field,
            require_file=True,
        )
        if path.suffix.lower() != ".md":
            raise EpctlError(f"{field} must reference Markdown files: {relative}")
        if not any(path == root or root in path.parents for root in roots):
            raise EpctlError(
                f"{field} must be inside a registered architecture root: {relative}"
            )
        if relative not in normalized:
            normalized.append(relative)
    return normalized


def parse_design_evidence(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in parse_string_array(value, "design_evidence"):
        match = DESIGN_EVIDENCE_RE.fullmatch(item)
        if not match:
            raise EpctlError(
                "design_evidence must use "
                "DD-NNN@rev:N@sha256:<64 lowercase hex>"
            )
        design_id = match.group(1).upper()
        normalized = (
            f"{design_id}@rev:{int(match.group(2))}@sha256:{match.group(3)}"
        )
        if design_id in result:
            raise EpctlError(f"design_evidence duplicates {design_id}")
        result[design_id] = normalized
    return result


def design_manifest_digest(value: dict[str, object]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EpctlError(f"missing {label}: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EpctlError(f"invalid {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EpctlError(f"{label} must be a JSON object: {path}")
    return value


def verify_design_manifest(
    repo: Path,
    manifest_path: Path,
    bundle_root: Path,
    *,
    design_id: str,
    layout: str,
    root_data: dict[str, str] | None = None,
    revision: int | None = None,
    snapshot: bool = False,
) -> tuple[dict[str, object] | None, list[str]]:
    errors: list[str] = []
    try:
        manifest = load_json_object(manifest_path, "Design manifest")
    except EpctlError as exc:
        return None, [str(exc)]
    expected_type = (
        "design-revision-manifest" if layout == "single" else "design-manifest"
    )
    if manifest.get("schema_version") != "1":
        errors.append(f"{manifest_path}: schema_version must be '1'")
    if manifest.get("metadata_schema") != CURRENT_METADATA_SCHEMA:
        errors.append(f"{manifest_path}: metadata_schema must be '1'")
    if manifest.get("artifact_type") != expected_type:
        errors.append(
            f"{manifest_path}: artifact_type must be {expected_type!r}"
        )
    if manifest.get("design_id") != design_id:
        errors.append(f"{manifest_path}: design_id must be {design_id}")
    if manifest.get("layout") != layout:
        errors.append(f"{manifest_path}: layout must be {layout!r}")
    if root_data is not None:
        for field in (
            "status",
            "author",
            "owner",
            "created",
            "updated",
        ):
            if manifest.get(field) != root_data.get(field, ""):
                errors.append(
                    f"{manifest_path}: {field} does not match Design root"
                )
        for field in ("working_revision", "published_revision"):
            try:
                expected = int(root_data.get(field, ""))
            except ValueError:
                expected = -1
            if manifest.get(field) != expected:
                errors.append(
                    f"{manifest_path}: {field} does not match Design root"
                )
    if revision is not None:
        manifest_revision = (
            manifest.get("revision")
            if layout == "single"
            else manifest.get("published_revision")
        )
        if manifest_revision != revision:
            errors.append(
                f"{manifest_path}: snapshot revision must be {revision}"
            )
    if layout == "package":
        if manifest.get("entrypoint") != "DESIGN.md":
            errors.append(f"{manifest_path}: entrypoint must be DESIGN.md")
        if manifest.get("reading_map") != "docs/README.md":
            errors.append(
                f"{manifest_path}: reading_map must be docs/README.md"
            )
    elif manifest.get("entrypoint") != "DESIGN.md":
        errors.append(f"{manifest_path}: entrypoint must be DESIGN.md")

    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        return manifest, errors + [f"{manifest_path}: documents must be non-empty"]
    paths: set[str] = set()
    ids: set[str] = set()
    reading_maps = 0
    for position, item in enumerate(documents, start=1):
        prefix = f"{manifest_path}: document #{position}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        document_id = item.get("id")
        role = item.get("role")
        raw_path = item.get("path")
        if not isinstance(document_id, str) or not document_id:
            errors.append(f"{prefix} id must be non-empty")
        elif document_id in ids:
            errors.append(f"{prefix} duplicates id {document_id}")
        else:
            ids.add(document_id)
        if role == "reading-map":
            reading_maps += 1
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"{prefix} path must be non-empty")
            continue
        candidate = bundle_root / raw_path
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(bundle_root.resolve(strict=True))
        except (FileNotFoundError, ValueError):
            errors.append(f"{prefix} path is missing or escapes bundle: {raw_path}")
            continue
        if candidate.is_symlink():
            errors.append(f"{prefix} path must not be a symbolic link: {raw_path}")
            continue
        if raw_path in paths:
            errors.append(f"{prefix} duplicates path {raw_path}")
            continue
        paths.add(raw_path)
        payload = candidate.read_bytes()
        if item.get("bytes") != len(payload):
            errors.append(f"{prefix} byte count drift for {raw_path}")
        digest = hashlib.sha256(payload).hexdigest()
        if item.get("sha256") != digest:
            errors.append(f"{prefix} SHA-256 drift for {raw_path}")
    if "DESIGN.md" not in paths:
        errors.append(f"{manifest_path}: documents must include DESIGN.md")
    if layout == "package":
        if "docs/README.md" not in paths or reading_maps != 1:
            errors.append(
                f"{manifest_path}: package requires one docs/README.md reading map"
            )
        managed_paths = {"DESIGN.md"}
        managed_roots = {
            "architecture",
            "contracts",
            "data",
            "docs",
            "operations",
            "migration",
            "verification",
        }
        for candidate in bundle_root.rglob("*.md"):
            relative = candidate.relative_to(bundle_root)
            if not snapshot and "snapshots" in relative.parts:
                continue
            if snapshot or (relative.parts and relative.parts[0] in managed_roots):
                managed_paths.add(relative.as_posix())
        if paths != managed_paths:
            missing = managed_paths - paths
            extra = paths - managed_paths
            if missing:
                errors.append(
                    f"{manifest_path}: unregistered managed Markdown: "
                    + ", ".join(sorted(missing))
                )
            if extra:
                errors.append(
                    f"{manifest_path}: manifest paths outside managed set: "
                    + ", ".join(sorted(extra))
                )
    elif paths != {"DESIGN.md"}:
        errors.append(
            f"{manifest_path}: single revision must contain only DESIGN.md"
        )
    return manifest, errors


def design_snapshot_contract(
    repo: Path,
    path: Path,
    data: dict[str, str],
    revision: int,
) -> tuple[str, list[str]]:
    design_id = data.get("id", "").upper()
    layout = data.get("layout", "")
    if layout == "package":
        snapshot = path.parent / "snapshots" / f"rev-{revision:03d}"
    else:
        snapshot = (
            repo
            / "docs"
            / ".designctl"
            / "snapshots"
            / design_id
            / f"rev-{revision:03d}"
        )
    manifest_path = snapshot / "DESIGN_MANIFEST.json"
    manifest, errors = verify_design_manifest(
        repo,
        manifest_path,
        snapshot,
        design_id=design_id,
        layout=layout,
        revision=revision,
        snapshot=True,
    )
    if manifest is None:
        return "", errors
    evidence = (
        f"{design_id}@rev:{revision}@sha256:"
        f"{design_manifest_digest(manifest)}"
    )
    return evidence, errors


def design_ref_details(
    repo: Path,
    value: str,
    *,
    entrypoint: bool = False,
) -> tuple[dict[str, object], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    label = "architecture_entrypoint" if entrypoint else "design_refs"
    try:
        refs = normalize_document_refs(repo, (value,), label)
    except EpctlError as exc:
        return {}, [str(exc)], warnings
    relative = refs[0]
    path = repo / relative
    try:
        data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    except EpctlError:
        try:
            data, _, _ = parse_legacy_frontmatter(
                path.read_text(encoding="utf-8")
            )
        except EpctlError:
            warnings.append(
                f"{path}: linked Design Doc has no readable metadata"
            )
            return {"path": relative}, errors, warnings
    design_id = data.get("id", "").upper()
    if data.get("metadata_schema"):
        errors.extend(
            validate_metadata_contract(path, data, "design-doc", design_id)
        )
        if not ID_RE["DD"].fullmatch(design_id):
            errors.append(f"{path}: Design Doc id must use DD-NNN")
    else:
        warnings.append(
            f"{path}: legacy Design Doc has no Artifact Metadata Contract"
        )
    doc_type = data.get("doc_type", "")
    if doc_type and doc_type != "design":
        errors.append(f"{path}: design_refs target has doc_type {doc_type!r}")
    elif not doc_type:
        warnings.append(f"{path}: linked Design Doc has no doc_type")
    status = data.get("status", "").lower()
    if status in {"obsolete", "abandoned", "superseded", "rejected"}:
        errors.append(f"{path}: linked Design Doc has terminal status {status!r}")
    elif status in {"draft", "review_ready"}:
        warnings.append(f"{path}: linked Design Doc is unpublished ({status})")
    elif not status:
        warnings.append(f"{path}: linked Design Doc has no status")

    details: dict[str, object] = {
        "path": relative,
        "data": data,
        "id": design_id,
        "legacy": data.get("schema_version") != "1.1",
        "dependencies": [],
        "evidence": "",
    }
    if data.get("schema_version") != "1.1":
        return details, errors, warnings
    layout = data.get("layout", "")
    if layout not in {"single", "package"}:
        errors.append(f"{path}: Design layout must be single or package")
    elif layout == "package" and path.name != "DESIGN.md":
        errors.append(f"{path}: package Design entrypoint must be DESIGN.md")
    elif layout == "single" and path.parent != repo / "docs" / "design-docs":
        errors.append(
            f"{path}: single Design must be directly under docs/design-docs"
        )
    try:
        dependencies = parse_string_array(
            data.get("design_dependencies", "[]"),
            "design_dependencies",
        )
    except EpctlError as exc:
        errors.append(f"{path}: {exc}")
        dependencies = []
    normalized_dependencies: list[str] = []
    for dependency in dependencies:
        if ":" not in dependency:
            errors.append(
                f"{path}: Design dependency must use TYPE:DD-NNN: {dependency}"
            )
            continue
        kind, target = dependency.split(":", 1)
        target = target.upper()
        if kind not in {"uses", "extends", "implements", "replaces"}:
            errors.append(f"{path}: invalid Design dependency type {kind!r}")
        if not ID_RE["DD"].fullmatch(target):
            errors.append(f"{path}: invalid Design dependency target {target!r}")
        normalized_dependencies.append(f"{kind}:{target}")
    details["dependencies"] = normalized_dependencies
    try:
        published_revision = int(data.get("published_revision", "0"))
        working_revision = int(data.get("working_revision", "0"))
    except ValueError:
        errors.append(f"{path}: Design revisions must be integers")
        published_revision = 0
        working_revision = 0
    if working_revision < 1 or published_revision < 0:
        errors.append(f"{path}: invalid Design revision counters")
    if status == "current" and working_revision != published_revision:
        errors.append(
            f"{path}: current Design working revision must be published"
        )
    if status == "revising" and published_revision > 0:
        warnings.append(
            f"{path}: working revision is unpublished; consumers use rev "
            f"{published_revision}"
        )
    if layout == "package":
        _, manifest_errors = verify_design_manifest(
            repo,
            path.parent / "DESIGN_MANIFEST.json",
            path.parent,
            design_id=design_id,
            layout=layout,
            root_data=data,
        )
        errors.extend(manifest_errors)
    if published_revision > 0:
        evidence, snapshot_errors = design_snapshot_contract(
            repo, path, data, published_revision
        )
        details["evidence"] = evidence
        errors.extend(snapshot_errors)
        if not all(
            data.get(field, "").strip()
            for field in ("approved_by", "approved_at", "approval_ref")
        ):
            errors.append(f"{path}: published Design lacks approval metadata")
    elif status == "current":
        errors.append(f"{path}: current Design has no approved revision")
    return details, list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def validate_design_evidence(
    repo: Path,
    design_ref: str,
    evidence: str,
) -> list[str]:
    details, errors, _ = design_ref_details(repo, design_ref)
    if errors:
        return errors
    data = details.get("data")
    if not isinstance(data, dict) or details.get("legacy"):
        return [f"{design_ref}: legacy Design cannot carry revision evidence"]
    match = DESIGN_EVIDENCE_RE.fullmatch(evidence)
    if not match or match.group(1).upper() != details.get("id"):
        return [f"{design_ref}: Design evidence identity does not match"]
    revision = int(match.group(2))
    actual, snapshot_errors = design_snapshot_contract(
        repo,
        repo / str(details["path"]),
        data,
        revision,
    )
    if actual != evidence:
        snapshot_errors.append(
            f"{design_ref}: Design evidence digest changed for {evidence}"
        )
    return list(dict.fromkeys(snapshot_errors))


def design_completion_blockers(
    repo: Path,
    schema_version: str,
    design_details: dict[str, dict[str, object]],
    design_evidence: dict[str, str],
) -> list[str]:
    if schema_version != "2.8":
        return []
    blockers: list[str] = []
    for design_id, details in sorted(design_details.items()):
        data = details.get("data")
        if not isinstance(data, dict):
            blockers.append(f"design_inputs_invalid:{design_id}")
            continue
        if details.get("legacy"):
            if data.get("status") != "current":
                blockers.append(f"design_unpublished:{design_id}")
            continue
        evidence = design_evidence.get(design_id)
        if not evidence:
            blockers.append(f"design_evidence_missing:{design_id}")
            continue
        evidence_errors = validate_design_evidence(
            repo,
            str(details["path"]),
            evidence,
        )
        if evidence_errors:
            blockers.append(f"design_evidence_invalid:{design_id}")
    return blockers


def validate_design_ref(
    repo: Path,
    value: str,
    *,
    entrypoint: bool = False,
) -> tuple[list[str], list[str]]:
    _, errors, warnings = design_ref_details(
        repo,
        value,
        entrypoint=entrypoint,
    )
    return errors, warnings


def validate_design_input_set(
    repo: Path,
    design_refs: Iterable[str],
) -> tuple[dict[str, dict[str, object]], list[str], list[str]]:
    details_by_id: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    warnings: list[str] = []
    for design_ref in design_refs:
        details, item_errors, item_warnings = design_ref_details(repo, design_ref)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        design_id = details.get("id")
        if not isinstance(design_id, str) or not design_id:
            continue
        previous = details_by_id.get(design_id)
        if previous is not None and previous.get("path") != details.get("path"):
            errors.append(
                f"design_refs duplicate {design_id}: "
                f"{previous.get('path')} and {details.get('path')}"
            )
        else:
            details_by_id[design_id] = details

    graph: dict[str, list[str]] = {}
    for design_id, details in details_by_id.items():
        targets: list[str] = []
        dependencies = details.get("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []
        for dependency in dependencies:
            if not isinstance(dependency, str) or ":" not in dependency:
                continue
            target = dependency.split(":", 1)[1].upper()
            targets.append(target)
            if target not in details_by_id:
                errors.append(
                    f"{details.get('path')}: Design dependency closure "
                    f"requires a design_ref for {target}"
                )
        graph[design_id] = targets

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            cycle = trail[trail.index(node) :] + [node]
            errors.append("Design dependency cycle: " + " -> ".join(cycle))
            return
        if node in visited:
            return
        visiting.add(node)
        for target in graph.get(node, []):
            if target in graph:
                visit(target, trail + [target])
        visiting.remove(node)
        visited.add(node)

    for design_id in graph:
        visit(design_id, [design_id])
    return (
        details_by_id,
        list(dict.fromkeys(errors)),
        list(dict.fromkeys(warnings)),
    )


def validate_design_doc_corpus(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_paths: set[Path] = set()
    paths_by_id: dict[str, Path] = {}
    for root in architecture_roots(repo, existing_only=True):
        for path in sorted(root.rglob("*.md")):
            if "snapshots" in path.relative_to(root).parts:
                continue
            resolved = path.resolve(strict=False)
            if resolved in seen_paths or path.is_symlink():
                continue
            seen_paths.add(resolved)
            try:
                data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            except (EpctlError, OSError, UnicodeDecodeError):
                continue
            if data.get("doc_type", "").lower() != "design":
                continue
            if not data.get("metadata_schema"):
                warnings.append(
                    f"{path}: legacy Design Doc has no Artifact Metadata Contract"
                )
                continue
            design_id = data.get("id", "")
            errors.extend(
                validate_metadata_contract(
                    path,
                    data,
                    "design-doc",
                    design_id,
                )
            )
            if not ID_RE["DD"].fullmatch(design_id):
                errors.append(f"{path}: Design Doc id must use DD-NNN")
                continue
            previous = paths_by_id.get(design_id)
            if previous is not None:
                errors.append(
                    f"{path}: duplicate Design Doc id {design_id}; "
                    f"already used by {previous}"
                )
            else:
                paths_by_id[design_id] = path
            if data.get("schema_version") == "1.1":
                relative = path.relative_to(repo).as_posix()
                _, contract_errors, contract_warnings = design_ref_details(
                    repo,
                    relative,
                )
                errors.extend(contract_errors)
                warnings.extend(contract_warnings)
    return errors, warnings


def adr_relations(data: dict[str, str]) -> list[str]:
    relations: list[str] = []
    for field in ("depends_on", "amends"):
        relations.extend(parse_reference_array(data.get(field, ""), "ADR", field))
    return list(dict.fromkeys(relations))


def adr_decision_outcome(data: dict[str, str]) -> str:
    if data.get("schema_version") == "1.4":
        return data.get("decision_outcome", "")
    status = data.get("status", "")
    return "accepted" if status in ADR_ACCEPTED_ORIGIN_STATUSES else status


def adr_corpus_data(repo: Path) -> dict[str, dict[str, str]]:
    corpus: dict[str, dict[str, str]] = {}
    for path in adr_files(repo):
        try:
            data, _ = adr_document_data(path)
        except (EpctlError, OSError, UnicodeDecodeError):
            continue
        adr_id = data.get("id", "")
        if adr_id:
            corpus[adr_id] = data
    return corpus


def adr_currentness(
    repo: Path,
    adr_id: str,
    *,
    data_by_id: dict[str, dict[str, str]] | None = None,
    _memo: dict[str, tuple[bool, list[str]]] | None = None,
) -> tuple[bool, list[str]]:
    corpus = data_by_id if data_by_id is not None else adr_corpus_data(repo)
    normalized = normalize_reference_ids((adr_id,), "ADR")[0]
    memo = _memo if _memo is not None else {}
    visiting: list[str] = []

    def visit(item_id: str) -> tuple[bool, list[str]]:
        if item_id in memo:
            return memo[item_id]
        if item_id in visiting:
            cycle = " -> ".join((*visiting[visiting.index(item_id) :], item_id))
            result = (False, [f"ADR dependency cycle: {cycle}"])
            memo[item_id] = result
            return result
        data = corpus.get(item_id)
        if data is None:
            result = (False, [f"{item_id} is missing"])
            memo[item_id] = result
            return result
        reasons: list[str] = []
        status = data.get("status", "")
        if status != "accepted":
            reasons.append(f"{item_id} status is {status or 'missing'}")
        visiting.append(item_id)
        try:
            for related_id in adr_relations(data):
                related_current, related_reasons = visit(related_id)
                if not related_current:
                    reasons.append(
                        f"{item_id} references non-current {related_id}"
                    )
                    reasons.extend(related_reasons)
        except EpctlError as exc:
            reasons.append(str(exc))
        visiting.pop()
        result = (not reasons, list(dict.fromkeys(reasons)))
        memo[item_id] = result
        return result

    return visit(normalized)


def architecture_review_reasons(
    repo: Path,
    adr_values: Iterable[str],
) -> list[str]:
    corpus = adr_corpus_data(repo)
    reasons: list[str] = []
    for adr_id in normalize_reference_ids(adr_values, "ADR"):
        current, item_reasons = adr_currentness(
            repo,
            adr_id,
            data_by_id=corpus,
        )
        if not current:
            reasons.extend(item_reasons)
    return list(dict.fromkeys(reasons))


def adr_input_closure(
    repo: Path,
    adr_values: Iterable[str],
    *,
    allowed_statuses: set[str] | None = None,
    historical: bool = False,
    data_overrides: dict[str, dict[str, str]] | None = None,
) -> tuple[list[str], dict[str, dict[str, str]]]:
    requested = normalize_reference_ids(adr_values, "ADR")
    valid_statuses = allowed_statuses or {"accepted"}
    ordered: list[str] = []
    data_by_id: dict[str, dict[str, str]] = {}
    visiting: list[str] = []

    def visit(adr_id: str) -> None:
        if adr_id in visiting:
            cycle = " -> ".join((*visiting[visiting.index(adr_id) :], adr_id))
            raise EpctlError(f"ADR dependency cycle: {cycle}")
        if adr_id in data_by_id:
            return
        if data_overrides and adr_id in data_overrides:
            adr_errors: list[str] = []
            data = data_overrides[adr_id]
        else:
            path = find_adr(repo, adr_id)
            adr_errors, _, data = validate_adr(path, historical=historical)
        if adr_errors or data.get("status") not in valid_statuses:
            details = "; ".join(adr_errors) if adr_errors else data.get("status", "")
            if valid_statuses == {"accepted"} and not historical:
                raise EpctlError(
                    f"{adr_id} must be valid, accepted and current: {details}"
                )
            raise EpctlError(
                f"{adr_id} must be valid with status in "
                f"{sorted(valid_statuses)}: {details}"
            )
        visiting.append(adr_id)
        for dependency in adr_relations(data):
            visit(dependency)
        visiting.pop()
        data_by_id[adr_id] = data
        ordered.append(adr_id)

    for adr_id in requested:
        visit(adr_id)
    if not historical and valid_statuses == {"accepted"}:
        corpus = adr_corpus_data(repo)
        if data_overrides:
            corpus.update(data_overrides)
        for adr_id in requested:
            current, reasons = adr_currentness(
                repo,
                adr_id,
                data_by_id=corpus,
            )
            if not current:
                raise EpctlError(
                    f"{adr_id} must be valid, accepted and current: "
                    + "; ".join(reasons)
                )
    return ordered, data_by_id


def resolve_decision_context(
    repo: Path,
    adr_values: Iterable[str],
) -> dict[str, object]:
    raw_values = list(adr_values)
    direct_adrs = normalize_reference_ids(raw_values, "ADR")
    if not direct_adrs:
        raise EpctlError("Decision context requires at least one ADR")
    if len(direct_adrs) != len(raw_values):
        raise EpctlError("Decision context contains duplicate ADR references")

    closure, data_by_id = adr_input_closure(repo, direct_adrs)
    resolved = set(closure)
    corpus = adr_corpus_data(repo)

    while True:
        structured_refs: set[str] = set()
        for adr_id in sorted(resolved):
            path = find_adr(repo, adr_id)
            structured_refs.update(
                adr_constraint_refs(path.read_text(encoding="utf-8"), adr_id)
            )
        amendment_candidates: list[str] = []
        for candidate_id, candidate in corpus.items():
            if candidate_id in resolved or candidate.get("status") != "accepted":
                continue
            current, _ = adr_currentness(
                repo,
                candidate_id,
                data_by_id=corpus,
            )
            if not current:
                continue
            amended_adrs = set(
                parse_inline_ids(candidate.get("amends", ""), "ADR")
            )
            amended_constraints = set(
                parse_adr_constraint_array(
                    candidate.get("amends_constraints", "[]"),
                    "amends_constraints",
                )
            )
            if amended_adrs & resolved or amended_constraints & structured_refs:
                amendment_candidates.append(candidate_id)
        if not amendment_candidates:
            break
        for candidate_id in sorted(amendment_candidates):
            candidate_closure, candidate_data = adr_input_closure(
                repo,
                (candidate_id,),
            )
            resolved.update(candidate_closure)
            data_by_id.update(candidate_data)

    ordered_adrs = sorted(resolved)
    projection = {
        str(item["id"]): item for item in adr_effect_projection(repo)
    }
    sources: list[dict[str, object]] = []
    all_constraint_refs: list[str] = []
    amendment_targets: dict[str, list[str]] = {}
    for adr_id in ordered_adrs:
        path = find_adr(repo, adr_id)
        raw_source = path.read_bytes()
        try:
            text = raw_source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EpctlError(f"{adr_id} source is not UTF-8: {path}") from exc
        item_errors, _, data = validate_adr(path)
        if item_errors:
            raise EpctlError(
                f"{adr_id} is not valid for a Decision context:\n- "
                + "\n- ".join(item_errors)
            )
        if data.get("status") != "accepted":
            raise EpctlError(
                f"{adr_id} must be accepted and current for a Decision context"
            )
        current, reasons = adr_currentness(
            repo,
            adr_id,
            data_by_id=corpus,
        )
        if not current:
            raise EpctlError(
                f"{adr_id} must be current for a Decision context: "
                + "; ".join(reasons)
            )
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        _, strict = adr_document_data_from_text(path, normalized_text)
        structured = strict and data.get("schema_version") in {
            "1.2",
            "1.3",
            "1.4",
        }
        decision_source = ""
        constraint_headers: list[str] = []
        constraint_rows: list[dict[str, object]] = []
        if structured:
            decision_source = markdown_section_source(text, "Decision Statement")
            constraint_headers, constraint_rows = adr_constraint_source_rows(
                text,
                adr_id,
            )
            all_constraint_refs.extend(
                str(row["ref"]) for row in constraint_rows
            )
        amended_constraints = parse_adr_constraint_array(
            data.get("amends_constraints", "[]"),
            "amends_constraints",
        )
        for target in amended_constraints:
            amendment_targets.setdefault(target, []).append(adr_id)
        document_sha256 = hashlib.sha256(raw_source).hexdigest()
        payload_digest = inline_text(data.get("payload_sha256", ""))
        sources.append(
            {
                "id": adr_id,
                "title": data.get("title", ""),
                "path": path.relative_to(repo).as_posix(),
                "text": text,
                "data": data,
                "contract": "strict-structured" if structured else "whole-document",
                "document_sha256": document_sha256,
                "payload_sha256": payload_digest,
                "decision_source": decision_source,
                "constraint_headers": constraint_headers,
                "constraint_rows": constraint_rows,
                "effect": projection.get(adr_id, {}).get("effect", "current"),
                "amended_by": projection.get(adr_id, {}).get("amended_by", []),
            }
        )
    for values in amendment_targets.values():
        values.sort()
    return {
        "direct_adrs": sorted(direct_adrs),
        "resolved_adrs": ordered_adrs,
        "sources": sources,
        "constraint_refs": sorted(all_constraint_refs),
        "amendment_targets": dict(sorted(amendment_targets.items())),
    }


def decision_context_source_by_id(
    context: dict[str, object],
) -> dict[str, dict[str, object]]:
    sources = context.get("sources", [])
    assert isinstance(sources, list)
    return {
        str(source["id"]): source
        for source in sources
        if isinstance(source, dict)
    }


def expanded_decision_constraint_refs(
    context: dict[str, object],
    constraint_values: Iterable[str],
) -> tuple[list[str], list[str]]:
    raw_values = list(constraint_values)
    requested = normalize_adr_constraint_refs(
        raw_values,
        "constraint selection",
    )
    if len(requested) != len(raw_values):
        raise EpctlError("Decision capsule constraint selection contains duplicates")
    available = {
        str(value) for value in context.get("constraint_refs", [])
    }
    if not requested:
        return [], sorted(available)
    missing = sorted(set(requested) - available)
    if missing:
        raise EpctlError(
            "Decision capsule constraints are outside the resolved context: "
            + ", ".join(missing)
        )
    selected = set(requested)
    amendment_targets = context.get("amendment_targets", {})
    assert isinstance(amendment_targets, dict)
    source_by_id = decision_context_source_by_id(context)
    changed = True
    while changed:
        changed = False
        for reference in list(selected):
            for amender_id in amendment_targets.get(reference, []):
                amender = source_by_id.get(str(amender_id))
                if not amender:
                    continue
                for row in amender.get("constraint_rows", []):
                    assert isinstance(row, dict)
                    target = str(row["ref"])
                    if target not in selected:
                        selected.add(target)
                        changed = True
            source_id = reference.split("#", 1)[0]
            source = source_by_id.get(source_id)
            if not source:
                continue
            data = source.get("data", {})
            assert isinstance(data, dict)
            for target in parse_adr_constraint_array(
                str(data.get("amends_constraints", "[]")),
                "amends_constraints",
            ):
                if target in available and target not in selected:
                    selected.add(target)
                    changed = True
    return sorted(requested), sorted(selected)


def compile_decision_capsule(
    context: dict[str, object],
    constraint_values: Iterable[str] = (),
    *,
    budget_bytes: int | None = DECISION_CAPSULE_DEFAULT_BUDGET_BYTES,
    budget_reason: str = "",
) -> dict[str, object]:
    if budget_bytes is not None:
        if not isinstance(budget_bytes, int) or budget_bytes <= 0:
            raise EpctlError("Decision capsule budget must be a positive integer")
        if (
            budget_bytes > DECISION_CAPSULE_DEFAULT_BUDGET_BYTES
            and not inline_text(budget_reason)
        ):
            raise EpctlError(
                "A Decision capsule budget above 32768 bytes requires "
                "--budget-reason"
            )
    requested_constraints, selected_constraints = (
        expanded_decision_constraint_refs(context, constraint_values)
    )
    selected_set = set(selected_constraints)
    direct_adrs = [str(value) for value in context.get("direct_adrs", [])]
    resolved_adrs = [str(value) for value in context.get("resolved_adrs", [])]
    amendment_targets = context.get("amendment_targets", {})
    assert isinstance(amendment_targets, dict)
    chunks = [
        "# ADR Decision Context Capsule\n\n",
        f"Protocol: `{DECISION_CAPSULE_SCHEMA_VERSION}`\n\n",
        "This is a non-normative retrieval projection. ADR source documents, "
        "their seals, and explicit lifecycle authority remain normative. "
        "Source text inside the marked blocks is exact and digest-verified; it "
        "has not been summarized or truncated.\n\n",
        "- Direct ADRs: "
        + (", ".join(f"`{item}`" for item in direct_adrs) or "none")
        + "\n",
        "- Resolved current ADRs: "
        + (", ".join(f"`{item}`" for item in resolved_adrs) or "none")
        + "\n",
        "- Requested constraints: "
        + (
            ", ".join(f"`{item}`" for item in requested_constraints)
            if requested_constraints
            else "all structured constraints in the resolved context"
        )
        + "\n",
        "- Exact selected constraints after amendment expansion: "
        + (", ".join(f"`{item}`" for item in selected_constraints) or "none")
        + "\n",
    ]
    source_costs: list[dict[str, object]] = []
    sources = context.get("sources", [])
    assert isinstance(sources, list)
    for source in sources:
        assert isinstance(source, dict)
        adr_id = str(source["id"])
        title = str(source.get("title", ""))
        path = str(source["path"])
        contract = str(source["contract"])
        metadata = (
            f"\n\n## {adr_id}: {title}\n\n"
            f"- Source: `{path}`\n"
            f"- Contract: `{contract}`\n"
            f"- Document SHA-256: `{source['document_sha256']}`\n"
        )
        payload_digest = str(source.get("payload_sha256", ""))
        if payload_digest:
            metadata += f"- Decision payload SHA-256: `{payload_digest}`\n"
        if contract == "whole-document":
            exact = str(source["text"])
            source_chunk = (
                metadata
                + f"\n--- BEGIN EXACT WHOLE ADR {adr_id} ---\n"
                + exact
                + ("" if exact.endswith("\n") else "\n")
                + f"--- END EXACT WHOLE ADR {adr_id} ---\n"
            )
        else:
            decision_source = str(source["decision_source"])
            source_chunk = (
                metadata
                + f"\n--- BEGIN EXACT DECISION STATEMENT {adr_id} ---\n"
                + decision_source
                + ("" if decision_source.endswith("\n") else "\n")
                + f"--- END EXACT DECISION STATEMENT {adr_id} ---\n"
            )
            rows = [
                row
                for row in source.get("constraint_rows", [])
                if isinstance(row, dict) and str(row["ref"]) in selected_set
            ]
            if rows:
                source_chunk += (
                    f"\n--- BEGIN EXACT SELECTED CONSTRAINTS {adr_id} ---\n"
                    "## Normative Constraints\n\n"
                )
                for line in source.get("constraint_headers", []):
                    exact_line = str(line)
                    source_chunk += exact_line
                    if not exact_line.endswith(("\n", "\r")):
                        source_chunk += "\n"
                for row in rows:
                    reference = str(row["ref"])
                    amenders = amendment_targets.get(reference, [])
                    if amenders:
                        source_chunk += (
                            "<!-- Current amendment: "
                            + ", ".join(str(item) for item in amenders)
                            + " -->\n"
                        )
                    exact_line = str(row["line"])
                    source_chunk += exact_line
                    if not exact_line.endswith(("\n", "\r")):
                        source_chunk += "\n"
                source_chunk += f"--- END EXACT SELECTED CONSTRAINTS {adr_id} ---\n"
        source_bytes = len(source_chunk.encode("utf-8"))
        source_costs.append(
            {
                "adr_id": adr_id,
                "bytes": source_bytes,
                "contract": contract,
            }
        )
        chunks.append(source_chunk)
    capsule = "".join(chunks)
    capsule_bytes = len(capsule.encode("utf-8"))
    capsule_sha256 = hashlib.sha256(capsule.encode("utf-8")).hexdigest()
    if budget_bytes is not None and capsule_bytes > budget_bytes:
        cost_text = ", ".join(
            f"{item['adr_id']}:{item['bytes']}"
            for item in source_costs
        ) or "none"
        raise EpctlError(
            "DECISION_CONTEXT_BUDGET_EXCEEDED: "
            f"capsule is {capsule_bytes} bytes; budget is {budget_bytes}; "
            f"source_bytes={cost_text}; narrow ADRs or stable constraints, "
            "partition the task, migrate whole-document legacy ADRs, or raise "
            "the reviewed budget with --budget-reason"
        )
    return {
        "schema_version": DECISION_CAPSULE_SCHEMA_VERSION,
        "non_normative": True,
        "direct_adrs": direct_adrs,
        "resolved_adrs": resolved_adrs,
        "requested_constraints": requested_constraints,
        "selected_constraints": selected_constraints,
        "sources": [
            {
                "adr_id": str(source["id"]),
                "path": str(source["path"]),
                "contract": str(source["contract"]),
                "document_sha256": str(source["document_sha256"]),
                "payload_sha256": str(source.get("payload_sha256", "")),
            }
            for source in sources
            if isinstance(source, dict)
        ],
        "source_costs": source_costs,
        "budget_bytes": budget_bytes,
        "budget_reason": inline_text(budget_reason),
        "bytes": capsule_bytes,
        "sha256": capsule_sha256,
        "context": capsule,
    }


def normalized_repository_error(repo: Path, exc: Exception) -> str:
    return str(exc).replace(str(repo) + os.sep, "")


def decision_view_projection(
    repo: Path,
    view: dict[str, object],
) -> tuple[str, dict[str, object]]:
    view_id = str(view["id"])
    title = str(view["title"])
    direct_adrs = [str(item) for item in view["adr_refs"]]
    try:
        context = resolve_decision_context(repo, direct_adrs)
        capsule = compile_decision_capsule(context, budget_bytes=None)
        status = "current"
        error = ""
    except (EpctlError, OSError, UnicodeDecodeError) as exc:
        context = {
            "direct_adrs": direct_adrs,
            "resolved_adrs": [],
            "sources": [],
            "constraint_refs": [],
            "amendment_targets": {},
        }
        capsule = {"bytes": 0}
        status = "review_required"
        error = normalized_repository_error(repo, exc)
    resolved_adrs = [str(item) for item in context["resolved_adrs"]]
    constraint_refs = [str(item) for item in context["constraint_refs"]]
    amendment_targets = context["amendment_targets"]
    assert isinstance(amendment_targets, dict)
    lines = [
        f"# {title}\n\n",
        "Generated by `epctl` from repository ADR sources. Do not edit this "
        "projection directly. It is non-normative; source ADRs and explicit "
        "lifecycle authority remain normative.\n\n",
        f"- View: `{view_id}`\n",
        f"- Status: `{status}`\n",
        "- Direct ADRs: "
        + (", ".join(f"`{item}`" for item in direct_adrs) or "none")
        + "\n",
        "- Resolved current ADRs: "
        + (", ".join(f"`{item}`" for item in resolved_adrs) or "none")
        + "\n",
        f"- Structured constraints: {len(constraint_refs)}\n",
        f"- Full exact capsule bytes: {capsule['bytes']}\n",
    ]
    if error:
        lines.extend(
            [
                "\n## Review required\n\n",
                f"`{md_cell(error)}`\n",
            ]
        )
    else:
        lines.extend(
            [
                "\n## Current source manifest\n\n",
                "| ADR | Title | Effect | Contract | Constraints | Document SHA-256 | Source |\n",
                "|---|---|---|---|---|---|---|\n",
            ]
        )
        sources = context["sources"]
        assert isinstance(sources, list)
        for source in sources:
            assert isinstance(source, dict)
            source_rows = source.get("constraint_rows", [])
            path = str(source["path"])
            relative_link = os.path.relpath(
                repo / path,
                decision_view_path(repo, view_id).parent,
            )
            lines.append(
                f"| {source['id']} | {md_cell(str(source['title']))} | "
                f"{source['effect']} | {source['contract']} | "
                f"{len(source_rows) if isinstance(source_rows, list) else 0} | "
                f"`{source['document_sha256']}` | [ADR]({relative_link}) |\n"
            )
        lines.extend(["\n## Exact Decision Statements\n\n"])
        for source in sources:
            assert isinstance(source, dict)
            if source["contract"] == "whole-document":
                lines.append(
                    f"### {source['id']}: {source['title']}\n\n"
                    "Whole-document context is required because this ADR has no "
                    "strict machine-verifiable Decision Statement/constraint "
                    "boundary. Use `decision-capsule` to load its exact bytes.\n\n"
                )
                continue
            lines.append(
                f"### {source['id']}: {source['title']}\n\n"
                f"<!-- Exact source: {source['path']} -->\n"
                + str(source["decision_source"])
                + ("" if str(source["decision_source"]).endswith("\n") else "\n")
            )
        lines.extend(
            [
                "\n## Structured constraint catalog\n\n",
                "| Constraint | Current amendment ADRs |\n",
                "|---|---|\n",
            ]
        )
        for reference in constraint_refs:
            amenders = amendment_targets.get(reference, [])
            lines.append(
                f"| {reference} | "
                + (", ".join(str(item) for item in amenders) or "—")
                + " |\n"
            )
    document = "".join(lines)
    details = {
        "id": view_id,
        "title": title,
        "status": status,
        "error": error,
        "direct_adrs": direct_adrs,
        "resolved_adrs": resolved_adrs,
        "constraints": len(constraint_refs),
        "capsule_bytes": int(capsule["bytes"]),
        "path": decision_view_path(repo, view_id).relative_to(repo).as_posix(),
    }
    return document, details


def render_decision_view_index(
    text: str,
    projections: Iterable[dict[str, object]],
) -> str:
    start = "<!-- ADRCTX:VIEWS:START -->"
    end = "<!-- ADRCTX:VIEWS:END -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise EpctlError("Malformed Decision View index markers")
    start_index = text.index(start) + len(start)
    end_index = text.index(end)
    rows = [
        "| View | Title | Status | Direct ADRs | Resolved ADRs | Constraints | Capsule bytes | Path |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in sorted(projections, key=lambda value: str(value["id"])):
        relative = Path(str(item["path"])).relative_to("docs").as_posix()
        rows.append(
            f"| {item['id']} | {md_cell(str(item['title']))} | "
            f"{item['status']} | {len(item['direct_adrs'])} | "
            f"{len(item['resolved_adrs'])} | {item['constraints']} | "
            f"{item['capsule_bytes']} | [view]({relative}) |"
        )
    body = "\n" + "\n".join(rows) + "\n"
    return text[:start_index] + body + text[end_index:]


def rebuild_decision_views(
    repo: Path,
    registry: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    require_decision_view_infrastructure(repo)
    selected = registry if registry is not None else load_decision_view_registry(repo)
    views = selected.get("views")
    if not isinstance(views, list):
        raise EpctlError("Decision View registry views must be an array")
    projections: list[dict[str, object]] = []
    for view in views:
        assert isinstance(view, dict)
        document, details = decision_view_projection(repo, view)
        path = decision_view_path(repo, str(view["id"]))
        reject_symlink_path(repo, path)
        atomic_write(path, document)
        projections.append(details)
    index = decision_view_index_path(repo)
    reject_symlink_path(repo, index)
    if not index.is_file():
        raise EpctlError(f"Decision View index is missing; run init: {index}")
    atomic_write(
        index,
        render_decision_view_index(index.read_text(encoding="utf-8"), projections),
    )
    return projections


def decision_view_file_snapshots(
    repo: Path,
    view_ids: Iterable[str],
) -> dict[Path, str | None]:
    paths = {
        decision_view_registry_path(repo),
        decision_view_index_path(repo),
        *(decision_view_path(repo, view_id) for view_id in view_ids),
    }
    for path in paths:
        reject_symlink_path(repo, path)
    return {
        path: path.read_text(encoding="utf-8") if path.is_file() else None
        for path in paths
    }


def restore_file_snapshots(snapshots: dict[Path, str | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            if path.exists() and path.is_file() and not path.is_symlink():
                path.unlink()
        else:
            atomic_write(path, content)


def decision_view_changes(
    repo: Path,
    registry: dict[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    projections: list[dict[str, object]] = []
    changes: list[str] = []
    views = registry["views"]
    assert isinstance(views, list)
    for view in views:
        assert isinstance(view, dict)
        document, details = decision_view_projection(repo, view)
        path = decision_view_path(repo, str(view["id"]))
        reject_symlink_path(repo, path)
        existing = path.read_text(encoding="utf-8") if path.is_file() else None
        if existing != document:
            changes.append(path.relative_to(repo).as_posix())
        projections.append(details)
    index = decision_view_index_path(repo)
    reject_symlink_path(repo, index)
    if index.is_file():
        expected_index = render_decision_view_index(
            index.read_text(encoding="utf-8"),
            projections,
        )
        if index.read_text(encoding="utf-8") != expected_index:
            changes.append(index.relative_to(repo).as_posix())
    else:
        changes.append(index.relative_to(repo).as_posix())
    rendered_registry = (
        json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    registry_path = decision_view_registry_path(repo)
    existing_registry = (
        registry_path.read_text(encoding="utf-8")
        if registry_path.is_file()
        else None
    )
    if existing_registry != rendered_registry:
        changes.append(registry_path.relative_to(repo).as_posix())
    return projections, sorted(set(changes))


def set_decision_view(
    repo: Path,
    view_id: str,
    title: str,
    adr_values: Iterable[str],
    apply: bool,
) -> dict[str, object]:
    validate_slug(view_id)
    normalized_title = inline_text(title)
    if not normalized_title:
        raise EpctlError("Decision View title must be non-empty")
    raw_adrs = list(adr_values)
    direct_adrs = normalize_reference_ids(raw_adrs, "ADR")
    if not direct_adrs:
        raise EpctlError("set-decision-view requires at least one --adr")
    if len(direct_adrs) != len(raw_adrs):
        raise EpctlError("set-decision-view contains duplicate --adr values")
    direct_adrs.sort()
    context = resolve_decision_context(repo, direct_adrs)
    registry = load_decision_view_registry(repo)
    views = registry["views"]
    assert isinstance(views, list)
    record = {"id": view_id, "title": normalized_title, "adr_refs": direct_adrs}
    candidate_views = [
        item
        for item in views
        if isinstance(item, dict) and item.get("id") != view_id
    ]
    candidate_views.append(record)
    candidate_views.sort(key=lambda item: str(item["id"]))
    candidate = {
        "version": DECISION_VIEW_SCHEMA_VERSION,
        "views": candidate_views,
    }
    projections, changes = decision_view_changes(repo, candidate)
    payload = {
        "operation": "set-decision-view",
        "mode": "apply" if apply else "preview",
        "applied": False,
        "view": record,
        "registry_before": registry,
        "registry_after": candidate,
        "resolved_adrs": context["resolved_adrs"],
        "constraint_refs": context["constraint_refs"],
        "changes": changes,
        "projections": projections,
    }
    if not apply:
        return payload
    require_decision_view_infrastructure(repo)
    with repo_lock(repo):
        require_decision_view_infrastructure(repo)
        locked_context = resolve_decision_context(repo, direct_adrs)
        locked_registry = load_decision_view_registry(repo)
        if locked_registry != registry:
            raise EpctlError(
                "Decision View preflight changed while acquiring the lock; "
                "rerun the preview"
            )
        locked_views = locked_registry["views"]
        assert isinstance(locked_views, list)
        locked_candidate_views = [
            item
            for item in locked_views
            if isinstance(item, dict) and item.get("id") != view_id
        ]
        locked_candidate_views.append(record)
        locked_candidate_views.sort(key=lambda item: str(item["id"]))
        locked_candidate = {
            "version": DECISION_VIEW_SCHEMA_VERSION,
            "views": locked_candidate_views,
        }
        view_ids = [str(item["id"]) for item in locked_candidate_views]
        snapshots = decision_view_file_snapshots(repo, view_ids)
        try:
            save_decision_view_registry(repo, locked_candidate)
            locked_projections = rebuild_decision_views(repo, locked_candidate)
            view_errors, _ = validate_decision_views(repo)
            if view_errors:
                raise EpctlError(
                    "Decision View apply validation failed:\n- "
                    + "\n- ".join(view_errors)
                )
        except Exception:
            restore_file_snapshots(snapshots)
            raise
    payload["applied"] = True
    payload["resolved_adrs"] = locked_context["resolved_adrs"]
    payload["constraint_refs"] = locked_context["constraint_refs"]
    payload["registry_before"] = locked_registry
    payload["registry_after"] = locked_candidate
    payload["projections"] = locked_projections
    return payload


def remove_decision_view(
    repo: Path,
    view_id: str,
    apply: bool,
) -> dict[str, object]:
    validate_slug(view_id)
    registry = load_decision_view_registry(repo)
    views = registry["views"]
    assert isinstance(views, list)
    if not any(
        isinstance(item, dict) and item.get("id") == view_id for item in views
    ):
        raise EpctlError(f"Decision View does not exist: {view_id}")
    candidate_views = [
        item
        for item in views
        if isinstance(item, dict) and item.get("id") != view_id
    ]
    candidate = {
        "version": DECISION_VIEW_SCHEMA_VERSION,
        "views": candidate_views,
    }
    _, changes = decision_view_changes(repo, candidate)
    target = decision_view_path(repo, view_id)
    reject_symlink_path(repo, target)
    if target.is_file():
        changes.append(target.relative_to(repo).as_posix())
    payload = {
        "operation": "remove-decision-view",
        "mode": "apply" if apply else "preview",
        "applied": False,
        "view_id": view_id,
        "registry_before": registry,
        "registry_after": candidate,
        "changes": sorted(set(changes)),
    }
    if not apply:
        return payload
    require_decision_view_infrastructure(repo)
    with repo_lock(repo):
        require_decision_view_infrastructure(repo)
        locked = load_decision_view_registry(repo)
        if locked != registry:
            raise EpctlError(
                "Decision View preflight changed while acquiring the lock; "
                "rerun the preview"
            )
        locked_views = locked["views"]
        assert isinstance(locked_views, list)
        if not any(
            isinstance(item, dict) and item.get("id") == view_id
            for item in locked_views
        ):
            raise EpctlError(f"Decision View does not exist: {view_id}")
        locked_candidate_views = [
            item
            for item in locked_views
            if isinstance(item, dict) and item.get("id") != view_id
        ]
        locked_candidate = {
            "version": DECISION_VIEW_SCHEMA_VERSION,
            "views": locked_candidate_views,
        }
        view_ids = [
            view_id,
            *(str(item["id"]) for item in locked_candidate_views),
        ]
        snapshots = decision_view_file_snapshots(repo, view_ids)
        try:
            save_decision_view_registry(repo, locked_candidate)
            rebuild_decision_views(repo, locked_candidate)
            reject_symlink_path(repo, target)
            if target.exists():
                if not target.is_file():
                    raise EpctlError(
                        f"Decision View projection is not a regular file: {target}"
                    )
                target.unlink()
            view_errors, _ = validate_decision_views(repo)
            if view_errors:
                raise EpctlError(
                    "Decision View removal validation failed:\n- "
                    + "\n- ".join(view_errors)
                )
        except Exception:
            restore_file_snapshots(snapshots)
            raise
    payload["applied"] = True
    payload["registry_before"] = locked
    payload["registry_after"] = locked_candidate
    return payload


def validate_decision_views(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    registry_path = decision_view_registry_path(repo)
    index_path = decision_view_index_path(repo)
    view_root = repo / DECISION_VIEW_ROOT

    for path, label in (
        (registry_path, "Decision View registry"),
        (index_path, "Decision View index"),
    ):
        if path.is_symlink():
            errors.append(f"{path}: symbolic links are not supported")
        elif not path.is_file():
            errors.append(f"{path}: missing {label}; run init")
    if view_root.is_symlink():
        errors.append(f"{view_root}: symbolic links are not supported")
    elif not view_root.is_dir():
        errors.append(f"{view_root}: missing Decision View directory; run init")

    if errors:
        return errors, warnings
    try:
        registry = load_decision_view_registry(repo)
    except EpctlError as exc:
        errors.append(str(exc))
        return errors, warnings

    views = registry["views"]
    assert isinstance(views, list)
    projections: list[dict[str, object]] = []
    expected_paths: set[Path] = set()
    for view in views:
        assert isinstance(view, dict)
        path = decision_view_path(repo, str(view["id"]))
        expected_paths.add(path)
        if path.is_symlink():
            errors.append(f"{path}: symbolic links are not supported")
            continue
        expected, details = decision_view_projection(repo, view)
        projections.append(details)
        if details["status"] == "review_required":
            warnings.append(
                f"{path}: Decision View requires owner review: "
                f"{details['error']}"
            )
        if not path.is_file():
            errors.append(f"{path}: missing generated Decision View; run reindex")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"{path}: generated Decision View drift; run reindex")

    if view_root.is_dir() and not view_root.is_symlink():
        for path in sorted(view_root.glob("*.md")):
            if path.is_symlink():
                errors.append(f"{path}: symbolic links are not supported")
            elif path not in expected_paths:
                errors.append(
                    f"{path}: unregistered Decision View projection; "
                    "remove it or register the view"
                )

    if index_path.is_file() and not index_path.is_symlink():
        try:
            current_index = index_path.read_text(encoding="utf-8")
            expected_index = render_decision_view_index(
                current_index,
                projections,
            )
        except (EpctlError, OSError, UnicodeDecodeError) as exc:
            errors.append(f"{index_path}: {exc}")
        else:
            if current_index != expected_index:
                errors.append(
                    f"{index_path}: Decision View index drift; run reindex"
                )
    return errors, warnings


def decision_selection_context(
    repo: Path,
    view_id: str,
    adr_values: Iterable[str],
) -> tuple[dict[str, object], dict[str, object]]:
    raw_adrs = list(adr_values)
    if bool(view_id) == bool(raw_adrs):
        raise EpctlError("Select exactly one --view or one or more --adr values")
    if view_id:
        view = find_decision_view(repo, view_id)
        seeds = view["adr_refs"]
        assert isinstance(seeds, list)
        selection = {
            "kind": "view",
            "view_id": str(view["id"]),
            "title": str(view["title"]),
        }
        return resolve_decision_context(repo, seeds), selection
    return resolve_decision_context(repo, raw_adrs), {
        "kind": "explicit_adrs",
        "view_id": "",
        "title": "",
    }


def adr_graph_metrics(
    current_ids: set[str],
    data_by_id: dict[str, dict[str, str]],
) -> dict[str, object]:
    all_edges: set[tuple[str, str, str]] = set()
    current_edges: set[tuple[str, str, str]] = set()
    adjacency = {adr_id: set() for adr_id in current_ids}
    for adr_id, data in data_by_id.items():
        for field in ("depends_on", "amends", "supersedes"):
            for target in parse_inline_ids(data.get(field, ""), "ADR"):
                edge = (adr_id, field, target)
                all_edges.add(edge)
                if adr_id in current_ids and target in current_ids:
                    current_edges.add(edge)
                    adjacency[adr_id].add(target)
                    adjacency[target].add(adr_id)
    components: list[list[str]] = []
    remaining = set(current_ids)
    while remaining:
        root = min(remaining)
        stack = [root]
        component: set[str] = set()
        while stack:
            item = stack.pop()
            if item in component:
                continue
            component.add(item)
            stack.extend(sorted(adjacency.get(item, set()) - component))
        remaining -= component
        components.append(sorted(component))
    components.sort(key=lambda value: (-len(value), value))
    return {
        "typed_edges": len(all_edges),
        "effective_typed_edges": len(current_edges),
        "connected_components": len(components),
        "largest_component": len(components[0]) if components else 0,
        "component_sizes": [len(component) for component in components],
    }


def health_signal(
    dimension: str,
    value: int,
    threshold: int,
    explanation: str,
) -> dict[str, object]:
    return {
        "dimension": dimension,
        "value": value,
        "review_threshold": threshold,
        "state": "review_recommended" if value > threshold else "within_target",
        "explanation": explanation,
    }


def adr_health(repo: Path) -> dict[str, object]:
    rows = status_rows(repo)
    adrs = rows["adrs"]
    plans = rows["plans"]
    data_by_id = adr_corpus_data(repo)
    current_ids = {
        str(item["id"])
        for item in adrs
        if bool(item.get("current"))
    }
    total_lines = 0
    total_bytes = 0
    structured_total = 0
    whole_document_total = 0
    structured_constraints_total = 0
    structured_current = 0
    legacy_current = 0
    current_constraints = 0
    for item in adrs:
        path = repo / str(item["path"])
        text = path.read_text(encoding="utf-8")
        total_lines += len(text.splitlines())
        total_bytes += len(text.encode("utf-8"))
        data = data_by_id.get(str(item["id"]), {})
        structured = data.get("schema_version") in {"1.2", "1.3", "1.4"}
        constraints = item.get("constraints", [])
        if structured:
            structured_total += 1
            if isinstance(constraints, list):
                structured_constraints_total += len(constraints)
        else:
            whole_document_total += 1
        if not bool(item.get("current")):
            continue
        if structured:
            structured_current += 1
            if isinstance(constraints, list):
                current_constraints += len(constraints)
        else:
            legacy_current += 1

    graph = adr_graph_metrics(current_ids, data_by_id)
    partially_amended = [
        str(item["id"])
        for item in adrs
        if bool(item.get("current")) and bool(item.get("amended_by"))
    ]
    current_amenders = [
        str(item["id"])
        for item in adrs
        if bool(item.get("current")) and bool(item.get("amends"))
    ]
    amended_constraint_refs: set[str] = set()
    for adr_id in current_amenders:
        amended_constraint_refs.update(
            parse_adr_constraint_array(
                data_by_id[adr_id].get("amends_constraints", "[]"),
                "amends_constraints",
            )
        )

    active_plan_rows: list[dict[str, object]] = []
    for plan in plans:
        if str(plan.get("status")) not in PLAN_ACTIVE_STATUSES:
            continue
        adr_refs = [str(value) for value in plan.get("adr_refs", [])]
        constraint_refs = [
            str(value) for value in plan.get("adr_constraint_refs", [])
        ]
        active_plan_rows.append(
            {
                "id": str(plan["id"]),
                "adr_refs": len(adr_refs),
                "constraint_refs": len(constraint_refs),
                "architecture_review_required": bool(
                    plan.get("architecture_review_required")
                ),
            }
        )
    active_plan_rows.sort(key=lambda value: str(value["id"]))
    max_plan_adrs = max(
        (int(item["adr_refs"]) for item in active_plan_rows),
        default=0,
    )
    max_plan_constraints = max(
        (int(item["constraint_refs"]) for item in active_plan_rows),
        default=0,
    )

    registry = load_decision_view_registry(repo)
    views = registry["views"]
    assert isinstance(views, list)
    view_rows: list[dict[str, object]] = []
    covered_current: set[str] = set()
    for view in views:
        assert isinstance(view, dict)
        _, details = decision_view_projection(repo, view)
        resolved = {str(value) for value in details["resolved_adrs"]}
        if details["status"] == "current":
            covered_current.update(resolved & current_ids)
        view_rows.append(
            {
                "id": str(details["id"]),
                "status": str(details["status"]),
                "direct_adrs": len(details["direct_adrs"]),
                "resolved_adrs": len(details["resolved_adrs"]),
                "constraints": int(details["constraints"]),
                "estimated_full_capsule_bytes": int(details["capsule_bytes"]),
            }
        )
    max_view_bytes = max(
        (int(item["estimated_full_capsule_bytes"]) for item in view_rows),
        default=0,
    )
    uncovered = sorted(current_ids - covered_current)
    signals = [
        health_signal(
            "effective_adrs",
            len(current_ids),
            ADR_HEALTH_EFFECTIVE_TARGET,
            "Review view taxonomy when the current ADR set exceeds the "
            f"navigation target of {ADR_HEALTH_EFFECTIVE_TARGET}.",
        ),
        health_signal(
            "largest_component",
            int(graph["largest_component"]),
            ADR_HEALTH_COMPONENT_TARGET,
            "A large weakly connected current graph usually needs narrower "
            f"task capsules; target is {ADR_HEALTH_COMPONENT_TARGET} ADRs.",
        ),
        health_signal(
            "max_active_plan_adr_refs",
            max_plan_adrs,
            ADR_HEALTH_ACTIVE_PLAN_TARGET,
            "An active plan above this ADR input target should be partitioned "
            "or use stable constraint selection.",
        ),
        health_signal(
            "max_active_plan_constraint_refs",
            max_plan_constraints,
            ADR_HEALTH_ACTIVE_PLAN_CONSTRAINT_TARGET,
            "A plan above this structured-constraint input target should use "
            "task-specific selection or narrower implementation milestones.",
        ),
        health_signal(
            "partially_amended_adrs",
            len(partially_amended),
            ADR_HEALTH_PARTIAL_AMENDMENT_TARGET,
            "A high partially-amended count warrants owner review for possible "
            "new atomic consolidation ADRs; it never triggers automatic merge.",
        ),
        health_signal(
            "legacy_current_adrs",
            legacy_current,
            0,
            "Each current legacy ADR requires whole-document capsule context.",
        ),
        health_signal(
            "uncovered_current_adrs",
            len(uncovered),
            0,
            "Current ADRs outside every healthy view remain discoverable but "
            "lack persistent domain navigation.",
        ),
        health_signal(
            "max_view_capsule_bytes",
            max_view_bytes,
            DECISION_CAPSULE_DEFAULT_BUDGET_BYTES,
            "A complete view above the default capsule budget requires a "
            "narrower task selection or a reviewed budget reason.",
        ),
    ]
    return {
        "schema_version": ADR_HEALTH_SCHEMA_VERSION,
        "non_normative": True,
        "corpus": {
            "total_adrs": len(adrs),
            "total_lines": total_lines,
            "total_bytes": total_bytes,
            "effective_adrs": len(current_ids),
            "historical_or_review_adrs": len(adrs) - len(current_ids),
        },
        "contracts": {
            "structured_adrs": structured_total,
            "whole_document_adrs": whole_document_total,
            "structured_current_adrs": structured_current,
            "whole_document_current_adrs": legacy_current,
        },
        "graph": graph,
        "constraints": {
            "structured_constraints": structured_constraints_total,
            "structured_current_constraints": current_constraints,
        },
        "amendments": {
            "current_amending_adrs": len(current_amenders),
            "partially_amended_adrs": len(partially_amended),
            "amended_constraint_refs": len(amended_constraint_refs),
            "partially_amended_ids": partially_amended,
        },
        "active_plans": {
            "count": len(active_plan_rows),
            "max_adr_refs": max_plan_adrs,
            "max_constraint_refs": max_plan_constraints,
            "plans": active_plan_rows,
        },
        "views": {
            "count": len(view_rows),
            "current_count": sum(
                item["status"] == "current" for item in view_rows
            ),
            "covered_current_adrs": len(covered_current),
            "uncovered_current_adrs": uncovered,
            "coverage_ratio": (
                round(len(covered_current) / len(current_ids), 4)
                if current_ids
                else 1.0
            ),
            "max_estimated_full_capsule_bytes": max_view_bytes,
            "items": view_rows,
        },
        "signals": signals,
    }


def print_adr_health(payload: dict[str, object]) -> None:
    print("ADR health is a non-normative, read-only projection; no aggregate score is used.")
    print()
    corpus = payload["corpus"]
    contracts = payload["contracts"]
    graph = payload["graph"]
    constraints = payload["constraints"]
    amendments = payload["amendments"]
    active_plans = payload["active_plans"]
    views = payload["views"]
    for item in (
        corpus,
        contracts,
        graph,
        constraints,
        amendments,
        active_plans,
        views,
    ):
        assert isinstance(item, dict)
    metrics = (
        ("corpus", "total_adrs", corpus["total_adrs"]),
        ("corpus", "effective_adrs", corpus["effective_adrs"]),
        ("corpus", "total_lines", corpus["total_lines"]),
        ("corpus", "total_bytes", corpus["total_bytes"]),
        ("contracts", "structured_current_adrs", contracts["structured_current_adrs"]),
        ("contracts", "whole_document_current_adrs", contracts["whole_document_current_adrs"]),
        ("graph", "typed_edges", graph["typed_edges"]),
        ("graph", "connected_components", graph["connected_components"]),
        ("graph", "largest_component", graph["largest_component"]),
        ("constraints", "structured_current_constraints", constraints["structured_current_constraints"]),
        ("amendments", "current_amending_adrs", amendments["current_amending_adrs"]),
        ("amendments", "partially_amended_adrs", amendments["partially_amended_adrs"]),
        ("active_plans", "count", active_plans["count"]),
        ("active_plans", "max_adr_refs", active_plans["max_adr_refs"]),
        ("active_plans", "max_constraint_refs", active_plans["max_constraint_refs"]),
        ("views", "count", views["count"]),
        ("views", "covered_current_adrs", views["covered_current_adrs"]),
        ("views", "coverage_ratio", views["coverage_ratio"]),
        ("views", "max_estimated_full_capsule_bytes", views["max_estimated_full_capsule_bytes"]),
    )
    print("| Dimension | Metric | Value |")
    print("|---|---|---:|")
    for dimension, metric, value in metrics:
        print(f"| {dimension} | {metric} | {value} |")
    print()
    print("| Dimension | Value | Review threshold | State | Explanation |")
    print("|---|---:|---:|---|---|")
    signals = payload["signals"]
    assert isinstance(signals, list)
    for item in signals:
        assert isinstance(item, dict)
        print(
            f"| {item['dimension']} | {item['value']} | "
            f"{item['review_threshold']} | {item['state']} | "
            f"{md_cell(str(item['explanation']))} |"
        )


def amendment_chain_paths(
    edges: Iterable[dict[str, str]],
) -> list[list[str]]:
    targets_by_amender: dict[str, list[str]] = {}
    all_targets: set[str] = set()
    for edge in edges:
        amender = edge["amender"]
        target = edge["target"]
        targets_by_amender.setdefault(amender, []).append(target)
        all_targets.add(target)
    for targets in targets_by_amender.values():
        targets.sort()
    roots = sorted(set(targets_by_amender) - all_targets)
    if not roots:
        roots = sorted(targets_by_amender)
    chains: list[list[str]] = []

    def walk(item: str, path: list[str]) -> None:
        targets = targets_by_amender.get(item, [])
        if not targets:
            if len(path) > 1:
                chains.append(path)
            return
        for target in targets:
            if target in path:
                continue
            walk(target, [*path, target])

    for root in roots:
        walk(root, [root])
    return sorted(chains)


def adr_consolidation_plan(
    repo: Path,
    view_id: str,
    adr_values: Iterable[str],
) -> dict[str, object]:
    context, selection = decision_selection_context(repo, view_id, adr_values)
    resolved = {str(value) for value in context["resolved_adrs"]}
    source_by_id = decision_context_source_by_id(context)
    amendment_edges: list[dict[str, str]] = []
    for adr_id in sorted(resolved):
        source = source_by_id[adr_id]
        data = source["data"]
        assert isinstance(data, dict)
        for target in parse_inline_ids(str(data.get("amends", "")), "ADR"):
            if target in resolved:
                amendment_edges.append({"amender": adr_id, "target": target})

    rows = status_rows(repo)
    active_plan_impact: list[dict[str, object]] = []
    for plan in rows["plans"]:
        if str(plan.get("status")) not in PLAN_ACTIVE_STATUSES:
            continue
        intersection = sorted(
            resolved & {str(value) for value in plan.get("adr_refs", [])}
        )
        if intersection:
            active_plan_impact.append(
                {"id": str(plan["id"]), "adr_refs": intersection}
            )

    selected_constraints = {
        str(value) for value in context.get("constraint_refs", [])
    }
    proposed_overlap: list[dict[str, object]] = []
    data_by_id = adr_corpus_data(repo)
    for adr_id, data in sorted(data_by_id.items()):
        if data.get("status") != "proposed":
            continue
        relation_overlap = sorted(
            resolved
            & set(parse_inline_ids(data.get("depends_on", ""), "ADR"))
            | resolved
            & set(parse_inline_ids(data.get("amends", ""), "ADR"))
        )
        constraint_overlap = sorted(
            selected_constraints
            & set(
                parse_adr_constraint_array(
                    data.get("amends_constraints", "[]"),
                    "amends_constraints",
                )
            )
        )
        if relation_overlap or constraint_overlap:
            proposed_overlap.append(
                {
                    "id": adr_id,
                    "related_adrs": relation_overlap,
                    "constraint_refs": constraint_overlap,
                }
            )

    legacy = sorted(
        adr_id
        for adr_id, source in source_by_id.items()
        if source.get("contract") == "whole-document"
    )
    partial = sorted(
        adr_id
        for adr_id, source in source_by_id.items()
        if bool(source.get("amended_by"))
    )
    recommendation = (
        "defer_while_active_or_proposed_work_depends_on_context"
        if active_plan_impact or proposed_overlap
        else "decision_owner_review_required"
    )
    source_digests = [
        {
            "adr_id": adr_id,
            "document_sha256": str(source_by_id[adr_id]["document_sha256"]),
            "payload_sha256": str(source_by_id[adr_id].get("payload_sha256", "")),
        }
        for adr_id in sorted(resolved)
    ]
    return {
        "schema_version": ADR_CONSOLIDATION_SCHEMA_VERSION,
        "non_normative": True,
        "preview_only": True,
        "selection": selection,
        "direct_adrs": context["direct_adrs"],
        "resolved_adrs": sorted(resolved),
        "amendment_edges": amendment_edges,
        "amendment_chains": amendment_chain_paths(amendment_edges),
        "partially_amended_adrs": partial,
        "whole_document_legacy_adrs": legacy,
        "active_plan_impact": active_plan_impact,
        "proposed_overlap": proposed_overlap,
        "source_digests": source_digests,
        "recommendation": recommendation,
        "required_next_step": (
            "If semantic consolidation remains desirable, author one new atomic "
            "proposed ADR, obtain explicit Decision Owner acceptance, implement "
            "migration, then use authorized effect transitions."
        ),
        "forbidden_mutations": [
            "merge",
            "accept",
            "retire",
            "supersede",
            "rewrite",
            "delete",
        ],
    }


def print_adr_consolidation_plan(payload: dict[str, object]) -> None:
    print("ADR consolidation analysis is non-normative and preview-only.")
    print(f"Recommendation: {payload['recommendation']}")
    print(f"Resolved ADRs: {', '.join(payload['resolved_adrs'])}")
    print()
    print("| Impact | Count | Items |")
    print("|---|---:|---|")
    for key in (
        "amendment_edges",
        "amendment_chains",
        "partially_amended_adrs",
        "whole_document_legacy_adrs",
        "active_plan_impact",
        "proposed_overlap",
    ):
        value = payload[key]
        assert isinstance(value, list)
        print(f"| {key} | {len(value)} | {md_cell(json.dumps(value, ensure_ascii=False))} |")
    print()
    print(str(payload["required_next_step"]))


def task_files(plan_path: Path) -> list[Path]:
    return sorted((plan_path.parent / "tasks").glob("*.md"))


def checkpoint_files(plan_path: Path) -> list[Path]:
    return sorted(
        (plan_path.parent / "history").glob("cp-*.md"),
        key=lambda path: path_id_number(path, "CP") or 0,
    )


def frontmatter_body(text: str) -> str:
    _, _, end = parse_frontmatter(text)
    return text[end + 5 :]


def payload_sha256(text: str) -> str:
    return hashlib.sha256(frontmatter_body(text).encode("utf-8")).hexdigest()


def adr_payload_sha256(text: str, data: dict[str, str]) -> str:
    if data.get("schema_version") not in {"1.1", "1.2", "1.3", "1.4"}:
        return payload_sha256(text)
    decision_payload = {
        "schema_version": data.get("schema_version", ""),
        "id": data.get("id", ""),
        "title": data.get("title", ""),
        "research_refs": data.get("research_refs", ""),
        "depends_on": data.get("depends_on", ""),
        "amends": data.get("amends", ""),
        "design_refs": data.get("design_refs", ""),
        "decision_maker": data.get("decision_maker", ""),
        "decided": data.get("decided", ""),
        "decision_outcome": adr_decision_outcome(data),
        "body": frontmatter_body(text),
    }
    if data.get("schema_version") in {"1.2", "1.3", "1.4"}:
        decision_payload["amends_constraints"] = data.get(
            "amends_constraints",
            "",
        )
    if data.get("schema_version") in {"1.3", "1.4"}:
        decision_payload["metadata_schema"] = data.get("metadata_schema", "")
        decision_payload["artifact_type"] = data.get("artifact_type", "")
        decision_payload["author"] = data.get("author", "")
        decision_payload["owner"] = data.get("owner", "")
        decision_payload["created"] = data.get("created", "")
    if data.get("schema_version") == "1.3":
        decision_payload["updated"] = data.get("updated", "")
    canonical = json.dumps(
        decision_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def canonical_document_sha256(text: str, digest_field: str) -> str:
    candidate, count = re.subn(
        rf"(?m)^{re.escape(digest_field)}:.*$",
        f"{digest_field}:",
        text,
        count=1,
    )
    if count != 1:
        raise EpctlError(f"Missing digest field {digest_field}")
    return hashlib.sha256(candidate.encode("utf-8")).hexdigest()


def research_manifest_sha256(data: dict[str, object]) -> str:
    payload = json.loads(json.dumps(data))
    payload["payload_sha256"] = ""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def research_manifest_locator_path(
    repo: Path,
    package: Path,
    locator: dict[str, object],
) -> Path:
    base = locator.get("base")
    raw_path = locator.get("path")
    if base not in {"repo", "package"} or not isinstance(raw_path, str):
        raise EpctlError(f"invalid Research manifest locator: {locator!r}")
    relative = Path(raw_path)
    if relative.is_absolute() or any(
        component in {"", ".", ".."} for component in relative.parts
    ):
        raise EpctlError(f"unsafe Research manifest path: {raw_path!r}")
    root = repo if base == "repo" else package
    candidate = root / relative
    reject_symlink_path(repo, candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise EpctlError(
            f"Research manifest document does not exist: {candidate}"
        ) from exc
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise EpctlError(
            f"Research manifest document escapes repository: {candidate}"
        ) from exc
    if not resolved.is_file():
        raise EpctlError(f"Research manifest document is not a file: {candidate}")
    return resolved


def validate_research_manifest(
    repo: Path,
    path: Path,
    parent_id: str,
    require_sealed: bool,
) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path}: missing Research manifest"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: invalid Research manifest: {exc}"]
    if not isinstance(data, dict):
        return [f"{path}: Research manifest must be an object"]
    manifest_schema = data.get("schema_version")
    if manifest_schema not in {"1", "1.1"}:
        errors.append(
            f"{path}: Research manifest schema_version must be 1 or 1.1"
        )
    if data.get("research_id") != parent_id:
        errors.append(f"{path}: research_id must be {parent_id}")
    status = data.get("status")
    mode = data.get("mode")
    if status not in {"active", "sealed"}:
        errors.append(f"{path}: invalid Research manifest status {status!r}")
    if mode not in {"managed", "linked", "snapshot"}:
        errors.append(f"{path}: invalid Research manifest mode {mode!r}")
    if manifest_schema == "1.1":
        for field, expected in (
            ("metadata_schema", "1"),
            ("artifact_type", "research-manifest"),
            ("id", f"{parent_id}-MANIFEST"),
        ):
            if data.get(field) != expected:
                errors.append(f"{path}: {field} must be {expected!r}")
        for field in ("title", "author", "owner", "created", "updated"):
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{path}: metadata field {field} must be non-empty")
    if require_sealed and status != "sealed":
        errors.append(f"{path}: concluded Research requires sealed manifest")
    documents = data.get("documents")
    entrypoints = data.get("entrypoints")
    if not isinstance(documents, list):
        errors.append(f"{path}: documents must be an array")
        documents = []
    if not isinstance(entrypoints, list):
        errors.append(f"{path}: entrypoints must be an array")
        entrypoints = []
    if status == "sealed":
        expected = data.get("payload_sha256")
        actual = research_manifest_sha256(data)
        if not isinstance(expected, str) or not expected:
            errors.append(f"{path}: sealed manifest requires payload_sha256")
        elif expected != actual:
            errors.append(
                f"{path}: sealed Research manifest payload changed "
                f"(expected {expected}, got {actual})"
            )
        seen: set[tuple[str, str]] = set()
        for document in documents:
            if not isinstance(document, dict):
                errors.append(f"{path}: manifest document must be an object")
                continue
            base = document.get("base")
            raw_document_path = document.get("path")
            key = (str(base), str(raw_document_path))
            if key in seen:
                errors.append(f"{path}: duplicate manifest document {key}")
            seen.add(key)
            if require_sealed and base != "package":
                errors.append(
                    f"{path}: concluded manifest documents must be package-relative"
                )
            try:
                document_path = research_manifest_locator_path(
                    repo, path.parent, document
                )
            except EpctlError as exc:
                errors.append(f"{path}: {exc}")
                continue
            expected_hash = document.get("sha256")
            expected_bytes = document.get("bytes")
            actual_hash = hashlib.sha256(document_path.read_bytes()).hexdigest()
            actual_bytes = document_path.stat().st_size
            if expected_hash != actual_hash:
                errors.append(f"{document_path}: sealed document digest changed")
            if expected_bytes != actual_bytes:
                errors.append(f"{document_path}: sealed document size changed")
        entrypoint_keys: set[tuple[str, str]] = set()
        for entrypoint in entrypoints:
            if not isinstance(entrypoint, dict):
                errors.append(f"{path}: manifest entrypoint must be an object")
                continue
            entrypoint_keys.add(
                (str(entrypoint.get("base")), str(entrypoint.get("path")))
            )
        missing_entrypoints = entrypoint_keys - seen
        if missing_entrypoints:
            errors.append(
                f"{path}: entrypoints are absent from documents: "
                + ", ".join(
                    f"{base}:{document_path}"
                    for base, document_path in sorted(missing_entrypoints)
                )
            )
    elif data.get("payload_sha256"):
        errors.append(f"{path}: active manifest cannot have payload_sha256")
    return errors


def history_event_count(text: str) -> int:
    count = 0
    for heading in (
        "Progress",
        "Surprises & Discoveries",
        "Decision Log",
        "Revision Notes",
    ):
        body = section(text, heading) or ""
        count += sum(
            1
            for line in visible_markdown_lines(body)
            if re.match(r"^\s*-\s+", line)
            and not re.match(r"^\s*-\s+None(?:\s|\.|$)", line, re.IGNORECASE)
        )
    count += len(blocker_rows(text))
    return count


def milestone_count(text: str) -> int:
    body = section(text, "Milestones") or ""
    return sum(
        1
        for line in visible_markdown_lines(body)
        if re.match(r"^###\s+\S", line)
    )


def working_set_state(
    root_lines: int,
    root_bytes: int,
    live_history_events: int,
) -> str:
    if (
        root_lines > ROOT_LINE_WARNING
        or root_bytes > ROOT_BYTE_WARNING
        or live_history_events > HISTORY_EVENT_WARNING
    ):
        return "checkpoint_required"
    if (
        root_lines > ROOT_LINE_RECOMMENDATION
        or root_bytes > ROOT_BYTE_RECOMMENDATION
        or live_history_events > HISTORY_EVENT_RECOMMENDATION
    ):
        return "checkpoint_recommended"
    return "bounded"


def scope_state(milestones: int, unfinished_tasks: int) -> str:
    if (
        milestones > MILESTONE_SPLIT_THRESHOLD
        or unfinished_tasks > UNFINISHED_TASK_SPLIT_THRESHOLD
    ):
        return "split_recommended"
    if (
        milestones > MILESTONE_REVIEW_THRESHOLD
        or unfinished_tasks > UNFINISHED_TASK_REVIEW_THRESHOLD
    ):
        return "scope_review"
    return "bounded"


def completion_state(
    text: str,
    status: str,
    task_statuses: Iterable[str],
) -> tuple[str, list[str]]:
    if status in PLAN_COMPLETED_STATUSES:
        return "archived", []
    acceptance = checkboxes(section(text, "Validation and Acceptance") or "")
    if not acceptance or not all(acceptance):
        return "in_progress", []
    blockers: list[str] = []
    if marker_names(text):
        blockers.append("required_placeholders")
    if unresolved_blockers(text):
        blockers.append("open_blockers")
    if any(task not in {"done", "cancelled"} for task in task_statuses):
        blockers.append("unfinished_tasks")
    if blockers:
        return "archive_blocked", blockers
    return "ready_to_archive", []


def plan_lifecycle_metrics(
    text: str,
    status: str,
    task_statuses: Iterable[str],
) -> dict[str, object]:
    tasks = list(task_statuses)
    root_lines = len(text.splitlines())
    root_bytes = len(text.encode("utf-8"))
    live_history_events = history_event_count(text)
    milestones = milestone_count(text)
    unfinished_tasks = sum(
        task not in {"done", "cancelled"} for task in tasks
    )
    completion, completion_blockers = completion_state(text, status, tasks)
    archived = status in PLAN_COMPLETED_STATUSES
    return {
        "completion": completion,
        "completion_blockers": completion_blockers,
        "working_set": (
            "archived"
            if archived
            else working_set_state(root_lines, root_bytes, live_history_events)
        ),
        "scope": (
            "archived"
            if archived
            else scope_state(milestones, unfinished_tasks)
        ),
        "root_lines": root_lines,
        "root_bytes": root_bytes,
        "live_history_events": live_history_events,
        "milestones": milestones,
        "unfinished_tasks": unfinished_tasks,
    }


def new_research(
    repo: Path,
    slug: str,
    title: str,
    owner: str,
    author: str,
) -> Path:
    validate_slug(slug)
    owner_value = metadata_actor(owner)
    author_value = metadata_actor(author)
    with repo_lock(repo):
        init_repo(repo)
        item_id = next_id(repo, "R")
        number = int(item_id.split("-")[1])
        directory_name = f"r-{number:03d}_{slug}"
        directory = repo / "docs" / "research" / "active" / directory_name
        path = directory / "RESEARCH.md"
        synthesis_path = directory / "SYNTHESIS.md"
        reject_symlink_path(repo, path)
        reject_symlink_path(repo, synthesis_path)
        if directory.exists():
            raise EpctlError(f"Destination already exists: {directory}")
        research_text = render_asset(
            "research.md",
            {
                "ID": item_id,
                "TITLE": yaml_string(title),
                "OWNER": yaml_string(owner_value),
                "AUTHOR": yaml_string(author_value),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
                "DIR_NAME": directory_name,
            },
        )
        synthesis_text = render_asset(
            "synthesis.md",
            {
                "ID": f"{item_id}-SYNTHESIS",
                "PARENT_ID": item_id,
                "TITLE": yaml_string(f"{title} — Synthesis"),
                "AUTHOR": yaml_string(author_value),
                "OWNER": yaml_string(owner_value),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
            },
        )
        index_path = repo / "docs" / "RESEARCH.md"
        old_index = index_path.read_text(encoding="utf-8")
        relative = path.relative_to(repo / "docs").as_posix()
        synthesis_relative = synthesis_path.relative_to(repo / "docs").as_posix()
        row = (
            f"| {item_id} | {md_cell(title)} | active | {date_string()} | "
            f"[Synthesis]({synthesis_relative}) | [Research]({relative}) |"
        )
        new_index = upsert_index_row(
            old_index, "R", "ACTIVE", item_id, row
        )
        try:
            atomic_write(path, research_text)
            atomic_write(synthesis_path, synthesis_text)
            (directory / "notes").mkdir()
            (directory / "artifacts").mkdir()
            atomic_write(index_path, new_index)
        except Exception:
            atomic_write(index_path, old_index)
            for candidate in (synthesis_path, path):
                if candidate.exists():
                    candidate.unlink()
            for child in (directory / "artifacts", directory / "notes"):
                if child.exists() and not any(child.iterdir()):
                    child.rmdir()
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
            raise
        return path


def new_adr(
    repo: Path,
    slug: str,
    title: str,
    owner: str,
    author: str,
    research_values: Iterable[str],
    depends_on_values: Iterable[str],
    amends_values: Iterable[str],
    amends_constraint_values: Iterable[str],
    design_values: Iterable[str],
) -> Path:
    validate_slug(slug)
    owner_value = metadata_actor(owner)
    author_value = metadata_actor(author)
    research_refs = normalize_reference_ids(research_values, "R")
    depends_on = normalize_reference_ids(depends_on_values, "ADR")
    amends = normalize_reference_ids(amends_values, "ADR")
    amends_constraints = normalize_adr_constraint_refs(
        amends_constraint_values,
        "amends_constraints",
    )
    overlap = set(depends_on) & set(amends)
    if overlap:
        raise EpctlError(
            "ADR cannot both depend on and amend: " + ", ".join(sorted(overlap))
        )
    amended_constraint_parents = {
        reference.split("#", 1)[0] for reference in amends_constraints
    }
    if amended_constraint_parents != set(amends):
        missing = set(amends) - amended_constraint_parents
        extra = amended_constraint_parents - set(amends)
        details: list[str] = []
        if missing:
            details.append(
                "missing constraint references for " + ", ".join(sorted(missing))
            )
        if extra:
            details.append(
                "constraint references without --amends "
                + ", ".join(sorted(extra))
            )
        raise EpctlError("Scoped amendments are inconsistent: " + "; ".join(details))
    with repo_lock(repo):
        init_repo(repo)
        design_refs = normalize_document_refs(repo, design_values, "design_refs")
        for research_id in research_refs:
            research_path = find_research(repo, research_id, "completed")
            errors, _ = validate_research(research_path)
            data, _, _ = parse_frontmatter(
                research_path.read_text(encoding="utf-8")
            )
            if errors or data.get("status") != "concluded":
                details = "; ".join(errors) if errors else data.get("status", "")
                raise EpctlError(
                    f"{research_id} must be valid and concluded: {details}"
                )
        for related_id in (*depends_on, *amends):
            related_path = find_adr(repo, related_id)
            related_errors, _, related_data = validate_adr(related_path)
            related_current, current_reasons = adr_currentness(repo, related_id)
            if related_errors or not related_current:
                details = (
                    "; ".join(related_errors)
                    if related_errors
                    else "; ".join(current_reasons)
                )
                raise EpctlError(
                    f"{related_id} must be valid, accepted and current: {details}"
                )
        for constraint_ref in amends_constraints:
            related_id = constraint_ref.split("#", 1)[0]
            related_path = find_adr(repo, related_id)
            available = set(
                adr_constraint_refs(
                    related_path.read_text(encoding="utf-8"),
                    related_id,
                )
            )
            if constraint_ref not in available:
                raise EpctlError(
                    f"{constraint_ref} does not identify a structured constraint "
                    f"in {related_id}; supersede legacy or unstructured decisions"
                )
        item_id = next_id(repo, "ADR")
        number = int(item_id.split("-")[1])
        path = repo / "docs" / "adr" / f"adr-{number:03d}_{slug}.md"
        reject_symlink_path(repo, path)
        if path.exists():
            raise EpctlError(f"Destination already exists: {path}")
        refs_json = json.dumps(research_refs, ensure_ascii=False)
        text = render_asset(
            "adr.md",
            {
                "ID": item_id,
                "TITLE": yaml_string(title),
                "OWNER": yaml_string(owner_value),
                "AUTHOR": yaml_string(author_value),
                "RESEARCH_REFS": refs_json,
                "DEPENDS_ON": json.dumps(depends_on, ensure_ascii=False),
                "AMENDS": json.dumps(amends, ensure_ascii=False),
                "AMENDS_CONSTRAINTS": json.dumps(
                    amends_constraints,
                    ensure_ascii=False,
                ),
                "DESIGN_REFS": json.dumps(design_refs, ensure_ascii=False),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
            },
        )
        index_path = repo / "docs" / "DECISIONS.md"
        old_index = index_path.read_text(encoding="utf-8")
        try:
            atomic_write(path, text)
            atomic_write(
                index_path,
                rebuild_adr_index_text(repo, old_index),
            )
        except Exception:
            if path.exists():
                path.unlink()
            atomic_write(index_path, old_index)
            raise
        return path


def new_ep(
    repo: Path,
    slug: str,
    title: str,
    owner: str,
    author: str,
    research_values: Iterable[str],
    adr_values: Iterable[str],
    design_values: Iterable[str],
    benchmark_scenario_values: Iterable[str],
    architecture_entrypoint_value: str,
    research_not_required_reason: str,
    decision_not_required_reason: str,
    architecture_not_applicable_reason: str,
) -> Path:
    validate_slug(slug)
    owner_value = metadata_actor(owner)
    author_value = metadata_actor(author)
    research_refs = normalize_reference_ids(research_values, "R")
    adr_refs = normalize_reference_ids(adr_values, "ADR")
    benchmark_scenario_refs = normalize_benchmark_scenario_ids(
        benchmark_scenario_values
    )
    raw_design_values = list(design_values)
    research_reason = inline_text(research_not_required_reason)
    decision_reason = inline_text(decision_not_required_reason)
    compliance_reason = inline_text(architecture_not_applicable_reason)
    if research_refs and research_reason:
        raise EpctlError(
            "Use Research references or --research-not-required-reason, not both"
        )
    if not research_refs and not research_reason:
        raise EpctlError(
            "new-ep requires concluded --research references or "
            "--research-not-required-reason"
        )
    if not adr_refs and not decision_reason:
        raise EpctlError(
            "new-ep requires accepted --adr references or a "
            "--decision-not-required-reason"
        )
    with repo_lock(repo):
        init_repo(repo)
        for scenario_id in benchmark_scenario_refs:
            scenario_errors = validate_benchmark_scenario_reference(
                repo,
                scenario_id,
            )
            if scenario_errors:
                raise EpctlError(
                    f"{scenario_id} is not a valid predeclared Benchmark "
                    "Scenario:\n- "
                    + "\n- ".join(scenario_errors)
                )
        design_refs = normalize_document_refs(
            repo,
            raw_design_values,
            "design_refs",
        )
        design_details, design_errors, design_warnings = (
            validate_design_input_set(repo, design_refs)
        )
        if design_errors:
            raise EpctlError(
                "Design input set is invalid:\n- "
                + "\n- ".join(design_errors)
            )
        for warning in design_warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        design_evidence = [
            str(details["evidence"])
            for details in design_details.values()
            if details.get("evidence")
        ]
        architecture_entrypoint = ""
        if inline_text(architecture_entrypoint_value):
            architecture_entrypoint = normalize_document_refs(
                repo,
                (architecture_entrypoint_value,),
                "architecture_entrypoint",
            )[0]
        has_architecture_inputs = bool(
            adr_refs or design_refs or architecture_entrypoint
        )
        if has_architecture_inputs and compliance_reason:
            raise EpctlError(
                "--architecture-not-applicable-reason cannot be used when "
                "architecture inputs are present"
            )
        if not has_architecture_inputs and not compliance_reason:
            compliance_reason = decision_reason
        if not has_architecture_inputs and not compliance_reason:
            raise EpctlError(
                "Architecture compliance not_applicable requires a reason"
            )
        for research_id in research_refs:
            research_path = find_research(repo, research_id, "completed")
            errors, _ = validate_research(research_path)
            data, _, _ = parse_frontmatter(
                research_path.read_text(encoding="utf-8")
            )
            if errors or data.get("status") != "concluded":
                details = "; ".join(errors) if errors else data.get("status", "")
                raise EpctlError(
                    f"{research_id} must be valid and concluded: {details}"
                )
        closure, adr_data_by_id = adr_input_closure(repo, adr_refs)
        missing_adrs = set(closure) - set(adr_refs)
        if missing_adrs:
            raise EpctlError(
                "Plan ADR set is not dependency-closed; add: "
                + ", ".join(sorted(missing_adrs))
            )
        for adr_id in closure:
            adr_data = adr_data_by_id[adr_id]
            missing_research = set(
                parse_inline_ids(adr_data.get("research_refs", ""), "R")
            ) - set(research_refs)
            if missing_research:
                raise EpctlError(
                    f"{adr_id} requires Research references missing from the plan: "
                    + ", ".join(sorted(missing_research))
                )
            required_designs = set(
                parse_string_array(adr_data.get("design_refs", ""), "design_refs")
            )
            missing_designs = required_designs - set(design_refs)
            if missing_designs:
                raise EpctlError(
                    f"{adr_id} requires Design Doc references missing from the plan: "
                    + ", ".join(sorted(missing_designs))
                )
        structured_constraint_refs, compliance_rows = (
            render_architecture_compliance_rows(
                adr_refs,
                repo,
                design_refs,
                architecture_entrypoint,
            )
        )
        scoped_amendments = current_constraint_amendments(
            repo,
            structured_constraint_refs,
        )
        missing_amendments = set(scoped_amendments) - set(adr_refs)
        if missing_amendments:
            details = "; ".join(
                f"{adr_id} (amends {', '.join(scoped_amendments[adr_id])})"
                for adr_id in sorted(missing_amendments)
            )
            raise EpctlError(
                "Plan ADR set omits current scoped amendments: " + details
            )
        adr_evidence = adr_evidence_values(adr_refs, adr_data_by_id)
        item_id = next_id(repo, "EP")
        number = int(item_id.split("-")[1])
        directory_name = f"ep-{number:03d}_{slug}"
        directory = repo / "docs" / "exec-plans" / "active" / directory_name
        path = directory / "EXECPLAN.md"
        reject_symlink_path(repo, path)
        if directory.exists():
            raise EpctlError(f"Destination already exists: {directory}")
        text = render_asset(
            "execplan.md",
            {
                "ID": item_id,
                "TITLE": yaml_string(title),
                "OWNER": yaml_string(owner_value),
                "AUTHOR": yaml_string(author_value),
                "RESEARCH_REFS": json.dumps(
                    research_refs, ensure_ascii=False
                ),
                "RESEARCH_GATE": (
                    "satisfied" if research_refs else "not_required"
                ),
                "RESEARCH_GATE_REASON": yaml_string(research_reason),
                "ADR_REFS": json.dumps(adr_refs, ensure_ascii=False),
                "ADR_CONSTRAINT_REFS": json.dumps(
                    structured_constraint_refs,
                    ensure_ascii=False,
                ),
                "ADR_EVIDENCE": json.dumps(
                    adr_evidence,
                    ensure_ascii=False,
                ),
                "DESIGN_REFS": json.dumps(design_refs, ensure_ascii=False),
                "DESIGN_EVIDENCE": json.dumps(
                    design_evidence,
                    ensure_ascii=False,
                ),
                "REQUIRED_BENCHMARK_SCENARIOS": json.dumps(
                    benchmark_scenario_refs,
                    ensure_ascii=False,
                ),
                "BENCHMARK_GATE_ROWS": benchmark_gate_rows(
                    benchmark_scenario_refs
                ),
                "BENCHMARK_ACCEPTANCE_ITEMS": benchmark_acceptance_items(
                    benchmark_scenario_refs
                ),
                "ARCHITECTURE_ENTRYPOINT": yaml_string(
                    architecture_entrypoint
                ),
                "ARCHITECTURE_DECISION_GATE": (
                    "not_required" if decision_reason else "satisfied"
                ),
                "ARCHITECTURE_DECISION_GATE_REASON": yaml_string(
                    decision_reason
                ),
                "ARCHITECTURE_COMPLIANCE": (
                    "applicable" if has_architecture_inputs else "not_applicable"
                ),
                "ARCHITECTURE_COMPLIANCE_REASON": yaml_string(
                    compliance_reason
                ),
                "ARCHITECTURE_COMPLIANCE_ROWS": compliance_rows,
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
                "DIR_NAME": directory_name,
            },
        )
        index_path = repo / "docs" / "PLANS.md"
        old_index = index_path.read_text(encoding="utf-8")
        relative = path.relative_to(repo / "docs").as_posix()
        row = (
            f"| {item_id} | {md_cell(title)} | active | {date_string()} | "
            f"[EXECPLAN]({relative}) |"
        )
        new_index = upsert_index_row(old_index, "EP", "ACTIVE", item_id, row)
        try:
            atomic_write(path, text)
            atomic_write(index_path, new_index)
        except Exception:
            if path.exists():
                path.unlink()
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
            atomic_write(index_path, old_index)
            raise
        return path


def new_task(
    repo: Path,
    plan_id: str,
    slug: str,
    title: str,
    owner: str,
    author: str,
) -> Path:
    validate_slug(slug)
    with repo_lock(repo):
        plan_path = find_plan(repo, plan_id, "active")
        if plan_path.name != "EXECPLAN.md":
            raise EpctlError("new-task requires a v2 plan with EXECPLAN.md")
        plan_data, _, _ = parse_frontmatter(
            plan_path.read_text(encoding="utf-8")
        )
        owner_value = metadata_actor(owner or plan_data.get("owner", ""))
        author_value = metadata_actor(author or plan_data.get("author", ""))
        tasks_dir = plan_path.parent / "tasks"
        reject_symlink_path(repo, tasks_dir)
        tasks_dir.mkdir(exist_ok=True)
        task_id = next_id(
            repo,
            "TASK",
            tasks_dir,
            state_key=f"TASK:{plan_id.upper()}",
        )
        path = tasks_dir / f"{slug}.md"
        reject_symlink_path(repo, path)
        if path.exists():
            raise EpctlError(f"Task already exists: {path}")
        text = render_asset(
            "task.md",
            {
                "TASK_ID": task_id,
                "TITLE": yaml_string(title),
                "PARENT_ID": plan_id.upper(),
                "OWNER": yaml_string(owner_value),
                "AUTHOR": yaml_string(author_value),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
            },
        )
        atomic_write(path, text)
        return path


def new_bugfix(
    repo: Path,
    slug: str,
    title: str,
    area: str,
    severity: str,
    owner: str,
    author: str,
) -> Path:
    validate_slug(slug)
    owner_value = metadata_actor(owner)
    author_value = metadata_actor(author)
    with repo_lock(repo):
        init_repo(repo)
        item_id = next_id(repo, "BF")
        number = int(item_id.split("-")[1])
        path = (
            repo
            / "docs"
            / "bugfixes"
            / "active"
            / f"bf-{number:03d}_{slug}.md"
        )
        reject_symlink_path(repo, path)
        text = render_asset(
            "bugfix.md",
            {
                "ID": item_id,
                "TITLE": yaml_string(title),
                "AREA": yaml_string(area),
                "SEVERITY": yaml_string(severity),
                "OWNER": yaml_string(owner_value),
                "AUTHOR": yaml_string(author_value),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
            },
        )
        index_path = repo / "docs" / "BUGFIXES.md"
        old_index = index_path.read_text(encoding="utf-8")
        relative = path.relative_to(repo / "docs").as_posix()
        row = (
            f"| {item_id} | {md_cell(title)} | {md_cell(area)} | "
            f"{md_cell(severity)} | open | {date_string()} |  | "
            f"[record]({relative}) |"
        )
        new_index = upsert_index_row(old_index, "BF", "ACTIVE", item_id, row)
        try:
            atomic_write(path, text)
            atomic_write(index_path, new_index)
        except Exception:
            if path.exists():
                path.unlink()
            atomic_write(index_path, old_index)
            raise
        return path


def new_debt(
    repo: Path, description: str, area: str, priority: str, target: str
) -> str:
    with repo_lock(repo):
        init_repo(repo)
        legacy = repo / "docs" / "tech-debt-tracker.md"
        path = (
            legacy
            if legacy.exists()
            else repo / "docs" / "exec-plans" / "tech-debt-tracker.md"
        )
        reject_symlink_path(repo, path)
        text = path.read_text(encoding="utf-8")
        if "<!-- TDCTL:ACTIVE:START -->" not in text:
            text = ensure_markers(text, "TD")
        item_id = next_id(repo, "TD")
        row = (
            f"| {item_id} | {md_cell(description)} | {md_cell(area)} | "
            f"{md_cell(priority)} | {md_cell(target)} | open | {date_string()} |"
        )
        text = upsert_index_row(text, "TD", "ACTIVE", item_id, row)
        text = re.sub(
            r"(?m)^Last updated: .*$", f"Last updated: {date_string()}", text
        )
        atomic_write(path, text)
        return item_id


def inline_text(value: str) -> str:
    return " ".join(value.strip().split())


def plan_repository(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == "docs":
            return parent.parent
    raise EpctlError(f"ExecPlan is not below a docs directory: {path}")


def validate_benchmark_scenario_reference(
    repo: Path,
    scenario_id: str,
) -> list[str]:
    paths = sorted(
        (repo / "benchmarks" / "suites").glob(
            f"*/scenarios/{scenario_id.lower()}_*.md"
        )
    )
    if len(paths) != 1:
        return [
            f"{scenario_id}: expected exactly one local predeclared Scenario, "
            f"found {len(paths)}"
        ]
    path = paths[0]
    try:
        reject_symlink_path(repo, path)
        text = path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
    except (EpctlError, OSError, UnicodeDecodeError) as exc:
        return [f"{path}: invalid Benchmark Scenario: {exc}"]
    errors: list[str] = []
    expected_fields = {"id": scenario_id, "status": "active"}
    for field, expected in expected_fields.items():
        if data.get(field) != expected:
            errors.append(
                f"{path}: {field} must be {expected!r}, "
                f"found {data.get(field)!r}"
            )
    if data.get("schema_version") not in {"1", "1.1"}:
        errors.append(f"{path}: schema_version must be '1' or '1.1'")
    if data.get("schema_version") == "1.1":
        errors.extend(
            validate_metadata_contract(
                path,
                data,
                "benchmark-scenario",
                scenario_id,
            )
        )
    if not inline_text(data.get("title", "")):
        errors.append(f"{path}: title must be a non-empty string")
    errors.extend(
        validate_required_sections(
            path,
            text,
            BENCHMARK_SCENARIO_SECTIONS,
        )
    )
    suite_id = data.get("suite_id", "")
    if not re.fullmatch(r"B-\d{3,}", suite_id, re.IGNORECASE):
        errors.append(f"{path}: invalid suite_id {suite_id!r}")
    else:
        suite_path = path.parent.parent / "BENCHMARK.md"
        try:
            reject_symlink_path(repo, suite_path)
            suite_text = suite_path.read_text(encoding="utf-8")
            suite_data, _, _ = parse_frontmatter(suite_text)
        except (EpctlError, OSError, UnicodeDecodeError) as exc:
            errors.append(f"{suite_path}: invalid Benchmark Suite: {exc}")
        else:
            if suite_data.get("schema_version") not in {"1", "1.1"}:
                errors.append(
                    f"{suite_path}: schema_version must be '1' or '1.1'"
                )
            if suite_data.get("id") != suite_id:
                errors.append(
                    f"{suite_path}: id does not match Scenario suite_id {suite_id}"
                )
            if suite_data.get("status") != "active":
                errors.append(f"{suite_path}: status must be 'active'")
            if not inline_text(suite_data.get("title", "")):
                errors.append(f"{suite_path}: title must be a non-empty string")
            if suite_data.get("schema_version") == "1.1":
                errors.extend(
                    validate_metadata_contract(
                        suite_path,
                        suite_data,
                        "benchmark-suite",
                        suite_id,
                    )
                )
            owner = inline_text(suite_data.get("owner", ""))
            if not owner or owner == "Unassigned":
                errors.append(
                    f"{suite_path}: owner must identify an accountable owner"
                )
            errors.extend(
                validate_required_sections(
                    suite_path,
                    suite_text,
                    BENCHMARK_SUITE_SECTIONS,
                )
            )
            if marker_names(suite_text):
                errors.append(
                    f"{suite_path}: unresolved REQUIRED marker in Benchmark Suite"
                )
    if marker_names(text):
        errors.append(
            f"{path}: unresolved REQUIRED marker in Benchmark Scenario"
        )
    return errors


def benchmark_manifest_digest(manifest: dict[str, object]) -> str:
    payload = dict(manifest)
    payload["payload_sha256"] = ""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def benchmark_bundle_inventory(
    repo: Path,
    run_directory: Path,
) -> tuple[list[dict[str, object]], list[str]]:
    errors: list[str] = []
    allowed_root_files = {
        "SCENARIO.md",
        "RESULT.md",
        "EVIDENCE_MANIFEST.json",
    }
    try:
        reject_symlink_path(repo, run_directory)
    except EpctlError as exc:
        return [], [str(exc)]
    for child in sorted(run_directory.iterdir()):
        try:
            reject_symlink_path(repo, child)
        except EpctlError as exc:
            errors.append(str(exc))
            continue
        if child.is_file() and child.name not in allowed_root_files:
            errors.append(
                f"{child}: Benchmark Run files must be below artifacts/"
            )
        elif child.is_dir() and child.name != "artifacts":
            errors.append(
                f"{child}: unexpected Benchmark Run directory"
            )
    artifacts = run_directory / "artifacts"
    if not artifacts.is_dir() or artifacts.is_symlink():
        errors.append(f"{artifacts}: missing regular artifacts directory")
        return [], errors

    paths = [
        run_directory / "RESULT.md",
        run_directory / "SCENARIO.md",
    ]
    for root, directories, files in os.walk(artifacts, followlinks=False):
        root_path = Path(root)
        for name in directories:
            candidate = root_path / name
            if candidate.is_symlink():
                errors.append(
                    f"{candidate}: symlinked Benchmark artifact directory"
                )
        for name in files:
            candidate = root_path / name
            if candidate.is_symlink():
                errors.append(f"{candidate}: symlinked Benchmark artifact")
            elif candidate.is_file():
                paths.append(candidate)
            else:
                errors.append(
                    f"{candidate}: Benchmark artifact is not a regular file"
                )
    inventory: list[dict[str, object]] = []
    for path in sorted(paths):
        if not path.is_file() or path.is_symlink():
            errors.append(f"{path}: missing regular Benchmark evidence file")
            continue
        content = path.read_bytes()
        inventory.append(
            {
                "path": path.relative_to(run_directory).as_posix(),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return sorted(inventory, key=lambda item: str(item["path"])), errors


def validate_benchmark_evidence_reference(
    repo: Path,
    reference: str,
    verified_revision: str,
) -> tuple[list[str], str | None]:
    match = BENCHMARK_EVIDENCE_RE.fullmatch(reference)
    if not match:
        return (
            [
                "Benchmark evidence must use "
                "benchmark:BR-NNN@sha256:<manifest-payload-sha256>"
            ],
            None,
        )
    run_id, referenced_digest = match.groups()
    manifest_paths = sorted(
        (
            repo
            / "benchmarks"
            / "suites"
        ).glob(
            f"*/runs/{run_id.lower()}_*/EVIDENCE_MANIFEST.json"
        )
    )
    if len(manifest_paths) != 1:
        return (
            [
                f"{reference}: expected exactly one local sealed {run_id}, "
                f"found {len(manifest_paths)}"
            ],
            None,
        )
    manifest_path = manifest_paths[0]
    try:
        reject_symlink_path(repo, manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (EpctlError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{manifest_path}: invalid Benchmark Manifest: {exc}"], None
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: Benchmark Manifest must be an object"], None

    errors: list[str] = []
    expected_fields = {
        "run_id": run_id,
        "status": "sealed",
        "outcome": "passed",
    }
    for field, expected in expected_fields.items():
        if manifest.get(field) != expected:
            errors.append(
                f"{manifest_path}: {field} must be {expected!r}, "
                f"found {manifest.get(field)!r}"
            )
    manifest_schema = manifest.get("schema_version")
    if manifest_schema not in {"1", "1.1"}:
        errors.append(
            f"{manifest_path}: schema_version must be '1' or '1.1'"
        )
    if manifest_schema == "1.1":
        for field, expected in (
            ("metadata_schema", "1"),
            ("artifact_type", "benchmark-manifest"),
            ("id", f"{run_id}-MANIFEST"),
        ):
            if manifest.get(field) != expected:
                errors.append(f"{manifest_path}: {field} must be {expected!r}")
        for field in ("title", "author", "owner", "created", "updated"):
            value = manifest.get(field)
            if not isinstance(value, str) or not inline_text(value):
                errors.append(
                    f"{manifest_path}: metadata field {field} must be non-empty"
                )
    for field in (
        "suite_id",
        "scenario_id",
        "created",
        "sealed_at",
        "executed_by",
    ):
        value = manifest.get(field)
        if not isinstance(value, str) or not inline_text(value):
            errors.append(
                f"{manifest_path}: {field} must be a non-empty string"
            )
    payload = manifest.get("payload_sha256")
    if payload != referenced_digest:
        errors.append(
            f"{manifest_path}: reference digest does not match payload_sha256"
        )
    if not isinstance(payload, str) or not re.fullmatch(
        r"[0-9a-f]{64}",
        payload,
    ):
        errors.append(f"{manifest_path}: invalid payload_sha256")
    elif benchmark_manifest_digest(manifest) != payload:
        errors.append(f"{manifest_path}: payload_sha256 mismatch")

    expected_inventory, inventory_errors = benchmark_bundle_inventory(
        repo,
        manifest_path.parent,
    )
    errors.extend(inventory_errors)
    if manifest.get("files") != expected_inventory:
        errors.append(
            f"{manifest_path}: Benchmark evidence inventory or digest drift"
        )

    result_path = manifest_path.parent / "RESULT.md"
    if result_path.is_file() and not result_path.is_symlink():
        try:
            result_text = result_path.read_text(encoding="utf-8")
            result_data, _, _ = parse_frontmatter(result_text)
        except (EpctlError, OSError, UnicodeDecodeError) as exc:
            errors.append(f"{result_path}: invalid Benchmark Result: {exc}")
        else:
            result_expectations = {
                "schema_version": manifest_schema,
                "id": run_id,
                "suite_id": manifest.get("suite_id"),
                "scenario_id": manifest.get("scenario_id"),
                "status": "sealed",
                "outcome": "passed",
                "completed": manifest.get("sealed_at"),
                "executed_by": manifest.get("executed_by"),
            }
            for field, expected in result_expectations.items():
                if result_data.get(field) != expected:
                    errors.append(
                        f"{result_path}: {field} does not match the Manifest"
                    )
            if result_data.get("schema_version") == "1.1":
                errors.extend(
                    validate_metadata_contract(
                        result_path,
                        result_data,
                        "benchmark-result",
                        run_id,
                    )
                )
            if result_data.get("subject_revision") != verified_revision:
                errors.append(
                    f"{result_path}: subject_revision "
                    f"{result_data.get('subject_revision')!r} does not match "
                    f"ExecPlan verified_revision {verified_revision!r}"
                )
            if result_data.get("manifest") != "EVIDENCE_MANIFEST.json":
                errors.append(
                    f"{result_path}: manifest must be "
                    "EVIDENCE_MANIFEST.json"
                )
            if marker_names(result_text):
                errors.append(
                    f"{result_path}: sealed Benchmark Result has "
                    "required placeholders"
                )
    scenario_path = manifest_path.parent / "SCENARIO.md"
    if scenario_path.is_file() and not scenario_path.is_symlink():
        try:
            scenario_text = scenario_path.read_text(encoding="utf-8")
            scenario_data, _, _ = parse_frontmatter(scenario_text)
        except (EpctlError, OSError, UnicodeDecodeError) as exc:
            errors.append(
                f"{scenario_path}: invalid Benchmark Scenario: {exc}"
            )
        else:
            if scenario_data.get("schema_version") not in {"1", "1.1"}:
                errors.append(
                    f"{scenario_path}: schema_version must be '1' or '1.1'"
                )
            if scenario_data.get("id") != manifest.get("scenario_id"):
                errors.append(
                    f"{scenario_path}: id does not match the Manifest"
                )
            if scenario_data.get("suite_id") != manifest.get("suite_id"):
                errors.append(
                    f"{scenario_path}: suite_id does not match the Manifest"
                )
            if scenario_data.get("schema_version") == "1.1":
                errors.extend(
                    validate_metadata_contract(
                        scenario_path,
                        scenario_data,
                        "benchmark-scenario",
                        str(manifest.get("scenario_id", "")),
                    )
                )
            if marker_names(scenario_text):
                errors.append(
                    f"{scenario_path}: sealed Benchmark Scenario has "
                    "required placeholders"
                )
    scenario_id = manifest.get("scenario_id")
    return errors, scenario_id if isinstance(scenario_id, str) else None


def validate_benchmark_evidence(
    repo: Path,
    evidence: Iterable[str],
    verified_revision: str,
    required_scenarios: Iterable[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    declared = (
        list(required_scenarios)
        if required_scenarios is not None
        else None
    )
    accepted_by_scenario: dict[str, list[str]] = {}
    for reference in evidence:
        if reference.startswith("benchmark:"):
            reference_errors, scenario_id = (
                validate_benchmark_evidence_reference(
                    repo,
                    reference,
                    verified_revision,
                )
            )
            errors.extend(reference_errors)
            if not reference_errors and scenario_id:
                accepted_by_scenario.setdefault(scenario_id, []).append(
                    reference
                )
    if declared is not None:
        declared_set = set(declared)
        for scenario_id in sorted(set(accepted_by_scenario) - declared_set):
            errors.append(
                f"Benchmark evidence belongs to undeclared Scenario {scenario_id}"
            )
        for scenario_id in declared:
            references = accepted_by_scenario.get(scenario_id, [])
            if not references:
                errors.append(
                    f"Required Benchmark Scenario {scenario_id} has no valid "
                    "passed sealed Run evidence"
                )
            elif len(references) > 1:
                errors.append(
                    f"Required Benchmark Scenario {scenario_id} must have "
                    "exactly one accepted Run evidence"
                )
    return errors


def archive_or_none(value: str) -> str:
    return "- None." if is_empty_history_body(value) else value.strip()


def checkpoint_plan(
    repo: Path,
    plan_id: str,
    slug: str,
    title: str,
    current_milestone: str,
    summary: str,
    next_action: str,
    revision: str,
    dry_run: bool,
) -> dict[str, object]:
    validate_slug(slug)
    if not inline_text(title):
        raise EpctlError("Checkpoint title must not be empty")
    if not inline_text(current_milestone):
        raise EpctlError("Checkpoint current milestone must not be empty")
    if not inline_text(summary):
        raise EpctlError("Checkpoint summary must not be empty")
    if not inline_text(next_action):
        raise EpctlError("Checkpoint next action must not be empty")
    revision = inline_text(revision)
    if not revision:
        raise EpctlError(
            "Checkpoint requires --revision so sealed history is bound "
            "to a repository or workspace version"
        )

    with repo_lock(repo):
        plan_path = find_plan(repo, plan_id, "active")
        if plan_path.name != "EXECPLAN.md":
            raise EpctlError("checkpoint requires a v2 EXECPLAN.md")
        text = plan_path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
        if data.get("schema_version") not in {
            "2.1",
            "2.2",
            "2.3",
            "2.4",
            "2.5",
            "2.6",
            "2.7",
            "2.8",
        }:
            raise EpctlError(
                "checkpoint requires schema_version 2.1 through 2.8 "
                "and ## Current Snapshot"
            )
        errors, _ = validate_plan(plan_path)
        if errors:
            raise EpctlError(
                "Checkpoint blocked by invalid plan:\n- " + "\n- ".join(errors)
            )
        if marker_names(text):
            raise EpctlError(
                "Checkpoint blocked: required placeholders remain in EXECPLAN.md"
            )

        history_dir = plan_path.parent / "history"
        reject_symlink_path(repo, history_dir)
        state_key = f"CP:{plan_id.upper()}"
        if dry_run:
            checkpoint_id = peek_next_id(
                repo,
                "CP",
                history_dir,
                state_key=state_key,
            )
        else:
            checkpoint_id = next_id(
                repo,
                "CP",
                history_dir,
                state_key=state_key,
            )
        number = int(checkpoint_id.split("-")[1])
        filename = f"cp-{number:03d}_{slug}.md"
        checkpoint_path = history_dir / filename
        reject_symlink_path(repo, checkpoint_path)
        if checkpoint_path.exists():
            raise EpctlError(f"Checkpoint already exists: {checkpoint_path}")

        archived_progress, remaining_progress = partition_completed_progress(
            section(text, "Progress") or ""
        )
        archived_discoveries = archive_or_none(
            section(text, "Surprises & Discoveries") or ""
        )
        archived_decisions = archive_or_none(
            section(text, "Decision Log") or ""
        )
        archived_revisions = archive_or_none(
            section(text, "Revision Notes") or ""
        )
        archived_blockers, remaining_blockers = partition_blockers(
            section(text, "Blockers") or ""
        )
        archived_blocker_count = sum(
            1
            for line in archived_blockers.splitlines()
            if line.lstrip().startswith("|")
            and (cells := split_table_row(line))
            and cells[0] != "ID"
            and set(cells[0]) != {"-"}
        )
        archived_progress = archive_or_none(archived_progress)
        archived_blockers = archive_or_none(archived_blockers)

        relative_checkpoint = checkpoint_path.relative_to(
            plan_path.parent
        ).as_posix()
        open_blockers = unresolved_blockers(text)
        snapshot = "\n".join(
            (
                f"- Latest checkpoint: [{checkpoint_id}]({relative_checkpoint}).",
                f"- Current milestone: {inline_text(current_milestone)}",
                f"- Current state: {inline_text(summary)}",
                f"- Next action: {inline_text(next_action)}",
                "- Open blockers: "
                + (
                    ", ".join(f"`{item}`" for item in open_blockers)
                    if open_blockers
                    else "none."
                ),
            )
        )
        if not remaining_progress.strip():
            remaining_progress = (
                f"- [ ] ({timestamp_string()}) "
                f"Continue with: {inline_text(next_action)}"
            )
        revision_note = (
            f"- {timestamp_string()} — Sealed {checkpoint_id}; "
            "refreshed Current Snapshot and preserved historical detail."
        )

        new_root = replace_section(text, "Current Snapshot", snapshot)
        new_root = replace_section(new_root, "Progress", remaining_progress)
        new_root = replace_section(
            new_root,
            "Surprises & Discoveries",
            f"- None since {checkpoint_id}.",
        )
        new_root = replace_section(
            new_root,
            "Decision Log",
            f"- None since {checkpoint_id}.",
        )
        new_root = replace_section(new_root, "Blockers", remaining_blockers)
        new_root = replace_section(new_root, "Revision Notes", revision_note)
        new_root = update_frontmatter(
            new_root,
            {
                "latest_checkpoint": checkpoint_id,
                "updated": date_string(),
            },
        )

        previous = data.get("latest_checkpoint", "")
        candidate = render_asset(
            "checkpoint.md",
            {
                "CHECKPOINT_ID": checkpoint_id,
                "PARENT_ID": plan_id.upper(),
                "TITLE": yaml_string(inline_text(title)),
                "PREVIOUS_CHECKPOINT": previous,
                "REPOSITORY_REVISION": yaml_string(revision),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
                "AUTHOR": yaml_string(
                    metadata_actor(data.get("author", ""))
                ),
                "OWNER": yaml_string(
                    metadata_actor(data.get("owner", ""))
                ),
                "PAYLOAD_SHA256": "PENDING",
                "SUMMARY": summary.strip(),
                "NEXT_ACTION": next_action.strip(),
                "ARCHIVED_PROGRESS": archived_progress,
                "ARCHIVED_DISCOVERIES": archived_discoveries,
                "ARCHIVED_DECISIONS": archived_decisions,
                "ARCHIVED_BLOCKERS": archived_blockers,
                "ARCHIVED_REVISIONS": archived_revisions,
            },
        )
        digest = canonical_document_sha256(candidate, "payload_sha256")
        candidate = candidate.replace(
            "payload_sha256: PENDING",
            f"payload_sha256: {digest}",
            1,
        )
        payload = {
            "checkpoint_id": checkpoint_id,
            "path": checkpoint_path.relative_to(repo).as_posix(),
            "previous_checkpoint": previous or None,
            "repository_revision": revision,
            "dry_run": dry_run,
            "archived": {
                "progress_blocks": (
                    0
                    if archived_progress == "- None."
                    else len(markdown_list_blocks(archived_progress))
                ),
                "discoveries": archived_discoveries != "- None.",
                "decisions": archived_decisions != "- None.",
                "resolved_blockers": archived_blocker_count,
                "revision_notes": archived_revisions != "- None.",
            },
        }
        if dry_run:
            return payload

        snapshots = managed_index_snapshots(repo)
        try:
            atomic_write(checkpoint_path, candidate)
            atomic_write(plan_path, new_root)
            post_errors, _ = validate_plan(plan_path)
            if post_errors:
                raise EpctlError(
                    "Checkpoint produced invalid plan:\n- "
                    + "\n- ".join(post_errors)
                )
            rebuild_indexes(repo)
        except Exception:
            atomic_write(plan_path, text)
            if checkpoint_path.exists():
                checkpoint_path.unlink()
            if history_dir.exists() and not any(history_dir.iterdir()):
                history_dir.rmdir()
            restore_managed_indexes(snapshots)
            raise
        return payload


def path_id_number(path: Path, prefix: str) -> int | None:
    matches = re.findall(
        rf"(?i)(?:^|/){re.escape(prefix)}-(\d{{3,}})(?=[_./-]|$)",
        path.as_posix(),
    )
    return int(matches[-1]) if matches else None


def validate_common_frontmatter(
    path: Path,
    data: dict[str, str],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    item_id = data.get("id", "")
    match = ID_RE[prefix].fullmatch(item_id)
    if not match:
        errors.append(f"{path}: invalid {prefix.lower()} id {item_id!r}")
    elif prefix in {"EP", "BF"}:
        path_number = path_id_number(path, prefix)
        if path_number is not None and int(match.group(1)) != path_number:
            errors.append(f"{path}: frontmatter id {item_id} does not match path")
    for field in ("title", "created", "updated"):
        if not data.get(field):
            errors.append(f"{path}: missing frontmatter field {field}")
    for field in ("created", "updated"):
        value = data.get(field, "")
        if value:
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: {field} must be an ISO date, got {value!r}")
    return errors


def validate_required_sections(
    path: Path,
    text: str,
    headings: Iterable[str],
) -> list[str]:
    errors: list[str] = []
    for heading in headings:
        values = section_values(text, heading)
        if not values:
            errors.append(f"{path}: missing ## {heading}")
        elif len(values) > 1:
            errors.append(f"{path}: duplicate ## {heading}")
    return errors


def marker_names(text: str) -> set[str]:
    return set(
        re.findall(r"<!--\s*(REQUIRED(?:_[A-Z_]+)?)\s*:", text)
    )


def marker_present(text: str, marker: str) -> bool:
    return marker in marker_names(text)


def validate_blocked_state(
    path: Path,
    status: str,
    blockers: list[str],
    active_statuses: set[str],
) -> list[str]:
    errors: list[str] = []
    if status == "blocked" and not blockers:
        errors.append(f"{path}: blocked status requires an open blocker")
    elif status in active_statuses - {"blocked"} and blockers:
        errors.append(
            f"{path}: open blockers require blocked status: {', '.join(blockers)}"
        )
    return errors


def validate_blocker_table(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for cells in blocker_rows(text):
        blocker_id = cells[0].upper()
        status = cells[1].lower()
        if not BLOCKER_ID_RE.fullmatch(blocker_id):
            errors.append(f"{path}: invalid blocker id {cells[0]!r}")
        elif blocker_id in seen:
            errors.append(f"{path}: duplicate blocker id {blocker_id}")
        seen.add(blocker_id)
        if status not in {"open", "resolved", "dismissed"}:
            errors.append(f"{path}: invalid blocker status {cells[1]!r}")
        if len(cells) < 7:
            errors.append(f"{path}: blocker {blocker_id} must have seven columns")
            continue
        if not cells[2]:
            errors.append(f"{path}: blocker {blocker_id} requires Opened")
        if status in {"resolved", "dismissed"} and not cells[3]:
            errors.append(
                f"{path}: {status} blocker {blocker_id} requires Resolved"
            )
        if status == "open" and cells[3]:
            errors.append(
                f"{path}: open blocker {blocker_id} cannot have Resolved"
            )
    return errors


def research_question_rows(text: str) -> list[list[str]]:
    body = section(text, "Research Questions") or ""
    rows: list[list[str]] = []
    for line in visible_markdown_lines(body):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells or cells[0].lower() == "id" or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


def validate_research_questions(path: Path, text: str) -> tuple[list[str], int]:
    errors: list[str] = []
    seen: set[str] = set()
    open_count = 0
    rows = research_question_rows(text)
    if not rows:
        return [f"{path}: Research Questions needs at least one row"], open_count
    for cells in rows:
        if len(cells) < 5:
            errors.append(f"{path}: Research Question rows need five columns")
            continue
        question_id = cells[0].upper()
        status = cells[1].lower()
        if not RESEARCH_QUESTION_ID_RE.fullmatch(question_id):
            errors.append(f"{path}: invalid Research Question id {cells[0]!r}")
        elif question_id in seen:
            errors.append(f"{path}: duplicate Research Question id {question_id}")
        seen.add(question_id)
        if status not in RESEARCH_QUESTION_STATUSES:
            errors.append(
                f"{path}: invalid Research Question status {cells[1]!r}"
            )
            continue
        if not cells[2]:
            errors.append(f"{path}: {question_id} requires a question")
        if status == "open":
            open_count += 1
        elif not cells[3]:
            errors.append(
                f"{path}: {status} {question_id} requires an answer or disposition"
            )
        if status in {"answered", "invalidated"} and not cells[4]:
            errors.append(f"{path}: {status} {question_id} requires evidence")
    return errors, open_count


def validate_synthesis(
    path: Path,
    parent_id: str,
    require_sealed: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return [f"{path}: missing Synthesis"], warnings
    text = path.read_text(encoding="utf-8")
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings
    schema_version = data.get("schema_version")
    if schema_version not in {"1", "1.1", "1.2"}:
        errors.append(
            f"{path}: synthesis schema_version must be 1, 1.1 or 1.2"
        )
    if data.get("parent_id") != parent_id:
        errors.append(f"{path}: parent_id must be {parent_id}")
    if not data.get("title"):
        errors.append(f"{path}: missing synthesis title")
    for field in ("created", "updated"):
        value = data.get(field, "")
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            errors.append(f"{path}: {field} must be an ISO date, got {value!r}")
    status = data.get("status", "")
    allowed_statuses = (
        {"draft", "review_ready", "sealed"}
        if schema_version in {"1.1", "1.2"}
        else {"draft", "sealed"}
    )
    if status not in allowed_statuses:
        errors.append(f"{path}: invalid synthesis status {status!r}")
    if data.get("metadata_schema"):
        errors.extend(
            validate_metadata_contract(
                path,
                data,
                "research-synthesis",
                f"{parent_id}-SYNTHESIS",
            )
        )
    errors.extend(validate_required_sections(path, text, SYNTHESIS_SECTIONS))
    required = bool(marker_names(text))
    if require_sealed and status != "sealed":
        errors.append(f"{path}: concluded Research requires sealed Synthesis")
    if status in {"review_ready", "sealed"}:
        if required:
            errors.append(
                f"{path}: {status} Synthesis has required placeholders"
            )
        expected = data.get("payload_sha256", "")
        actual = payload_sha256(text)
        if not expected:
            errors.append(f"{path}: {status} Synthesis requires payload_sha256")
        elif expected != actual:
            errors.append(
                f"{path}: {status} Synthesis payload changed "
                f"(expected {expected}, got {actual})"
            )
    elif data.get("payload_sha256"):
        errors.append(f"{path}: draft Synthesis cannot have payload_sha256")
    elif required:
        warnings.append(f"{path}: required placeholders remain")
    return errors, warnings


def validate_research(
    path: Path,
    archive_status: str | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings
    research_id = data.get("id", "")
    errors.extend(validate_common_frontmatter(path, data, "R"))
    schema_version = data.get("schema_version")
    if schema_version not in {"1", "1.1", "1.2"}:
        errors.append(f"{path}: Research schema_version must be 1, 1.1 or 1.2")
    if data.get("metadata_schema") and research_id:
        errors.extend(
            validate_metadata_contract(path, data, "research", research_id)
        )
    location = "completed" if "/completed/" in path.as_posix() else "active"
    allowed = (
        RESEARCH_COMPLETED_STATUSES
        if location == "completed"
        else RESEARCH_ACTIVE_STATUSES
    )
    status = data.get("status", "")
    if status not in allowed and not (
        archive_status in RESEARCH_COMPLETED_STATUSES and location == "active"
    ):
        errors.append(f"{path}: status {status!r} is invalid in {location}")
    errors.extend(validate_required_sections(path, text, RESEARCH_SECTIONS))
    errors.extend(validate_blocker_table(path, text))
    blockers = unresolved_blockers(text)
    errors.extend(
        validate_blocked_state(
            path,
            status,
            blockers,
            RESEARCH_ACTIVE_STATUSES,
        )
    )
    question_errors, open_questions = validate_research_questions(path, text)
    errors.extend(question_errors)
    synthesis_name = data.get("synthesis", "")
    if synthesis_name != "SYNTHESIS.md":
        errors.append(f"{path}: synthesis must be SYNTHESIS.md")
    synthesis_path = path.parent / "SYNTHESIS.md"
    concluding = archive_status == "concluded" or (
        archive_status is None and status == "concluded"
    )
    synthesis_errors, synthesis_warnings = validate_synthesis(
        synthesis_path,
        research_id,
        require_sealed=concluding,
    )
    errors.extend(synthesis_errors)
    warnings.extend(synthesis_warnings)
    manifest_name = data.get("manifest", "")
    if manifest_name:
        if manifest_name != "RESEARCH_MANIFEST.json":
            errors.append(
                f"{path}: manifest must be RESEARCH_MANIFEST.json"
            )
        else:
            errors.extend(
                validate_research_manifest(
                    repository_from_artifact(path),
                    path.parent / manifest_name,
                    research_id,
                    require_sealed=concluding,
                )
            )
    if concluding:
        if open_questions:
            errors.append(
                f"{path}: {open_questions} open Research Questions block conclusion"
            )
        if blockers:
            errors.append(
                f"{path}: open blockers block conclusion: {', '.join(blockers)}"
            )
        if marker_names(text):
            errors.append(f"{path}: concluded Research has required placeholders")
        if schema_version in {"1.1", "1.2"}:
            if data.get("maturity") != "review_ready":
                errors.append(
                    f"{path}: concluded Research must have review_ready maturity"
                )
            for field in ("owner", "approved_by", "approved_at", "approval_ref"):
                if not data.get(field):
                    errors.append(
                        f"{path}: concluded Research requires {field}"
                    )
    elif marker_names(text) and status != "cancelled":
        warnings.append(f"{path}: required placeholders remain")
    root_bytes = len(text.encode("utf-8"))
    root_lines = len(text.splitlines())
    if root_bytes > ROOT_BYTE_WARNING or root_lines > ROOT_LINE_WARNING:
        warnings.append(
            f"{path}: Research controller is {root_lines} lines/{root_bytes} "
            "bytes; move focused analysis to notes/ and raw evidence to artifacts/"
        )
    return errors, warnings


def validate_adr(
    path: Path,
    *,
    historical: bool = False,
    document_text: str | None = None,
) -> tuple[list[str], list[str], dict[str, str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = (
        document_text
        if document_text is not None
        else path.read_text(encoding="utf-8")
    )
    try:
        data, strict = adr_document_data_from_text(path, text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings, {}
    adr_id = data.get("id", "")
    repo = repository_from_artifact(path)
    if strict:
        errors.extend(validate_common_frontmatter(path, data, "ADR"))
        if data.get("schema_version") not in {
            "1",
            "1.1",
            "1.2",
            "1.3",
            "1.4",
        }:
            errors.append(
                f"{path}: ADR schema_version must be 1, 1.1, 1.2, 1.3 or 1.4"
            )
        errors.extend(validate_required_sections(path, text, ADR_SECTIONS))
        if data.get("schema_version") in {"1.2", "1.3", "1.4"}:
            errors.extend(
                validate_required_sections(path, text, ADR_V12_SECTIONS)
            )
        if data.get("schema_version") in {"1.3", "1.4"} and adr_id:
            errors.extend(
                validate_metadata_contract(path, data, "adr", adr_id)
            )
    else:
        if not ID_RE["ADR"].fullmatch(adr_id):
            errors.append(
                f"{path}: linked ADR needs an ADR-NNN id in frontmatter or filename"
            )
        if data.get("doc_type") and data.get("doc_type") != "adr":
            errors.append(f"{path}: linked ADR has doc_type {data.get('doc_type')!r}")
        if not data.get("title"):
            errors.append(f"{path}: linked ADR requires a title")
        warnings.append(
            f"{path}: legacy linked ADR has no epctl decision authority/seal; "
            "treat it as read-only and use a new strict ADR for later decisions"
        )
    status = data.get("status", "")
    effect_metadata = (
        inline_text(data.get("effect_changed_by", "")),
        inline_text(data.get("effect_changed", "")),
        inline_text(data.get("effect_reason", "")),
    )
    if data.get("schema_version") != "1.4" and any(effect_metadata):
        if not all(effect_metadata):
            errors.append(
                f"{path}: effect transition metadata must set actor, time, and reason"
            )
        if status in {"under_review", "retired", "superseded"} and not all(
            effect_metadata
        ):
            errors.append(
                f"{path}: status {status!r} requires effect transition metadata"
            )
        if effect_metadata[1]:
            try:
                dt.datetime.fromisoformat(
                    effect_metadata[1].replace("Z", "+00:00")
                )
            except ValueError:
                errors.append(f"{path}: effect_changed must be an ISO timestamp")
    if status not in ADR_STATUSES:
        errors.append(f"{path}: invalid ADR status {status!r}")
    arrays: dict[str, list[str]] = {}
    try:
        for field, prefix in (
            ("research_refs", "R"),
            ("depends_on", "ADR"),
            ("amends", "ADR"),
            ("supersedes", "ADR"),
        ):
            arrays[field] = parse_reference_array(
                data.get(field, ""), prefix, field
            )
        design_refs = parse_string_array(data.get("design_refs", ""), "design_refs")
        amends_constraints = parse_adr_constraint_array(
            data.get("amends_constraints", ""),
            "amends_constraints",
        )
    except EpctlError as exc:
        errors.append(f"{path}: {exc}")
        arrays = {
            "research_refs": [],
            "depends_on": [],
            "amends": [],
            "supersedes": [],
        }
        design_refs = []
        amends_constraints = []
    research_refs = arrays["research_refs"]
    depends_on = arrays["depends_on"]
    amends = arrays["amends"]
    supersedes = arrays["supersedes"]
    if data.get("schema_version") in {"1.1", "1.2", "1.3", "1.4"}:
        required_fields = ["depends_on", "amends", "design_refs"]
        if data.get("schema_version") in {"1.2", "1.3", "1.4"}:
            required_fields.append("amends_constraints")
        if data.get("schema_version") == "1.4":
            required_fields.extend(
                (
                    "decision_outcome",
                    "effect_changed_by",
                    "effect_changed",
                    "effect_reason",
                )
            )
        for field in required_fields:
            if field not in data:
                errors.append(
                    f"{path}: schema {data.get('schema_version')} ADR requires "
                    f"{field}"
                )
    for field, values in (
        ("depends_on", depends_on),
        ("amends", amends),
        ("supersedes", supersedes),
    ):
        if adr_id in values:
            errors.append(f"{path}: ADR cannot list itself in {field}")
    overlap = (set(depends_on) & set(amends)) | (
        (set(depends_on) | set(amends)) & set(supersedes)
    )
    if overlap:
        errors.append(
            f"{path}: ADR relations must be disjoint: {', '.join(sorted(overlap))}"
        )
    for research_id in research_refs:
        try:
            research_path = find_research(
                repo,
                research_id,
                "completed",
            )
        except EpctlError:
            errors.append(f"{path}: missing concluded Research {research_id}")
            continue
        research_data = artifact_metadata(research_path, "R")
        research_errors, _ = validate_research(research_path)
        if research_errors or research_data.get("status") != "concluded":
            errors.append(f"{path}: {research_id} is not valid and concluded")
    relation_statuses = ADR_ACCEPTED_ORIGIN_STATUSES
    for related_id in (*depends_on, *amends):
        try:
            related_path = find_adr(repo, related_id)
            related_data, _ = adr_document_data(related_path)
        except EpctlError:
            errors.append(f"{path}: related ADR {related_id} is missing")
            continue
        if related_data.get("status") not in relation_statuses:
            errors.append(
                f"{path}: {related_id} in depends_on/amends must have status in "
                f"{sorted(relation_statuses)}"
            )
        elif (
            status in {"proposed", "accepted"}
            and related_data.get("status") != "accepted"
        ):
            warnings.append(
                f"{path}: architecture_review_required because related ADR "
                f"{related_id} is {related_data.get('status')!r}"
            )
    if data.get("schema_version") in {"1.2", "1.3", "1.4"}:
        decision_statement = re.sub(
            r"<!--[\s\S]*?-->",
            "",
            section(text, "Decision Statement") or "",
        )
        statement_issues = warnings if status == "proposed" else errors
        if unresolved_contract_cell(decision_statement):
            statement_issues.append(
                f"{path}: structured ADR needs a Decision Statement"
            )
        constraint_rows = adr_constraint_rows(text)
        seen_constraints: set[str] = set()
        incomplete_constraints = warnings if status == "proposed" else errors
        if not constraint_rows:
            incomplete_constraints.append(
                f"{path}: structured ADR needs a normative constraint"
            )
        for cells in constraint_rows:
            if len(cells) != 5:
                errors.append(
                    f"{path}: Normative Constraints rows require 5 columns"
                )
                continue
            constraint_id, strength, scope, constraint, confirmation = cells
            match = LOCAL_CONSTRAINT_RE.fullmatch(constraint_id.upper())
            if not match:
                errors.append(
                    f"{path}: invalid constraint ID {constraint_id!r}; "
                    "expected C-NNN"
                )
                continue
            canonical = f"C-{int(match.group(1)):03d}"
            if canonical in seen_constraints:
                errors.append(f"{path}: duplicate constraint ID {canonical}")
            seen_constraints.add(canonical)
            if strength.lower() not in ADR_CONSTRAINT_STRENGTHS:
                errors.append(
                    f"{path}: {canonical} strength must be one of "
                    + ", ".join(sorted(ADR_CONSTRAINT_STRENGTHS))
                )
            for label, value in (
                ("scope", scope),
                ("constraint", constraint),
                ("confirmation", confirmation),
            ):
                if unresolved_contract_cell(value):
                    incomplete_constraints.append(
                        f"{path}: {canonical} has unresolved {label}"
                    )
        amended_parents = {
            reference.split("#", 1)[0] for reference in amends_constraints
        }
        if amended_parents != set(amends):
            errors.append(
                f"{path}: structured amends_constraints must cover exactly "
                "the ADRs listed in amends"
            )
        for constraint_ref in amends_constraints:
            related_id = constraint_ref.split("#", 1)[0]
            try:
                related_path = find_adr(repo, related_id)
            except EpctlError:
                continue
            available = set(
                adr_constraint_refs(
                    related_path.read_text(encoding="utf-8"),
                    related_id,
                )
            )
            if constraint_ref not in available:
                errors.append(
                    f"{path}: amended constraint {constraint_ref} does not exist"
                )
    for design_ref in design_refs:
        design_errors, design_warnings = validate_design_ref(repo, design_ref)
        errors.extend(f"{path}: {error}" for error in design_errors)
        warnings.extend(design_warnings)
    superseded_by = data.get("superseded_by", "")
    if superseded_by and not ID_RE["ADR"].fullmatch(superseded_by):
        errors.append(f"{path}: invalid superseded_by {superseded_by!r}")
    decided = status in ADR_HISTORICAL_STATUSES
    if strict and decided:
        if not data.get("decision_maker"):
            errors.append(f"{path}: decided ADR requires decision_maker")
        if not data.get("decided"):
            errors.append(f"{path}: decided ADR requires decided timestamp")
        else:
            try:
                dt.datetime.fromisoformat(
                    data["decided"].replace("Z", "+00:00")
                )
            except ValueError:
                errors.append(f"{path}: decided must be an ISO timestamp")
        if marker_names(text):
            errors.append(f"{path}: decided ADR has required placeholders")
        expected = data.get("payload_sha256", "")
        actual = adr_payload_sha256(text, data)
        if not expected:
            errors.append(f"{path}: decided ADR requires payload_sha256")
        elif expected != actual:
            errors.append(
                f"{path}: decided ADR payload changed "
                f"(expected {expected}, got {actual})"
            )
    elif strict:
        if data.get("decision_maker") or data.get("decided"):
            errors.append(f"{path}: proposed ADR cannot record a decision")
        if data.get("payload_sha256"):
            errors.append(f"{path}: proposed ADR cannot have payload_sha256")
        if marker_names(text):
            warnings.append(f"{path}: required placeholders remain")
    if data.get("schema_version") == "1.4":
        decision_outcome = data.get("decision_outcome", "")
        expected_outcome = (
            "accepted"
            if status in ADR_ACCEPTED_ORIGIN_STATUSES
            else "rejected"
            if status == "rejected"
            else ""
        )
        if decision_outcome != expected_outcome:
            errors.append(
                f"{path}: decision_outcome must be {expected_outcome!r} "
                f"for status {status!r}"
            )
        effect_values = [
            inline_text(data.get(field, ""))
            for field in (
                "effect_changed_by",
                "effect_changed",
                "effect_reason",
            )
        ]
        if any(effect_values) and not all(effect_values):
            errors.append(
                f"{path}: effect transition metadata must set actor, time, and reason"
            )
        if status in {"under_review", "retired", "superseded"} and not all(
            effect_values
        ):
            errors.append(
                f"{path}: status {status!r} requires effect transition metadata"
            )
        if status in {"proposed", "rejected"} and any(effect_values):
            errors.append(
                f"{path}: status {status!r} cannot record effect transition metadata"
            )
        if effect_values[1]:
            try:
                dt.datetime.fromisoformat(effect_values[1].replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}: effect_changed must be an ISO timestamp")
    if status == "superseded" and not superseded_by:
        errors.append(f"{path}: superseded ADR requires superseded_by")
    if status != "superseded" and superseded_by:
        errors.append(f"{path}: only superseded ADR can set superseded_by")
    return errors, warnings, data


def validate_registered_adr_revision(
    repo: Path,
    path: Path,
    *,
    document_text: str | None = None,
    expected_adr_id: str | None = None,
) -> tuple[list[str], list[str], dict[str, str], str]:
    errors: list[str] = []
    warnings: list[str] = []
    root = adr_revision_root(repo)
    try:
        relative = path.relative_to(root)
    except ValueError:
        return [f"{path}: ADR revision escapes {root}"], warnings, {}, ""
    if len(relative.parts) != 2:
        errors.append(
            f"{path}: ADR revision path must use ADR-NNN/sha256-<digest>.md"
        )
        path_adr_id = ""
        filename_digest = ""
    else:
        path_adr_id = relative.parts[0]
        filename_match = ADR_REVISION_FILE_RE.fullmatch(relative.parts[1])
        filename_digest = filename_match.group(1) if filename_match else ""
        if not ID_RE["ADR"].fullmatch(path_adr_id) or path_adr_id != path_adr_id.upper():
            errors.append(f"{path}: ADR revision directory must use canonical ADR-NNN")
        if not filename_match:
            errors.append(
                f"{path}: ADR revision filename must use sha256-<64-hex>.md"
            )
    if document_text is None:
        if path.is_symlink() or not path.is_file():
            return [*errors, f"{path}: ADR revision must be a regular file"], warnings, {}, ""
        if path.stat().st_size > ADR_REVISION_MAX_BYTES:
            return [
                *errors,
                f"{path}: ADR revision exceeds {ADR_REVISION_MAX_BYTES} bytes",
            ], warnings, {}, ""
        try:
            text = normalized_utf8_document(path.read_bytes(), str(path))
        except EpctlError as exc:
            return [*errors, str(exc)], warnings, {}, ""
    else:
        text = document_text
    try:
        _, strict = adr_document_data_from_text(path, text)
    except EpctlError as exc:
        return [*errors, f"{path}: {exc}"], warnings, {}, text
    if not strict:
        errors.append(f"{path}: registered ADR revision must use a strict schema")
    adr_errors, adr_warnings, data = validate_adr(
        path,
        historical=True,
        document_text=text,
    )
    errors.extend(adr_errors)
    warnings.extend(adr_warnings)
    adr_id = data.get("id", "")
    digest = inline_text(data.get("payload_sha256", "")).lower()
    if data.get("status") not in ADR_ACCEPTED_ORIGIN_STATUSES:
        errors.append(
            f"{path}: registered ADR revision must record an accepted decision outcome"
        )
    if path_adr_id and adr_id != path_adr_id:
        errors.append(
            f"{path}: registered ADR id {adr_id!r} does not match {path_adr_id}"
        )
    if expected_adr_id and adr_id != expected_adr_id:
        errors.append(
            f"{path}: registered ADR id {adr_id!r} does not match {expected_adr_id}"
        )
    if filename_digest and digest != filename_digest:
        errors.append(
            f"{path}: registered ADR digest {digest!r} does not match filename"
        )
    return errors, warnings, data, text


def validate_adr_revision_store(
    repo: Path,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    root = adr_revision_root(repo)
    if not root.exists():
        return errors, warnings
    if root.is_symlink() or not root.is_dir():
        return [f"{root}: ADR revision root must be a regular directory"], warnings
    for directory in sorted(root.iterdir()):
        if directory.is_symlink() or not directory.is_dir():
            errors.append(f"{directory}: ADR revision entry must be an ADR-NNN directory")
            continue
        if not ID_RE["ADR"].fullmatch(directory.name) or directory.name != directory.name.upper():
            errors.append(
                f"{directory}: ADR revision directory must use canonical ADR-NNN"
            )
            continue
        revisions = sorted(directory.iterdir())
        if not revisions:
            errors.append(f"{directory}: empty ADR revision directory")
        for path in revisions:
            item_errors, item_warnings, _, _ = validate_registered_adr_revision(
                repo,
                path,
            )
            errors.extend(item_errors)
            warnings.extend(item_warnings)
    return errors, warnings


def resolve_adr_evidence(
    repo: Path,
    adr_id: str,
    digest: str,
) -> tuple[Path, str, dict[str, str]]:
    normalized_id = normalize_reference_ids((adr_id,), "ADR")[0]
    normalized_digest = digest.lower()
    try:
        current_path = find_adr(repo, normalized_id)
    except EpctlError:
        current_path = None
    if current_path is not None:
        current_errors, _, current_data = validate_adr(
            current_path,
            historical=True,
        )
        if (
            not current_errors
            and current_data.get("status") in {"accepted", "superseded"}
            and inline_text(current_data.get("payload_sha256", "")).lower()
            == normalized_digest
        ):
            return (
                current_path,
                current_path.read_text(encoding="utf-8"),
                current_data,
            )
    revision_path = adr_revision_path(repo, normalized_id, normalized_digest)
    if not revision_path.is_file() or revision_path.is_symlink():
        raise EpctlError(
            f"historical ADR revision is not registered for "
            f"{normalized_id}@sha256:{normalized_digest}"
        )
    revision_errors, _, revision_data, revision_text = (
        validate_registered_adr_revision(
            repo,
            revision_path,
            expected_adr_id=normalized_id,
        )
    )
    if revision_errors:
        raise EpctlError(
            f"historical ADR revision is invalid for "
            f"{normalized_id}@sha256:{normalized_digest}: "
            + "; ".join(revision_errors)
        )
    return revision_path, revision_text, revision_data


def register_adr_revision(
    repo: Path,
    adr_id: str,
    *,
    source_file: str,
    git_object_id: str,
    apply: bool,
) -> dict[str, object]:
    normalized_id = normalize_reference_ids((adr_id,), "ADR")[0]

    def build_registration() -> tuple[dict[str, object], Path, str]:
        if source_file:
            text, locator = read_adr_revision_file(repo, source_file)
            source_kind = "file"
        else:
            text, locator = git_blob(repo, git_object_id)
            source_kind = "git-blob"
        try:
            data, strict = adr_document_data_from_text(
                adr_revision_root(repo) / normalized_id / "candidate.md",
                text,
            )
        except EpctlError as exc:
            raise EpctlError(f"Invalid ADR revision source: {exc}") from exc
        if not strict:
            raise EpctlError("ADR revision source must use a strict ADR schema")
        digest = inline_text(data.get("payload_sha256", "")).lower()
        target = adr_revision_path(repo, normalized_id, digest)
        item_errors, item_warnings, _, _ = validate_registered_adr_revision(
            repo,
            target,
            document_text=text,
            expected_adr_id=normalized_id,
        )
        if item_errors:
            raise EpctlError(
                "ADR revision registration blocked:\n- "
                + "\n- ".join(item_errors)
            )
        action = "create"
        if target.exists():
            reject_symlink_path(repo, target)
            existing = normalized_utf8_document(target.read_bytes(), str(target))
            if existing != text:
                raise EpctlError(
                    f"ADR revision conflict at {target}: immutable bytes differ"
                )
            action = "preserve"
        result: dict[str, object] = {
            "action": action,
            "applied": apply,
            "adr_id": normalized_id,
            "payload_sha256": digest,
            "document_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "bytes": len(text.encode("utf-8")),
            "source": {"kind": source_kind, "locator": locator},
            "target": target.relative_to(repo).as_posix(),
            "warnings": item_warnings,
        }
        return result, target, text

    if not apply:
        result, _, _ = build_registration()
        return result
    with repo_lock(repo):
        result, target, text = build_registration()
        created = False
        if result["action"] == "create":
            reject_symlink_path(repo, target)
            atomic_write(target, text)
            created = True
        post_errors, _, _, _ = validate_registered_adr_revision(repo, target)
        if post_errors:
            if created and target.is_file() and not target.is_symlink():
                target.unlink()
                if not any(target.parent.iterdir()):
                    target.parent.rmdir()
                root = adr_revision_root(repo)
                if root.is_dir() and not any(root.iterdir()):
                    root.rmdir()
            raise EpctlError(
                "ADR revision registration failed post-write validation:\n- "
                + "\n- ".join(post_errors)
            )
        return result


def validate_task(
    path: Path,
    plan_id: str,
    require_terminal: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings
    task_id = data.get("id", "")
    errors.extend(validate_common_frontmatter(path, data, "TASK"))
    if data.get("schema_version") == "1" and task_id:
        errors.extend(
            validate_metadata_contract(path, data, "task", task_id)
        )
    parent_id = data.get("parent_id") or data.get("parent")
    if parent_id != plan_id:
        errors.append(f"{path}: parent_id must be {plan_id}")
    elif "parent_id" not in data:
        warnings.append(f"{path}: legacy parent field; rename it to parent_id")
    status = data.get("status", "")
    if status not in TASK_STATUSES:
        errors.append(f"{path}: invalid task status {status!r}")
    errors.extend(validate_required_sections(path, text, TASK_SECTIONS))
    validation = checkboxes(section(text, "Validation") or "")
    if not validation:
        errors.append(f"{path}: Validation needs at least one checkbox")
    if status == "done" and validation and not all(validation):
        errors.append(f"{path}: done task has incomplete validation")
    if require_terminal and status not in {"done", "cancelled"}:
        errors.append(f"{path}: task status {status!r} blocks archive")
    if status == "done" and marker_present(text, "REQUIRED"):
        errors.append(f"{path}: required placeholders remain")
    elif marker_present(text, "REQUIRED"):
        warnings.append(f"{path}: required placeholders remain")
    blockers = unresolved_blockers(text)
    errors.extend(validate_blocker_table(path, text))
    errors.extend(
        validate_blocked_state(
            path,
            status,
            blockers,
            {"todo", "in_progress", "blocked"},
        )
    )
    blocked_by = {
        f"BLK-{int(number):03d}"
        for number in BLOCKER_ID_RE.findall(data.get("blocked_by", ""))
    }
    open_blockers = {blocker.upper() for blocker in blockers}
    if status == "blocked" and blocked_by != open_blockers:
        errors.append(
            f"{path}: blocked_by must exactly list open blockers "
            f"({', '.join(sorted(open_blockers)) or 'none'})"
        )
    elif status != "blocked" and blocked_by:
        errors.append(f"{path}: blocked_by must be empty unless status is blocked")
    return errors, warnings


def validate_checkpoint(
    path: Path,
    plan_id: str,
) -> tuple[list[str], list[str], dict[str, str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings, {}
    checkpoint_id = data.get("id", "")
    match = ID_RE["CP"].fullmatch(checkpoint_id)
    if not match:
        errors.append(f"{path}: invalid checkpoint id {checkpoint_id!r}")
    else:
        path_number = path_id_number(path, "CP")
        if path_number is None or path_number != int(match.group(1)):
            errors.append(
                f"{path}: frontmatter id {checkpoint_id} does not match path"
            )
    checkpoint_schema = data.get("schema_version", "")
    if checkpoint_schema not in {"1", "1.1", "1.2"}:
        errors.append(
            f"{path}: checkpoint schema_version must be 1, 1.1 or 1.2"
        )
    if checkpoint_schema in {"1.1", "1.2"} and not inline_text(
        data.get("repository_revision", "")
    ):
        errors.append(
            f"{path}: checkpoint requires repository_revision"
        )
    if data.get("parent_id") != plan_id:
        errors.append(f"{path}: parent_id must be {plan_id}")
    if data.get("status") != "sealed":
        errors.append(f"{path}: checkpoint status must be sealed")
    if not data.get("title"):
        errors.append(f"{path}: missing checkpoint title")
    previous = data.get("previous_checkpoint", "")
    if previous and not ID_RE["CP"].fullmatch(previous):
        errors.append(f"{path}: invalid previous_checkpoint {previous!r}")
    try:
        dt.date.fromisoformat(data.get("created", ""))
    except ValueError:
        errors.append(f"{path}: created must be an ISO date")
    created_at = data.get("created_at", "")
    try:
        dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: created_at must be an ISO timestamp")
    if checkpoint_schema == "1.2" and checkpoint_id:
        errors.extend(
            validate_metadata_contract(
                path,
                data,
                "checkpoint",
                checkpoint_id,
            )
        )
    errors.extend(
        validate_required_sections(path, text, CHECKPOINT_SECTIONS)
    )
    if marker_names(text):
        errors.append(f"{path}: required placeholders remain")
    expected_digest = data.get("payload_sha256", "")
    actual_digest = (
        canonical_document_sha256(text, "payload_sha256")
        if checkpoint_schema == "1.2"
        else payload_sha256(text)
    )
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        errors.append(f"{path}: invalid payload_sha256")
    elif expected_digest != actual_digest:
        errors.append(
            f"{path}: sealed checkpoint payload changed "
            f"(expected {expected_digest}, got {actual_digest})"
        )
    for heading in ("Handoff Summary", "Next Action At Checkpoint"):
        value = section(text, heading) or ""
        if is_empty_history_body(value):
            errors.append(f"{path}: ## {heading} must not be empty")
    return errors, warnings, data


def validate_plan(
    path: Path,
    archive_status: str | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    if path.name != "EXECPLAN.md":
        try:
            data, _, _ = parse_frontmatter(text)
        except EpctlError:
            return [], [f"{path}: legacy plan without v2 frontmatter; checks skipped"]
        status = data.get("status", "")
        if status and status not in PLAN_ACTIVE_STATUSES | PLAN_COMPLETED_STATUSES:
            errors.append(f"{path}: invalid legacy plan status {status!r}")
        warnings.append(f"{path}: legacy plan; v2 structural checks skipped")
        return errors, warnings
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings
    plan_id = data.get("id", "")
    errors.extend(validate_common_frontmatter(path, data, "EP"))
    schema_version = data.get("schema_version", "2.0")
    if (schema_version in {"2.7", "2.8"} or data.get("metadata_schema")) and plan_id:
        errors.extend(
            validate_metadata_contract(path, data, "exec-plan", plan_id)
        )
    required_benchmark_scenarios: list[str] | None = None
    architecture_review_required = False
    architecture_review_details: list[str] = []
    repo = repository_from_artifact(path)
    design_details: dict[str, dict[str, object]] = {}
    design_evidence: dict[str, str] = {}
    if schema_version not in {
        "2.0",
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.6",
        "2.7",
        "2.8",
    }:
        errors.append(f"{path}: unsupported schema_version {schema_version!r}")
    if schema_version in {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"}:
        errors.extend(
            validate_required_sections(path, text, EXECPLAN_V21_SECTIONS)
        )
        if "latest_checkpoint" not in data:
            errors.append(f"{path}: missing frontmatter field latest_checkpoint")
    elif schema_version == "2.0":
        warnings.append(
            f"{path}: v2.0 plan has no bounded checkpoint model; "
            "add schema_version 2.1 and ## Current Snapshot before checkpointing"
        )
    status = data.get("status", "")
    location = "completed" if "/completed/" in path.as_posix() else "active"
    historical_plan = (
        location == "completed" and status in PLAN_COMPLETED_STATUSES
    ) or archive_status == "cancelled"
    if schema_version in {"2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"}:
        errors.extend(
            validate_required_sections(path, text, EXECPLAN_V22_SECTIONS)
        )
        try:
            research_refs = parse_reference_array(
                data.get("research_refs", ""),
                "R",
                "research_refs",
            )
            adr_refs = parse_reference_array(
                data.get("adr_refs", ""),
                "ADR",
                "adr_refs",
            )
            design_refs = (
                parse_string_array(data.get("design_refs", ""), "design_refs")
                if schema_version in {"2.4", "2.5", "2.6", "2.7", "2.8"}
                else []
            )
            adr_constraint_ref_values = (
                parse_adr_constraint_array(
                    data.get("adr_constraint_refs", ""),
                    "adr_constraint_refs",
                )
                if schema_version in {"2.6", "2.7", "2.8"}
                else []
            )
            adr_evidence = (
                parse_adr_evidence(data.get("adr_evidence", ""))
                if schema_version in {"2.6", "2.7", "2.8"}
                else {}
            )
            design_evidence = (
                parse_design_evidence(data.get("design_evidence", ""))
                if schema_version == "2.8"
                else {}
            )
        except EpctlError as exc:
            errors.append(f"{path}: {exc}")
            research_refs = []
            adr_refs = []
            design_refs = []
            adr_constraint_ref_values = []
            adr_evidence = {}
            design_evidence = {}
        repo = repository_from_artifact(path)
        inputs = section(text, "Research and Architecture Inputs") or ""
        research_gate = data.get("research_gate", "")
        research_reason = inline_text(data.get("research_gate_reason", ""))
        if research_gate == "satisfied":
            if not research_refs:
                errors.append(
                    f"{path}: satisfied Research Gate requires research_refs"
                )
            if research_reason:
                errors.append(
                    f"{path}: satisfied Research Gate cannot have a skip reason"
                )
        elif research_gate == "not_required":
            if research_refs:
                errors.append(
                    f"{path}: not_required Research Gate cannot have research_refs"
                )
            if not research_reason:
                errors.append(
                    f"{path}: not_required Research Gate requires a reason"
                )
        else:
            errors.append(f"{path}: invalid research_gate {research_gate!r}")
        for research_id in research_refs:
            try:
                research_path = find_research(repo, research_id, "completed")
            except EpctlError:
                errors.append(f"{path}: missing concluded Research {research_id}")
                continue
            research_errors, _ = validate_research(research_path)
            research_data = artifact_metadata(research_path, "R")
            if research_errors or research_data.get("status") != "concluded":
                errors.append(f"{path}: {research_id} is not valid and concluded")
            if research_id not in inputs:
                errors.append(
                    f"{path}: Research and Architecture Inputs must mention "
                    f"{research_id}"
                )
        architecture_entrypoint = (
            inline_text(data.get("architecture_entrypoint", ""))
            if schema_version in {"2.4", "2.5", "2.6", "2.7", "2.8"}
            else ""
        )
        if schema_version in {"2.6", "2.7", "2.8"}:
            decision_gate = data.get("architecture_decision_gate", "")
            decision_reason = inline_text(
                data.get("architecture_decision_gate_reason", "")
            )
            if decision_gate == "satisfied":
                if not adr_refs:
                    errors.append(
                        f"{path}: satisfied Architecture Decision Gate requires "
                        "adr_refs"
                    )
                if decision_reason:
                    errors.append(
                        f"{path}: satisfied Architecture Decision Gate cannot "
                        "have a skip reason"
                    )
            elif decision_gate == "not_required":
                if not decision_reason:
                    errors.append(
                        f"{path}: not_required Architecture Decision Gate "
                        "requires a reason"
                    )
            else:
                errors.append(
                    f"{path}: invalid architecture_decision_gate "
                    f"{decision_gate!r}"
                )
            compliance = data.get("architecture_compliance", "")
            compliance_reason = inline_text(
                data.get("architecture_compliance_reason", "")
            )
            has_architecture_inputs = bool(
                adr_refs or design_refs or architecture_entrypoint
            )
            if compliance == "applicable":
                if not has_architecture_inputs:
                    errors.append(
                        f"{path}: applicable architecture compliance requires "
                        "ADR, Design Doc, or entrypoint inputs"
                    )
                if compliance_reason:
                    errors.append(
                        f"{path}: applicable architecture compliance cannot "
                        "have a not-applicable reason"
                    )
            elif compliance == "not_applicable":
                if has_architecture_inputs:
                    errors.append(
                        f"{path}: not_applicable architecture compliance "
                        "cannot have architecture inputs"
                    )
                if not compliance_reason:
                    errors.append(
                        f"{path}: not_applicable architecture compliance "
                        "requires a reason"
                    )
                if adr_constraint_ref_values or adr_evidence:
                    errors.append(
                        f"{path}: not_applicable architecture compliance "
                        "cannot have ADR constraints or evidence"
                    )
            else:
                errors.append(
                    f"{path}: invalid architecture_compliance {compliance!r}"
                )
        else:
            architecture_gate = data.get("architecture_gate", "")
            architecture_reason = inline_text(
                data.get("architecture_gate_reason", "")
            )
            if architecture_gate == "satisfied":
                if not adr_refs:
                    errors.append(
                        f"{path}: satisfied Architecture Gate requires adr_refs"
                    )
                if architecture_reason:
                    errors.append(
                        f"{path}: satisfied Architecture Gate cannot have a "
                        "skip reason"
                    )
            elif architecture_gate == "not_required":
                if adr_refs:
                    errors.append(
                        f"{path}: not_required Architecture Gate cannot have "
                        "adr_refs"
                    )
                if not architecture_reason:
                    errors.append(
                        f"{path}: not_required Architecture Gate requires a reason"
                    )
                if design_refs or architecture_entrypoint:
                    errors.append(
                        f"{path}: not_required Architecture Gate cannot have "
                        "Design Docs or an architecture entrypoint"
                    )
            else:
                errors.append(
                    f"{path}: invalid architecture_gate {architecture_gate!r}"
                )
        adr_data_by_id: dict[str, dict[str, str]] = {}
        adr_text_by_id: dict[str, str] = {}
        adr_resolution_failures: set[str] = set()
        allowed_adr_statuses = (
            ADR_ACCEPTED_ORIGIN_STATUSES if historical_plan else {"accepted"}
        )
        review_reasons = (
            []
            if historical_plan
            else architecture_review_reasons(repo, adr_refs)
        )
        review_required = bool(review_reasons)
        architecture_review_required = review_required
        architecture_review_details = review_reasons
        if review_required:
            warnings.append(
                f"{path}: architecture_review_required: "
                + "; ".join(review_reasons)
            )
        for adr_id in adr_refs:
            adr_path: Path | None = None
            adr_text = ""
            if historical_plan and adr_id in adr_evidence:
                try:
                    adr_path, adr_text, _ = resolve_adr_evidence(
                        repo,
                        adr_id,
                        adr_evidence[adr_id],
                    )
                except EpctlError as exc:
                    errors.append(
                        f"{path}: ADR evidence digest changed for {adr_id}: {exc}"
                    )
                    adr_resolution_failures.add(adr_id)
            if adr_path is None:
                try:
                    adr_path = find_adr(repo, adr_id)
                    adr_text = adr_path.read_text(encoding="utf-8")
                except EpctlError:
                    errors.append(f"{path}: missing accepted ADR {adr_id}")
                    continue
            adr_errors, _, adr_data = validate_adr(
                adr_path,
                historical=historical_plan,
                document_text=adr_text,
            )
            historically_accepted = (
                adr_decision_outcome(adr_data) == "accepted"
            )
            current_plan_adr = (
                adr_data.get("status") == "accepted"
                or (review_required and historically_accepted)
            )
            valid_for_plan = (
                historically_accepted
                if historical_plan
                else current_plan_adr
            )
            if adr_errors or not valid_for_plan:
                errors.append(
                    f"{path}: {adr_id} is not valid with status in "
                    f"{sorted(allowed_adr_statuses)}"
                )
            else:
                adr_data_by_id[adr_id] = adr_data
                adr_text_by_id[adr_id] = adr_text
            missing_research = set(
                parse_inline_ids(adr_data.get("research_refs", ""), "R")
            ) - set(research_refs)
            if missing_research:
                errors.append(
                    f"{path}: {adr_id} requires missing Research references "
                    + ", ".join(sorted(missing_research))
                )
            if adr_id not in inputs:
                errors.append(
                    f"{path}: Research and Architecture Inputs must mention {adr_id}"
                )
        if adr_data_by_id and not review_required:
            try:
                closure, closure_data = adr_input_closure(
                    repo,
                    adr_refs,
                    allowed_statuses=allowed_adr_statuses,
                    historical=historical_plan,
                    data_overrides=(
                        adr_data_by_id if historical_plan else None
                    ),
                )
            except EpctlError as exc:
                errors.append(f"{path}: {exc}")
                closure = []
                closure_data = {}
            missing_adrs = set(closure) - set(adr_refs)
            if missing_adrs:
                errors.append(
                    f"{path}: ADR set is not dependency-closed; missing "
                    + ", ".join(sorted(missing_adrs))
                )
            for adr_id, adr_data in closure_data.items():
                missing_designs = set(
                    parse_string_array(
                        adr_data.get("design_refs", ""),
                        "design_refs",
                    )
                ) - set(design_refs)
                if missing_designs:
                    errors.append(
                        f"{path}: {adr_id} requires missing Design Docs "
                        + ", ".join(sorted(missing_designs))
                    )
        elif adr_data_by_id:
            try:
                closure, closure_data = adr_input_closure(
                    repo,
                    adr_refs,
                    allowed_statuses=ADR_ACCEPTED_ORIGIN_STATUSES,
                    historical=True,
                )
            except EpctlError as exc:
                errors.append(f"{path}: {exc}")
                closure = []
                closure_data = {}
            missing_adrs = set(closure) - set(adr_refs)
            if missing_adrs:
                errors.append(
                    f"{path}: ADR set is not dependency-closed; missing "
                    + ", ".join(sorted(missing_adrs))
                )
            for adr_id, adr_data in closure_data.items():
                missing_designs = set(
                    parse_string_array(
                        adr_data.get("design_refs", ""),
                        "design_refs",
                    )
                ) - set(design_refs)
                if missing_designs:
                    errors.append(
                        f"{path}: {adr_id} requires missing Design Docs "
                        + ", ".join(sorted(missing_designs))
                    )
        design_details = {}
        if schema_version in {"2.4", "2.5", "2.6", "2.7", "2.8"}:
            if "design_refs" not in data:
                errors.append(f"{path}: missing frontmatter field design_refs")
            if "architecture_entrypoint" not in data:
                errors.append(
                    f"{path}: missing frontmatter field architecture_entrypoint"
                )
            design_details, design_errors, design_warnings = (
                validate_design_input_set(repo, design_refs)
            )
            errors.extend(f"{path}: {error}" for error in design_errors)
            warnings.extend(design_warnings)
            for design_ref in design_refs:
                if design_ref not in inputs:
                    errors.append(
                        f"{path}: Research and Architecture Inputs must mention "
                        f"{design_ref}"
                    )
            if architecture_entrypoint:
                item_errors, item_warnings = validate_design_ref(
                    repo,
                    architecture_entrypoint,
                    entrypoint=True,
                )
                errors.extend(f"{path}: {error}" for error in item_errors)
                warnings.extend(item_warnings)
                if architecture_entrypoint not in inputs:
                    errors.append(
                        f"{path}: Research and Architecture Inputs must mention "
                        f"{architecture_entrypoint}"
                    )
            if schema_version == "2.8":
                if "design_evidence" not in data:
                    errors.append(
                        f"{path}: missing frontmatter field design_evidence"
                    )
                unknown_evidence = set(design_evidence) - set(design_details)
                if unknown_evidence:
                    errors.append(
                        f"{path}: design_evidence references unlinked Designs: "
                        + ", ".join(sorted(unknown_evidence))
                    )
                for design_id, evidence_value in design_evidence.items():
                    details = design_details.get(design_id)
                    if details is None:
                        continue
                    evidence_errors = validate_design_evidence(
                        repo,
                        str(details["path"]),
                        evidence_value,
                    )
                    errors.extend(
                        f"{path}: {error}" for error in evidence_errors
                    )
                if design_evidence and not all(
                    value in inputs for value in design_evidence.values()
                ):
                    errors.append(
                        f"{path}: Research and Architecture Inputs must mention "
                        "every design_evidence pin"
                    )
        if schema_version in {"2.6", "2.7", "2.8"}:
            errors.extend(
                validate_required_sections(path, text, EXECPLAN_V26_SECTIONS)
            )
            for field in (
                "adr_constraint_refs",
                "adr_evidence",
                "architecture_decision_gate",
                "architecture_decision_gate_reason",
                "architecture_compliance",
                "architecture_compliance_reason",
            ):
                if field not in data:
                    errors.append(f"{path}: missing frontmatter field {field}")
            expected_constraint_refs: list[str] = []
            expected_matrix_refs: list[str] = []
            for adr_id in adr_refs:
                if adr_id not in adr_data_by_id:
                    continue
                constraints = adr_constraint_refs(
                    adr_text_by_id[adr_id],
                    adr_id,
                )
                if constraints:
                    expected_constraint_refs.extend(constraints)
                    expected_matrix_refs.extend(constraints)
                else:
                    expected_matrix_refs.append(adr_id)
            if not expected_matrix_refs and design_refs:
                expected_matrix_refs.extend(design_refs)
            if (
                not expected_matrix_refs
                and architecture_entrypoint
            ):
                expected_matrix_refs.append(architecture_entrypoint)
            if not historical_plan and not review_required:
                try:
                    scoped_amendments = current_constraint_amendments(
                        repo,
                        expected_constraint_refs,
                    )
                except EpctlError as exc:
                    errors.append(f"{path}: {exc}")
                    scoped_amendments = {}
                missing_amendments = set(scoped_amendments) - set(adr_refs)
                if missing_amendments:
                    details = "; ".join(
                        f"{adr_id} (amends "
                        f"{', '.join(scoped_amendments[adr_id])})"
                        for adr_id in sorted(missing_amendments)
                    )
                    errors.append(
                        f"{path}: active EP omits current scoped amendments: "
                        + details
                    )
            if set(adr_constraint_ref_values) != set(expected_constraint_refs):
                missing = set(expected_constraint_refs) - set(
                    adr_constraint_ref_values
                )
                extra = set(adr_constraint_ref_values) - set(
                    expected_constraint_refs
                )
                details: list[str] = []
                if missing:
                    details.append("missing " + ", ".join(sorted(missing)))
                if extra:
                    details.append("unexpected " + ", ".join(sorted(extra)))
                errors.append(
                    f"{path}: adr_constraint_refs do not match referenced ADRs: "
                    + "; ".join(details)
                )
            for constraint_ref in adr_constraint_ref_values:
                if constraint_ref not in inputs:
                    errors.append(
                        f"{path}: Research and Architecture Inputs must mention "
                        f"{constraint_ref}"
                    )
            expected_evidence_ids = {
                adr_id
                for adr_id, adr_data in adr_data_by_id.items()
                if re.fullmatch(
                    r"[0-9a-f]{64}",
                    inline_text(adr_data.get("payload_sha256", "")),
                )
            }
            if set(adr_evidence) != expected_evidence_ids:
                missing = expected_evidence_ids - set(adr_evidence)
                extra = set(adr_evidence) - expected_evidence_ids
                details = []
                if missing:
                    details.append("missing " + ", ".join(sorted(missing)))
                if extra:
                    details.append("unexpected " + ", ".join(sorted(extra)))
                errors.append(
                    f"{path}: adr_evidence does not match sealed ADR inputs: "
                    + "; ".join(details)
                )
            for adr_id, digest in adr_evidence.items():
                adr_data = adr_data_by_id.get(adr_id)
                recorded_digest = (
                    inline_text(adr_data.get("payload_sha256", "")).lower()
                    if adr_data
                    else ""
                )
                if (
                    adr_data
                    and digest != recorded_digest
                    and adr_id not in adr_resolution_failures
                ):
                    errors.append(
                        f"{path}: ADR evidence digest changed for {adr_id}"
                    )
                evidence_ref = f"{adr_id}@sha256:{digest}"
                if evidence_ref not in inputs:
                    errors.append(
                        f"{path}: Research and Architecture Inputs must mention "
                        f"{evidence_ref}"
                    )
            matrix_rows = architecture_compliance_rows(text)
            matrix_refs: list[str] = []
            matrix_incomplete = (
                errors
                if historical_plan or archive_status == "completed"
                else warnings
            )
            for cells in matrix_rows:
                if len(cells) != 3:
                    errors.append(
                        f"{path}: Architecture Compliance Matrix rows require "
                        "3 columns"
                    )
                    continue
                reference = cells[0]
                if ADR_CONSTRAINT_RE.fullmatch(reference):
                    reference = normalize_adr_constraint_refs(
                        (reference,),
                        "Architecture Compliance Matrix",
                    )[0]
                elif ID_RE["ADR"].fullmatch(reference):
                    reference = normalize_reference_ids((reference,), "ADR")[0]
                if reference in matrix_refs:
                    errors.append(
                        f"{path}: duplicate architecture compliance row "
                        f"{reference}"
                    )
                matrix_refs.append(reference)
                for label, value in (
                    ("implementation", cells[1]),
                    ("verification", cells[2]),
                ):
                    if unresolved_contract_cell(value):
                        matrix_incomplete.append(
                            f"{path}: {reference} has unresolved {label} mapping"
                        )
            if set(matrix_refs) != set(expected_matrix_refs):
                missing = set(expected_matrix_refs) - set(matrix_refs)
                extra = set(matrix_refs) - set(expected_matrix_refs)
                details = []
                if missing:
                    details.append("missing " + ", ".join(sorted(missing)))
                if extra:
                    details.append("unexpected " + ", ".join(sorted(extra)))
                errors.append(
                    f"{path}: Architecture Compliance Matrix does not match "
                    "architecture inputs: " + "; ".join(details)
                )
    if schema_version in {"2.5", "2.6", "2.7", "2.8"}:
        errors.extend(
            validate_required_sections(path, text, EXECPLAN_V25_SECTIONS)
        )
        if "required_benchmark_scenarios" not in data:
            errors.append(
                f"{path}: missing frontmatter field "
                "required_benchmark_scenarios"
            )
        try:
            required_benchmark_scenarios = parse_reference_array(
                data.get("required_benchmark_scenarios", ""),
                "BS",
                "required_benchmark_scenarios",
            )
        except EpctlError as exc:
            errors.append(f"{path}: {exc}")
            required_benchmark_scenarios = []
        benchmark_gate_set = section(text, "Benchmark Gate Set") or ""
        for scenario_id in required_benchmark_scenarios:
            errors.extend(
                validate_benchmark_scenario_reference(
                    repository_from_artifact(path),
                    scenario_id,
                )
            )
            if scenario_id not in benchmark_gate_set:
                errors.append(
                    f"{path}: Benchmark Gate Set must mention {scenario_id}"
                )
    status = data.get("status", "")
    location = "completed" if "/completed/" in path.as_posix() else "active"
    allowed = PLAN_COMPLETED_STATUSES if location == "completed" else PLAN_ACTIVE_STATUSES
    if status not in allowed and not (
        archive_status in PLAN_COMPLETED_STATUSES and location == "active"
    ):
        errors.append(f"{path}: status {status!r} is invalid in {location}")
    errors.extend(validate_required_sections(path, text, EXECPLAN_SECTIONS))
    acceptance = checkboxes(section(text, "Validation and Acceptance") or "")
    if not acceptance:
        errors.append(f"{path}: Validation and Acceptance needs a checkbox")
    completing = archive_status == "completed" or (
        archive_status is None and status == "completed"
    )
    if completing and architecture_review_required:
        errors.append(
            f"{path}: architecture_review_required blocks completion: "
            + "; ".join(architecture_review_details)
        )
    if completing and schema_version == "2.8":
        for design_id, details in design_details.items():
            design_data = details.get("data")
            if not isinstance(design_data, dict):
                errors.append(
                    f"{path}: {design_id} has no readable Design contract"
                )
                continue
            if details.get("legacy"):
                if design_data.get("status") != "current":
                    errors.append(
                        f"{path}: legacy Design {design_id} must be current "
                        "before EP completion"
                    )
                continue
            if design_id not in design_evidence:
                errors.append(
                    f"{path}: EP completion requires approved revision "
                    f"evidence for {design_id}"
                )
    if schema_version in {"2.3", "2.4", "2.5", "2.6", "2.7", "2.8"}:
        attestation_version = schema_version
        if "verified_revision" not in data:
            errors.append(f"{path}: missing frontmatter field verified_revision")
        if "verification_evidence" not in data:
            errors.append(f"{path}: missing frontmatter field verification_evidence")
        if "archive_sha256" not in data:
            errors.append(f"{path}: missing frontmatter field archive_sha256")
        try:
            verification_evidence = parse_string_array(
                data.get("verification_evidence", ""),
                "verification_evidence",
            )
        except EpctlError as exc:
            errors.append(f"{path}: {exc}")
            verification_evidence = []
        verified_revision = inline_text(data.get("verified_revision", ""))
        if completing:
            if not verified_revision:
                errors.append(
                    f"{path}: completed v{attestation_version} plan requires "
                    "verified_revision"
                )
            if not verification_evidence:
                errors.append(
                    f"{path}: completed v{attestation_version} plan requires "
                    "verification_evidence"
                )
            errors.extend(
                validate_benchmark_evidence(
                    plan_repository(path),
                    verification_evidence,
                    verified_revision,
                    required_benchmark_scenarios,
                )
            )
        elif status in PLAN_ACTIVE_STATUSES and (
            verified_revision or verification_evidence
        ):
            errors.append(
                f"{path}: active v{attestation_version} plan cannot carry "
                "completion attestation"
            )
        sealed = (
            location == "completed"
            or archive_status in PLAN_COMPLETED_STATUSES
        )
        archive_digest = data.get("archive_sha256", "")
        if sealed:
            if not re.fullmatch(r"[0-9a-f]{64}", archive_digest):
                errors.append(
                    f"{path}: archived v{attestation_version} plan requires "
                    "archive_sha256"
                )
            else:
                try:
                    actual_archive_digest = canonical_document_sha256(
                        text,
                        "archive_sha256",
                    )
                except EpctlError as exc:
                    errors.append(f"{path}: {exc}")
                else:
                    if archive_digest != actual_archive_digest:
                        errors.append(
                            f"{path}: archived v{attestation_version} plan changed "
                            f"(expected {archive_digest}, "
                            f"got {actual_archive_digest})"
                        )
        elif archive_digest:
            errors.append(
                f"{path}: active v{attestation_version} plan cannot carry "
                "archive_sha256"
            )
    if completing and acceptance and not all(acceptance):
        errors.append(f"{path}: incomplete acceptance blocks completion")
    blockers = unresolved_blockers(text)
    errors.extend(validate_blocker_table(path, text))
    errors.extend(validate_blocked_state(path, status, blockers, PLAN_ACTIVE_STATUSES))
    if completing and blockers:
        errors.append(f"{path}: open blockers: {', '.join(blockers)}")
    required = bool(marker_names(text))
    if completing and required:
        errors.append(f"{path}: required placeholders remain")
    elif required:
        warnings.append(f"{path}: required placeholders remain")
    seen_tasks: set[str] = set()
    task_dependencies: dict[str, list[str]] = {}
    task_statuses: dict[str, str] = {}
    for task in task_files(path):
        task_errors, task_warnings = validate_task(
            task,
            plan_id,
            require_terminal=archive_status in PLAN_COMPLETED_STATUSES,
        )
        errors.extend(task_errors)
        warnings.extend(task_warnings)
        try:
            task_data, _, _ = parse_frontmatter(task.read_text(encoding="utf-8"))
        except EpctlError:
            continue
        task_id = task_data.get("id", "")
        if task_id in seen_tasks:
            errors.append(f"{task}: duplicate task id {task_id}")
        seen_tasks.add(task_id)
        task_statuses[task_id] = task_data.get("status", "")
        task_dependencies[task_id] = parse_inline_ids(
            task_data.get("depends_on", ""), "TASK"
        )
    for task_id, dependencies in task_dependencies.items():
        missing = [dependency for dependency in dependencies if dependency not in seen_tasks]
        if missing:
            errors.append(f"{path}: {task_id} depends on missing {', '.join(missing)}")
        if task_id in dependencies:
            errors.append(f"{path}: {task_id} cannot depend on itself")
        if task_statuses.get(task_id) in {"in_progress", "blocked", "done"}:
            unfinished = [
                dependency
                for dependency in dependencies
                if task_statuses.get(dependency) not in {"done", "cancelled"}
            ]
            if unfinished:
                errors.append(
                    f"{path}: {task_id} started before dependencies finished: "
                    + ", ".join(unfinished)
                )
    if has_dependency_cycle(task_dependencies):
        errors.append(f"{path}: task dependency cycle detected")
    checkpoints = checkpoint_files(path)
    previous_checkpoint = ""
    seen_checkpoints: set[str] = set()
    for checkpoint in checkpoints:
        checkpoint_errors, checkpoint_warnings, checkpoint_data = (
            validate_checkpoint(checkpoint, plan_id)
        )
        errors.extend(checkpoint_errors)
        warnings.extend(checkpoint_warnings)
        checkpoint_id = checkpoint_data.get("id", "")
        if checkpoint_id in seen_checkpoints:
            errors.append(f"{checkpoint}: duplicate checkpoint id {checkpoint_id}")
        if checkpoint_id:
            seen_checkpoints.add(checkpoint_id)
        if checkpoint_data.get("previous_checkpoint", "") != previous_checkpoint:
            errors.append(
                f"{checkpoint}: previous_checkpoint must be "
                f"{previous_checkpoint or 'empty'}"
            )
        previous_checkpoint = checkpoint_id
    latest_checkpoint = data.get("latest_checkpoint", "")
    if latest_checkpoint != previous_checkpoint:
        errors.append(
            f"{path}: latest_checkpoint must be "
            f"{previous_checkpoint or 'empty'}"
        )
    snapshot = section(text, "Current Snapshot") or ""
    if latest_checkpoint and latest_checkpoint not in snapshot:
        errors.append(
            f"{path}: Current Snapshot must link {latest_checkpoint}"
        )
    if schema_version in {
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.6",
        "2.7",
        "2.8",
    } and not re.search(
        r"(?im)^-\s+Next action:\s+\S",
        snapshot,
    ):
        errors.append(f"{path}: Current Snapshot requires a non-empty Next action")
    lifecycle = plan_lifecycle_metrics(text, status, task_statuses.values())
    completion_design_blockers = design_completion_blockers(
        repo,
        schema_version,
        design_details,
        design_evidence,
    )
    if completion_design_blockers and lifecycle["completion"] == "ready_to_archive":
        lifecycle["completion"] = "archive_blocked"
        lifecycle["completion_blockers"] = completion_design_blockers
    if status in PLAN_ACTIVE_STATUSES:
        root_lines = lifecycle["root_lines"]
        root_bytes = lifecycle["root_bytes"]
        event_count = lifecycle["live_history_events"]
        if root_bytes > ROOT_BYTE_WARNING or root_lines > ROOT_LINE_WARNING:
            warnings.append(
                f"{path}: root working set is {root_lines} lines/"
                f"{root_bytes} bytes; create a checkpoint"
            )
        elif (
            root_bytes > ROOT_BYTE_RECOMMENDATION
            or root_lines > ROOT_LINE_RECOMMENDATION
        ):
            warnings.append(
                f"{path}: root working set is {root_lines} lines/"
                f"{root_bytes} bytes; checkpoint recommended before the "
                "working set reaches its hard threshold"
            )
        if event_count > HISTORY_EVENT_WARNING:
            warnings.append(
                f"{path}: {event_count} live history events exceed "
                f"the {HISTORY_EVENT_WARNING}-event checkpoint threshold"
            )
        elif event_count > HISTORY_EVENT_RECOMMENDATION:
            warnings.append(
                f"{path}: {event_count} live history events exceed the "
                f"{HISTORY_EVENT_RECOMMENDATION}-event checkpoint "
                "recommendation"
            )
        if lifecycle["scope"] == "split_recommended":
            warnings.append(
                f"{path}: active scope has {lifecycle['milestones']} milestones "
                f"and {lifecycle['unfinished_tasks']} unfinished tasks; split "
                "independently verifiable outcomes into successor EPs"
            )
        elif lifecycle["scope"] == "scope_review":
            warnings.append(
                f"{path}: active scope has {lifecycle['milestones']} milestones "
                f"and {lifecycle['unfinished_tasks']} unfinished tasks; review "
                "whether the EP still has one completion boundary"
            )
        if lifecycle["completion"] == "ready_to_archive":
            warnings.append(
                f"{path}: plan content is ready to archive; run final "
                "verification and archive-ep with the required attestation"
            )
        elif lifecycle["completion"] == "archive_blocked":
            warnings.append(
                f"{path}: checked acceptance is not archivable; blockers: "
                + ", ".join(lifecycle["completion_blockers"])
            )
    return errors, warnings


def has_dependency_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in graph and visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def validate_bugfix(
    path: Path,
    archive_status: str | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        data, _, _ = parse_frontmatter(text)
    except EpctlError as exc:
        return [f"{path}: {exc}"], warnings
    errors.extend(validate_common_frontmatter(path, data, "BF"))
    bugfix_id = data.get("id", "")
    if data.get("schema_version") == "1" and bugfix_id:
        errors.extend(
            validate_metadata_contract(path, data, "bugfix", bugfix_id)
        )
    status = data.get("status", "")
    location = "completed" if "/completed/" in path.as_posix() else "active"
    allowed = BUGFIX_COMPLETED_STATUSES if location == "completed" else BUGFIX_ACTIVE_STATUSES
    if status not in allowed and not (
        archive_status in BUGFIX_COMPLETED_STATUSES and location == "active"
    ):
        errors.append(f"{path}: status {status!r} is invalid in {location}")
    errors.extend(validate_required_sections(path, text, BUGFIX_SECTIONS))
    verification = checkboxes(section(text, "Verification") or "")
    if not verification:
        errors.append(f"{path}: Verification needs a checkbox")
    target_status = archive_status or status
    if target_status == "fixed" and verification and not all(verification):
        errors.append(f"{path}: fixed bugfix has incomplete verification")
    if target_status == "escalated" and not data.get("linked_ep"):
        errors.append(f"{path}: escalated bugfix requires linked_ep")
    blockers = unresolved_blockers(text)
    errors.extend(validate_blocker_table(path, text))
    errors.extend(
        validate_blocked_state(
            path,
            status,
            blockers,
            BUGFIX_ACTIVE_STATUSES,
        )
    )
    if target_status in {"fixed", "escalated"} and blockers:
        errors.append(f"{path}: open blockers: {', '.join(blockers)}")
    has_required = marker_present(text, "REQUIRED")
    has_fixed_required = marker_present(text, "REQUIRED_FOR_FIXED")
    has_archive_required = marker_present(text, "REQUIRED_AT_ARCHIVE")
    if target_status == "fixed" and (
        has_required or has_fixed_required or has_archive_required
    ):
        errors.append(f"{path}: required placeholders remain")
    elif target_status in {"escalated", "cancelled"} and (
        has_required or has_archive_required
    ):
        errors.append(f"{path}: archive placeholders remain")
    elif has_required or has_fixed_required or has_archive_required:
        warnings.append(f"{path}: required placeholders remain")
    return errors, warnings


def validate_repo(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        load_config(repo)
        configured_roots = architecture_roots(repo)
    except EpctlError as exc:
        errors.append(str(exc))
        configured_roots = ()
    for root in configured_roots:
        if not root.is_dir():
            errors.append(f"{root}: registered architecture root is missing")
        elif root.is_symlink():
            errors.append(f"{root}: symbolic links are not supported")
    try:
        design_errors, design_warnings = validate_design_doc_corpus(repo)
    except EpctlError as exc:
        errors.append(str(exc))
    else:
        errors.extend(design_errors)
        warnings.extend(design_warnings)
    docs_root = repo / "docs"
    if docs_root.exists():
        for path in docs_root.rglob("*"):
            if path.is_symlink() and (
                "exec-plans" in path.parts
                or "research" in path.parts
                or "adr" in path.parts
                or "decision-views" in path.parts
                or "bugfixes" in path.parts
                or ".epctl" in path.parts
                or path.name
                in {
                    "PLANS.md",
                    "RESEARCH.md",
                    "DECISIONS.md",
                    "DECISION-VIEWS.md",
                    "BUGFIXES.md",
                }
            ):
                errors.append(f"{path}: symbolic links are not supported")
    revision_errors, revision_warnings = validate_adr_revision_store(repo)
    errors.extend(revision_errors)
    warnings.extend(revision_warnings)
    view_errors, view_warnings = validate_decision_views(repo)
    errors.extend(view_errors)
    warnings.extend(view_warnings)
    plans_index = repo / "docs" / "PLANS.md"
    research_index = repo / "docs" / "RESEARCH.md"
    decision_index = repo / "docs" / "DECISIONS.md"
    bugfix_index = repo / "docs" / "BUGFIXES.md"
    if not plans_index.is_file():
        errors.append(f"{plans_index}: missing; run init")
    if not research_index.is_file():
        message = f"{research_index}: missing; run init"
        if research_files(repo):
            errors.append(message)
        else:
            warnings.append(message)
    if not decision_index.is_file():
        message = f"{decision_index}: missing; run init"
        if adr_files(repo):
            errors.append(message)
        else:
            warnings.append(message)
    if not bugfix_index.is_file():
        errors.append(f"{bugfix_index}: missing; run init")

    seen: set[str] = set()
    plan_ids: set[str] = set()
    plan_ids_by_table = {"ACTIVE": set(), "COMPLETED": set()}
    plan_paths_by_table: dict[str, dict[str, str]] = {
        "ACTIVE": {},
        "COMPLETED": {},
    }
    plans_text = plans_index.read_text(encoding="utf-8") if plans_index.exists() else ""
    for path in plan_files(repo):
        plan_errors, plan_warnings = validate_plan(path)
        errors.extend(plan_errors)
        warnings.extend(plan_warnings)
        data = artifact_metadata(path, "EP")
        item_id = data.get("id", "")
        if item_id and item_id in seen:
            errors.append(f"{path}: duplicate plan id {item_id}")
        if item_id:
            seen.add(item_id)
            plan_ids.add(item_id)
            table = "COMPLETED" if "/completed/" in path.as_posix() else "ACTIVE"
            plan_ids_by_table[table].add(item_id)
            plan_paths_by_table[table][item_id] = path.relative_to(
                repo / "docs"
            ).as_posix()
    if "<!-- EPCTL:ACTIVE:START -->" in plans_text:
        for table in ("ACTIVE", "COMPLETED"):
            body = managed_index_body(plans_text, "EP", table)
            indexed = managed_table_ids(plans_text, "EP", table)
            expected = plan_ids_by_table[table]
            for item_id in sorted(expected - indexed):
                errors.append(
                    f"{plans_index}: {item_id} missing from {table.lower()}; "
                    "run reindex"
                )
            for item_id in sorted(indexed - expected):
                errors.append(
                    f"{plans_index}: stale {item_id} in {table.lower()}; "
                    "run reindex"
                )
            for item_id in sorted(expected & indexed):
                if plan_paths_by_table[table][item_id] not in body:
                    errors.append(
                        f"{plans_index}: stale path for {item_id}; run reindex"
                    )
    elif plans_index.exists():
        warnings.append(f"{plans_index}: no epctl managed block; run reindex")

    seen.clear()
    research_ids_by_table = {"ACTIVE": set(), "COMPLETED": set()}
    research_paths_by_table: dict[str, dict[str, str]] = {
        "ACTIVE": {},
        "COMPLETED": {},
    }
    research_text = (
        research_index.read_text(encoding="utf-8")
        if research_index.exists()
        else ""
    )
    for path in research_files(repo):
        item_errors, item_warnings = validate_research(path)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        data = artifact_metadata(path, "R")
        item_id = data.get("id", "")
        if item_id and item_id in seen:
            errors.append(f"{path}: duplicate Research id {item_id}")
        if item_id:
            seen.add(item_id)
            table = "COMPLETED" if "/completed/" in path.as_posix() else "ACTIVE"
            research_ids_by_table[table].add(item_id)
            research_paths_by_table[table][item_id] = path.relative_to(
                repo / "docs"
            ).as_posix()
    if "<!-- RCTL:ACTIVE:START -->" in research_text:
        for table in ("ACTIVE", "COMPLETED"):
            body = managed_index_body(research_text, "R", table)
            indexed = managed_table_ids(research_text, "R", table)
            expected = research_ids_by_table[table]
            for item_id in sorted(expected - indexed):
                errors.append(
                    f"{research_index}: {item_id} missing from {table.lower()}; "
                    "run reindex"
                )
            for item_id in sorted(indexed - expected):
                errors.append(
                    f"{research_index}: stale {item_id} in {table.lower()}; "
                    "run reindex"
                )
            for item_id in sorted(expected & indexed):
                if research_paths_by_table[table][item_id] not in body:
                    errors.append(
                        f"{research_index}: stale path for {item_id}; run reindex"
                    )
    elif research_index.exists():
        warnings.append(f"{research_index}: no epctl managed block; run reindex")

    seen.clear()
    adr_ids_by_table = {"ACTIVE": set(), "COMPLETED": set()}
    adr_paths_by_table: dict[str, dict[str, str]] = {
        "ACTIVE": {},
        "COMPLETED": {},
    }
    adr_data_by_id: dict[str, dict[str, str]] = {}
    decision_text = (
        decision_index.read_text(encoding="utf-8")
        if decision_index.exists()
        else ""
    )
    for path in adr_files(repo):
        item_errors, item_warnings, data = validate_adr(path)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        item_id = data.get("id", "")
        if item_id and item_id in seen:
            errors.append(f"{path}: duplicate ADR id {item_id}")
        if item_id:
            seen.add(item_id)
            adr_data_by_id[item_id] = data
            table = "ACTIVE" if data.get("status") == "proposed" else "COMPLETED"
            adr_ids_by_table[table].add(item_id)
            adr_paths_by_table[table][item_id] = path.relative_to(
                repo / "docs"
            ).as_posix()
    for item_id, data in adr_data_by_id.items():
        superseded_by = data.get("superseded_by", "")
        if superseded_by:
            target = adr_data_by_id.get(superseded_by)
            if not target:
                errors.append(f"{item_id}: superseding ADR {superseded_by} is missing")
            elif target.get("status") != "accepted":
                errors.append(
                    f"{item_id}: superseding ADR {superseded_by} must be accepted"
                )
            elif item_id not in parse_inline_ids(
                target.get("supersedes", ""),
                "ADR",
            ):
                errors.append(
                    f"{item_id}: {superseded_by} must list it in supersedes"
                )
        supersedes_ids = parse_inline_ids(data.get("supersedes", ""), "ADR")
        if supersedes_ids:
            transition_fields = (
                inline_text(data.get("effect_changed_by", "")),
                inline_text(data.get("effect_changed", "")),
                inline_text(data.get("effect_reason", "")),
            )
            if not all(transition_fields):
                message = (
                    f"{item_id}: supersession has no effect transition "
                    "actor, time, and reason on the replacement ADR"
                )
                if data.get("schema_version") == "1.4":
                    errors.append(message)
                else:
                    warnings.append(message + "; preserving legacy history")
        for old_id in supersedes_ids:
            old = adr_data_by_id.get(old_id)
            if not old:
                errors.append(f"{item_id}: superseded ADR {old_id} is missing")
            elif (
                old.get("status") != "superseded"
                or old.get("superseded_by") != item_id
            ):
                errors.append(
                    f"{item_id}: supersession backlink from {old_id} is invalid"
                )
        for relation in ("depends_on", "amends"):
            related_statuses = ADR_ACCEPTED_ORIGIN_STATUSES
            try:
                related_ids = parse_reference_array(
                    data.get(relation, ""),
                    "ADR",
                    relation,
                )
            except EpctlError:
                continue
            for related_id in related_ids:
                related = adr_data_by_id.get(related_id)
                if not related:
                    errors.append(
                        f"{item_id}: {relation} ADR {related_id} is missing"
                    )
                elif related.get("status") not in related_statuses:
                    errors.append(
                        f"{item_id}: {relation} ADR {related_id} must have "
                        f"status in {sorted(related_statuses)}"
                    )
                elif (
                    data.get("status") in {"proposed", "accepted"}
                    and related.get("status") != "accepted"
                ):
                    warnings.append(
                        f"{item_id}: architecture_review_required because "
                        f"{relation} ADR {related_id} is "
                        f"{related.get('status')!r}"
                    )

    adr_graph: dict[str, list[str]] = {}
    for item_id, data in adr_data_by_id.items():
        try:
            adr_graph[item_id] = adr_relations(data)
        except EpctlError:
            adr_graph[item_id] = []
    visited: set[str] = set()
    visiting: list[str] = []

    def visit_adr_graph(item_id: str) -> None:
        if item_id in visiting:
            cycle = " -> ".join(
                (*visiting[visiting.index(item_id) :], item_id)
            )
            errors.append(f"ADR dependency cycle: {cycle}")
            return
        if item_id in visited:
            return
        visiting.append(item_id)
        for related_id in adr_graph.get(item_id, []):
            if related_id in adr_graph:
                visit_adr_graph(related_id)
        visiting.pop()
        visited.add(item_id)

    for item_id in sorted(adr_graph):
        visit_adr_graph(item_id)
    if "<!-- ADRCTL:ACTIVE:START -->" in decision_text:
        effect_markers = tuple(
            f"<!-- ADRCTL:{table}:{boundary} -->"
            for table in ("CURRENT", "AMENDMENTS", "REVIEW")
            for boundary in ("START", "END")
        )
        has_any_effect_markers = any(
            marker in decision_text for marker in effect_markers
        )
        has_all_effect_markers = all(
            marker in decision_text for marker in effect_markers
        )
        if has_all_effect_markers:
            projection = adr_effect_projection(repo)
            for table in ("ACTIVE", "CURRENT", "REVIEW", "COMPLETED"):
                expected_items = [
                    item for item in projection if item.get("table") == table
                ]
                expected_ids = {str(item["id"]) for item in expected_items}
                indexed_ids = managed_table_ids(
                    decision_text,
                    "ADR",
                    table,
                )
                for item_id in sorted(expected_ids - indexed_ids):
                    errors.append(
                        f"{decision_index}: {item_id} missing from "
                        f"{table.lower()}; run reindex"
                    )
                for item_id in sorted(indexed_ids - expected_ids):
                    errors.append(
                        f"{decision_index}: stale {item_id} in "
                        f"{table.lower()}; run reindex"
                    )
                expected_rows = [
                    adr_index_row(repo, item)
                    for item in expected_items
                ]
                expected_body = rendered_index_body("ADR", table, expected_rows)
                if managed_index_body(decision_text, "ADR", table) != expected_body:
                    errors.append(
                        f"{decision_index}: stale {table.lower()} ADR projection; "
                        "run reindex"
                    )
            expected_amendments = rendered_index_body(
                "ADR",
                "AMENDMENTS",
                adr_amendment_index_rows(repo, projection),
            )
            if (
                managed_index_body(decision_text, "ADR", "AMENDMENTS")
                != expected_amendments
            ):
                errors.append(
                    f"{decision_index}: stale current constraint amendment "
                    "projection; run reindex"
                )
        elif has_any_effect_markers:
            errors.append(
                f"{decision_index}: incomplete ADR effect projection markers; "
                "run reindex after restoring the managed layout"
            )
        else:
            for table in ("ACTIVE", "COMPLETED"):
                body = managed_index_body(decision_text, "ADR", table)
                indexed = managed_table_ids(decision_text, "ADR", table)
                expected = adr_ids_by_table[table]
                for item_id in sorted(expected - indexed):
                    errors.append(
                        f"{decision_index}: {item_id} missing from "
                        f"{table.lower()}; run reindex"
                    )
                for item_id in sorted(indexed - expected):
                    errors.append(
                        f"{decision_index}: stale {item_id} in "
                        f"{table.lower()}; run reindex"
                    )
                for item_id in sorted(expected & indexed):
                    if adr_paths_by_table[table][item_id] not in body:
                        errors.append(
                            f"{decision_index}: stale path for {item_id}; "
                            "run reindex"
                        )
            warnings.append(
                f"{decision_index}: legacy ADR index projection; run reindex "
                "or validate --fix-index to expose effective decisions"
            )
    elif decision_index.exists():
        warnings.append(f"{decision_index}: no epctl managed block; run reindex")

    seen.clear()
    bugfix_ids: set[str] = set()
    bugfix_ids_by_table = {"ACTIVE": set(), "COMPLETED": set()}
    bugfix_paths_by_table: dict[str, dict[str, str]] = {
        "ACTIVE": {},
        "COMPLETED": {},
    }
    escalated_links: list[tuple[Path, str]] = []
    bugfix_text = bugfix_index.read_text(encoding="utf-8") if bugfix_index.exists() else ""
    for path in bugfix_files(repo):
        item_errors, item_warnings = validate_bugfix(path)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        data = artifact_metadata(path, "BF")
        item_id = data.get("id", "")
        if item_id and item_id in seen:
            errors.append(f"{path}: duplicate bugfix id {item_id}")
        if item_id:
            seen.add(item_id)
            bugfix_ids.add(item_id)
            table = "COMPLETED" if "/completed/" in path.as_posix() else "ACTIVE"
            bugfix_ids_by_table[table].add(item_id)
            bugfix_paths_by_table[table][item_id] = path.relative_to(
                repo / "docs"
            ).as_posix()
        if data.get("status") == "escalated":
            escalated_links.append((path, data.get("linked_ep", "")))
    if "<!-- BFCTL:ACTIVE:START -->" in bugfix_text:
        for table in ("ACTIVE", "COMPLETED"):
            body = managed_index_body(bugfix_text, "BF", table)
            indexed = managed_table_ids(bugfix_text, "BF", table)
            expected = bugfix_ids_by_table[table]
            for item_id in sorted(expected - indexed):
                errors.append(
                    f"{bugfix_index}: {item_id} missing from {table.lower()}; "
                    "run reindex"
                )
            for item_id in sorted(indexed - expected):
                errors.append(
                    f"{bugfix_index}: stale {item_id} in {table.lower()}; "
                    "run reindex"
                )
            for item_id in sorted(expected & indexed):
                if bugfix_paths_by_table[table][item_id] not in body:
                    errors.append(
                        f"{bugfix_index}: stale path for {item_id}; run reindex"
                    )
    elif bugfix_index.exists():
        warnings.append(f"{bugfix_index}: no epctl managed block; run reindex")
    for path, linked_ep in escalated_links:
        if linked_ep not in plan_ids:
            errors.append(f"{path}: linked plan {linked_ep!r} does not exist")

    try:
        state = load_state(repo)
    except EpctlError as exc:
        errors.append(str(exc))
    else:
        high_water = state["high_water"]
        assert isinstance(high_water, dict)
        for prefix in ("EP", "R", "ADR", "BF", "TD"):
            observed = max(scan_ids(repo, prefix), default=0)
            if int(high_water.get(prefix, 0)) < observed:
                warnings.append(
                    f"{state_path(repo)}: {prefix} high-water is stale; run reindex"
                )
    return errors, warnings


def fill_outcome_marker(
    text: str,
    heading: str,
    marker: str,
    label: str,
    reason: str,
) -> str:
    if not reason:
        return text
    entry = f"- {date_string()} — {label}: {reason}"
    pattern = rf"<!--\s*{re.escape(marker)}\s*:[\s\S]*?-->"
    replaced, count = re.subn(pattern, entry, text, count=1)
    if count:
        return replaced
    heading_pattern = rf"(?m)^(## {re.escape(heading)}\s*)$"
    if not re.search(heading_pattern, text):
        raise EpctlError(f"Missing ## {heading}")
    return re.sub(heading_pattern, rf"\1\n\n{entry}", text, count=1)


def replace_required_markers_for_cancellation(text: str, reason: str) -> str:
    replacement = f"Cancelled before completion: {inline_text(reason)}"
    return re.sub(
        r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
        replacement,
        text,
    )


def archive_research(
    repo: Path,
    research_id: str,
    outcome: str,
    reason: str,
) -> Path:
    with repo_lock(repo):
        path = find_research(repo, research_id, "active")
        if outcome not in RESEARCH_COMPLETED_STATUSES:
            raise EpctlError("Research outcome must be concluded or cancelled")
        if outcome == "cancelled" and not inline_text(reason):
            raise EpctlError("Cancelled Research requires --reason")
        text = path.read_text(encoding="utf-8")
        synthesis_path = path.parent / "SYNTHESIS.md"
        synthesis_text = synthesis_path.read_text(encoding="utf-8")
        base_errors, _ = validate_research(path)
        if base_errors:
            raise EpctlError(
                "Research archive blocked:\n- " + "\n- ".join(base_errors)
            )
        if outcome == "concluded":
            _, open_questions = validate_research_questions(path, text)
            blockers = unresolved_blockers(text)
            if open_questions:
                raise EpctlError(
                    f"Research conclusion blocked by {open_questions} open questions"
                )
            if blockers:
                raise EpctlError(
                    "Research conclusion blocked by open blockers: "
                    + ", ".join(blockers)
                )
            if marker_names(text) or marker_names(synthesis_text):
                raise EpctlError(
                    "Research conclusion blocked by required placeholders"
                )
            synthesis_candidate = update_frontmatter(
                synthesis_text,
                {
                    "status": "sealed",
                    "updated": date_string(),
                },
            )
            synthesis_candidate = update_frontmatter(
                synthesis_candidate,
                {"payload_sha256": payload_sha256(synthesis_candidate)},
            )
            outcome_body = (
                f"- {date_string()} — Concluded with sealed "
                "`SYNTHESIS.md`; downstream decisions must cite its evidence."
            )
            research_candidate = replace_section(text, "Outcome", outcome_body)
        else:
            synthesis_candidate = replace_required_markers_for_cancellation(
                synthesis_text,
                reason,
            )
            outcome_body = (
                f"- {date_string()} — Cancelled: {inline_text(reason)}"
            )
            research_candidate = replace_required_markers_for_cancellation(
                text,
                reason,
            )
            research_candidate = replace_section(
                research_candidate,
                "Outcome",
                outcome_body,
            )
        research_candidate = update_frontmatter(
            research_candidate,
            {
                "status": outcome,
                "updated": date_string(),
            },
        )
        container = path.parent
        destination = repo / "docs" / "research" / "completed" / container.name
        reject_symlink_path(repo, destination)
        if destination.exists():
            raise EpctlError(f"Archive destination exists: {destination}")
        research_candidate = research_candidate.replace(
            f"docs/research/active/{container.name}",
            f"docs/research/completed/{container.name}",
        )
        snapshots = managed_index_snapshots(repo)
        try:
            atomic_write(path, research_candidate)
            atomic_write(synthesis_path, synthesis_candidate)
            post_errors, _ = validate_research(path, archive_status=outcome)
            if post_errors:
                raise EpctlError(
                    "Research archive produced invalid artifacts:\n- "
                    + "\n- ".join(post_errors)
                )
            os.replace(container, destination)
            rebuild_indexes(repo)
        except Exception:
            if destination.exists() and not container.exists():
                os.replace(destination, container)
            atomic_write(path, text)
            atomic_write(synthesis_path, synthesis_text)
            restore_managed_indexes(snapshots)
            raise
        return destination / "RESEARCH.md"


def decide_adr(
    repo: Path,
    adr_id: str,
    outcome: str,
    decision_maker: str,
) -> Path:
    with repo_lock(repo):
        if outcome not in {"accepted", "rejected"}:
            raise EpctlError("ADR outcome must be accepted or rejected")
        maker = inline_text(decision_maker)
        if not maker:
            raise EpctlError("ADR decision requires --decision-maker")
        path = find_adr(repo, adr_id)
        text = path.read_text(encoding="utf-8")
        errors, _, data = validate_adr(path)
        if errors:
            raise EpctlError("ADR decision blocked:\n- " + "\n- ".join(errors))
        if data.get("status") != "proposed":
            raise EpctlError("Only a proposed ADR can be decided")
        if marker_names(text):
            raise EpctlError("ADR decision blocked by required placeholders")
        candidate = update_frontmatter(
            text,
            {
                "status": outcome,
                "decision_maker": json.dumps(maker, ensure_ascii=False),
                "decided": json.dumps(timestamp_string()),
                "decision_outcome": outcome,
                "updated": date_string(),
            },
        )
        candidate = update_frontmatter(
            candidate,
            {
                "payload_sha256": adr_payload_sha256(
                    candidate,
                    parse_frontmatter(candidate)[0],
                )
            },
        )
        snapshots = managed_index_snapshots(repo)
        try:
            atomic_write(path, candidate)
            post_errors, _, _ = validate_adr(path)
            if post_errors:
                raise EpctlError(
                    "ADR decision produced invalid artifact:\n- "
                    + "\n- ".join(post_errors)
                )
            rebuild_indexes(repo)
        except Exception:
            atomic_write(path, text)
            restore_managed_indexes(snapshots)
            raise
        return path


def adr_effect_updates(
    data: dict[str, str],
    target_status: str,
    decision_maker: str,
    reason: str,
) -> dict[str, str]:
    updates = {
        "status": target_status,
        "effect_changed_by": json.dumps(decision_maker, ensure_ascii=False),
        "effect_changed": json.dumps(timestamp_string()),
        "effect_reason": json.dumps(reason, ensure_ascii=False),
    }
    if data.get("schema_version") == "1.4":
        updates["updated"] = date_string()
    return updates


def adr_effect_impact(
    repo: Path,
    adr_id: str,
    from_status: str,
    to_status: str,
    *,
    replacement: str = "",
    apply: bool = False,
    no_op: bool = False,
) -> dict[str, object]:
    corpus = adr_corpus_data(repo)
    affected: set[str] = {adr_id}
    changed = True
    while changed:
        changed = False
        for item_id, data in corpus.items():
            if item_id in affected:
                continue
            try:
                relations = set(adr_relations(data))
            except EpctlError:
                relations = set()
            if relations & affected:
                affected.add(item_id)
                changed = True
    constraints: set[str] = set()
    for item_id in affected:
        try:
            path = find_adr(repo, item_id)
            constraints.update(
                adr_constraint_refs(
                    path.read_text(encoding="utf-8"),
                    item_id,
                )
            )
        except EpctlError:
            continue
    active_plans: list[str] = []
    for path in plan_files(repo, "active"):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            plan_adrs = set(
                parse_reference_array(data.get("adr_refs", "[]"), "ADR", "adr_refs")
            )
        except EpctlError:
            continue
        if plan_adrs & affected:
            active_plans.append(data.get("id", path.stem))
    actions = [
        find_adr(repo, adr_id).relative_to(repo).as_posix(),
        "docs/DECISIONS.md",
    ]
    if replacement:
        actions.insert(1, find_adr(repo, replacement).relative_to(repo).as_posix())
    return {
        "mode": "apply" if apply else "preview",
        "adr_id": adr_id,
        "from_status": from_status,
        "to_status": to_status,
        "replacement": replacement or None,
        "affected_constraints": sorted(constraints),
        "affected_adrs": sorted(affected - {adr_id}),
        "affected_active_plans": sorted(active_plans),
        "actions": [] if no_op else actions,
        "warnings": [
            "Implementation and active ExecPlans are not modified automatically."
        ],
        "no_op": no_op,
    }


def validate_effect_authority(
    decision_maker: str,
    reason: str,
) -> tuple[str, str]:
    maker = inline_text(decision_maker)
    rationale = inline_text(reason)
    if not maker:
        raise EpctlError("ADR effect change requires --decision-maker")
    if not rationale:
        raise EpctlError("ADR effect change requires --reason")
    return maker, rationale


def transition_adr(
    repo: Path,
    adr_id: str,
    target_status: str,
    decision_maker: str,
    reason: str,
    apply: bool,
) -> dict[str, object]:
    maker, rationale = validate_effect_authority(decision_maker, reason)
    target = inline_text(target_status).lower()
    if target not in {"accepted", "under_review", "retired"}:
        raise EpctlError(
            "ADR effect target must be accepted, under_review or retired"
        )
    normalized = normalize_reference_ids((adr_id,), "ADR")[0]

    def prepare() -> tuple[Path, str, dict[str, str], dict[str, object]]:
        path = find_adr(repo, normalized)
        text = path.read_text(encoding="utf-8")
        errors, _, data = validate_adr(path)
        if errors:
            raise EpctlError("ADR transition blocked:\n- " + "\n- ".join(errors))
        source = data.get("status", "")
        no_op = source == target
        if no_op:
            if source not in {"accepted", "under_review", "retired"}:
                raise EpctlError(f"{normalized} cannot transition from {source!r}")
        elif target not in ADR_TRANSITIONS.get(source, set()):
            raise EpctlError(
                f"Illegal ADR effect transition: {source} -> {target}"
            )
        impact = adr_effect_impact(
            repo,
            normalized,
            source,
            target,
            apply=apply,
            no_op=no_op,
        )
        return path, text, data, impact

    if not apply:
        return prepare()[3]
    with repo_lock(repo):
        path, text, data, impact = prepare()
        if impact["no_op"]:
            return impact
        candidate = update_adr_frontmatter(
            text,
            data,
            adr_effect_updates(data, target, maker, rationale),
        )
        snapshots = managed_index_snapshots(repo)
        try:
            atomic_write(path, candidate)
            post_errors, _, _ = validate_adr(path)
            if post_errors:
                raise EpctlError(
                    "ADR transition produced invalid artifact:\n- "
                    + "\n- ".join(post_errors)
                )
            rebuild_indexes(repo)
            repo_errors, _ = validate_repo(repo)
            if repo_errors:
                raise EpctlError(
                    "ADR transition produced an invalid repository:\n- "
                    + "\n- ".join(repo_errors)
                )
        except Exception:
            atomic_write(path, text)
            restore_managed_indexes(snapshots)
            raise
        return impact


def supersede_adr(
    repo: Path,
    old_adr_id: str,
    new_adr_id: str,
    decision_maker: str,
    reason: str,
    apply: bool,
) -> dict[str, object]:
    maker, rationale = validate_effect_authority(decision_maker, reason)
    old_id = normalize_reference_ids((old_adr_id,), "ADR")[0]
    new_id = normalize_reference_ids((new_adr_id,), "ADR")[0]
    if old_id == new_id:
        raise EpctlError("An ADR cannot supersede itself")

    def prepare() -> tuple[
        Path,
        Path,
        str,
        str,
        dict[str, str],
        dict[str, str],
        dict[str, object],
    ]:
        old_path = find_adr(repo, old_id)
        new_path = find_adr(repo, new_id)
        old_text = old_path.read_text(encoding="utf-8")
        new_text = new_path.read_text(encoding="utf-8")
        old_errors, _, old_data = validate_adr(old_path)
        new_errors, _, new_data = validate_adr(new_path)
        if old_errors or new_errors:
            raise EpctlError(
                "ADR supersession blocked:\n- "
                + "\n- ".join((*old_errors, *new_errors))
            )
        existing_replacement = old_data.get("superseded_by", "")
        no_op = old_data.get("status") == "superseded" and existing_replacement == new_id
        if not no_op and old_data.get("status") not in {"accepted", "under_review"}:
            raise EpctlError(
                f"{old_id} must be accepted or under_review before supersession"
            )
        new_current, new_reasons = adr_currentness(repo, new_id)
        if not new_current:
            raise EpctlError(
                f"{new_id} must be valid, accepted and current: "
                + "; ".join(new_reasons)
            )
        impact = adr_effect_impact(
            repo,
            old_id,
            old_data.get("status", ""),
            "superseded",
            replacement=new_id,
            apply=apply,
            no_op=no_op,
        )
        return (
            old_path,
            new_path,
            old_text,
            new_text,
            old_data,
            new_data,
            impact,
        )

    if not apply:
        return prepare()[-1]
    with repo_lock(repo):
        (
            old_path,
            new_path,
            old_text,
            new_text,
            old_data,
            new_data,
            impact,
        ) = prepare()
        if impact["no_op"]:
            return impact
        supersedes = parse_reference_array(
            new_data.get("supersedes", ""),
            "ADR",
            "supersedes",
        )
        if old_id not in supersedes:
            supersedes.append(old_id)
        transition_time = timestamp_string()
        old_updates = adr_effect_updates(
            old_data,
            "superseded",
            maker,
            rationale,
        )
        old_updates["effect_changed"] = json.dumps(transition_time)
        old_updates["superseded_by"] = new_id
        new_updates = {
            "supersedes": json.dumps(supersedes),
            "effect_changed_by": json.dumps(maker, ensure_ascii=False),
            "effect_changed": json.dumps(transition_time),
            "effect_reason": json.dumps(rationale, ensure_ascii=False),
        }
        if new_data.get("schema_version") == "1.4":
            new_updates["updated"] = date_string()
        old_candidate = update_adr_frontmatter(old_text, old_data, old_updates)
        new_candidate = update_adr_frontmatter(new_text, new_data, new_updates)
        snapshots = managed_index_snapshots(repo)
        try:
            atomic_write(old_path, old_candidate)
            atomic_write(new_path, new_candidate)
            old_post, _, _ = validate_adr(old_path)
            new_post, _, _ = validate_adr(new_path)
            if old_post or new_post:
                raise EpctlError(
                    "ADR supersession produced invalid artifacts:\n- "
                    + "\n- ".join((*old_post, *new_post))
                )
            rebuild_indexes(repo)
            repo_errors, _ = validate_repo(repo)
            if repo_errors:
                raise EpctlError(
                    "ADR supersession produced an invalid repository:\n- "
                    + "\n- ".join(repo_errors)
                )
        except Exception:
            atomic_write(old_path, old_text)
            atomic_write(new_path, new_text)
            restore_managed_indexes(snapshots)
            raise
        return impact


def archive_ep(
    repo: Path,
    plan_id: str,
    outcome: str,
    reason: str,
    verified_revision: str,
    evidence: Iterable[str],
) -> Path:
    with repo_lock(repo):
        path = find_plan(repo, plan_id, "active")
        if path.name != "EXECPLAN.md":
            raise EpctlError(
                "archive-ep requires a v2 EXECPLAN.md; "
                "migrate legacy plans explicitly"
            )
        if outcome not in PLAN_COMPLETED_STATUSES:
            raise EpctlError("EP outcome must be completed or cancelled")
        if outcome == "cancelled" and not reason.strip():
            raise EpctlError("Cancelled EP requires --reason")
        verified_revision = inline_text(verified_revision)
        verification_evidence = [inline_text(item) for item in evidence]
        if any(not item for item in verification_evidence):
            raise EpctlError("--evidence cannot be empty")
        if len(set(verification_evidence)) != len(verification_evidence):
            raise EpctlError("--evidence values must be unique")
        if outcome == "cancelled" and (
            verified_revision or verification_evidence
        ):
            raise EpctlError(
                "--verified-revision and --evidence are valid only "
                "for completed EPs"
            )
        text = path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
        schema_version = data.get("schema_version")
        has_completion_attestation = schema_version in {
            "2.3",
            "2.4",
            "2.5",
            "2.6",
            "2.7",
            "2.8",
        }
        if outcome == "completed" and has_completion_attestation:
            if not verified_revision:
                raise EpctlError(
                    "Completed v2.3+ EP requires --verified-revision"
                )
            if not verification_evidence:
                raise EpctlError(
                    "Completed v2.3+ EP requires at least one --evidence"
                )
            required_benchmark_scenarios: list[str] | None = None
            if schema_version in {"2.5", "2.6", "2.7", "2.8"}:
                required_benchmark_scenarios = parse_reference_array(
                    data.get("required_benchmark_scenarios", ""),
                    "BS",
                    "required_benchmark_scenarios",
                )
            benchmark_errors = validate_benchmark_evidence(
                repo,
                verification_evidence,
                verified_revision,
                required_benchmark_scenarios,
            )
            if benchmark_errors:
                raise EpctlError(
                    "Benchmark evidence is invalid:\n- "
                    + "\n- ".join(benchmark_errors)
                )
        container = path.parent
        destination = repo / "docs" / "exec-plans" / "completed" / container.name
        reject_symlink_path(repo, destination)
        if destination.exists():
            raise EpctlError(f"Archive destination exists: {destination}")
        updates = {"status": outcome, "updated": date_string()}
        if has_completion_attestation and outcome == "completed":
            updates["verified_revision"] = json.dumps(
                verified_revision,
                ensure_ascii=False,
            )
            updates["verification_evidence"] = json.dumps(
                verification_evidence,
                ensure_ascii=False,
            )
        if has_completion_attestation:
            updates["archive_sha256"] = ""
        new_text = update_frontmatter(text, updates).replace(
            f"docs/exec-plans/active/{container.name}",
            f"docs/exec-plans/completed/{container.name}",
        )
        if outcome == "cancelled":
            new_text = fill_outcome_marker(
                new_text,
                "Outcomes & Retrospective",
                "REQUIRED_AT_COMPLETION",
                "Cancelled",
                reason.strip(),
            )
        if has_completion_attestation:
            archive_digest = canonical_document_sha256(
                new_text,
                "archive_sha256",
            )
            new_text = update_frontmatter(
                new_text,
                {"archive_sha256": archive_digest},
            )
        snapshots = managed_index_snapshots(repo)
        atomic_write(path, new_text)
        errors, _ = validate_plan(path, archive_status=outcome)
        if errors:
            atomic_write(path, text)
            raise EpctlError("Archive blocked:\n- " + "\n- ".join(errors))
        try:
            os.replace(container, destination)
            rebuild_indexes(repo)
        except Exception:
            if destination.exists() and not container.exists():
                os.replace(destination, container)
            atomic_write(path, text)
            restore_managed_indexes(snapshots)
            raise
        return destination / "EXECPLAN.md"


def archive_bugfix(
    repo: Path,
    bugfix_id: str,
    outcome: str,
    reason: str,
    linked_ep: str,
) -> Path:
    with repo_lock(repo):
        path = find_bugfix(repo, bugfix_id, "active")
        if outcome not in BUGFIX_COMPLETED_STATUSES:
            raise EpctlError(
                "Bugfix outcome must be fixed, escalated or cancelled"
            )
        if outcome in {"escalated", "cancelled"} and not reason.strip():
            raise EpctlError(f"{outcome} bugfix requires --reason")
        if outcome == "escalated":
            if not linked_ep:
                raise EpctlError("Escalated bugfix requires --linked-ep")
            linked_ep = linked_ep.upper()
            find_plan(repo, linked_ep)
        elif linked_ep:
            raise EpctlError("--linked-ep is valid only for escalated bugfixes")

        text = path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
        updates = {"status": outcome, "updated": date_string()}
        if linked_ep:
            updates["linked_ep"] = linked_ep
        new_text = update_frontmatter(text, updates)
        if reason.strip():
            new_text = fill_outcome_marker(
                new_text,
                "Outcome",
                "REQUIRED_AT_ARCHIVE",
                outcome.capitalize(),
                reason.strip(),
            )
        destination = repo / "docs" / "bugfixes" / "completed" / path.name
        reject_symlink_path(repo, destination)
        if destination.exists():
            raise EpctlError(f"Archive destination exists: {destination}")

        snapshots = managed_index_snapshots(repo)
        atomic_write(path, new_text)
        errors, _ = validate_bugfix(path, archive_status=outcome)
        if errors:
            atomic_write(path, text)
            raise EpctlError("Archive blocked:\n- " + "\n- ".join(errors))
        try:
            os.replace(path, destination)
            rebuild_indexes(repo)
        except Exception:
            if destination.exists() and not path.exists():
                os.replace(destination, path)
            atomic_write(path, text)
            restore_managed_indexes(snapshots)
            raise
        return destination


def last_activity(text: str, data: dict[str, str]) -> str:
    candidates = re.findall(
        r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?",
        text,
    )
    candidates.extend(
        value
        for key in ("created", "updated")
        if (value := data.get(key, ""))
    )
    return max(candidates, default="")


def status_rows(repo: Path) -> dict[str, list[dict[str, object]]]:
    research: list[dict[str, object]] = []
    for path in research_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
            data, _, _ = parse_frontmatter(text)
        except EpctlError:
            continue
        _, open_questions = validate_research_questions(path, text)
        synthesis_status = ""
        synthesis_path = path.parent / "SYNTHESIS.md"
        if synthesis_path.is_file():
            try:
                synthesis_data, _, _ = parse_frontmatter(
                    synthesis_path.read_text(encoding="utf-8")
                )
                synthesis_status = synthesis_data.get("status", "")
            except EpctlError:
                synthesis_status = "invalid"
        research.append(
            {
                "id": data.get("id", ""),
                "title": data.get("title", ""),
                "status": data.get("status", ""),
                "synthesis_status": synthesis_status,
                "open_questions": open_questions,
                "open_blockers": len(unresolved_blockers(text)),
                "root_lines": len(text.splitlines()),
                "root_bytes": len(text.encode("utf-8")),
                "last_activity": last_activity(text, data),
                "path": path.relative_to(repo).as_posix(),
            }
        )
    adr_projection_by_id = {
        str(item["id"]): item for item in adr_effect_projection(repo)
    }
    adrs: list[dict[str, object]] = []
    for path in adr_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
            data, strict = adr_document_data(path)
        except EpctlError:
            continue
        projected = adr_projection_by_id.get(data.get("id", ""), {})
        adrs.append(
            {
                "id": data.get("id", ""),
                "title": data.get("title", ""),
                "status": data.get("status", ""),
                "research_refs": parse_inline_ids(
                    data.get("research_refs", ""),
                    "R",
                ),
                "decision_maker": data.get("decision_maker", ""),
                "depends_on": parse_inline_ids(data.get("depends_on", ""), "ADR"),
                "amends": parse_inline_ids(data.get("amends", ""), "ADR"),
                "amends_constraints": parse_string_array(
                    data.get("amends_constraints", "[]"),
                    "amends_constraints",
                ),
                "constraints": adr_constraint_refs(
                    text,
                    data.get("id", ""),
                ),
                "design_refs": parse_string_array(
                    data.get("design_refs", ""),
                    "design_refs",
                ),
                "contract": "strict" if strict else "legacy-linked",
                "superseded_by": data.get("superseded_by", ""),
                "decision_outcome": adr_decision_outcome(data),
                "projection": projected.get("projection", "unknown"),
                "effect": projected.get("effect", data.get("status", "unknown")),
                "current": projected.get("current", False),
                "amended_by": projected.get("amended_by", []),
                "review_reasons": projected.get("review_reasons", []),
                "last_activity": last_activity(text, data),
                "path": path.relative_to(repo).as_posix(),
            }
        )
    plans: list[dict[str, object]] = []
    for path in plan_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
            data, _, _ = parse_frontmatter(text)
        except EpctlError:
            continue
        acceptance = checkboxes(section(text, "Validation and Acceptance") or "")
        try:
            benchmark_scenarios = parse_reference_array(
                data.get("required_benchmark_scenarios", "[]"),
                "BS",
                "required_benchmark_scenarios",
            )
        except EpctlError:
            benchmark_scenarios = []
        tasks = []
        for task in task_files(path):
            try:
                task_data, _, _ = parse_frontmatter(task.read_text(encoding="utf-8"))
            except EpctlError:
                continue
            tasks.append(task_data.get("status", "unknown"))
        lifecycle = plan_lifecycle_metrics(
            text,
            data.get("status", ""),
            tasks,
        )
        archive_inputs = (
            ["verified_revision", "verification_evidence"]
            if data.get("status", "") in PLAN_ACTIVE_STATUSES
            and data.get("schema_version", "")
            in {"2.3", "2.4", "2.5", "2.6", "2.7", "2.8"}
            else []
        )
        decision_gate = data.get(
            "architecture_decision_gate",
            data.get("architecture_gate", "legacy"),
        )
        architecture_compliance = data.get(
            "architecture_compliance",
            (
                "applicable"
                if data.get("architecture_gate") == "satisfied"
                else "not_applicable"
                if data.get("architecture_gate") == "not_required"
                else "legacy"
            ),
        )
        plan_adr_refs = parse_inline_ids(data.get("adr_refs", ""), "ADR")
        review_reasons = (
            architecture_review_reasons(repo, plan_adr_refs)
            if data.get("status", "") in PLAN_ACTIVE_STATUSES
            else []
        )
        if review_reasons:
            lifecycle["completion"] = "archive_blocked"
            lifecycle["completion_blockers"] = list(
                dict.fromkeys(
                    [
                        *lifecycle["completion_blockers"],
                        "architecture_review_required",
                    ]
                )
            )
        if (
            lifecycle["completion"] == "ready_to_archive"
            and data.get("schema_version", "") == "2.8"
        ):
            try:
                status_design_refs = parse_string_array(
                    data.get("design_refs", ""),
                    "design_refs",
                )
                status_design_evidence = parse_design_evidence(
                    data.get("design_evidence", "")
                )
                status_design_details, status_design_errors, _ = (
                    validate_design_input_set(repo, status_design_refs)
                )
                if set(status_design_evidence) - set(status_design_details):
                    status_design_errors.append(
                        "design_evidence references an unlinked Design"
                    )
                status_design_blockers = design_completion_blockers(
                    repo,
                    "2.8",
                    status_design_details,
                    status_design_evidence,
                )
                if status_design_errors:
                    status_design_blockers.insert(0, "design_inputs_invalid")
            except EpctlError:
                status_design_blockers = ["design_inputs_invalid"]
            if status_design_blockers:
                lifecycle["completion"] = "archive_blocked"
                lifecycle["completion_blockers"] = list(
                    dict.fromkeys(status_design_blockers)
                )
        plans.append(
            {
                "id": data.get("id", ""),
                "title": data.get("title", ""),
                "status": data.get("status", ""),
                "research_gate": data.get("research_gate", "legacy"),
                "architecture_gate": decision_gate,
                "architecture_decision_gate": decision_gate,
                "architecture_compliance": architecture_compliance,
                "adr_refs": plan_adr_refs,
                "adr_constraint_refs": parse_string_array(
                    data.get("adr_constraint_refs", "[]"),
                    "adr_constraint_refs",
                ),
                "adr_evidence": parse_string_array(
                    data.get("adr_evidence", "[]"),
                    "adr_evidence",
                ),
                "design_refs": parse_string_array(
                    data.get("design_refs", ""),
                    "design_refs",
                ),
                "architecture_entrypoint": data.get(
                    "architecture_entrypoint",
                    "",
                ),
                "architecture_review_required": bool(review_reasons),
                "architecture_review_reasons": review_reasons,
                "benchmark_scenarios": benchmark_scenarios,
                "acceptance": f"{sum(acceptance)}/{len(acceptance)}",
                "tasks": f"{sum(s in {'done', 'cancelled'} for s in tasks)}/{len(tasks)}"
                if tasks
                else "—",
                "open_blockers": len(unresolved_blockers(text)),
                "completion": lifecycle["completion"],
                "completion_blockers": lifecycle["completion_blockers"],
                "archive_inputs_required": archive_inputs,
                "working_set": lifecycle["working_set"],
                "scope": lifecycle["scope"],
                "latest_checkpoint": data.get("latest_checkpoint", ""),
                "checkpoints": len(checkpoint_files(path)),
                "root_lines": lifecycle["root_lines"],
                "root_bytes": lifecycle["root_bytes"],
                "live_history_events": lifecycle["live_history_events"],
                "milestones": lifecycle["milestones"],
                "unfinished_tasks": lifecycle["unfinished_tasks"],
                "last_activity": last_activity(text, data),
                "path": path.relative_to(repo).as_posix(),
            }
        )
    bugfixes: list[dict[str, object]] = []
    for path in bugfix_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
            data, _, _ = parse_frontmatter(text)
        except EpctlError:
            continue
        bugfixes.append(
            {
                "id": data.get("id", ""),
                "title": data.get("title", ""),
                "area": data.get("area", ""),
                "status": data.get("status", ""),
                "linked_ep": data.get("linked_ep", ""),
                "open_blockers": len(unresolved_blockers(text)),
                "last_activity": last_activity(text, data),
                "path": path.relative_to(repo).as_posix(),
            }
        )
    research.sort(key=lambda row: str(row["id"]))
    adrs.sort(key=lambda row: str(row["id"]))
    plans.sort(key=lambda row: str(row["id"]))
    bugfixes.sort(key=lambda row: str(row["id"]))
    return {
        "research": research,
        "adrs": adrs,
        "plans": plans,
        "bugfixes": bugfixes,
    }


def print_status(repo: Path, as_json: bool) -> None:
    payload = status_rows(repo)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(
        "| Research | Title | Status | Synthesis | Open questions | "
        "Open blockers | Root | Last activity |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for row in payload["research"]:
        print(
            f"| {row['id']} | {md_cell(str(row['title']))} | {row['status']} | "
            f"{row['synthesis_status'] or '—'} | {row['open_questions']} | "
            f"{row['open_blockers']} | "
            f"{row['root_lines']}L/{row['root_bytes']}B | "
            f"{row['last_activity']} |"
        )
    print()
    print(
        "| ADR | Title | Status | Decision | Effect | Current | Amended by | "
        "Relations | Constraints | Research | Designs | Contract | Decision maker | "
        "Superseded by | Last activity |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in payload["adrs"]:
        relations = [
            *(f"depends:{item}" for item in row["depends_on"]),
            *(f"amends:{item}" for item in row["amends"]),
        ]
        print(
            f"| {row['id']} | {md_cell(str(row['title']))} | {row['status']} | "
            f"{row['decision_outcome'] or 'pending'} | "
            f"{str(row['effect']).replace('_', ' ')} | "
            f"{'yes' if row['current'] else 'no'} | "
            f"{md_cell(', '.join(row['amended_by']) or '—')} | "
            f"{md_cell(', '.join(relations) or '—')} | "
            f"{len(row['constraints']) or '—'} | "
            f"{md_cell(', '.join(row['research_refs']) or '—')} | "
            f"{len(row['design_refs']) or '—'} | {row['contract']} | "
            f"{md_cell(str(row['decision_maker']) or '—')} | "
            f"{row['superseded_by'] or '—'} | {row['last_activity']} |"
        )
    print()
    print(
        "| EP | Title | Status | Completion | Scope | Working set | "
        "Gates (R/Decision/Compliance/Benchmark) | Acceptance | Tasks | Open blockers | "
        "Checkpoint | Root | Events | Last activity |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in payload["plans"]:
        print(
            f"| {row['id']} | {md_cell(str(row['title']))} | {row['status']} | "
            f"{row['completion']} | {row['scope']} | {row['working_set']} | "
            f"{row['research_gate']}/{row['architecture_decision_gate']}/"
            f"{row['architecture_compliance']}/"
            f"{len(row['benchmark_scenarios'])} | "
            f"{row['acceptance']} | {row['tasks']} | {row['open_blockers']} | "
            f"{row['latest_checkpoint'] or '—'} ({row['checkpoints']}) | "
            f"{row['root_lines']}L/{row['root_bytes']}B | "
            f"{row['live_history_events']} | "
            f"{row['last_activity']} |"
        )
    print()
    print("| Bugfix | Title | Area | Status | Linked EP | Open blockers | Last activity |")
    print("|---|---|---|---|---|---|---|")
    for row in payload["bugfixes"]:
        print(
            f"| {row['id']} | {md_cell(str(row['title']))} | "
            f"{md_cell(str(row['area']))} | {row['status']} | {row['linked_ep']} | "
            f"{row['open_blockers']} | {row['last_activity']} |"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Target repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create missing directories and repository indexes")
    architecture_root = sub.add_parser(
        "register-architecture-root",
        help="Register an existing repository Design Doc/ADR corpus",
    )
    architecture_root.add_argument(
        "path",
        help="Repository-relative directory under docs/",
    )

    research = sub.add_parser(
        "new-research",
        help="Create a bounded Research package with a draft Synthesis",
    )
    research.add_argument("--slug", required=True)
    research.add_argument("--title", required=True)
    research.add_argument("--owner", default="")
    research.add_argument("--author", default="")

    archive_research_parser = sub.add_parser(
        "archive-research",
        help="Conclude and seal or cancel a Research package",
    )
    archive_research_parser.add_argument("research_id")
    archive_research_parser.add_argument(
        "--outcome",
        choices=sorted(RESEARCH_COMPLETED_STATUSES),
        required=True,
    )
    archive_research_parser.add_argument("--reason", default="")

    adr = sub.add_parser(
        "new-adr",
        help="Create a proposed architecture decision record",
    )
    adr.add_argument("--slug", required=True)
    adr.add_argument("--title", required=True)
    adr.add_argument("--owner", default="")
    adr.add_argument("--author", default="")
    adr.add_argument(
        "--research",
        action="append",
        default=[],
        metavar="R-NNN",
        help="Concluded Research reference; repeat for multiple packages",
    )
    adr.add_argument(
        "--depends-on",
        action="append",
        default=[],
        metavar="ADR-NNN",
        help="Accepted prerequisite ADR; repeat for multiple dependencies",
    )
    adr.add_argument(
        "--amends",
        action="append",
        default=[],
        metavar="ADR-NNN",
        help="Accepted ADR narrowed or extended by this decision; repeatable",
    )
    adr.add_argument(
        "--amends-constraint",
        action="append",
        default=[],
        metavar="ADR-NNN#C-NNN",
        help=(
            "Structured constraint changed in each --amends ADR; repeat for "
            "multiple constraints"
        ),
    )
    adr.add_argument(
        "--design",
        action="append",
        default=[],
        metavar="PATH",
        help="Repository-relative Design Doc; repeat for multiple documents",
    )

    decide = sub.add_parser(
        "decide-adr",
        help="Accept or reject a proposed ADR with explicit decision authority",
    )
    decide.add_argument("adr_id")
    decide.add_argument(
        "--outcome",
        choices=("accepted", "rejected"),
        required=True,
    )
    decide.add_argument("--decision-maker", required=True)

    transition = sub.add_parser(
        "transition-adr",
        help="Preview or apply an authorized ADR effect-state transition",
    )
    transition.add_argument("adr_id", metavar="ADR-NNN")
    transition.add_argument(
        "--to",
        choices=("accepted", "under_review", "retired"),
        required=True,
        dest="target_status",
    )
    transition.add_argument("--decision-maker", required=True)
    transition.add_argument("--reason", required=True)
    transition.add_argument(
        "--apply",
        action="store_true",
        help="Apply the previewed transition atomically",
    )

    supersede = sub.add_parser(
        "supersede-adr",
        help="Preview or apply an authorized ADR replacement",
    )
    supersede.add_argument("old_adr_id")
    supersede.add_argument(
        "--by",
        required=True,
        dest="new_adr_id",
        metavar="ADR-NNN",
    )
    supersede.add_argument("--decision-maker", required=True)
    supersede.add_argument("--reason", required=True)
    supersede.add_argument(
        "--apply",
        action="store_true",
        help="Apply the previewed supersession atomically",
    )

    sub.add_parser(
        "adr-health",
        help="Report independent, non-normative ADR corpus pressure dimensions",
    ).add_argument("--json", action="store_true", dest="as_json")

    set_view = sub.add_parser(
        "set-decision-view",
        help="Preview or apply a persistent non-normative Decision View",
    )
    set_view.add_argument("view_id", metavar="VIEW")
    set_view.add_argument("--title", required=True)
    set_view.add_argument(
        "--adr",
        action="append",
        required=True,
        metavar="ADR-NNN",
        help="Current accepted ADR seed; repeat for multiple seeds",
    )
    set_view.add_argument(
        "--apply",
        action="store_true",
        help="Apply the previewed registry and projection changes atomically",
    )

    remove_view = sub.add_parser(
        "remove-decision-view",
        help="Preview or apply removal of a Decision View",
    )
    remove_view.add_argument("view_id", metavar="VIEW")
    remove_view.add_argument(
        "--apply",
        action="store_true",
        help="Apply the previewed registry and projection removal atomically",
    )

    capsule = sub.add_parser(
        "decision-capsule",
        help="Compile exact digest-verifiable ADR task context",
    )
    capsule_selection = capsule.add_mutually_exclusive_group(required=True)
    capsule_selection.add_argument("--view", default="", metavar="VIEW")
    capsule_selection.add_argument(
        "--adr",
        action="append",
        default=[],
        metavar="ADR-NNN",
        help="Current accepted ADR seed; repeat for multiple seeds",
    )
    capsule.add_argument(
        "--constraint",
        action="append",
        default=[],
        metavar="ADR-NNN#C-NNN",
        help="Exact stable constraint selection; repeat for multiple rows",
    )
    capsule.add_argument(
        "--budget-bytes",
        type=int,
        default=DECISION_CAPSULE_DEFAULT_BUDGET_BYTES,
    )
    capsule.add_argument("--budget-reason", default="")
    capsule.add_argument("--json", action="store_true", dest="as_json")

    consolidation = sub.add_parser(
        "adr-consolidation-plan",
        help="Preview semantic-consolidation impact without changing ADRs",
    )
    consolidation_selection = consolidation.add_mutually_exclusive_group(
        required=True
    )
    consolidation_selection.add_argument("--view", default="", metavar="VIEW")
    consolidation_selection.add_argument(
        "--adr",
        action="append",
        default=[],
        metavar="ADR-NNN",
        help="Current accepted ADR seed; repeat for multiple seeds",
    )
    consolidation.add_argument("--json", action="store_true", dest="as_json")

    register_revision = sub.add_parser(
        "register-adr-revision",
        help="Preview or store immutable historical ADR evidence",
    )
    register_revision.add_argument("adr_id", metavar="ADR-NNN")
    revision_source = register_revision.add_mutually_exclusive_group(
        required=True
    )
    revision_source.add_argument(
        "--from-file",
        default="",
        metavar="PATH",
        help="Repository-relative strict decided ADR document",
    )
    revision_source.add_argument(
        "--from-git-blob",
        default="",
        metavar="OBJECT_ID",
        help="Full Git blob object ID; Git is used only during explicit import",
    )
    register_revision.add_argument(
        "--apply",
        action="store_true",
        help="Write the previewed immutable revision into docs/.epctl",
    )

    ep = sub.add_parser(
        "new-ep",
        help="Create a gated v2.8 ExecPlan from architecture, Design and benchmark inputs",
    )
    ep.add_argument("--slug", required=True)
    ep.add_argument("--title", required=True)
    ep.add_argument("--owner", default="")
    ep.add_argument("--author", default="")
    ep.add_argument(
        "--research",
        action="append",
        default=[],
        metavar="R-NNN",
        help="Concluded Research reference; repeat for multiple packages",
    )
    ep.add_argument(
        "--adr",
        action="append",
        default=[],
        metavar="ADR-NNN",
        help="Accepted current ADR reference; repeat for multiple decisions",
    )
    ep.add_argument(
        "--design",
        action="append",
        default=[],
        metavar="PATH",
        help="Repository-relative Design Doc; repeat for multiple documents",
    )
    ep.add_argument(
        "--benchmark-scenario",
        action="append",
        default=[],
        metavar="BS-NNN",
        help=(
            "Predeclared Benchmark Scenario required for completion; "
            "repeat for multiple gates"
        ),
    )
    ep.add_argument(
        "--architecture-entrypoint",
        default="",
        metavar="PATH",
        help="Optional index or overview for the architecture input set",
    )
    ep.add_argument("--research-not-required-reason", default="")
    ep.add_argument(
        "--decision-not-required-reason",
        "--architecture-not-required-reason",
        dest="decision_not_required_reason",
        default="",
        help=(
            "Why this EP creates no new durable architecture decision; the "
            "legacy --architecture-not-required-reason spelling remains an alias"
        ),
    )
    ep.add_argument(
        "--architecture-not-applicable-reason",
        default="",
        help="Why no existing ADR or architecture input applies to this EP",
    )

    task = sub.add_parser("new-task", help="Create a task under an active v2 plan")
    task.add_argument("plan_id")
    task.add_argument("--slug", required=True)
    task.add_argument("--title", required=True)
    task.add_argument("--owner", default="")
    task.add_argument("--author", default="")

    bug = sub.add_parser("new-bugfix", help="Create a persistent bugfix record")
    bug.add_argument("--slug", required=True)
    bug.add_argument("--title", required=True)
    bug.add_argument("--area", default="unspecified")
    bug.add_argument("--severity", default="unspecified")
    bug.add_argument("--owner", default="")
    bug.add_argument("--author", default="")

    debt = sub.add_parser("new-debt", help="Add an active technical debt entry")
    debt.add_argument("--description", required=True)
    debt.add_argument("--area", default="unspecified")
    debt.add_argument("--priority", default="unspecified")
    debt.add_argument("--target", default="unscheduled")

    checkpoint = sub.add_parser(
        "checkpoint",
        help="Seal older history and refresh the bounded root working set",
    )
    checkpoint.add_argument("plan_id")
    checkpoint.add_argument("--slug", required=True)
    checkpoint.add_argument("--title", required=True)
    checkpoint.add_argument("--current-milestone", required=True)
    checkpoint.add_argument("--summary", required=True)
    checkpoint.add_argument("--next-action", required=True)
    checkpoint.add_argument(
        "--revision",
        required=True,
        help=(
            "Repository or workspace revision represented by this checkpoint, "
            "for example git:<sha> or snapshot:<id>"
        ),
    )
    checkpoint.add_argument("--dry-run", action="store_true")

    validate_parser = sub.add_parser(
        "validate",
        help="Validate repository plan artifacts",
    )
    validate_parser.add_argument(
        "--fix-index",
        action="store_true",
        help="Rebuild only the managed index projections before validation",
    )
    sub.add_parser("reindex", help="Rebuild managed index projections")
    status_parser = sub.add_parser(
        "status",
        help="Print Research, ADR, plan and bugfix status",
    )
    status_parser.add_argument("--json", action="store_true", dest="as_json")

    archive_plan = sub.add_parser("archive-ep", help="Strictly complete and archive an EP")
    archive_plan.add_argument("plan_id")
    archive_plan.add_argument(
        "--outcome",
        choices=sorted(PLAN_COMPLETED_STATUSES),
        default="completed",
    )
    archive_plan.add_argument("--reason", default="")
    archive_plan.add_argument(
        "--verified-revision",
        default="",
        help="Repository or workspace revision that passed final verification",
    )
    archive_plan.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="Verification artifact or CI reference; repeat for multiple items",
    )
    archive_bug = sub.add_parser(
        "archive-bugfix", help="Archive a fixed, escalated or cancelled bugfix"
    )
    archive_bug.add_argument("bugfix_id")
    archive_bug.add_argument(
        "--outcome",
        choices=sorted(BUGFIX_COMPLETED_STATUSES),
        required=True,
    )
    archive_bug.add_argument("--reason", default="")
    archive_bug.add_argument("--linked-ep", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = normalize_repo(args.repo)
        if args.command == "init":
            with repo_lock(repo):
                created = init_repo(repo)
            print(json.dumps({"created": created}, ensure_ascii=False))
        elif args.command == "register-architecture-root":
            print(register_architecture_root(repo, args.path))
        elif args.command == "new-research":
            print(
                new_research(
                    repo,
                    args.slug,
                    args.title,
                    args.owner,
                    args.author,
                )
            )
        elif args.command == "archive-research":
            print(
                archive_research(
                    repo,
                    args.research_id,
                    args.outcome,
                    args.reason,
                )
            )
        elif args.command == "new-adr":
            print(
                new_adr(
                    repo,
                    args.slug,
                    args.title,
                    args.owner,
                    args.author,
                    args.research,
                    args.depends_on,
                    args.amends,
                    args.amends_constraint,
                    args.design,
                )
            )
        elif args.command == "decide-adr":
            print(
                decide_adr(
                    repo,
                    args.adr_id,
                    args.outcome,
                    args.decision_maker,
                )
            )
        elif args.command == "transition-adr":
            print(
                json.dumps(
                    transition_adr(
                        repo,
                        args.adr_id,
                        args.target_status,
                        args.decision_maker,
                        args.reason,
                        args.apply,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "supersede-adr":
            print(
                json.dumps(
                    supersede_adr(
                        repo,
                        args.old_adr_id,
                        args.new_adr_id,
                        args.decision_maker,
                        args.reason,
                        args.apply,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "adr-health":
            payload = adr_health(repo)
            if args.as_json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_adr_health(payload)
        elif args.command == "set-decision-view":
            print(
                json.dumps(
                    set_decision_view(
                        repo,
                        args.view_id,
                        args.title,
                        args.adr,
                        args.apply,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "remove-decision-view":
            print(
                json.dumps(
                    remove_decision_view(repo, args.view_id, args.apply),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "decision-capsule":
            context, _ = decision_selection_context(repo, args.view, args.adr)
            payload = compile_decision_capsule(
                context,
                args.constraint,
                budget_bytes=args.budget_bytes,
                budget_reason=args.budget_reason,
            )
            if args.as_json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(payload["context"], end="")
        elif args.command == "adr-consolidation-plan":
            payload = adr_consolidation_plan(repo, args.view, args.adr)
            if args.as_json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_adr_consolidation_plan(payload)
        elif args.command == "register-adr-revision":
            print(
                json.dumps(
                    register_adr_revision(
                        repo,
                        args.adr_id,
                        source_file=args.from_file,
                        git_object_id=args.from_git_blob,
                        apply=args.apply,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "new-ep":
            print(
                new_ep(
                    repo,
                    args.slug,
                    args.title,
                    args.owner,
                    args.author,
                    args.research,
                    args.adr,
                    args.design,
                    args.benchmark_scenario,
                    args.architecture_entrypoint,
                    args.research_not_required_reason,
                    args.decision_not_required_reason,
                    args.architecture_not_applicable_reason,
                )
            )
        elif args.command == "new-task":
            print(
                new_task(
                    repo,
                    args.plan_id,
                    args.slug,
                    args.title,
                    args.owner,
                    args.author,
                )
            )
        elif args.command == "new-bugfix":
            print(
                new_bugfix(
                    repo,
                    args.slug,
                    args.title,
                    args.area,
                    args.severity,
                    args.owner,
                    args.author,
                )
            )
        elif args.command == "new-debt":
            print(
                new_debt(
                    repo, args.description, args.area, args.priority, args.target
                )
            )
        elif args.command == "checkpoint":
            print(
                json.dumps(
                    checkpoint_plan(
                        repo,
                        args.plan_id,
                        args.slug,
                        args.title,
                        args.current_milestone,
                        args.summary,
                        args.next_action,
                        args.revision,
                        args.dry_run,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "validate":
            if args.fix_index:
                with repo_lock(repo):
                    rebuild_indexes(repo)
            errors, warnings = validate_repo(repo)
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
        elif args.command == "reindex":
            with repo_lock(repo):
                result = rebuild_indexes(repo)
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == "status":
            print_status(repo, args.as_json)
        elif args.command == "archive-ep":
            print(
                archive_ep(
                    repo,
                    args.plan_id,
                    args.outcome,
                    args.reason,
                    args.verified_revision,
                    args.evidence,
                )
            )
        elif args.command == "archive-bugfix":
            print(
                archive_bugfix(
                    repo,
                    args.bugfix_id,
                    args.outcome,
                    args.reason,
                    args.linked_ep,
                )
            )
        return 0
    except (EpctlError, OSError) as exc:
        print(f"epctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
