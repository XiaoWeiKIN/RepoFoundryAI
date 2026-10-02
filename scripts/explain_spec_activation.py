#!/usr/bin/env python3
"""Inspect Spec routing in a local, read-only HTML view. No activation receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "assets/core/engineering-specs/spec_router.py"
PAGE = ROOT / "assets/explain/spec-activation.html"
MAX_REQUEST_BYTES = 32 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_BUDGET = 32 * 1024


class ExplainError(ValueError):
    """An invalid request or a source that cannot be verified."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def load_router() -> ModuleType:
    # Import only this distribution's engine, never executable code in the target.
    name = "_repofoundry_explanation_router"
    spec = importlib.util.spec_from_file_location(name, ENGINE)
    if spec is None or spec.loader is None:
        raise ExplainError("The bundled Spec Router is missing.")
    source_sha256 = digest(ENGINE.read_bytes())
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    if digest(ENGINE.read_bytes()) != source_sha256:
        raise ExplainError("Bundled Router changed while loading. Restart the view.")
    module._explain_source_sha256 = source_sha256
    if module.PROTOCOL_VERSION != 2 or module.ROUTER_VERSION != 5:
        raise ExplainError("This prototype requires bundled Router 5 / protocol 2.")
    return module


def string_list(value: object, label: str, limit: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > limit:
        raise ExplainError(f"{label}: expected an array of at most {limit} strings.")
    if any(not isinstance(item, str) or not item.strip() or len(item) > 512
           for item in value):
        raise ExplainError(f"{label}: expected nonempty strings of at most 512 characters.")
    return tuple(dict.fromkeys(value))


def metadata_digests(root: Path, router: ModuleType) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for relative in (router.MANIFEST_PATH, router.LOCK_PATH, router.REQUIREMENT_INDEX_PATH):
        path = root / relative
        if relative == router.REQUIREMENT_INDEX_PATH and not path.exists() and not path.is_symlink():
            result[relative] = None  # Router's explicit legacy whole-Spec path.
            continue
        path = router._resolve_regular(root, relative, "EXPLAIN_METADATA_INVALID")
        result[relative] = digest(router._read_bytes(path, "EXPLAIN_METADATA_INVALID", router.MAX_JSON_BYTES))
    return result


def git_identity(root: Path) -> dict[str, object]:
    # Avoid optional index writes, fsmonitor commands, and submodule traversal.
    prefix = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false"]
    try:
        head = subprocess.run(prefix + ["rev-parse", "--verify", "HEAD"], cwd=root,
                              capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        status = subprocess.run(prefix + ["status", "--porcelain=v1", "-z", "--untracked-files=normal", "--ignore-submodules=all"],
                                cwd=root, capture_output=True, timeout=10, check=True)
        return {"head": head, "dirty": bool(status.stdout)}
    except (OSError, subprocess.SubprocessError):
        return {"head": None, "dirty": None}


def build_preview(root: Path, router: ModuleType, request: object) -> dict[str, object]:
    """Use canonical read functions, without begin/activate/audit or runtime state."""
    if not isinstance(request, dict) or set(request) - {"paths", "requirements", "whole_specs", "budget_bytes"}:
        raise ExplainError("Expected paths, requirements, whole_specs, and budget_bytes only.")
    paths = string_list(request.get("paths", []), "paths", 8)
    if not paths:
        raise ExplainError("Provide at least one exact planned file path.")
    # Path globs are deliberately excluded: this view does not expand a workspace.
    if any(any(char in path for char in "*?[]") for path in paths):
        raise ExplainError("Use exact planned file paths, not glob expressions.")
    paths = tuple(router._normalize_planned_path(root, path) for path in paths)
    direct = string_list(request.get("requirements", []), "requirements", 128)
    whole_requested = string_list(request.get("whole_specs", []), "whole_specs", 16)
    budget = request.get("budget_bytes", DEFAULT_BUDGET)
    if type(budget) is not int or not 1 <= budget <= DEFAULT_BUDGET:
        raise ExplainError(f"budget_bytes: expected 1..{DEFAULT_BUDGET}. This view cannot raise the Router budget.")

    if digest(ENGINE.read_bytes()) != router._explain_source_sha256:
        raise ExplainError("Bundled Router changed. Restart the view before previewing.")
    before = metadata_digests(root, router)
    state = router.load_state(root)
    index = state.requirement_index
    candidates = router.candidate_entries(state, paths)
    candidate_ids = {entry.key for entry in candidates}
    for identifier in direct:
        record = index.by_requirement.get(identifier)
        if record is None:
            raise ExplainError(f"Unknown Requirement: {identifier}")
        if record.spec_id not in candidate_ids:
            raise ExplainError(f"Requirement is not a path candidate: {identifier}")
    for identifier in whole_requested:
        if identifier not in candidate_ids or index.by_spec[identifier].mode != "whole-spec":
            raise ExplainError(f"Not a candidate legacy whole-Spec entry: {identifier}")
    resolved = router.requirement_dependency_closure(index, direct)
    whole = tuple(entry.key for entry in router.dependency_closure(state, whole_requested))
    if {record.spec_id for record in resolved}.intersection(whole):
        raise ExplainError("Requirement and whole-Spec selections overlap. Remove the redundant selection.")

    capsule = None
    if direct or whole:
        text, mode = router.compile_context_capsule(root, state, direct, resolved, whole, (), budget)
        raw = text.encode("utf-8")
        capsule = {"text": text, "mode": mode, "bytes": len(raw), "sha256": digest(raw), "budget_bytes": budget}

    specs = []
    for entry in candidates:
        payload = router.entry_payload(root, entry, index)
        payload["cards"] = [router._card_payload(record) for record in index.by_spec[entry.key].requirements]
        specs.append(payload)
    sources = []
    for indexed in index.specs:
        # Reverify after compilation too; no stale source is labeled current.
        raw = router._verified_spec_content(root, indexed)
        sources.append({"path": indexed.path, "sha256": digest(raw), "bytes": len(raw)})
    if metadata_digests(root, router) != before:
        raise ExplainError("Source metadata changed during the preview. Refresh and review the new selection.")
    resolved_payload = router._resolved_payload(resolved, direct)
    for record in resolved_payload:
        record["path"] = index.by_spec[record["spec_id"]].path
    source_identity = {"metadata": before, "specs": sources}
    result = {
        "kind": "read-only-preview", "authority": "none", "receipt_created": False,
        "paths": list(paths), "direct": list(direct), "whole_specs": list(whole),
        "specs": specs, "resolved": resolved_payload,
        "edges": router._dependency_edges(resolved), "capsule": capsule,
        "provenance": {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "git": git_identity(root), "source_set_sha256": digest(json_bytes(source_identity)),
            "sources": source_identity,
            "catalog": {"id": state.catalog_id, "version": state.catalog_version,
                        "sha256": state.catalog_digest, "revision": state.revision},
            "engine": {"router_version": router.ROUTER_VERSION, "protocol_version": router.PROTOCOL_VERSION,
                       "sha256": router._explain_source_sha256},
        },
    }
    if len(json_bytes(result)) > MAX_RESPONSE_BYTES:
        raise ExplainError("Preview exceeds the response limit. Narrow the planned paths; source text was not truncated.")
    return result


def page_bytes() -> tuple[bytes, str]:
    page = PAGE.read_bytes()
    scripts = re.findall(rb"<script>(.*?)</script>", page, re.DOTALL)
    if len(scripts) != 1:
        raise ExplainError("The explanation page must contain one bundled script.")
    import base64
    script_hash = base64.b64encode(hashlib.sha256(scripts[0]).digest()).decode("ascii")
    csp = ("default-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
           "form-action 'none'; connect-src 'self'; style-src 'unsafe-inline'; "
           f"script-src 'sha256-{script_hash}'")
    return page, csp


class PreviewServer(HTTPServer):
    """Single-process local development server, not a hosted application."""

    def __init__(self, root: Path, router: ModuleType, port: int = 0):
        self.root = root
        self.router = router
        self.token = secrets.token_urlsafe(32)
        self.page, self.csp = page_bytes()
        super().__init__(("127.0.0.1", port), PreviewHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


class PreviewHandler(BaseHTTPRequestHandler):
    server: PreviewServer

    def log_message(self, format: str, *args: object) -> None:
        pass  # Do not log source paths, capabilities, or document contents.

    def respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", self.server.csp)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def error(self, status: int, message: str) -> None:
        self.respond(status, json_bytes({"error": message}), "application/json; charset=utf-8")

    def local_host(self) -> bool:
        return self.headers.get_all("Host", []) == [urlsplit(self.server.origin).netloc]

    def do_GET(self) -> None:
        if not self.local_host():
            self.error(403, "Untrusted Host.")
        elif self.path != "/":
            self.error(404, "Not found. This server does not serve repository files.")
        else:
            self.respond(200, self.server.page, "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if (not self.local_host()
                or self.headers.get_all("Origin", []) != [self.server.origin]
                or len(self.headers.get_all("X-Explain-Token", [])) != 1
                or not secrets.compare_digest(self.headers.get("X-Explain-Token", "").encode("utf-8"), self.server.token.encode("ascii"))):
            self.error(403, "Use the local URL printed by the CLI.")
            return
        if self.path != "/api/preview":
            self.error(404, "Not found.")
            return
        if (self.headers.get_all("Content-Type", []) != ["application/json"]
                or self.headers.get("Transfer-Encoding") is not None
                or len(self.headers.get_all("Content-Length", [])) != 1):
            self.error(400, "Expected bounded application/json with Content-Length.")
            return
        try:
            length = int(self.headers["Content-Length"])
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ExplainError("Request exceeds the 32 KiB limit or is empty.")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ExplainError("Incomplete request body.")
            request = json.loads(raw.decode("utf-8"))
            result = build_preview(self.server.root, self.server.router, request)
        except (ExplainError, self.server.router.RouterError, UnicodeError, ValueError, RecursionError) as exc:
            self.error(400, str(exc))
            return
        except (OSError, subprocess.SubprocessError):
            self.error(400, "Local source is unavailable. Check the terminal and local Spec state.")
            return
        self.respond(200, json_bytes(result), "application/json; charset=utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="A repository with installed, locked Engineering Specs")
    parser.add_argument("--port", type=int, default=0, help="Loopback port; 0 selects an available port")
    parser.add_argument("--json", action="store_true", help="Print one read-only preview instead of starting HTML")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--requirement", action="append", default=[])
    parser.add_argument("--whole-spec", action="append", default=[])
    parser.add_argument("--budget-bytes", type=int, default=DEFAULT_BUDGET)
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.port <= 65535:
            raise ExplainError("--port must be between 0 and 65535.")
        if not args.json and (args.path or args.requirement or args.whole_spec or args.budget_bytes != DEFAULT_BUDGET):
            raise ExplainError("CLI selections require --json. In HTML mode, select paths in the page.")
        router = load_router()
        root = router.repository_root(args.repo)
        router.load_state(root)  # Fail before exposing an unusable view; never bootstrap.
        if args.json:
            result = build_preview(root, router, {"paths": args.path, "requirements": args.requirement,
                                                  "whole_specs": args.whole_spec, "budget_bytes": args.budget_bytes})
            print(json_bytes(result).decode("utf-8"))
            return 0
        with PreviewServer(root, router, args.port) as server:
            print(f"Spec activation preview (read-only): {server.origin}/#{server.token}", flush=True)
            print("Keep this URL private. No receipts or repository files are written. Ctrl-C stops the server.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except (ExplainError, OSError, ValueError, RuntimeError) as exc:
        print(f"explain-spec-activation: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
