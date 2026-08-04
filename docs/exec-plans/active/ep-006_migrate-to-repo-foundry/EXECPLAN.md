---
schema_version: "2.5"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-006
title: "Migrate EngineeringWorkflow to RepoFoundry AI"
status: active
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-004", "ADR-007", "ADR-008", "ADR-009"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/repo-foundry-system.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-07-30
updated: 2026-08-04
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Migrate EngineeringWorkflow to RepoFoundry AI

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Present the distribution externally as **RepoFoundry AI**, The Agent-Native
Engineering System, while preserving `RepoFoundry` as its technical basename.
A user should immediately understand that the system turns a repository into an
AI-ready engineering environment, then be able to install `$repo-foundry-ai`, run
`scripts/foundryctl.py`, bootstrap a target repository, and see new Harness and
Spec manifests owned by `repo-foundry`.

The completed repository will also contain an original RepoFoundry AI icon and
a clear system model: Inventory discovers the repository, Scaffold fills
missing entrypoints, the Repository Harness persists constraints and
validation, and professional Skills operate above that environment.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 4 — validated implementation ready for review.
- Current state: ADR-009 amends ADR-008 after the Repository Owner explicitly
  requested the Skill and project names be synchronized. Public Skill surfaces
  now use `$repo-foundry-ai`; CLI, environment variable, manifest owner, and
  state paths remain stable. Skill validation and the canonical repository
  check pass, including 109 tests and zero repository validation warnings.
- Next action: commit and push the synchronized naming change to the amended PR
  branch. The external GitHub repository rename remains a separate operation.
- Open questions: the external GitHub repository rename is intentionally
  outside this local implementation.

## Context and Orientation

The repository root is an installable aggregation Skill. `SKILL.md`,
`agents/openai.yaml`, `evals/evals.json`, `scripts/foundryctl.py`, and
`scripts/spec_manager.py` implement its current public contract.
`engineering-benchmark/`, `engineering-research/`,
`engineering-execution-plan/`, and `engineering-case-study/` are independent
capability Skills and keep their names.

`scripts/foundryctl.py` bootstraps a Repository Harness and composes
`engineering-execution-plan/scripts/epctl.py` only during initialization.
`scripts/spec_manager.py` selects and locks Engineering Specs. Both tools write
owner fields into files under `docs/.engineering/` in target repositories.

Current documentation lives in `README.md`, `README.zh-CN.md`, `references/`,
and `docs/design-docs/`. Accepted ADRs, completed ExecPlans, and their artifacts
are sealed history. They can contain `EngineeringWorkflow` without representing
the current product.

