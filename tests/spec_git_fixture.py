from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


SPEC_CONTENTS = {
    "specification/core/semantic-naming.md": (
        "# Semantic Naming\n\n"
        "## Purpose\n\nUse stable semantic names.\n\n"
        "## Applicability\n\nLoad for shared public names.\n\n"
        "## Agent workflow\n\n1. Inspect public call sites.\n\n"
        "## Terminology\n\nA public name is caller-visible.\n\n"
        "## Requirements\n\n"
        "### SEM-NAME-001 — Names expose observable behavior\n\n"
        "**Activation:** Load when changing a shared or public name.\n\n"
        "**Context dependencies:** None\n\n"
        "Public names **MUST** expose observable behavior.\n\n"
        "**Rationale (non-normative):** Prevent semantic drift.\n\n"
        "**Enforcement (review):** Review call sites.\n\n"
        "**Evidence:** Reviewed public API.\n\n"
        "## Exceptions\n\nNone.\n\n"
        "## Verification\n\n"
        "| Requirement | Minimum verification |\n"
        "| --- | --- |\n"
        "| `SEM-NAME-001` | Public API review |\n\n"
        "## Agent handoff\n\nReport the activated Requirement.\n\n"
        "## Compatibility and migration\n\nPreserve published names.\n"
    ),
    "specification/languages/go.md": (
        "# Go Implementation\n\n"
        "## Purpose\n\nKeep Go APIs clear and verifiable.\n\n"
        "## Applicability\n\nLoad for hand-written Go changes.\n\n"
        "## Agent workflow\n\n1. Inspect Go call sites.\n\n"
        "## Terminology\n\nAn exported API is caller-visible.\n\n"
        "## Requirements\n\n"
        "### GO-NAME-001 — Go names preserve shared semantics\n\n"
        "**Activation:** Load when changing a Go package or API name.\n\n"
        "**Context dependencies:** `SEM-NAME-001`\n\n"
        "Go names **MUST** preserve `SEM-NAME-001`.\n\n"
        "**Rationale (non-normative):** Keep language and shared meaning aligned.\n\n"
        "**Enforcement (review):** Review declarations and call sites.\n\n"
        "**Evidence:** Reviewed Go API.\n\n"
        "### GO-TEST-001 — Go changes have focused evidence\n\n"
        "**Activation:** Load when adding or reviewing Go tests.\n\n"
        "**Context dependencies:** None\n\n"
        "Go changes **MUST** have focused verification.\n\n"
        "**Rationale (non-normative):** Catch contract regressions.\n\n"
        "**Enforcement (mechanical):** Run focused tests.\n\n"
        "**Evidence:** Focused test output with UNRELATED-TEST-SENTINEL.\n\n"
        "## Exceptions\n\nNone.\n\n"
        "## Verification\n\n"
        "| Requirement | Minimum verification |\n"
        "| --- | --- |\n"
        "| `GO-NAME-001` | Go API review |\n"
        "| `GO-TEST-001` | Focused Go tests |\n\n"
        "## Agent handoff\n\nReport exact Requirement IDs.\n\n"
        "## Compatibility and migration\n\nPreserve exported Go APIs.\n"
    ),
    "specification/languages/typescript.md": (
        "# TypeScript Implementation\n\nTreat external values as unknown.\n"
    ),
    "specification/languages/python.md": (
        "# Python Implementation\n\nUse typed boundary parsers.\n"
    ),
}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def catalog_data(
    contents: dict[str, str],
    *,
    catalog_version: str = "0.1.0",
) -> dict[str, object]:
    return {
        "catalog_id": "test.engineering-specifications",
        "catalog_version": catalog_version,
        "schema_version": 1,
        "specs": [
            {
                "applies_to": ["**/*"],
                "description": "Semantic naming fixture",
                "id": "core/semantic-naming",
                "path": "specification/core/semantic-naming.md",
                "required": True,
                "requires": [],
                "sha256": sha256(
                    contents[
                        "specification/core/semantic-naming.md"
                    ].encode("utf-8")
                ),
                "version": catalog_version,
            },
            {
                "applies_to": ["**/*.go", "**/go.mod", "**/go.work"],
                "description": "Go implementation fixture",
                "detection": {
                    "extensions": [".go"],
                    "filenames": ["go.mod", "go.work"],
                },
                "id": "languages/go",
                "path": "specification/languages/go.md",
                "required": False,
                "requires": ["core/semantic-naming"],
                "sha256": sha256(
                    contents["specification/languages/go.md"].encode("utf-8")
                ),
                "version": catalog_version,
            },
            {
                "applies_to": [
                    "**/*.ts",
                    "**/*.tsx",
                    "**/*.mts",
                    "**/*.cts",
                    "**/tsconfig*.json",
                ],
                "description": "TypeScript implementation fixture",
                "detection": {
                    "extensions": [".cts", ".mts", ".ts", ".tsx"],
                    "filenames": ["tsconfig.json"],
                },
                "id": "languages/typescript",
                "path": "specification/languages/typescript.md",
                "required": False,
                "requires": ["core/semantic-naming"],
                "sha256": sha256(
                    contents[
                        "specification/languages/typescript.md"
                    ].encode("utf-8")
                ),
                "version": catalog_version,
            },
            {
                "applies_to": [
                    "**/*.py",
                    "**/*.pyi",
                    "**/pyproject.toml",
                    "**/requirements*.txt",
                ],
                "description": "Python implementation fixture",
                "detection": {
                    "extensions": [".py", ".pyi"],
                    "filenames": [
                        "pyproject.toml",
                        "requirements.txt",
                        "setup.py",
                    ],
                },
                "id": "languages/python",
                "path": "specification/languages/python.md",
                "required": False,
                "requires": ["core/semantic-naming"],
                "sha256": sha256(
                    contents[
                        "specification/languages/python.md"
                    ].encode("utf-8")
                ),
                "version": catalog_version,
            },
        ],
    }


