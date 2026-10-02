"""Versioned, renderer-neutral explanations derived from Spec Lab snapshots.

Hashes detect inconsistency; they are not signatures or approval evidence.
The v1 producer is deliberately limited to Spec activation previews.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "repofoundry.explanation/v1"
MAX_BYTES = 2 * 1024 * 1024
FPS = 30
FRAMES_PER_SCENE = 180
BOUNDARY = "Derived preview only. No activation receipt, approval, or execution authority."


class IRError(ValueError):
    """Malformed, inconsistent, or unsupported explanation input."""


def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise IRError("Input must be bounded, finite UTF-8 JSON.") from exc


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse(raw: bytes) -> Any:
    if len(raw) > MAX_BYTES:
        raise IRError("Input exceeds 2 MiB; narrow the explanation instead of truncating it.")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise IRError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(IRError("Nonfinite JSON number.")))
        canonical(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IRError(f"Invalid explanation JSON: {exc}") from exc


def strings(value: object, name: str, maximum: int) -> list[str]:
    if (not isinstance(value, list) or len(value) > maximum
            or any(not isinstance(x, str) or not x.strip() or len(x) > 512 for x in value)
            or len(set(value)) != len(value)):
        raise IRError(f"{name} must be a bounded list of distinct nonempty strings.")
    return value


def digest_field(value: object, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise IRError(f"{name} must be a lowercase SHA-256.")


def pointer(value: object, path: str) -> Any:
    """Resolve local JSON Pointers only. Never fetch a URI or read a file."""
    if path == "":
        return value
    if not path.startswith("/"):
        raise IRError("Evidence references must be local JSON Pointers.")
    try:
        for part in path[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            value = value[int(part)] if isinstance(value, list) else value[part]
        return value
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        raise IRError(f"Evidence pointer does not resolve: {path}") from exc


def from_preview(preview: object) -> dict:
    """Build a reproducible storyboard, without inference or new repository reads."""
    if not isinstance(preview, dict) or len(canonical(preview)) > MAX_BYTES:
        raise IRError("Expected a bounded Spec Lab preview object.")
    preview = parse(canonical(preview))  # Capture values; do not alias mutable caller state.
    if (preview.get("kind") != "read-only-preview" or preview.get("authority") != "none"
            or preview.get("receipt_created") is not False):
        raise IRError("Only read-only, authority-free Spec Lab previews are supported.")
    try:
        paths = strings(preview["paths"], "paths", 8)
        if not paths:
            raise IRError("A preview needs at least one planned path.")
        direct = strings(preview["direct"], "direct", 128)
        whole = strings(preview["whole_specs"], "whole_specs", 128)
        specs, resolved, edges = preview["specs"], preview["resolved"], preview["edges"]
        if any(not isinstance(x, list) or len(x) > 1024 for x in (specs, resolved, edges)):
            raise IRError("Spec lists and dependency graphs must be bounded arrays.")
        strings([s["id"] for s in specs], "Spec IDs", 1024)
        ids = strings([r["id"] for r in resolved], "Requirement IDs", 1024)
        if not set(direct).issubset(ids):
            raise IRError("Direct Requirements are missing from the resolved closure.")
        expected_edges = []
        by_id = {r["id"]: r for r in resolved}
        for r in resolved:
            if r["source"] != ("direct" if r["id"] in direct else "context_dependency"):
                raise IRError("Direct/dependency classification disagrees with the selection.")
            for dep in strings(r["context_dependencies"], "dependencies", 128):
                if dep not in by_id:
                    raise IRError("Dependency is missing from the resolved closure.")
                expected_edges.append({"from": r["id"], "to": dep})
        if sorted(edges, key=canonical) != sorted(expected_edges, key=canonical):
            raise IRError("Dependency edges disagree with the resolved Requirements.")
        # Bounded iterative DAG validation; never rely on browser recursion.
        remaining = {r["id"]: set(r["context_dependencies"]) for r in resolved}
        while remaining:
            leaves = {key for key, deps in remaining.items() if not deps}
            if not leaves:
                raise IRError("Requirement dependency cycle.")
            remaining = {key: deps - leaves for key, deps in remaining.items() if key not in leaves}
        reachable, pending = set(), list(direct)
        while pending:
            key = pending.pop()
            if key not in reachable:
                reachable.add(key)
                pending.extend(by_id[key]["context_dependencies"])
        if reachable != set(ids):
            raise IRError("Resolved Requirements include nodes outside the selected dependency closure.")
        capsule = preview["capsule"]
        if (capsule is None) != (not direct and not whole):
            raise IRError("Selection and capsule presence disagree.")
        if capsule is not None:
            text = capsule["text"]
            if not isinstance(text, str):
                raise IRError("Capsule text must be a string.")
            raw = text.encode("utf-8")
            if (type(capsule["bytes"]) is not int or type(capsule["budget_bytes"]) is not int
                    or not 1 <= capsule["budget_bytes"] <= 32768
                    or len(raw) != capsule["bytes"] or len(raw) > capsule["budget_bytes"]
                    or sha256(raw) != capsule["sha256"]):
                raise IRError("Capsule bytes, budget, or digest disagree. Nothing was truncated.")
        provenance = preview["provenance"]
        for field in ("checked_at",):
            if not isinstance(provenance[field], str) or not provenance[field]:
                raise IRError("Missing source check time.")
        git = provenance["git"]
        if git["dirty"] is not None and type(git["dirty"]) is not bool:
            raise IRError("Git dirty status must be true, false, or null.")
        if git["head"] is not None and not isinstance(git["head"], str):
            raise IRError("Git HEAD must be a string or null.")
        digest_field(provenance["source_set_sha256"], "Source set")
        # Spec Lab uses the standard json.dumps separators, not this IR's canonical form.
        source_raw = json.dumps(provenance["sources"], ensure_ascii=False, sort_keys=True,
                                allow_nan=False).encode("utf-8")
        if sha256(source_raw) != provenance["source_set_sha256"]:
            raise IRError("Source-set digest disagrees with the embedded provenance.")
    except (KeyError, TypeError, AttributeError, UnicodeError) as exc:
        raise IRError("Incomplete or malformed Spec Lab snapshot.") from exc

    def quantity(count: int, noun: str) -> str:
        return f"{count} {noun if count == 1 else noun + 's'}"

    facts = [
        ("paths", "observation", f"The preview contains {quantity(len(paths), 'planned file path')}.", ["/paths"]),
        ("candidates", "observation", f"Path matching returned {quantity(len(specs), 'candidate Spec')}.", ["/specs"]),
        ("selection", "observation", f"The preview records {quantity(len(direct), 'direct Requirement')}; the whole-Spec closure contains {quantity(len(whole), 'Spec')}.", ["/direct", "/whole_specs"]),
        ("closure", "observation", f"The Requirement closure contains {quantity(len(resolved), 'Requirement')} and {quantity(len(edges), 'dependency edge')}.", ["/resolved", "/edges"]),
        ("capsule", "observation", (f"The capsule contains {capsule['bytes']} UTF-8 bytes within a {capsule['budget_bytes']}-byte budget." if capsule else "No capsule was compiled. An empty selection is not a formal no-applicable-Spec decision."), ["/capsule"]),
        ("authority", "limitation", BOUNDARY, ["/authority", "/receipt_created"]),
        ("applicability", "limitation", "Path candidates do not establish semantic applicability. Formal activation still needs task-specific reasons.", ["/kind"]),
        ("freshness", "limitation", "This is a captured local snapshot, not a live view. HEAD alone does not identify uncommitted source bytes.", ["/provenance"]),
    ]
    statements = [{"id": key, "kind": kind, "text": text, "refs": refs} for key, kind, text, refs in facts]
    for statement in statements:
        for ref in statement["refs"]:
            pointer(preview, ref)
    scenes = [{"id": key, "title": title, "statement_ids": [key],
               "from_frame": i * FRAMES_PER_SCENE, "duration_frames": FRAMES_PER_SCENE}
              for i, (key, title) in enumerate([
                  ("paths", "01 / Planned paths"), ("candidates", "02 / Candidate Specs"),
                  ("selection", "03 / Reader selection"), ("closure", "04 / Dependency closure"),
                  ("capsule", "05 / Exact context"), ("authority", "06 / No activation authority")])]
    payload = {
        "schema": SCHEMA, "kind": "derived-explanation", "authority": "none",
        "subject": {"kind": "spec-activation", "title": "From planned paths to exact context"},
        "source": {"kind": "spec-lab-snapshot", "sha256": sha256(canonical(preview)),
                   "snapshot": preview},
        "statements": statements, "scenes": scenes,
        "timeline": {"fps": FPS, "duration_frames": len(scenes) * FRAMES_PER_SCENE,
                     "meaning": "reading order, not observed execution time"},
        "graph": {"nodes": [{"id": r["id"], "role": r["source"],
                               "ref": f"/resolved/{i}"} for i, r in enumerate(resolved)],
                  "edges": edges, "meaning": "from requires to; not measured causality"},
    }
    payload["sha256"] = sha256(canonical(payload))
    if len(canonical(payload)) > MAX_BYTES:
        raise IRError("IR exceeds 2 MiB. Narrow the preview; source text was not truncated.")
    return payload


def validate(ir: object) -> dict:
    """Rebuild v1 projections to reject edited claims, lost limits, or stale hashes."""
    if not isinstance(ir, dict) or ir.get("schema") != SCHEMA:
        raise IRError(f"Unsupported Explanation IR; expected {SCHEMA}.")
    try:
        expected = from_preview(ir["source"]["snapshot"])
    except (KeyError, TypeError) as exc:
        raise IRError("IR has no embedded source snapshot.") from exc
    if canonical(expected) != canonical(ir):
        raise IRError("IR differs from its source-derived projection. Regenerate it; do not edit its claims or hashes.")
    return ir
