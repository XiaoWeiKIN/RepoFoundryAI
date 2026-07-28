#!/usr/bin/env python3
"""Deterministic repository operations for the execution-plan skill."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
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
CHECKPOINT_SECTIONS = (
    "Handoff Summary",
    "Next Action At Checkpoint",
    "Archived Progress",
    "Archived Surprises & Discoveries",
    "Archived Decision Log",
    "Archived Resolved Blockers",
    "Archived Revision Notes",
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
TASK_STATUSES = {"todo", "in_progress", "blocked", "done", "cancelled"}
BUGFIX_ACTIVE_STATUSES = {"open", "in_progress", "blocked"}
BUGFIX_COMPLETED_STATUSES = {"fixed", "escalated", "cancelled"}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BLOCKER_ID_RE = re.compile(r"\bBLK-(\d{3,})\b", re.IGNORECASE)
ROOT_LINE_WARNING = 800
ROOT_BYTE_WARNING = 64 * 1024
HISTORY_EVENT_WARNING = 50
ID_RE = {
    "EP": re.compile(r"\bEP-(\d{3,})\b", re.IGNORECASE),
    "BF": re.compile(r"\bBF-(\d{3,})\b", re.IGNORECASE),
    "TD": re.compile(r"\bTD-(\d{3,})\b", re.IGNORECASE),
    "TASK": re.compile(r"\bTASK-(\d{3,})\b", re.IGNORECASE),
    "CP": re.compile(r"\bCP-(\d{3,})\b", re.IGNORECASE),
}


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
    directories = (
        "docs/.epctl",
        "docs/exec-plans/active",
        "docs/exec-plans/completed",
        "docs/bugfixes/active",
        "docs/bugfixes/completed",
    )
    for relative in directories:
        path = repo / relative
        reject_symlink_path(repo, path)
        if not path.exists():
            path.mkdir(parents=True)
            created.append(relative + "/")

    files = (
        ("docs/PLANS.md", "plans-index.md", {}),
        ("docs/BUGFIXES.md", "bugfixes-index.md", {}),
        (
            "docs/exec-plans/tech-debt-tracker.md",
            "tech-debt-tracker.md",
            {"DATE": date_string()},
        ),
    )
    for relative, asset, values in files:
        path = repo / relative
        reject_symlink_path(repo, path)
        if ensure_file(path, asset, values):
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


def ensure_markers(text: str, kind: str) -> str:
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


def index_header(kind: str) -> tuple[str, str]:
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
    header, divider = index_header(kind)
    ordered_rows = sorted(
        rows,
        key=lambda row: int(ID_RE[kind].search(row).group(1)),
    )
    replacement = "\n" + "\n".join((header, divider, *ordered_rows)) + "\n"
    return text[:body_start] + replacement + text[end:]


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
        for number in ID_RE[kind].findall(
            managed_index_body(text, kind, table)
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


def rebuild_indexes(repo: Path) -> dict[str, int]:
    init_repo(repo)
    plan_index = repo / "docs" / "PLANS.md"
    bugfix_index = repo / "docs" / "BUGFIXES.md"
    active_plans = plan_files(repo, "active")
    completed_plans = plan_files(repo, "completed")
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

    state = load_state(repo)
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    for prefix in ("EP", "BF", "TD"):
        high_water[prefix] = max(
            int(high_water.get(prefix, 0)),
            max(scan_ids(repo, prefix), default=0),
        )
    save_state(repo, state)
    return {
        "plans": len(active_plans) + len(completed_plans),
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


def new_ep(repo: Path, slug: str, title: str, owner: str) -> Path:
    validate_slug(slug)
    with repo_lock(repo):
        init_repo(repo)
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
                "OWNER": yaml_string(owner),
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


def new_task(repo: Path, plan_id: str, slug: str, title: str, owner: str) -> Path:
    validate_slug(slug)
    with repo_lock(repo):
        plan_path = find_plan(repo, plan_id, "active")
        if plan_path.name != "EXECPLAN.md":
            raise EpctlError("new-task requires a v2 plan with EXECPLAN.md")
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
                "OWNER": yaml_string(owner),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
            },
        )
        atomic_write(path, text)
        return path


def new_bugfix(
    repo: Path, slug: str, title: str, area: str, severity: str
) -> Path:
    validate_slug(slug)
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

    with repo_lock(repo):
        plan_path = find_plan(repo, plan_id, "active")
        if plan_path.name != "EXECPLAN.md":
            raise EpctlError("checkpoint requires a v2 EXECPLAN.md")
        text = plan_path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
        if data.get("schema_version") != "2.1":
            raise EpctlError(
                "checkpoint requires schema_version 2.1 and ## Current Snapshot"
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
        revision = (
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
        new_root = replace_section(new_root, "Revision Notes", revision)
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
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
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
        digest = payload_sha256(candidate)
        candidate = candidate.replace(
            "payload_sha256: PENDING",
            f"payload_sha256: {digest}",
            1,
        )
        payload = {
            "checkpoint_id": checkpoint_id,
            "path": checkpoint_path.relative_to(repo).as_posix(),
            "previous_checkpoint": previous or None,
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

        plans_index = repo / "docs" / "PLANS.md"
        bugfix_index = repo / "docs" / "BUGFIXES.md"
        old_plans_index = plans_index.read_text(encoding="utf-8")
        old_bugfix_index = bugfix_index.read_text(encoding="utf-8")
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
            atomic_write(plans_index, old_plans_index)
            atomic_write(bugfix_index, old_bugfix_index)
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
    if data.get("schema_version") != "1":
        errors.append(f"{path}: checkpoint schema_version must be 1")
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
    errors.extend(
        validate_required_sections(path, text, CHECKPOINT_SECTIONS)
    )
    if marker_names(text):
        errors.append(f"{path}: required placeholders remain")
    expected_digest = data.get("payload_sha256", "")
    actual_digest = payload_sha256(text)
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
    if schema_version not in {"2.0", "2.1"}:
        errors.append(f"{path}: unsupported schema_version {schema_version!r}")
    if schema_version == "2.1":
        errors.extend(
            validate_required_sections(path, text, EXECPLAN_V21_SECTIONS)
        )
        if "latest_checkpoint" not in data:
            errors.append(f"{path}: missing frontmatter field latest_checkpoint")
    else:
        warnings.append(
            f"{path}: v2.0 plan has no bounded checkpoint model; "
            "add schema_version 2.1 and ## Current Snapshot before checkpointing"
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
    if schema_version == "2.1" and not re.search(
        r"(?im)^-\s+Next action:\s+\S",
        snapshot,
    ):
        errors.append(f"{path}: Current Snapshot requires a non-empty Next action")
    root_bytes = len(text.encode("utf-8"))
    root_lines = len(text.splitlines())
    event_count = history_event_count(text)
    if root_bytes > ROOT_BYTE_WARNING or root_lines > ROOT_LINE_WARNING:
        warnings.append(
            f"{path}: root working set is {root_lines} lines/{root_bytes} bytes; "
            "create a checkpoint"
        )
    if event_count > HISTORY_EVENT_WARNING:
        warnings.append(
            f"{path}: {event_count} live history events exceed "
            f"the {HISTORY_EVENT_WARNING}-event checkpoint threshold"
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
    docs_root = repo / "docs"
    if docs_root.exists():
        for path in docs_root.rglob("*"):
            if path.is_symlink() and (
                "exec-plans" in path.parts
                or "bugfixes" in path.parts
                or ".epctl" in path.parts
                or path.name in {"PLANS.md", "BUGFIXES.md"}
            ):
                errors.append(f"{path}: symbolic links are not supported")
    plans_index = repo / "docs" / "PLANS.md"
    bugfix_index = repo / "docs" / "BUGFIXES.md"
    if not plans_index.is_file():
        errors.append(f"{plans_index}: missing; run init")
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
        for prefix in ("EP", "BF", "TD"):
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


def archive_ep(
    repo: Path,
    plan_id: str,
    outcome: str,
    reason: str,
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
        text = path.read_text(encoding="utf-8")
        container = path.parent
        destination = repo / "docs" / "exec-plans" / "completed" / container.name
        reject_symlink_path(repo, destination)
        if destination.exists():
            raise EpctlError(f"Archive destination exists: {destination}")
        new_text = update_frontmatter(
            text, {"status": outcome, "updated": date_string()}
        ).replace(
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
        plans_index = repo / "docs" / "PLANS.md"
        bugfix_index = repo / "docs" / "BUGFIXES.md"
        old_plans_index = plans_index.read_text(encoding="utf-8")
        old_bugfix_index = bugfix_index.read_text(encoding="utf-8")
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
            atomic_write(plans_index, old_plans_index)
            atomic_write(bugfix_index, old_bugfix_index)
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

        plans_index = repo / "docs" / "PLANS.md"
        bugfix_index = repo / "docs" / "BUGFIXES.md"
        old_plans_index = plans_index.read_text(encoding="utf-8")
        old_bugfix_index = bugfix_index.read_text(encoding="utf-8")
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
            atomic_write(plans_index, old_plans_index)
            atomic_write(bugfix_index, old_bugfix_index)
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
    plans: list[dict[str, object]] = []
    for path in plan_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
            data, _, _ = parse_frontmatter(text)
        except EpctlError:
            continue
        acceptance = checkboxes(section(text, "Validation and Acceptance") or "")
        tasks = []
        for task in task_files(path):
            try:
                task_data, _, _ = parse_frontmatter(task.read_text(encoding="utf-8"))
            except EpctlError:
                continue
            tasks.append(task_data.get("status", "unknown"))
        plans.append(
            {
                "id": data.get("id", ""),
                "title": data.get("title", ""),
                "status": data.get("status", ""),
                "acceptance": f"{sum(acceptance)}/{len(acceptance)}",
                "tasks": f"{sum(s in {'done', 'cancelled'} for s in tasks)}/{len(tasks)}"
                if tasks
                else "—",
                "open_blockers": len(unresolved_blockers(text)),
                "latest_checkpoint": data.get("latest_checkpoint", ""),
                "checkpoints": len(checkpoint_files(path)),
                "root_lines": len(text.splitlines()),
                "root_bytes": len(text.encode("utf-8")),
                "live_history_events": history_event_count(text),
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
    plans.sort(key=lambda row: str(row["id"]))
    bugfixes.sort(key=lambda row: str(row["id"]))
    return {"plans": plans, "bugfixes": bugfixes}


def print_status(repo: Path, as_json: bool) -> None:
    payload = status_rows(repo)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(
        "| EP | Title | Status | Acceptance | Tasks | Open blockers | "
        "Checkpoint | Root | Events | Last activity |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for row in payload["plans"]:
        print(
            f"| {row['id']} | {md_cell(str(row['title']))} | {row['status']} | "
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

    ep = sub.add_parser("new-ep", help="Create a v2 self-contained ExecPlan")
    ep.add_argument("--slug", required=True)
    ep.add_argument("--title", required=True)
    ep.add_argument("--owner", default="")

    task = sub.add_parser("new-task", help="Create a task under an active v2 plan")
    task.add_argument("plan_id")
    task.add_argument("--slug", required=True)
    task.add_argument("--title", required=True)
    task.add_argument("--owner", default="")

    bug = sub.add_parser("new-bugfix", help="Create a persistent bugfix record")
    bug.add_argument("--slug", required=True)
    bug.add_argument("--title", required=True)
    bug.add_argument("--area", default="unspecified")
    bug.add_argument("--severity", default="unspecified")

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
    status_parser = sub.add_parser("status", help="Print plan and bugfix status")
    status_parser.add_argument("--json", action="store_true", dest="as_json")

    archive_plan = sub.add_parser("archive-ep", help="Strictly complete and archive an EP")
    archive_plan.add_argument("plan_id")
    archive_plan.add_argument(
        "--outcome",
        choices=sorted(PLAN_COMPLETED_STATUSES),
        default="completed",
    )
    archive_plan.add_argument("--reason", default="")
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
        elif args.command == "new-ep":
            print(new_ep(repo, args.slug, args.title, args.owner))
        elif args.command == "new-task":
            print(new_task(repo, args.plan_id, args.slug, args.title, args.owner))
        elif args.command == "new-bugfix":
            print(
                new_bugfix(
                    repo, args.slug, args.title, args.area, args.severity
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
            print(archive_ep(repo, args.plan_id, args.outcome, args.reason))
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
