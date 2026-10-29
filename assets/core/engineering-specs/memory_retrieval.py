"""Deterministic, non-normative memory selection. No filesystem or lifecycle writes.

P1-A deliberately returns a shadow proposal: effective context is the baseline.
A review assessment is an annotation, never an authority or applicability input.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable

SCHEMA_VERSION = 1
POLICY_ID = "task-scoped-shadow-v1"
MAX_CANDIDATES = 128
MAX_CONTENT_BYTES = 1024 * 1024
KINDS = {"exec-plan", "adr", "spec", "requirement"}
ASSESSMENTS = {"retain_active", "review_due", "historical", "insufficient_evidence"}


class RetrievalError(ValueError):
    """Invalid required selection input; do not produce partial context."""


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def instant(value: str) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise RetrievalError("TIME_INVALID")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError as exc:
        raise RetrievalError("TIME_INVALID") from exc


@dataclass(frozen=True)
class MemoryCandidate:
    kind: str
    artifact_id: str
    source: str
    source_sha256: str
    content: str
    relation: str = "unknown"  # direct / related / background / unknown
    current_effect: bool | None = None
    historical: bool = False
    mandatory: bool = False
    priority: int = 20

    @property
    def key(self) -> tuple[str, str]:
        return self.kind, self.artifact_id

    @property
    def section_id(self) -> str:
        # Safe for Spec Router's section ID grammar, including project Spec IDs.
        return "memory-" + sha256(canonical(self.key))[:32]


def checked_candidates(values: Iterable[MemoryCandidate]) -> tuple[MemoryCandidate, ...]:
    candidates = tuple(values)
    if len(candidates) > MAX_CANDIDATES:
        raise RetrievalError("CANDIDATE_LIMIT_EXCEEDED")
    seen: set[tuple[str, str]] = set()
    sources: set[str] = set()
    total = 0
    for item in candidates:
        if not isinstance(item, MemoryCandidate):
            raise RetrievalError("CANDIDATE_INVALID")
        if (not isinstance(item.kind, str) or item.kind not in KINDS or not isinstance(item.artifact_id, str)
                or not 1 <= len(item.artifact_id) <= 256
                or any(ord(c) < 32 for c in item.artifact_id)
                or not isinstance(item.relation, str)
                or item.relation not in {"direct", "related", "background", "unknown"}
                or type(item.mandatory) is not bool or type(item.historical) is not bool
                or (item.current_effect is not None and type(item.current_effect) is not bool)
                or (item.historical and item.current_effect is True)
                or type(item.priority) is not int or item.priority < 0
                or not isinstance(item.source, str) or not 1 <= len(item.source) <= 512
                or any(ord(c) < 32 for c in item.source) or "\\" in item.source
                or not isinstance(item.source_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", item.source_sha256)
                or not isinstance(item.content, str) or not item.content.strip()):
            raise RetrievalError("CANDIDATE_INVALID")
        path = item.source.split("#", 1)[0]
        if PurePosixPath(path).is_absolute() or any(p in {"", ".", ".."} for p in path.split("/")):
            raise RetrievalError("SOURCE_PATH_INVALID")
        if item.key in seen or item.source in sources:
            raise RetrievalError("CANDIDATE_DUPLICATE")
        seen.add(item.key)
        sources.add(item.source)
        total += len(item.content.encode("utf-8"))
        if total > MAX_CONTENT_BYTES:
            raise RetrievalError("CONTEXT_INPUT_TOO_LARGE")
    return tuple(sorted(candidates, key=lambda c: c.key))


def review_hints(report: object, candidates: Iterable[MemoryCandidate], *,
                 as_of: str, max_age_seconds: int = 86400) -> dict[str, Any]:
    """Validate optional P0 annotations; never use them to hide a candidate.

    Matching source bytes and the report self-digest detect drift, not truth or
    authorization. Related-source authority is always resolved independently.
    """
    when = instant(as_of)
    if type(max_age_seconds) is not int or not 0 <= max_age_seconds <= 365 * 86400:
        raise RetrievalError("HINT_AGE_LIMIT_INVALID")
    fallback = {"status": "unavailable", "reason": "REPORT_ABSENT", "items": {}}
    if report is None:
        return fallback
    try:
        if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
                or report["schema_version"] != 1
                or report.get("engine_version") != "memory-review-v1"
                or report.get("input_integrity") != "validated"
                or report.get("read_only") is not True):
            raise RetrievalError("REPORT_UNSUPPORTED_OR_INCOMPLETE")
        payload = {k: v for k, v in report.items() if k != "report_sha256"}
        if report.get("report_sha256") != sha256(canonical(payload)):
            raise RetrievalError("REPORT_DIGEST_MISMATCH")
        stamp = instant(report.get("as_of"))
        if stamp > when:
            raise RetrievalError("REPORT_FROM_FUTURE")
        if (when - stamp).total_seconds() > max_age_seconds:
            raise RetrievalError("REPORT_TOO_OLD")
        raw = report.get("items")
        if not isinstance(raw, list) or len(raw) > 20000:
            raise RetrievalError("REPORT_ITEMS_INVALID")
        by_key = {}
        for item in raw:
            if (not isinstance(item, dict) or item.get("kind") not in KINDS
                    or not isinstance(item.get("artifact_id"), str)):
                raise RetrievalError("REPORT_ITEMS_INVALID")
            key = item["kind"], item["artifact_id"]
            if key in by_key:
                raise RetrievalError("REPORT_ITEM_DUPLICATE")
            by_key[key] = item
        hints = {}
        for candidate in checked_candidates(candidates):
            item = by_key.get(candidate.key)
            if item is None:
                continue
            source = item.get("source")
            path = candidate.source.split("#", 1)[0]
            if (not isinstance(source, dict) or source.get("path") != path
                    or source.get("sha256") != candidate.source_sha256):
                hints[candidate.key] = {"status": "ignored", "reason": "SOURCE_CHANGED"}
            elif item.get("assessment") not in ASSESSMENTS:
                hints[candidate.key] = {"status": "ignored", "reason": "ASSESSMENT_INVALID"}
            else:
                hints[candidate.key] = {
                    "status": "source_matched", "assessment": item["assessment"],
                    "authority_verified": False,
                }
        return {"status": "available", "reason": "SOURCE_SCOPED_ANNOTATIONS_ONLY",
                "report_sha256": report["report_sha256"], "items": hints}
    except (RetrievalError, ValueError, TypeError, OverflowError) as exc:
        return {**fallback, "reason": str(exc) if isinstance(exc, RetrievalError) else "REPORT_INVALID"}


def select_memory(candidates: Iterable[MemoryCandidate], hints: dict[str, Any] | None = None
                  ) -> list[dict[str, Any]]:
    rows = []
    for item in checked_candidates(candidates):
        tier = "required" if item.mandatory else item.relation
        action = "reference" if tier == "background" else "include"
        reasons = [{"required": "MANDATORY_SECTION_PRESERVED", "direct": "EXPLICIT_TASK_REFERENCE",
                    "related": "DECLARED_TASK_RELATION", "background": "BACKGROUND_NAVIGATION_ONLY",
                    "unknown": "RELEVANCE_UNKNOWN_PRESERVED"}[tier]]
        if item.historical:
            reasons.append("HISTORICAL_NOT_CURRENT_AUTHORITY")
        if item.current_effect is True:
            reasons.append("CURRENT_AUTHORITY_UNCHANGED")
        hint = (hints or {}).get("items", {}).get(item.key)
        if hint and hint.get("status") == "source_matched":
            if hint.get("assessment") == "review_due":
                reasons.append("REVIEW_DUE_IS_NOT_EXPIRY")
            if hint.get("assessment") == "insufficient_evidence":
                reasons.append("INSUFFICIENT_EVIDENCE_IS_NOT_IDLE")
        rows.append({"kind": item.kind, "artifact_id": item.artifact_id,
                     "section_id": item.section_id, "source": item.source,
                     "source_sha256": item.source_sha256, "tier": tier,
                     "proposed_action": action, "reason_codes": sorted(reasons),
                     "current_effect": item.current_effect, "historical": item.historical,
                     "review_hint": hint})
    return rows


def shadow_context(router: Any, candidates: Iterable[MemoryCandidate], *,
                   hints: dict[str, Any] | None = None, budget_bytes: int = 8192) -> dict[str, Any]:
    """Render both plans with the existing budgeter. Never replace effective text."""
    values = checked_candidates(candidates)
    rows = select_memory(values, hints)
    actions = {r["section_id"]: r["proposed_action"] for r in rows}

    def sections(proposed: bool):
        for c in values:
            content = c.content
            if proposed and actions[c.section_id] == "reference":
                content = f"[ContextRef:{c.section_id}] {c.source}"
            yield router.SessionContextSection(
                id=c.section_id, priority=c.priority, content=content,
                source=c.source, mandatory=c.mandatory,
            )

    baseline = router.plan_session_context(sections(False), budget_bytes)
    proposal = router.plan_session_context(sections(True), budget_bytes)
    return {
        "schema_version": SCHEMA_VERSION, "policy_id": POLICY_ID, "mode": "shadow",
        "scope": "supplemental_artifact_context_only", "read_only": True,
        "effective_context": baseline["text"], "baseline": baseline, "proposal": proposal,
        "selection": rows, "effective_changed": False,
        "baseline_sha256": sha256(baseline["text"].encode("utf-8")),
        "proposal_sha256": sha256(proposal["text"].encode("utf-8")),
        "byte_delta": proposal["used_bytes"] - baseline["used_bytes"],
        "hint_status": {k: v for k, v in (hints or {}).items() if k != "items"},
        "authority_changed": False,
        "coverage": {"normative_capsules": "existing_resolvers_unchanged",
                     "code_to_adr": "unknown", "semantic_obsolescence": "not_inferred"},
    }
