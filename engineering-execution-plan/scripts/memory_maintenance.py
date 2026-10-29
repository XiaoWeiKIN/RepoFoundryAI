#!/usr/bin/env python3
"""Read-only, evidence-bound EP/ADR/Spec guided-maintenance plan (#90 P2).

The professional lifecycle owner remains epctl; this script neither modifies
governed artifacts nor authorizes their transitions. No Git or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ENGINE = "memory-maintenance-v1"
SCHEMA_VERSION = 1
MAX_ACTIONS = 1024

class MaintenanceError(RuntimeError):
    """An incomplete or changed assessment cannot be presented as actionable."""


def _load(path: Path, name: str):
    if not path.is_file() or path.is_symlink():
        raise MaintenanceError("DISTRIBUTION_MODULE_MISSING: " + path.name)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MaintenanceError("DISTRIBUTION_MODULE_MISSING: " + path.name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prior
    return module


def _source(item: dict[str, Any]) -> dict[str, str]:
    source = item["source"]
    if (not isinstance(source, dict) or
            not isinstance(source.get("path"), str) or
            not isinstance(source.get("sha256"), str)):
        raise MaintenanceError("SOURCE_REFERENCE_INVALID")
    return {"path": source["path"], "sha256": source["sha256"]}


def _impact(item: dict[str, Any], *, extra: dict[str, Any] | None = None
            ) -> dict[str, Any]:
    return {
        "declared_consumers": item.get("consumers", []),
        "declared_dependencies": item.get("dependencies", []),
        "coverage": item.get("coverage", {}),
        **(extra or {}),
    }


def _candidate(item: dict[str, Any], kind: str, *, code: str,
               reasons: list[str], command: str, authorization: str,
               mutation_route: str | None, impact: dict[str, Any],
               extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "action_id": f"{kind}:{item['artifact_id']}:{code}",
        "kind": kind,
        "artifact_id": item["artifact_id"],
        "type": code,
        "preview_only": True,
        "preview_command": command,
        "reason_codes": sorted(set(reasons)),
        "assessment": item["assessment"],
        "source": _source(item),
        "impact": impact,
        "authorization_before_mutation": authorization,
        "mutation_route_after_approval": mutation_route,
        "automatic_mutation_allowed": False,
        **(extra or {}),
    }


def plan_actions(
    report: dict[str, Any],
    status: dict[str, list[dict[str, Any]]],
    adr_maintenance: dict[str, Any],
) -> list[dict[str, Any]]:
    """Pure selection: observations never act as authority or removal proof."""
    if (report.get("schema_version") != 1 or report.get("input_integrity") != "validated"
            or report.get("read_only") is not True
            or not isinstance(report.get("items"), list)):
        raise MaintenanceError("MEMORY_REVIEW_NOT_VALIDATED")
    plans = {str(row["id"]): row for row in status.get("plans", [])}
    actions: list[dict[str, Any]] = []
    for item in report["items"]:
        kind = item["kind"]
        identity = item["artifact_id"]
        reasons = item["reason_codes"]
        if kind == "exec-plan" and item["status"] in {"active", "blocked"}:
            row = plans.get(identity)
            if row is None:
                raise MaintenanceError("ACTIVE_EP_STATUS_MISSING: " + identity)
            detail = {
                "open_blockers": item["open_blockers"],
                "completion": row["completion"],
                "completion_blockers": row["completion_blockers"],
                "working_set": row["working_set"],
            }
            if item["assessment"] == "review_due":
                actions.append(_candidate(
                    item, kind, code="review_continuation",
                    reasons=reasons,
                    command="epctl status --json",
                    authorization="plan_owner_for_any_completion_or_cancellation",
                    mutation_route="epctl archive-ep (only after explicit outcome, reason and validation)",
                    impact=_impact(item, extra=detail),
                    extra={"decision_needed": "continue | replan | retain_with_review_date | cancel",
                           "do_not_infer": ["abandoned_from_age", "completed_from_code_presence"]},
                ))
            if row["working_set"] in {"checkpoint_recommended", "checkpoint_required"}:
                actions.append(_candidate(
                    item, kind, code="preview_ep_compaction",
                    reasons=["EP_WORKING_SET_" + str(row["working_set"]).upper()],
                    command=f"epctl auto-checkpoint {identity}",
                    authorization="existing_auto_checkpoint_gates_before_apply",
                    mutation_route="epctl auto-checkpoint (explicit --apply after preview)",
                    impact=_impact(item, extra=detail),
                    extra={"checkpoint_eligibility": "requires_existing_cli_preview",
                           "does_not_prove": "EP completion or abandonment"},
                ))
        elif kind == "adr":
            if item["status"] in {"accepted", "under_review"} and item["assessment"] == "review_due":
                actions.append(_candidate(
                    item, kind, code="review_adr_effect",
                    reasons=reasons,
                    command="epctl adr-maintenance --json",
                    authorization="decision_owner",
                    mutation_route="epctl transition-adr / supersede-adr (separate explicit owner decision)",
                    impact=_impact(item, extra={"current_effect": item["current_effect"]}),
                    extra={"no_automatic_retirement": True},
                ))
            if (item["current_effect"] is True and
                    "AMENDMENT_CONSOLIDATION_CANDIDATE" in reasons):
                actions.append(_candidate(
                    item, kind, code="preview_adr_consolidation",
                    reasons=["AMENDMENT_CONSOLIDATION_CANDIDATE"],
                    command=f"epctl adr-consolidation-plan --adr {identity} --json",
                    authorization="decision_owner_before_any_new_atomic_adr_or_effect_transition",
                    mutation_route="new atomic ADR + owner acceptance + reviewed transition",
                    impact=_impact(item, extra={"current_effect": True,
                                                "amended_by": item.get("amended_by", [])}),
                    extra={"consolidation_is_semantic": "not_proven_by_amendment_edges"},
                ))
        elif kind in {"spec", "requirement"} and item["assessment"] == "review_due":
            actions.append(_candidate(
                item, kind, code="review_spec_version",
                reasons=reasons,
                command="foundryctl --repo . spec validate",
                authorization="explicit_spec_owner_selection_and_lock_update",
                mutation_route="foundryctl spec update (preview and explicit selection)",
                impact=_impact(item, extra={"locked_version": item.get("version"),
                                            "catalog_revision": item.get("catalog_revision")}),
                extra={"never_auto_update_spec_lock": True},
            ))
    for maintenance in adr_maintenance.get("actions", []):
        targets = maintenance["affected"]
        actions.append({
            "action_id": "adr-corpus:" + str(maintenance["type"]),
            "kind": "adr-corpus",
            "artifact_id": "ADR-CORPUS",
            "type": "preview_" + str(maintenance["type"]),
            "preview_only": True,
            "preview_command": str(maintenance["next_command"]),
            "reason_codes": sorted(set(map(str, maintenance["reason_dimensions"]))),
            "severity": maintenance["severity"],
            "impact": {
                "affected": targets,
                "coverage": "epctl_adr_maintenance_default_v1",
            },
            "source": {"path": "docs/DECISIONS.md", "sha256": None,
                       "source_binding": "validated_repository_snapshot"},
            "authorization_before_mutation": str(maintenance["authority_required"]),
            "mutation_route_after_approval": (
                "epctl pack-historical-adrs with explicit IDs, actor and reason"
                if maintenance["type"] == "pack_history"
                else "reviewed Decision Owner / repository owner lifecycle action"
            ),
            "automatic_mutation_allowed": False,
        })
    actions.sort(key=lambda x: (x["kind"], x["artifact_id"], x["type"]))
    if len(actions) > MAX_ACTIONS:
        raise MaintenanceError("MAINTENANCE_ACTION_LIMIT_EXCEEDED")
    ids = [a["action_id"] for a in actions]
    if len(ids) != len(set(ids)):
        raise MaintenanceError("MAINTENANCE_ACTION_DUPLICATE")
    return actions


def _decorate_consolidations(
    ep: Any, root: Path, actions: list[dict[str, Any]],
) -> None:
    """Use the existing read-only ADR impact compiler; never infer equivalence."""
    for action in actions:
        if action["type"] != "preview_adr_consolidation":
            continue
        try:
            detail = ep.adr_consolidation_plan(root, "", [action["artifact_id"]])
        except (ValueError, RuntimeError, OSError) as exc:
            raise MaintenanceError(
                "ADR_CONSOLIDATION_PREVIEW_UNAVAILABLE: "
                + action["artifact_id"] + ": " + str(exc)
            ) from exc
        if not detail.get("preview_only") or not detail.get("non_normative"):
            raise MaintenanceError("ADR_CONSOLIDATION_AUTHORITY_INVALID")
        action["impact"]["resolver_preview"] = {
            key: detail[key] for key in (
                "resolved_adrs", "amendment_edges", "active_plan_impact",
                "proposed_overlap", "source_digests", "recommendation"
            )
        }



def group_adr_review_packets(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One review packet per identical resolved closure *and* impact evidence.

    Preserve the per-ADR action records and exact provenance for existing API
    clients. Different resolver impacts are never silently coalesced, even
    where the ADR ID closure happens to be equal.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    previews: dict[str, dict[str, Any]] = {}
    for action in actions:
        if action["type"] != "preview_adr_consolidation":
            continue
        impact = action["impact"]["resolver_preview"]
        required = (
            "resolved_adrs", "amendment_edges", "active_plan_impact",
            "proposed_overlap", "source_digests", "recommendation",
        )
        signature = {key: impact[key] for key in required}
        resolved = signature["resolved_adrs"]
        if not isinstance(resolved, list) or not resolved:
            raise MaintenanceError("ADR_REVIEW_PACKET_CLOSURE_INVALID")
        # Canonical signature includes source hashes and live consumer impact.
        # A different source/impact means a different review obligation.
        key = hashlib.sha256(json.dumps(
            signature, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        groups.setdefault(key, []).append(action)
        previews[key] = signature
    packets: list[dict[str, Any]] = []
    for key, members in sorted(groups.items()):
        ordered = sorted(members, key=lambda x: x["artifact_id"])
        primary = ordered[0]
        packet_id = "adr-review:" + key
        for member in ordered:
            member["review_packet_id"] = packet_id
            member["review_packet_primary"] = member is primary
        packets.append({
            "packet_id": packet_id,
            "kind": "adr-consolidation",
            "preview_only": True,
            "primary_artifact_id": primary["artifact_id"],
            "preview_command": primary["preview_command"],
            "member_artifact_ids": [x["artifact_id"] for x in ordered],
            "member_action_ids": [x["action_id"] for x in ordered],
            "member_sources": [
                {"artifact_id": x["artifact_id"], **x["source"]} for x in ordered
            ],
            "resolver_impact": previews[key],
            "authorization_before_mutation":
                "decision_owner_before_any_new_atomic_adr_or_effect_transition",
            "automatic_mutation_allowed": False,
            "semantic_equivalence_proven": False,
        })
    return sorted(packets, key=lambda p: p["primary_artifact_id"])


def build_plan(
    root: Path,
    *,
    as_of: str,
    policy_path: str | None = None,
    observations_path: str | None = None,
    milestones_path: str | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    review = _load(Path(__file__).with_name("memory_review.py"), "_memory_maintenance_review")
    report = review.build_report(
        root, as_of=as_of, policy_path=policy_path,
        observations_path=observations_path,
    )
    if report.get("input_integrity") != "validated":
        raise MaintenanceError("MEMORY_REVIEW_NOT_VALIDATED")
    extras = [v for v in (policy_path, observations_path) if v]
    evidence_paths = {
        record["evidence"]["path"]
        for item in report["items"]
        for record in item.get("evidence_refs", [])
        if isinstance(record.get("evidence"), dict)
    }
    captured = review.inventory(root, extras + sorted(evidence_paths))
    if review.digest(review.canonical(captured)) != report["source_snapshot_sha256"]:
        raise MaintenanceError("MEMORY_SOURCE_CHANGED_AFTER_REVIEW")
    ep = _load(Path(__file__).with_name("epctl.py"), "_memory_maintenance_epctl")
    status = ep.status_rows(root)
    if report["adr_health"]:
        maintenance = ep.evaluate_adr_maintenance(
            report["adr_health"], status, ep.eligible_terminal_adr_ids(root),
            explain=True,
        )
    else:
        maintenance = {"actions": [], "policy": {"id": "default-v1"}}
    milestone_actions: list[dict[str, Any]] = []
    milestone_paths: list[str] = []
    milestone_hashes: dict[str, str] = {}
    if milestones_path is not None:
        milestone = _load(
            Path(__file__).with_name("memory_milestones.py"),
            "_memory_maintenance_milestone_evidence",
        )
        milestone_actions, milestone_paths, milestone_hashes = milestone.collect(
            root, milestones_path, report, review, ep,
        )
        combined = review.inventory(
            root, extras + sorted(evidence_paths) + milestone_paths,
        )
        if any(combined.get(path) != expected
               for path, expected in milestone_hashes.items()):
            raise MaintenanceError("MILESTONE_SOURCES_CHANGED_DURING_REVIEW")
    actions = plan_actions(report, status, maintenance)
    actions.extend(milestone_actions)
    actions.sort(key=lambda x: (x["kind"], x["artifact_id"], x["type"], x["action_id"]))
    if len(actions) > MAX_ACTIONS or len({a["action_id"] for a in actions}) != len(actions):
        raise MaintenanceError("MAINTENANCE_ACTION_IDENTITY_INVALID")
    for action in actions:
        if action["kind"] == "adr-corpus":
            # Grouped maintenance actions also need a concrete source digest;
            # the report-level inventory hash alone is not an artifact ID.
            projection_digest = captured.get("docs/DECISIONS.md")
            if not isinstance(projection_digest, str):
                raise MaintenanceError("ADR_CORPUS_SOURCE_UNAVAILABLE")
            action["source"]["sha256"] = projection_digest
    _decorate_consolidations(ep, root, actions)
    review_packets = group_adr_review_packets(actions)
    if review.inventory(root, extras + sorted(evidence_paths)) != captured:
        raise MaintenanceError("MEMORY_SOURCE_CHANGED_DURING_MAINTENANCE")
    if milestones_path is not None:
        latest = review.inventory(
            root, extras + sorted(evidence_paths) + milestone_paths,
        )
        if latest != combined:
            raise MaintenanceError("MILESTONE_SOURCES_CHANGED_DURING_MAINTENANCE")
    result = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE,
        "read_only": True,
        "input_integrity": "validated",
        "as_of": report["as_of"],
        "source_snapshot_sha256": report["source_snapshot_sha256"],
        "review_report_sha256": report["report_sha256"],
        "review_policy": report["policy"],
        "adr_maintenance_policy": maintenance["policy"]["id"],
        "authority_changed": False,
        "current_code_verified": False,
        "coverage": report["coverage"],
        "actions": actions,
        "review_packets": review_packets,
        "milestone_source_snapshot_sha256": (
            review.digest(review.canonical(
                {path: milestone_hashes[path] for path in milestone_paths}
            )) if milestones_path is not None else None
        ),
        "summary": {
            "actions": len(actions),
            "adr_consolidation_packets": len(review_packets),
            "adr_consolidation_deduplicated": (
                sum(a["type"] == "preview_adr_consolidation" for a in actions)
                - len(review_packets)
            ),
            "milestone_review_actions": len(milestone_actions),
            "ep_actions": sum(x["kind"] == "exec-plan" for x in actions),
            "adr_actions": sum(x["kind"] in {"adr", "adr-corpus"} for x in actions),
            "spec_actions": sum(x["kind"] in {"spec", "requirement"} for x in actions),
            "review_due_artifacts": report["summary"]["review_due"],
        },
        "warnings": report["warnings"],
    }
    result["report_sha256"] = review.digest(review.canonical(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--as-of", required=True, help="Timezone-aware ISO instant; no implicit clock")
    parser.add_argument("--policy", help="Optional repository-relative memory-review policy")
    parser.add_argument("--observations", help="Optional digest-bound memory-review observations")
    parser.add_argument("--milestones", help="Optional exported, digest-bound release/CI evidence JSON")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        result = build_plan(
            Path(args.repo), as_of=args.as_of, policy_path=args.policy,
            observations_path=args.observations,
            milestones_path=args.milestones,
        )
    except (OSError, RuntimeError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        message = str(exc).replace(str(Path(args.repo).resolve()), ".")
        if args.as_json:
            print(json.dumps({
                "schema_version": SCHEMA_VERSION, "read_only": True,
                "input_integrity": "incomplete", "actions": [], "error": message,
            }, sort_keys=True))
        print("memory-maintenance: " + message, file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print("Guided memory maintenance as of " + result["as_of"]
              + " (preview only; no authority changed)")
        print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
        for packet in result["review_packets"]:
            print(f"{packet['packet_id']}: {packet['preview_command']}")
            print("  grouped ADRs: " + ", ".join(packet["member_artifact_ids"]))
        for action in result["actions"]:
            if (action["type"] == "preview_adr_consolidation"
                    and "review_packet_id" in action):
                continue
            print(f"{action['action_id']}: {action['preview_command']}")
            print("  reason: " + ", ".join(action["reason_codes"]))
            print("  authorization: " + action["authorization_before_mutation"])
        for warning in result["warnings"]:
            print("WARNING: " + warning, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
