---
schema_version: "2.6"
id: {{ID}}
title: "{{TITLE}}"
status: active
latest_checkpoint:
research_refs: {{RESEARCH_REFS}}
research_gate: {{RESEARCH_GATE}}
research_gate_reason: "{{RESEARCH_GATE_REASON}}"
adr_refs: {{ADR_REFS}}
adr_constraint_refs: {{ADR_CONSTRAINT_REFS}}
adr_evidence: {{ADR_EVIDENCE}}
design_refs: {{DESIGN_REFS}}
architecture_entrypoint: "{{ARCHITECTURE_ENTRYPOINT}}"
architecture_decision_gate: {{ARCHITECTURE_DECISION_GATE}}
architecture_decision_gate_reason: "{{ARCHITECTURE_DECISION_GATE_REASON}}"
architecture_compliance: {{ARCHITECTURE_COMPLIANCE}}
architecture_compliance_reason: "{{ARCHITECTURE_COMPLIANCE_REASON}}"
required_benchmark_scenarios: {{REQUIRED_BENCHMARK_SCENARIOS}}
verified_revision:
verification_evidence: []
archive_sha256:
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

## Research and Architecture Inputs

- Research gate: `{{RESEARCH_GATE}}`.
- Research references: {{RESEARCH_REFS}}.
- Architecture decision gate: `{{ARCHITECTURE_DECISION_GATE}}`.
- Architecture compliance: `{{ARCHITECTURE_COMPLIANCE}}`.
- ADR references: {{ADR_REFS}}.
- ADR constraint references: {{ADR_CONSTRAINT_REFS}}.
- ADR evidence: {{ADR_EVIDENCE}}.
- Design document references: {{DESIGN_REFS}}.
- Architecture entrypoint: `{{ARCHITECTURE_ENTRYPOINT}}`.

<!-- REQUIRED: Restate the Research conclusions, accepted ADR consequences, implementation constraints, and remaining unknowns needed to execute this plan without opening upstream artifacts. Explain each not-required reason when a gate was explicitly skipped. -->

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
{{ARCHITECTURE_COMPLIANCE_ROWS}}

Every structured constraint from every referenced ADR must appear exactly once.
For a legacy ADR without structured constraints, restate its applicable decision
at document level. Design Docs are explanatory inputs and cannot override an ADR.

## Benchmark Gate Set

- Required Scenario IDs: {{REQUIRED_BENCHMARK_SCENARIOS}}.

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
{{BENCHMARK_GATE_ROWS}}

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

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

### Required Benchmark Scenario Gates

{{BENCHMARK_ACCEPTANCE_ITEMS}}

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

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
