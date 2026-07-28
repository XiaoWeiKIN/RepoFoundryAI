# Execution Plans

This file is the repository entry point and index for persistent ExecPlans. Each active ExecPlan must be self-contained and maintained as a living document.

## Protocol

- New plans live at `docs/exec-plans/active/ep-NNN_slug/EXECPLAN.md`.
- Completed or cancelled plans move to `docs/exec-plans/completed/`.
- IDs are monotonic across active, completed, this index and `.epctl/state.json`.
- `completed` requires checked acceptance, closed tasks, no open blockers and a retrospective.
- The managed tables below are projections. Rebuild them with `epctl reindex`; do not treat a missing row as proof that an artifact is absent.

## Active

<!-- EPCTL:ACTIVE:START -->
| ID | Title | Status | Updated | Path |
|---|---|---|---|---|
<!-- EPCTL:ACTIVE:END -->

## Completed

<!-- EPCTL:COMPLETED:START -->
| ID | Title | Status | Updated | Path |
|---|---|---|---|---|
| EP-001 | Add research and ADR lifecycle | completed | 2026-07-28 | [EXECPLAN](exec-plans/completed/ep-001_add-research-adr-lifecycle/EXECPLAN.md) |
<!-- EPCTL:COMPLETED:END -->
