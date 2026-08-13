---
schema_version: "2.7"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-056
title: "Implement reversible ADR effect lifecycle"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "The Repository Owner fixed the lifecycle direction after a concrete validator failure was demonstrated; no evidence-dependent technology choice remains."
adr_refs: ["ADR-014", "ADR-016"]
adr_constraint_refs: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008"]
adr_evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb"]
design_refs: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: satisfied
architecture_decision_gate_reason: ""
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-13
updated: 2026-08-13
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Implement reversible ADR effect lifecycle

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Give Repository Owners a safe way to stop following an ADR that later proves
unreasonable without rewriting the accepted decision or making the repository
invalid. After this plan, `epctl` previews and applies explicit review,
reaffirmation, retirement, and supersession transitions. The preview shows
affected constraints, dependent/amending ADRs, and active ExecPlans. New work
cannot consume non-current architecture; existing active plans remain readable
but expose `architecture_review_required` and cannot be completed until revised.

The user can observe the capability through JSON transition previews, ADR
status/index output, active-plan status, stable decision digests, and the
focused/canonical test suites.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — verified and ready for handoff.
- Current state: ADR schema 1.4, recursive currentness, preview-first review /
  reaffirm / retirement / supersession, transitive impact, active-plan review
  gating, and legacy digest compatibility are implemented. Focused tests,
  repository validation, and the canonical check pass.
- Next action: review the handoff and, when a real ADR needs correction, run a
  dry-run `transition-adr` or `supersede-adr` before explicitly applying it.
- Open question: none that changes the accepted route. Lifecycle history is
  represented by current transition metadata plus repository revision history;
  a cryptographic event ledger is an explicit revisit trigger, not this scope.

## Context and Orientation

`engineering-execution-plan/scripts/epctl.py` owns ADR creation, decision,
supersession, validation, input closure, active-plan validation, indexes, and
status output. `engineering-execution-plan/assets/adr.md` is the only new-ADR
template. `engineering-execution-plan/references/adr.md` and `SKILL.md` are the
human/Agent lifecycle contracts; repository contract tests ensure their public
surface stays aligned.

Today `ADR_STATUSES` has only proposed, accepted, rejected, and superseded.
`validate_adr` requires every `depends_on` or `amends` target of an accepted ADR
to remain accepted. `adr_input_closure` uses the same status for historical
validity and current eligibility. `validate_plan` rejects any non-accepted ADR
in an active EP. `supersede_adr` mutates immediately and has no impact preview.

