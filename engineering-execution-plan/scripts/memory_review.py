#!/usr/bin/env python3
"""Read-only, evidence-scoped engineering memory review (Issue #90).

This companion entrypoint reuses epctl and the distribution's Spec Router.
It never imports executable code from the repository being assessed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
ENGINE_VERSION = "memory-review-v1"
MAX_FILES = 20000
MAX_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
DEFAULT_POLICY = {
    "schema_version": 1,
    "id": "conservative-v1",
    "ep_idle_days": None,
    "adr_review_days": None,
    "spec_review_days": None,
    "version_snapshot_days": None,
}
KINDS = {"exec-plan", "adr", "spec", "requirement"}
EVENTS = {"progress", "review", "retain", "pause", "spec_version"}


class ReviewError(RuntimeError):
    """An incomplete input must not produce a successful assessment."""


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def instant(value: object) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise ReviewError("TIME_INVALID: use a timezone-aware ISO timestamp")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError as exc:
        raise ReviewError("TIME_INVALID: invalid timestamp") from exc


def iso(value: dt.datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReviewError(f"JSON_DUPLICATE_KEY: {key}")
        result[key] = value
    return result


def safe_path(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative
            or any(ord(c) < 32 for c in relative) or "\\" in relative
            or PurePosixPath(relative).is_absolute()
            or any(p in {"", ".", ".."} for p in relative.split("/"))):
        raise ReviewError("PATH_INVALID: expected a canonical repository-relative path")
    path = root
    for part in relative.split("/"):
        path = path / part
        if path.is_symlink():
            raise ReviewError(f"SYMLINK_REJECTED: {relative}")
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise ReviewError(f"PATH_ESCAPE: {relative}") from exc
    return path


def read_json(root: Path, relative: str) -> dict[str, Any]:
    path = safe_path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise ReviewError(f"JSON_SOURCE_INVALID: {relative}")
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise ReviewError(f"JSON_TOO_LARGE: {relative}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               ReviewError("JSON_NONFINITE_NUMBER")))
    except (ValueError, UnicodeError) as exc:
        raise ReviewError(f"JSON_INVALID: {relative}") from exc
    if not isinstance(value, dict):
        raise ReviewError(f"JSON_OBJECT_REQUIRED: {relative}")
    return value


def policy_from(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return dict(DEFAULT_POLICY)
    if (set(value) - set(DEFAULT_POLICY) or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1
            or not isinstance(value.get("id"), str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", value["id"])):
        raise ReviewError("POLICY_INVALID")
    result = {**DEFAULT_POLICY, **value}
    for key in ("ep_idle_days", "adr_review_days", "spec_review_days", "version_snapshot_days"):
        days = result[key]
        if days is not None and (type(days) is not int or not 1 <= days <= 36500):
            raise ReviewError(f"POLICY_INVALID: {key}")
    return result


def file_digest(path: Path) -> str:
    sha = hashlib.sha256()
    count = 0
    if not path.is_file():
        raise ReviewError("EVIDENCE_SOURCE_INVALID")
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            count += len(block)
            if count > MAX_BYTES:
                raise ReviewError("SOURCE_BYTE_LIMIT_EXCEEDED")
            sha.update(block)
    return sha.hexdigest()


def inventory(root: Path, extras: list[str]) -> dict[str, str]:
    """Bound and fingerprint governed sources; reject symlinks before validators."""
    paths: set[str] = set(extras)
    for directory in ("docs", "benchmarks"):
        base = safe_path(root, directory)
        if not base.exists():
            continue
        if not base.is_dir():
            raise ReviewError(f"SOURCE_DIRECTORY_INVALID: {directory}")
        for folder, directories, files in os.walk(base, followlinks=False):
            for name in directories + files:
                candidate = Path(folder) / name
                relative = candidate.relative_to(root).as_posix()
                safe_path(root, relative)
                if not stat.S_ISREG(candidate.lstat().st_mode) and not candidate.is_dir():
                    raise ReviewError(f"SOURCE_TYPE_INVALID: {relative}")
            paths.update((Path(folder) / name).relative_to(root).as_posix() for name in files)
            if len(paths) > MAX_FILES:
                raise ReviewError("SOURCE_FILE_LIMIT_EXCEEDED")
    output: dict[str, str] = {}
    total = 0
    for relative in sorted(paths):
        path = safe_path(root, relative)
        if not path.is_file():
            raise ReviewError(f"SOURCE_MISSING: {relative}")
        sha = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_BYTES:
                    raise ReviewError("SOURCE_BYTE_LIMIT_EXCEEDED")
                sha.update(block)
        output[relative] = sha.hexdigest()
    return output


def owned_module(path: Path, name: str):
    """Load only a sibling/distribution-owned validator, with no bytecode writes."""
    if not path.is_file() or path.is_symlink():
        raise ReviewError(f"VALIDATOR_UNAVAILABLE: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReviewError(f"VALIDATOR_UNAVAILABLE: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_record(root: Path, path: Path, raw: bytes | None = None) -> dict[str, str]:
    relative = path.relative_to(root).as_posix()
    safe_path(root, relative)
    return {"path": relative, "sha256": digest(path.read_bytes() if raw is None else raw)}


def collect(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    ep = owned_module(Path(__file__).with_name("epctl.py"), "memory_review_epctl")
    nodes: list[dict[str, Any]] = []
    warnings: list[str] = []
    health: dict[str, Any] = {}
    governed = ((root / "docs/.epctl").exists() or ep.plan_files(root) or ep.adr_files(root))
    if governed:
        errors, notices = ep.validate_repo(root)
        if errors:
            raise ReviewError("ARTIFACT_VALIDATION_FAILED: " + " | ".join(sorted(errors)))
        warnings.extend(notices)
        rows = ep.status_rows(root)
        health = ep.adr_health(root, rows=rows)
        sources = {s.data["id"]: s for s in ep.adr_sources(root)}
        reviewed_paths: set[str] = set()
        for row in rows["plans"]:
            path = safe_path(root, row["path"])
            text = path.read_text(encoding="utf-8")
            data, _, _ = ep.parse_frontmatter(text)
            snapshot = ep.section(text, "Current Snapshot") or ""
            next_lines = re.findall(r"(?m)^-[ \t]+Next action:[ \t]*([^\r\n]*)$", snapshot)
            next_known = len(next_lines) == 1 and bool(next_lines[0].strip())
            if next_known:
                next_known = not any(s in next_lines[0] for s in ("<", "REQUIRED", "BOOTSTRAP_TODO"))
            nodes.append({
                "artifact_id": row["id"], "kind": "exec-plan", "status": row["status"],
                "current_effect": None, "source": source_record(root, path),
                "dependencies": row.get("adr_refs", []),
                "dependency_review": bool(row.get("architecture_review_required")),
                "next_action_known": next_known, "open_blockers": row["open_blockers"],
                "verification_revision": data.get("verified_revision") or None,
                "verification_evidence": ep.parse_string_array(data.get("verification_evidence", "[]"), "verification_evidence"),
            })
            reviewed_paths.add(row["path"])
        if reviewed_paths != {p.relative_to(root).as_posix() for p in ep.plan_files(root)}:
            raise ReviewError("PLAN_COVERAGE_INCOMPLETE: migrate unsupported legacy plans explicitly")
        for row in rows["adrs"]:
            source = sources[row["id"]]
            nodes.append({
                "artifact_id": row["id"], "kind": "adr", "status": source.data["status"],
                "current_effect": bool(row.get("current")),
                "source": {**source_record(root, source.container_path),
                           "logical_path": source.path.relative_to(root).as_posix(),
                           "document_sha256": digest(source.raw_bytes)},
                "dependencies": sorted(set(ep.parse_inline_ids(source.data.get("depends_on", ""), "ADR")
                                           + ep.parse_inline_ids(source.data.get("amends", ""), "ADR"))),
                "amended_by": row.get("amended_by", []),
                "replacement": source.data.get("superseded_by") or None,
                "verification_revision": None, "verification_evidence": [],
            })
    spec_files = [root / "docs/.engineering" / name for name in ("specs.json", "specs.lock.json")]
    if any(p.exists() for p in spec_files):
        # Never execute the target repository's installed router.
        distribution = Path(__file__).resolve().parents[2]
        router = owned_module(distribution / "assets/core/engineering-specs/spec_router.py",
                              "memory_review_spec_router")
        state = router.load_state(root)
        for entry in state.entries:
            nodes.append({
                "artifact_id": entry.key, "kind": "spec", "status": "project" if entry.project_owned else "locked",
                "current_effect": None, "source": source_record(root, safe_path(root, entry.path)),
                "dependencies": list(entry.requires), "version": entry.version,
                "catalog_revision": state.revision, "verification_revision": None,
                "verification_evidence": [],
            })
        for spec in state.requirement_index.specs:
            for requirement in spec.requirements:
                nodes.append({
                    "artifact_id": requirement.requirement_id, "kind": "requirement", "status": "locked",
                    "current_effect": None,
                    "source": {**source_record(root, safe_path(root, spec.path)),
                               "requirement_sha256": requirement.block.sha256},
                    "dependencies": list(requirement.dependencies), "spec_id": spec.spec_id,
                    "version": spec.version, "catalog_revision": state.revision,
                    "verification_revision": None, "verification_evidence": [],
                })
    keys = [(n["kind"], n["artifact_id"]) for n in nodes]
    if len(keys) != len(set(keys)):
        raise ReviewError("DUPLICATE_ARTIFACT_ID")
    for node in nodes:
        target_kind = "adr" if node["kind"] == "adr" else node["kind"]
        consumers = []
        for other in nodes:
            live = ((other["kind"] == "exec-plan" and other["status"] in {"active", "blocked"})
                    or (other["kind"] == "adr" and other["current_effect"])
                    or other["kind"] in {"spec", "requirement"})
            relation_kind = "adr" if other["kind"] in {"exec-plan", "adr"} else other["kind"]
            if live and relation_kind == target_kind and node["artifact_id"] in other["dependencies"]:
                consumers.append({"kind": other["kind"], "artifact_id": other["artifact_id"]})
        node["consumers"] = sorted(consumers, key=lambda v: (v["kind"], v["artifact_id"]))
    return sorted(nodes, key=lambda n: (n["kind"], n["artifact_id"])), health, sorted(set(warnings))


def observations_from(root: Path, value: dict[str, Any] | None,
                      nodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    if value is None:
        return [], []
    if (set(value) != {"schema_version", "observations"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(value["observations"], list) or len(value["observations"]) > 10000):
        raise ReviewError("OBSERVATIONS_INVALID")
    identities = {(n["kind"], n["artifact_id"]) for n in nodes}
    output: list[dict[str, Any]] = []
    extras: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    required = {"kind", "artifact_id", "event", "at", "recorded_by", "reason"}
    allowed = required | {"evidence", "next_review_at", "available_version", "disposition"}
    for raw in value["observations"]:
        if not isinstance(raw, dict) or not required <= set(raw) or set(raw) - allowed:
            raise ReviewError("OBSERVATION_FIELDS_INVALID")
        if any(not isinstance(raw[k], str) or not raw[k].strip() for k in required):
            raise ReviewError("OBSERVATION_FIELDS_INVALID")
        if (raw["kind"], raw["artifact_id"]) not in identities or raw["event"] not in EVENTS:
            raise ReviewError("OBSERVATION_TARGET_INVALID")
        record = dict(raw)
        record["at"] = iso(instant(raw["at"]))
        key = (raw["kind"], raw["artifact_id"], raw["event"], record["at"])
        if key in seen:
            raise ReviewError("OBSERVATION_DUPLICATE")
        seen.add(key)
        if raw["event"] == "progress" and raw["kind"] != "exec-plan":
            raise ReviewError("PROGRESS_REQUIRES_EP")
        if raw["event"] in {"progress", "review", "spec_version"}:
            evidence = raw.get("evidence")
            if (not isinstance(evidence, dict) or set(evidence) != {"path", "sha256", "revision"}
                    or any(not isinstance(v, str) or not v.strip() for v in evidence.values())
                    or not re.fullmatch(r"[0-9a-f]{64}", evidence["sha256"])):
                raise ReviewError("EVIDENCE_REFERENCE_INVALID")
            path = safe_path(root, evidence["path"])
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                raise ReviewError("EVIDENCE_SOURCE_INVALID")
            if file_digest(path) != evidence["sha256"]:
                raise ReviewError("EVIDENCE_DIGEST_MISMATCH")
            extras.append(evidence["path"])
        if raw["event"] in {"pause", "retain"}:
            record["next_review_at"] = iso(instant(raw.get("next_review_at")))
            if instant(record["next_review_at"]) <= instant(record["at"]):
                raise ReviewError("REVIEW_SCHEDULE_INVALID")
            if "evidence" in raw:
                raise ReviewError("HOLD_IS_NOT_PROGRESS_EVIDENCE")
        elif "next_review_at" in raw:
            raise ReviewError("REVIEW_SCHEDULE_REQUIRES_HOLD")
        if raw["event"] == "spec_version":
            if raw["kind"] not in {"spec", "requirement"}:
                raise ReviewError("VERSION_OBSERVATION_REQUIRES_SPEC")
            if raw.get("disposition") not in {"published", "withdrawn", "superseded"}:
                raise ReviewError("SPEC_DISPOSITION_INVALID")
            if not isinstance(raw.get("available_version"), str) or not raw["available_version"].strip():
                raise ReviewError("SPEC_VERSION_INVALID")
        elif "disposition" in raw or "available_version" in raw:
            raise ReviewError("SPEC_FIELDS_REQUIRE_VERSION_OBSERVATION")
        output.append(record)
    return sorted(output, key=lambda v: (v["kind"], v["artifact_id"], instant(v["at"]), v["event"])), sorted(set(extras))


def assess(node: dict[str, Any], observations: list[dict[str, Any]],
           policy: dict[str, Any], as_of: dt.datetime) -> dict[str, Any]:
    records = [r for r in observations if (r["kind"], r["artifact_id"]) == (node["kind"], node["artifact_id"])]
    future = [r for r in records if instant(r["at"]) > as_of]
    valid = [r for r in records if instant(r["at"]) <= as_of]
    latest = {event: max((r for r in valid if r["event"] == event),
                        key=lambda r: instant(r["at"]), default=None) for event in EVENTS}
    progress, review = latest["progress"], latest["review"]
    reasons: list[str] = []
    due: list[str] = []
    if future:
        reasons.append("FUTURE_OBSERVATION_IGNORED")
    holds = [r for r in valid if r["event"] in {"pause", "retain"}]
    hold = max(holds, key=lambda r: (instant(r["at"]), r["event"]), default=None)
    # A subsequent evidence-backed review fulfills an earlier hold. A new
    # hold after that review still creates its own independent deadline.
    hold_satisfied = bool(hold and review and instant(review["at"]) > instant(hold["at"]))
    deferred = bool(hold and not hold_satisfied and instant(hold["next_review_at"]) > as_of)
    historical = (node["status"] in {"completed", "cancelled", "rejected", "retired", "superseded"})
    kind = node["kind"]
    status = "historical" if historical else "insufficient_evidence"
    if not historical:
        if kind == "exec-plan":
            if node.get("dependency_review"):
                due.append("EP_DEPENDENCY_REVIEW_REQUIRED")
            if not node.get("next_action_known"):
                due.append("EP_NEXT_ACTION_UNKNOWN")
            if node.get("open_blockers"):
                reasons.append("EP_HAS_OPEN_BLOCKERS")
            clock, threshold = progress, policy["ep_idle_days"]
            unknown, aged = "PROGRESS_TIME_UNKNOWN", "EP_IDLE_REVIEW_DUE"
            if progress:
                status = "retain_active"
        else:
            clock, threshold = review, policy["adr_review_days" if kind == "adr" else "spec_review_days"]
            unknown, aged = "REVIEW_TIME_UNKNOWN", "PERIODIC_REVIEW_DUE"
            if kind == "adr":
                if node["current_effect"]:
                    status = "retain_active"
                    reasons.append("CURRENT_AUTHORITY_NOT_AGED_OUT")
                    if node.get("consumers"):
                        reasons.append("CURRENT_ARTIFACT_CONSUMERS")
                    if node.get("amended_by"):
                        reasons.append("AMENDMENT_CONSOLIDATION_CANDIDATE")
                elif node["status"] == "under_review" or node["status"] == "accepted":
                    due.append("ADR_EFFECT_REVIEW_REQUIRED")
                else:
                    reasons.append("PROPOSED_DECISION_NOT_ACCEPTED")
            else:
                reasons.append("LOCKED_VERSION_NOT_AUTOMATICALLY_EXPIRED")
                if review:
                    status = "retain_active"
        if clock is None:
            reasons.append(unknown)
        elif threshold is not None and as_of - instant(clock["at"]) >= dt.timedelta(days=threshold):
            if deferred:
                reasons.append("TIME_REVIEW_DEFERRED")
            else:
                due.append(aged)
        if hold:
            if hold_satisfied:
                reasons.append("REVIEW_HOLD_SATISFIED")
            else:
                reasons.append("EXPLICIT_REVIEW_HOLD" if deferred else "REVIEW_HOLD_ELAPSED")
                if not deferred:
                    due.append("SCHEDULED_REVIEW_DUE")
        version = latest["spec_version"]
        if version and kind in {"spec", "requirement"}:
            window = policy["version_snapshot_days"]
            if window is not None and as_of - instant(version["at"]) >= dt.timedelta(days=window):
                reasons.append("VERSION_SNAPSHOT_STALE")
            elif (version["available_version"] != node["version"] or version["disposition"] != "published"):
                due.append("SPEC_VERSION_REVIEW_CANDIDATE")
        elif kind in {"spec", "requirement"}:
            reasons.append("EXTERNAL_VERSION_UNKNOWN")
        if due:
            status = "review_due"
    else:
        reasons.append("TERMINAL_HISTORY_RETAINED")
    actions = []
    if due:
        action = {"exec-plan": "review_continuation_or_replan", "adr": "review_current_effect",
                  "spec": "review_locked_version", "requirement": "review_requirement_source"}[kind]
        actions.append({"action": action, "authorization_required": "explicit_owner_before_any_transition"})
    if "AMENDMENT_CONSOLIDATION_CANDIDATE" in reasons:
        actions.append({"action": "preview_adr_consolidation", "authorization_required": "none_for_read_only_preview"})
    return {
        **node, "assessment": status, "reason_codes": sorted(set(reasons + due)),
        "last_progress_at": progress["at"] if progress else None,
        "last_review_at": review["at"] if review else None,
        "hold": hold, "evidence_refs": records,
        "recommended_actions": actions, "automatic_mutation_allowed": False,
        "current_code_verified": False,
        "coverage": {"consumers": "declared_artifact_relationships_only",
                     "code_and_test_consumers": "unknown", "activity": "explicit_digest_checked_observations_only"},
    }


def build_report(root: Path, *, as_of: str, policy_path: str | None = None,
                 observations_path: str | None = None) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ReviewError("REPOSITORY_NOT_FOUND")
    when = instant(as_of)
    extras = [s for s in (policy_path, observations_path) if s]
    before = inventory(root, extras)
    policy = policy_from(read_json(root, policy_path) if policy_path else None)
    bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        nodes, health, warnings = collect(root)
    finally:
        sys.dont_write_bytecode = bytecode
    observations, evidence_paths = observations_from(
        root, read_json(root, observations_path) if observations_path else None, nodes
    )
    # Evidence outside docs/benchmarks is pinned separately, not inferred from HEAD.
    if inventory(root, extras) != before:
        raise ReviewError("INPUT_CHANGED_DURING_REVIEW")
    evidence_snapshot = inventory(root, extras + evidence_paths)
    for record in observations:
        proof = record.get("evidence")
        if proof and evidence_snapshot.get(proof["path"]) != proof["sha256"]:
            raise ReviewError("INPUT_CHANGED_DURING_REVIEW")
    items = [assess(node, observations, policy, when) for node in nodes]
    if inventory(root, extras + evidence_paths) != evidence_snapshot:
        raise ReviewError("INPUT_CHANGED_DURING_REVIEW")
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
        "as_of": iso(when), "read_only": True, "input_integrity": "validated",
        "policy": policy, "policy_sha256": digest(canonical(policy)),
        "source_snapshot_sha256": digest(canonical(evidence_snapshot)),
        "coverage": {"git_history": "not_collected", "external_versions": "supplied_snapshots_only",
                     "semantic_obsolescence": "not_inferred", "current_code_verification": "not_performed"},
        "items": items, "adr_health": health,
        "warnings": sorted(w.replace(str(root), ".") for w in warnings),
        "summary": {name: sum(item["assessment"] == name for item in items)
                    for name in ("review_due", "retain_active", "historical", "insufficient_evidence")},
    }
    report["report_sha256"] = digest(canonical(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--as-of", required=True, help="Timezone-aware evaluation instant (no implicit clock)")
    parser.add_argument("--policy", help="Optional repository-relative policy JSON")
    parser.add_argument("--observations", help="Optional repository-relative, digest-bound evidence declarations")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        report = build_report(Path(args.repo), as_of=args.as_of, policy_path=args.policy,
                              observations_path=args.observations)
    except (ReviewError, OSError, UnicodeError, RuntimeError, ValueError) as exc:
        failure = {"schema_version": SCHEMA_VERSION, "read_only": True,
                   "input_integrity": "incomplete", "items": [],
                   "error": str(exc).replace(str(Path(args.repo).resolve()), ".")}
        if args.as_json:
            print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        print(f"memory-review: {failure['error']}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Memory review as of {report['as_of']} (read-only; no authority changed)")
        for item in report["items"]:
            print(f"{item['kind']} {item['artifact_id']}: {item['assessment']} "
                  f"[{', '.join(item['reason_codes'])}]")
        print(json.dumps(report["summary"], sort_keys=True))
        for warning in report["warnings"]:
            print(f"WARNING: {warning}", file=sys.stderr)
        print("Coverage: declared artifact references; code consumers and semantic expiry are unknown.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
