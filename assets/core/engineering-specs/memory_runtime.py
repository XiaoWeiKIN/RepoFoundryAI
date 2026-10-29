"""Opt-in session memory selection; never owns applicability or lifecycle state.

Called only after the Core has rendered a valid routing baseline and before
its exact activation capsule is appended. This module never writes files or
executes a professional Skill. Configuration and background EPs are optional.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

CONFIG_PATH = ".repo-foundry/memory-context.json"
CONFIG_SCHEMA = 1
MODES = ("off", "shadow", "opt-in")
MAX_CONFIG_BYTES = 16 * 1024
MAX_REPORT_BYTES = 1024 * 1024
MAX_BACKGROUND_EPS = 8
EP_ID = re.compile(r"EP-([0-9]{3,8})", re.IGNORECASE)


class MemoryRuntimeError(ValueError):
    """An optional optimization input is unavailable or inconsistent."""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MemoryRuntimeError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _relative(value: object) -> str:
    if (not isinstance(value, str) or not value or len(value) > 512
            or any(ord(c) < 32 for c in value) or "\\" in value
            or PurePosixPath(value).is_absolute()
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise MemoryRuntimeError("PATH_INVALID")
    return value


def _read(router: Any, root: Path, relative: str, limit: int) -> bytes:
    path = router._resolve_regular(root, _relative(relative), "MEMORY_SOURCE_INVALID")
    if path.stat().st_size > limit:
        raise MemoryRuntimeError("SOURCE_TOO_LARGE")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise MemoryRuntimeError("SOURCE_TOO_LARGE")
    return raw


def _json(raw: bytes) -> dict[str, Any]:
    def constant(_value):
        raise MemoryRuntimeError("JSON_NONFINITE")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                       parse_constant=constant)
    if not isinstance(value, dict):
        raise MemoryRuntimeError("JSON_OBJECT_REQUIRED")
    return value


def config_from(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "mode"}
    allowed = required | {"background_ep", "review_report", "max_report_age_seconds"}
    if (not isinstance(value, dict) or not required <= set(value)
            or set(value) - allowed or type(value["schema_version"]) is not int
            or value["schema_version"] != CONFIG_SCHEMA
            or not isinstance(value["mode"], str) or value["mode"] not in MODES):
        raise MemoryRuntimeError("CONFIG_INVALID")
    ids = value.get("background_ep", [])
    if not isinstance(ids, list) or len(ids) > MAX_BACKGROUND_EPS:
        raise MemoryRuntimeError("BACKGROUND_SELECTOR_INVALID")
    normalized = []
    for raw in ids:
        match = EP_ID.fullmatch(raw) if isinstance(raw, str) else None
        if match is None:
            raise MemoryRuntimeError("BACKGROUND_SELECTOR_INVALID")
        normalized.append(f"EP-{int(match[1]):03d}")
    if len(set(normalized)) != len(normalized):
        raise MemoryRuntimeError("BACKGROUND_SELECTOR_DUPLICATE")
    report = value.get("review_report")
    if report is not None:
        report = _relative(report)
    maximum_age = value.get("max_report_age_seconds", 86400)
    if type(maximum_age) is not int or not 0 <= maximum_age <= 365 * 86400:
        raise MemoryRuntimeError("REPORT_AGE_INVALID")
    return {"schema_version": CONFIG_SCHEMA, "mode": value["mode"],
            "background_ep": sorted(normalized), "review_report": report,
            "max_report_age_seconds": maximum_age}


def _selection_module():
    path = Path(__file__).with_name("memory_retrieval.py")
    if path.is_symlink() or not path.is_file():
        raise MemoryRuntimeError("RETRIEVAL_MODULE_UNAVAILABLE")
    name = "_repoharness_memory_retrieval_runtime"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MemoryRuntimeError("RETRIEVAL_MODULE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _result(baseline: dict[str, Any], *, mode: str, status: str,
            reason: str, **diagnostics) -> dict[str, Any]:
    return {**baseline, "memory": {
        "schema_version": 1, "policy_id": "runtime-background-v1",
        "mode": mode, "status": status, "reason": reason,
        "original_core_bytes": baseline["used_bytes"],
        "configured_baseline_bytes": baseline["used_bytes"],
        "proposed_bytes": baseline["used_bytes"],
        "effective_bytes": baseline["used_bytes"], "saved_bytes": 0,
        "core_context_sha256": _digest(baseline["text"].encode("utf-8")),
        "protected_core_unchanged": True, "authority_changed": False,
        "capsule_budget_included": False, **diagnostics,
    }}


def apply_context(router: Any, root: Path, runtime: dict[str, Any],
                  baseline: dict[str, Any], *, as_of: str | None = None
                  ) -> dict[str, Any]:
    """Preserve the rendered Core prefix; spend only its remaining byte budget.

    Off/absent config cannot add work to the ordinary task path. Shadow shows
    the configured baseline, opt-in selects the proposal. No claim is made
    that adding configured background context saves bytes over config=off.
    """
    config_path = root / CONFIG_PATH
    if not config_path.exists() and not config_path.is_symlink():
        return baseline
    mode = "off"
    try:
        config_raw = _read(router, root, CONFIG_PATH, MAX_CONFIG_BYTES)
        config = config_from(_json(config_raw))
        mode = config["mode"]
        if mode == "off":
            return _result(baseline, mode=mode, status="off", reason="EXPLICIT_OFF")
        if runtime.get("context_direct_ep_overflow"):
            raise MemoryRuntimeError("TASK_SCOPE_TOO_LARGE")
        direct = set(runtime.get("context_direct_ep_refs", []))
        selected = runtime.get("context_ep_ref")
        if isinstance(selected, str):
            direct.add(selected)
        background = [item for item in config["background_ep"] if item not in direct]
        if not background:
            return _result(baseline, mode=mode, status="unchanged", reason="NO_BACKGROUND_CONTEXT")
        separator = 2 if baseline["text"] else 0
        remaining = baseline["budget_bytes"] - baseline["used_bytes"] - separator
        if remaining < 1:
            return _result(baseline, mode=mode, status="baseline_fallback", reason="NO_SUPPLEMENTAL_BUDGET")
        selection = _selection_module()
        when = as_of or dt.datetime.now(dt.timezone.utc).isoformat()
        stamp = selection.instant(when).isoformat().replace("+00:00", "Z")
        candidates = []
        source_hashes = {}
        for plan_id in background:
            number = int(plan_id.split("-", 1)[1])
            folder = root / "docs/exec-plans/active"
            matches = sorted(folder.glob(f"ep-{number:03d}_*/EXECPLAN.md"))
            if len(matches) != 1:
                raise MemoryRuntimeError("BACKGROUND_EP_UNAVAILABLE")
            relative = matches[0].relative_to(root).as_posix()
            before = _read(router, root, relative, router.MAX_CONTEXT_BYTES)
            snapshot, _unused_adr_refs = router._session_ep_snapshot(root, plan_id)
            after = _read(router, root, relative, router.MAX_CONTEXT_BYTES)
            if before != after:
                raise MemoryRuntimeError("SOURCE_CHANGED")
            if snapshot.source != relative:
                raise MemoryRuntimeError("BACKGROUND_EP_UNAVAILABLE")
            source_hashes[relative] = _digest(before)
            candidates.append(selection.MemoryCandidate(
                kind="exec-plan", artifact_id=plan_id, source=relative,
                source_sha256=_digest(before), content=snapshot.content,
                relation="background", priority=40,
            ))
        review = None
        report_raw = None
        report_path = config["review_report"]
        if report_path is not None:
            report_raw = _read(router, root, report_path, MAX_REPORT_BYTES)
            review = _json(report_raw)
        hints = selection.review_hints(
            review, candidates, as_of=stamp,
            max_age_seconds=config["max_report_age_seconds"],
        )
        if report_path is not None:
            if hints["status"] != "available":
                raise MemoryRuntimeError("OPTIONAL_REPORT_UNAVAILABLE")
            for candidate in candidates:
                hint = hints["items"].get(candidate.key, {})
                if hint.get("status") != "source_matched":
                    raise MemoryRuntimeError("OPTIONAL_REPORT_SOURCE_CHANGED")
        comparison = selection.shadow_context(router, candidates, hints=hints,
                                               budget_bytes=remaining)
        for relative, expected in source_hashes.items():
            if _digest(_read(router, root, relative, router.MAX_CONTEXT_BYTES)) != expected:
                raise MemoryRuntimeError("SOURCE_CHANGED")
        if _read(router, root, CONFIG_PATH, MAX_CONFIG_BYTES) != config_raw:
            raise MemoryRuntimeError("CONFIG_CHANGED")
        if report_raw is not None and _read(router, root, report_path, MAX_REPORT_BYTES) != report_raw:
            raise MemoryRuntimeError("REPORT_CHANGED")
        normal = comparison["baseline"]
        proposal = comparison["proposal"]
        usable = (comparison["proposal_status"] == "rendered"
                  and proposal["used_bytes"] <= normal["used_bytes"])
        effective = proposal if mode == "opt-in" and usable else normal
        prefix = baseline["text"] + ("\n\n" if baseline["text"] and effective["text"] else "")
        text = prefix + effective["text"]
        used = len(text.encode("utf-8"))
        if used > baseline["budget_bytes"]:
            raise MemoryRuntimeError("EFFECTIVE_CONTEXT_EXCEEDS_BUDGET")
        reason = ("SHADOW_BASELINE_PRESERVED" if mode == "shadow"
                  else "BACKGROUND_REFERENCES_APPLIED" if usable
                  else "NO_BOUNDED_PROPOSAL_BENEFIT")
        result = _result(
            baseline, mode=mode, status="shadow" if mode == "shadow" else "applied" if usable else "unchanged",
            reason=reason, as_of=stamp, config_sha256=_digest(config_raw),
            sources=dict(sorted(source_hashes.items())),
            configured_baseline_bytes=baseline["used_bytes"] + separator + normal["used_bytes"],
            proposed_bytes=baseline["used_bytes"] + separator + proposal["used_bytes"],
            effective_bytes=used,
            saved_bytes=(normal["used_bytes"] - effective["used_bytes"]),
            selection=comparison["selection"], hint_status=comparison["hint_status"],
            proposal_status=comparison["proposal_status"],
        )
        result.update(text=text, used_bytes=used,
                      selections=baseline["selections"] + effective["selections"])
        return result
    except (OSError, ValueError, RuntimeError, UnicodeError, ImportError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, MemoryRuntimeError) else "OPTIONAL_MEMORY_INPUT_UNAVAILABLE"
        return _result(baseline, mode=mode, status="baseline_fallback", reason=reason)