This plan introduces **decision outcome** as the sealed historical result and
**effect status** as the current `status`. An ADR is a current architecture
input only when its own status and its transitive `depends_on`/`amends` closure
are accepted. A non-current relationship remains valid history but creates a
derived review requirement.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-016_reversible-decision-effect.md` | Normative authority, lifecycle constraints, and compatibility | Before every milestone |
| `docs/design-docs/reversible-adr-effect.md` | State machine, impact semantics, schema, and CLI behavior | Before lifecycle edits |
| `docs/adr/adr-014_governed-artifact-metadata-contract.md` | Common metadata and integrity contract amended by ADR-016 | Before schema/payload edits |
| `engineering-execution-plan/references/adr.md` | Public ADR lifecycle and input rules | Before CLI or validator edits |
| `engineering-execution-plan/scripts/epctl.py` | Canonical deterministic implementation | During every source milestone |
| `engineering-execution-plan/tests/test_epctl.py` | Backward compatibility and behavior evidence | Alongside every source edit |
| `python3 -B scripts/check.py` | Canonical repository gate | At final validation |

Universal invariants are: never change a decided ADR body or its original
decision authority; never infer transition authority; preserve schemas 1–1.3
and archived EP evidence; make mutations preview-first, locked, atomic, and
rollback-safe; do not automatically edit plans or implementation code; and
preserve unrelated EP-057, EP-054, and EP-055 worktree changes.

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `satisfied`.
- Architecture compliance: `applicable`.
- ADR references: ["ADR-014", "ADR-016"].
- ADR constraint references: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008"].
- ADR evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb"].
- Design document references: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

Research is not required because the Repository Owner identified the defect in
an observable local contract, the ADR-010/ADR-012 graph reproduces it, and the
Owner selected the concrete lifecycle route. No technology, performance, or
external-fact uncertainty can change that route.

ADR-014 requires common semantic identity and preserves distinct authority
roles. Its C-001/C-004 are amended only to split sealed decision metadata from
mutable effect metadata; identity, authorship, ownership, created time,
decision authority, inputs, body, and confirmation remain in the integrity
boundary. Raw evidence, actor separation, legacy preservation, and non-governed
file rules remain unchanged.

ADR-016 requires stable decision payloads, explicit authorized preview/apply,
under-review suspension, retirement without fake rollback, replacement links,
active-plan review blockers, current-only new inputs, and legacy compatibility.
Implementation must report transitive impact without automatically choosing a
replacement or mutating affected plans. There are no remaining route-changing
unknowns.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-014#C-001 | Schema 1.4 retains common metadata; `status`/`updated` are lifecycle fields while decision metadata remains sealed. | Template/frontmatter and payload-tamper tests. |
| ADR-014#C-002 | No raw/binary evidence schema changes. | Existing Research/Benchmark suites. |
| ADR-014#C-003 | Transition commands require explicit `decision_maker`; author/owner never grant authority. | Missing/explicit authority CLI tests. |
| ADR-014#C-004 | Decision integrity includes immutable semantic metadata; effect metadata is separately validated and intentionally mutable. | Schema-1.4 payload and effect-validation tests. |
| ADR-014#C-005 | Schemas 1–1.3 remain valid and keep exact decided digests through effect changes. | Legacy compatibility and repository corpus tests. |
| ADR-014#C-006 | Source and generated indexes retain Git/generator provenance without new author headers. | Repository contract suite. |
| ADR-016#C-001 | Normalize historical accepted-origin states for old schemas and seal `decision_outcome` in schema 1.4. | Cross-schema digest-stability tests. |
| ADR-016#C-002 | Add deterministic transition planning, explicit actor/reason, repository lock, recomputation, atomic writes, and rollback. | Preview/apply/idempotence/rollback tests. |
| ADR-016#C-003 | Derive currentness recursively and suspend under-review ADR constraints and affected dependents from new input. | ADR-010/012-shaped chain tests. |
| ADR-016#C-004 | Add terminal `retired` with no replacement requirement and no code mutation. | Retirement preview/apply and filesystem-scope tests. |
| ADR-016#C-005 | Make supersession preview-first with accepted-current replacement and backlinks. | Supersession and historical evidence tests. |
| ADR-016#C-006 | Report affected active EPs, warn during validation, expose status blocker, and reject completed archival. | Plan status/validate/archive tests. |
| ADR-016#C-007 | `new-adr`, `new-ep`, and scoped amendment resolution use recursive currentness. | Creation/input-selection tests. |
| ADR-016#C-008 | Do not migrate sealed historical files; transition legacy ADRs without changing their payload digest. | v1/v1.1/v1.2/v1.3 fixtures and full suite. |

Every structured constraint from every referenced ADR must appear exactly once.
For a legacy ADR without structured constraints, restate its applicable decision
at document level. Design Docs are explanatory inputs and cannot override an ADR.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First extend the ADR template and validator to schema 1.4. Add helpers for
decision outcome, accepted-origin states, recursive currentness, and transition
metadata. Ensure old schemas calculate their original accepted payload even
after review, retirement, or supersession.

Next add deterministic impact analysis and `transition-adr`. Convert
`supersede-adr` to the same preview/apply engine. The engine reports transitive
dependent/amending ADRs, constraints, active plans, and file actions; apply
recomputes under lock and rolls back ADR/index writes on any failure.

Then decouple historical relationship validity from current input eligibility.
New ADRs/EPs and current amendments remain fail-closed. Existing active plans
with affected inputs become review-required warnings and completion blockers;
archived plans keep their historical evidence semantics.

Finally update Skill/reference/design/metadata documentation and repository
contract assertions, rebuild indexes, and run focused plus canonical checks.

## Milestones

### Milestone 1: Decision history and effect are distinct

Schema 1.4 ADRs seal `decision_outcome` and immutable metadata while status and
effect-transition metadata remain mutable and validated. Schemas 1–1.3 retain
their exact payloads across new accepted-origin statuses. Focused digest and
schema tests pass.

### Milestone 2: Effect changes are previewed and atomic

`transition-adr` and `supersede-adr` output deterministic dry-run JSON and only
write with `--apply`. Legal transitions, explicit actor/reason, impact sets,
idempotence, and rollback are exercised by CLI tests.

### Milestone 3: Affected architecture pauses instead of locking history

Historical `depends_on`/`amends` edges remain valid. Recursive currentness
blocks new inputs, and affected active EPs expose
`architecture_review_required` and cannot archive. Documentation, indexes,
professional suites, and the canonical check pass.

## Concrete Steps

All commands run from `/Users/wangxiaowei1/x-otel/EngineeringPlan`.

1. Patch `engineering-execution-plan/assets/adr.md`, `scripts/epctl.py`, and
   `tests/test_epctl.py` together.
2. Run `python3 -B engineering-execution-plan/tests/test_epctl.py`; expect all
   lifecycle, legacy, plan, and existing tests to pass.
3. Patch `engineering-execution-plan/SKILL.md`, `references/adr.md`,
   `references/template.md`, `references/integrity.md`, DD-008, DD-010, and
   repository contracts.
4. Run `python3 -B -m unittest tests.test_repository_contracts`; expect exit 0.
5. Run `python3 -B engineering-execution-plan/scripts/epctl.py --repo . reindex`
   and `... validate`; expect zero errors.
6. Run `python3 -B scripts/check.py`; expect all integrity checks passed.

## Validation and Acceptance

- [x] Run `python3 -B engineering-execution-plan/tests/test_epctl.py`; expect all
  tests green, including schema 1.4, legacy digest stability, state matrix,
  preview/apply, impact, and archive blocking. Evidence:
  `artifacts/epctl-tests.txt`.
- [x] In a temporary repository, preview and apply `accepted → under_review →
  accepted`; preview writes nothing, apply records actor/reason, repeated apply
  is a no-op, and decision digest never changes. Evidence: focused CLI tests.
- [x] Reproduce an accepted amendment chain, transition the base under review,
  and observe the amendment plus active plan in `affected_*`; repository
  validation has no errors, new plans reject the chain, and completion is
  blocked. Evidence: `artifacts/transition-contract.txt`.
- [x] Run `python3 -B -m unittest tests.test_repository_contracts`; expect all
  public lifecycle/schema surfaces aligned. Evidence:
  `artifacts/repository-contracts.txt`.
- [x] Run `python3 -B engineering-execution-plan/scripts/epctl.py --repo .
  validate`; expect zero errors. Evidence: `artifacts/epctl-validate.txt`.
- [x] Run `python3 -B scripts/check.py`; expect exit 0 and `all integrity checks
  passed`. Evidence: `artifacts/check.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Transition commands are dry-run by default. Apply locks the repository and
