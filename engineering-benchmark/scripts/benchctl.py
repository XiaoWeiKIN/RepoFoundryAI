#!/usr/bin/env python3
"""Create and validate reproducible Engineering Benchmark evidence bundles."""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence


STATE_SCHEMA_VERSION = "1"
ARTIFACT_SCHEMA_VERSION = "1.1"
SUPPORTED_ARTIFACT_SCHEMA_VERSIONS = {"1", "1.1"}
CURRENT_METADATA_SCHEMA = "1"
ALLOWED_OUTCOMES = ("passed", "failed", "inconclusive", "errored")
ID_PATTERNS = {
    "B": re.compile(r"^B-(\d{3,})$"),
    "BS": re.compile(r"^BS-(\d{3,})$"),
    "BR": re.compile(r"^BR-(\d{3,})$"),
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(
    r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>[\s\S]*)\Z",
    re.MULTILINE | re.DOTALL,
)
REQUIRED_MARKER_RE = re.compile(
    r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:",
    re.IGNORECASE,
)

SUITE_SECTIONS = (
    "Purpose and Scope",
    "Subject Under Test",
    "Consumers",
    "Ownership and Lifecycle",
    "Non-goals",
    "Safety and Data Policy",
)
SCENARIO_SECTIONS = (
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
RESULT_SECTIONS = (
    "Summary",
    "Revisions and Environment",
    "Procedure and Commands",
    "Decision Rule",
    "Raw Observations",
    "Interpretation",
    "Contradictions and Supersession",
    "Boundaries and Extrapolation",
    "Handoff",
    "Artifacts",
)


class BenchmarkError(RuntimeError):
    """A user-correctable command error."""


class ValidationFailed(BenchmarkError):
    """Repository validation failed."""


@dataclass(frozen=True)
class Record:
    kind: str
    identifier: str
    path: Path
    metadata: dict[str, object]


def benchmark_root(repo: Path) -> Path:
    return repo / "benchmarks"


def state_path(repo: Path) -> Path:
    return benchmark_root(repo) / ".benchctl" / "state.json"


def index_path(repo: Path) -> Path:
    return benchmark_root(repo) / "BENCHMARKS.md"


def suites_root(repo: Path) -> Path:
    return benchmark_root(repo) / "suites"


def assets_root() -> Path:
    return Path(__file__).resolve().parent.parent / "assets"


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def metadata_actor(value: str) -> str:
    return value.strip() or "Unassigned"


def validate_metadata_contract(
    path: Path,
    metadata: dict[str, object],
    artifact_type: str,
    expected_id: str,
) -> list[str]:
    errors: list[str] = []
    if metadata.get("metadata_schema") != CURRENT_METADATA_SCHEMA:
        errors.append(
            f"{path}: metadata_schema must be {CURRENT_METADATA_SCHEMA!r}"
        )
    if metadata.get("artifact_type") != artifact_type:
        errors.append(f"{path}: artifact_type must be {artifact_type!r}")
    if metadata.get("id") != expected_id:
        errors.append(f"{path}: metadata id must be {expected_id!r}")
    for field in ("title", "status", "author", "owner", "created", "updated"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: metadata field {field} must be non-empty")
    for field in ("created", "updated"):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip():
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"{path}: metadata field {field} must be an ISO date or timestamp"
                )
    return errors


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


@contextlib.contextmanager
def repository_lock(repo: Path) -> Iterator[None]:
    lock_directory = benchmark_root(repo) / ".benchctl"
    lock_directory.mkdir(parents=True, exist_ok=True)
    lock_path = lock_directory / "lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            import fcntl
        except ImportError:
            yield
            return
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_template(name: str) -> str:
    path = assets_root() / name
    if not path.is_file():
        raise BenchmarkError(f"missing Skill asset: {path}")
    return path.read_text(encoding="utf-8")


def render_template(name: str, values: dict[str, object]) -> str:
    result = load_template(name)
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    unresolved = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", result)))
    if unresolved:
        raise BenchmarkError(
            f"template {name} has unresolved values: {', '.join(unresolved)}"
        )
    return result


def parse_frontmatter_text(
    text: str,
    source: str,
) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise BenchmarkError(f"{source}: missing flat YAML frontmatter")
    metadata: dict[str, object] = {}
    for number, line in enumerate(
        match.group("frontmatter").splitlines(),
        start=2,
    ):
        if not line.strip():
            continue
        if line[:1].isspace() or ":" not in line:
            raise BenchmarkError(
                f"{source}:{number}: only flat frontmatter fields are supported"
            )
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key or key in metadata:
            raise BenchmarkError(
                f"{source}:{number}: invalid or duplicate frontmatter key"
            )
        raw_value = raw_value.strip()
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        metadata[key] = value
    return metadata, match.group("body")


def parse_document(path: Path) -> tuple[dict[str, object], str, str]:
    if path.is_symlink():
        raise BenchmarkError(f"{path}: symlinked fact files are not supported")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BenchmarkError(f"{path}: expected UTF-8 Markdown") from exc
    metadata, body = parse_frontmatter_text(text, str(path))
    return metadata, body, text


def update_frontmatter(text: str, values: dict[str, object], source: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise BenchmarkError(f"{source}: missing flat YAML frontmatter")
    remaining = dict(values)
    lines: list[str] = []
    for line in match.group("frontmatter").splitlines():
        if line[:1].isspace() or ":" not in line:
            lines.append(line)
            continue
        key = line.split(":", 1)[0].strip()
        if key in remaining:
            lines.append(f"{key}: {json_text(remaining.pop(key))}")
        else:
            lines.append(line)
    if remaining:
        raise BenchmarkError(
            f"{source}: missing frontmatter fields: {', '.join(sorted(remaining))}"
        )
    return "---\n" + "\n".join(lines) + "\n---\n" + match.group("body")


def section_body(body: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        body,
    )
    return None if match is None else match.group("body")


def document_structure_errors(
    path: Path,
    body: str,
    sections: Sequence[str],
    *,
    require_complete: bool = False,
) -> list[str]:
    errors: list[str] = []
    for heading in sections:
        matches = re.findall(
            rf"(?m)^## {re.escape(heading)}\s*$",
            body,
        )
        if len(matches) != 1:
            errors.append(
                f"{path}: expected exactly one '## {heading}' section"
            )
            continue
        if require_complete:
            content = section_body(body, heading) or ""
            visible = re.sub(r"<!--[\s\S]*?-->", "", content).strip()
            if not visible:
                errors.append(f"{path}: section '## {heading}' is empty")
    if require_complete and REQUIRED_MARKER_RE.search(body):
        errors.append(f"{path}: unresolved REQUIRED marker")
    return errors


def require_complete_document(path: Path, sections: Sequence[str]) -> None:
    _, body, _ = parse_document(path)
    errors = document_structure_errors(
        path,
        body,
        sections,
        require_complete=True,
    )
    if errors:
        raise BenchmarkError("\n".join(errors))


def validate_slug(slug: str) -> None:
    if not SLUG_RE.fullmatch(slug):
        raise BenchmarkError(
            "slug must contain lowercase letters, digits, and single hyphens"
        )


def validate_single_line(label: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise BenchmarkError(f"{label} must not be empty")
    if "\n" in cleaned or "\r" in cleaned:
        raise BenchmarkError(f"{label} must be a single line")
    if "{{" in cleaned or "}}" in cleaned:
        raise BenchmarkError(f"{label} must not contain template delimiters")
    return cleaned


def normalize_id(kind: str, value: str) -> str:
    identifier = value.strip().upper()
    if not ID_PATTERNS[kind].fullmatch(identifier):
        raise BenchmarkError(
            f"expected {kind}-NNN identifier, received {value!r}"
        )
    return identifier


def id_number(kind: str, identifier: str) -> int:
    match = ID_PATTERNS[kind].fullmatch(identifier)
    if not match:
        raise BenchmarkError(f"invalid {kind} identifier: {identifier!r}")
    return int(match.group(1))


def id_sort_key(identifier: str) -> tuple[str, int]:
    for kind in ("BR", "BS", "B"):
        match = ID_PATTERNS[kind].fullmatch(identifier)
        if match:
            return kind, int(match.group(1))
    return identifier, 0


def format_id(kind: str, number: int) -> str:
    return f"{kind}-{number:03d}"


def expected_stem(identifier: str) -> str:
    return identifier.lower()


def suite_paths(repo: Path) -> list[Path]:
    root = suites_root(repo)
    return sorted(root.glob("*/BENCHMARK.md")) if root.exists() else []


def scenario_paths(repo: Path) -> list[Path]:
    root = suites_root(repo)
    return sorted(root.glob("*/scenarios/*.md")) if root.exists() else []


def result_paths(repo: Path) -> list[Path]:
    root = suites_root(repo)
    return sorted(root.glob("*/runs/*/RESULT.md")) if root.exists() else []


def discover_kind(repo: Path, kind: str) -> dict[str, Record]:
    paths = {
        "B": suite_paths,
        "BS": scenario_paths,
        "BR": result_paths,
    }[kind](repo)
    records: dict[str, Record] = {}
    for path in paths:
        metadata, _, _ = parse_document(path)
        raw_identifier = metadata.get("id")
        if not isinstance(raw_identifier, str):
            raise BenchmarkError(f"{path}: id must be a string")
        identifier = normalize_id(kind, raw_identifier)
        if identifier in records:
            raise BenchmarkError(
                f"duplicate {identifier}: {records[identifier].path} and {path}"
            )
        records[identifier] = Record(kind, identifier, path, metadata)
    return records


def discover_all(
    repo: Path,
) -> tuple[dict[str, Record], dict[str, Record], dict[str, Record]]:
    return (
        discover_kind(repo, "B"),
        discover_kind(repo, "BS"),
        discover_kind(repo, "BR"),
    )


def find_record(repo: Path, kind: str, value: str) -> Record:
    identifier = normalize_id(kind, value)
    record = discover_kind(repo, kind).get(identifier)
    if record is None:
        raise BenchmarkError(f"{identifier} not found")
    return record


def initial_state(repo: Path) -> dict[str, object]:
    high_water: dict[str, int] = {}
    for kind in ("B", "BS", "BR"):
        numbers = [
            id_number(kind, identifier)
            for identifier in discover_kind(repo, kind)
        ]
        high_water[kind] = max(numbers, default=0)
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "high_water": high_water,
    }


def load_state(repo: Path) -> dict[str, object]:
    path = state_path(repo)
    if not path.is_file():
        raise BenchmarkError(
            f"{path} is missing; run benchctl --repo <repo> init"
        )
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BenchmarkError(f"{path}: invalid UTF-8 JSON") from exc
    if not isinstance(state, dict):
        raise BenchmarkError(f"{path}: state must be a JSON object")
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise BenchmarkError(
            f"{path}: unsupported schema_version {state.get('schema_version')!r}"
        )
    high_water = state.get("high_water")
    if not isinstance(high_water, dict):
        raise BenchmarkError(f"{path}: high_water must be an object")
    for kind in ("B", "BS", "BR"):
        value = high_water.get(kind)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise BenchmarkError(
                f"{path}: high_water.{kind} must be a non-negative integer"
            )
    return state


def save_state(repo: Path, state: dict[str, object]) -> None:
    atomic_write_text(
        state_path(repo),
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def reserve_next_id(
    repo: Path,
    state: dict[str, object],
    kind: str,
) -> tuple[str, int]:
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    current = high_water[kind]
    assert isinstance(current, int)
    existing = [
        id_number(kind, identifier)
        for identifier in discover_kind(repo, kind)
    ]
    number = max(current, *existing, 0) + 1
    return format_id(kind, number), number


def commit_reserved_id(
    repo: Path,
    state: dict[str, object],
    kind: str,
    number: int,
) -> None:
    high_water = state["high_water"]
    assert isinstance(high_water, dict)
    high_water[kind] = number
    save_state(repo, state)


def ensure_initialized(repo: Path) -> None:
    if not state_path(repo).is_file():
        raise BenchmarkError(
            f"{benchmark_root(repo)} is not initialized; run the init command"
        )
    load_state(repo)


def markdown_cell(value: object) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def relative_fact_path(repo: Path, path: Path) -> str:
    return path.relative_to(benchmark_root(repo)).as_posix()


def render_index(repo: Path) -> str:
    suites, scenarios, runs = discover_all(repo)
    scenarios_by_suite: dict[str, list[Record]] = {}
    runs_by_suite: dict[str, list[Record]] = {}
    runs_by_scenario: dict[str, list[Record]] = {}
    for scenario in scenarios.values():
        suite_id = str(scenario.metadata.get("suite_id", ""))
        scenarios_by_suite.setdefault(suite_id, []).append(scenario)
    for run in runs.values():
        suite_id = str(run.metadata.get("suite_id", ""))
        scenario_id = str(run.metadata.get("scenario_id", ""))
        runs_by_suite.setdefault(suite_id, []).append(run)
        runs_by_scenario.setdefault(scenario_id, []).append(run)

    suite_rows: list[str] = []
    for identifier in sorted(suites, key=id_sort_key):
        record = suites[identifier]
        path = relative_fact_path(repo, record.path)
        suite_rows.append(
            "| "
            + " | ".join(
                (
                    f"[{identifier}]({path})",
                    markdown_cell(record.metadata.get("status", "")),
                    markdown_cell(record.metadata.get("title", "")),
                    markdown_cell(record.metadata.get("owner", "")),
                    str(len(scenarios_by_suite.get(identifier, []))),
                    str(len(runs_by_suite.get(identifier, []))),
                    f"`{path}`",
                )
            )
            + " |"
        )

    scenario_rows: list[str] = []
    for identifier in sorted(scenarios, key=id_sort_key):
        record = scenarios[identifier]
        path = relative_fact_path(repo, record.path)
        scenario_rows.append(
            "| "
            + " | ".join(
                (
                    f"[{identifier}]({path})",
                    markdown_cell(record.metadata.get("suite_id", "")),
                    markdown_cell(record.metadata.get("status", "")),
                    markdown_cell(record.metadata.get("title", "")),
                    str(len(runs_by_scenario.get(identifier, []))),
                    f"`{path}`",
                )
            )
            + " |"
        )

    run_rows: list[str] = []
    for identifier in sorted(runs, key=id_sort_key):
        record = runs[identifier]
        path = relative_fact_path(repo, record.path)
        supersedes = record.metadata.get("supersedes", [])
        if not isinstance(supersedes, list):
            supersedes = [supersedes]
        run_rows.append(
            "| "
            + " | ".join(
                (
                    f"[{identifier}]({path})",
                    markdown_cell(record.metadata.get("scenario_id", "")),
                    markdown_cell(record.metadata.get("status", "")),
                    markdown_cell(record.metadata.get("outcome", "") or "—"),
                    markdown_cell(record.metadata.get("subject_revision", "")),
                    markdown_cell(", ".join(map(str, supersedes)) or "—"),
                    f"`{path}`",
                )
            )
            + " |"
        )

    empty_suite = "| — | — | No suites | — | 0 | 0 | — |"
    empty_scenario = "| — | — | — | No scenarios | 0 | — |"
    empty_run = "| — | — | — | — | — | — | No runs |"
    return render_template(
        "benchmark-index.md",
        {
            "SUITE_ROWS": "\n".join(suite_rows) or empty_suite,
            "SCENARIO_ROWS": "\n".join(scenario_rows) or empty_scenario,
            "RUN_ROWS": "\n".join(run_rows) or empty_run,
        },
    )


def write_index(repo: Path) -> None:
    atomic_write_text(index_path(repo), render_index(repo))


def initialize(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    with repository_lock(repo):
        suites_root(repo).mkdir(parents=True, exist_ok=True)
        if not state_path(repo).exists():
            save_state(repo, initial_state(repo))
        else:
            load_state(repo)
        write_index(repo)
    return benchmark_root(repo)


def create_suite(
    repo: Path,
    slug: str,
    title: str,
    owner: str,
    author: str,
) -> Path:
    ensure_initialized(repo)
    validate_slug(slug)
    title = validate_single_line("title", title)
    owner = validate_single_line("owner", metadata_actor(owner))
    author = validate_single_line("author", metadata_actor(author))
    with repository_lock(repo):
        state = load_state(repo)
        identifier, number = reserve_next_id(repo, state, "B")
        directory = suites_root(repo) / f"{expected_stem(identifier)}_{slug}"
        if directory.exists():
            raise BenchmarkError(f"target already exists: {directory}")
        temporary = Path(
            tempfile.mkdtemp(prefix=".benchctl-suite-", dir=suites_root(repo))
        )
        try:
            (temporary / "scenarios").mkdir()
            (temporary / "runs").mkdir()
            content = render_template(
                "suite.md",
                {
                    "ID_JSON": json_text(identifier),
                    "TITLE_JSON": json_text(title),
                    "AUTHOR_JSON": json_text(author),
                    "OWNER_JSON": json_text(owner),
                    "DATE_JSON": json_text(utc_date()),
                    "TITLE": title,
                },
            )
            atomic_write_text(temporary / "BENCHMARK.md", content)
            os.replace(temporary, directory)
            commit_reserved_id(repo, state, "B", number)
            write_index(repo)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return directory / "BENCHMARK.md"


def create_scenario(
    repo: Path,
    suite_value: str,
    slug: str,
    title: str,
    author: str,
) -> Path:
    ensure_initialized(repo)
    validate_slug(slug)
    title = validate_single_line("title", title)
    with repository_lock(repo):
        suite = find_record(repo, "B", suite_value)
        if suite.metadata.get("status") != "active":
            raise BenchmarkError(f"{suite.identifier} is not active")
        if suite.metadata.get("owner") == "Unassigned":
            raise BenchmarkError(
                f"{suite.identifier} requires an accountable owner before "
                "creating a Scenario"
            )
        scenario_author = validate_single_line(
            "author",
            metadata_actor(author or str(suite.metadata.get("author", ""))),
        )
        scenario_owner = validate_single_line(
            "owner",
            metadata_actor(str(suite.metadata.get("owner", ""))),
        )
        require_complete_document(suite.path, SUITE_SECTIONS)
        state = load_state(repo)
        identifier, number = reserve_next_id(repo, state, "BS")
        target = (
            suite.path.parent
            / "scenarios"
            / f"{expected_stem(identifier)}_{slug}.md"
        )
        if target.exists():
            raise BenchmarkError(f"target already exists: {target}")
        content = render_template(
            "scenario.md",
            {
                "ID_JSON": json_text(identifier),
                "SUITE_ID_JSON": json_text(suite.identifier),
                "TITLE_JSON": json_text(title),
                "AUTHOR_JSON": json_text(scenario_author),
                "OWNER_JSON": json_text(scenario_owner),
                "DATE_JSON": json_text(utc_date()),
                "TITLE": title,
            },
        )
        atomic_write_text(target, content)
        commit_reserved_id(repo, state, "BS", number)
        write_index(repo)
    return target


def normalized_supersedes(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        identifier = normalize_id("BR", value)
        if identifier in result:
            raise BenchmarkError(f"duplicate supersedes target: {identifier}")
        result.append(identifier)
    return result


def validate_supersedes_for_new_run(
    repo: Path,
    scenario_id: str,
    values: Sequence[str],
) -> list[str]:
    result = normalized_supersedes(values)
    runs = discover_kind(repo, "BR")
    for identifier in result:
        target = runs.get(identifier)
        if target is None:
            raise BenchmarkError(f"supersedes target not found: {identifier}")
        if target.metadata.get("status") != "sealed":
            raise BenchmarkError(
                f"supersedes target must be sealed: {identifier}"
            )
        if target.metadata.get("scenario_id") != scenario_id:
            raise BenchmarkError(
                f"{identifier} belongs to a different Scenario; "
                "material protocol changes require a new Scenario"
            )
    return result


def create_run(
    repo: Path,
    scenario_value: str,
    slug: str,
    title: str,
    subject_revision: str,
    harness_revision: str,
    supersedes_values: Sequence[str],
    author: str,
) -> Path:
    ensure_initialized(repo)
    validate_slug(slug)
    title = validate_single_line("title", title)
    subject_revision = validate_single_line(
        "subject_revision",
        subject_revision,
    )
    harness_revision = validate_single_line(
        "harness_revision",
        harness_revision,
    )
    with repository_lock(repo):
        scenario = find_record(repo, "BS", scenario_value)
        if scenario.metadata.get("status") != "active":
            raise BenchmarkError(f"{scenario.identifier} is not active")
        suite_value = scenario.metadata.get("suite_id")
        if not isinstance(suite_value, str):
            raise BenchmarkError(f"{scenario.path}: suite_id must be a string")
        suite = find_record(repo, "B", suite_value)
        if suite.metadata.get("status") != "active":
            raise BenchmarkError(f"{suite.identifier} is not active")
        require_complete_document(suite.path, SUITE_SECTIONS)
        require_complete_document(scenario.path, SCENARIO_SECTIONS)
        run_author = validate_single_line(
            "author",
            metadata_actor(author or str(scenario.metadata.get("author", ""))),
        )
        run_owner = validate_single_line(
            "owner",
            metadata_actor(str(suite.metadata.get("owner", ""))),
        )
        supersedes = validate_supersedes_for_new_run(
            repo,
            scenario.identifier,
            supersedes_values,
        )

        state = load_state(repo)
        identifier, number = reserve_next_id(repo, state, "BR")
        runs_directory = suite.path.parent / "runs"
        target = runs_directory / f"{expected_stem(identifier)}_{slug}"
        if target.exists():
            raise BenchmarkError(f"target already exists: {target}")
        temporary = Path(
            tempfile.mkdtemp(prefix=".benchctl-run-", dir=runs_directory)
        )
        try:
            shutil.copyfile(scenario.path, temporary / "SCENARIO.md")
            (temporary / "artifacts").mkdir()
            content = render_template(
                "result.md",
                {
                    "ID_JSON": json_text(identifier),
                    "SUITE_ID_JSON": json_text(suite.identifier),
                    "SCENARIO_ID_JSON": json_text(scenario.identifier),
                    "TITLE_JSON": json_text(title),
                    "SUBJECT_REVISION_JSON": json_text(subject_revision),
                    "HARNESS_REVISION_JSON": json_text(harness_revision),
                    "SUPERSEDES_JSON": json_text(supersedes),
                    "TIMESTAMP_JSON": json_text(utc_timestamp()),
                    "AUTHOR_JSON": json_text(run_author),
                    "OWNER_JSON": json_text(run_owner),
                    "TITLE": title,
                },
            )
            atomic_write_text(temporary / "RESULT.md", content)
            os.replace(temporary, target)
            commit_reserved_id(repo, state, "BR", number)
            write_index(repo)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return target / "RESULT.md"


def inspect_run_layout(run_directory: Path) -> list[str]:
    errors: list[str] = []
    allowed_root_files = {
        "SCENARIO.md",
        "RESULT.md",
        "EVIDENCE_MANIFEST.json",
    }
    for child in sorted(run_directory.iterdir()):
        if child.is_symlink():
            errors.append(f"{child}: symlinks are not allowed in a Run")
            continue
        if child.is_file() and child.name not in allowed_root_files:
            errors.append(
                f"{child}: Run files must be placed below artifacts/"
            )
        elif child.is_dir() and child.name != "artifacts":
            errors.append(
                f"{child}: Run directories other than artifacts/ are not allowed"
            )
    artifacts = run_directory / "artifacts"
    if not artifacts.is_dir() or artifacts.is_symlink():
        errors.append(f"{artifacts}: missing regular artifacts directory")
        return errors
    for root, directories, files in os.walk(artifacts, followlinks=False):
        root_path = Path(root)
        for name in directories:
            candidate = root_path / name
            if candidate.is_symlink():
                errors.append(
                    f"{candidate}: symlinked artifact directories are not allowed"
                )
        for name in files:
            candidate = root_path / name
            if candidate.is_symlink():
                errors.append(
                    f"{candidate}: symlinked artifacts are not allowed"
                )
            elif not candidate.is_file():
                errors.append(f"{candidate}: artifact must be a regular file")
    return errors


def bundle_inventory(run_directory: Path) -> list[dict[str, object]]:
    errors = inspect_run_layout(run_directory)
    if errors:
        raise BenchmarkError("\n".join(errors))
    paths = [
        run_directory / "SCENARIO.md",
        run_directory / "RESULT.md",
    ]
    paths.extend(
        sorted(
            path
            for path in (run_directory / "artifacts").rglob("*")
            if path.is_file() and not path.is_symlink()
        )
    )
    records: list[dict[str, object]] = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise BenchmarkError(f"{path}: missing regular evidence file")
        records.append(
            {
                "path": path.relative_to(run_directory).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return sorted(records, key=lambda item: str(item["path"]))


def manifest_digest(manifest: dict[str, object]) -> str:
    payload = copy.deepcopy(manifest)
    payload["payload_sha256"] = ""
    return sha256_bytes(canonical_json_bytes(payload))


def build_manifest(
    run: Record,
    metadata: dict[str, object],
    sealed_at: str,
    executed_by: str,
) -> dict[str, object]:
    schema_version = str(metadata.get("schema_version", ""))
    manifest: dict[str, object] = {
        "schema_version": schema_version,
        "run_id": run.identifier,
        "suite_id": metadata["suite_id"],
        "scenario_id": metadata["scenario_id"],
        "status": "sealed",
        "outcome": metadata["outcome"],
        "created": metadata["created"],
        "sealed_at": sealed_at,
        "executed_by": executed_by,
        "files": bundle_inventory(run.path.parent),
        "payload_sha256": "",
    }
    if schema_version == "1.1":
        manifest.update(
            {
                "metadata_schema": CURRENT_METADATA_SCHEMA,
                "artifact_type": "benchmark-manifest",
                "id": f"{run.identifier}-MANIFEST",
                "title": f"{metadata.get('title', '')} — Evidence manifest",
                "author": metadata.get("author", ""),
                "owner": metadata.get("owner", ""),
                "updated": sealed_at,
            }
        )
    manifest["payload_sha256"] = manifest_digest(manifest)
    return manifest


def require_draft_run_contract(repo: Path, run: Record) -> None:
    metadata = run.metadata
    if metadata.get("schema_version") not in SUPPORTED_ARTIFACT_SCHEMA_VERSIONS:
        raise BenchmarkError(f"{run.path}: unsupported schema_version")
    if metadata.get("schema_version") == ARTIFACT_SCHEMA_VERSION:
        metadata_errors = validate_metadata_contract(
            run.path,
            metadata,
            "benchmark-result",
            run.identifier,
        )
        if metadata_errors:
            raise BenchmarkError("\n".join(metadata_errors))
    for field in (
        "title",
        "subject_revision",
        "harness_revision",
        "created",
    ):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BenchmarkError(
                f"{run.path}: {field} must be a non-empty string"
            )
    if metadata.get("manifest") != "EVIDENCE_MANIFEST.json":
        raise BenchmarkError(
            f"{run.path}: manifest must be EVIDENCE_MANIFEST.json"
        )
    suite_value = metadata.get("suite_id")
    scenario_value = metadata.get("scenario_id")
    if not isinstance(suite_value, str) or not isinstance(
        scenario_value,
        str,
    ):
        raise BenchmarkError(
            f"{run.path}: suite_id and scenario_id must be strings"
        )
    suite = find_record(repo, "B", suite_value)
    scenario = find_record(repo, "BS", scenario_value)
    if scenario.metadata.get("suite_id") != suite.identifier:
        raise BenchmarkError(
            f"{run.path}: {scenario.identifier} is not in {suite.identifier}"
        )
    if run.path.parent.parent.parent != suite.path.parent:
        raise BenchmarkError(
            f"{run.path}: Run path is outside {suite.identifier}"
        )
    snapshot_path = run.path.parent / "SCENARIO.md"
    snapshot_metadata, _, _ = parse_document(snapshot_path)
    if snapshot_metadata.get("id") != scenario.identifier:
        raise BenchmarkError(
            f"{snapshot_path}: id must be {scenario.identifier}"
        )
    if snapshot_metadata.get("suite_id") != suite.identifier:
        raise BenchmarkError(
            f"{snapshot_path}: suite_id must be {suite.identifier}"
        )
    supersedes = metadata.get("supersedes")
    if not isinstance(supersedes, list) or any(
        not isinstance(value, str) for value in supersedes
    ):
        raise BenchmarkError(
            f"{run.path}: supersedes must be an array of Run IDs"
        )
    validate_supersedes_for_new_run(
        repo,
        scenario.identifier,
        supersedes,
    )


def verify_manifest(run: Record) -> list[str]:
    errors: list[str] = []
    manifest_path = run.path.parent / "EVIDENCE_MANIFEST.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return [f"{manifest_path}: sealed Run requires a regular Manifest"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"{manifest_path}: invalid UTF-8 JSON: {exc}"]
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: Manifest must be an object"]

    expected_fields = {
        "schema_version": run.metadata.get("schema_version"),
        "run_id": run.identifier,
        "suite_id": run.metadata.get("suite_id"),
        "scenario_id": run.metadata.get("scenario_id"),
        "status": "sealed",
        "outcome": run.metadata.get("outcome"),
        "created": run.metadata.get("created"),
        "sealed_at": run.metadata.get("completed"),
        "executed_by": run.metadata.get("executed_by"),
    }
    for field, expected in expected_fields.items():
        if manifest.get(field) != expected:
            errors.append(
                f"{manifest_path}: {field} must be {expected!r}, "
                f"found {manifest.get(field)!r}"
            )
    if run.metadata.get("schema_version") == ARTIFACT_SCHEMA_VERSION:
        manifest_id = f"{run.identifier}-MANIFEST"
        for field, expected in (
            ("metadata_schema", CURRENT_METADATA_SCHEMA),
            ("artifact_type", "benchmark-manifest"),
            ("id", manifest_id),
        ):
            if manifest.get(field) != expected:
                errors.append(
                    f"{manifest_path}: {field} must be {expected!r}"
                )
        for field in ("title", "author", "owner", "created", "updated"):
            value = manifest.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"{manifest_path}: metadata field {field} must be non-empty"
                )
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append(f"{manifest_path}: files must be an array")
    else:
        try:
            expected_inventory = bundle_inventory(run.path.parent)
        except BenchmarkError as exc:
            errors.extend(str(exc).splitlines())
        else:
            if files != expected_inventory:
                errors.append(
                    f"{manifest_path}: evidence inventory or file digest drift"
                )
    payload = manifest.get("payload_sha256")
    if not isinstance(payload, str) or not re.fullmatch(
        r"[0-9a-f]{64}",
        payload,
    ):
        errors.append(
            f"{manifest_path}: payload_sha256 must be a lowercase SHA-256"
        )
    elif manifest_digest(manifest) != payload:
        errors.append(f"{manifest_path}: payload_sha256 mismatch")
    return errors


def seal_run(
    repo: Path,
    run_value: str,
    outcome: str,
    executed_by: str,
) -> Path:
    ensure_initialized(repo)
    if outcome not in ALLOWED_OUTCOMES:
        raise BenchmarkError(
            f"outcome must be one of: {', '.join(ALLOWED_OUTCOMES)}"
        )
    executed_by = validate_single_line("executed_by", executed_by)
    with repository_lock(repo):
        run = find_record(repo, "BR", run_value)
        if run.metadata.get("status") != "draft":
            raise BenchmarkError(f"{run.identifier} is already sealed")
        require_draft_run_contract(repo, run)
        require_complete_document(
            run.path.parent / "SCENARIO.md",
            SCENARIO_SECTIONS,
        )
        require_complete_document(run.path, RESULT_SECTIONS)
        layout_errors = inspect_run_layout(run.path.parent)
        if layout_errors:
            raise BenchmarkError("\n".join(layout_errors))

        original = run.path.read_bytes()
        manifest_path = run.path.parent / "EVIDENCE_MANIFEST.json"
        if manifest_path.exists():
            raise BenchmarkError(
                f"{manifest_path}: draft Run must not already have a Manifest"
            )
        completed = utc_timestamp()
        updated = update_frontmatter(
            original.decode("utf-8"),
            {
                "status": "sealed",
                "outcome": outcome,
                "updated": completed,
                "completed": completed,
                "executed_by": executed_by,
            },
            str(run.path),
        )
        try:
            atomic_write_text(run.path, updated)
            updated_metadata, _, _ = parse_document(run.path)
            updated_run = Record(
                "BR",
                run.identifier,
                run.path,
                updated_metadata,
            )
            manifest = build_manifest(
                updated_run,
                updated_metadata,
                completed,
                executed_by,
            )
            atomic_write_text(
                manifest_path,
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
            errors = verify_manifest(updated_run)
            if errors:
                raise BenchmarkError("\n".join(errors))
            write_index(repo)
        except Exception:
            atomic_write_bytes(run.path, original)
            if manifest_path.exists():
                manifest_path.unlink()
            write_index(repo)
            raise
    return manifest_path


def metadata_string(
    metadata: dict[str, object],
    field: str,
    path: Path,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or (not allow_empty and not value):
        errors.append(f"{path}: {field} must be a non-empty string")
        return ""
    return value


def validate_path_identity(record: Record, errors: list[str]) -> None:
    prefix = expected_stem(record.identifier) + "_"
    if record.kind == "B":
        name = record.path.parent.name
    elif record.kind == "BS":
        name = record.path.stem
    else:
        name = record.path.parent.name
    if not name.startswith(prefix):
        errors.append(
            f"{record.path}: path must start with {prefix!r} for "
            f"{record.identifier}"
        )
        return
    slug = name[len(prefix) :]
    if not SLUG_RE.fullmatch(slug):
        errors.append(f"{record.path}: invalid slug in fact path")


def validate_supersession_graph(
    runs: dict[str, Record],
    errors: list[str],
) -> None:
    graph: dict[str, list[str]] = {}
    for identifier, run in runs.items():
        values = run.metadata.get("supersedes", [])
        if not isinstance(values, list) or any(
            not isinstance(value, str) for value in values
        ):
            errors.append(f"{run.path}: supersedes must be an array of Run IDs")
            continue
        normalized: list[str] = []
        for value in values:
            try:
                target_id = normalize_id("BR", value)
            except BenchmarkError as exc:
                errors.append(f"{run.path}: {exc}")
                continue
            if target_id in normalized:
                errors.append(
                    f"{run.path}: duplicate supersedes target {target_id}"
                )
                continue
            normalized.append(target_id)
            target = runs.get(target_id)
            if target is None:
                errors.append(
                    f"{run.path}: supersedes target not found: {target_id}"
                )
            else:
                if target.metadata.get("status") != "sealed":
                    errors.append(
                        f"{run.path}: supersedes target must be sealed: "
                        f"{target_id}"
                    )
                if target.metadata.get("scenario_id") != run.metadata.get(
                    "scenario_id"
                ):
                    errors.append(
                        f"{run.path}: supersedes target {target_id} belongs "
                        "to a different Scenario"
                    )
        graph[identifier] = normalized

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str, trail: list[str]) -> None:
        if identifier in visiting:
            cycle = trail[trail.index(identifier) :] + [identifier]
            errors.append("supersedes cycle: " + " -> ".join(cycle))
            return
        if identifier in visited:
            return
        visiting.add(identifier)
        for target in graph.get(identifier, []):
            if target in graph:
                visit(target, trail + [target])
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in graph:
        visit(identifier, [identifier])


def validate_repository(repo: Path) -> list[str]:
    errors: list[str] = []
    root = benchmark_root(repo)
    if not root.is_dir():
        return [f"{root}: missing; run benchctl init"]
    try:
        state = load_state(repo)
    except BenchmarkError as exc:
        errors.append(str(exc))
        state = None
    try:
        suites, scenarios, runs = discover_all(repo)
    except BenchmarkError as exc:
        errors.append(str(exc))
        return errors

    for record in suites.values():
        validate_path_identity(record, errors)
        metadata = record.metadata
        if metadata.get("schema_version") not in SUPPORTED_ARTIFACT_SCHEMA_VERSIONS:
            errors.append(f"{record.path}: unsupported schema_version")
        if metadata.get("status") != "active":
            errors.append(f"{record.path}: status must be active")
        metadata_string(metadata, "title", record.path, errors)
        metadata_string(metadata, "owner", record.path, errors)
        if metadata.get("schema_version") == ARTIFACT_SCHEMA_VERSION:
            errors.extend(
                validate_metadata_contract(
                    record.path,
                    metadata,
                    "benchmark-suite",
                    record.identifier,
                )
            )
        _, body, _ = parse_document(record.path)
        errors.extend(
            document_structure_errors(record.path, body, SUITE_SECTIONS)
        )

    for record in scenarios.values():
        validate_path_identity(record, errors)
        metadata = record.metadata
        if metadata.get("schema_version") not in SUPPORTED_ARTIFACT_SCHEMA_VERSIONS:
            errors.append(f"{record.path}: unsupported schema_version")
        if metadata.get("status") != "active":
            errors.append(f"{record.path}: status must be active")
        suite_id = metadata_string(metadata, "suite_id", record.path, errors)
        metadata_string(metadata, "title", record.path, errors)
        if metadata.get("schema_version") == ARTIFACT_SCHEMA_VERSION:
            errors.extend(
                validate_metadata_contract(
                    record.path,
                    metadata,
                    "benchmark-scenario",
                    record.identifier,
                )
            )
        suite = suites.get(suite_id)
        if suite is None:
            errors.append(f"{record.path}: Suite not found: {suite_id}")
        elif record.path.parent.parent != suite.path.parent:
            errors.append(
                f"{record.path}: Scenario path is outside {suite_id}"
            )
        _, body, _ = parse_document(record.path)
        errors.extend(
            document_structure_errors(record.path, body, SCENARIO_SECTIONS)
        )

    for record in runs.values():
        snapshot_body = ""
        validate_path_identity(record, errors)
        metadata = record.metadata
        if metadata.get("schema_version") not in SUPPORTED_ARTIFACT_SCHEMA_VERSIONS:
            errors.append(f"{record.path}: unsupported schema_version")
        suite_id = metadata_string(metadata, "suite_id", record.path, errors)
        scenario_id = metadata_string(
            metadata,
            "scenario_id",
            record.path,
            errors,
        )
        metadata_string(metadata, "title", record.path, errors)
        metadata_string(metadata, "subject_revision", record.path, errors)
        metadata_string(metadata, "harness_revision", record.path, errors)
        metadata_string(metadata, "created", record.path, errors)
        if metadata.get("schema_version") == ARTIFACT_SCHEMA_VERSION:
            errors.extend(
                validate_metadata_contract(
                    record.path,
                    metadata,
                    "benchmark-result",
                    record.identifier,
                )
            )
        if metadata.get("manifest") != "EVIDENCE_MANIFEST.json":
            errors.append(
                f"{record.path}: manifest must be EVIDENCE_MANIFEST.json"
            )
        scenario = scenarios.get(scenario_id)
        suite = suites.get(suite_id)
        if scenario is None:
            errors.append(f"{record.path}: Scenario not found: {scenario_id}")
        elif scenario.metadata.get("suite_id") != suite_id:
            errors.append(
                f"{record.path}: Scenario {scenario_id} is not in {suite_id}"
            )
        if suite is None:
            errors.append(f"{record.path}: Suite not found: {suite_id}")
        elif record.path.parent.parent.parent != suite.path.parent:
            errors.append(f"{record.path}: Run path is outside {suite_id}")

        snapshot_path = record.path.parent / "SCENARIO.md"
        try:
            snapshot_metadata, snapshot_body, _ = parse_document(snapshot_path)
        except (BenchmarkError, OSError) as exc:
            errors.append(str(exc))
        else:
            snapshot_schema = snapshot_metadata.get("schema_version")
            if snapshot_schema not in SUPPORTED_ARTIFACT_SCHEMA_VERSIONS:
                errors.append(
                    f"{snapshot_path}: unsupported schema_version"
                )
            if snapshot_metadata.get("id") != scenario_id:
                errors.append(
                    f"{snapshot_path}: id must match {scenario_id}"
                )
            if snapshot_metadata.get("suite_id") != suite_id:
                errors.append(
                    f"{snapshot_path}: suite_id must match {suite_id}"
                )
            if snapshot_schema == ARTIFACT_SCHEMA_VERSION:
                errors.extend(
                    validate_metadata_contract(
                        snapshot_path,
                        snapshot_metadata,
                        "benchmark-scenario",
                        scenario_id,
                    )
                )
            errors.extend(
                document_structure_errors(
                    snapshot_path,
                    snapshot_body,
                    SCENARIO_SECTIONS,
                )
            )
        _, result_body, _ = parse_document(record.path)
        errors.extend(inspect_run_layout(record.path.parent))

        status = metadata.get("status")
        manifest_path = record.path.parent / "EVIDENCE_MANIFEST.json"
        if status == "draft":
            errors.extend(
                document_structure_errors(
                    record.path,
                    result_body,
                    RESULT_SECTIONS,
                )
            )
            if metadata.get("outcome") not in ("", None):
                errors.append(f"{record.path}: draft outcome must be empty")
            for field in ("completed", "executed_by"):
                if metadata.get(field) not in ("", None):
                    errors.append(
                        f"{record.path}: draft {field} must be empty"
                    )
            if manifest_path.exists():
                errors.append(
                    f"{manifest_path}: draft Run must not have a Manifest"
                )
        elif status == "sealed":
            if metadata.get("outcome") not in ALLOWED_OUTCOMES:
                errors.append(
                    f"{record.path}: sealed outcome must be one of "
                    + ", ".join(ALLOWED_OUTCOMES)
                )
            metadata_string(metadata, "completed", record.path, errors)
            metadata_string(metadata, "executed_by", record.path, errors)
            errors.extend(
                document_structure_errors(
                    record.path,
                    result_body,
                    RESULT_SECTIONS,
                    require_complete=True,
                )
            )
            if snapshot_body:
                errors.extend(
                    document_structure_errors(
                        snapshot_path,
                        snapshot_body,
                        SCENARIO_SECTIONS,
                        require_complete=True,
                    )
                )
            errors.extend(verify_manifest(record))
        else:
            errors.append(
                f"{record.path}: status must be draft or sealed, found {status!r}"
            )

    validate_supersession_graph(runs, errors)

    if state is not None:
        high_water = state["high_water"]
        assert isinstance(high_water, dict)
        for kind, records in (("B", suites), ("BS", scenarios), ("BR", runs)):
            maximum = max(
                (id_number(kind, identifier) for identifier in records),
                default=0,
            )
            current = high_water[kind]
            assert isinstance(current, int)
            if current < maximum:
                errors.append(
                    f"{state_path(repo)}: high_water.{kind}={current} "
                    f"is below existing ID {maximum}"
                )

    if not index_path(repo).is_file():
        errors.append(f"{index_path(repo)}: missing generated index")
    else:
        try:
            actual_index = index_path(repo).read_text(encoding="utf-8")
            expected_index = render_index(repo)
        except (BenchmarkError, UnicodeDecodeError) as exc:
            errors.append(str(exc))
        else:
            if actual_index != expected_index:
                errors.append(
                    f"{index_path(repo)}: generated index is stale; run reindex"
                )
    return errors


def reindex(repo: Path) -> Path:
    ensure_initialized(repo)
    with repository_lock(repo):
        write_index(repo)
    return index_path(repo)


def evidence_reference(repo: Path, run_value: str) -> str:
    ensure_initialized(repo)
    run = find_record(repo, "BR", run_value)
    if run.metadata.get("status") != "sealed":
        raise BenchmarkError(f"{run.identifier} is not sealed")
    errors = verify_manifest(run)
    if errors:
        raise BenchmarkError("\n".join(errors))
    manifest = json.loads(
        (run.path.parent / "EVIDENCE_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(manifest, dict)
    payload = manifest["payload_sha256"]
    assert isinstance(payload, str)
    return f"benchmark:{run.identifier}@sha256:{payload}"


def status_text(repo: Path) -> str:
    ensure_initialized(repo)
    suites, scenarios, runs = discover_all(repo)
    outcomes = {outcome: 0 for outcome in ALLOWED_OUTCOMES}
    drafts = 0
    for run in runs.values():
        if run.metadata.get("status") == "draft":
            drafts += 1
        outcome = run.metadata.get("outcome")
        if isinstance(outcome, str) and outcome in outcomes:
            outcomes[outcome] += 1
    lines = [
        "# Engineering Benchmark status",
        "",
        f"- Suites: {len(suites)}",
        f"- Scenarios: {len(scenarios)}",
        f"- Runs: {len(runs)} ({drafts} draft, {len(runs) - drafts} sealed)",
        "- Sealed outcomes: "
        + ", ".join(f"{key}={value}" for key, value in outcomes.items()),
    ]
    if runs:
        lines.extend(("", "## Runs", ""))
        for identifier in sorted(runs, key=id_sort_key):
            metadata = runs[identifier].metadata
            lines.append(
                f"- {identifier}: {metadata.get('status')} / "
                f"{metadata.get('outcome') or 'pending'} / "
                f"{metadata.get('subject_revision')}"
            )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage reproducible Engineering Benchmark evidence.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="target repository root (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="initialize benchmark governance")

    new_suite = subparsers.add_parser(
        "new-suite",
        help="create a Benchmark Suite",
    )
    new_suite.add_argument("--slug", required=True)
    new_suite.add_argument("--title", required=True)
    new_suite.add_argument("--owner", default="Unassigned")
    new_suite.add_argument("--author", default="")

    new_scenario = subparsers.add_parser(
        "new-scenario",
        help="create a stable Scenario in a Suite",
    )
    new_scenario.add_argument("suite_id")
    new_scenario.add_argument("--slug", required=True)
    new_scenario.add_argument("--title", required=True)
    new_scenario.add_argument("--author", default="")

    new_run = subparsers.add_parser(
        "new-run",
        help="create a Run with a Scenario snapshot",
    )
    new_run.add_argument("scenario_id")
    new_run.add_argument("--slug", required=True)
    new_run.add_argument("--title", required=True)
    new_run.add_argument("--subject-revision", required=True)
    new_run.add_argument("--harness-revision", required=True)
    new_run.add_argument("--author", default="")
    new_run.add_argument(
        "--supersedes",
        action="append",
        default=[],
        metavar="BR-NNN",
    )

    seal = subparsers.add_parser(
        "seal-run",
        help="seal a completed Run and generate its Manifest",
    )
    seal.add_argument("run_id")
    seal.add_argument("--outcome", choices=ALLOWED_OUTCOMES, required=True)
    seal.add_argument("--executed-by", required=True)

    subparsers.add_parser("validate", help="validate all benchmark contracts")
    subparsers.add_parser("status", help="show benchmark lifecycle status")
    subparsers.add_parser("reindex", help="rebuild BENCHMARKS.md")
    evidence = subparsers.add_parser(
        "evidence-ref",
        help="verify a sealed Run and print its consumer reference",
    )
    evidence.add_argument("run_id")
    return parser


def run_command(arguments: argparse.Namespace) -> int:
    repo = arguments.repo.resolve()
    if arguments.command == "init":
        print(initialize(repo))
    elif arguments.command == "new-suite":
        print(
            create_suite(
                repo,
                arguments.slug,
                arguments.title,
                arguments.owner,
                arguments.author,
            )
        )
    elif arguments.command == "new-scenario":
        print(
            create_scenario(
                repo,
                arguments.suite_id,
                arguments.slug,
                arguments.title,
                arguments.author,
            )
        )
    elif arguments.command == "new-run":
        print(
            create_run(
                repo,
                arguments.scenario_id,
                arguments.slug,
                arguments.title,
                arguments.subject_revision,
                arguments.harness_revision,
                arguments.supersedes,
                arguments.author,
            )
        )
    elif arguments.command == "seal-run":
        print(
            seal_run(
                repo,
                arguments.run_id,
                arguments.outcome,
                arguments.executed_by,
            )
        )
    elif arguments.command == "validate":
        errors = validate_repository(repo)
        if errors:
            raise ValidationFailed(
                "validation failed:\n- " + "\n- ".join(errors)
            )
        print("Engineering Benchmark validation passed")
    elif arguments.command == "status":
        print(status_text(repo), end="")
    elif arguments.command == "reindex":
        print(reindex(repo))
    elif arguments.command == "evidence-ref":
        print(evidence_reference(repo, arguments.run_id))
    else:
        raise BenchmarkError(f"unsupported command: {arguments.command}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        return run_command(arguments)
    except ValidationFailed as exc:
        print(f"benchctl: {exc}", file=sys.stderr)
        return 1
    except (BenchmarkError, OSError) as exc:
        print(f"benchctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
