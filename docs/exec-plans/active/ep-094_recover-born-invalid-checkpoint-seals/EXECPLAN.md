---
schema_version: "2.8"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-094
title: "Recover born-invalid checkpoint seals from Git evidence"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "DataFox EP-091 CP-001 is reproduced byte-for-byte at its introducing Git commit and has no later source change; the failure and recovery evidence are already bounded."
adr_refs: []
adr_constraint_refs: []
adr_evidence: []
design_refs: ["docs/design-docs/repo-foundry-versioning-and-migrations.md", "docs/design-docs/engineering-workflow-packaging.md"]
design_evidence: []
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: not_required
architecture_decision_gate_reason: "The existing immutable-checkpoint contract and EP-057 repository-owned historical-evidence pattern already fix the route: Git is an explicit one-time source, recovery evidence is committed, and normal validation stays offline and fail-closed."
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-09-03
updated: 2026-09-03
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Recover born-invalid checkpoint seals from Git evidence

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry must recover a checkpoint whose seal was already wrong in the Git
commit that introduced the checkpoint, without rewriting the immutable
checkpoint or weakening validation for later edits. The observable result is a
preview-first command that proves the exact current checkpoint bytes were added
at an ancestor commit, records a sealed repository-owned recovery receipt, and
lets ordinary `epctl validate` succeed without Git only while those exact bytes
and receipt remain unchanged.

DataFox EP-091 CP-001 is the compatibility case. Commit
`e73ac75fe5c4e566a3c3d65a3b18bb4f75e243e1` introduced its current bytes with a
stored digest of `2f34ff8c...`, while canonical schema-1.2 validation computes
`3f1bcb25...`. The checkpoint has not changed since. After RepoFoundry is
released and DataFox upgrades, a recovery receipt will remove only that
birth-time mismatch; any additional checkpoint defect or later byte change
will still fail closed.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — finish the authorized DataFox ADR transitions.
- Current state: RepoFoundry 0.8.2 is released and installed; DataFox is upgraded,
  CP-001 has a verified recovery receipt, EP-092 is structurally valid, ADR-038
  is accepted, and ADR-052/053/054 are superseded by ADR-055. ADR-051 apply
  rolled back atomically because the validator did not support the existing
  `ADR-010 -> ADR-051 -> ADR-055` supersession chain.
- Next action: publish the additive 0.8.3 chain-validation fix, upgrade DataFox,
  supersede ADR-051, and retarget the storage Decision View to ADR-055.
- Open questions: none that can change the route; file naming and JSON field
  names remain bounded implementation details and will be fixed by tests.

## Context and Orientation

Schema-1.2 checkpoints are Markdown history files under an ExecPlan's
`history/` directory. `payload_sha256` is the SHA-256 of the whole checkpoint
after replacing that field with an empty value. `validate_checkpoint()` in
`engineering-execution-plan/scripts/epctl.py` currently treats every mismatch
as post-seal mutation.

A *born-invalid checkpoint* is narrower: the exact current bytes, including the
bad stored digest, must be the bytes at the commit that introduced the exact
repository-relative checkpoint path; that commit must be a full Git commit ID
and an ancestor of `HEAD`. A *recovery receipt* is immutable JSON under
`docs/.epctl/checkpoint-recoveries/EP-NNN/CP-NNN/sha256-<document>.json`. It
records the checkpoint path and exact document digest, stored and computed
payload digests, Git commit, blob and commit-time evidence, attesting actor,
reason, and a canonical receipt digest.