The user has uncommitted Prompt-example rewrites in four files. This plan
preserves their content and changes only the one former-brand reference that
overlaps the migration.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-007_repo-foundry-identity.md` | Accepted naming, migration, and compatibility decision | Before changing a public contract |
| `docs/adr/adr-008_repofoundry-ai-brand.md` | Accepted external brand and stable technical-name boundary | Before changing promotional surfaces |
| `docs/adr/adr-009_align-repofoundry-ai-skill-name.md` | Accepted project/Skill naming alignment | Before changing the root Skill ID |
| `docs/design-docs/repo-foundry-system.md` | Target layers, names, brand assets, and verification | Before each milestone |
| `docs/design-docs/engineering-workflow-packaging.md` | Existing package ownership retained by this migration | Before moving root paths |
| `SKILL.md` | Root Skill boundary and user-facing routing | Before rewriting the root entrypoint |
| `scripts/foundryctl.py` | Current Bootstrap and Harness implementation | Before changing CLI behavior |
| `scripts/spec_manager.py` | Spec owner and lock contracts | Before changing manifest ownership |
| `tests/test_repository_contracts.py` | Distribution and current-document invariants | Before updating current naming assertions |
| `python3 -B scripts/check.py` | Canonical repository validation | Before completion |

Do not rename `.engineering` state, professional Skill IDs, or their CLIs.
Do not edit sealed historical bodies to erase the former name. Do not change
the configured Git remote or claim the external repository was renamed.

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-004", "ADR-007", "ADR-008", "ADR-009"].
- Design document references: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/repo-foundry-system.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 and ADR-001 established that multi-document Research has a lifecycle and
evidence responsibility separate from execution planning. ADR-004 preserved
that separation while making the former root an aggregation layer. This
migration must keep every professional Skill independently installable and must
not move its artifact lifecycle into the root.

ADR-007 amends the presentation part of ADR-004. It selects `RepoFoundry` as the
product identity and `Agent-Native Engineering System` as the category. The root
Skill becomes `repo-foundry`; the CLI becomes `scripts/foundryctl.py`; examples
use `REPO_FOUNDRY_HOME`; new Harness and Spec manifests use owner
`repo-foundry`.

ADR-008 amends the public-brand portion of ADR-007. Promotional surfaces use
`RepoFoundry AI`, the category line `The Agent-Native Engineering System`, and
the claim `Turn any repository into an AI-ready engineering system.` ADR-009
then narrows that technical-name split: the root Skill ID becomes
`repo-foundry-ai` so project discovery and invocation match. The CLI,
environment variable, asset prefix, manifest owner, state path, and
professional Skill IDs remain unchanged.

Existing target repositories may already contain owner
`engineering-workflow`. Validation must recognize that value as legacy input
while all newly created manifests use the current owner. Historical repository
artifacts retain their original names. No remaining unknown changes the
implementation route.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

The root CLI and focused test module have been renamed. Root metadata, evals,
command help, dynamic module names, owner constants, and integrity checks use
the RepoFoundry technical identity. Explicit compatibility predicates accept
old manifest owners without scattering string alternatives through validators.

Next, finish the opening and navigation model of both READMEs around RepoFoundry
AI and The Agent-Native Engineering System. Update current Bootstrap, Spec,
packaging, and example documents. Preserve sealed history and explain the exact
installation migration.

The generated visual exploration has been reduced to a deterministic SVG mark:
two repository braces around a forge-orange AI spark. Keep the transparent
master, square application-icon variant, raster icon, and README usage aligned.

Finally, run focused unit tests and the canonical check. Store concise final
validation output in this plan's `artifacts/` directory, scan former-name
references against the historical allowlist, and update this living document.

## Milestones

### Milestone 1: RepoFoundry becomes the executable technical identity

Rename the root CLI and test module; update Skill metadata, evals, owner
constants, script help, test imports, and repository contracts. Focused tests
must prove new manifests use `repo-foundry` and legacy manifests remain
readable.

### Milestone 2: RepoFoundry AI explains one system model

Rewrite both README introductions and current design/Bootstrap/Spec documents.
All current installation examples must use `$repo-foundry-ai`,
`scripts/foundryctl.py`, and `REPO_FOUNDRY_HOME`. Historical evidence remains
unchanged.

### Milestone 3: RepoFoundry AI has a production icon

Add transparent vector and fixed-background application icon assets under
`assets/brand/`, plus a square PNG. The symbol must remain recognizable at
32 pixels and use the documented graphite, forge orange, and warm-white
palette.

### Milestone 4: The repository passes one canonical validation

Run focused tests, the full canonical check, an active-surface former-name scan,
and visual asset checks. Save complete console output under this EP's
`artifacts/`.

## Concrete Steps

Run every command from the repository root. The source renames are already
present in the working tree. Use targeted patches for root metadata, source,
tests, README files, references, and mutable design documents. Do not apply a
repository-wide replacement over `docs/adr/` or
`docs/exec-plans/completed/`.

Generate the PNG from the final SVG with an available deterministic local SVG
renderer. Confirm its dimensions and alpha/channel behavior with an image
inspection tool.

Run:

```bash
python3 -B -m unittest tests.test_foundryctl tests.test_spec_manager
python3 -B -m unittest tests.test_repository_contracts
python3 -B scripts/check.py
python3 -B engineering-execution-plan/scripts/epctl.py --repo . validate
```

## Validation and Acceptance

- [x] From the repository root, run
  `python3 -B -m unittest tests.test_foundryctl tests.test_spec_manager`;
  expect all Bootstrap and Spec tests to pass, including current and legacy
  manifest owners. Evidence:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/artifacts/focused-tests.txt`.
- [x] Run `python3 -B -m unittest tests.test_repository_contracts`; expect root
  metadata, install examples, packaging, and brand-asset contracts to pass.
  Evidence:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/artifacts/repository-contracts.txt`.
- [x] Run `python3 -B scripts/check.py`; expect exit code 0 from the only
  canonical repository check. Evidence:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/artifacts/check.txt`.
