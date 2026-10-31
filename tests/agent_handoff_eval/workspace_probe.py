#!/usr/bin/env python3
"""Fixed-schema, read-only Work workspace isolation probe (Python 3.10+).

All arms invoke this exact script; no per-agent generated validators or aliases.
Exit 0=matching workspace, 1=environment_drift, 2=checker_error.
This is an experiment fixture, not a product Handoff/Receipt authority.
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

FIELDS = frozenset({
    "root", "head", "index", "status", "files",
    "index_sha256", "status_sha256",
})
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40,64}\Z")
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_WORKTREE_FILES = 20_000
MAX_SINGLE_FILE_BYTES = 64 * 1024 * 1024

class CheckerError(RuntimeError):
    """Invalid schema, unsafe input or failed observation; not file drift."""


def hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(root: Path, *args: str) -> bytes:
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=30, env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckerError("unable to observe git " + args[0]) from exc
    if result.returncode:
        raise CheckerError("git " + args[0] + " failed (exit " +
                           str(result.returncode) + ")")
    return result.stdout


def repository_root(value: str) -> Path:
    raw = Path(value)
    if not raw.is_absolute() or raw.is_symlink():
        raise CheckerError("--repo must be an absolute non-symlink checkout root")
    try:
        root = raw.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CheckerError("missing or invalid repository root") from exc
    if not root.is_dir() or root != raw:
        raise CheckerError("noncanonical repository root")
    actual = git(root, "rev-parse", "--show-toplevel")
    try:
        reported = Path(actual.decode("utf-8").strip()).resolve(strict=True)
    except (UnicodeError, OSError) as exc:
        raise CheckerError("unrepresentable Git worktree root") from exc
    if reported != root:
        raise CheckerError("--repo must name the exact Git worktree root")
    return root


def relative_path(value: str) -> str:
    if (not isinstance(value, str) or not value or
        "\x00" in value or "\\" in value):
        raise CheckerError("invalid manifest path")
    candidate = PurePosixPath(value)
    if (candidate.is_absolute() or candidate.as_posix() != value or
        any(p in ("", ".", "..") for p in value.split("/")) or
        candidate.as_posix() == "."):
        raise CheckerError("noncanonical manifest path")
    if ".git" in candidate.parts:
        raise CheckerError("manifest cannot include Git internals")
    return value


def file_inventory(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for parent, dirs, names in os.walk(root, topdown=True, followlinks=False):
        location = Path(parent)
        dirs.sort()
        names.sort()
        for dirname in list(dirs):
            child = location / dirname
            if location == root and dirname == ".git":
                dirs.remove(dirname)
            elif child.is_symlink():
                raise CheckerError("symlink directory is not supported: " +
                                   child.relative_to(root).as_posix())
        for name in names:
            path = location / name
            relative = relative_path(path.relative_to(root).as_posix())
            if path.is_symlink():
                raise CheckerError("symlink source is not supported: " + relative)
            try:
                meta = path.lstat()
                if not stat.S_ISREG(meta.st_mode):
                    raise CheckerError("non-regular source: " + relative)
                if meta.st_size > MAX_SINGLE_FILE_BYTES:
                    raise CheckerError("source too large: " + relative)
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                with os.fdopen(os.open(path, flags), "rb") as handle:
                    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                        raise CheckerError("source changed type: " + relative)
                    digest = hashlib.sha256()
                    count = 0
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        count += len(block)
                        if count > MAX_SINGLE_FILE_BYTES:
                            raise CheckerError("source grew too large: " + relative)
                        digest.update(block)
            except (OSError, RuntimeError) as exc:
                if isinstance(exc, CheckerError):
                    raise
                raise CheckerError("cannot read source: " + relative) from exc
            files[relative] = digest.hexdigest()
            if len(files) > MAX_WORKTREE_FILES:
                raise CheckerError("too many worktree source files")
    return dict(sorted(files.items()))


def observation(root: Path) -> dict[str, object]:
    try:
        head = git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
        index_raw = git(root, "ls-files", "--stage", "-z")
        status_raw = git(root, "status", "--porcelain=v1", "-z",
                         "--untracked-files=all")
        # surrogateescape round-trips Git byte paths without removing NUL
        index_text = index_raw.decode("utf-8", errors="surrogateescape")
        status_text = status_raw.decode("utf-8", errors="surrogateescape")
    except UnicodeError as exc:
        raise CheckerError("invalid Git HEAD encoding") from exc
    if not GIT_SHA.fullmatch(head):
        raise CheckerError("malformed Git HEAD")
    before_files = file_inventory(root)
    if before_files != file_inventory(root):
        raise CheckerError("worktree file contents changed during observation")
    # Catch observable mutation during the audit rather than claiming a
    # successful comparison against a mixed-time snapshot.
    if (index_raw != git(root, "ls-files", "--stage", "-z") or
        status_raw != git(root, "status", "--porcelain=v1", "-z",
                         "--untracked-files=all") or
        head != git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()):
        raise CheckerError("worktree changed during observation; retry separately")
    return {
        "root": str(root),
        "head": head,
        "index": index_text,
        "status": status_text,
        "files": before_files,
        "index_sha256": hash_bytes(index_raw),
        "status_sha256": hash_bytes(status_raw),
    }


def unique_json(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise CheckerError("duplicate JSON key: " + key)
        result[key] = value
    return result


def manifest_path(value: str, root: Path, *, output: bool) -> Path:
    raw = Path(value)
    if not raw.is_absolute() or raw.is_symlink():
        raise CheckerError("manifest path must be absolute and non-symlink")
    try:
        actual_parent = raw.parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CheckerError("manifest parent path is unavailable") from exc
    actual = actual_parent / raw.name
    if actual == root or root in actual.parents:
        raise CheckerError("manifest must be outside the checkout")
    if actual.name in (".", ".."):
        raise CheckerError("invalid manifest filename")
    return actual


def load_manifest(value: str, root: Path) -> dict:
    raw = manifest_path(value, root, output=False)
    try:
        if not raw.is_file() or raw.stat().st_size > MAX_MANIFEST_BYTES:
            raise CheckerError("missing or oversized expected manifest")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(raw, flags), "rb") as stream:
            data = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(data) > MAX_MANIFEST_BYTES:
            raise CheckerError("expected manifest is oversized")
        manifest = json.loads(
            data.decode("utf-8"), object_pairs_hook=unique_json,
            parse_constant=lambda _: (_ for _ in ()).throw(
                CheckerError("nonfinite JSON value")),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise CheckerError("cannot parse expected manifest") from exc

    if not isinstance(manifest, dict) or set(manifest) != FIELDS:
        raise CheckerError("expected manifest schema must have exactly: " +
                           ", ".join(sorted(FIELDS)))
    for key in ("root", "head", "index", "status",
                "index_sha256", "status_sha256"):
        if not isinstance(manifest[key], str):
            raise CheckerError("manifest field must be a string: " + key)
    if not GIT_SHA.fullmatch(manifest["head"]):
        raise CheckerError("invalid expected HEAD")
    for key in ("index_sha256", "status_sha256"):
        if not HEX64.fullmatch(manifest[key]):
            raise CheckerError("invalid digest field: " + key)
    for key, digest_key in (("index", "index_sha256"),
                            ("status", "status_sha256")):
        if hash_bytes(manifest[key].encode("utf-8", "surrogateescape")) != manifest[digest_key]:
            raise CheckerError("inconsistent expected " + key + " digest")
    if manifest["root"] != str(root):
        raise CheckerError("expected manifest targets a different checkout")
    files = manifest["files"]
    if not isinstance(files, dict) or len(files) > MAX_WORKTREE_FILES:
        raise CheckerError("invalid files inventory")
    for name, value in files.items():
        relative_path(name)
        if not isinstance(value, str) or not HEX64.fullmatch(value):
            raise CheckerError("invalid file digest in manifest: " + name)
    return manifest


def compare(expected: dict, actual: dict) -> dict:
    checks = {}
    for key in ("root", "head", "index", "status"):
        checks[key] = expected[key] == actual[key]
    # Compare raw bytes via lossless surrogateescape strings AND digests;
    # digest equality alone does not replace exact comparison.
    checks["index_sha256"] = expected["index_sha256"] == actual["index_sha256"]
    checks["status_sha256"] = expected["status_sha256"] == actual["status_sha256"]
    expected_files, actual_files = expected["files"], actual["files"]
    mismatched = sorted(
        name for name in expected_files.keys() | actual_files.keys()
        if expected_files.get(name) != actual_files.get(name)
    )
    checks["files"] = not mismatched
    mismatched_fields = [key for key, ok in checks.items() if not ok]
    return {
        "status": "matching" if not mismatched_fields else "environment_drift",
        "checks": checks,
        "mismatched_fields": mismatched_fields,
        "mismatched_paths": mismatched,
    }


def new_manifest(path_text: str, root: Path, manifest: dict) -> None:
    path = manifest_path(path_text, root, output=True)
    payload = (json.dumps(manifest, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    if len(payload) > MAX_MANIFEST_BYTES:
        raise CheckerError("expected manifest exceeds limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        with os.fdopen(os.open(path, flags, 0o600), "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CheckerError("cannot create new expected manifest") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="absolute checkout root")
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="save one expected manifest outside checkout")
    capture.add_argument("--output", required=True, help="new absolute manifest file; never overwritten")
    check = commands.add_parser("check", help="read-only fixed-schema worktree comparison")
    check.add_argument("--expected", required=True, help="existing absolute expected manifest")
    args = parser.parse_args()
    result: dict[str, object] = {
        "checker": "workspace_probe/v1",
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "action": args.command,
        "status": "checker_error",
        "read_only": args.command == "check",
    }
    code = 2
    try:
        root = repository_root(args.repo)
        if args.command == "capture":
            captured = observation(root)
            new_manifest(args.output, root, captured)
            result.update(status="captured", manifest=args.output,
                          head=captured["head"],
                          index_sha256=captured["index_sha256"],
                          status_sha256=captured["status_sha256"],
                          file_count=len(captured["files"]))
            code = 0
        else:
            expected = load_manifest(args.expected, root)
            actual = observation(root)
            result.update(compare(expected, actual))
            result.update(head=actual["head"],
                          index_sha256=actual["index_sha256"],
                          status_sha256=actual["status_sha256"],
                          file_count=len(actual["files"]))
            code = 0 if result["status"] == "matching" else 1
    except (CheckerError, OSError, UnicodeError, RuntimeError) as exc:
        result.update(status="checker_error", error=str(exc))
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
