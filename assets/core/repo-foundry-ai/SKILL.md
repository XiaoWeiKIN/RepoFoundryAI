---
name: repo-foundry-ai
description: "Use the repository-local RepoFoundry AI Harness to plan, implement, validate, and migrate high-quality software changes with explicit evidence."
---

# RepoFoundry AI project workflow

Use this Skill when a task changes, reviews, diagnoses, or evolves this
repository. Treat repository state as the source of truth; do not depend on a
user-home installation path.

## Establish the Harness contract

1. Work from the repository root and read
   `docs/.engineering/harness.json` when it exists.
2. Run `repofoundry --repo . validate --harness` before a substantial change.
   If the Harness is absent, preview `repofoundry --repo . bootstrap` and ask
   the maintainer to select the intended adapters before applying it.
3. Read `docs/index.md`, `ARCHITECTURE.md`, and the applicable design or
   governance indexes. Preserve repository-owned customizations.
4. Preview every Harness or Specification mutation before passing `--apply`.
   Resolve conflicts explicitly; never overwrite an unknown managed path.

## Route engineering work

- Read `governance.profile` from the Harness. Missing policy means strict
  compatibility; strict stays Governed. Adaptive starts Explore.
- Explore covers bounded reversible inspection, experiments, local edits, and
  tests without persistent governance artifacts or a Spec receipt.
- Promote to Build for bounded production work. Keep a concise intent, path,
  acceptance, and compatibility contract; activate applicable Specs.
- Promote to Governed for public contracts, security, data, irreversible
  operations, reliability claims, release, or durable decisions. Use Research,
  ADR, ExecPlan, and sealed Benchmark only when their trigger applies.
- Use the case-study workflow only after implementation evidence exists.

Authority, destructive or external actions, security, data integrity, locked
content, sealed evidence, and honest verification remain hard in every mode.

When those professional workflows are available as separate Skills, invoke
them instead of reproducing their lifecycle rules here.

## Classify and activate Engineering Specifications

Before modifying a scoped path, use the canonical repository engine at
`.repo-foundry/engineering-specs/spec_router.py`:

1. Establish one stable adapter, session, and turn identity with `begin`.
2. Continue bounded Explore work, or use `classify --mode build|governed
   --reason <risk>` before crossing that boundary. Mode decreases are invalid.
3. In Build or Governed, inspect candidates and record applicable IDs or
   `--none` with a reason before mutation.
4. Keep activated requirements in context and run `audit` before completion.

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
