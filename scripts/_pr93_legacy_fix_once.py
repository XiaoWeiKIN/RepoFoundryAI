#!/usr/bin/env python3
"""One-shot, branch-scoped fixture repair; removed by its preparation workflow."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_COMMIT = "bb16b18d9457f048a737137f46603264043fba98"
EXPECTED = {
    "tests/test_foundryctl.py": "d788e25284a0115e6c25b670660d17935892aa39",
    "tests/test_writing_routes.py": "fb1591b3878d97675e8896c5f82a3a9057495a33",
}


def replace_once(text: str, old: str, new: str, count: int = 1) -> str:
    if text.count(old) != count:
        raise RuntimeError(f"Patch anchor changed: {old[:100]!r}")
    return text.replace(old, new)


def edit_function(text: str, name: str, old: str, new: str, count: int = 1) -> str:
    nodes = [node for node in ast.walk(ast.parse(text))
             if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(nodes) != 1:
        raise RuntimeError(f"Function anchor changed: {name}")
    node = nodes[0]
    lines = text.splitlines(keepends=True)
    part = "".join(lines[node.lineno - 1:node.end_lineno])
    return ("".join(lines[:node.lineno - 1])
            + replace_once(part, old, new, count)
            + "".join(lines[node.end_lineno:]))


def patch_fixtures() -> None:
    outputs = {}
    for relative, expected in EXPECTED.items():
        raw = (ROOT / relative).read_bytes()
        actual = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Source changed; refusing patch: {relative}")
        outputs[relative] = raw.decode("utf-8")
    name = "tests/test_foundryctl.py"
    text = outputs[name]
    text = replace_once(
        text, "from unittest import mock\n",
        "from unittest import mock\n\nfrom tests.harness_legacy_fixture import CORE_MEMORY_PATHS, strip_memory_assets\n",
    )
    for function, variable, version in (
        ("write_pre_project_skill_schema3_manifest", "payload", "1.0.0"),
        ("test_084_manifest_can_upgrade_after_core_skill_template_change", "manifest", "1.5.0"),
        ("test_090_upgrade_installs_maintenance_guidance_without_packing", "manifest", "1.5.1"),
        ("test_041_upgrade_installs_lightweight_analysis_routing", "manifest", "1.3.0"),
        ("test_030_core_upgrade_installs_the_selection_decision_gate", "manifest", "1.2.0"),
    ):
        anchor = f'        {variable}["core"]["version"] = "{version}"\n'
        text = edit_function(text, function, anchor,
                             anchor + f"        strip_memory_assets(self.repo, {variable})\n")
    anchor = ("                foundryctl.CORE_PROJECT_SKILL_PATH,\n"
              "                foundryctl.CODEX_PROJECT_SKILL_PATH,\n"
              "            },")
    text = edit_function(
        text, "test_schema3_component_upgrade_adds_project_skills_safely",
        anchor, anchor.replace("            },", "                *CORE_MEMORY_PATHS,\n            },"), 2,
    )
    outputs[name] = text
    name = "tests/test_writing_routes.py"
    text = replace_once(outputs[name], "from pathlib import Path\n",
                        "from pathlib import Path\n\nfrom tests.harness_legacy_fixture import strip_memory_assets\n")
    anchor = '        manifest["core"]["version"] = "1.5.4"\n'
    outputs[name] = edit_function(text, "old_harness", anchor,
                                 anchor + "        strip_memory_assets(self.repo, manifest)\n")
    for relative, text in outputs.items():
        ast.parse(text, filename=relative)
    for relative, text in outputs.items():
        (ROOT / relative).write_bytes(text.encode("utf-8"))
    print(json.dumps({"patched": sorted(outputs), "production_validator_changed": False}))


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"{args!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def inventory(repo: Path) -> dict[str, bytes]:
    return {path.relative_to(repo).as_posix(): path.read_bytes()
            for path in repo.rglob("*") if path.is_file()}


def verify_actual_old_install() -> None:
    sys.path.insert(0, str(ROOT))
    from tests.spec_git_fixture import create_git_catalog
    from tests.harness_legacy_fixture import CORE_MEMORY_PATHS
    with tempfile.TemporaryDirectory(prefix="pr93-real-migration-") as directory:
        base = Path(directory)
        old = base / "old-source"
        target = base / "target"
        target.mkdir()
        run("git", "worktree", "add", "--detach", str(old), OLD_COMMIT)
        try:
            catalog, _ = create_git_catalog(base)
            run(sys.executable, "-B", str(old / "scripts/foundryctl.py"), "--repo", str(target),
                "bootstrap", "--all-adapters", "--spec-repository", catalog.as_uri(),
                "--spec-ref", "main", "--required-only", "--apply")
            path = target / "docs/.engineering/harness.json"
            before_manifest = json.loads(path.read_text())
            assert before_manifest["core"]["version"] == "1.5.6"
            assert not any((target / relative).exists() for relative in CORE_MEMORY_PATHS)
            before = inventory(target)
            command = (sys.executable, "-B", str(ROOT / "scripts/foundryctl.py"), "--repo", str(target))
            version = (ROOT / "VERSION").read_text().strip()
            preview = json.loads(run(*command, "upgrade", "--to", version))
            assert inventory(target) == before, "preview changed the old installation"
            creates = {row["path"] for row in preview["actions"] if row["action"] == "create_file"}
            assert CORE_MEMORY_PATHS <= creates
            applied = json.loads(run(*command, "upgrade", "--to", version, "--apply"))
            migrated = json.loads(path.read_text())
            assert migrated["core"]["version"] == "1.6.0"
            assert CORE_MEMORY_PATHS <= set(applied["created"])
            assert not (target / ".repo-foundry/memory-context.json").exists()
            for relative, data in before.items():
                if relative.startswith("docs/agent-guides/managed/") or relative in {
                    "docs/.engineering/specs.json", "docs/.engineering/specs.lock.json"
                }:
                    assert (target / relative).read_bytes() == data, relative
            run(*command, "validate", "--harness")
            after = inventory(target)
            repeated = json.loads(run(*command, "upgrade", "--to", version, "--apply"))
            assert repeated["created"] == [] and repeated["updated"] == []
            assert inventory(target) == after
            print(json.dumps({"actual_old_source": OLD_COMMIT, "from_core": "1.5.6",
                              "to_core": "1.6.0", "created": applied["created"],
                              "preview_read_only": True, "idempotent": True,
                              "locked_specs_unchanged": True, "cooling_enabled": False}))
        finally:
            run("git", "worktree", "remove", "--force", str(old))


if __name__ == "__main__":
    if sys.argv[1:] == ["--verify-actual"]:
        verify_actual_old_install()
    elif not sys.argv[1:]:
        patch_fixtures()
    else:
        raise SystemExit("Unsupported invocation")