Git participates only in `register-checkpoint-recovery`. Normal repository
validation discovers and validates receipts from repository files, then allows
the one matching payload mismatch for the exact checkpoint bytes. The receipt
does not replace the checkpoint, repair its digest, mask structural errors, or
authorize a different checkpoint revision.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `engineering-execution-plan/scripts/epctl.py` | Owns checkpoint creation, seal validation, repository locks, immutable registries and CLI routing | Before every implementation change |
| `engineering-execution-plan/tests/test_epctl.py` | Defines preview/apply, Git, tamper, portability and compatibility behavior | Before and during implementation |
| `engineering-execution-plan/references/checkpoints.md` | Requires sealed checkpoint history to remain immutable | Before changing validation semantics |
| `engineering-execution-plan/references/integrity.md` | Requires repository-owned, offline, fail-closed evidence | Before defining the receipt boundary |
| `docs/exec-plans/completed/ep-057_historical-adr-revision-evidence/EXECPLAN.md` | Proven pattern for one-time Git import and offline historical evidence | Before implementing storage and recovery |
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Preview-first migration, compatibility and release contract | Before changing public commands or version |
| `docs/design-docs/engineering-workflow-packaging.md` | Keeps checkpoint lifecycle in the standalone execution-plan Skill | Before choosing module ownership |
| `scripts/check.py` | Single repository-wide verification entrypoint | Before completion and release |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `not_required`.
- Architecture compliance: `applicable`.
- ADR references: [].
- ADR constraint references: [].
- ADR evidence: [].
- Design document references: ["docs/design-docs/repo-foundry-versioning-and-migrations.md", "docs/design-docs/engineering-workflow-packaging.md"].
- Approved Design revision evidence: [].
- Architecture entrypoint: `docs/design-docs/index.md`.

Research is not required. DataFox provides a fully reproduced case: its current
CP-001 bytes match the file at the path-introducing ancestor commit, every
released validator computes the same canonical digest, and Git history contains
no later checkpoint change. No experiment or external source can change the
implementation route.

No new architecture decision is required. The existing checkpoint contract
already forbids rewriting sealed history, and EP-057 already selects the only
compatible recovery shape: Git is an explicit one-time evidence adapter,
validated evidence becomes repository-owned, and routine validation remains
offline. Directly fixing the stored digest would falsify history; accepting any
ancestor version without proving path introduction would weaken integrity.

Architecture compliance remains applicable. Registration must be preview-first,
atomic and idempotent; the target is content-addressed and conflict-closed;
normal validation cannot require `.git`; only a schema-1.2 checkpoint whose sole
error is the payload mismatch is eligible; exact source-byte, path, commit,
blob, actor and reason evidence is retained. The Harness schema, Core, adapters,
governance policy and activation protocol do not change. The distribution
advances from 0.8.1 to 0.8.2.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| docs/design-docs/repo-foundry-versioning-and-migrations.md | Add a preview-first explicit registration command, content-addressed immutable receipts, conflict detection and offline post-registration validation; publish 0.8.2 without changing Harness component versions. | Focused preview/apply/idempotence/wrong-commit/tamper/no-Git tests, installer checks and the canonical repository check. |
| docs/design-docs/engineering-workflow-packaging.md | Keep checkpoint recovery state and validation wholly inside independently installable `engineering-execution-plan`; do not move it into `foundryctl`, Harness state or an Agent adapter. | Standalone `test_epctl.py`, copied-package contract tests and `scripts/check.py`. |

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

First, add tests that build a valid checkpoint, deliberately write the wrong
digest before its first Git commit, and exercise the public recovery command.
The tests will prove preview has no side effects, apply creates one immutable
receipt, repeated apply preserves it, normal validation works with Git removed,
and wrong/non-ancestor commits, pre-existing paths, non-matching bytes,
additional checkpoint errors, receipt tampering and later checkpoint edits all
fail closed.

Second, add a narrow receipt store and validator to `epctl.py`. Registration
will resolve an exact plan/checkpoint, validate raw UTF-8 bytes and schema 1.2,
confirm the payload mismatch is the only checkpoint error, prove the supplied
full commit is an ancestor and introduced the exact path with the same blob
bytes, and generate a canonical self-digested JSON receipt. Repository
validation will validate the entire store and suppress only the matching seal
mismatch.

Third, document the command, storage layout, trust boundary and recovery
limitations in the Skill and checkpoint/integrity/versioning references. Update
public examples, tests, `VERSION` and release notes to 0.8.2 without changing
Harness schema or component versions.

Finally, run focused and canonical checks, publish and install 0.8.2, upgrade
the DataFox Harness, preview/apply the EP-091 CP-001 receipt, repair EP-092's
structural blocker fields without overwriting unrelated work, accept ADR-038,
and preview/apply ADR-055 supersession of ADR-051 through ADR-054. Rebuild
Decision Views and run DataFox validation after each lifecycle stage.

