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
| EP-006 | Migrate EngineeringWorkflow to RepoFoundry AI | active | 2026-08-04 | [EXECPLAN](exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md) |
<!-- EPCTL:ACTIVE:END -->

## Completed

<!-- EPCTL:COMPLETED:START -->
| ID | Title | Status | Updated | Path |
|---|---|---|---|---|
| EP-001 | Add research and ADR lifecycle | completed | 2026-07-28 | [EXECPLAN](exec-plans/completed/ep-001_add-research-adr-lifecycle/EXECPLAN.md) |
| EP-002 | Split engineering research from execution planning | completed | 2026-07-28 | [EXECPLAN](exec-plans/completed/ep-002_split-engineering-research/EXECPLAN.md) |
| EP-003 | Restructure EngineeringWorkflow skill ownership | completed | 2026-07-30 | [EXECPLAN](exec-plans/completed/ep-003_restructure-engineering-workflow/EXECPLAN.md) |
| EP-004 | Add Engineering Spec management to Harness bootstrap | completed | 2026-07-30 | [EXECPLAN](exec-plans/completed/ep-004_add-spec-management/EXECPLAN.md) |
| EP-005 | Externalize engineering specifications and fetch by Git revision | completed | 2026-07-30 | [EXECPLAN](exec-plans/completed/ep-005_externalize-engineering-specifications/EXECPLAN.md) |
| EP-007 | Pin Engineering Specification releases | completed | 2026-08-02 | [EXECPLAN](exec-plans/completed/ep-007_versioned-spec-releases/EXECPLAN.md) |
| EP-008 | Let users explicitly select installed Engineering Specs | completed | 2026-08-02 | [EXECPLAN](exec-plans/completed/ep-008_explicit-spec-selection/EXECPLAN.md) |
| EP-009 | Enforce Engineering Spec task activation | completed | 2026-08-03 | [EXECPLAN](exec-plans/completed/ep-009_enforce-spec-task-activation/EXECPLAN.md) |
| EP-010 | Implement Agent-neutral Harness and Engineering Spec adapters | completed | 2026-08-04 | [EXECPLAN](exec-plans/completed/ep-010_implement-agent-neutral-adapters/EXECPLAN.md) |
| EP-011 | Add one-command RepoFoundry AI install and upgrade | completed | 2026-08-04 | [EXECPLAN](exec-plans/completed/ep-011_one-command-install-upgrade/EXECPLAN.md) |
<!-- EPCTL:COMPLETED:END -->