recomputes the complete plan; a changed preflight aborts. ADR and generated
index originals are restored if post-write validation or index rebuilding
fails. Repeating the same terminal target with matching replacement is a no-op
preview/apply result; conflicting actor/reason does not rewrite history.

No bulk migration runs. New ADRs use schema 1.4; old decided ADRs acquire only
effect metadata when explicitly transitioned. A failed or abandoned review can
be reaffirmed with explicit authority. Retired and superseded decisions are
terminal and require a new ADR rather than destructive rollback. Transition
apply never touches application code or active plan bytes.

## Progress

- [ ] (2026-08-13T10:32:12Z) Plan created; research and fill every REQUIRED section before implementation.
- [x] (2026-08-13T10:38:00Z) ADR-016 accepted from explicit Repository Owner
  authorization; DD-010 and the full implementation contract recorded.
- [x] (2026-08-13T10:41:00Z) Filled all required planning, architecture,
  validation, and recovery sections before source edits.
- [x] (2026-08-13) Implemented Milestone 1 schema and payload semantics; schema
  1.4 and schema-1.3 transition digest tests pass.
- [x] (2026-08-13) Implemented Milestone 2 preview-first transition engine with
  explicit authority/reason, deterministic impact, lock, atomic writes, no-op,
  and rollback behavior.
