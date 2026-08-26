---
schema_version: "2.8"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-059
title: "Expose effective and historical ADR projections"
status: completed
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "Accepted ADR-016 and the current epctl implementation already establish the lifecycle semantics; the remaining gap is a deterministic generated projection and needs no new evidence."
adr_refs: ["ADR-014", "ADR-016"]
adr_constraint_refs: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008"]
adr_evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb"]
design_refs: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md"]
design_evidence: []
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: not_required
architecture_decision_gate_reason: "This work implements ADR-016's existing current-effect and index-observability constraints without choosing a new lifecycle or compatibility model."
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision: "workspace:2026-08-26-effective-adr-index"
verification_evidence: ["python3 -B scripts/check.py (exit 0; 35 Research, 9 Benchmark, 16 Design, 59 ExecPlan, 118 integration tests)", "temporary DataFox copy reindex and validate (44 ADRs; 0 errors; source status unchanged)", "git diff --check (exit 0)"]
archive_sha256: a5a64aad1bf0bbcc4fa1abd16250e08be0bebc13e33bb95e0e6ca47c35d18462
created: 2026-08-26
updated: 2026-08-26
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Expose effective and historical ADR projections

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Make the rebuildable ADR index answer the operational question “which decisions
govern new work now?” without deleting or rewriting decision history. After
this plan, `epctl reindex` separates proposed, effective, review-required, and
historical ADRs; effective rows identify partial amendments, and a generated
constraint-amendment table maps each currently amended `ADR-NNN#C-NNN` to the
current amendment ADR. `epctl status` exposes the same derived effect in JSON
and human-readable output.

An existing repository upgrades the projection by installing the new
RepoFoundry version and running `epctl reindex` (or `validate --fix-index`). The
operation changes only managed index regions. ADR paths, sealed decision
payloads, implementation code, and human-authored index content remain intact.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 1 — projection contract and focused tests.
- Current state: ADR-016 already implements reversible effect states and
  recursive currentness. `DECISIONS.md` still flattens every non-proposed ADR
  into `Decided`, while human `status` output omits the existing `current` and
  `review_reasons` data. No source implementation has been edited yet.
- Next action: add focused index/status and legacy-layout upgrade tests in
  `engineering-execution-plan/tests/test_epctl.py`, then implement the shared
  projection in `engineering-execution-plan/scripts/epctl.py`.
- Open question: none that changes the accepted route.

## Context and Orientation

`engineering-execution-plan/scripts/epctl.py` owns ADR discovery, recursive
`adr_currentness`, lifecycle transitions, generated indexes, repository
validation, and `status`. `engineering-execution-plan/assets/decisions-index.md`
is the seed for a new repository. Existing repositories preserve that file and
therefore need an in-place managed-region upgrade during `reindex`.

The current index uses `ADRCTL:ACTIVE` for proposed ADRs and
`ADRCTL:COMPLETED` for every decided ADR. This plan preserves those marker names
as the proposed and historical compatibility anchors, and adds managed
`CURRENT`, `AMENDMENTS`, and `REVIEW` regions. A current accepted ADR appears in
`CURRENT`; an accepted ADR whose dependency/amendment closure is non-current,
or an ADR explicitly `under_review`, appears in `REVIEW`; rejected, retired,
and superseded ADRs appear in `COMPLETED` under the Historical heading.

“Partially amended” is a derived display state, not a new ADR lifecycle state.
It means at least one recursively current accepted ADR names the decision in
`amends`. Structured `amends_constraints` entries are projected separately so
readers can locate the currently effective override without mentally folding
the full ADR chain.

