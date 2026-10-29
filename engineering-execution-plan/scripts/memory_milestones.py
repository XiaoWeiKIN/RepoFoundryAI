"""Bounded optional evidence for EP next-action review; never progress/approval.

Consume explicitly supplied exported release/CI JSON snapshots. SHA-256 checks
bytes and identity, not whether an external service actually issued the record.
The source must already exist inside the assessed repository. No Git/network.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ENGINE = "ep-milestone-hints-v1"
MAX_RECORDS = 128
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
EP_ID = re.compile(r"EP-[0-9]{3,8}")
PUBLISH_VERB = re.compile(r"\b(?:publish|publishing|published|release|releasing)\b|发布|发行", re.I)


class MilestoneEvidenceError(RuntimeError):
    pass


def _next_action(snapshot: str) -> str:
    """Read one authored Snapshot action; accept wrapped continuation lines."""
    result = []
    active = False
    for line in snapshot.splitlines():
        match = re.match(r"^\s*-\s+Next action:\s*(.*)$", line)
        if match:
            if active:
                raise MilestoneEvidenceError("EP_NEXT_ACTION_AMBIGUOUS")
            active = True
            result.append(match[1])
        elif active and re.match(r"^\s*-\s+", line):
            break
        elif active and line.strip():
            if not line.startswith((" ", "\t")):
                break
            result.append(line.strip())
    return " ".join(result).strip()


def _record(root: Path, raw: object, items: dict[str, dict[str, Any]],
            report_time: object, review: Any, ep: Any) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(raw, dict) or not isinstance(raw.get("event"), str):
        raise MilestoneEvidenceError("MILESTONE_RECORD_INVALID")
    event = raw["event"]
    keys = (
        {"artifact_id", "event", "version", "at", "source"}
        if event == "release_published" else
        {"artifact_id", "event", "match_text", "at", "source"}
        if event == "ci_succeeded" else set()
    )
    if not keys or set(raw) != keys:
        raise MilestoneEvidenceError("MILESTONE_RECORD_FIELDS_INVALID")
    ep_id = raw["artifact_id"]
    if not isinstance(ep_id, str) or not EP_ID.fullmatch(ep_id):
        raise MilestoneEvidenceError("MILESTONE_EP_ID_INVALID")
    item = items.get(ep_id)
    if item is None or item["status"] not in {"active", "blocked"}:
        raise MilestoneEvidenceError("MILESTONE_ACTIVE_EP_REQUIRED")
    stamp = review.instant(raw["at"])
    if stamp > review.instant(report_time):
        raise MilestoneEvidenceError("MILESTONE_FUTURE_TIME")
    source = raw["source"]
    if (not isinstance(source, dict) or set(source) != {"path", "sha256", "revision"}
            or not isinstance(source["path"], str)
            or not isinstance(source["sha256"], str)
            or not SHA256.fullmatch(source["sha256"])
            or not isinstance(source["revision"], str)
            or not source["revision"].strip()):
        raise MilestoneEvidenceError("MILESTONE_SOURCE_INVALID")
    source_path = source["path"]
    # Canonical path validation, non-symlink checks and JSON bounding come
    # from the same validated P0 utility. Never import code from the target.
    evidence = review.read_json(root, source_path)
    if review.file_digest(review.safe_path(root, source_path)) != source["sha256"]:
        raise MilestoneEvidenceError("MILESTONE_EVIDENCE_DIGEST_MISMATCH")
    path = review.safe_path(root, item["source"]["path"])
    if review.file_digest(path) != item["source"]["sha256"]:
        raise MilestoneEvidenceError("MILESTONE_EP_SOURCE_CHANGED")
    text = path.read_text(encoding="utf-8")
    snapshot = ep.section(text, "Current Snapshot")
    if not isinstance(snapshot, str):
        raise MilestoneEvidenceError("MILESTONE_EP_SNAPSHOT_MISSING")
    next_action = _next_action(snapshot)
    if not next_action or not item["next_action_known"]:
        raise MilestoneEvidenceError("MILESTONE_EP_NEXT_ACTION_UNKNOWN")

    if event == "release_published":
        version = raw["version"]
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise MilestoneEvidenceError("MILESTONE_VERSION_INVALID")
        tag = "v" + version
        if (evidence.get("tag_name") != tag
                or evidence.get("draft") is not False
                or evidence.get("prerelease") is not False
                or evidence.get("published_at") != raw["at"]
                or source["revision"] != "release:" + tag):
            raise MilestoneEvidenceError("MILESTONE_RELEASE_IDENTITY_MISMATCH")
        url = evidence.get("html_url")
        if (not isinstance(url, str)
                or not re.fullmatch(
                    r"https://github\.com/[^/\s]+/[^/\s]+/releases/tag/" + re.escape(tag), url
                )):
            raise MilestoneEvidenceError("MILESTONE_RELEASE_URL_INVALID")
        matched = bool(
            PUBLISH_VERB.search(next_action)
            and re.search(r"(?<![A-Za-z0-9.])v?" + re.escape(version) + r"(?![A-Za-z0-9.])",
                          next_action, re.I)
        )
        target = version
        identity = tag
    else:
        target = raw["match_text"]
        if not isinstance(target, str) or not 5 <= len(target) <= 100:
            raise MilestoneEvidenceError("MILESTONE_CI_TOKEN_INVALID")
        if any(ord(c) < 32 for c in target):
            raise MilestoneEvidenceError("MILESTONE_CI_TOKEN_INVALID")
        commit = evidence.get("head_sha")
        if (not isinstance(commit, str) or not COMMIT.fullmatch(commit)
                or evidence.get("conclusion") != "success"
                or evidence.get("completed_at") != raw["at"]
                or source["revision"] != "git:" + commit
                or not isinstance(evidence.get("name"), str)):
            raise MilestoneEvidenceError("MILESTONE_CI_IDENTITY_MISMATCH")
        matched = target.lower() in next_action.lower() and target.lower() in evidence["name"].lower()
        identity = review.digest(target.encode("utf-8"))[:16]
    # A validated source may concern an unrelated task; do not infer a match.
    if not matched:
        return {}, [source_path]
    action = {
        "action_id": "exec-plan:" + ep_id + ":review_milestone_evidence:"
                     + event + ":" + identity,
        "kind": "exec-plan",
        "artifact_id": ep_id,
        "type": "review_milestone_evidence",
        "assessment": item["assessment"],
        "reason_codes": ["EP_NEXT_ACTION_EVIDENCE_REVIEW_CANDIDATE"],
        "source": {"path": item["source"]["path"], "sha256": item["source"]["sha256"]},
        "impact": {
            "declared_consumers": item.get("consumers", []),
            "declared_dependencies": item.get("dependencies", []),
            "coverage": item.get("coverage", {}),
            "current_ep_status": item["status"],
        },
        "milestone_evidence": {
            "event": event, "value": target, "at": raw["at"],
            "source": dict(source),
            "next_action": next_action,
            "source_content_checked": True,
            "external_authenticity": "not_verified_offline",
            "head_verification": "not_claimed",
        },
        "preview_only": True,
        "preview_command": "epctl status --json",
        "authorization_before_mutation": "plan_owner",
        "mutation_route_after_approval": "review_and_update_authored_EP_snapshot"
                                        " (existing EP workflow and validation)",
        "automatic_mutation_allowed": False,
        "completion_inferred": False,
        "progress_observation_created": False,
    }
    return action, [source_path]


def collect(root: Path, path: str, report: dict[str, Any],
            review: Any, ep: Any) -> tuple[list[dict[str, Any]], list[str], dict[str, str]]:
    """Return preview actions and exact digests of all opt-in input sources."""
    data = review.read_json(root, path)
    if (set(data) != {"schema_version", "records"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or not isinstance(data["records"], list) or len(data["records"]) > MAX_RECORDS):
        raise MilestoneEvidenceError("MILESTONES_INVALID")
    items = {
        i["artifact_id"]: i for i in report["items"]
        if i["kind"] == "exec-plan" and i["status"] in {"active", "blocked"}
    }
    sources = {path}
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in data["records"]:
        action, paths = _record(root, raw, items, report["as_of"], review, ep)
        sources.update(paths)
        if action:
            if action["action_id"] in seen:
                raise MilestoneEvidenceError("MILESTONE_DUPLICATE_EVENT")
            seen.add(action["action_id"])
            actions.append(action)
    hashes = {relative: review.file_digest(review.safe_path(root, relative))
              for relative in sorted(sources)}
    actions.sort(key=lambda x: (x["kind"], x["artifact_id"], x["action_id"]))
    return actions, sorted(sources), hashes