During the DataFox apply, preserve chained supersession instead of flattening
history. Permit an immediate replacement to have any accepted-origin lifecycle
status, require every backlink, reject cycles, and keep current contexts anchored
only at an accepted/current terminal ADR. Publish this additive validator fix as
0.8.3 before retrying the rolled-back ADR-051 transition.

## Milestones

### Milestone 1: Register and validate exact born-invalid evidence

`epctl.py` exposes `register-checkpoint-recovery EP-NNN CP-NNN` with required
`--from-git-commit`, `--attested-by` and `--reason`, plus optional `--apply`.
Focused tests prove the Git introduction predicate, exact-byte boundary,
receipt integrity and selective validation behavior.

### Milestone 2: Publish a portable 0.8.2 contract

Skill/reference/design documentation and examples explain why checkpoint bytes
remain unchanged and why Git is not a runtime dependency. `VERSION` and release
documentation identify the additive 0.8.2 capability. Focused suites and
`python3 -B scripts/check.py` pass with zero errors.

### Milestone 3: Apply the recovery and ADR transitions in DataFox

The installed 0.8.3 distribution upgrades DataFox. A committed receipt makes
EP-091 CP-001 valid offline. EP-092 is structurally valid, ADR-038 is accepted
by Wangxiaowei1, and ADR-051 through ADR-054 are superseded by current accepted
ADR-055 with no active-plan consumer left stale. DataFox's source checkpoint
and unrelated dirty files remain byte-for-byte untouched.

## Concrete Steps

From `/Users/wangxiaowei1/x-otel/EngineeringPlan-checkpoint-recovery`:

    python3 -B -m unittest engineering-execution-plan.tests.test_epctl
    python3 -B scripts/check.py

Expected: focused tests and the canonical check exit zero; only documented
pre-existing warnings may remain.

From `/Users/wangxiaowei1/x-otel/datafox` after installing 0.8.2:

    repofoundry --repo . upgrade --to 0.8.2
    repofoundry --repo . upgrade --to 0.8.2 --apply
    epctl --repo . register-checkpoint-recovery EP-091 CP-001 \
      --from-git-commit e73ac75fe5c4e566a3c3d65a3b18bb4f75e243e1 \
      --attested-by Wangxiaowei1 \
      --reason "CP-001 was introduced with this invalid seal and has not changed"
    epctl --repo . register-checkpoint-recovery EP-091 CP-001 \
      --from-git-commit e73ac75fe5c4e566a3c3d65a3b18bb4f75e243e1 \
      --attested-by Wangxiaowei1 \
      --reason "CP-001 was introduced with this invalid seal and has not changed" --apply
    epctl --repo . validate

Expected: preview reports one `create` without changing files; apply writes one
content-addressed receipt; the checkpoint seal mismatch disappears while
unrelated validation findings remain visible until separately corrected.

## Validation and Acceptance

- [x] From the RepoFoundry worktree, run the focused checkpoint recovery tests;
  expect preview/apply, introduction proof, offline validation and all fail-closed
  cases to pass. Evidence: `docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/artifacts/focused-tests.txt`.
- [x] Run `python3 -B scripts/check.py`; expect zero errors and unchanged
  generated projections after regeneration. Evidence: `artifacts/repository-check.txt`.
- [x] Publish and reinstall RepoFoundry AI 0.8.2; expect the release tag to
  resolve to the merged source commit and the immutable local `current` link to
  select 0.8.2. Evidence: `artifacts/release-notes.md`.
- [ ] Publish and reinstall RepoFoundry AI 0.8.3; expect chained supersession and
  cycle tests plus the canonical check to pass. Evidence:
  `artifacts/release-notes-0.8.3.md`.
- [ ] In DataFox, preview/apply the EP-091/CP-001 receipt and validate once with
  Git available and once from a copied tree without `.git`; expect no checkpoint
  seal error and no checkpoint byte diff. Evidence: `artifacts/datafox-compatibility.txt`.
