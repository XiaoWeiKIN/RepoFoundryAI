#!/usr/bin/env python3
"""P1-A: explicit, read-only shadow preview of task-scoped artifact context.

This is not a SessionStart hook and does not replace normative Spec/ADR capsules.
Only distribution-owned modules are imported; target repositories supply data.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

MAX_SELECTORS = 32


def module_at(path: Path, name: str):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"VALIDATOR_UNAVAILABLE: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("VALIDATOR_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build_preview(root: Path, *, as_of: str, ep_refs: tuple[str, ...] = (),
                  adr_refs: tuple[str, ...] = (), views: tuple[str, ...] = (),
                  paths: tuple[str, ...] = (), background_eps: tuple[str, ...] = (),
                  history: bool = False, review_report: str | None = None,
                  max_report_age_seconds: int = 86400,
                  budget_bytes: int = 8192) -> dict[str, Any]:
    """Run on demand, never as an implicit full-corpus SessionStart operation."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("REPOSITORY_NOT_FOUND")
    groups = (ep_refs, adr_refs, views, paths, background_eps)
    if sum(len(group) for group in groups) > MAX_SELECTORS:
        raise ValueError("SELECTOR_LIMIT_EXCEEDED")
    for group in groups:
        if len(set(group)) != len(group):
            raise ValueError("SELECTOR_DUPLICATE")
    old_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        package = Path(__file__).resolve().parent
        distribution = package.parents[1]
        memory = module_at(package / "memory_review.py", "context_review_support")
        ep = module_at(package / "epctl.py", "context_epctl")
        core_dir = distribution / "assets/core/engineering-specs"
        retrieval = module_at(core_dir / "memory_retrieval.py", "context_memory_core")
        router = module_at(core_dir / "spec_router.py", "context_spec_router")
        retrieval.instant(as_of)
        explicit_ep = set(ep.normalize_reference_ids(ep_refs, "EP"))
        explicit_adr = set(ep.normalize_reference_ids(adr_refs, "ADR"))
        background = set(ep.normalize_reference_ids(background_eps, "EP")) - explicit_ep
        sources: dict[str, str] = {}
        candidates = {}
        notices = []
        adr_seeds = set(explicit_adr)
        constraints = set()

        def record(path: Path) -> tuple[str, str]:
            relative = path.relative_to(root).as_posix()
            checked = memory.safe_path(root, relative)
            if not checked.is_file():
                raise ValueError(f"SOURCE_MISSING: {relative}")
            value = memory.file_digest(checked)
            if relative in sources and sources[relative] != value:
                raise ValueError("SOURCE_CHANGED_DURING_SELECTION")
            sources[relative] = value
            return relative, value

        def add(candidate):
            existing = candidates.get(candidate.key)
            if existing is None or candidate.relation == "direct":
                candidates[candidate.key] = candidate

        if explicit_ep or background:
            for directory in ("docs/exec-plans/active", "docs/exec-plans/completed"):
                memory.safe_path(root, directory)
            for plan_file in ep.plan_files(root):
                memory.safe_path(root, plan_file.relative_to(root).as_posix())
                if not plan_file.is_file():
                    raise ValueError("EP_SOURCE_NOT_REGULAR")
        for item_id in sorted(explicit_ep | background):
            path = ep.find_plan(root, item_id)
            ep.reject_symlink_path(root, path)
            if path.stat().st_size > retrieval.MAX_CONTENT_BYTES:
                raise ValueError("EP_SOURCE_TOO_LARGE")
            relative, digest = record(path)
            errors, warnings = ep.validate_plan(path)
            if errors:
                raise ValueError("EP_VALIDATION_FAILED: " + " | ".join(errors))
            notices.extend(warnings)
            text = path.read_text(encoding="utf-8")
            data, _, _ = ep.parse_frontmatter(text)
            terminal = data["status"] in ep.PLAN_COMPLETED_STATUSES
            if terminal and item_id in explicit_ep and not history:
                raise ValueError(f"HISTORY_INTENT_REQUIRED: {item_id}")
            snapshot = ep.markdown_section_source(text, "Current Snapshot")
            relation = "direct" if item_id in explicit_ep else "background"
            content = (
                f"{item_id} ({data['status']}); informational, not acceptance evidence.\n"
                f"Source: {relative}\n\n" + snapshot
            )
            add(retrieval.MemoryCandidate(
                kind="exec-plan", artifact_id=item_id, source=relative,
                source_sha256=digest, content=content, relation=relation,
                historical=terminal, priority=5 if relation == "direct" else 40,
            ))
            # A background EP cannot make its decisions relevant to this task.
            if relation == "direct":
                adr_seeds.update(ep.parse_inline_ids(data.get("adr_refs", ""), "ADR"))

        if views:
            registry_path = root / "docs/.epctl/decision-views.json"
            record(registry_path)
            registry = ep.load_decision_view_registry(root)
            view_by_id = {v["id"]: v for v in registry["views"]}
            for view in sorted(views):
                if view not in view_by_id:
                    raise ValueError(f"VIEW_NOT_FOUND: {view}")
                adr_seeds.update(view_by_id[view]["adr_refs"])

        if adr_seeds:
            # The existing resolver owns currentness, transitive dependencies,
            # scoped amendments and packed-history identity. Never copy it here.
            adr_sources = ep.adr_sources(root)
            source_by_id = {s.data["id"]: s for s in adr_sources}
            for source in adr_sources:
                record(source.container_path)
            current_seeds = []
            with ep.use_adr_sources(root, adr_sources):
                for item_id in sorted(adr_seeds):
                    if item_id not in source_by_id:
                        raise ValueError(f"ADR_NOT_FOUND: {item_id}")
                    source = source_by_id[item_id]
                    current, _ = ep.adr_currentness(root, item_id)
                    if current and source.data.get("status") == "accepted":
                        current_seeds.append(item_id)
                    else:
                        if not history:
                            raise ValueError(f"NONCURRENT_ADR_REQUIRES_HISTORY: {item_id}")
                        errors, warnings, _ = ep.validate_adr_source(source, historical=True)
                        if errors:
                            raise ValueError("ADR_VALIDATION_FAILED: " + " | ".join(errors))
                        notices.extend(warnings)
                        relative, digest = record(source.container_path)
                        add(retrieval.MemoryCandidate(
                            kind="adr", artifact_id=item_id,
                            source=relative + "#" + item_id, source_sha256=digest,
                            content=f"{item_id}: {relative}#{item_id}; {source.data['status']}; "
                                    "historical/proposed evidence, NOT current architecture authority.",
                            relation="direct" if item_id in explicit_adr else "related",
                            current_effect=False,
                            historical=source.data["status"] in ep.ADR_HISTORY_PACK_STATUSES,
                            priority=10,
                        ))
                if current_seeds:
                    context = ep.resolve_decision_context(root, current_seeds)
                    constraints.update(context["constraint_refs"])
                    for source in context["sources"]:
                        item_id = source["id"]
                        relative, digest = record(root / source["container_path"])
                        add(retrieval.MemoryCandidate(
                            kind="adr", artifact_id=item_id,
                            source=relative + "#" + item_id, source_sha256=digest,
                            content=f"{item_id}: {relative}; current effect verified by ADR resolver. "
                                    "Navigation only; use the existing decision-capsule for exact constraints.",
                            relation="direct" if item_id in explicit_adr else "related",
                            current_effect=True, priority=10 if item_id in explicit_adr else 15,
                        ))
            # A newly introduced amendment can affect closure even if all old
            # source files remain unchanged. Detect additions/removals too.
            after_adr = {s.data["id"]: hashlib.sha256(s.raw_bytes).hexdigest()
                         for s in ep.adr_sources(root)}
            before_adr = {s.data["id"]: hashlib.sha256(s.raw_bytes).hexdigest()
                          for s in adr_sources}
            if before_adr != after_adr:
                raise ValueError("ADR_CORPUS_CHANGED_DURING_SELECTION")

        spec_coverage = "not_requested"
        if paths:
            for path in paths:
                memory.safe_path(root, path)
                if any(c in path for c in "*?["):
                    raise ValueError("TASK_PATH_MUST_BE_CONCRETE")
            spec_coverage = "unknown"
            if any((root / "docs/.engineering" / name).exists()
                   for name in ("specs.json", "specs.lock.json")):
                for name in ("specs.json", "specs.lock.json"):
                    record(root / "docs/.engineering" / name)
                requirement_index = root / "docs/agent-guides/managed/requirements.json"
                if requirement_index.exists():
                    record(requirement_index)
                state = router.load_state(root)
                spec_coverage = "declared_applies_to_candidates_only"
                for entry in state.entries:
                    if any(router._matches(path, pattern) for path in paths for pattern in entry.applies_to):
                        relative, digest = record(root / entry.path)
                        add(retrieval.MemoryCandidate(
                            kind="spec", artifact_id=entry.key,
                            source=relative, source_sha256=digest,
                            content=f"Spec candidate {entry.key}@{entry.version}: {relative}. "
                                    "Path match is not activation or proof of applicability; use Spec Router.",
                            relation="related", priority=20,
                        ))

        review = None
        hint_error = None
        if review_report:
            try:
                review = memory.read_json(root, review_report)
            except (OSError, ValueError, RuntimeError) as exc:
                hint_error = type(exc).__name__
        hints = retrieval.review_hints(
            review, candidates.values(), as_of=as_of,
            max_age_seconds=max_report_age_seconds,
        )
        if hint_error:
            hints["reason"] = "OPTIONAL_REPORT_UNAVAILABLE"
        result = retrieval.shadow_context(router, candidates.values(), hints=hints,
                                          budget_bytes=budget_bytes)
        for relative, expected in sources.items():
            if memory.file_digest(memory.safe_path(root, relative)) != expected:
                raise ValueError("SOURCE_CHANGED_DURING_SELECTION")
        result.update({
            "as_of": retrieval.instant(as_of).isoformat().replace("+00:00", "Z"),
            "request": {"ep": sorted(explicit_ep), "adr": sorted(explicit_adr),
                        "views": sorted(views), "paths": sorted(paths),
                        "background_ep": sorted(background), "history": history},
            "hint_max_age_seconds": max_report_age_seconds,
            "sources": dict(sorted(sources.items())),
            "source_snapshot_sha256": retrieval.sha256(retrieval.canonical(sources)),
            "resolved_constraint_refs": sorted(constraints),
            "warnings": sorted(set(w.replace(str(root), ".") for w in notices)),
        })
        result["coverage"]["spec_paths"] = spec_coverage
        result["report_sha256"] = retrieval.sha256(retrieval.canonical(result))
        return result
    finally:
        sys.dont_write_bytecode = old_bytecode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--ep", action="append", default=[])
    parser.add_argument("--adr", action="append", default=[])
    parser.add_argument("--view", action="append", default=[])
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--background-ep", action="append", default=[],
                        help="Existing optional context to compare; never makes its ADRs task-required")
    parser.add_argument("--history", action="store_true", help="Permit explicit noncurrent/historical lookup")
    parser.add_argument("--review-report", help="Optional existing P0 report; no regeneration")
    parser.add_argument("--max-report-age-seconds", type=int, default=86400)
    parser.add_argument("--budget-bytes", type=int, default=8192)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        report = build_preview(
            Path(args.repo), as_of=args.as_of, ep_refs=tuple(args.ep), adr_refs=tuple(args.adr),
            views=tuple(args.view), paths=tuple(args.path), background_eps=tuple(args.background_ep),
            history=args.history, review_report=args.review_report,
            max_report_age_seconds=args.max_report_age_seconds, budget_bytes=args.budget_bytes,
        )
    except (ValueError, RuntimeError, OSError, UnicodeError) as exc:
        failure = {"schema_version": 1, "mode": "shadow", "input_integrity": "incomplete",
                   "selection": [], "error": str(exc).replace(str(Path(args.repo).resolve()), ".")}
        if args.as_json:
            print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        print(f"memory-context: {failure['error']}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print("Shadow preview only; default SessionStart and engineering authority are unchanged.")
        for row in report["selection"]:
            print(f"{row['kind']} {row['artifact_id']}: {row['tier']} -> {row['proposed_action']}")
        print(f"Supplemental bytes: {report['baseline']['used_bytes']} -> {report['proposal']['used_bytes']}")
        print(f"Optional review hints: {report['hint_status']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
