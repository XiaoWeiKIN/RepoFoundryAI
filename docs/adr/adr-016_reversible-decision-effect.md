---
schema_version: "1.3"
metadata_schema: "1"
artifact_type: adr
id: ADR-016
title: "Separate ADR history from current decision effect"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-014"]
amends_constraints: ["ADR-014#C-001", "ADR-014#C-004"]
design_refs: ["docs/design-docs/reversible-adr-effect.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicitly instructed '好的 调整' for the concrete reversible ADR-effect proposal in the current conversation on 2026-08-13)"
decided: "2026-08-13T10:32:05Z"
payload_sha256: 448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb
created: 2026-08-13
updated: 2026-08-13
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Separate ADR history from current decision effect

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

RepoFoundry seals accepted ADR content so later work cannot rewrite what was
authorized. The same artifact `status`, however, is also used as the current
constraint switch. `depends_on` and `amends` validation requires every target
of an accepted ADR to remain accepted. Together these rules turn historical
integrity into practical irreversibility: an owner can discover that an
implemented ADR is harmful, yet suspending or superseding it can invalidate
dependent ADRs and active plans, so Agents continue implementing the known-bad
constraint.

ADR-010 and ADR-012 expose the concrete failure mode. ADR-012 historically
amends ADR-010. Marking ADR-010 superseded makes ADR-012 invalid under the
current relationship validator even though the historical statement “ADR-012
amended ADR-010” remains true. The repository needs a first-class way to stop
treating a decision as current without falsifying its history or silently
rewriting implementation.

## Decision Drivers

- Preserve the exact accepted/rejected decision payload and authority record.
- Let an authorized owner suspend, reaffirm, retire, or replace a decision.
- Prevent new work from blindly consuming a questioned constraint.
- Keep a deliberate lifecycle transition repository-valid even when accepted
  ADRs or active plans historically reference the affected decision.
- Expose transitive impact before mutation and avoid implicit plan/code edits.
- Preserve old ADR schemas and archived ExecPlan evidence.
- Require explicit authority and a non-empty reason for every effect change.

## Research Evidence

No new Research package is required. The problem is demonstrated directly by
the repository's validator and the accepted ADR-010/ADR-012 relationship. The
Repository Owner identified the undesirable behavior and explicitly authorized
the proposed under-review, reaffirm, retirement, and supersession route in the
current conversation. DD-010 records the state, impact, compatibility, and
command design.

## Considered Options

### Keep accepted ADRs permanently effective

This preserves simple validation but knowingly forces obsolete constraints and
makes revisit triggers largely ceremonial.

### Edit or delete the old ADR

This removes the immediate constraint but destroys the evidence explaining why
the implementation exists and who authorized it.

### Require a replacement ADR before any old constraint can stop

This works for known replacements but cannot safely pause a harmful decision
while alternatives are still being evaluated, nor retire a decision that needs
no successor.

### Separate immutable decision history from reversible current effect

Keep the original decision sealed, add explicit effect states and authority,
derive transitive review impact, and make all effect changes preview-first.

## Decision Outcome

Adopt separate decision-history and current-effect semantics. It retains audit
integrity while making architectural correction a supported operation rather
than a repository-invalidating workaround.

## Decision Statement

RepoFoundry will keep an ADR's authorized decision payload immutable while
allowing explicitly authorized, previewed transitions of its current effect
through accepted, under-review, retired, and superseded states.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | decided ADR payload | Preserve the original decision outcome, authority, inputs, constraints, and body across every effect transition. | Cross-schema payload-digest transition tests |
| C-002 | must | ADR effect changes | Require an explicit decision authority, non-empty reason, legal state transition, deterministic preview, and atomic apply. | `transition-adr` and `supersede-adr` contract tests |
| C-003 | must | under-review ADR | Suspend the ADR and any transitively dependent/amending ADR from new current architecture input without changing historical relation validity. | Relationship/currentness tests using an amendment chain |
| C-004 | must | retired ADR | Remove its constraints from current governance without claiming implementation rollback or requiring a replacement ADR. | Retirement impact and new-EP rejection tests |
| C-005 | must | superseded ADR | Link to an accepted current replacement while retaining the old decision and historical consumers. | Supersession backlink and archived-evidence tests |
| C-006 | must | active ExecPlans affected by a non-current ADR | Surface `architecture_review_required` and block completion while keeping the repository and plan structurally valid for revision. | Active-plan status, validation-warning, and archive-block tests |
| C-007 | must | new ExecPlans and current scoped amendments | Consume only ADRs whose own state and `depends_on`/`amends` closure are current. | New-EP and amendment-selection rejection tests |
| C-008 | must | legacy decided ADR schemas | Preserve schemas 1–1.3 and their existing payload digests during effect transitions; do not mass-rewrite sealed history. | Legacy fixture and repository validation suites |

## Consequences

### Positive

- Owners can stop a known-bad constraint before choosing its replacement.
- Revisit triggers become executable lifecycle behavior.
- Historical ADR relations no longer prevent correction.
- Active work identifies architectural uncertainty instead of silently
  continuing or making the entire repository invalid.

### Negative

- “Current ADR” becomes a derived graph property rather than `status ==
  accepted` alone.
- Lifecycle commands and status output carry more state and tests.
- Implemented behavior may temporarily differ from current architecture after
  review or retirement; an explicit migration EP or technical debt item must
  close that gap.

### Compatibility and migration

- New ADRs use schema 1.4 with an immutable `decision_outcome` and mutable
  effect metadata.
- Existing ADRs gain lifecycle fields only when transitioned. Their body,
  decision inputs, authority, and sealed digest remain unchanged.
- Existing `supersede-adr` becomes preview-first and requires explicit
  transition authority and reason.

## Confirmation

- Unit tests cover every legal and illegal transition, preview/apply
  idempotence, rollback, payload stability, impact discovery, and index output.
- A regression fixture reproduces ADR-012 amending ADR-010 and proves review or
  retirement reports impact rather than invalidating the sealed documents.
- ExecPlan tests prove affected active plans cannot archive and new plans cannot
  use non-current input, while completed plans still verify historical digests.
- `python3 -B scripts/check.py` remains the canonical repository gate.

## Revisit Triggers

- Repositories need concurrent or time-bounded effect states that cannot be
  represented by one current status.
- Policy requires cryptographically chained lifecycle events independent of
  repository/VCS history.
- Real usage shows that transitive review propagation is too broad and a safe,
  constraint-level effect model is required.
- Automated code rollback becomes reliable enough to be coupled to retirement
  without inferring destructive authority.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-014"]
- Amended constraints: ["ADR-014#C-001", "ADR-014#C-004"]
- Design documents: ["docs/design-docs/reversible-adr-effect.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-08-13T10:30:09Z — Proposed ADR created.