- [x] (2026-08-13) Implemented Milestone 3 currentness, active-plan review
  behavior, documentation, and public command alignment.
- [x] (2026-08-13) Verified 53 execution-plan tests, 15 repository-contract
  tests, zero repository validation errors, `git diff --check`, and the full
  canonical check (`all integrity checks passed`).

## Surprises & Discoveries

- ADR-012 amends ADR-010, so the existing validator makes a legitimate
  supersession of ADR-010 invalidate ADR-012. This is the concrete regression
  fixture for historical-relation/current-effect separation.
- Schema 1.3 includes `updated` in its sealed payload. Legacy effect transitions
  must not modify that field; schema 1.4 deliberately removes lifecycle fields
  from the decision payload.

## Decision Log

- 2026-08-13, Repository Owner: authorized the concrete under-review,
  reaffirmation, retirement, supersession, and impact-reporting design with
  “好的 调整”.
- 2026-08-13, Codex: use schema 1.4 for clean outcome/effect separation while
  adding transition-only compatibility to schemas 1–1.3; no mass migration.
- 2026-08-13, Codex: keep affected active EP files unchanged. Surface a derived
  review requirement and block completion so lifecycle apply remains atomic and
  does not assume how each implementation should migrate.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

ADR history is no longer the same thing as permanent current effect. An owner
can preview and apply `under_review`, reaffirmation, retirement, or
supersession without rewriting the accepted decision. Impact reporting includes
constraints, transitively affected ADRs, and active EPs; new work rejects the
non-current graph while existing active plans remain structurally valid and
cannot complete until architecture review is resolved. Existing decided schema
1.1–1.3 payloads retain their digest.

No real existing ADR was transitioned as part of implementation. The new
capability is available for an explicit follow-up choice about which decision
to review or replace. Canonical validation retains three unrelated readiness
warnings for EP-006, EP-057, and EP-055; there are no errors.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

- Standard-library Python only; no new runtime dependency.
- ADR schema `1.4` fields: `decision_outcome`, `effect_changed_by`,
  `effect_changed`, and `effect_reason` in addition to existing metadata.
- CLI: `transition-adr ADR --to under_review|accepted|retired
  --decision-maker ACTOR --reason TEXT [--apply]`.
- CLI: `supersede-adr OLD --by NEW --decision-maker ACTOR --reason TEXT
  [--apply]`.
- JSON impact fields: `from_status`, `to_status`, `affected_constraints`,
  `affected_adrs`, `affected_active_plans`, `actions`, `warnings`, and
  `mode`.
- Status output exposes `current`, `review_reasons`, and active-plan
  `architecture_review_required` / completion blocker.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-056_reversible-adr-effect/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-13T10:32:12Z — Initial plan created.
- 2026-08-13 — Replaced all placeholders with the accepted lifecycle,
  compatibility, implementation, evidence, and recovery contract.
- 2026-08-13 — Completed lifecycle implementation, compatibility/docs updates,
  focused tests, repository validation, and canonical verification.
