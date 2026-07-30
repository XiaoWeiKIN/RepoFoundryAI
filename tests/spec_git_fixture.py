from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


SPEC_CONTENTS = {
    "specification/core/semantic-naming.md": (
        "# Semantic Naming\n\nUse stable semantic names.\n"
    ),
    "specification/languages/go.md": (
        "# Go Implementation\n\nParse boundary data before core logic.\n"
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


def create_git_catalog(parent: Path) -> tuple[Path, str]:
    repository = parent / "specification-source"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    write_catalog(repository)
    commit = commit_all(repository, "initial catalog")
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
    return commit_all(repository, "update Go specification")