- [ ] In DataFox, accept ADR-038 and supersede ADR-051 through ADR-054 by ADR-055
  using Wangxiaowei1's explicit authority; expect current/historical indexes and
  Decision Views to resolve consistently and repository validation to report no
  lifecycle error. Evidence: `artifacts/datafox-adr-transitions.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Preview performs no directory, lock, receipt or index write. Apply runs under the
repository lock, writes the target atomically, validates it, and removes only a
newly created receipt on post-write failure. Repeating the same registration is
a no-op; an existing target with different bytes is a conflict. Receipts never
modify checkpoints and can be reviewed as ordinary Git changes.

If implementation validation fails, revert only this branch's source and EP
changes; do not touch the dirty DataFox workspace. If release or installation
fails, the immutable 0.8.2 release and current symlink remain the rollback
point. If DataFox apply fails, the command must remove the newly created receipt
and leave the checkpoint unchanged. ADR lifecycle commands retain their
existing preview/snapshot/rollback behavior and are applied one old ADR at a
time so a failed transition has an exact boundary.

## Progress

- [x] (2026-09-03T07:24:46Z) Plan created and routed through existing immutable-history architecture inputs.
- [x] (2026-09-03T07:24:59Z) Reproduced the DataFox birth-time digest mismatch and selected the EP-057 repository-owned evidence pattern.
- [x] (2026-09-03T07:48:22Z) Implemented and verified the recovery receipt contract; 72 ExecPlan tests and the canonical repository check pass.
- [x] (2026-09-03) Published and installed RepoFoundry AI 0.8.2.
- [x] (2026-09-03) Upgraded DataFox, registered CP-001 recovery,
  repaired EP-092, accepted ADR-038, and superseded ADR-052/053/054.
- [ ] Publish and install RepoFoundry AI 0.8.3, then complete ADR-051 and the
  Decision View retargeting.

## Surprises & Discoveries

- 2026-09-03 — DataFox CP-001 was introduced at commit
  `e73ac75fe5c4e566a3c3d65a3b18bb4f75e243e1` with the same bytes present now;
  every RepoFoundry version computes the same different canonical digest. This
  is producer-invalid history, not later tampering or a 0.8.1 regression.
- 2026-09-03 — ADR-051 already supersedes legacy ADR-010. Attempting to
  supersede ADR-051 by ADR-055 exposed a one-level validator assumption; the
  atomic command restored ADR-051, ADR-055 and generated indexes exactly.

## Decision Log

- 2026-09-03 — Preserve the checkpoint and add an external, content-addressed
  recovery receipt. Rewriting the digest would falsify sealed history; runtime
  dependence on Git would break exported and source-package validation.
- 2026-09-03 — Require the supplied commit to be an ancestor, to introduce the
  exact path, and to contain the exact current bytes. Merely finding matching
  bytes in any Git object is insufficient evidence that the seal was invalid at
  birth.
- 2026-09-03 — Keep the receipt keyed by logical EP/CP identity and document
  digest rather than its current active/completed path. This preserves offline
  validation when a recovered plan is later archived while retaining the
  original Git path as introduction evidence.
- 2026-09-03 — Preserve every immediate supersession edge rather than rewriting
  ADR-010 to point directly at ADR-055. Accepted-origin historical states remain
  structurally valid, cycles fail closed, and only the terminal accepted/current
  ADR can seed new Decision contexts.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

<!-- REQUIRED_AT_COMPLETION: Compare the result with the original purpose. Record completed behavior, evidence, gaps, remaining work, and lessons. -->

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No third-party dependency is added. The implementation uses Python standard
library JSON, SHA-256, subprocess and atomic file helpers already present in
`epctl.py`, plus the user's existing Git executable only during explicit
registration.

Public interface:

    register-checkpoint-recovery EP-NNN CP-NNN
      --from-git-commit <full-commit-id>
      --attested-by <actor>
      --reason <non-empty-reason>
      [--apply]

The receipt schema is version 1 and uses a canonical JSON SHA-256 with
`receipt_sha256` blanked during calculation. Repository validation must remain
compatible with repositories that have no recovery directory.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/EXECPLAN.md`
- Focused tests: `docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/artifacts/focused-tests.txt`
- Canonical check: `docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/artifacts/repository-check.txt`
- DataFox preview: `docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/artifacts/datafox-compatibility.txt`
- Release notes: `docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/artifacts/release-notes.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-09-03T07:24:46Z — Initial plan created.
- 2026-09-03T07:48:22Z — Updated the current snapshot, verification evidence,
  archive-path compatibility decision and release handoff after implementation.
