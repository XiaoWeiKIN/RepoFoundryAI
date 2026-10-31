#!/usr/bin/env python3
"""Read-only Spec-aware verification suggestions for a local Git change.

Shadow-mode engineering evidence: this script does not execute commands,
activate Requirements, issue a Verification Receipt, or change CI gates.
Python 3.10+; stdlib, Git, and the installed Spec Router source only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import session_handoff as handoff

# Reuse the authoritative, validated Spec Router rather than implementing a
# second Spec catalog/lock parser or guessing Requirement applicability.
ROUTER_PATH = Path(__file__).resolve().parent.parent / "assets/core/engineering-specs"
sys.path.insert(0, str(ROUTER_PATH))
import spec_router as router  # noqa: E402

SCHEMA_VERSION = 1
MAX_PATHS = handoff.MAX_CHANGED_PATHS
BASE_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,127}\Z")
GIT_SHA_RE = re.compile(r"[a-f0-9]{40,64}\Z")
SOURCE_EXTENSIONS = frozenset({
    ".py", ".pyi", ".go", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".jsx",
    ".java", ".rs", ".sh", ".sql", ".c", ".cc", ".cpp", ".h", ".hpp",
})
DOCUMENT_EXTENSIONS = frozenset({".md", ".rst", ".txt"})
CONFIG_EXTENSIONS = frozenset({
    ".json", ".jsonl", ".toml", ".yaml", ".yml", ".xml", ".ini",
})
SENSITIVE_FILES = frozenset({
    "go.mod", "go.sum", "go.work", "go.work.sum", "Cargo.toml",
    "Cargo.lock", "package.json", "package-lock.json", "pnpm-lock.yaml",
    "yarn.lock", "pyproject.toml", "requirements.txt", "setup.py",
    "Makefile", "Dockerfile", "AGENTS.md", "SKILL.md",
})
SENSITIVE_PREFIXES = (
    ".github/", "scripts/", "assets/core/engineering-specs/",
    "docs/.engineering/", "docs/agent-guides/managed/",
)

class PlanError(RuntimeError):
    """Invalid input or unobservable Git state; no plan can be trusted."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def base_revision(root: Path, raw: str) -> str:
    if (not BASE_RE.fullmatch(raw) or ".." in raw or
            raw.endswith(("/", ".")) or raw.endswith(".lock")):
        raise PlanError("PLAN_BASE_REF_INVALID")
    commit = handoff.git(root, "rev-parse", "--verify", raw + "^{commit}")
    sha = commit.decode("ascii").strip()
    if not GIT_SHA_RE.fullmatch(sha):
        raise PlanError("PLAN_BASE_SHA_INVALID")
    return sha


def git_paths(root: Path, base: str, manual: list[str]) -> list[str]:
    """Compare base commit to working tree, including staged and untracked.

    --no-renames makes both sides of a rename visible for path-based routing.\n    Union base/worktree, base/index, index/worktree so a reverted working\n    file with different staged bytes is not silently treated as unchanged.
    Git-ignored inputs are not observable unless explicitly supplied --path.
    """
    compared = handoff.git(root, "diff", "--no-ext-diff", "--no-renames",
                           "--name-only", "-z", base, "--")
    staged = handoff.git(root, "diff", "--cached", "--no-ext-diff",
                         "--no-renames", "--name-only", "-z", base, "--")
    unstaged = handoff.git(root, "diff", "--no-ext-diff", "--no-renames",
                           "--name-only", "-z", "--")
    untracked = handoff.git(root, "ls-files", "--others",
                            "--exclude-standard", "-z")
    try:
        names = [part.decode("utf-8")
                 for data in (compared, staged, unstaged, untracked)
                 for part in data.split(b"\x00") if part]
    except UnicodeDecodeError as exc:
        raise PlanError("PLAN_NON_UTF8_GIT_PATH") from exc
    paths = {handoff.relative_path(path) for path in names + manual}
    if any(path == ".git" or path.startswith(".git/") for path in paths):
        raise PlanError("PLAN_GIT_INTERNAL_PATH_FORBIDDEN")
    if len(paths) > MAX_PATHS:
        raise PlanError("PLAN_TOO_MANY_CHANGED_PATHS")
    return sorted(paths)


