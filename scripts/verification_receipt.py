#!/usr/bin/env python3
"""Opt-in revision-bound verification of an explicitly executed local command."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import session_handoff as handoff

SCHEMA = 1
MAX_RECORD = 256 * 1024
MAX_LOG = 8 * 1024 * 1024
SPEC_FILES = ("docs/.engineering/harness.json", "docs/.engineering/specs.json",
              "docs/.engineering/specs.lock.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40,64}$")
BASE_REF = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]{0,127}$")


def fail(reason: str) -> None:
    raise handoff.HandoffError(reason)


def canonical(obj: object) -> bytes:
    return handoff.canonical(obj)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_args(argv: list[str]) -> list[str]:
    if not isinstance(argv, list):
        fail("command argv must be an array")
    result = argv[1:] if argv and argv[0] == "--" else argv
    if not 1 <= len(result) <= 64:
        fail("explicit command argv is required (maximum 64 elements)")
    if any(not isinstance(s, str) or not s or "\x00" in s or
           len(s.encode("utf-8")) > 4096 for s in result):
        fail("invalid command argv")
    return result


def base_revision(root: Path, ref: str | None) -> str | None:
    if ref is None:
        return None
    if not BASE_REF.fullmatch(ref) or ".." in ref or ref.endswith((".", "/")):
        fail("invalid base ref")
    value = handoff.git(root, "rev-parse", "--verify", ref + "^{commit}").decode("ascii").strip()
    if not GIT_SHA.fullmatch(value):
        fail("invalid base commit")
    return value


def observe(root: Path, inputs: list[str], base: str | None) -> dict:
    data = handoff.snapshot(root, sorted(set(inputs) | set(SPEC_FILES)))
    data["index_sha256"] = sha(handoff.git(root, "ls-files", "--stage", "-z"))
    data["base_sha"] = base
    return data


def drift(old: dict, now: dict) -> list[str]:
    return [reason for key, reason in (
        ("checkout_root", "CHECKOUT_CHANGED"), ("head", "HEAD_CHANGED"),
        ("branch", "BRANCH_CHANGED"), ("base_sha", "BASE_CHANGED"),
        ("index_sha256", "STAGED_INDEX_CHANGED"),
        ("changes", "WORKTREE_STATUS_CHANGED"),
        ("observed_files", "OBSERVED_BYTES_CHANGED")
    ) if old[key] != now[key]]


def output_path(raw: str, root: Path) -> str:
    out = handoff.safe_path(raw)
    if out == root or root in out.parents:
        fail("receipt output must be outside the observed worktree")
    if out.exists() or out.is_symlink():
        fail("receipt exists; will not overwrite")
    return str(out)


def hash_stream(handle) -> dict:
    handle.seek(0)
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_LOG:
            fail("command output exceeds 8 MiB receipt limit")
        digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def execute(args: argparse.Namespace, root: Path) -> int:
    argv = validate_args(args.argv)
    if not 1 <= args.timeout <= 900:
        fail("timeout must be 1..900 seconds")
    paths = [handoff.relative_path(p) for p in args.path]
    if len(paths) > handoff.MAX_CHANGED_PATHS:
        fail("too many input paths")
    out = output_path(args.output, root) if args.output else None
    base = base_revision(root, args.base_ref)
    before = observe(root, paths, base)
    if observe(root, paths, base) != before:
        fail("repository changed during precheck")
    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            proc = subprocess.run(argv, cwd=root, stdin=subprocess.DEVNULL,
                                  stdout=stdout, stderr=stderr, timeout=args.timeout)
            exit_code, error = proc.returncode, None
        except subprocess.TimeoutExpired:
            exit_code, error = None, "TIMED_OUT"
        except FileNotFoundError:
            exit_code, error = None, "COMMAND_NOT_FOUND"
        streams = {"stdout": hash_stream(stdout), "stderr": hash_stream(stderr)}
    after = observe(root, paths, base)
    changed = drift(before, after)
    outcome = ("unknown" if changed or error else "passed" if exit_code == 0 else "failed")
    record = {
        "schema_version": SCHEMA,
        "captured_at": captured_at,
        "command": argv,
        "environment": {"python": sys.version.split()[0], "platform": sys.platform},
        "result": {"outcome": outcome, "exit_code": exit_code,
                   "execution_error": error, "changed_during_execution": changed,
                   "output": streams},
        "revision": after,
        "coverage": "head_index_visible_changes_explicit_paths;ignored_and_external_unknown",
    }
    record["payload_sha256"] = sha(canonical(record))
    data = canonical(record)
    if len(data) > MAX_RECORD:
        fail("receipt too large")
    if out:
        handoff.write_new(out, data)
    sys.stdout.buffer.write(canonical({
        "outcome": outcome, "exit_code": exit_code,
        "reason_codes": changed + ([error] if error else []),
        "receipt_sha256": record["payload_sha256"], "written": out,
        "current_head": after["head"], "scope": record["coverage"],
        "source_integrity": "digest_checked_not_authenticated",
    }))
    return 0 if outcome == "passed" else 1


def schema(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        fail("invalid " + label + " schema")
    return value


def read(raw: str) -> dict:
    path = handoff.safe_path(raw)
    if not path.is_file() or path.stat().st_size > MAX_RECORD:
        fail("missing, unsafe or oversized receipt")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        data = handle.read(MAX_RECORD + 1)
    if len(data) > MAX_RECORD:
        fail("receipt too large")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                fail("duplicate receipt JSON field")
            result[key] = value
        return result

    try:
        record = json.loads(data.decode("utf-8"), object_pairs_hook=unique,
                            parse_constant=lambda _: fail("nonfinite JSON"))
    except (UnicodeError, ValueError) as exc:
        raise handoff.HandoffError("invalid receipt JSON") from exc
    schema(record, {"schema_version", "captured_at", "command", "environment",
                    "result", "revision", "coverage", "payload_sha256"}, "receipt")
    if type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA:
        fail("unsupported receipt version")
    token = record["payload_sha256"]
    if not isinstance(token, str) or not SHA256.fullmatch(token):
        fail("invalid receipt digest")
    if sha(canonical({k: v for k, v in record.items() if k != "payload_sha256"})) != token:
        fail("receipt has changed")
    if not isinstance(record["captured_at"], str) or not record["captured_at"].endswith("Z"):
        fail("invalid timestamp")
    validate_args(record["command"])
    env = schema(record["environment"], {"python", "platform"}, "environment")
    if not all(isinstance(v, str) and len(v) <= 128 for v in env.values()):
        fail("invalid environment")
    result = schema(record["result"], {"outcome", "exit_code", "execution_error",
                                       "changed_during_execution", "output"}, "result")
    if result["outcome"] not in ("passed", "failed", "unknown"):
        fail("invalid outcome")
    rc = result["exit_code"]
    if rc is not None and (type(rc) is not int or not -255 <= rc <= 255):
        fail("invalid process status")
    if result["execution_error"] not in (None, "TIMED_OUT", "COMMAND_NOT_FOUND"):
        fail("invalid execution error")
    reasons = result["changed_during_execution"]
    if not isinstance(reasons, list) or any(not isinstance(x, str) for x in reasons):
        fail("invalid drift evidence")
    streams = schema(result["output"], {"stdout", "stderr"}, "output")
    for value in streams.values():
        schema(value, {"sha256", "bytes"}, "output stream")
        if not isinstance(value["sha256"], str) or not SHA256.fullmatch(value["sha256"]):
            fail("invalid stream digest")
        if type(value["bytes"]) is not int or not 0 <= value["bytes"] <= MAX_LOG:
            fail("invalid stream size")
    if (result["outcome"] == "passed" and (rc != 0 or reasons or result["execution_error"])) or (
        result["outcome"] == "failed" and (rc is None or rc == 0 or reasons or result["execution_error"])
    ):
        fail("receipt claims inconsistent result")
    rev = schema(record["revision"],
                 {"checkout_root", "head", "branch", "changes", "observed_files",
                  "coverage", "index_sha256", "base_sha"}, "revision")
    if not isinstance(rev["checkout_root"], str) or not isinstance(rev["head"], str) or (
        not GIT_SHA.fullmatch(rev["head"])
    ):
        fail("invalid Git identity")
    if rev["base_sha"] is not None and (
        not isinstance(rev["base_sha"], str) or not GIT_SHA.fullmatch(rev["base_sha"])
    ):
        fail("invalid base commit")
    if rev["branch"] is not None and not isinstance(rev["branch"], str):
        fail("invalid branch")
    if not isinstance(rev["index_sha256"], str) or not SHA256.fullmatch(rev["index_sha256"]):
        fail("invalid staged index")
    if rev["coverage"] != "tracked_changes_and_visible_untracked_plus_explicit_paths":
        fail("unsupported snapshot coverage")
    if not isinstance(rev["changes"], list) or not isinstance(rev["observed_files"], list) or (
        len(rev["changes"]) > handoff.MAX_CHANGED_PATHS or
        len(rev["observed_files"]) > handoff.MAX_CHANGED_PATHS
    ):
        fail("invalid path observations")
    for row in rev["changes"]:
        if not isinstance(row, dict) or not {"path", "code"} <= set(row) or (
            set(row) - {"path", "code", "previous_path"}
        ):
            fail("invalid change row")
        handoff.relative_path(row["path"])
        if not isinstance(row["code"], str) or len(row["code"]) != 2:
            fail("invalid change code")
        if "previous_path" in row:
            handoff.relative_path(row["previous_path"])
    for row in rev["observed_files"]:
        schema(row, {"path", "kind", "sha256"}, "file")
        handoff.relative_path(row["path"])
        if row["kind"] not in ("regular", "absent", "symlink") or not isinstance(row["sha256"], str):
            fail("invalid file kind or digest")
        if (row["kind"] == "absent" and row["sha256"] != "") or (
            row["kind"] != "absent" and not SHA256.fullmatch(row["sha256"])
        ):
            fail("invalid file digest")
    if record["coverage"] != "head_index_visible_changes_explicit_paths;ignored_and_external_unknown":
        fail("invalid receipt coverage")
    return record


def check_receipt(root: Path, raw: str) -> dict:
    record = read(raw)
    old = record["revision"]
    current = observe(root, [x["path"] for x in old["observed_files"]], old["base_sha"])
    changed = drift(old, current)
    result = record["result"]
    return {
        "outcome": "stale" if changed else result["outcome"],
        "original_outcome": result["outcome"],
        "reasons": changed or result["changed_during_execution"] or (
            [result["execution_error"]] if result["execution_error"] else []
        ),
        "command": record["command"], "exit_code": result["exit_code"],
        "receipt_sha256": record["payload_sha256"],
        "source_integrity": "digest_checked_not_authenticated",
        "scope": record["coverage"], "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="execute an explicit command and bind outcome to code")
    run.add_argument("--path", action="append", default=[], help="extra source input")
    run.add_argument("--base-ref", help="optional Git base commit ref")
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--output", help="optional new private receipt outside worktree")
    run.add_argument("argv", nargs=argparse.REMAINDER, help="command argv after --")
    check = commands.add_parser("check", help="compare receipt to current checkout (read-only)")
    check.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = handoff.repository_root(args.repo)
        if args.action == "run":
            return execute(args, root)
        result = check_receipt(root, args.input)
        sys.stdout.buffer.write(canonical(result))
        return 0 if result["outcome"] == "passed" else 1
    except (handoff.HandoffError, OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        print("verification-receipt: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