def write_catalog(
    root: Path,
    *,
    contents: dict[str, str] | None = None,
    catalog: dict[str, object] | None = None,
    catalog_version: str = "0.1.0",
) -> dict[str, object]:
    selected_contents = dict(SPEC_CONTENTS if contents is None else contents)
    for relative, text in selected_contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    selected_catalog = (
        catalog_data(selected_contents, catalog_version=catalog_version)
        if catalog is None
        else catalog
    )
    (root / "catalog.json").write_text(
        json.dumps(selected_catalog, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return selected_catalog


def git(
    repository: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        text=True,
        capture_output=True,
        timeout=20,
        check=True,
    )


def commit_all(repository: Path, message: str) -> str:
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=Engineering Spec Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD").stdout.strip()


def tag_release(repository: Path, version: str) -> None:
    git(
        repository,
        "-c",
        "user.name=Engineering Spec Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "tag",
        "-a",
        f"v{version}",
        "-m",
        f"fixture Catalog v{version}",
    )


def create_git_catalog(parent: Path) -> tuple[Path, str]:
    repository = parent / "specification-source"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    write_catalog(repository)
    commit = commit_all(repository, "initial catalog")
    tag_release(repository, "0.1.0")
    return repository, commit


def update_go_spec(
    repository: Path,
    *,
    catalog_version: str = "0.2.0",
) -> str:
    contents = {
        relative: (repository / relative).read_text(encoding="utf-8")
        for relative in SPEC_CONTENTS
    }
    contents["specification/languages/go.md"] = (
        "# Go Implementation\n\nUpdated remote rule.\n"
    )
    write_catalog(
        repository,
        contents=contents,
        catalog_version=catalog_version,
    )
    commit = commit_all(repository, "update Go specification")
    tag_release(repository, catalog_version)
    return commit
