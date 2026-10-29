"""Test-only helpers for synthetic pre-memory Harness installations.

These fixtures reproduce the historical file-set boundary, not every historical
seed byte. Keep the paths independent of production versioned_file_assets so a
regression in that function cannot silently change the expected test input.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


CORE_MEMORY_PATHS = frozenset({
    ".repo-foundry/engineering-specs/memory_retrieval.py",
    ".repo-foundry/engineering-specs/memory_runtime.py",
})


def strip_memory_assets(repo: Path, manifest: dict[str, Any]) -> None:
    """Remove 1.6-only records AND files when constructing an older fixture.

    Never use this helper in product code or to repair an actual installation.
    Version/file mismatches must still be rejected by production validation.
    """
    version = tuple(int(part) for part in manifest["core"]["version"].split("."))
    if len(version) != 3 or version >= (1, 6, 0):
        raise AssertionError("fixture must declare a Core version before 1.6.0")
    records = manifest["files"]
    for record in records:
        if record["path"] in CORE_MEMORY_PATHS:
            if record["owner_kind"] != "core" or record.get("owner_id") is not None:
                raise AssertionError("memory fixture path has unexpected ownership")
    targets = [repo / relative for relative in sorted(CORE_MEMORY_PATHS)]
    for path in targets:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise AssertionError("fixture cleanup requires ordinary memory files")
    for path in targets:
        path.unlink(missing_ok=True)
    manifest["files"] = [
        record for record in records if record["path"] not in CORE_MEMORY_PATHS
    ]