- [x] Scan current source and mutable documentation; expect former identity
  matches only in explicit migration/legacy-compatibility text or sealed
  history. Evidence:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/artifacts/identity-scan.txt`.
- [x] Parse both SVGs and inspect `repofoundry-icon.png`; expect valid XML,
  a square raster, and a recognizable mark at 32×32. Evidence:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/artifacts/brand-check.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Source renames and text patches are version-controlled and can be retried after
checking `git status`. The implementation never rewrites target repositories or
the configured remote. Legacy-owner support prevents installed Harnesses from
requiring an eager state migration.

If a rename is interrupted, restore one canonical filename before running
tests; never leave both full CLI implementations. Generated raster assets can
be regenerated from the SVG master. Existing uncommitted Prompt-example edits
must remain in place throughout the work.

## Progress

- [x] (2026-07-30T16:19:12Z) Created EP-006 with dependency-closed Research
  and ADR inputs.
- [x] (2026-07-30T16:24:00Z) Accepted ADR-007 from the Repository Owner's
  explicit RepoFoundry approval and wrote the target system design.
- [x] (2026-07-30T16:28:00Z) Explored two icon concepts and identified the
  outer-mold/engineered-core direction.
- [x] (2026-07-31T00:44:00Z) Accepted ADR-008 after the Repository Owner
  explicitly approved `RepoFoundry AI` as the external brand.
- [x] (2026-07-31T00:49:00Z) Renamed and updated executable contracts, added
  current/legacy owner tests, and passed the 25 focused Bootstrap and Spec tests.
- [x] (2026-07-31T01:02:00Z) Added the vector master, application SVG, 256px
  PNG, palette guide, and inspected a 32px raster rendering.
- [x] (2026-07-31T01:16:00Z) Rewrote the current README, Skill metadata,
  Bootstrap and Spec documents, design index, migration guide, and system
  design around the RepoFoundry AI message hierarchy.
- [x] (2026-07-31T01:22:00Z) Passed all acceptance checks and recorded focused,
  repository, canonical, identity, and brand evidence under `artifacts/`.
- [x] (2026-08-01T08:18:00Z) Accepted ADR-009 from the Repository Owner's
  explicit instruction to synchronize the project and root Skill names.
- [x] (2026-08-01T08:31:00Z) Updated every current Skill surface to `$repo-foundry-ai` and reran the
  canonical validation before pushing the amended PR branch.

## Surprises & Discoveries

- The design document initially referenced the expected next ADR ID. The
  allocator correctly treated that reference as occupied and created ADR-007,
  leaving ADR-006 as an intentional gap.
- The first generated icon had a useful boundary/core model but too many
  package-like internal segments. The second removed that complexity but became
  overly shield-like. The final SVG should retain the conceptual contrast while
  using a simpler original geometry.
- Two further imagegen iterations made the repository-and-anvil metaphor clear
  but remained too literal at favicon size. The final vector keeps the
  repository braces and one AI spark, dropping the document, code lines, and
  anvil silhouette.

## Decision Log

- 2026-07-30 — Use `RepoFoundry` as the brand and
  `Agent-Native Engineering System` as the category. This separates a memorable
  identity from a precise description.
- 2026-07-30 — Keep `.engineering` and all professional `engineering-*` Skill
  IDs stable because they describe domain contracts.
- 2026-07-30 — Write `repo-foundry` in new manifests and accept the former owner
  only as legacy input.
- 2026-07-30 — Preserve sealed history and avoid an unverified external GitHub
  rename in this local change.
- 2026-07-31 — Use `RepoFoundry AI` on external promotional surfaces while
  retaining all ADR-007 technical identifiers. This adds immediate AI relevance
  without creating a second compatibility migration.
- 2026-08-01 — Align the public root Skill ID with the project as
  `repo-foundry-ai`. Keep `repo-foundry` only as the stable manifest owner and
  as an explicitly documented pre-merge candidate name.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry AI is now the external brand, backed by the category line
`The Agent-Native Engineering System` and an AI-ready repository claim.
`repo-foundry-ai` is the synchronized public Skill ID. `foundryctl`,
`REPO_FOUNDRY_HOME`, and the `repo-foundry` manifest owner remain stable
machine contracts.

The migration retains compatibility with existing `engineering-workflow`
Harness and Spec owners, while one current root Skill and CLI avoid permanent
alias complexity. The final mark uses repository braces and a forge-orange AI
spark; SVG is the source and the checked 256px PNG remains recognizable at
32px.

The canonical check passed 109 tests. Research and ExecPlan validators returned
zero errors and zero warnings. The configured Git remote still uses the former
hosting path because remote rename was explicitly outside this local change.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

- `scripts/foundryctl.py` remains a Python standard-library CLI and dynamically
  composes `engineering-execution-plan/scripts/epctl.py` during Bootstrap.
- `scripts/spec_manager.py` remains the sole implementation for Spec selection,
  lock, sync, update, and validation.
- Harness, Spec selection, and Spec lock JSON keep their current schemas and
  `docs/.engineering/` paths.
- Professional Skills keep independent metadata, scripts, tests, and evals.
- SVG files are source assets; raster generation adds no runtime dependency to
  RepoFoundry.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-07-30T16:19:12Z — Initial plan created.
- 2026-07-30T16:31:00Z — Filled the self-contained migration route,
  compatibility boundary, milestones, validation evidence, and recovery model.
- 2026-07-31T01:05:00Z — Added ADR-008 to the dependency-closed architecture
  inputs, updated current truth after executable and icon work, and refined the
  remaining route around RepoFoundry AI.
- 2026-07-31T01:24:00Z — Recorded completed documentation, icon, compatibility,
  identity-scan, and canonical-check evidence. The plan remains active until the
  reviewed working tree receives a stable commit or snapshot revision for
  archival.
- 2026-08-01T08:18:00Z — Added accepted ADR-009 and reopened current-surface
  validation to align the root Skill ID with RepoFoundry AI without changing
  persistent target-repository contracts.
- 2026-08-01T08:31:00Z — Regenerated root Skill UI metadata, synchronized
  prompts, evals, current design documents, and installation tests, then passed
  the 109-test canonical check with zero validation errors or warnings.
