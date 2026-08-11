---
name: repo-foundry-ai
description: "Use the repository-local RepoFoundry AI Harness for repository changes, formal code reviews or defect diagnoses, Harness operations, or explicit RepoFoundry requests. Do not auto-trigger for ordinary read-only code explanation, navigation, call-chain tracing, or behavior summaries."
---

# RepoFoundry AI project workflow

Use this Skill when a task changes the repository, performs a formal review or
defect diagnosis, evolves an engineering contract, operates the Harness, or
explicitly requests RepoFoundry. Treat repository state as the source of truth;
do not depend on a user-home installation path.

## Choose the activation depth

- For ordinary read-only explanation, navigation, call-chain tracing, or a
  summary of existing behavior, do not start the full Harness workflow. Read
  only the code and repository documents needed to answer. Do not run Harness
  validation, activate Engineering Specifications, create governed artifacts,
  or require the five-label handoff solely for that analysis.
- For a formal code review, contract assessment, security or reliability
  analysis, or defect diagnosis, use the relevant repository contracts. Activate
  Engineering Specifications for code review or explicit Spec-conformance work,
  but do not bootstrap, migrate, or create Research/ExecPlan artifacts merely
  because the work is read-only.
- For implementation, refactoring, generated-file changes, Harness migration, or
  other repository mutation, establish the full contract below before writing.
  Escalate from read-only analysis only when the requested scope actually changes.

## Establish the Harness contract

1. Work from the repository root and read
   `docs/.engineering/harness.json` when it exists.
2. Run `repofoundry --repo . validate --harness` before a substantial change.
   If the Harness is absent, preview `repofoundry --repo . bootstrap` and ask
   the maintainer to select the intended adapters before applying it.
3. Read `docs/index.md`, `ARCHITECTURE.md`, and the applicable design or
   governance indexes. Preserve repository-owned customizations.
4. Preview every Harness or Specification mutation before passing `--apply`.
   Resolve conflicts explicitly; never overwrite an unknown managed path. If
   a Specification update reports `selection_decision.status=required`, show
   every candidate's ID, description, and dependencies, then ask the maintainer
   to choose the complete `--spec` set, `--required-only`, or
   `--keep-selection`. Do not apply or infer a selection before they answer.

## Route engineering work

- Use the repository's engineering research workflow when important facts,
  alternatives, or feasibility remain uncertain.
- Use sealed benchmark evidence when a decision depends on measured behavior.
- Use the execution-plan workflow for multi-step implementation, keeping its
  decisions, progress, validation evidence, and recovery notes current.
- Use the case-study workflow only after implementation evidence exists.
- Follow any applicable external Engineering Specifications locked under
  `docs/.engineering/`.

When those professional workflows are available as separate Skills, invoke
them instead of reproducing their lifecycle rules here.

## Activate Engineering Specifications

Before modifying a scoped path, performing a formal code review, or evaluating
explicit Spec conformance, use the canonical repository engine at
`.repo-foundry/engineering-specs/spec_router.py`:

1. Establish one stable adapter, session, and turn identity with `begin`.
2. Inspect path-matched choices with `candidates --path <path>` and decide Spec
   Applicability.
3. Use `requirements` for bounded cards, then `activate` exact direct IDs with
   one task-specific reason each; code resolves their context dependencies.
4. Use reasoned whole-Spec fallback only for legacy/migration/audit work, or
   `--none` with a reason when no Spec applies.
5. Keep the exact digest-verified capsule in context; run `rehydrate` after a
   context reset rather than summarizing normative text.
6. Run `audit` before completion so changed paths and the handoff are checked
   against the recorded receipt.

If the engine is absent, report that project Spec activation is unavailable;
do not silently claim that no Specification applies.

## Complete with evidence

For governed reviews or repository mutations, run validation proportional to
risk, including focused tests and the repository's canonical check when
present. Report the result using these labels so the activation decision
remains auditable:

- `Activated specifications:`
- `Activated requirements:`
- `Verification:`
- `Exceptions:`
- `Compatibility or migration:`

Do not mark an execution plan complete until required checks pass and its
evidence points at the verified revision.
