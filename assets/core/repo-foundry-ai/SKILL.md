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

- Read `governance.profile` from the Harness. Missing policy means strict
  compatibility; strict stays Governed. Adaptive starts Explore.
- Explore covers bounded reversible inspection, experiments, local edits, and
  tests without persistent governance artifacts or a Spec receipt.
- Promote to Build for bounded production work. Keep a concise intent, path,
  acceptance, and compatibility contract; activate applicable Specs.
- Promote to Governed for public contracts, security, data, irreversible
  operations, reliability claims, release, or durable decisions. Use Research,
  Design Package, ADR, ExecPlan, and sealed Benchmark only when their trigger
  applies. Research establishes evidence; Design specifies how the system works;
  ADR authorizes durable choices; ExecPlan governs delivery.
- Route ADR corpus reduction to the Engineering Execution Plan workflow. Semantic
  consolidation remains an authorized ADR lifecycle change; physical compaction
  may only use its explicit lossless terminal History Pack preview/apply and exact
  unpack contract. A Harness upgrade never packs ADRs automatically.
- Use the case-study workflow only after implementation evidence exists.

Authority, destructive or external actions, security, data integrity, locked
content, sealed evidence, and honest verification remain hard in every mode.

When those professional workflows are available as separate Skills, invoke
them instead of reproducing their lifecycle rules here.

## Classify and activate Engineering Specifications

Before modifying a scoped path, performing a formal code review, or evaluating
explicit Spec conformance, use the canonical repository engine at
`.repo-foundry/engineering-specs/spec_router.py`:

1. Establish one stable adapter, session, and turn identity with `begin`.
2. Continue bounded Explore work, or use `classify --mode build|governed
   --reason <risk>` before crossing that boundary. Mode decreases are invalid.
3. In Build or Governed, inspect path-matched choices with `candidates --path <path>` and decide Spec
   Applicability.
4. Use `requirements` for bounded cards, then `activate` exact direct IDs with
   one task-specific reason each; code resolves their context dependencies.
5. Use reasoned whole-Spec fallback only for legacy/migration/audit work, or
   `--none` with a reason when no Spec applies.
6. Keep the exact digest-verified capsule in context; run `rehydrate` after a
   context reset rather than summarizing normative text.
7. Run `audit` before completion so changed paths and the handoff are checked
   against the recorded receipt.

If the engine is absent, report that project Spec activation is unavailable;
do not silently claim that no Specification applies.

## Complete with evidence

Run validation proportional to risk. Explore reports outcome, verification,
and unresolved risk in normal prose. Build and Governed use these labels so an
activation decision remains auditable:

- `Activated specifications:`
- `Activated requirements:`
- `Verification:`
- `Exceptions:`
- `Compatibility or migration:`

Do not mark an execution plan complete until required checks pass and its
evidence points at the verified revision.
