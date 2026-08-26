# Architecture Decisions

This file is the repository entry point and rebuildable index for ADRs. The
default Effective view contains only decisions that govern new work now. ADR
paths remain stable across every lifecycle state so history stays auditable.

## Protocol

- New ADRs live at `docs/adr/adr-NNN_slug.md`; registered legacy architecture
  roots are projected here without moving their source files.
- Agents may author proposed ADRs.
- Accept or reject an ADR only after explicit user or Decision Owner
  authorization.
- Accepted and rejected bodies are sealed. New evidence creates an amending or
  superseding ADR; an authorized effect transition may place an accepted ADR
  under review or retire it without rewriting history.
- The managed tables are projections. Rebuild or upgrade them with
  `epctl reindex` (or `epctl validate --fix-index`).
- Effective lists recursively current accepted ADRs. Review Required contains
  explicit and transitive review work. Historical contains rejected, retired,
  and superseded decisions.

## Proposed

<!-- ADRCTL:ACTIVE:START -->
| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |
|---|---|---|---|---|---|---|---|
<!-- ADRCTL:ACTIVE:END -->

## Effective

<!-- ADRCTL:CURRENT:START -->
| ID | Title | Decision | Effect | Related ADRs | Updated | Research | Path |
|---|---|---|---|---|---|---|---|
<!-- ADRCTL:CURRENT:END -->

## Current constraint amendments

<!-- ADRCTL:AMENDMENTS:START -->
| Constraint | Amended By | Amendment | Path |
|---|---|---|---|
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