def observe(root: Path, base: str, manual: list[str]) -> dict:
    paths = git_paths(root, base, manual)
    snapshot = handoff.snapshot(
        root, sorted(set(paths) | {
            router.MANIFEST_PATH, router.LOCK_PATH,
            router.REQUIREMENT_INDEX_PATH,
        }),
    )
    return {
        "checkout_root": str(root),
        "base_sha": base,
        "head": snapshot["head"],
        "branch": snapshot["branch"],
        "index_sha256": digest(handoff.git(root, "ls-files", "--stage", "-z")),
        "status_sha256": digest(
            handoff.git(root, "status", "--porcelain=v1", "-z",
                        "--untracked-files=all")
        ),
        "changed_paths": paths,
        "observed_files": snapshot["observed_files"],
        "visibility": "base_to_worktree_tracked_plus_visible_untracked_and_explicit_paths",
    }


def plan_risk(paths: list[str]) -> tuple[list[dict], bool]:
    suggestions: dict[str, dict] = {}
    full = False
    for path in paths:
        suffix = Path(path).suffix.lower()
        name = Path(path).name
        if path.startswith(SENSITIVE_PREFIXES) or name in SENSITIVE_FILES:
            full = True
            suggestions["full_suite"] = {
                "id": "full_suite",
                "kind": "full_suite_review",
                "reason": "high-impact CI, generator, Spec, dependency, or build input changed",
                "command": None,
                "execution": "not_executed",
            }
        elif suffix in SOURCE_EXTENSIONS:
            key = "focused_source_tests"
            suggestions[key] = {
                "id": key,
                "kind": "targeted_test_discovery",
                "reason": "source code changed; identify actual affected tests and callers",
                "command": None,
                "execution": "not_executed",
            }
        elif suffix in DOCUMENT_EXTENSIONS:
            key = "documentation_consumer_review"
            suggestions[key] = {
                "id": key,
                "kind": "documentation_consumer_review",
                "reason": "confirm documentation is not a generator, parser, or Spec input",
                "command": None,
                "execution": "not_executed",
            }
        elif suffix in CONFIG_EXTENSIONS:
            full = True
            suggestions["full_suite"] = {
                "id": "full_suite",
                "kind": "full_suite_review",
                "reason": "configuration dependency coverage is unknown",
                "command": None,
                "execution": "not_executed",
            }
        else:
            full = True
            suggestions["full_suite"] = {
                "id": "full_suite",
                "kind": "full_suite_review",
                "reason": "unsupported file type; dependency coverage is unknown",
                "command": None,
                "execution": "not_executed",
            }
    return [suggestions[key] for key in sorted(suggestions)], full


