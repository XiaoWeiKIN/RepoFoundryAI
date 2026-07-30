# Architecture Decisions

This file is the repository entry point and rebuildable index for ADRs. ADR
paths remain stable across proposed, accepted, rejected and superseded states.

## Protocol

- ADRs live at `docs/adr/adr-NNN_slug.md`.
- Agents may author proposed ADRs.
- Accept or reject an ADR only after explicit user or Decision Owner
  authorization.
- Accepted and rejected bodies are sealed. New evidence creates a superseding
  ADR.
- The managed table is a projection. Rebuild it with `epctl reindex`.

## Proposed

<!-- ADRCTL:ACTIVE:START -->
| ID | Title | Status | Updated | Research | Superseded By | Path |
|---|---|---|---|---|---|---|
<!-- ADRCTL:ACTIVE:END -->

## Decided

<!-- ADRCTL:COMPLETED:START -->
| ID | Title | Status | Updated | Research | Superseded By | Path |
|---|---|---|---|---|---|---|
| ADR-001 | Separate engineering research from execution planning | accepted | 2026-07-28 | ["R-001"] |  | [ADR](adr/adr-001_split-engineering-research.md) |
| ADR-002 | Add a Codex project documentation bootstrap | accepted | 2026-07-30 | [] |  | [ADR](adr/adr-002_codex-project-documentation-bootstrap.md) |
| ADR-004 | Separate workflow orchestration from execution planning | accepted | 2026-07-30 | [] |  | [ADR](adr/adr-004_separate-workflow-orchestration-from-execution-planning.md) |
| ADR-005 | Store engineering specifications in a separate repository | accepted | 2026-07-30 | [] |  | [ADR](adr/adr-005_external-engineering-specifications.md) |
| ADR-007 | Adopt RepoFoundry as the product identity | accepted | 2026-07-30 | [] |  | [ADR](adr/adr-007_repo-foundry-identity.md) |
| ADR-008 | Use RepoFoundry AI as the external brand | accepted | 2026-07-30 | [] |  | [ADR](adr/adr-008_repofoundry-ai-brand.md) |
<!-- ADRCTL:COMPLETED:END -->
