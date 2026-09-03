# Architecture Decisions

This file is the repository entry point and rebuildable index for ADRs. The
default Effective view contains only decisions that govern new work now. ADR
paths remain stable across proposed, accepted, rejected, under-review, retired,
and superseded states so history remains auditable.

## Protocol

- ADRs live at `docs/adr/adr-NNN_slug.md`.
- Agents may author proposed ADRs.
- Accept or reject an ADR only after explicit user or Decision Owner
  authorization.
- Decided bodies are sealed. New evidence may trigger an authorized review,
  retirement, or superseding ADR without rewriting decision history.
- Effective, Review Required, Historical, and constraint-amendment tables are
  derived projections. Rebuild or upgrade them with `epctl reindex` (or
  `epctl validate --fix-index`).

## Proposed

<!-- ADRCTL:ACTIVE:START -->
| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |
|---|---|---|---|---|---|---|---|
<!-- ADRCTL:ACTIVE:END -->

## Effective

<!-- ADRCTL:CURRENT:START -->
| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |
|---|---|---|---|---|---|---|---|
| ADR-001 | Separate engineering research from execution planning | accepted | partially amended | amended by ADR-004 | 2026-07-28 | ["R-001"] | [ADR](adr/adr-001_split-engineering-research.md) |
| ADR-002 | Add a Codex project documentation bootstrap | accepted | partially amended | depends on ADR-004; amended by ADR-011 | 2026-07-30 | [] | [ADR](adr/adr-002_codex-project-documentation-bootstrap.md) |
| ADR-004 | Separate workflow orchestration from execution planning | accepted | partially amended | amends ADR-001; amended by ADR-007 | 2026-07-30 | [] | [ADR](adr/adr-004_separate-workflow-orchestration-from-execution-planning.md) |
| ADR-005 | Store engineering specifications in a separate repository | accepted | current | depends on ADR-002 | 2026-07-30 | [] | [ADR](adr/adr-005_external-engineering-specifications.md) |
| ADR-007 | Adopt RepoFoundry as the product identity | accepted | partially amended | amends ADR-004; amended by ADR-008 | 2026-07-30 | [] | [ADR](adr/adr-007_repo-foundry-identity.md) |
| ADR-008 | Use RepoFoundry AI as the external brand | accepted | partially amended | amends ADR-007; amended by ADR-009 | 2026-07-30 | [] | [ADR](adr/adr-008_repofoundry-ai-brand.md) |
| ADR-009 | Align the root Skill name with RepoFoundry AI | accepted | current | amends ADR-008 | 2026-08-01 | [] | [ADR](adr/adr-009_align-repofoundry-ai-skill-name.md) |
| ADR-010 | Use one project-local Engineering Specs Router with trusted Hook enforcement | accepted | partially amended | depends on ADR-002; depends on ADR-005; amended by ADR-012 | 2026-08-03 | [] | [ADR](adr/adr-010_spec-task-activation-router.md) |
| ADR-011 | Separate the RepoFoundry core from Agent product adapters | accepted | current | depends on ADR-004; amends ADR-002 | 2026-08-04 | [] | [ADR](adr/adr-011_agent-neutral-harness-adapters.md) |
| ADR-012 | Separate Engineering Spec activation from Agent runtime adapters | accepted | current | depends on ADR-005; amends ADR-010 | 2026-08-04 | [] | [ADR](adr/adr-012_agent-neutral-spec-activation.md) |
| ADR-014 | Require semantic metadata for governed engineering artifacts | accepted | partially amended | amended by ADR-016 | 2026-08-04 | [] | [ADR](adr/adr-014_governed-artifact-metadata-contract.md) |
| ADR-015 | Adopt risk-adaptive Agent governance modes | accepted | current | depends on ADR-004; depends on ADR-012 | 2026-08-13 | [] | [ADR](adr/adr-015_risk-adaptive-agent-governance.md) |
| ADR-016 | Separate ADR history from current decision effect | accepted | current | amends ADR-014 | 2026-08-13 | [] | [ADR](adr/adr-016_reversible-decision-effect.md) |
| ADR-018 | Make technical Design Docs a first-class governed artifact | accepted | current | depends on ADR-001; depends on ADR-004; depends on ADR-014 | 2026-08-17 | [] | [ADR](adr/adr-018_first-class-technical-design-documents.md) |
| ADR-058 | Separate ADR history from lossless decision working context | accepted | partially amended | depends on ADR-014; depends on ADR-016; amended by ADR-059 | 2026-09-01 | [] | [ADR](adr/adr-058_lossless-adr-context-compaction.md) |
| ADR-059 | Add explicit focused materialization to ADR task capsules | accepted | current | amends ADR-058 | 2026-09-03 | [] | [ADR](adr/adr-059_focused-adr-context-materialization.md) |
<!-- ADRCTL:CURRENT:END -->

## Current constraint amendments

<!-- ADRCTL:AMENDMENTS:START -->
| Constraint | Amended By | Amendment | Path |
|---|---|---|---|
| ADR-014#C-001 | ADR-016 | Separate ADR history from current decision effect | [ADR](adr/adr-016_reversible-decision-effect.md) |
| ADR-014#C-004 | ADR-016 | Separate ADR history from current decision effect | [ADR](adr/adr-016_reversible-decision-effect.md) |
| ADR-058#C-006 | ADR-059 | Add explicit focused materialization to ADR task capsules | [ADR](adr/adr-059_focused-adr-context-materialization.md) |
<!-- ADRCTL:AMENDMENTS:END -->

## Review required

<!-- ADRCTL:REVIEW:START -->
| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |
|---|---|---|---|---|---|---|---|
<!-- ADRCTL:REVIEW:END -->

## Historical

<!-- ADRCTL:COMPLETED:START -->
| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |
|---|---|---|---|---|---|---|---|
<!-- ADRCTL:COMPLETED:END -->