def spec_candidates(root: Path, paths: list[str]) -> dict:
    manifest = root / router.MANIFEST_PATH
    lock = root / router.LOCK_PATH
    if not manifest.is_file() or not lock.is_file():
        return {
            "state": "missing",
            "catalog": None,
            "candidate_specs": [],
            "candidate_requirements": [],
            "gaps": ["SPECS_NOT_INSTALLED"],
        }
    try:
        state = router.load_state(root)
        direct = router.candidate_entries(state, paths)
        closure = router.dependency_closure(state, (entry.key for entry in direct))
        candidate_specs = []
        candidate_requirements = []
        gaps: list[str] = []
        for entry in closure:
            indexed = state.requirement_index.by_spec[entry.key]
            candidate_specs.append({
                "id": entry.key,
                "path": entry.path,
                "version": entry.version,
                "sha256": indexed.sha256,
                "selection": "path_candidate" if entry in direct else "spec_dependency",
                "mode": indexed.mode,
            })
            if indexed.mode == "whole-spec":
                gaps.append("WHOLE_SPEC_REQUIRES_MANUAL_REVIEW:" + entry.key)
                continue
            # Router validated every Requirement source range and its SHA.
            raw = router._read_bytes(
                router._resolve_regular(root, entry.path, "PLAN_SPEC_SOURCE_INVALID"),
                "PLAN_SPEC_SOURCE_INVALID", router.MAX_CONTEXT_BYTES,
            )
            if digest(raw) != indexed.sha256:
                raise PlanError("PLAN_SPEC_CHANGED_DURING_READ")
            for requirement in indexed.requirements:
                span = requirement.verification
                line = raw[span.start_byte:span.end_byte]
                if digest(line) != span.sha256:
                    raise PlanError("PLAN_VERIFICATION_ROW_CHANGED")
                candidate_requirements.append({
                    "id": requirement.requirement_id,
                    "spec_id": entry.key,
                    "title": requirement.title,
                    "activation_rule": requirement.activation,
                    "applicability": "requires_agent_review",
                    "published_verification_row": line.decode("utf-8").strip(),
                    "source": {
                        "path": entry.path,
                        "start_byte": span.start_byte,
                        "end_byte": span.end_byte,
                        "sha256": span.sha256,
                    },
                    "execution": "not_executed",
                })
        if paths and not direct:
            gaps.append("NO_SPEC_PATH_CANDIDATE")
        return {
            "state": "validated",
            "catalog": {
                "id": state.catalog_id,
                "version": state.catalog_version,
                "digest": state.catalog_digest,
                "revision": state.revision,
            },
            "candidate_specs": candidate_specs,
            "candidate_requirements": candidate_requirements,
            "gaps": sorted(set(gaps)),
        }
    except (router.RouterError, OSError, UnicodeError, ValueError) as exc:
        # An invalid installed Spec is an explicit evidence gap. Never use a
        # stale or inconsistent lock to claim that verification is sufficient.
        return {
            "state": "invalid",
            "catalog": None,
            "candidate_specs": [],
            "candidate_requirements": [],
            "gaps": ["SPEC_ROUTER_VALIDATION_FAILED:" + str(exc)[:256]],
        }


def calculate(root: Path, base: str, manual: list[str]) -> tuple[dict, int]:
    first = observe(root, base, manual)
    paths = first["changed_paths"]
    specs = spec_candidates(root, paths)
    suggestions, full = plan_risk(paths)
    if specs["state"] != "validated" or specs["gaps"]:
        full = True
    if full and "full_suite" not in {row["id"] for row in suggestions}:
        suggestions.append({
            "id": "full_suite",
            "kind": "full_suite_review",
            "reason": "Spec applicability or dependency coverage is incomplete",
            "command": None,
            "execution": "not_executed",
        })
    # A second observation rejects a mixed-time plan, including Spec changes.
    if observe(root, base, manual) != first:
        raise PlanError("PLAN_WORKTREE_CHANGED_DURING_READ")
    output = {
        "schema_version": SCHEMA_VERSION,
        "kind": "spec_aware_verification_plan",
        "mode": "shadow",
        "status": "incomplete" if specs["state"] != "validated" else "advisory",
        "revision": first,
        "specs": specs,
        "suggested_checks": sorted(suggestions, key=lambda row: row["id"]),
        "requires_full_suite_review": full,
        "evidence_gaps": specs["gaps"] + (["REQUIREMENT_ACTIVATION_NOT_ATTESTED"]
                                         if specs["candidate_requirements"] else []),
        "executed_checks": [],
        "verification_outcome": "not_executed",
        "authority": "advisory_only;not_an_approval_or_receipt;required_ci_unchanged",
    }
    return output, 1 if output["status"] == "incomplete" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="target Git worktree root")
    parser.add_argument("--base", default="HEAD", help="Git base ref or commit")
    parser.add_argument("--path", action="append", default=[],
                        help="explicit repository-relative observed path, may be repeated")
    args = parser.parse_args()
    try:
        root = handoff.repository_root(args.repo)
        base = base_revision(root, args.base)
        plan, status = calculate(root, base, args.path)
        sys.stdout.buffer.write(handoff.canonical(plan))
        return status
    except (PlanError, handoff.HandoffError, OSError, UnicodeError) as exc:
        print("verification-plan: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
