---
schema_version: "2.1"
id: {{ID}}
title: "{{TITLE}}"
status: active
latest_checkpoint:
created: {{DATE}}
updated: {{DATE}}
owner: "{{OWNER}}"
---

# {{TITLE}}

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

<!-- REQUIRED: Explain the user-visible capability, why it matters, and how someone can observe it working. -->

## Current Snapshot

<!-- REQUIRED: State the current milestone, what is true now, the exact next action, and any open question. Keep this section short enough for handoff. -->

- Latest checkpoint: none.
- Current milestone: `<milestone or phase>`.
- Current state: `<concise factual state>`.
- Next action: `<exact file, command, or decision>`.

## Context and Orientation

<!-- REQUIRED: Define terms, describe the current system, and name exact repository-relative paths and module relationships. -->

## Constraints and References

<!-- REQUIRED: Summarize task-relevant invariants here, then link canonical repository sources. -->

| Source | Why it matters | When to read |
|---|---|---|
| `path/from/repo/root` | Replace with a real entry point | Before implementation |

## Plan of Work

<!-- REQUIRED: Describe the current sequence of edits and additions in prose, including files, functions or modules and why. -->

## Milestones

### Milestone 1: Replace with an independently verifiable outcome

<!-- REQUIRED: State what will exist, the work scope, the command or action to run, and the observable result. -->

## Concrete Steps

<!-- REQUIRED: Give working directories, exact commands, key edit locations, and short expected transcripts. -->

## Validation and Acceptance

<!-- REQUIRED: Replace every placeholder with observable behavior, exact commands, expected results, and evidence. -->

- [ ] From `<repo-root>`, run `<command>`; expect `<observable result>`. Evidence: `<path or concise transcript>`.

## Idempotence and Recovery

<!-- REQUIRED: Explain safe repetition, retry after partial failure, rollback, backup, migration and cleanup behavior. -->

## Progress

- [ ] ({{TIMESTAMP}}) Plan created; research and fill every REQUIRED section before implementation.

## Surprises & Discoveries

- None yet.

## Decision Log

- None yet.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

<!-- REQUIRED_AT_COMPLETION: Compare the result with the original purpose. Record completed behavior, evidence, gaps, remaining work, and lessons. -->

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

<!-- REQUIRED: Name required libraries, services, types, interfaces, signatures and dependency constraints. -->

## Artifacts and Notes

- Plan: `docs/exec-plans/active/{{DIR_NAME}}/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- {{TIMESTAMP}} — Initial plan created.