DataFox is only a read-only compatibility corpus for this work. No command in
this plan writes `/Users/wangxiaowei1/x-otel/datafox`.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-016_reversible-decision-effect.md` | Authorizes immutable history plus reversible current effect and observable index/status behavior | Before projection semantics change |
| `docs/design-docs/reversible-adr-effect.md` | Defines currentness, lifecycle states, impact, and compatibility | Before implementation and verification |
| `docs/adr/adr-014_governed-artifact-metadata-contract.md` | Protects stable identity, attribution, and sealed payload boundaries | Before touching ADR-derived data |
| `engineering-execution-plan/scripts/epctl.py` | Canonical deterministic implementation | During every source milestone |
| `engineering-execution-plan/assets/decisions-index.md` | New-repository index seed | When changing layout |
| `engineering-execution-plan/references/adr.md` | Public lifecycle and operator contract | When changing user-visible behavior |
| `engineering-execution-plan/tests/test_epctl.py` | Compatibility and behavior evidence | Alongside each implementation edit |
| `python3 -B scripts/check.py` | Canonical repository gate | At final verification |

The implementation must preserve all decided ADR payload digests, avoid a new
ADR schema or lifecycle state, keep generated ordering deterministic, preserve
human text outside managed markers, and make repeated reindexing byte-stable.
Legacy two-table indexes remain readable; validation gives an actionable
upgrade signal and `reindex`/`validate --fix-index` performs the projection
upgrade without requiring Harness migration.

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `not_required`.
- Architecture compliance: `applicable`.
- ADR references: ["ADR-014", "ADR-016"].
- ADR constraint references: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008"].
- ADR evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb"].
- Design document references: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md"].
- Approved Design revision evidence: [].
- Architecture entrypoint: `docs/design-docs/index.md`.

Research is not required because the relevant facts are deterministic local
behavior: the lifecycle states, relation graph, index generator, validator, and
tests are all present in this repository. ADR-016 already selected the
history/effect separation; this plan does not compare a new architecture.

ADR-014 keeps identity, author/owner, decision authority, inputs, body, and
payload seals authoritative. A generated projection may read them but must not
mutate them. ADR-016 requires only recursively current accepted ADRs to govern
new work, makes retirement/supersession historical without fake rollback, and
requires affected accepted chains to surface review rather than disappear or
invalidate history. The effective index must therefore use
`adr_currentness`, not `status == accepted`, and must treat partial amendment as
a relationship projection rather than a state transition.

The negative consequence is a larger generated index and a richer public
projection contract. That cost is accepted because the default view becomes
smaller and current, while history stays one link away. No remaining unknown
can change the route; exact Markdown wording and helper decomposition are local
implementation choices.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-014#C-001 | Keep ADR identity and metadata in artifact files; generated rows only reference them. | Metadata and index projection tests plus canonical repository contracts. |
| ADR-014#C-002 | Make no Research/Benchmark evidence or raw artifact changes. | Existing Research/Benchmark suites in `scripts/check.py`. |
| ADR-014#C-003 | Do not add or infer transition authority; projections only report previously authorized state. | Lifecycle authority tests remain green and projection tests perform no ADR writes. |
| ADR-014#C-004 | Derive views without changing sealed decision or attribution fields. | Before/after payload digest assertions in lifecycle and reindex tests. |
| ADR-014#C-005 | Accept legacy ADR schemas and legacy two-table index layout without mass migration. | Legacy-layout upgrade, schema 1–1.3, and historical evidence tests. |
| ADR-014#C-006 | Treat `DECISIONS.md` as generated projection with no decorative authorship metadata. | Asset/reindex diff and repository contract tests. |
| ADR-016#C-001 | Read immutable `decision_outcome` separately from current effect and never rewrite it. | Status/index tests assert decision and effect independently. |
| ADR-016#C-002 | Keep transition preview/apply semantics unchanged; apply rebuilds the richer projection atomically. | Existing transition rollback/idempotence tests plus projected-table assertions. |
| ADR-016#C-003 | Put under-review and transitively non-current accepted ADRs in Review Required. | Amendment/dependency-chain projection tests. |
| ADR-016#C-004 | Put retired ADRs in Historical and never claim code rollback. | Retirement projection and unchanged-files assertions. |
| ADR-016#C-005 | Put superseded ADRs in Historical with their accepted current successor. | Supersession backlink and index tests. |
| ADR-016#C-006 | Show review-required effect and reasons in index/status without editing active EPs. | Human/JSON status and active-plan regression tests. |
| ADR-016#C-007 | Put only recursively current accepted ADRs in Effective and list current scoped amendments. | Currentness and constraint-amendment projection tests. |
| ADR-016#C-008 | Preserve old ADR bytes/digests and upgrade only managed index regions. | Legacy fixture, human-note preservation, and idempotent reindex tests. |

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

First add focused tests that create accepted base/amendment chains and exercise
review, retirement, rejection, and supersession. The tests will assert table
membership, partial-amendment links, constraint-level mappings, shared
human/JSON status fields, legacy layout conversion, human-note preservation,
and byte-stable repeated reindexing.

Then refactor the ADR index helpers in `epctl.py` around one derived projection
model. Keep generic EP/Research/Bugfix marker behavior unchanged. ADR-specific
layout normalization recognizes the old `ACTIVE/COMPLETED` form, inserts the
new managed regions, and relabels the old generated `Decided` heading as
Historical while leaving content outside the bounded managed layout untouched.
Rebuild and validation use the same category function so they cannot disagree.

Finally update the index asset and ADR operator documentation, regenerate this
repository's `docs/DECISIONS.md`, and run focused, repository-contract,
epctl-validation, read-only DataFox-copy compatibility, whitespace, and full
canonical checks.

## Milestones

### Milestone 1: One deterministic effect projection

`epctl` has one tested helper that classifies ADRs as proposed, effective,
review-required, or historical and derives `current`, `partially_amended`, and
constraint-amendment relationships. Focused tests demonstrate that lifecycle
state and graph currentness cannot diverge between index and status output.

### Milestone 2: Existing indexes upgrade without content loss

`reindex` converts a legacy two-table managed layout to the richer layout,
preserves human notes and ADR files, and is byte-stable on a second run.
Validation recognizes both layouts, reports the legacy layout as upgradeable,
and strictly validates category membership after conversion.

### Milestone 3: Public contract and distribution are verified

The seed asset and ADR references describe the effective/default view and the
one-command project adjustment. This repository and a temporary copy of the
DataFox documentation corpus reindex successfully; all focused and canonical
tests pass with no new errors.

## Concrete Steps

All commands run from `/Users/wangxiaowei1/x-otel/EngineeringPlan`.

1. Patch `engineering-execution-plan/tests/test_epctl.py`; run
   `python3 -B engineering-execution-plan/tests/test_epctl.py` and observe the
   new tests fail before implementation.
2. Patch `engineering-execution-plan/scripts/epctl.py` and
   `engineering-execution-plan/assets/decisions-index.md`; rerun the focused
   suite until all tests pass.
3. Patch `engineering-execution-plan/SKILL.md`,
   `engineering-execution-plan/references/adr.md`, and
   `engineering-execution-plan/references/integrity.md`; regenerate indexes
   with `python3 -B engineering-execution-plan/scripts/epctl.py --repo . reindex`.
4. Run repository contracts, `epctl validate`, a temporary DataFox-copy
   reindex/validate check, `git diff --check`, and `python3 -B scripts/check.py`.

## Validation and Acceptance

- [x] `python3 -B engineering-execution-plan/tests/test_epctl.py` passed all
  59 lifecycle, index, legacy-layout, and status tests.
- [x] `python3 -B -m unittest tests.test_repository_contracts` passed all 16
  public package contracts.
- [x] `python3 -B engineering-execution-plan/scripts/epctl.py --repo .
  validate` reported zero errors and only the five documented pre-existing or
  active-plan warnings.
- [x] A temporary DataFox copy reindexed 44 ADRs and validated with zero errors
  after its 16 MiB Benchmark evidence directory was copied. The projection
  contained 2 Proposed, 42 Effective, 68 current constraint amendments, 0
  Review Required, and 0 Historical rows. Source DataFox status was identical
  before and after the exercise.
- [x] `git diff --check` reported no whitespace errors.
- [x] `python3 -B scripts/check.py` exited 0 after 35 Research, 9 Benchmark, 16
  Design, 59 ExecPlan, and 118 integration tests and printed
  `all integrity checks passed`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

`reindex` remains deterministic and safe to repeat. It edits only marked
generated regions and `.epctl/state.json`; no ADR body or lifecycle metadata is
changed. Legacy-layout conversion is performed in memory and written through
the existing atomic writer. Transition commands already snapshot generated
indexes and restore them if post-write validation fails.

If an implementation attempt fails, restore only EP-059-owned source and
generated-index changes from the current diff; do not reset unrelated work.
Temporary compatibility repositories are created under the operating system's
temporary directory and left to normal system cleanup. No application-data
migration, Harness migration, or rollback of DataFox is part of this plan.

## Progress

- [x] (2026-08-26T01:19:52Z) Created EP-059 and filled its governed contract
  before source implementation.
- [x] (2026-08-26) Baseline `epctl validate` reported zero errors and the
  canonical repository check passed all 56 execution-plan and 118 integration
  tests, with only pre-existing plan/design warnings.
- [x] (2026-08-26) Filled the implementation, compatibility, architecture,
  validation, and recovery contract before editing source files.
- [x] (2026-08-26) Implemented one currentness/effect projection for indexes
  and status, legacy-layout upgrade, strict projection validation, current
  constraint amendment mapping, and deterministic repeated reindexing.
- [x] (2026-08-26) Updated the seed asset, public Skill/reference contract, and
  this repository's generated ADR index.
- [x] (2026-08-26) Verified a read-only DataFox-copy upgrade and passed every
  focused and canonical repository gate.

## Surprises & Discoveries

- 2026-08-26 — Retirement, under-review, supersession, immutable
  `decision_outcome`, recursive currentness, and effect-transition commands
  already exist under ADR-016/EP-056. The missing capability is projection and
  navigation, not the lifecycle state machine itself.
- 2026-08-26 — `status --json` already returns `current` and
  `review_reasons`, while human status and `DECISIONS.md` hide those fields.
  One shared projection can close both drift points without a schema change.
- 2026-08-26 — Once rows began carrying related ADR IDs, the old validator's
  “scan every ADR token in a table” logic misclassified relation targets as
  members. Restricting membership parsing to the first table cell fixed the
  ambiguity for every managed index.
- 2026-08-26 — A docs-only DataFox copy lacks Benchmark evidence referenced by
  completed EPs. Adding the repository's `benchmarks/` directory made the
  compatibility validation representative and reduced it from 25 unrelated
  errors to zero.

## Decision Log

- 2026-08-26, User: implementation must modify RepoFoundry itself; DataFox is
  not a write target and will be adjusted later through a tool upgrade.
- 2026-08-26, Codex: implement under accepted ADR-016 with no new ADR; this is
  completion of an existing observable-index constraint, not a new lifecycle
  choice.
- 2026-08-26, Codex: preserve `ADRCTL:ACTIVE` and
  `ADRCTL:COMPLETED` as compatibility anchors and add managed current,
  amendment, and review regions. First reindex upgrades the generated layout
  while preserving human content.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry now already has both halves of ADR retirement governance: the
existing preview/apply lifecycle command authorizes `under_review`, reaffirm,
`retired`, and supersession without rewriting the decided payload; the new
projection makes those effects usable at repository scale. `DECISIONS.md`
defaults to recursively current Effective ADRs, exposes partial amendments and
constraint-level overrides, isolates review-required chains, and keeps
rejected/retired/superseded ADRs as navigable history.

Existing repositories can adopt the behavior after installing a release that
contains this change by running `epctl reindex` or `validate --fix-index`.
Legacy headings and managed rows are upgraded in place, human notes survive,
and a second reindex is byte-stable. The DataFox source repository was not
modified; its temporary-copy exercise proved the future upgrade path against
44 real ADRs.

No ADR schema, lifecycle state, Harness schema, dependency, or automatic
age-based retirement was added. Automatic retirement would confuse age with
invalidity and bypass Decision Owner authority. Publishing/tagging a later
RepoFoundry distribution is the remaining delivery step; it is intentionally
separate because the current branch already contains other unreleased work
after 0.6.0.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

- Standard-library Python only; no new runtime dependency.
- Existing public commands remain: `reindex`, `validate --fix-index`, `status`,
  `transition-adr`, and `supersede-adr`.
- `status --json` keeps every existing field and adds derived effect and
  amendment fields; human status adds current effect and amendment columns.
- Generated ADR index markers retain `ACTIVE`/`COMPLETED` compatibility and add
  `CURRENT`, `AMENDMENTS`, and `REVIEW` managed regions.
- ADR schema remains 1.4 and ExecPlan schema remains 2.8. No product or Harness
  version bump is required merely to implement the unreleased source change.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-059_effective-adr-index-projection/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-26T01:19:52Z — Initial plan created.
- 2026-08-26 — Replaced all implementation-time placeholders with the bounded
  effective-index route, legacy conversion contract, ADR matrix, validation,
  and recovery plan.
- 2026-08-26 — Recorded the completed projection, documentation, DataFox-copy
  compatibility exercise, full verification evidence, and release boundary.
