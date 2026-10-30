#!/usr/bin/env python3
"""Offline ChatGPT Chat A/B evaluation fixture; never calls or simulates a model."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ARMS = ("control", "handoff", "receipt")
CASES = ("pagination", "stale-receipt")
MARKER = ".chat-pilot-owned.json"
FILES = {
 "pagination": {
  "paging.py": '''def page(items, page_size, cursor=0):
    """Return (items, next_cursor); None means the final page."""
    if page_size <= 0 or page_size > 100 or cursor < 0:
        raise ValueError("invalid page request")
    selected = items[cursor:cursor + page_size]
    end = cursor + len(selected)
    return selected, (end if len(selected) == page_size else None)
''',
  "test_visible.py": '''import unittest
from paging import page

class Visible(unittest.TestCase):
    def test_has_more(self):
        self.assertEqual(page([1, 2, 3], 2), ([1, 2], 2))
''',
 },
 "stale-receipt": {
  "quota.py": '''def request_allowed(used, limit):
    """Enforce nonnegative quota without changing the function signature."""
    if used < 0 or limit < 0:
        raise ValueError("negative quota")
    return used <= limit  # at the boundary, another request is forbidden
''',
  "test_visible.py": '''import unittest
from quota import request_allowed

class Visible(unittest.TestCase):
    def test_below_limit(self):
        self.assertTrue(request_allowed(2, 3))
''',
 },
}
ACCEPTANCE = {
 "pagination": '''import sys, unittest
sys.path.insert(0, sys.argv[1])
from paging import page
class Check(unittest.TestCase):
    def test_exact_boundary(self):
        self.assertEqual(page([1,2,3,4], 2, 2), ([3,4], None))
    def test_partial_final(self):
        self.assertEqual(page([1,2,3], 2, 2), ([3], None))
    def test_empty(self):
        self.assertEqual(page([], 2), ([], None))
    def test_next(self):
        self.assertEqual(page([1,2,3], 2), ([1,2], 2))
if __name__ == "__main__": unittest.main(argv=[sys.argv[0]])
''',
 "stale-receipt": '''import sys, unittest
sys.path.insert(0, sys.argv[1])
from quota import request_allowed
class Check(unittest.TestCase):
    def test_boundary(self):
        self.assertFalse(request_allowed(3,3))
    def test_zero(self):
        self.assertFalse(request_allowed(0,0))
    def test_below(self):
        self.assertTrue(request_allowed(2,3))
    def test_negative(self):
        with self.assertRaises(ValueError): request_allowed(-1,3)
if __name__ == "__main__": unittest.main(argv=[sys.argv[0]])
''',
}

def timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

def safe_root(value, must_exist):
    root = Path(os.path.abspath(value))
    if root == Path("/") or root.is_symlink():
        raise ValueError("unsafe evaluation root")
    for parent in root.parents:
        if parent.is_symlink():
            raise ValueError("symlink parent")
    if must_exist and not root.is_dir():
        raise ValueError("missing evaluation root")
    return root

def owned(value):
    root = safe_root(value, True)
    path = root / MARKER
    if path.is_symlink() or not path.is_file():
        raise ValueError("unmanaged evaluation root")
    info = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(info, dict) or info != {"schema": 1, "root": str(root), "case": info.get("case")} or info["case"] not in CASES:
        raise ValueError("invalid ownership marker")
    return root, info

def git(work, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-C", str(work), *args],
                            capture_output=True, text=True, env=env, timeout=15)
    if result.returncode:
        raise RuntimeError("git command failed: " + result.stderr[:200])
    return result.stdout.strip()

def prepare(args):
    root = safe_root(args.root, False)
    if root.exists():
        raise ValueError("prepare never overwrites an existing path")
    root.mkdir(mode=0o700)
    try:
        work = root / "workspace"
        work.mkdir()
        for name in ("private", "snapshots", "results"):
            (root / name).mkdir(mode=0o700)
        (root / MARKER).write_bytes(encoded({"schema": 1, "root": str(root), "case": args.case}))
        for name, data in FILES[args.case].items():
            (work / name).write_text(data, encoding="utf-8")
        git(work, "init", "-b", "main")
        git(work, "-c", "user.name=Chat Pilot Fixture", "-c", "user.email=fixture@example.invalid",
            "add", ".")
        git(work, "-c", "user.name=Chat Pilot Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-m", "initial task")
        (root / "private" / "acceptance.py").write_text(ACCEPTANCE[args.case], encoding="utf-8")
        task = ("Fix end-of-pagination cursor semantics" if args.case == "pagination" else
                "Fix strict request quota boundary and inspect stale test evidence")
        (root / "task.txt").write_text(task + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(root)
        raise
    print(json.dumps({"workspace": str(work), "case": args.case,
                      "model_executions": 0, "task": str(root / "task.txt")}))

def inject(args):
    root, info = owned(args.root)
    if info["case"] != "stale-receipt" or (root / "snapshots" / "interruption").exists():
        raise ValueError("inject is allowed only before stale-receipt snapshot")
    source = root / "workspace" / "quota.py"
    if source.is_symlink() or not source.is_file():
        raise ValueError("invalid source")
    tag = "\n# Controlled post-receipt change: prior verification must be rechecked.\n"
    data = source.read_text(encoding="utf-8")
    if tag in data:
        raise ValueError("drift already injected")
    source.write_text(data + tag, encoding="utf-8")
    print(json.dumps({"source_changed": "quota.py", "old_receipt_should_be": "stale"}))

def snapshot(args):
    root, _ = owned(args.root)
    work = root / "workspace"
    saved = root / "snapshots" / "interruption"
    if saved.exists() or not (work / ".git").is_dir():
        raise ValueError("already saved or no local Git checkout")
    shutil.copytree(work, saved, symlinks=True)
    if git(work, "status", "--porcelain=v1", "--untracked-files=all") != git(saved, "status", "--porcelain=v1", "--untracked-files=all"):
        shutil.rmtree(saved)
        raise ValueError("Git state drift during snapshot")
    print(json.dumps({"saved": str(saved), "model_execution_verified": False}))

def restore(args):
    root, _ = owned(args.root)
    work = root / "workspace"
    saved = root / "snapshots" / "interruption"
    if not saved.is_dir() or saved.is_symlink() or work.is_symlink() or not (work / ".git").is_dir():
        raise ValueError("restore requires a managed Git workspace and snapshot")
    if (root / "results" / (args.arm + ".json")).exists():
        raise ValueError("arm already graded; use a fresh pilot")
    # Explicit destructive operation, restricted to the fixture's owned workspace.
    shutil.rmtree(work)
    shutil.copytree(saved, work, symlinks=True)
    (root / "current-arm.json").write_bytes(encoded({"arm": args.arm, "time": timestamp()}))
    print(json.dumps({"arm": args.arm, "workspace": str(work), "model_execution_verified": False}))

def grade(args):
    root, info = owned(args.root)
    arm_path = root / "current-arm.json"
    if arm_path.is_symlink() or not arm_path.is_file():
        raise ValueError("restore an experiment arm first")
    arm = json.loads(arm_path.read_text())["arm"]
    if arm not in ARMS:
        raise ValueError("invalid arm")
    report = root / "results" / (arm + ".json")
    if report.exists():
        raise ValueError("grade is write-once")
    work = root / "workspace"
    test = root / "private" / "acceptance.py"
    result = subprocess.run([sys.executable, "-B", str(test), str(work)],
                            cwd=work, capture_output=True, timeout=15,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    record = {
        "case": info["case"], "arm": arm, "time": timestamp(),
        "acceptance_passed": result.returncode == 0, "test_exit_code": result.returncode,
        "head": git(work, "rev-parse", "HEAD"),
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        "model_execution_verified": False, "agent_success_rate": None,
        "stale_evidence_judgment": "requires_authentic_chat_transcript",
    }
    with report.open("xb") as handle:
        handle.write(encoded(record))
    print(json.dumps(record))

def summary(args):
    root, info = owned(args.root)
    arms = {}
    for arm in ARMS:
        p = root / "results" / (arm + ".json")
        arms[arm] = json.loads(p.read_text())["acceptance_passed"] if p.is_file() else None
    print(json.dumps({"case": info["case"], "acceptance_by_arm": arms,
                      "complete": all(x is not None for x in arms.values()),
                      "model_execution_verified": False, "agent_success_rate": None,
                      "scope": "scripted acceptance only; no ChatGPT Chat invocation"}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name, action in (("prepare", prepare), ("inject", inject), ("snapshot", snapshot),
                         ("restore", restore), ("grade", grade), ("summary", summary)):
        p = commands.add_parser(name)
        p.add_argument("--root", required=True)
        if name == "prepare":
            p.add_argument("--case", choices=CASES, required=True)
        if name == "restore":
            p.add_argument("--arm", choices=ARMS, required=True)
        p.set_defaults(fn=action)
    args = parser.parse_args()
    try:
        args.fn(args)
        return 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print("chat-pilot: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
