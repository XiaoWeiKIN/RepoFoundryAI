#!/usr/bin/env python3
"""Deterministic multi-document Research operations."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
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
MANIFEST_NAME = "RESEARCH_MANIFEST.json"
SNAPSHOT_DIRECTORY = "artifacts/research-snapshot"

RESEARCH_SECTIONS = (
    "Research Metadata",
    "Purpose and Decision to Enable",
    "Current Snapshot",
    "Research Rounds",
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
RESEARCH_LEGACY_SECTIONS = tuple(
    heading
    for heading in RESEARCH_SECTIONS
    if heading not in {"Research Metadata", "Research Rounds"}
)
ROUND_SECTIONS = (
    "Focus and Questions",
    "Scope",
    "Evidence Added",
    "Synthesis Delta",
    "Next Inquiry",
    "Round Outcome",
)
TOPIC_V1_SECTIONS = (
    "Executive Takeaway",
    "Question and Decision Relevance",
    "Scope and Non-goals",
    "Current Context",
    "Method and Evidence Selection",
    "Evidence",
    "Analysis",
    "Alternatives and Counterevidence",
    "Findings",
    "Uncertainty and Limitations",
    "Impact on Synthesis",
    "Next Inquiry",
    "References and Artifacts",
    "Revision Notes",
)
TOPIC_V2_SECTIONS = (
    "Decision Brief",
    "Model at a Glance",
    "Claims and Evidence",
    "Options and Trade-offs",
    "Risks, Unknowns, and Validation",
    "Handoff",
    "Sources",
    "Revision Notes",
)
TOPIC_V21_ROLES = (
    "decision-brief",
    "mental-model",
    "analysis",
    "alternatives",
    "implications",
    "falsifiers",
    "handoff",
    "evidence-index",
    "sources",
    "revision-notes",
)
TOPIC_SCHEMA_VERSIONS = {"1", "2", "2.1"}
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
RESEARCH_QUESTION_STATUSES = {"open", "answered", "deferred", "invalidated"}
RESEARCH_SCHEMA_VERSIONS = {"1", "1.1"}
SYNTHESIS_SCHEMA_VERSIONS = {"1", "1.1"}
RESEARCH_TYPES = {
    "technical",
    "architecture",
    "feasibility",
    "comparative",
    "incident",
    "domain",
    "other",
}
RESEARCH_MATURITY = {"exploratory", "evidence_building", "review_ready"}
ROUND_STATUSES = {"active", "completed", "cancelled"}
TOPIC_CONFIDENCE_LEVELS = {"high", "medium", "low"}
TOPIC_EVIDENCE_LABELS = (
    "Observation",
    "Evidence",
    "Interpretation",
    "Confidence",
)
TOPIC_CLAIM_LABELS = (
    "Evidence",
    "Reasoning",
    "Decision impact",
    "Confidence",
    "Falsifier",
)
TOPIC_BRIEF_LABELS = (
    "Answer",
    "Confidence",
    "Decision impact",
    "Applies when",
)
TOPIC_V21_BRIEF_FIELDS = (
    ("Answer", ("Answer", "答案")),
    ("Confidence", ("Confidence", "置信度")),
    ("Decision impact", ("Decision impact", "决策影响")),
    ("Applies when", ("Applies when", "适用边界")),
)
TOPIC_V21_BRIEF_LABELS = tuple(
    alias
    for _, aliases in TOPIC_V21_BRIEF_FIELDS
    for alias in aliases
)
TOPIC_MIN_ANALYSIS_CHARS = 120
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESEARCH_ID_RE = re.compile(r"\bR-(\d{3,})\b", re.IGNORECASE)
RESEARCH_QUESTION_ID_RE = re.compile(r"RQ-(\d{3,})", re.IGNORECASE)
ROUND_ID_RE = re.compile(r"\bRR-(\d{3,})\b", re.IGNORECASE)
TOPIC_EVIDENCE_ID_RE = re.compile(r"\bE-(\d{3,})\b", re.IGNORECASE)
TOPIC_FINDING_ID_RE = re.compile(r"\bF-(\d{3,})\b", re.IGNORECASE)
TOPIC_ANALYSIS_ID_RE = re.compile(r"\bA-(\d{3,})\b", re.IGNORECASE)
TOPIC_SOURCE_ID_RE = re.compile(r"\bS-(\d{3,})\b", re.IGNORECASE)
TOPIC_ROLE_RE = re.compile(
    r"<!--\s*topic-role\s*:\s*([a-z0-9-]+)\s*-->",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


class ResearchctlError(RuntimeError):
    pass


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def date_string() -> str:
    return utc_now().date().isoformat()


def timestamp_string() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def normalize_repo(value: str) -> Path:
    repo = Path(value).expanduser().resolve()
    if not repo.is_dir():
        raise ResearchctlError(f"Repository directory does not exist: {repo}")
    return repo


def repository_from_artifact(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == "docs":
            return parent.parent
    raise ResearchctlError(f"Artifact is not under a docs directory: {path}")


def validate_slug(value: str) -> str:
    if not SLUG_RE.fullmatch(value):
        raise ResearchctlError(
            "Slug must be lowercase kebab-case, for example cache-topology"
        )
    return value


def validate_research_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in RESEARCH_TYPES:
        raise ResearchctlError(
            "Research type must be one of: " + ", ".join(sorted(RESEARCH_TYPES))
        )
    return normalized


def yaml_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", " ")
        .replace("\n", " ")
    )


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def md_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ").strip()


def display_value(value: str, fallback: str = "Unassigned") -> str:
    return md_cell(value) if value.strip() else fallback


def research_type_label(value: str) -> str:
    return value.replace("_", " ").title()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = ""
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
        temporary = handle.name
    try:
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def asset_text(name: str) -> str:
    path = ASSET_DIR / name
    if not path.is_file():
        raise ResearchctlError(f"Missing bundled asset: {path}")
    return path.read_text(encoding="utf-8")


def render_asset(name: str, values: dict[str, str]) -> str:
    text = asset_text(name)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftovers = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
    if leftovers:
        raise ResearchctlError(
            f"Unresolved template values in {name}: {', '.join(leftovers)}"
        )
    return text


def reject_symlink_path(repo: Path, path: Path) -> None:
    try:
        relative = path.relative_to(repo)
    except ValueError as exc:
        raise ResearchctlError(f"Managed path escapes repository: {path}") from exc
    current = repo
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ResearchctlError(f"Refusing symbolic link: {current}")


def reject_input_symlink_path(repo: Path, path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        candidate = current / component
        if candidate.is_symlink():
            try:
                current.resolve(strict=True).relative_to(repo)
            except (FileNotFoundError, ValueError):
                pass
            else:
                raise ResearchctlError(f"Refusing symbolic link: {candidate}")
        current = candidate


def normalized_existing_path(repo: Path, raw: str, kind: str) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = repo / candidate
    reject_input_symlink_path(repo, candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ResearchctlError(f"{kind} does not exist: {raw}") from exc
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ResearchctlError(f"{kind} escapes repository: {raw}") from exc
    reject_symlink_path(repo, resolved)
    return resolved


def normalized_relative_path(repo: Path, raw: str, kind: str) -> str:
    return normalized_existing_path(repo, raw, kind).relative_to(repo).as_posix()


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


def load_state(repo: Path) -> dict[str, object]:
    path = state_path(repo)
    if not path.exists():
        return {"version": STATE_VERSION, "high_water": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchctlError(f"Invalid state file {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != STATE_VERSION:
        raise ResearchctlError(f"Unsupported state file: {path}")
    high_water = value.get("high_water")
    if not isinstance(high_water, dict) or any(
        not isinstance(key, str)
        or not isinstance(number, int)
        or number < 0
        for key, number in high_water.items()
    ):
        raise ResearchctlError(f"Invalid high_water map: {path}")
    return value


def save_state(repo: Path, value: dict[str, object]) -> None:
    atomic_write(
        state_path(repo),
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def scan_research_numbers(repo: Path) -> set[int]:
    values: set[int] = set()
    research_root = repo / "docs" / "research"
    if research_root.exists():
        for path in research_root.rglob("*"):
            for match in RESEARCH_ID_RE.finditer(path.name):
                values.add(int(match.group(1)))
            if path.is_file() and path.suffix.lower() in {".md", ".json"}:
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                values.update(int(value) for value in RESEARCH_ID_RE.findall(text))
    return values


def next_research_id(repo: Path) -> str:
    state = load_state(repo)
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    number = max(
        max(scan_research_numbers(repo), default=0),
        int(high_water.get("R", 0)),
    ) + 1
    high_water["R"] = number
    save_state(repo, state)
    return f"R-{number:03d}"


def init_repo(repo: Path) -> list[str]:
    created: list[str] = []
    for relative in (
        "docs/.epctl",
        "docs/research/active",
        "docs/research/completed",
    ):
        path = repo / relative
        reject_symlink_path(repo, path)
        if not path.exists():
            path.mkdir(parents=True)
            created.append(relative + "/")
    index = repo / "docs" / "RESEARCH.md"
    reject_symlink_path(repo, index)
    if not index.exists():
        atomic_write(index, asset_text("research-index.md"))
        created.append("docs/RESEARCH.md")
    if not state_path(repo).exists():
        save_state(repo, {"version": STATE_VERSION, "high_water": {}})
        created.append("docs/.epctl/state.json")
    return created


def parse_frontmatter(text: str) -> tuple[dict[str, str], int, int]:
    if not text.startswith("---\n"):
        raise ResearchctlError("Missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ResearchctlError("Unclosed YAML frontmatter")
    data: dict[str, str] = {}
    for line_number, raw in enumerate(text[4:end].splitlines(), start=2):
        if "\t" in raw:
            raise ResearchctlError(
                f"Tabs are not allowed in frontmatter (line {line_number})"
            )
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isspace() or ":" not in raw:
            raise ResearchctlError(
                f"Only top-level key: value fields are supported (line {line_number})"
            )
        key, raw_value = raw.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ResearchctlError(
                f"Invalid frontmatter key {key!r} (line {line_number})"
            )
        value = raw_value.strip()
        if value.startswith('"'):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ResearchctlError(
                    f"Invalid quoted scalar for {key!r} (line {line_number})"
                ) from exc
            if not isinstance(decoded, str):
                raise ResearchctlError(f"{key!r} must be a scalar")
            value = decoded
        elif value.startswith("'"):
            if len(value) < 2 or not value.endswith("'"):
                raise ResearchctlError(f"Invalid single-quoted scalar for {key!r}")
            value = value[1:-1].replace("''", "'")
        data[key] = value
    return data, 4, end


def update_frontmatter(text: str, updates: dict[str, str]) -> str:
    _, start, end = parse_frontmatter(text)
    remaining = dict(updates)
    output: list[str] = []
    for line in text[start:end].splitlines():
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key in remaining:
            output.append(f"{key}: {remaining.pop(key)}")
        else:
            output.append(line)
    for key, value in remaining.items():
        output.append(f"{key}: {value}")
    return "---\n" + "\n".join(output) + "\n---\n" + text[end + 5 :]


def frontmatter_body(text: str) -> str:
    _, _, end = parse_frontmatter(text)
    return text[end + 5 :]


def payload_sha256(text: str) -> str:
    return hashlib.sha256(frontmatter_body(text).encode("utf-8")).hexdigest()


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
    result: list[tuple[str, list[str]]] = []
    heading: str | None = None
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            if heading is not None:
                lines.append(line)
            continue
        match = re.match(r"^##\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if match:
            if heading is not None:
                result.append((heading, lines))
            heading = match.group(1).strip()
            lines = []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        result.append((heading, lines))
    return result


def section_values(text: str, heading: str) -> list[str]:
    return [
        "\n".join(lines).strip()
        for name, lines in markdown_sections(text)
        if name == heading
    ]


def section(text: str, heading: str) -> str | None:
    values = section_values(text, heading)
    return values[0] if values else None


def section_spans(text: str) -> list[tuple[str, int, int, int]]:
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
    matches = [value for value in section_spans(text) if value[0] == heading]
    if len(matches) != 1:
        raise ResearchctlError(
            f"Expected exactly one ## {heading}, found {len(matches)}"
        )
    _, _, body_start, end = matches[0]
    return text[:body_start] + "\n" + body.strip() + "\n\n" + text[end:]


def append_section_entry(text: str, heading: str, entry: str) -> str:
    current = section(text, heading)
    if current is None:
        raise ResearchctlError(f"Missing ## {heading}")
    return replace_section(text, heading, current.rstrip() + "\n" + entry.strip())


def research_metadata_body(data: dict[str, str]) -> str:
    approval = "Pending"
    if data.get("approved_by"):
        approval = display_value(data["approved_by"])
        if data.get("approved_at"):
            approval += f" at {md_cell(data['approved_at'])}"
        if data.get("approval_ref"):
            approval += f" ({md_cell(data['approval_ref'])})"
    revision = data.get("synthesis_revision", "0")
    return "\n".join(
        (
            "| Field | Value |",
            "|---|---|",
            f"| Date | {md_cell(data.get('created', ''))} |",
            f"| Last Updated | {md_cell(data.get('updated', ''))} |",
            "| Research Type | "
            f"{research_type_label(data.get('research_type', 'other'))} |",
            f"| Research Owner | {display_value(data.get('owner', ''))} |",
            f"| Author | {display_value(data.get('author', ''))} |",
            f"| Lifecycle | {md_cell(data.get('status', ''))} |",
            f"| Maturity | {md_cell(data.get('maturity', ''))} |",
            f"| Current Round | {md_cell(data.get('current_round', ''))} |",
            f"| Synthesis Revision | v{md_cell(revision)} |",
            f"| Approval | {approval} |",
        )
    )


def sync_research_metadata(text: str) -> str:
    data, _, _ = parse_frontmatter(text)
    if data.get("schema_version") != "1.1":
        return text
    return replace_section(text, "Research Metadata", research_metadata_body(data))


def marker_names(text: str) -> set[str]:
    return set(re.findall(r"<!--\s*(REQUIRED(?:_[A-Z_]+)?)\s*:", text))


def split_table_row(line: str) -> list[str]:
    return [
        cell.replace(r"\|", "|").strip()
        for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
    ]


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


def open_research_questions(text: str) -> list[str]:
    return [
        cells[0]
        for cells in research_question_rows(text)
        if len(cells) >= 2 and cells[1].lower() == "open"
    ]


def blocker_rows(text: str) -> list[list[str]]:
    body = section(text, "Blockers") or ""
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if len(cells) < 2 or cells[0] == "ID" or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


def open_blockers(text: str) -> list[str]:
    return [
        cells[0]
        for cells in blocker_rows(text)
        if len(cells) >= 2 and cells[1].lower() == "open"
    ]


def research_round_rows(text: str) -> list[list[str]]:
    body = section(text, "Research Rounds") or ""
    rows: list[list[str]] = []
    for line in visible_markdown_lines(body):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells or cells[0].lower() == "round" or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


def update_round_row_status(text: str, round_id: str, status: str) -> str:
    body = section(text, "Research Rounds")
    if body is None:
        raise ResearchctlError("Missing ## Research Rounds")
    updated: list[str] = []
    found = False
    for line in body.splitlines():
        if line.lstrip().startswith("|"):
            cells = split_table_row(line)
            if cells and cells[0].upper() == round_id.upper():
                if len(cells) < 6:
                    raise ResearchctlError(
                        f"Research Round row {round_id} needs six columns"
                    )
                cells[2] = status
                line = "| " + " | ".join(md_cell(cell) for cell in cells[:6]) + " |"
                found = True
        updated.append(line)
    if not found:
        raise ResearchctlError(f"Research Round row not found: {round_id}")
    return replace_section(text, "Research Rounds", "\n".join(updated))


def append_round_row(
    text: str,
    round_id: str,
    focus: str,
    author: str,
    started: str,
    path: str,
) -> str:
    row = (
        f"| {round_id} | {md_cell(focus)} | active | {display_value(author)} | "
        f"{started} | `{path}` |"
    )
    return append_section_entry(text, "Research Rounds", row)


def round_paths(package: Path) -> list[Path]:
    root = package / "rounds"
    return sorted(root.glob("rr-*_*.md")) if root.exists() else []


def topic_note_paths(package: Path) -> list[Path]:
    root = package / "notes"
    if not root.exists():
        return []
    return sorted({*root.rglob("*.md"), *root.rglob("*.markdown")})


def find_round_path(package: Path, round_id: str) -> Path:
    canonical = round_id.strip().upper()
    matches: list[Path] = []
    for path in round_paths(package):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, ResearchctlError):
            continue
        if data.get("id", "").upper() == canonical:
            matches.append(path)
    if len(matches) != 1:
        raise ResearchctlError(
            f"Expected one {canonical} round in {package}, found {len(matches)}"
        )
    return matches[0]


def next_round_id(package: Path) -> str:
    numbers: list[int] = []
    for path in round_paths(package):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, ResearchctlError):
            continue
        match = ROUND_ID_RE.fullmatch(data.get("id", ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"RR-{max(numbers, default=0) + 1:03d}"


def synthesis_path(
    research_path: Path,
    data: dict[str, str] | None = None,
) -> Path:
    if data is None:
        data, _, _ = parse_frontmatter(research_path.read_text(encoding="utf-8"))
    if data.get("synthesis") != "SYNTHESIS.md":
        raise ResearchctlError(
            f"{research_path}: synthesis must be SYNTHESIS.md"
        )
    return research_path.parent / "SYNTHESIS.md"


def manifest_path(research_path: Path, data: dict[str, str] | None = None) -> Path:
    if data is None:
        data, _, _ = parse_frontmatter(research_path.read_text(encoding="utf-8"))
    if data.get("manifest", MANIFEST_NAME) != MANIFEST_NAME:
        raise ResearchctlError(
            f"{research_path}: manifest must be {MANIFEST_NAME}"
        )
    return research_path.parent / MANIFEST_NAME


def load_manifest(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ResearchctlError(f"Missing Research manifest: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchctlError(f"Invalid Research manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResearchctlError(f"Research manifest must be an object: {path}")
    return value


def manifest_digest(value: dict[str, object]) -> str:
    payload = json.loads(json.dumps(value))
    payload["payload_sha256"] = ""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def manifest_text(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def locator_key(value: dict[str, object]) -> tuple[str, str]:
    return str(value.get("base", "")), str(value.get("path", ""))


def resolve_locator(
    repo: Path,
    package: Path,
    locator: dict[str, object],
    *,
    require_file: bool = False,
) -> Path:
    base = locator.get("base")
    raw_path = locator.get("path")
    if base not in {"repo", "package"} or not isinstance(raw_path, str):
        raise ResearchctlError(f"Invalid manifest locator: {locator!r}")
    pure = Path(raw_path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ResearchctlError(f"Unsafe manifest path: {raw_path!r}")
    root = repo if base == "repo" else package
    candidate = root / pure
    reject_symlink_path(repo, candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ResearchctlError(f"Manifest path does not exist: {candidate}") from exc
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ResearchctlError(f"Manifest path escapes repository: {candidate}") from exc
    if require_file and not resolved.is_file():
        raise ResearchctlError(f"Manifest document is not a file: {candidate}")
    return resolved


def relative_locator(base: str, root: Path, path: Path) -> dict[str, str]:
    return {"base": base, "path": path.relative_to(root).as_posix()}


def inferred_document_role(path: Path, default_role: str) -> str:
    if default_role != "document" or path.suffix.lower() not in {
        ".md",
        ".markdown",
    }:
        return default_role
    try:
        text = path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
    except (OSError, UnicodeDecodeError, ResearchctlError):
        return default_role
    return "topic" if data.get("doc_type") == "research-topic" else default_role


def discover_documents(
    repo: Path,
    package: Path,
    manifest: dict[str, object],
) -> list[dict[str, object]]:
    roots = manifest.get("roots")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(roots, list) or not isinstance(entrypoints, list):
        raise ResearchctlError("Manifest roots and entrypoints must be arrays")
    entrypoint_keys: set[tuple[str, str]] = set()
    for entrypoint in entrypoints:
        if not isinstance(entrypoint, dict):
            raise ResearchctlError("Manifest entrypoints must be locator objects")
        resolve_locator(repo, package, entrypoint, require_file=True)
        entrypoint_keys.add(locator_key(entrypoint))

    documents: dict[tuple[str, str], dict[str, object]] = {}
    for root_spec in roots:
        if not isinstance(root_spec, dict):
            raise ResearchctlError("Manifest roots must be objects")
        base = root_spec.get("base")
        raw_path = root_spec.get("path")
        includes = root_spec.get("include")
        default_role = root_spec.get("role", "document")
        if (
            base not in {"repo", "package"}
            or not isinstance(raw_path, str)
            or not isinstance(includes, list)
            or not includes
            or not all(isinstance(item, str) and item for item in includes)
            or not isinstance(default_role, str)
            or not default_role
        ):
            raise ResearchctlError(f"Invalid manifest root: {root_spec!r}")
        root_path = resolve_locator(repo, package, root_spec)
        if not root_path.is_dir():
            raise ResearchctlError(f"Manifest root is not a directory: {root_path}")
        for candidate in root_path.rglob("*"):
            if candidate.is_symlink():
                raise ResearchctlError(f"Refusing symbolic link in corpus: {candidate}")
        locator_root = repo if base == "repo" else package
        for pattern in includes:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                raise ResearchctlError(f"Unsafe include pattern: {pattern!r}")
            for candidate in root_path.glob(pattern):
                if not candidate.is_file():
                    continue
                reject_symlink_path(repo, candidate)
                locator = relative_locator(str(base), locator_root, candidate)
                key = locator_key(locator)
                documents[key] = {
                    **locator,
                    "role": (
                        "entrypoint"
                        if key in entrypoint_keys
                        else inferred_document_role(candidate, default_role)
                    ),
                    "bytes": candidate.stat().st_size,
                    "sha256": sha256_file(candidate),
                }
    missing_entrypoints = entrypoint_keys - set(documents)
    if missing_entrypoints:
        rendered = ", ".join(f"{base}:{path}" for base, path in missing_entrypoints)
        raise ResearchctlError(
            f"Entrypoints are outside the declared document set: {rendered}"
        )
    return [documents[key] for key in sorted(documents)]


def frontmatter_input_documents(text: str) -> list[str]:
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---\n", 4)
    if end < 0:
        return []
    lines = text[4:end].splitlines()
    results: list[str] = []
    active_indent: int | None = None
    for line in lines:
        if re.match(r"^inputDocuments\s*:\s*$", line):
            active_indent = 0
            continue
        if active_indent is None:
            continue
        match = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if match:
            value = match.group(1).strip().strip("\"'")
            if value:
                results.append(value)
            continue
        if line.strip() and not line[:1].isspace():
            break
    return results


def local_markdown_targets(text: str) -> list[str]:
    targets: list[str] = []
    for line in visible_markdown_lines(text):
        for match in MARKDOWN_LINK_RE.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<") and ">" in raw:
                raw = raw[1 : raw.find(">")]
            elif " " in raw:
                raw = raw.split(" ", 1)[0]
            if raw:
                targets.append(raw)
    return targets


def reference_diagnostics(
    repo: Path,
    package: Path,
    documents: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for document in documents:
        if document.get("role") == "snapshot":
            continue
        try:
            path = resolve_locator(repo, package, document, require_file=True)
        except ResearchctlError as exc:
            errors.append(str(exc))
            continue
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append(f"{path}: Markdown document is not UTF-8")
            continue
        for raw_target in local_markdown_targets(text):
            parsed = urllib.parse.urlsplit(raw_target)
            if parsed.scheme or raw_target.startswith(("#", "mailto:", "data:")):
                continue
            decoded = urllib.parse.unquote(parsed.path)
            if not decoded:
                continue
            candidate = Path(decoded).expanduser()
            if candidate.is_absolute():
                warnings.append(
                    f"{path}: absolute Markdown reference is not portable: {decoded}"
                )
                if not candidate.exists():
                    errors.append(f"{path}: missing absolute Markdown target: {decoded}")
                continue
            resolved = (path.parent / candidate).resolve()
            try:
                resolved.relative_to(repo)
            except ValueError:
                errors.append(f"{path}: Markdown reference escapes repository: {decoded}")
                continue
            if not resolved.exists():
                errors.append(f"{path}: missing Markdown target: {decoded}")
        for raw_target in frontmatter_input_documents(text):
            candidate = Path(raw_target).expanduser()
            if candidate.is_absolute():
                warnings.append(
                    f"{path}: absolute inputDocuments path is not portable: "
                    f"{raw_target}"
                )
                if not candidate.exists():
                    errors.append(
                        f"{path}: missing absolute inputDocuments target: {raw_target}"
                    )
                continue
            resolved = (repo / candidate).resolve()
            try:
                resolved.relative_to(repo)
            except ValueError:
                errors.append(
                    f"{path}: inputDocuments path escapes repository: {raw_target}"
                )
                continue
            if not resolved.exists():
                errors.append(f"{path}: missing inputDocuments target: {raw_target}")
    return errors, warnings


def refresh_manifest(
    repo: Path,
    research_path: Path,
) -> tuple[dict[str, object], list[str], list[str]]:
    data, _, _ = parse_frontmatter(research_path.read_text(encoding="utf-8"))
    path = manifest_path(research_path, data)
    manifest = load_manifest(path)
    if manifest.get("status") != "active":
        raise ResearchctlError("Only an active manifest can be refreshed")
    documents = discover_documents(repo, research_path.parent, manifest)
    manifest["documents"] = documents
    manifest["payload_sha256"] = ""
    errors, warnings = reference_diagnostics(
        repo, research_path.parent, documents
    )
    atomic_write(path, manifest_text(manifest))
    return manifest, errors, warnings


def find_research(repo: Path, research_id: str, state: str | None = None) -> Path:
    match = RESEARCH_ID_RE.fullmatch(research_id.strip().upper())
    if not match:
        raise ResearchctlError(f"Invalid Research ID: {research_id!r}")
    canonical = f"R-{int(match.group(1)):03d}"
    roots: list[Path] = []
    if state in {None, "active"}:
        roots.append(repo / "docs" / "research" / "active")
    if state in {None, "completed"}:
        roots.append(repo / "docs" / "research" / "completed")
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("r-*/RESEARCH.md"):
            try:
                data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            except (OSError, ResearchctlError):
                continue
            if data.get("id", "").upper() == canonical:
                matches.append(path)
    if not matches:
        suffix = f" in {state}" if state else ""
        raise ResearchctlError(f"Research {canonical} not found{suffix}")
    if len(matches) > 1:
        raise ResearchctlError(f"Duplicate Research {canonical}: {matches}")
    return matches[0]


def research_paths(repo: Path) -> list[Path]:
    paths: list[Path] = []
    for state in ("active", "completed"):
        root = repo / "docs" / "research" / state
        if root.exists():
            paths.extend(root.glob("r-*/RESEARCH.md"))
    return sorted(paths)


def index_row(repo: Path, path: Path) -> str:
    data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    relative = path.relative_to(repo / "docs").as_posix()
    synthesis = synthesis_path(path, data).relative_to(repo / "docs").as_posix()
    return (
        f"| {data.get('id', '')} | {md_cell(data.get('title', ''))} | "
        f"{research_type_label(data.get('research_type', 'legacy'))} | "
        f"{md_cell(data.get('status', ''))} | "
        f"{md_cell(data.get('maturity', 'legacy'))} | "
        f"{display_value(data.get('owner', ''))} | "
        f"{md_cell(data.get('updated', ''))} | "
        f"[Synthesis]({synthesis}) | [Research]({relative}) |"
    )


def replace_index_table(text: str, table: str, rows: list[str]) -> str:
    start_marker = f"<!-- RCTL:{table}:START -->"
    end_marker = f"<!-- RCTL:{table}:END -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end < start:
        raise ResearchctlError(f"Malformed Research index markers for {table}")
    body_start = start + len(start_marker)
    header = (
        "| ID | Title | Type | Status | Maturity | Owner | Updated | "
        "Synthesis | Path |"
    )
    divider = "|---|---|---|---|---|---|---|---|---|"
    ordered = sorted(
        rows,
        key=lambda row: int(RESEARCH_ID_RE.search(row).group(1)),
    )
    replacement = "\n" + "\n".join((header, divider, *ordered)) + "\n"
    return text[:body_start] + replacement + text[end:]


def rebuild_index(repo: Path) -> int:
    init_repo(repo)
    active_rows: list[str] = []
    completed_rows: list[str] = []
    for path in research_paths(repo):
        row = index_row(repo, path)
        if "/active/" in path.as_posix():
            active_rows.append(row)
        else:
            completed_rows.append(row)
    index = repo / "docs" / "RESEARCH.md"
    text = index.read_text(encoding="utf-8")
    if "<!-- RCTL:ACTIVE:START -->" not in text:
        text = text.rstrip() + "\n\n" + asset_text("research-index.md")
    text = replace_index_table(text, "ACTIVE", active_rows)
    text = replace_index_table(text, "COMPLETED", completed_rows)
    atomic_write(index, text)
    return len(active_rows) + len(completed_rows)


def new_research(
    repo: Path,
    slug: str,
    title: str,
    owner: str,
    author: str,
    research_type: str,
    corpus_roots: list[str],
    entrypoint_values: list[str],
    includes: list[str],
) -> Path:
    validate_slug(slug)
    research_type = validate_research_type(research_type)
    with repo_lock(repo):
        init_repo(repo)
        item_id = next_research_id(repo)
        number = int(item_id.split("-")[1])
        directory_name = f"r-{number:03d}_{slug}"
        directory = repo / "docs" / "research" / "active" / directory_name
        research_path = directory / "RESEARCH.md"
        synthesis_path = directory / "SYNTHESIS.md"
        manifest_file = directory / MANIFEST_NAME
        if directory.exists():
            raise ResearchctlError(f"Destination already exists: {directory}")

        root_specs: list[dict[str, object]] = []
        entrypoints: list[dict[str, str]] = []
        mode = "managed"
        include_patterns = includes or ["**/*.md"]
        if corpus_roots:
            mode = "linked"
            resolved_roots = [
                normalized_existing_path(repo, value, "Corpus root")
                for value in corpus_roots
            ]
            for root in resolved_roots:
                if not root.is_dir():
                    raise ResearchctlError(f"Corpus root is not a directory: {root}")
                root_specs.append(
                    {
                        "base": "repo",
                        "path": root.relative_to(repo).as_posix(),
                        "include": include_patterns,
                    }
                )
            for raw in entrypoint_values:
                candidate = Path(raw).expanduser()
                if not candidate.is_absolute():
                    repo_candidate = repo / candidate
                    if repo_candidate.exists():
                        candidate = repo_candidate
                    elif len(resolved_roots) == 1:
                        candidate = resolved_roots[0] / candidate
                resolved = normalized_existing_path(
                    repo, str(candidate), "Entrypoint"
                )
                if not resolved.is_file():
                    raise ResearchctlError(f"Entrypoint is not a file: {resolved}")
                if not any(
                    resolved == root or root in resolved.parents
                    for root in resolved_roots
                ):
                    raise ResearchctlError(
                        f"Entrypoint is outside declared corpus roots: {resolved}"
                    )
                entrypoints.append(
                    {
                        "base": "repo",
                        "path": resolved.relative_to(repo).as_posix(),
                    }
                )
        else:
            if entrypoint_values:
                raise ResearchctlError(
                    "--entrypoint requires at least one --corpus-root"
                )
        root_specs.append(
            {
                "base": "package",
                "path": "notes",
                "include": (
                    ["**/*.md"] if corpus_roots else include_patterns
                ),
            }
        )
        root_specs.extend(
            (
                {
                    "base": "package",
                    "path": "rounds",
                    "include": ["**/*.md"],
                    "role": "round",
                },
                {
                    "base": "package",
                    "path": "snapshots",
                    "include": ["**/*.md"],
                    "role": "snapshot",
                },
            )
        )

        research_text = render_asset(
            "research.md",
            {
                "ID": item_id,
                "TITLE": yaml_string(title),
                "OWNER": yaml_string(owner),
                "OWNER_LABEL": display_value(owner),
                "AUTHOR": yaml_string(author),
                "AUTHOR_LABEL": display_value(author),
                "RESEARCH_TYPE": research_type,
                "RESEARCH_TYPE_LABEL": research_type_label(research_type),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
                "DIR_NAME": directory_name,
            },
        )
        synthesis_text = render_asset(
            "synthesis.md",
            {
                "PARENT_ID": item_id,
                "TITLE": yaml_string(f"{title} — Synthesis"),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
            },
        )
        round_text = render_asset(
            "round.md",
            {
                "ROUND_ID": "RR-001",
                "PARENT_ID": item_id,
                "TITLE": yaml_string(f"{title} — RR-001 Baseline investigation"),
                "DATE": date_string(),
                "AUTHOR": yaml_string(author),
            },
        )
        manifest = json.loads(
            render_asset(
                "manifest.json",
                {
                    "ID": item_id,
                    "MODE": mode,
                    "ROOTS_JSON": json.dumps(
                        root_specs, ensure_ascii=False, indent=2
                    ),
                    "ENTRYPOINTS_JSON": json.dumps(
                        entrypoints, ensure_ascii=False, indent=2
                    ),
                },
            )
        )
        try:
            atomic_write(research_path, research_text)
            atomic_write(synthesis_path, synthesis_text)
            (directory / "notes").mkdir()
            (directory / "rounds").mkdir()
            (directory / "snapshots").mkdir()
            (directory / "artifacts").mkdir()
            atomic_write(directory / "rounds" / "rr-001_baseline.md", round_text)
            atomic_write(manifest_file, manifest_text(manifest))
            refresh_manifest(repo, research_path)
            rebuild_index(repo)
        except Exception:
            if directory.exists():
                shutil.rmtree(directory)
            rebuild_index(repo)
            raise
        return research_path


def validate_sections(path: Path, text: str, headings: Iterable[str]) -> list[str]:
    errors: list[str] = []
    for heading in headings:
        values = section_values(text, heading)
        if not values:
            errors.append(f"{path}: missing ## {heading}")
        elif len(values) > 1:
            errors.append(f"{path}: duplicate ## {heading}")
    return errors


def validate_section_order(
    path: Path,
    text: str,
    headings: tuple[str, ...],
) -> list[str]:
    if any(len(section_values(text, heading)) != 1 for heading in headings):
        return []
    required = set(headings)
    observed = tuple(
        heading for heading, _ in markdown_sections(text) if heading in required
    )
    if observed != headings:
        return [f"{path}: required topic sections are out of order"]
    return []


def topic_evidence_records(text: str) -> list[tuple[str, str]]:
    body = section(text, "Evidence") or ""
    matches = list(
        re.finditer(
            r"(?m)^###\s+(E-\d{3,})\b[^\n]*(?:\n|$)",
            body,
            re.IGNORECASE,
        )
    )
    return [
        (
            match.group(1).upper(),
            body[
                match.end() : (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(body)
                )
            ].strip(),
        )
        for index, match in enumerate(matches)
    ]


def topic_finding_rows(text: str) -> list[list[str]]:
    body = section(text, "Findings") or ""
    rows: list[list[str]] = []
    for line in visible_markdown_lines(body):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells or cells[0].lower() == "id" or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


def topic_claim_records(text: str) -> list[tuple[str, str]]:
    body = section(text, "Claims and Evidence") or ""
    matches = list(
        re.finditer(
            r"(?m)^###\s+(C-\d{3,})\b[^\n]*(?:\n|$)",
            body,
            re.IGNORECASE,
        )
    )
    return [
        (
            match.group(1).upper(),
            body[
                match.end() : (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(body)
                )
            ].strip(),
        )
        for index, match in enumerate(matches)
    ]


def markdown_label_value(
    text: str,
    label: str,
    labels: tuple[str, ...],
) -> tuple[int, str] | None:
    prefix = r"(?m)^\s*(?:>\s*)?"
    label_pattern = (
        rf"{prefix}\*\*{re.escape(label)}[:：]?\*\*"
    )
    match = re.search(label_pattern, text, re.IGNORECASE)
    if not match:
        return None
    next_positions = [
        candidate.start()
        for other_label in labels
        for candidate in re.finditer(
            rf"{prefix}\*\*{re.escape(other_label)}[:：]?\*\*",
            text[match.end() :],
            re.IGNORECASE,
        )
    ]
    end = (
        match.end() + min(next_positions)
        if next_positions
        else len(text)
    )
    value = re.sub(
        r"<!--[\s\S]*?-->",
        "",
        text[match.end() : end],
    )
    value = re.sub(r"(?m)^\s*>\s?", "", value).strip()
    return match.start(), value


def markdown_alias_label_value(
    text: str,
    aliases: tuple[str, ...],
    all_labels: tuple[str, ...],
) -> tuple[int, str] | None:
    candidates = [
        value
        for alias in aliases
        if (value := markdown_label_value(text, alias, all_labels))
        is not None
    ]
    return min(candidates, key=lambda value: value[0]) if candidates else None


def topic_role_entries(text: str) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for heading, lines in markdown_sections(text):
        body = "\n".join(lines).strip()
        for role in TOPIC_ROLE_RE.findall(body):
            entries.append((role.lower(), heading, body))
    return entries


def markdown_level_three_sections(
    text: str,
) -> list[tuple[str, list[str]]]:
    result: list[tuple[str, list[str]]] = []
    heading: str | None = None
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            if heading is not None:
                lines.append(line)
            continue
        match = (
            re.match(r"^###\s+(.+?)\s*#*\s*$", line)
            if fence is None
            else None
        )
        if match:
            if heading is not None:
                result.append((heading, lines))
            heading = match.group(1).strip()
            lines = []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        result.append((heading, lines))
    return result


def topic_analysis_records(
    body: str,
) -> list[tuple[str, str, str]]:
    records: list[tuple[str, str, str]] = []
    for heading, lines in markdown_level_three_sections(body):
        ids = normalized_topic_ids(
            TOPIC_ANALYSIS_ID_RE,
            "A",
            heading,
        )
        if len(ids) == 1:
            records.append(
                (
                    next(iter(ids)),
                    heading,
                    "\n".join(lines).strip(),
                )
            )
    return records


def topic_table_rows(body: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in visible_markdown_lines(body):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells:
            continue
        first = re.sub(r"<[^>]+>", "", cells[0]).strip()
        if (
            first.lower() == "id"
            or first in {"影响的分析", "Analysis"}
            or (first and set(first) <= {"-", ":"})
        ):
            continue
        rows.append(cells)
    return rows


def normalized_topic_ids(
    pattern: re.Pattern[str],
    prefix: str,
    text: str,
) -> set[str]:
    return {
        f"{prefix}-{int(value):03d}"
        for value in pattern.findall(text)
    }


def visible_topic_text(text: str) -> str:
    without_comments = re.sub(r"<!--[\s\S]*?-->", "", text)
    return re.sub(r"\s+", " ", without_comments).strip()


def validate_learning_topic_document(
    path: Path,
    text: str,
    valid_question_ids: set[str],
    quality_mode: str,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    quality_issues: list[str] = []
    entries = topic_role_entries(text)
    known_roles = set(TOPIC_V21_ROLES)
    for role, heading, _ in entries:
        if role not in known_roles:
            errors.append(
                f"{path}: ## {heading} declares unknown topic role {role!r}"
            )

    by_role: dict[str, list[tuple[str, str]]] = {
        role: [] for role in TOPIC_V21_ROLES
    }
    for role, heading, body in entries:
        if role in by_role:
            by_role[role].append((heading, body))
    for role in TOPIC_V21_ROLES:
        if not by_role[role]:
            errors.append(f"{path}: missing topic role {role}")
        elif len(by_role[role]) > 1:
            errors.append(f"{path}: duplicate topic role {role}")

    if all(len(by_role[role]) == 1 for role in TOPIC_V21_ROLES):
        observed = tuple(
            role for role, _, _ in entries if role in known_roles
        )
        if observed != TOPIC_V21_ROLES:
            errors.append(f"{path}: required topic roles are out of order")

    for heading, lines in markdown_sections(text):
        roles = TOPIC_ROLE_RE.findall("\n".join(lines))
        if len(roles) > 1:
            errors.append(
                f"{path}: ## {heading} declares multiple topic roles"
            )

    def role_body(role: str) -> str:
        values = by_role[role]
        return values[0][1] if len(values) == 1 else ""

    brief_body = role_body("decision-brief")
    question_ids = normalized_topic_ids(
        RESEARCH_QUESTION_ID_RE,
        "RQ",
        brief_body,
    )
    if not question_ids:
        errors.append(f"{path}: topic must reference at least one RQ-NNN")
    for question_id in sorted(question_ids - valid_question_ids):
        errors.append(
            f"{path}: topic references unknown Research Question {question_id}"
        )

    brief_fields = {
        canonical: markdown_alias_label_value(
            brief_body,
            aliases,
            TOPIC_V21_BRIEF_LABELS,
        )
        for canonical, aliases in TOPIC_V21_BRIEF_FIELDS
    }
    for canonical, field in brief_fields.items():
        if field is None:
            quality_issues.append(
                f"{path}: decision brief is missing {canonical}"
            )
        elif not field[1]:
            quality_issues.append(
                f"{path}: decision brief has empty {canonical}"
            )
    brief_positions = [
        field[0]
        for field in brief_fields.values()
        if field is not None
    ]
    if len(brief_positions) == len(TOPIC_V21_BRIEF_FIELDS):
        if brief_positions != sorted(brief_positions):
            quality_issues.append(
                f"{path}: decision brief fields are out of order"
            )
    brief_confidence = brief_fields["Confidence"]
    if brief_confidence and not re.match(
        r"(high|medium|low)\b",
        brief_confidence[1],
        re.IGNORECASE,
    ):
        quality_issues.append(
            f"{path}: decision brief confidence must start with "
            "high, medium, or low"
        )

    if quality_mode == "strict":
        parsed_roles = {"analysis", "falsifiers", "evidence-index"}
        for role in TOPIC_V21_ROLES:
            if role in parsed_roles:
                continue
            if not visible_topic_text(role_body(role)):
                quality_issues.append(
                    f"{path}: topic role {role} needs substantive content"
                )

    analysis_body = role_body("analysis")
    analysis_sections = markdown_level_three_sections(analysis_body)
    for heading, _ in analysis_sections:
        ids = normalized_topic_ids(
            TOPIC_ANALYSIS_ID_RE,
            "A",
            heading,
        )
        if len(ids) != 1:
            errors.append(
                f"{path}: analysis heading must contain one A-NNN: "
                f"{heading!r}"
            )
    analysis_records = topic_analysis_records(analysis_body)
    if not analysis_records:
        quality_issues.append(
            f"{path}: topic needs at least one A-NNN analysis section"
        )
    analysis_by_id: dict[str, str] = {}
    analysis_evidence: dict[str, set[str]] = {}
    for analysis_id, _, body in analysis_records:
        if analysis_id in analysis_by_id:
            errors.append(
                f"{path}: duplicate topic analysis id {analysis_id}"
            )
        analysis_by_id[analysis_id] = body
        visible = visible_topic_text(body)
        if len(visible) < TOPIC_MIN_ANALYSIS_CHARS:
            quality_issues.append(
                f"{path}: {analysis_id} needs explanatory analysis, "
                f"not only a conclusion ({TOPIC_MIN_ANALYSIS_CHARS}+ chars)"
            )
        evidence_ids = normalized_topic_ids(
            TOPIC_EVIDENCE_ID_RE,
            "E",
            body,
        )
        analysis_evidence[analysis_id] = evidence_ids
        if not evidence_ids:
            quality_issues.append(
                f"{path}: {analysis_id} must cite at least one E-NNN"
            )

    evidence_rows = topic_table_rows(role_body("evidence-index"))
    if not evidence_rows:
        quality_issues.append(
            f"{path}: evidence index needs at least one E-NNN row"
        )
    evidence_supports: dict[str, set[str]] = {}
    evidence_sources: dict[str, set[str]] = {}
    for cells in evidence_rows:
        if len(cells) < 5:
            errors.append(
                f"{path}: evidence index rows need five columns"
            )
            continue
        evidence_cell = re.sub(r"<[^>]+>", "", cells[0]).strip()
        evidence_id = evidence_cell.upper()
        if not TOPIC_EVIDENCE_ID_RE.fullmatch(evidence_id):
            errors.append(
                f"{path}: invalid evidence index id {evidence_cell!r}"
            )
            continue
        if evidence_id in evidence_supports:
            errors.append(
                f"{path}: duplicate evidence index id {evidence_id}"
            )
        if not cells[1]:
            quality_issues.append(
                f"{path}: {evidence_id} needs an observation"
            )
        if not cells[2]:
            quality_issues.append(
                f"{path}: {evidence_id} needs an exact source"
            )
        supports = normalized_topic_ids(
            TOPIC_ANALYSIS_ID_RE,
            "A",
            cells[3],
        )
        evidence_supports[evidence_id] = supports
        evidence_sources[evidence_id] = normalized_topic_ids(
            TOPIC_SOURCE_ID_RE,
            "S",
            cells[2],
        )
        if not supports:
            quality_issues.append(
                f"{path}: {evidence_id} must support at least one A-NNN"
            )
        for analysis_id in sorted(supports - set(analysis_by_id)):
            errors.append(
                f"{path}: {evidence_id} supports unknown analysis "
                f"{analysis_id}"
            )
        if cells[4].lower() not in TOPIC_CONFIDENCE_LEVELS:
            quality_issues.append(
                f"{path}: {evidence_id} confidence must be "
                "high, medium, or low"
            )

    known_evidence = set(evidence_supports)
    for analysis_id, evidence_ids in analysis_evidence.items():
        for evidence_id in sorted(evidence_ids - known_evidence):
            errors.append(
                f"{path}: {analysis_id} cites unknown evidence {evidence_id}"
            )
        for evidence_id in sorted(evidence_ids & known_evidence):
            if analysis_id not in evidence_supports[evidence_id]:
                quality_issues.append(
                    f"{path}: {evidence_id} must list {analysis_id} "
                    "in Supports"
                )
    for evidence_id, supports in evidence_supports.items():
        for analysis_id in sorted(supports & set(analysis_by_id)):
            if evidence_id not in analysis_evidence.get(analysis_id, set()):
                quality_issues.append(
                    f"{path}: {analysis_id} must cite {evidence_id} "
                    "listed by the evidence index"
                )

    falsifier_rows = topic_table_rows(role_body("falsifiers"))
    if not falsifier_rows:
        quality_issues.append(
            f"{path}: falsifiers need at least one analysis-linked row"
        )
    for cells in falsifier_rows:
        if len(cells) < 4:
            errors.append(f"{path}: falsifier rows need four columns")
            continue
        analysis_ids = normalized_topic_ids(
            TOPIC_ANALYSIS_ID_RE,
            "A",
            cells[0],
        )
        if not analysis_ids:
            quality_issues.append(
                f"{path}: falsifier row must reference an A-NNN"
            )
        for analysis_id in sorted(analysis_ids - set(analysis_by_id)):
            errors.append(
                f"{path}: falsifier references unknown analysis "
                f"{analysis_id}"
            )
        for index, name in enumerate(
            ("falsifying evidence", "decision relevance", "validation"),
            start=1,
        ):
            if not cells[index]:
                quality_issues.append(
                    f"{path}: falsifier row needs {name}"
                )

    source_body = role_body("sources")
    source_entries = [
        match.group(1).upper()
        for match in re.finditer(
            r"(?m)^\s*-\s+`?(S-\d{3,})`?\b",
            source_body,
            re.IGNORECASE,
        )
    ]
    if not source_entries:
        quality_issues.append(
            f"{path}: sources need at least one S-NNN entry"
        )
    if len(source_entries) != len(set(source_entries)):
        errors.append(f"{path}: duplicate S-NNN source entry")
    known_sources = set(source_entries)
    for evidence_id, source_ids in evidence_sources.items():
        for source_id in sorted(source_ids - known_sources):
            errors.append(
                f"{path}: {evidence_id} references unknown source "
                f"{source_id}"
            )

    if marker_names(text):
        quality_issues.append(f"{path}: required topic placeholders remain")
    if quality_mode == "strict":
        errors.extend(quality_issues)
    elif quality_mode == "warning":
        warnings.extend(quality_issues)
    return errors, warnings


def declares_topic_document(text: str) -> bool:
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---\n", 4)
    frontmatter = text[4:end] if end >= 0 else text[4:]
    return bool(
        re.search(
            r"(?m)^doc_type\s*:\s*[\"']?research-topic[\"']?\s*$",
            frontmatter,
        )
    )


def validate_topic_document(
    path: Path,
    text: str,
    data: dict[str, str],
    parent_id: str,
    valid_round_ids: set[str],
    valid_question_ids: set[str],
    quality_mode: str,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    schema_version = data.get("schema_version", "")
    if schema_version not in TOPIC_SCHEMA_VERSIONS:
        errors.append(
            f"{path}: topic schema_version must be one of "
            f"{sorted(TOPIC_SCHEMA_VERSIONS)}"
        )
        schema_version = "1"
    if data.get("doc_type") != "research-topic":
        errors.append(f"{path}: doc_type must be research-topic")
    if data.get("parent_id") != parent_id:
        errors.append(f"{path}: parent_id must be {parent_id}")
    round_id = data.get("round_id", "").upper()
    if not ROUND_ID_RE.fullmatch(round_id):
        errors.append(f"{path}: invalid topic round_id {round_id!r}")
    elif round_id not in valid_round_ids:
        errors.append(f"{path}: topic round_id {round_id} does not exist")
    for field in ("title", "author", "created", "updated"):
        if field not in data:
            errors.append(f"{path}: missing topic frontmatter field {field}")
    if not data.get("title"):
        errors.append(f"{path}: topic title must not be empty")
    if not data.get("author"):
        warnings.append(f"{path}: topic author is unassigned")
    if not SLUG_RE.fullmatch(path.stem):
        errors.append(f"{path}: topic filename must be lowercase kebab-case")

    if schema_version == "2.1":
        learning_errors, learning_warnings = (
            validate_learning_topic_document(
                path,
                text,
                valid_question_ids,
                quality_mode,
            )
        )
        errors.extend(learning_errors)
        warnings.extend(learning_warnings)
        return errors, warnings

    topic_sections = (
        TOPIC_V2_SECTIONS if schema_version == "2" else TOPIC_V1_SECTIONS
    )
    errors.extend(validate_sections(path, text, topic_sections))
    errors.extend(validate_section_order(path, text, topic_sections))

    question_heading = (
        "Decision Brief"
        if schema_version == "2"
        else "Question and Decision Relevance"
    )
    question_body = section(text, question_heading) or ""
    question_ids = {
        f"RQ-{int(value):03d}"
        for value in RESEARCH_QUESTION_ID_RE.findall(question_body)
    }
    if not question_ids:
        errors.append(f"{path}: topic must reference at least one RQ-NNN")
    for question_id in sorted(question_ids - valid_question_ids):
        errors.append(
            f"{path}: topic references unknown Research Question {question_id}"
        )

    quality_issues: list[str] = []
    if marker_names(text):
        quality_issues.append(f"{path}: required topic placeholders remain")
    if schema_version == "2":
        brief_fields = {
            label: markdown_label_value(
                question_body,
                label,
                TOPIC_BRIEF_LABELS,
            )
            for label in TOPIC_BRIEF_LABELS
        }
        for label, field in brief_fields.items():
            if field is None:
                quality_issues.append(
                    f"{path}: Decision Brief is missing {label}"
                )
            elif not field[1]:
                quality_issues.append(
                    f"{path}: Decision Brief has empty {label}"
                )
        brief_positions = [
            field[0]
            for field in brief_fields.values()
            if field is not None
        ]
        if len(brief_positions) == len(TOPIC_BRIEF_LABELS):
            if brief_positions != sorted(brief_positions):
                quality_issues.append(
                    f"{path}: Decision Brief fields are out of order"
                )
        brief_confidence = brief_fields["Confidence"]
        if brief_confidence and not re.match(
            r"(high|medium|low)\b",
            brief_confidence[1],
            re.IGNORECASE,
        ):
            quality_issues.append(
                f"{path}: Decision Brief confidence must start with "
                "high, medium, or low"
            )
    if quality_mode == "strict":
        record_sections = (
            {"Claims and Evidence"}
            if schema_version == "2"
            else {"Evidence", "Findings"}
        )
        for heading in topic_sections:
            if heading in record_sections:
                continue
            body = section(text, heading)
            visible = (
                re.sub(r"<!--[\s\S]*?-->", "", body).strip()
                if body is not None
                else ""
            )
            if not visible:
                quality_issues.append(
                    f"{path}: ## {heading} needs substantive content"
                )

    if schema_version == "2":
        claim_records = topic_claim_records(text)
        if not claim_records:
            quality_issues.append(
                f"{path}: topic needs at least one C-NNN claim"
            )
        seen_claims: set[str] = set()
        for claim_id, body in claim_records:
            if claim_id in seen_claims:
                errors.append(f"{path}: duplicate topic claim id {claim_id}")
            seen_claims.add(claim_id)
            label_positions: list[int] = []
            for label in TOPIC_CLAIM_LABELS:
                field = markdown_label_value(
                    body,
                    label,
                    TOPIC_CLAIM_LABELS,
                )
                if field is None:
                    quality_issues.append(
                        f"{path}: {claim_id} is missing {label}"
                    )
                else:
                    label_positions.append(field[0])
                    if not field[1]:
                        quality_issues.append(
                            f"{path}: {claim_id} has empty {label}"
                        )
            if len(label_positions) == len(TOPIC_CLAIM_LABELS):
                if label_positions != sorted(label_positions):
                    quality_issues.append(
                        f"{path}: {claim_id} claim fields are out of order"
                    )
            confidence = markdown_label_value(
                body,
                "Confidence",
                TOPIC_CLAIM_LABELS,
            )
            if confidence and not re.match(
                r"(high|medium|low)\b",
                confidence[1],
                re.IGNORECASE,
            ):
                quality_issues.append(
                    f"{path}: {claim_id} needs high, medium, or low confidence"
                )
    else:
        evidence_records = topic_evidence_records(text)
        if not evidence_records:
            quality_issues.append(
                f"{path}: topic needs at least one E-NNN record"
            )
        seen_evidence: set[str] = set()
        for evidence_id, body in evidence_records:
            if evidence_id in seen_evidence:
                errors.append(
                    f"{path}: duplicate topic evidence id {evidence_id}"
                )
            seen_evidence.add(evidence_id)
            for label in TOPIC_EVIDENCE_LABELS:
                if not re.search(
                    rf"\*\*{re.escape(label)}:?\*\*",
                    body,
                    re.IGNORECASE,
                ):
                    quality_issues.append(
                        f"{path}: {evidence_id} is missing {label}"
                    )
            confidence = re.search(
                r"\*\*Confidence:?\*\*\s*(?:\n\s*)?"
                r"(high|medium|low)\b",
                body,
                re.IGNORECASE,
            )
            if not confidence:
                quality_issues.append(
                    f"{path}: {evidence_id} needs high, medium, or low confidence"
                )

        finding_rows = topic_finding_rows(text)
        if not finding_rows:
            quality_issues.append(
                f"{path}: topic needs at least one F-NNN finding"
            )
        seen_findings: set[str] = set()
        for cells in finding_rows:
            if len(cells) < 5:
                errors.append(f"{path}: topic Finding rows need five columns")
                continue
            finding_id = cells[0].upper()
            if not TOPIC_FINDING_ID_RE.fullmatch(finding_id):
                errors.append(
                    f"{path}: invalid topic Finding id {cells[0]!r}"
                )
            elif finding_id in seen_findings:
                errors.append(
                    f"{path}: duplicate topic Finding id {finding_id}"
                )
            seen_findings.add(finding_id)
            if not cells[1]:
                quality_issues.append(
                    f"{path}: {finding_id} needs a finding"
                )
            if cells[2].lower() not in TOPIC_CONFIDENCE_LEVELS:
                quality_issues.append(
                    f"{path}: {finding_id} confidence must be "
                    "high, medium, or low"
                )
            if not cells[3]:
                quality_issues.append(
                    f"{path}: {finding_id} needs evidence"
                )
            if not cells[4]:
                quality_issues.append(
                    f"{path}: {finding_id} needs decision impact"
                )

    if quality_mode == "strict":
        errors.extend(quality_issues)
    elif quality_mode == "warning":
        warnings.extend(quality_issues)
    return errors, warnings


def validate_research_topics(
    research_path: Path,
    research_text: str,
    data: dict[str, str],
    quality_mode: str,
) -> tuple[list[str], list[str], list[Path]]:
    errors: list[str] = []
    warnings: list[str] = []
    topics: list[Path] = []
    valid_question_ids = {
        cells[0].upper()
        for cells in research_question_rows(research_text)
        if cells and RESEARCH_QUESTION_ID_RE.fullmatch(cells[0].upper())
    }
    round_documents: dict[str, str] = {}
    for round_path in round_paths(research_path.parent):
        try:
            round_text = round_path.read_text(encoding="utf-8")
            round_data, _, _ = parse_frontmatter(round_text)
        except (OSError, ResearchctlError):
            continue
        round_id = round_data.get("id", "").upper()
        if ROUND_ID_RE.fullmatch(round_id):
            round_documents[round_id] = round_text
    valid_round_ids = set(round_documents)

    for topic_path in topic_note_paths(research_path.parent):
        try:
            topic_text = topic_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{topic_path}: {exc}")
            continue
        declared = declares_topic_document(topic_text)
        if not declared:
            continue
        try:
            topic_data, _, _ = parse_frontmatter(topic_text)
        except ResearchctlError as exc:
            errors.append(f"{topic_path}: {exc}")
            continue
        topics.append(topic_path)
        topic_errors, topic_warnings = validate_topic_document(
            topic_path,
            topic_text,
            topic_data,
            data.get("id", ""),
            valid_round_ids,
            valid_question_ids,
            quality_mode,
        )
        errors.extend(topic_errors)
        warnings.extend(topic_warnings)
        round_id = topic_data.get("round_id", "").upper()
        if round_id in round_documents:
            expected_target = (
                "../notes/"
                + topic_path.relative_to(
                    research_path.parent / "notes"
                ).as_posix()
            )
            evidence_added = (
                section(round_documents[round_id], "Evidence Added") or ""
            )
            if expected_target not in local_markdown_targets(evidence_added):
                errors.append(
                    f"{topic_path}: {round_id} Evidence Added must link "
                    f"{expected_target}"
                )
    return errors, warnings, topics


def validate_questions(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    rows = research_question_rows(text)
    if not rows:
        return [f"{path}: Research Questions needs at least one row"]
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
            errors.append(f"{path}: invalid Research Question status {status!r}")
        elif status != "open" and not cells[3]:
            errors.append(f"{path}: {question_id} requires an answer or disposition")
        if status in {"answered", "invalidated"} and not cells[4]:
            errors.append(f"{path}: {question_id} requires evidence")
    return errors


def validate_round(
    path: Path,
    parent_id: str,
) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
    except (OSError, ResearchctlError) as exc:
        return [f"{path}: {exc}"], {}
    if data.get("schema_version") != "1":
        errors.append(f"{path}: round schema_version must be 1")
    if not ROUND_ID_RE.fullmatch(data.get("id", "")):
        errors.append(f"{path}: invalid Research Round id {data.get('id', '')!r}")
    if data.get("parent_id") != parent_id:
        errors.append(f"{path}: parent_id must be {parent_id}")
    if data.get("status") not in ROUND_STATUSES:
        errors.append(f"{path}: invalid round status {data.get('status')!r}")
    for field in ("title", "created", "updated", "author"):
        if field not in data:
            errors.append(f"{path}: missing round frontmatter field {field}")
    errors.extend(validate_sections(path, text, ROUND_SECTIONS))
    return errors, data


def validate_research_rounds(
    path: Path,
    text: str,
    data: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    parent_id = data.get("id", "")
    rows = research_round_rows(text)
    row_statuses: dict[str, str] = {}
    for cells in rows:
        if len(cells) < 6:
            errors.append(f"{path}: Research Round rows need six columns")
            continue
        round_id = cells[0].upper()
        if not ROUND_ID_RE.fullmatch(round_id):
            errors.append(f"{path}: invalid Research Round id {cells[0]!r}")
        elif round_id in row_statuses:
            errors.append(f"{path}: duplicate Research Round id {round_id}")
        row_statuses[round_id] = cells[2].lower()

    document_statuses: dict[str, str] = {}
    for round_path in round_paths(path.parent):
        round_errors, round_data = validate_round(round_path, parent_id)
        errors.extend(round_errors)
        round_id = round_data.get("id", "").upper()
        if round_id:
            if round_id in document_statuses:
                errors.append(f"{path}: duplicate Research Round document {round_id}")
            document_statuses[round_id] = round_data.get("status", "")
    if not document_statuses:
        errors.append(f"{path}: schema 1.1 Research requires at least one round")
    if set(row_statuses) != set(document_statuses):
        errors.append(
            f"{path}: Research Rounds table and rounds/ documents do not match"
        )
    for round_id in sorted(set(row_statuses) & set(document_statuses)):
        if row_statuses[round_id] != document_statuses[round_id]:
            errors.append(
                f"{path}: {round_id} table status {row_statuses[round_id]!r} "
                f"does not match document status {document_statuses[round_id]!r}"
            )

    current_round = data.get("current_round", "").upper()
    if current_round not in document_statuses:
        errors.append(f"{path}: current_round {current_round!r} is missing")
    elif data.get("maturity") == "review_ready":
        if document_statuses[current_round] != "completed":
            errors.append(
                f"{path}: review_ready Research requires a completed current round"
            )
    elif data.get("status") in {"active", "blocked"}:
        if document_statuses[current_round] != "active":
            errors.append(
                f"{path}: in-progress Research requires an active current round"
            )
    return errors


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
    except ResearchctlError as exc:
        return [f"{path}: {exc}"], warnings
    schema_version = data.get("schema_version")
    if schema_version not in SYNTHESIS_SCHEMA_VERSIONS:
        errors.append(
            f"{path}: synthesis schema_version must be 1 or 1.1"
        )
    if data.get("parent_id") != parent_id:
        errors.append(f"{path}: parent_id must be {parent_id}")
    errors.extend(validate_sections(path, text, SYNTHESIS_SECTIONS))
    status = data.get("status")
    allowed_statuses = (
        {"draft", "review_ready", "sealed"}
        if schema_version == "1.1"
        else {"draft", "sealed"}
    )
    if status not in allowed_statuses:
        errors.append(f"{path}: invalid synthesis status {status!r}")
    if schema_version == "1.1":
        try:
            revision = int(data.get("revision", ""))
        except ValueError:
            revision = -1
        if revision < 0:
            errors.append(f"{path}: revision must be a non-negative integer")
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
        if not expected or expected != actual:
            errors.append(f"{path}: {status} Synthesis payload changed")
    elif data.get("payload_sha256"):
        errors.append(f"{path}: draft Synthesis cannot have payload_sha256")
    elif required:
        warnings.append(f"{path}: required placeholders remain")
    return errors, warnings


def validate_synthesis_snapshots(
    package: Path,
    parent_id: str,
    current_revision: int,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    found: set[int] = set()
    payloads: dict[str, Path] = {}
    snapshot_root = package / "snapshots"
    for path in sorted(snapshot_root.glob("synthesis-v*.md")):
        match = re.fullmatch(r"synthesis-v(\d{3,})\.md", path.name)
        if not match:
            errors.append(f"{path}: invalid Synthesis snapshot filename")
            continue
        number = int(match.group(1))
        found.add(number)
        item_errors, item_warnings = validate_synthesis(
            path, parent_id, require_sealed=False
        )
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        try:
            snapshot_data, _, _ = parse_frontmatter(
                path.read_text(encoding="utf-8")
            )
        except ResearchctlError:
            continue
        if snapshot_data.get("schema_version") != "1.1":
            errors.append(f"{path}: review snapshot requires schema_version 1.1")
        if snapshot_data.get("status") != "review_ready":
            errors.append(f"{path}: review snapshot must be review_ready")
        if snapshot_data.get("revision") != str(number):
            errors.append(f"{path}: revision must match snapshot filename")
        snapshot_payload = payload_sha256(path.read_text(encoding="utf-8"))
        if snapshot_payload in payloads:
            warnings.append(
                f"{path}: duplicates Synthesis payload already preserved by "
                f"{payloads[snapshot_payload]}"
            )
        else:
            payloads[snapshot_payload] = path
    future = sorted(number for number in found if number > current_revision)
    if future:
        errors.append(
            f"{snapshot_root}: snapshot revisions {future} exceed current "
            f"Synthesis revision {current_revision}"
        )
    return errors, warnings


def validate_manifest(
    repo: Path,
    research_path: Path,
    parent_id: str,
    require_sealed: bool,
) -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_manifest(manifest_path(research_path))
    except ResearchctlError as exc:
        return [str(exc)], warnings, {}
    if manifest.get("schema_version") != "1":
        errors.append(f"{manifest_path(research_path)}: schema_version must be 1")
    if manifest.get("research_id") != parent_id:
        errors.append(
            f"{manifest_path(research_path)}: research_id must be {parent_id}"
        )
    status = manifest.get("status")
    mode = manifest.get("mode")
    if status not in {"active", "sealed"}:
        errors.append(f"{manifest_path(research_path)}: invalid status {status!r}")
    if mode not in {"managed", "linked", "snapshot"}:
        errors.append(f"{manifest_path(research_path)}: invalid mode {mode!r}")
    documents = manifest.get("documents")
    if not isinstance(documents, list):
        errors.append(f"{manifest_path(research_path)}: documents must be an array")
        documents = []
    if require_sealed and status != "sealed":
        errors.append(f"{manifest_path(research_path)}: manifest must be sealed")
    if status == "sealed":
        expected = manifest.get("payload_sha256")
        actual = manifest_digest(manifest)
        if not isinstance(expected, str) or not expected or expected != actual:
            errors.append(
                f"{manifest_path(research_path)}: sealed manifest payload changed"
            )
        seen: set[tuple[str, str]] = set()
        for document in documents:
            if not isinstance(document, dict):
                errors.append(
                    f"{manifest_path(research_path)}: document must be an object"
                )
                continue
            key = locator_key(document)
            if key in seen:
                errors.append(
                    f"{manifest_path(research_path)}: duplicate document {key}"
                )
            seen.add(key)
            try:
                path = resolve_locator(
                    repo, research_path.parent, document, require_file=True
                )
            except ResearchctlError as exc:
                errors.append(str(exc))
                continue
            expected_hash = document.get("sha256")
            expected_bytes = document.get("bytes")
            if expected_hash != sha256_file(path):
                errors.append(f"{path}: sealed document digest changed")
            if expected_bytes != path.stat().st_size:
                errors.append(f"{path}: sealed document size changed")
    else:
        if manifest.get("payload_sha256"):
            errors.append(
                f"{manifest_path(research_path)}: active manifest cannot be sealed"
            )
        try:
            discovered = discover_documents(repo, research_path.parent, manifest)
            if discovered != documents:
                errors.append(
                    f"{manifest_path(research_path)}: manifest drift; "
                    "run sync-research"
                )
            reference_errors, reference_warnings = reference_diagnostics(
                repo, research_path.parent, discovered
            )
            errors.extend(reference_errors)
            warnings.extend(reference_warnings)
        except ResearchctlError as exc:
            errors.append(str(exc))
    return errors, warnings, manifest


def validate_research(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        data, _, _ = parse_frontmatter(text)
    except ResearchctlError as exc:
        return [f"{path}: {exc}"], warnings
    research_id = data.get("id", "")
    if not RESEARCH_ID_RE.fullmatch(research_id):
        errors.append(f"{path}: invalid Research id {research_id!r}")
    schema_version = data.get("schema_version")
    if schema_version not in RESEARCH_SCHEMA_VERSIONS:
        errors.append(f"{path}: schema_version must be 1 or 1.1")
    for field in ("title", "created", "updated", "synthesis"):
        if not data.get(field):
            errors.append(f"{path}: missing frontmatter field {field}")
    if schema_version == "1.1":
        for field in (
            "owner",
            "author",
            "maturity",
            "research_type",
            "current_round",
            "synthesis_revision",
            "approved_by",
            "approved_at",
            "approval_ref",
        ):
            if field not in data:
                errors.append(f"{path}: missing frontmatter field {field}")
        if data.get("research_type") not in RESEARCH_TYPES:
            errors.append(
                f"{path}: invalid research_type {data.get('research_type')!r}"
            )
        if data.get("maturity") not in RESEARCH_MATURITY:
            errors.append(f"{path}: invalid maturity {data.get('maturity')!r}")
        if not ROUND_ID_RE.fullmatch(data.get("current_round", "")):
            errors.append(
                f"{path}: invalid current_round {data.get('current_round')!r}"
            )
        try:
            synthesis_revision = int(data.get("synthesis_revision", ""))
        except ValueError:
            synthesis_revision = -1
        if synthesis_revision < 0:
            errors.append(
                f"{path}: synthesis_revision must be a non-negative integer"
            )
        expected_metadata = research_metadata_body(data)
        if section(text, "Research Metadata") != expected_metadata:
            errors.append(
                f"{path}: Research Metadata projection drift; run sync-research"
            )
        errors.extend(validate_research_rounds(path, text, data))
        if synthesis_revision >= 0:
            snapshot_errors, snapshot_warnings = validate_synthesis_snapshots(
                path.parent,
                research_id,
                synthesis_revision,
            )
            errors.extend(snapshot_errors)
            warnings.extend(snapshot_warnings)
        if not data.get("owner"):
            warnings.append(
                f"{path}: Research Owner is unassigned; conclusion is forbidden"
            )
        if not data.get("author"):
            warnings.append(f"{path}: Research author is unassigned")
    location = "completed" if "/completed/" in path.as_posix() else "active"
    status = data.get("status")
    allowed = {"active", "blocked"} if location == "active" else {
        "concluded",
        "cancelled",
    }
    if status not in allowed:
        errors.append(f"{path}: status {status!r} is invalid in {location}")
    errors.extend(
        validate_sections(
            path,
            text,
            RESEARCH_SECTIONS
            if schema_version == "1.1"
            else RESEARCH_LEGACY_SECTIONS,
        )
    )
    errors.extend(validate_questions(path, text))
    topic_quality_mode = (
        "ignore"
        if status == "cancelled"
        else "strict"
        if status == "concluded" or data.get("maturity") == "review_ready"
        else "warning"
    )
    topic_errors, topic_warnings, structured_topics = validate_research_topics(
        path,
        text,
        data,
        topic_quality_mode,
    )
    errors.extend(topic_errors)
    warnings.extend(topic_warnings)
    blockers = open_blockers(text)
    if status == "blocked" and not blockers:
        errors.append(f"{path}: blocked status requires an open blocker")
    elif location == "active" and status == "active" and blockers:
        errors.append(f"{path}: open blockers require blocked status")
    require_sealed = status == "concluded"
    try:
        checked_synthesis_path = synthesis_path(path, data)
    except ResearchctlError as exc:
        errors.append(str(exc))
        checked_synthesis_path = path.parent / "SYNTHESIS.md"
    synthesis_errors, synthesis_warnings = validate_synthesis(
        checked_synthesis_path, research_id, require_sealed
    )
    errors.extend(synthesis_errors)
    warnings.extend(synthesis_warnings)
    if schema_version == "1.1" and checked_synthesis_path.is_file():
        try:
            synthesis_data, _, _ = parse_frontmatter(
                checked_synthesis_path.read_text(encoding="utf-8")
            )
        except ResearchctlError:
            synthesis_data = {}
        if synthesis_data.get("revision") != data.get("synthesis_revision"):
            errors.append(
                f"{path}: synthesis_revision does not match SYNTHESIS.md"
            )
        expected_synthesis_status = (
            "sealed"
            if status == "concluded"
            else "review_ready"
            if data.get("maturity") == "review_ready"
            else "draft"
        )
        if status != "cancelled" and synthesis_data.get("status") != (
            expected_synthesis_status
        ):
            errors.append(
                f"{path}: maturity/status requires Synthesis status "
                f"{expected_synthesis_status!r}"
            )
    if data.get("manifest"):
        if data.get("manifest") != MANIFEST_NAME:
            errors.append(f"{path}: manifest must be {MANIFEST_NAME}")
        else:
            manifest_errors, manifest_warnings, checked_manifest = validate_manifest(
                repository_from_artifact(path),
                path,
                research_id,
                require_sealed,
            )
            errors.extend(manifest_errors)
            warnings.extend(manifest_warnings)
            manifest_documents = checked_manifest.get("documents", [])
            document_roles = {
                locator_key(document): document.get("role")
                for document in manifest_documents
                if isinstance(document, dict)
            }
            for topic_path in structured_topics:
                topic_key = (
                    "package",
                    topic_path.relative_to(path.parent).as_posix(),
                )
                if topic_key not in document_roles:
                    errors.append(
                        f"{topic_path}: structured topic is missing from manifest"
                    )
                elif document_roles[topic_key] != "topic":
                    errors.append(
                        f"{topic_path}: manifest role must be topic"
                    )
    if status == "concluded":
        if open_research_questions(text):
            errors.append(f"{path}: concluded Research has open questions")
        if blockers:
            errors.append(f"{path}: concluded Research has open blockers")
        if marker_names(text):
            errors.append(f"{path}: concluded Research has required placeholders")
        if schema_version == "1.1":
            if data.get("maturity") != "review_ready":
                errors.append(
                    f"{path}: concluded Research must have review_ready maturity"
                )
            for field in ("owner", "approved_by", "approved_at", "approval_ref"):
                if not data.get(field):
                    errors.append(
                        f"{path}: concluded Research requires {field}"
                    )
    elif status == "cancelled" and schema_version == "1.1":
        for field in ("owner", "approved_by", "approved_at", "approval_ref"):
            if not data.get(field):
                errors.append(f"{path}: cancelled Research requires {field}")
    elif marker_names(text) and status != "cancelled":
        warnings.append(f"{path}: required placeholders remain")
    return errors, warnings


def validate_repo(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for path in research_paths(repo):
        try:
            data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except ResearchctlError as exc:
            errors.append(f"{path}: {exc}")
            continue
        research_id = data.get("id", "")
        if research_id in seen:
            errors.append(f"{path}: duplicate Research id {research_id}")
        seen.add(research_id)
        item_errors, item_warnings = validate_research(path)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
    return errors, warnings


def replace_required_markers(text: str, reason: str) -> str:
    replacement = f"Cancelled before completion: {reason.strip()}"
    return re.sub(
        r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
        replacement,
        text,
    )


def require_iterative_research(
    path: Path,
    text: str,
    data: dict[str, str],
) -> None:
    if data.get("schema_version") != "1.1":
        raise ResearchctlError(
            f"{path}: iterative commands require Research schema_version 1.1"
        )
    if data.get("status") not in {"active", "blocked"}:
        raise ResearchctlError(f"{path}: Research is not active")


def set_round_status(path: Path, status: str, outcome: str) -> str:
    if status not in ROUND_STATUSES:
        raise ResearchctlError(f"Invalid round status: {status}")
    text = path.read_text(encoding="utf-8")
    candidate = update_frontmatter(
        text,
        {"status": status, "updated": date_string()},
    )
    candidate = replace_section(candidate, "Round Outcome", outcome)
    return candidate


def canonical_question_ids(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        match = RESEARCH_QUESTION_ID_RE.fullmatch(value.strip().upper())
        if not match:
            raise ResearchctlError(f"Invalid Research Question ID: {value!r}")
        question_id = f"RQ-{int(match.group(1)):03d}"
        if question_id in result:
            raise ResearchctlError(
                f"Duplicate Research Question ID: {question_id}"
            )
        result.append(question_id)
    if not result:
        raise ResearchctlError("A topic requires at least one --question")
    return result


def ensure_topic_manifest_root(
    manifest: dict[str, object],
    topic_filename: str,
) -> None:
    roots = manifest.get("roots")
    if not isinstance(roots, list):
        raise ResearchctlError("Manifest roots must be an array")
    topic_root: dict[str, object] | None = None
    for root in roots:
        if (
            isinstance(root, dict)
            and root.get("base") == "package"
            and root.get("path") == "notes"
        ):
            topic_root = root
            break
    if topic_root is None:
        topic_root = {
            "base": "package",
            "path": "notes",
            "include": ["**/*.md"],
        }
        insert_at = next(
            (
                index
                for index, root in enumerate(roots)
                if isinstance(root, dict)
                and root.get("base") == "package"
                and root.get("path") in {"rounds", "snapshots"}
            ),
            len(roots),
        )
        roots.insert(insert_at, topic_root)
        return
    includes = topic_root.get("include")
    if not isinstance(includes, list) or not all(
        isinstance(value, str) and value for value in includes
    ):
        raise ResearchctlError("Manifest notes root has invalid include patterns")
    if not any(
        value in {topic_filename, "*.md", "**/*.md", "**/*"}
        for value in includes
    ):
        includes.append(topic_filename)


def new_topic(
    repo: Path,
    research_id: str,
    slug: str,
    title: str,
    author: str,
    question_values: list[str],
) -> Path:
    validate_slug(slug)
    if not title.strip():
        raise ResearchctlError("Topic title must not be empty")
    question_ids = canonical_question_ids(question_values)
    with repo_lock(repo):
        research_path = find_research(repo, research_id, "active")
        research_text = research_path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(research_text)
        require_iterative_research(research_path, research_text, data)
        if data.get("maturity") == "review_ready":
            raise ResearchctlError(
                "Start a new round before adding a topic to review-ready Research"
            )
        valid_questions = {
            cells[0].upper()
            for cells in research_question_rows(research_text)
            if cells and RESEARCH_QUESTION_ID_RE.fullmatch(cells[0].upper())
        }
        unknown = [value for value in question_ids if value not in valid_questions]
        if unknown:
            raise ResearchctlError(
                "Topic references unknown Research Questions: "
                + ", ".join(unknown)
            )
        pre_errors, _ = validate_research(research_path)
        if pre_errors:
            raise ResearchctlError(
                "Research is invalid before creating a topic:\n- "
                + "\n- ".join(pre_errors)
            )

        current_round = data.get("current_round", "")
        round_file = find_round_path(research_path.parent, current_round)
        round_text = round_file.read_text(encoding="utf-8")
        round_data, _, _ = parse_frontmatter(round_text)
        if round_data.get("status") != "active":
            raise ResearchctlError(
                "Current Research Round must be active before adding a topic"
            )

        notes = research_path.parent / "notes"
        reject_symlink_path(repo, notes)
        notes.mkdir(exist_ok=True)
        topic_path = notes / f"{slug}.md"
        reject_symlink_path(repo, topic_path)
        if topic_path.exists():
            raise ResearchctlError(f"Topic destination already exists: {topic_path}")

        topic_author = author.strip() or data.get("author", "")
        topic_text = render_asset(
            "topic.md",
            {
                "PARENT_ID": data["id"],
                "ROUND_ID": current_round,
                "TITLE": yaml_string(title.strip()),
                "AUTHOR": yaml_string(topic_author),
                "DATE": date_string(),
                "TIMESTAMP": timestamp_string(),
                "QUESTION_LIST": "\n".join(
                    f"- `{question_id}`" for question_id in question_ids
                ),
            },
        )
        safe_title = title.strip().replace("[", r"\[").replace("]", r"\]")
        round_candidate = append_section_entry(
            round_text,
            "Evidence Added",
            f"- [{safe_title}](../notes/{topic_path.name}) — addresses "
            + ", ".join(f"`{question_id}`" for question_id in question_ids)
            + ".",
        )
        round_candidate = update_frontmatter(
            round_candidate,
            {"updated": date_string()},
        )

        manifest_file = manifest_path(research_path, data)
        manifest_before = manifest_file.read_text(encoding="utf-8")
        manifest = load_manifest(manifest_file)
        if manifest.get("status") != "active":
            raise ResearchctlError("Only active Research can add a topic")
        ensure_topic_manifest_root(manifest, topic_path.name)
        try:
            atomic_write(topic_path, topic_text)
            atomic_write(round_file, round_candidate)
            atomic_write(manifest_file, manifest_text(manifest))
            _, reference_errors, _ = refresh_manifest(repo, research_path)
            if reference_errors:
                raise ResearchctlError(
                    "Topic references are invalid:\n- "
                    + "\n- ".join(reference_errors)
                )
            post_errors, _ = validate_research(research_path)
            if post_errors:
                raise ResearchctlError(
                    "Creating a topic produced invalid artifacts:\n- "
                    + "\n- ".join(post_errors)
                )
        except Exception:
            if topic_path.exists():
                topic_path.unlink()
            atomic_write(round_file, round_text)
            atomic_write(manifest_file, manifest_before)
            raise
        return topic_path


def new_round(
    repo: Path,
    research_id: str,
    slug: str,
    title: str,
    author: str,
) -> Path:
    validate_slug(slug)
    with repo_lock(repo):
        research_path = find_research(repo, research_id, "active")
        research_text = research_path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(research_text)
        require_iterative_research(research_path, research_text, data)
        if data.get("status") != "active":
            raise ResearchctlError("Resolve blockers before starting a new round")
        if data.get("maturity") != "review_ready":
            raise ResearchctlError(
                "Start a new round only after the current Synthesis is review_ready"
            )
        synthesis_file = synthesis_path(research_path, data)
        synthesis_text = synthesis_file.read_text(encoding="utf-8")
        synthesis_data, _, _ = parse_frontmatter(synthesis_text)
        if synthesis_data.get("status") != "review_ready":
            raise ResearchctlError(
                "Current Synthesis must be review_ready before a new round"
            )
        errors, _ = validate_research(research_path)
        if errors:
            raise ResearchctlError(
                "Research is invalid before starting a new round:\n- "
                + "\n- ".join(errors)
            )

        round_id = next_round_id(research_path.parent)
        number = int(round_id.split("-")[1])
        round_file = (
            research_path.parent / "rounds" / f"rr-{number:03d}_{slug}.md"
        )
        round_author = author.strip() or data.get("author", "")
        round_text = render_asset(
            "round.md",
            {
                "ROUND_ID": round_id,
                "PARENT_ID": data["id"],
                "TITLE": yaml_string(title),
                "DATE": date_string(),
                "AUTHOR": yaml_string(round_author),
            },
        )
        research_candidate = append_round_row(
            research_text,
            round_id,
            title,
            round_author,
            date_string(),
            f"rounds/{round_file.name}",
        )
        research_candidate = update_frontmatter(
            research_candidate,
            {
                "maturity": "evidence_building",
                "current_round": round_id,
                "updated": date_string(),
            },
        )
        research_candidate = replace_section(
            research_candidate,
            "Outcome",
            "Research is active in "
            f"{round_id}. The prior review-ready Synthesis remains available "
            "under `snapshots/`.",
        )
        research_candidate = append_section_entry(
            research_candidate,
            "Revision Notes",
            f"- {timestamp_string()} — Started {round_id}: {title}.",
        )
        research_candidate = sync_research_metadata(research_candidate)
        synthesis_candidate = update_frontmatter(
            synthesis_text,
            {
                "status": "draft",
                "updated": date_string(),
                "payload_sha256": "",
            },
        )
        manifest_file = manifest_path(research_path, data)
        manifest_before = manifest_file.read_text(encoding="utf-8")
        try:
            atomic_write(round_file, round_text)
            atomic_write(research_path, research_candidate)
            atomic_write(synthesis_file, synthesis_candidate)
            refresh_manifest(repo, research_path)
            rebuild_index(repo)
            post_errors, _ = validate_research(research_path)
            if post_errors:
                raise ResearchctlError(
                    "Starting a Research round produced invalid artifacts:\n- "
                    + "\n- ".join(post_errors)
                )
        except Exception:
            if round_file.exists():
                round_file.unlink()
            atomic_write(research_path, research_text)
            atomic_write(synthesis_file, synthesis_text)
            atomic_write(manifest_file, manifest_before)
            rebuild_index(repo)
            raise
        return round_file


def matching_synthesis_snapshot(package: Path, synthesis_text: str) -> Path | None:
    expected_payload = payload_sha256(synthesis_text)
    for path in sorted((package / "snapshots").glob("synthesis-v*.md")):
        try:
            snapshot_text = path.read_text(encoding="utf-8")
            snapshot_data, _, _ = parse_frontmatter(snapshot_text)
        except (OSError, UnicodeDecodeError, ResearchctlError):
            continue
        if (
            snapshot_data.get("status") == "review_ready"
            and snapshot_data.get("payload_sha256") == expected_payload
            and payload_sha256(snapshot_text) == expected_payload
        ):
            return path
    return None


def plan_synthesis_snapshot(
    package: Path,
    synthesis_text: str,
    revision: int,
) -> tuple[Path, bool]:
    if revision <= 0:
        raise ResearchctlError(
            "A milestone snapshot requires a positive Synthesis revision"
        )
    matching = matching_synthesis_snapshot(package, synthesis_text)
    if matching is not None:
        return matching, False
    snapshot_file = package / "snapshots" / f"synthesis-v{revision:03d}.md"
    if snapshot_file.exists():
        raise ResearchctlError(
            f"Synthesis snapshot already exists with another payload: {snapshot_file}"
        )
    return snapshot_file, True


def snapshot_review_ready_synthesis(
    repo: Path,
    research_path: Path,
    data: dict[str, str],
) -> Path:
    synthesis_file = synthesis_path(research_path, data)
    synthesis_text = synthesis_file.read_text(encoding="utf-8")
    synthesis_data, _, _ = parse_frontmatter(synthesis_text)
    if synthesis_data.get("status") != "review_ready":
        raise ResearchctlError("Only a review_ready Synthesis can be snapshotted")
    try:
        revision = int(data.get("synthesis_revision", "0"))
    except ValueError as exc:
        raise ResearchctlError(
            "Research has an invalid Synthesis revision"
        ) from exc
    if revision <= 0 or synthesis_data.get("revision") != str(revision):
        raise ResearchctlError(
            "Current Synthesis revision does not match the Research controller"
        )
    pre_errors, _ = validate_research(research_path)
    if pre_errors:
        raise ResearchctlError(
            "Research is invalid before creating a milestone snapshot:\n- "
            + "\n- ".join(pre_errors)
        )
    snapshot_file, should_create = plan_synthesis_snapshot(
        research_path.parent,
        synthesis_text,
        revision,
    )
    if not should_create:
        return snapshot_file
    manifest_file = manifest_path(research_path, data)
    manifest_before = manifest_file.read_text(encoding="utf-8")
    try:
        atomic_write(snapshot_file, synthesis_text)
        _, reference_errors, _ = refresh_manifest(repo, research_path)
        if reference_errors:
            raise ResearchctlError(
                "Milestone snapshot exposed invalid corpus references:\n- "
                + "\n- ".join(reference_errors)
            )
        rebuild_index(repo)
        post_errors, _ = validate_research(research_path)
        if post_errors:
            raise ResearchctlError(
                "Creating a milestone snapshot produced invalid artifacts:\n- "
                + "\n- ".join(post_errors)
            )
    except Exception:
        if snapshot_file.exists():
            snapshot_file.unlink()
        atomic_write(manifest_file, manifest_before)
        rebuild_index(repo)
        raise
    return snapshot_file


def mark_review_ready(
    repo: Path,
    research_id: str,
    snapshot: bool = False,
) -> Path:
    with repo_lock(repo):
        research_path = find_research(repo, research_id, "active")
        research_text = research_path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(research_text)
        require_iterative_research(research_path, research_text, data)
        if data.get("status") != "active":
            raise ResearchctlError("Resolve blockers before requesting review")
        if data.get("maturity") == "review_ready":
            if snapshot:
                return snapshot_review_ready_synthesis(repo, research_path, data)
            raise ResearchctlError("Research is already review_ready")
        questions = open_research_questions(research_text)
        blockers = open_blockers(research_text)
        if questions:
            raise ResearchctlError(
                "Review readiness blocked by open questions: "
                + ", ".join(questions)
            )
        if blockers:
            raise ResearchctlError(
                "Review readiness blocked by open blockers: "
                + ", ".join(blockers)
            )
        synthesis_file = synthesis_path(research_path, data)
        synthesis_text = synthesis_file.read_text(encoding="utf-8")
        if marker_names(research_text) or marker_names(synthesis_text):
            raise ResearchctlError(
                "Review readiness blocked by required placeholders"
            )
        topic_errors, _, _ = validate_research_topics(
            research_path,
            research_text,
            data,
            "strict",
        )
        if topic_errors:
            raise ResearchctlError(
                "Review readiness blocked by structured topic quality:\n- "
                + "\n- ".join(topic_errors)
            )
        synthesis_data, _, _ = parse_frontmatter(synthesis_text)
        if synthesis_data.get("status") != "draft":
            raise ResearchctlError("Only a draft Synthesis can become review_ready")
        current_round = data.get("current_round", "")
        round_file = find_round_path(research_path.parent, current_round)
        round_text = round_file.read_text(encoding="utf-8")
        round_data, _, _ = parse_frontmatter(round_text)
        if round_data.get("status") != "active":
            raise ResearchctlError("Current Research Round must be active")

        manifest_file = manifest_path(research_path, data)
        manifest_before = manifest_file.read_text(encoding="utf-8")
        _, reference_errors, _ = refresh_manifest(repo, research_path)
        if reference_errors:
            atomic_write(manifest_file, manifest_before)
            raise ResearchctlError(
                "Review readiness blocked by corpus references:\n- "
                + "\n- ".join(reference_errors)
            )

        revision = int(data.get("synthesis_revision", "0")) + 1
        synthesis_candidate = update_frontmatter(
            synthesis_text,
            {
                "status": "review_ready",
                "revision": yaml_scalar(str(revision)),
                "updated": date_string(),
                "payload_sha256": "",
            },
        )
        synthesis_candidate = update_frontmatter(
            synthesis_candidate,
            {"payload_sha256": payload_sha256(synthesis_candidate)},
        )
        snapshot_file: Path | None = None
        create_snapshot = False
        if snapshot:
            snapshot_file, create_snapshot = plan_synthesis_snapshot(
                research_path.parent,
                synthesis_candidate,
                revision,
            )
        snapshot_note = (
            f"Milestone snapshot: `{snapshot_file.relative_to(research_path.parent)}`."
            if snapshot_file is not None
            else "No physical milestone snapshot was requested."
        )
        round_candidate = set_round_status(
            round_file,
            "completed",
            f"- {date_string()} — Completed for Synthesis review v{revision}.",
        )
        research_candidate = update_round_row_status(
            research_text, current_round, "completed"
        )
        research_candidate = update_frontmatter(
            research_candidate,
            {
                "maturity": "review_ready",
                "synthesis_revision": yaml_scalar(str(revision)),
                "updated": date_string(),
            },
        )
        research_candidate = replace_section(
            research_candidate,
            "Outcome",
            f"Research is review-ready at Synthesis v{revision}, but remains "
            "active. "
            f"{snapshot_note} Only explicit Research Owner authorization may "
            "conclude it.",
        )
        research_candidate = append_section_entry(
            research_candidate,
            "Revision Notes",
            f"- {timestamp_string()} — Marked review-ready at Synthesis "
            f"v{revision}; {snapshot_note} Research remains active.",
        )
        research_candidate = sync_research_metadata(research_candidate)
        try:
            atomic_write(round_file, round_candidate)
            atomic_write(research_path, research_candidate)
            atomic_write(synthesis_file, synthesis_candidate)
            if snapshot_file is not None and create_snapshot:
                atomic_write(snapshot_file, synthesis_candidate)
            refresh_manifest(repo, research_path)
            rebuild_index(repo)
            post_errors, _ = validate_research(research_path)
            if post_errors:
                raise ResearchctlError(
                    "Review-ready transition produced invalid artifacts:\n- "
                    + "\n- ".join(post_errors)
                )
        except Exception:
            atomic_write(round_file, round_text)
            atomic_write(research_path, research_text)
            atomic_write(synthesis_file, synthesis_text)
            atomic_write(manifest_file, manifest_before)
            if (
                snapshot_file is not None
                and create_snapshot
                and snapshot_file.exists()
            ):
                snapshot_file.unlink()
            rebuild_index(repo)
            raise
        return snapshot_file if snapshot_file is not None else synthesis_file


def snapshot_linked_documents(
    repo: Path,
    research_path: Path,
    manifest: dict[str, object],
) -> tuple[dict[str, object], Path]:
    package = research_path.parent
    artifacts = package / "artifacts"
    artifacts.mkdir(exist_ok=True)
    final_snapshot = package / SNAPSHOT_DIRECTORY
    if final_snapshot.exists():
        raise ResearchctlError(f"Snapshot destination already exists: {final_snapshot}")
    temporary = Path(
        tempfile.mkdtemp(prefix=".research-snapshot-", dir=artifacts)
    )
    roots = manifest.get("roots")
    documents = manifest.get("documents")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(roots, list) or not isinstance(documents, list):
        raise ResearchctlError("Invalid linked manifest")
    entrypoint_keys = {
        locator_key(value)
        for value in entrypoints or []
        if isinstance(value, dict)
    }
    copied: list[dict[str, object]] = []
    copied_entrypoints: list[dict[str, str]] = []
    try:
        for document in documents:
            if not isinstance(document, dict):
                raise ResearchctlError("Invalid linked document record")
            if document.get("base") == "package":
                source = resolve_locator(
                    repo, package, document, require_file=True
                )
                record = {
                    "base": "package",
                    "path": str(document.get("path", "")),
                    "role": document.get("role", "document"),
                    "bytes": source.stat().st_size,
                    "sha256": sha256_file(source),
                }
                copied.append(record)
                if locator_key(document) in entrypoint_keys:
                    copied_entrypoints.append(
                        {
                            "base": "package",
                            "path": str(document.get("path", "")),
                        }
                    )
                continue
            source = resolve_locator(repo, package, document, require_file=True)
            matching: tuple[int, Path] | None = None
            for index, root_spec in enumerate(roots, start=1):
                if not isinstance(root_spec, dict):
                    continue
                if root_spec.get("base") != "repo":
                    continue
                root = resolve_locator(repo, package, root_spec)
                if source == root or root in source.parents:
                    matching = (index, root)
                    break
            if matching is None:
                raise ResearchctlError(
                    f"Document is outside declared roots: {source}"
                )
            root_index, root = matching
            relative = source.relative_to(root)
            temporary_target = temporary / f"root-{root_index:02d}" / relative
            temporary_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, temporary_target)
            package_path = (
                Path(SNAPSHOT_DIRECTORY) / f"root-{root_index:02d}" / relative
            ).as_posix()
            record: dict[str, object] = {
                "base": "package",
                "path": package_path,
                "source_path": source.relative_to(repo).as_posix(),
                "role": document.get("role", "document"),
                "bytes": temporary_target.stat().st_size,
                "sha256": sha256_file(temporary_target),
            }
            copied.append(record)
            if locator_key(document) in entrypoint_keys:
                copied_entrypoints.append(
                    {"base": "package", "path": package_path}
                )
        os.replace(temporary, final_snapshot)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    candidate = json.loads(json.dumps(manifest))
    candidate["status"] = "sealed"
    candidate["mode"] = "snapshot"
    candidate["documents"] = sorted(copied, key=locator_key)
    candidate["entrypoints"] = sorted(copied_entrypoints, key=locator_key)
    candidate["payload_sha256"] = ""
    candidate["payload_sha256"] = manifest_digest(candidate)
    return candidate, final_snapshot


def seal_managed_manifest(manifest: dict[str, object]) -> dict[str, object]:
    candidate = json.loads(json.dumps(manifest))
    candidate["status"] = "sealed"
    candidate["payload_sha256"] = ""
    candidate["payload_sha256"] = manifest_digest(candidate)
    return candidate


def archive_research(
    repo: Path,
    research_id: str,
    outcome: str,
    reason: str,
    approved_by: str,
    approval_ref: str,
) -> Path:
    if outcome not in {"concluded", "cancelled"}:
        raise ResearchctlError("Outcome must be concluded or cancelled")
    if outcome == "cancelled" and not reason.strip():
        raise ResearchctlError("Cancelled Research requires --reason")
    if not approved_by.strip() or not approval_ref.strip():
        raise ResearchctlError(
            "Terminal Research transitions require --approved-by and "
            "--approval-ref from explicit Research Owner authorization"
        )
    with repo_lock(repo):
        path = find_research(repo, research_id, "active")
        text = path.read_text(encoding="utf-8")
        data, _, _ = parse_frontmatter(text)
        if not data.get("owner", "").strip():
            raise ResearchctlError(
                "Terminal Research transitions require an assigned owner"
            )
        if (
            outcome == "concluded"
            and data.get("schema_version") == "1.1"
            and data.get("maturity") != "review_ready"
        ):
            raise ResearchctlError(
                "Research must be review_ready before explicit conclusion"
            )
        research_synthesis_path = synthesis_path(path, data)
        synthesis_text = research_synthesis_path.read_text(encoding="utf-8")
        synthesis_data, _, _ = parse_frontmatter(synthesis_text)
        if (
            outcome == "concluded"
            and data.get("schema_version") == "1.1"
            and synthesis_data.get("status") != "review_ready"
        ):
            raise ResearchctlError(
                "Synthesis must be review_ready before explicit conclusion"
            )
        manifest_file = manifest_path(path, data)
        manifest_text_before = manifest_file.read_text(encoding="utf-8")
        linked_snapshot_path: Path | None = None
        review_snapshot_file: Path | None = None
        create_review_snapshot = False

        manifest, reference_errors, _ = refresh_manifest(repo, path)
        if outcome == "concluded":
            if reference_errors:
                raise ResearchctlError(
                    "Research conclusion blocked by corpus references:\n- "
                    + "\n- ".join(reference_errors)
                )
            questions = open_research_questions(text)
            blockers = open_blockers(text)
            if questions:
                raise ResearchctlError(
                    "Research conclusion blocked by open questions: "
                    + ", ".join(questions)
                )
            if blockers:
                raise ResearchctlError(
                    "Research conclusion blocked by open blockers: "
                    + ", ".join(blockers)
                )
            if marker_names(text) or marker_names(synthesis_text):
                raise ResearchctlError(
                    "Research conclusion blocked by required placeholders"
                )
            milestone_clause = ""
            if data.get("schema_version") == "1.1":
                try:
                    synthesis_revision = int(
                        data.get("synthesis_revision", "0")
                    )
                except ValueError as exc:
                    raise ResearchctlError(
                        "Research has an invalid Synthesis revision"
                    ) from exc
                review_snapshot_file, create_review_snapshot = (
                    plan_synthesis_snapshot(
                        path.parent,
                        synthesis_text,
                        synthesis_revision,
                    )
                )
                milestone_clause = (
                    "; preserved the latest unique review payload as "
                    f"`{review_snapshot_file.relative_to(path.parent)}`"
                )
            synthesis_candidate = update_frontmatter(
                synthesis_text,
                {"status": "sealed", "updated": date_string()},
            )
            synthesis_candidate = update_frontmatter(
                synthesis_candidate,
                {"payload_sha256": payload_sha256(synthesis_candidate)},
            )
            outcome_body = (
                f"- {date_string()} — Concluded with explicit authorization "
                f"from {approved_by.strip()} ({approval_ref.strip()}); sealed "
                f"`{MANIFEST_NAME}` and `SYNTHESIS.md`{milestone_clause}."
            )
            research_candidate = replace_section(text, "Outcome", outcome_body)
        else:
            manifest_candidate = manifest
            synthesis_candidate = replace_required_markers(synthesis_text, reason)
            research_candidate = replace_required_markers(text, reason)
            research_candidate = replace_section(
                research_candidate,
                "Outcome",
                f"- {date_string()} — Cancelled by {approved_by.strip()} "
                f"({approval_ref.strip()}): {reason.strip()}",
            )
        approval_time = timestamp_string()
        research_candidate = update_frontmatter(
            research_candidate,
            {
                "status": outcome,
                "updated": date_string(),
                "approved_by": yaml_scalar(approved_by.strip()),
                "approved_at": yaml_scalar(approval_time),
                "approval_ref": yaml_scalar(approval_ref.strip()),
            },
        )
        research_candidate = sync_research_metadata(research_candidate)
        directory = path.parent
        destination = repo / "docs" / "research" / "completed" / directory.name
        if destination.exists():
            raise ResearchctlError(f"Archive destination exists: {destination}")
        research_candidate = research_candidate.replace(
            f"docs/research/active/{directory.name}",
            f"docs/research/completed/{directory.name}",
        )
        try:
            if outcome == "concluded":
                if create_review_snapshot:
                    assert review_snapshot_file is not None
                    atomic_write(review_snapshot_file, synthesis_text)
                    manifest, reference_errors, _ = refresh_manifest(repo, path)
                    if reference_errors:
                        raise ResearchctlError(
                            "Final milestone snapshot exposed invalid corpus "
                            "references:\n- "
                            + "\n- ".join(reference_errors)
                        )
                if manifest.get("mode") == "linked":
                    manifest_candidate, linked_snapshot_path = (
                        snapshot_linked_documents(repo, path, manifest)
                    )
                else:
                    manifest_candidate = seal_managed_manifest(manifest)
            atomic_write(path, research_candidate)
            atomic_write(research_synthesis_path, synthesis_candidate)
            atomic_write(manifest_file, manifest_text(manifest_candidate))
            os.replace(directory, destination)
            rebuild_index(repo)
            completed_path = destination / "RESEARCH.md"
            post_errors, _ = validate_research(completed_path)
            if post_errors:
                raise ResearchctlError(
                    "Research archive produced invalid artifacts:\n- "
                    + "\n- ".join(post_errors)
                )
        except Exception:
            if destination.exists() and not directory.exists():
                os.replace(destination, directory)
            atomic_write(path, text)
            atomic_write(research_synthesis_path, synthesis_text)
            atomic_write(manifest_file, manifest_text_before)
            if (
                linked_snapshot_path is not None
                and linked_snapshot_path.exists()
            ):
                shutil.rmtree(linked_snapshot_path)
            if (
                create_review_snapshot
                and review_snapshot_file is not None
                and review_snapshot_file.exists()
            ):
                review_snapshot_file.unlink()
            rebuild_index(repo)
            raise
        return destination / "RESEARCH.md"


def status_rows(repo: Path) -> list[str]:
    rows = [
        "| Research | Title | Type | Status | Maturity | Round | Revision | "
        "Mode | Documents | Synthesis | Path |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for path in research_paths(repo):
        data, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        try:
            manifest = load_manifest(manifest_path(path, data))
            mode = str(manifest.get("mode", ""))
            documents = manifest.get("documents", [])
            count = len(documents) if isinstance(documents, list) else 0
        except ResearchctlError:
            mode = "legacy"
            count = 0
        try:
            current_synthesis_path = synthesis_path(path, data)
        except ResearchctlError:
            current_synthesis_path = path.parent / "SYNTHESIS.md"
        synthesis = "missing"
        if current_synthesis_path.is_file():
            synthesis_data, _, _ = parse_frontmatter(
                current_synthesis_path.read_text(encoding="utf-8")
            )
            synthesis = synthesis_data.get("status", "")
        rows.append(
            f"| {data.get('id', '')} | {md_cell(data.get('title', ''))} | "
            f"{research_type_label(data.get('research_type', 'legacy'))} | "
            f"{data.get('status', '')} | "
            f"{data.get('maturity', 'legacy')} | "
            f"{data.get('current_round', '')} | "
            f"v{data.get('synthesis_revision', '0')} | "
            f"{mode} | {count} | {synthesis} | "
            f"`{path.relative_to(repo).as_posix()}` |"
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage multi-document Engineering Research packages"
    )
    parser.add_argument("--repo", default=".", help="Target repository")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize Research directories and index")

    new_parser = subparsers.add_parser(
        "new-research", help="Create a managed or linked Research"
    )
    new_parser.add_argument("--slug", required=True)
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--owner", default="")
    new_parser.add_argument("--author", default="")
    new_parser.add_argument(
        "--research-type",
        default="technical",
        choices=tuple(sorted(RESEARCH_TYPES)),
    )
    new_parser.add_argument("--corpus-root", action="append", default=[])
    new_parser.add_argument("--entrypoint", action="append", default=[])
    new_parser.add_argument("--include", action="append", default=[])

    sync_parser = subparsers.add_parser(
        "sync-research", help="Refresh an active document manifest"
    )
    sync_parser.add_argument("research_id")

    topic_parser = subparsers.add_parser(
        "new-topic",
        help="Create a structured topic document in the current Research round",
    )
    topic_parser.add_argument("research_id")
    topic_parser.add_argument("--slug", required=True)
    topic_parser.add_argument("--title", required=True)
    topic_parser.add_argument("--author", default="")
    topic_parser.add_argument("--question", action="append", required=True)

    round_parser = subparsers.add_parser(
        "new-round", help="Start another focused round in review-ready Research"
    )
    round_parser.add_argument("research_id")
    round_parser.add_argument("--slug", required=True)
    round_parser.add_argument("--title", required=True)
    round_parser.add_argument("--author", default="")

    review_parser = subparsers.add_parser(
        "mark-review-ready",
        help="Content-address a review-ready Synthesis without concluding Research",
    )
    review_parser.add_argument("research_id")
    review_parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Preserve this review as a deduplicated full milestone snapshot",
    )

    conclude_parser = subparsers.add_parser(
        "conclude-research",
        help="Conclude review-ready Research with explicit Owner authorization",
    )
    conclude_parser.add_argument("research_id")
    conclude_parser.add_argument("--approved-by", required=True)
    conclude_parser.add_argument("--approval-ref", required=True)

    cancel_parser = subparsers.add_parser(
        "cancel-research",
        help="Cancel Research with explicit Owner authorization and a reason",
    )
    cancel_parser.add_argument("research_id")
    cancel_parser.add_argument("--reason", required=True)
    cancel_parser.add_argument("--approved-by", required=True)
    cancel_parser.add_argument("--approval-ref", required=True)

    archive_parser = subparsers.add_parser(
        "archive-research",
        help="Deprecated compatibility alias for conclude/cancel",
    )
    archive_parser.add_argument("research_id")
    archive_parser.add_argument(
        "--outcome", required=True, choices=("concluded", "cancelled")
    )
    archive_parser.add_argument("--reason", default="")
    archive_parser.add_argument("--approved-by", default="")
    archive_parser.add_argument("--approval-ref", default="")

    subparsers.add_parser("validate", help="Validate Research artifacts")
    subparsers.add_parser("status", help="Summarize Research packages")
    subparsers.add_parser("reindex", help="Rebuild docs/RESEARCH.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo = normalize_repo(args.repo)
        if args.command == "init":
            created = init_repo(repo)
            print(json.dumps({"created": created}, ensure_ascii=False))
        elif args.command == "new-research":
            path = new_research(
                repo,
                args.slug,
                args.title,
                args.owner,
                args.author,
                args.research_type,
                args.corpus_root,
                args.entrypoint,
                args.include,
            )
            print(path)
        elif args.command == "sync-research":
            path = find_research(repo, args.research_id, "active")
            text = path.read_text(encoding="utf-8")
            synced_text = sync_research_metadata(text)
            if synced_text != text:
                atomic_write(path, synced_text)
            manifest, errors, warnings = refresh_manifest(repo, path)
            for warning in warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
            if errors:
                raise ResearchctlError(
                    "Manifest refreshed with reference errors:\n- "
                    + "\n- ".join(errors)
                )
            print(
                json.dumps(
                    {
                        "research_id": manifest.get("research_id"),
                        "documents": len(manifest.get("documents", [])),
                    },
                    ensure_ascii=False,
                )
            )
        elif args.command == "new-topic":
            print(
                new_topic(
                    repo,
                    args.research_id,
                    args.slug,
                    args.title,
                    args.author,
                    args.question,
                )
            )
        elif args.command == "new-round":
            print(
                new_round(
                    repo,
                    args.research_id,
                    args.slug,
                    args.title,
                    args.author,
                )
            )
        elif args.command == "mark-review-ready":
            print(mark_review_ready(repo, args.research_id, args.snapshot))
        elif args.command == "conclude-research":
            print(
                archive_research(
                    repo,
                    args.research_id,
                    "concluded",
                    "",
                    args.approved_by,
                    args.approval_ref,
                )
            )
        elif args.command == "cancel-research":
            print(
                archive_research(
                    repo,
                    args.research_id,
                    "cancelled",
                    args.reason,
                    args.approved_by,
                    args.approval_ref,
                )
            )
        elif args.command == "archive-research":
            print(
                "WARNING: archive-research is deprecated; use "
                "conclude-research or cancel-research",
                file=sys.stderr,
            )
            print(
                archive_research(
                    repo,
                    args.research_id,
                    args.outcome,
                    args.reason,
                    args.approved_by,
                    args.approval_ref,
                )
            )
        elif args.command == "validate":
            errors, warnings = validate_repo(repo)
            for warning in warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            print(json.dumps({"errors": len(errors), "warnings": len(warnings)}))
            return 1 if errors else 0
        elif args.command == "status":
            print("\n".join(status_rows(repo)))
        elif args.command == "reindex":
            print(json.dumps({"research": rebuild_index(repo)}))
        else:  # pragma: no cover - argparse enforces commands
            parser.error(f"Unknown command: {args.command}")
    except ResearchctlError as exc:
        print(f"researchctl: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
