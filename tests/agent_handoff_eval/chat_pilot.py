#!/usr/bin/env python3
"""Offline ChatGPT Chat A/B evaluation fixture; never calls or simulates a model."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
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


MAX_FILES = 20000
MAX_FILE_BYTES = 64 * 1024 * 1024
SNAPSHOT_PROOF = "interruption-fingerprint.json"


@contextmanager
def pilot_lock(root):
    """Refuse concurrent pilot CLI mutations; do not hide an abandoned lock."""
    lock = root / ".pilot-command.lock"
    if lock.is_symlink():
        raise ValueError("unsafe pilot lock")
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValueError("pilot command already active or stale lock present") from exc
    try:
        yield
    finally:
        lock.rmdir()


def git_raw(work, *args):
    result = subprocess.run(
        ["git", "-C", str(work), *args],
        capture_output=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0",
                                  "GIT_TERMINAL_PROMPT": "0"},
        timeout=20,
    )
    if result.returncode:
        raise RuntimeError("Git observation failed; no valid snapshot")
    return result.stdout


def files_manifest(work):
    """Hash all visible and ignored workspace files, without following symlinks."""
    if work.is_symlink() or not (work / ".git").is_dir():
        raise ValueError("not a managed Git checkout")
    entries = []
    for parent, directories, filenames in os.walk(work, topdown=True, followlinks=False):
        here = Path(parent)
        directories.sort()
        filenames.sort()
        for name in list(directories):
            target = here / name
            if here == work and name == ".git":
                directories.remove(name)
            elif target.is_symlink():
                directories.remove(name)
                filenames.append(name)
        for name in sorted(filenames):
            path = here / name
            relative = path.relative_to(work).as_posix()
            meta = path.lstat()
            mode = stat.S_IMODE(meta.st_mode)
            if stat.S_ISLNK(meta.st_mode):
                entry = {"path": relative, "kind": "symlink",
                         "sha256": hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest(),
                         "mode": mode}
            elif stat.S_ISREG(meta.st_mode):
                if meta.st_size > MAX_FILE_BYTES:
                    raise ValueError("snapshot source exceeds 64 MiB: " + relative)
                h = hashlib.sha256()
                size = 0
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                with os.fdopen(os.open(path, flags), "rb") as data:
                    while True:
                        chunk = data.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > MAX_FILE_BYTES:
                            raise ValueError("snapshot source too large: " + relative)
                        h.update(chunk)
                entry = {"path": relative, "kind": "regular", "sha256": h.hexdigest(),
                         "mode": mode}
            else:
                raise ValueError("unsupported workspace node: " + relative)
            entries.append(entry)
            if len(entries) > MAX_FILES:
                raise ValueError("too many workspace files to validate")
    return sorted(entries, key=lambda row: row["path"])


def workspace_fingerprint(work):
    """Stable HEAD/index/status and bytes; exclude Git internals except index projection."""
    manifest = files_manifest(work)
    projection = {
        "head": git_raw(work, "rev-parse", "--verify", "HEAD").decode("ascii").strip(),
        "branch": git_raw(work, "rev-parse", "--abbrev-ref", "HEAD").decode("utf-8").strip(),
        "index_sha256": hashlib.sha256(git_raw(work, "ls-files", "--stage", "-z")).hexdigest(),
        "status_sha256": hashlib.sha256(git_raw(
            work, "status", "--porcelain=v1", "-z", "--untracked-files=all"
        )).hexdigest(),
        "files": manifest,
    }
    projection["fingerprint_sha256"] = hashlib.sha256(encoded(projection)).hexdigest()
    return projection


def load_proof(root):
    path = root / "snapshots" / SNAPSHOT_PROOF
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing immutable interruption fingerprint")
    proof = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(proof, dict) or proof.get("schema") != 1 or
        proof.get("fingerprint_sha256") !=
        hashlib.sha256(encoded({k: v for k, v in proof.items()
                                if k != "fingerprint_sha256"})).hexdigest()):
        raise ValueError("invalid interruption fingerprint")
    required = {"schema", "head", "branch", "index_sha256", "status_sha256",
                "files", "fingerprint_sha256"}
    if set(proof) != required or not isinstance(proof["files"], list):
        raise ValueError("invalid interruption proof schema")
    return proof


def differences(expected, observed):
    mismatches = []
    for key in ("head", "branch", "index_sha256", "status_sha256"):
        if expected[key] != observed[key]:
            mismatches.append(key)
    before = {row["path"]: row for row in expected["files"]}
    after = {row["path"]: row for row in observed["files"]}
    for name in sorted(before.keys() | after.keys()):
        if before.get(name) != after.get(name):
            mismatches.append(name)
    return mismatches


def load_arm(root):
    path = root / "current-arm.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("no active experiment arm")
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("arm") not in ARMS or (
        state.get("status") not in (
            "restored_unverified", "ready", "invalid_environment", "graded"
        )
    ) or not isinstance(state.get("attempt_id"), str):
        raise ValueError("invalid arm state")
    return state


def update_arm(root, state):
    path = root / "current-arm.json"
    new = root / ("current-arm." + state["attempt_id"] + ".tmp")
    with new.open("xb") as stream:
        stream.write(encoded(state))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(new, path)


def invalid_record(root, state, mismatches):
    state = dict(state, status="invalid_environment",
                 invalid_at=timestamp(), mismatched_paths=mismatches)
    evidence = root / "results" / ("invalid-" + state["attempt_id"] + ".json")
    with evidence.open("xb") as stream:
        stream.write(encoded(state))
    update_arm(root, state)
    return state

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
    with pilot_lock(root):
        work = root / "workspace"
        saved = root / "snapshots" / "interruption"
        proof_path = root / "snapshots" / SNAPSHOT_PROOF
        if saved.exists() or proof_path.exists():
            raise ValueError("interruption already captured")
        before = workspace_fingerprint(work)
        shutil.copytree(work, saved, symlinks=True)
        try:
            saved_now = workspace_fingerprint(saved)
            after = workspace_fingerprint(work)
            if differences(before, saved_now) or differences(before, after):
                raise ValueError("Git or file bytes changed during snapshot")
            proof = {"schema": 1, **before}
            with proof_path.open("xb") as stream:
                stream.write(encoded(proof))
        except BaseException:
            shutil.rmtree(saved)
            raise
    print(json.dumps({"saved": str(saved), "fingerprint_sha256": before["fingerprint_sha256"],
                      "model_execution_verified": False}))


def fingerprint(args):
    root, _ = owned(args.root)
    with pilot_lock(root):
        observed = workspace_fingerprint(root / "workspace")
    print(json.dumps({
        "fingerprint_sha256": observed["fingerprint_sha256"],
        "head": observed["head"],
        "branch": observed["branch"],
        "index_sha256": observed["index_sha256"],
        "status_sha256": observed["status_sha256"],
        "file_count": len(observed["files"]),
    }))


def restore(args):
    root, _ = owned(args.root)
    with pilot_lock(root):
        work = root / "workspace"
        saved = root / "snapshots" / "interruption"
        if not saved.is_dir() or saved.is_symlink() or work.is_symlink():
            raise ValueError("restore requires a real managed snapshot")
        previous_path = root / "current-arm.json"
        if previous_path.exists() or previous_path.is_symlink():
            previous = load_arm(root)
            if previous["status"] in ("restored_unverified", "ready"):
                raise ValueError("another arm is active; grade or invalidate it first")
            if previous["status"] == "invalid_environment" and (
                not args.retry_invalid or previous["arm"] != args.arm
            ):
                raise ValueError("invalid environment; retry same arm with --retry-invalid")
        elif args.retry_invalid:
            raise ValueError("no failed restoration to retry")
        if (root / "results" / (args.arm + ".json")).exists():
            raise ValueError("arm already graded; use a fresh pilot")
        frozen = load_proof(root)
        if differences(frozen, workspace_fingerprint(saved)):
            raise ValueError("frozen snapshot drifted; refuse restore")
        if not (work / ".git").is_dir():
            raise ValueError("current workspace is not a local Git checkout")
        attempt = uuid.uuid4().hex
        staging = root / (".workspace-staging-" + attempt)
        try:
            shutil.copytree(saved, staging, symlinks=True)
            if differences(frozen, workspace_fingerprint(staging)):
                raise ValueError("staged restore does not match frozen snapshot")
            shutil.rmtree(work)
            os.replace(staging, work)
            observed = workspace_fingerprint(work)
            mismatches = differences(frozen, observed)
            state = {
                "arm": args.arm, "attempt_id": attempt, "time": timestamp(),
                "status": "restored_unverified",
                "expected_fingerprint": frozen["fingerprint_sha256"],
                "restored_fingerprint": observed["fingerprint_sha256"],
            }
            if mismatches:
                invalid_record(root, state, mismatches)
                raise ValueError("restore mismatched frozen snapshot: " + str(mismatches))
            update_arm(root, state)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print(json.dumps({"arm": args.arm, "workspace": str(work),
                      "status": "restored_unverified", "attempt_id": attempt,
                      "fingerprint_sha256": observed["fingerprint_sha256"],
                      "model_execution_verified": False}))


def verify_restore(args):
    root, _ = owned(args.root)
    with pilot_lock(root):
        current = load_arm(root)
        if current["status"] != "restored_unverified":
            raise ValueError("arm must be restored and not yet verified")
        frozen = load_proof(root)
        saved = workspace_fingerprint(root / "snapshots" / "interruption")
        actual = workspace_fingerprint(root / "workspace")
        mismatches = differences(frozen, saved) + differences(frozen, actual)
        mismatches = sorted(set(mismatches))
        if mismatches:
            invalid_record(root, current, mismatches)
            print(json.dumps({
                "status": "invalid_environment", "arm": current["arm"],
                "snapshot_matches": False, "mismatched_paths": mismatches,
                "attempt_id": current["attempt_id"],
            }))
            return 1
        update_arm(root, dict(current, status="ready", verified_at=timestamp()))
    print(json.dumps({
        "status": "ready", "arm": current["arm"], "snapshot_matches": True,
        "head_matches": True, "index_matches": True, "files_match": True,
        "mismatched_paths": [], "attempt_id": current["attempt_id"],
        "fingerprint_sha256": actual["fingerprint_sha256"],
    }))
    return 0


def grade(args):
    root, info = owned(args.root)
    with pilot_lock(root):
        active = load_arm(root)
        if active["status"] != "ready":
            raise ValueError("verify-restore must pass independently before grading")
        arm = active["arm"]
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
            "restore_attempt_id": active["attempt_id"],
            "restore_verified_at": active["verified_at"],
        }
        with report.open("xb") as handle:
            handle.write(encoded(record))
        update_arm(root, dict(active, status="graded", graded_at=timestamp()))
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
                         ("restore", restore), ("fingerprint", fingerprint),
                         ("verify-restore", verify_restore), ("grade", grade), ("summary", summary)):
        p = commands.add_parser(name)
        p.add_argument("--root", required=True)
        if name == "prepare":
            p.add_argument("--case", choices=CASES, required=True)
        if name == "restore":
            p.add_argument("--arm", choices=ARMS, required=True)
            p.add_argument("--retry-invalid", action="store_true")
        p.set_defaults(fn=action)
    args = parser.parse_args()
    try:
        result = args.fn(args)
        return result if isinstance(result, int) else 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print("chat-pilot: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
