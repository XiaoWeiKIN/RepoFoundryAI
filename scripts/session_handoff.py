#!/usr/bin/env python3
"""Explicit, local, non-authoritative session handoff and resume checks.

No Hooks, agent orchestration, EP lifecycle changes, or verification approval.
Python 3.10+. Output is JSON; capture without --output is read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 128 * 1024
MAX_CHANGED_PATHS = 512
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TEXT_BYTES = 4096
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


class HandoffError(Exception):
    """An unsafe or incomplete observation, not a successful handoff."""


def canonical(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> bytes:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "core.fsmonitor=false", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, timeout=30, check=False,
    )
    if result.returncode:
        raise HandoffError("git " + args[0] + " failed; no verified repository snapshot")
    return result.stdout


def repository_root(raw: str) -> Path:
    root = Path(raw).resolve(strict=True)
    if not root.is_dir():
        raise HandoffError("--repo must name a directory")
    actual = Path(git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    if root != actual:
        raise HandoffError("--repo must be the Git worktree root, not a subdirectory")
    return root


def check_text(value: str, name: str, *, required: bool = False) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise HandoffError(name + " must be bounded UTF-8 text")
    if required and not value.strip():
        raise HandoffError(name + " cannot be empty")
    if "\x00" in value:
        raise HandoffError(name + " contains NUL")
    return value


def relative_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise HandoffError("invalid repository-relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("..", ".") for part in raw.split("/")):
        raise HandoffError("path traversal or absolute path is forbidden")
    normalized = path.as_posix()
    if normalized == "." or normalized != raw:
        raise HandoffError("non-canonical repository path")
    return normalized


def entry(root: Path, raw: str) -> dict[str, str]:
    name = relative_path(raw)
    path = root
    parts = PurePosixPath(name).parts
    for part in parts[:-1]:
        path = path / part
        if path.is_symlink():
            raise HandoffError("symlink parent in observed path: " + name)
    path = path / parts[-1]
    if path.is_symlink():
        # Never follow links outside the repository; hash the link text only.
        return {"path": name, "kind": "symlink",
                "sha256": digest(os.fsencode(os.readlink(path)))}
    if not path.exists():
        return {"path": name, "kind": "absent", "sha256": ""}
    if not path.is_file():
        raise HandoffError("observed path is not a regular file: " + name)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise HandoffError("observed source changed type: " + name)
        h = hashlib.sha256()
        seen = 0
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            seen += len(chunk)
            if seen > MAX_FILE_BYTES:
                raise HandoffError("observed file exceeds size limit: " + name)
            h.update(chunk)
    return {"path": name, "kind": "regular", "sha256": h.hexdigest()}


def changed_status(root: Path) -> list[dict[str, str]]:
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    chunks = raw.split(b"\x00")
    changed: list[dict[str, str]] = []
    index = 0
    while index < len(chunks):
        token = chunks[index]
        index += 1
        if not token:
            continue
        if len(token) < 4 or token[2:3] != b" ":
            raise HandoffError("malformed Git porcelain status")
        try:
            code = token[:2].decode("ascii")
            name = relative_path(token[3:].decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise HandoffError("unrepresentable Git status path") from exc
        row = {"path": name, "code": code}
        if "R" in code or "C" in code:
            if index >= len(chunks) or not chunks[index]:
                raise HandoffError("incomplete Git rename status")
            try:
                row["previous_path"] = relative_path(chunks[index].decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise HandoffError("unrepresentable Git rename path") from exc
            index += 1
        changed.append(row)
        if len(changed) > MAX_CHANGED_PATHS:
            raise HandoffError("too many changed files; narrow the task")
    return sorted(changed, key=lambda row: (row["path"], row["code"]))


def snapshot(root: Path, requested: list[str]) -> dict[str, object]:
    head = git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD").decode("utf-8").strip() if (
        subprocess.run(["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    ) else None
    changes = changed_status(root)
    paths = set(requested)
    for row in changes:
        paths.add(row["path"])
        if "previous_path" in row:
            paths.add(row["previous_path"])
    if len(paths) > MAX_CHANGED_PATHS:
        raise HandoffError("too many observed paths")
    return {
        "checkout_root": str(root),
        "head": head,
        "branch": branch,
        "changes": changes,
        "observed_files": [entry(root, name) for name in sorted(paths)],
        "coverage": "tracked_changes_and_visible_untracked_plus_explicit_paths",
    }


def safe_path(raw: str) -> Path:
    path = Path(os.path.abspath(raw))
    if path.is_symlink():
        raise HandoffError("handoff file cannot be a symlink")
    current = path.parent
    while current != current.parent:
        if current.is_symlink():
            raise HandoffError("handoff file parent cannot be a symlink")
        current = current.parent
    return path


def write_new(raw: str, content: bytes) -> None:
    path = safe_path(raw)
    if len(content) > MAX_RECORD_BYTES:
        raise HandoffError("handoff record too large")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def read_record(raw: str) -> dict[str, object]:
    path = safe_path(raw)
    if not path.is_file() or path.stat().st_size > MAX_RECORD_BYTES:
        raise HandoffError("missing, non-file, or oversized handoff")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        data = handle.read(MAX_RECORD_BYTES + 1)
    if len(data) > MAX_RECORD_BYTES:
        raise HandoffError("handoff exceeds byte limit")
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise HandoffError("duplicate JSON field: " + key)
            result[key] = value
        return result
    try:
        record = json.loads(data.decode("utf-8"), object_pairs_hook=unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(HandoffError("non-finite JSON value")) )
    except (UnicodeDecodeError, ValueError) as exc:
        raise HandoffError("invalid handoff JSON") from exc
    if not isinstance(record, dict) or set(record) != {
        "schema_version", "created_at", "task", "next_action", "blockers",
        "evidence_refs", "repository", "payload_sha256",
    } or type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA_VERSION:
        raise HandoffError("unsupported handoff schema")
    expected = record["payload_sha256"]
    if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
        raise HandoffError("invalid handoff digest")
    body = {key: value for key, value in record.items() if key != "payload_sha256"}
    if digest(canonical(body)) != expected:
        raise HandoffError("handoff digest mismatch")
    check_text(record["task"], "task", required=True)
    check_text(record["next_action"], "next_action", required=True)
    for field in ("blockers", "evidence_refs"):
        if not isinstance(record[field], list) or len(record[field]) > 16:
            raise HandoffError("invalid " + field)
        for value in record[field]:
            check_text(value, field, required=True)
    if not isinstance(record["created_at"], str) or not isinstance(record["repository"], dict):
        raise HandoffError("invalid record metadata")
    repo = record["repository"]
    if set(repo) != {"checkout_root", "head", "branch", "changes",
                     "observed_files", "coverage"}:
        raise HandoffError("invalid repository snapshot schema")
    if (not isinstance(repo["checkout_root"], str) or
        not isinstance(repo["head"], str) or
        not re.fullmatch(r"[a-f0-9]{40,64}", repo["head"])):
        raise HandoffError("invalid repository identity")
    if repo["branch"] is not None and not isinstance(repo["branch"], str):
        raise HandoffError("invalid branch")
    if not isinstance(repo["changes"], list) or not isinstance(repo["observed_files"], list):
        raise HandoffError("invalid observed paths")
    if len(repo["changes"]) > MAX_CHANGED_PATHS or len(repo["observed_files"]) > MAX_CHANGED_PATHS:
        raise HandoffError("too many observed paths")
    if repo["coverage"] != "tracked_changes_and_visible_untracked_plus_explicit_paths":
        raise HandoffError("unsupported coverage")
    for item in repo["changes"]:
        if not isinstance(item, dict) or not {"path", "code"} <= set(item) or (
            set(item) - {"path", "code", "previous_path"}
        ):
            raise HandoffError("invalid changed path")
        relative_path(item["path"])
        if not isinstance(item["code"], str) or len(item["code"]) != 2:
            raise HandoffError("invalid change code")
        if "previous_path" in item:
            relative_path(item["previous_path"])
    for item in repo["observed_files"]:
        if not isinstance(item, dict) or set(item) != {"path", "kind", "sha256"}:
            raise HandoffError("invalid observed file")
        relative_path(item["path"])
        if item["kind"] not in ("regular", "absent", "symlink"):
            raise HandoffError("invalid file kind")
        if not isinstance(item["sha256"], str) or (
            item["kind"] == "absent" and item["sha256"] != ""
        ) or (item["kind"] != "absent" and not SHA_RE.fullmatch(item["sha256"])):
            raise HandoffError("invalid observed digest")
    return record


def capture(args: argparse.Namespace, root: Path) -> int:
    task = check_text(args.task, "task", required=True)
    next_action = check_text(args.next_action, "next_action", required=True)
    blockers = [check_text(value, "blocker", required=True) for value in args.blocker]
    evidence = [check_text(value, "evidence", required=True) for value in args.evidence]
    if max(len(blockers), len(evidence)) > 16:
        raise HandoffError("too many blockers or evidence references")
    requested = [relative_path(value) for value in args.path]
    if len(requested) > MAX_CHANGED_PATHS:
        raise HandoffError("too many explicit paths")
    first = snapshot(root, requested)
    if first != snapshot(root, requested):
        raise HandoffError("repository changed during capture; retry")
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "task": task,
        "next_action": next_action,
        "blockers": blockers,
        "evidence_refs": evidence,
        "repository": first,
    }
    record["payload_sha256"] = digest(canonical(record))
    data = canonical(record)
    if len(data) > MAX_RECORD_BYTES:
        raise HandoffError("handoff record too large")
    if args.output:
        destination = safe_path(args.output)
        if destination == root or root in destination.parents:
            raise HandoffError("save handoff outside the target worktree to avoid self-induced drift")
        write_new(args.output, data)
        print(json.dumps({"written": str(safe_path(args.output)),
                          "payload_sha256": record["payload_sha256"],
                          "verification": "not_evaluated"}))
    else:
        sys.stdout.buffer.write(data)
    return 0


def resume(args: argparse.Namespace, root: Path) -> int:
    record = read_record(args.input)
    old = record["repository"]
    requested = [value["path"] for value in old["observed_files"]]
    current = snapshot(root, requested)
    reasons = []
    for key, reason in (
        ("checkout_root", "CHECKOUT_CHANGED"),
        ("branch", "BRANCH_CHANGED"),
        ("head", "HEAD_CHANGED"),
        ("changes", "WORKTREE_STATUS_CHANGED"),
        ("observed_files", "OBSERVED_BYTES_CHANGED"),
    ):
        if old[key] != current[key]:
            reasons.append(reason)
    stale = bool(reasons)
    result = {
        "schema_version": SCHEMA_VERSION,
        "handoff_sha256": record["payload_sha256"],
        "task": record["task"],
        "next_action": record["next_action"],
        "blockers": record["blockers"],
        "evidence_refs": record["evidence_refs"],
        "state": "stale" if stale else "matching_snapshot",
        "reasons": reasons,
        "verification": "stale" if stale else "unknown",
        "source_integrity": "digest_checked_not_authenticated",
        "coverage": current["coverage"],
        "current_head": current["head"],
        "current_branch": current["branch"],
        "read_only": True,
    }
    if args.receipt:
        # A command receipt proves only its own explicitly scoped check.
        # This does not authorize the whole task or override a stale handoff.
        import verification_receipt
        try:
            result["verification_receipt"] = verification_receipt.check_receipt(
                root, args.receipt
            )
        except verification_receipt.handoff.HandoffError as exc:
            # Running this file as __main__ creates a distinct class identity
            # from the imported session_handoff module used by the receipt.
            raise HandoffError(str(exc)) from exc
    sys.stdout.buffer.write(canonical(result))
    return 1 if stale or (
        args.receipt and result["verification_receipt"]["outcome"] != "passed"
    ) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="exact Git worktree root")
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("capture", help="read-only JSON stdout unless --output is set")
    make.add_argument("--task", required=True, help="current engineering task")
    make.add_argument("--next-action", required=True, help="next concrete step")
    make.add_argument("--path", action="append", default=[], help="extra file to observe")
    make.add_argument("--evidence", action="append", default=[], help="unverified evidence pointer")
    make.add_argument("--blocker", action="append", default=[], help="open blocker")
    make.add_argument("--output", help="explicit new local JSON file (never overwritten)")
    load = commands.add_parser("resume", help="read-only revalidation of local checkout")
    load.add_argument("--input", required=True, help="existing Handoff JSON path")
    load.add_argument("--receipt", help="optional revision-bound command evidence")
    args = parser.parse_args()
    try:
        root = repository_root(args.repo)
        return capture(args, root) if args.command == "capture" else resume(args, root)
    except (HandoffError, OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        print("session-handoff: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
