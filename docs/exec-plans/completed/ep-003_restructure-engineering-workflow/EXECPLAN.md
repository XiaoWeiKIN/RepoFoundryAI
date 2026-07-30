---
schema_version: "2.4"
id: EP-003
title: "Restructure EngineeringWorkflow skill ownership"
status: completed
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-004", "ADR-002"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
verified_revision: "git:f3524a647c46eb4824897142ecdb5a6858bb8d3f"
verification_evidence: ["local:python3-B-scripts-check.py@f3524a647c46eb4824897142ecdb5a6858bb8d3f", "pr:https://github.com/XiaoWeiKIN/EngineeringPlan/pull/7"]
archive_sha256: 667d0a2b15f9b1b7b52fbd08d01822557e6f7cbb458a83e08a5f4a0a2aaa9cf6
created: 2026-07-30
updated: 2026-07-30
owner: "EngineeringWorkflow Maintainer"
---

# Restructure EngineeringWorkflow skill ownership

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Turn the repository into a coherent EngineeringWorkflow distribution. Users
can install the root `$engineering-workflow` Skill to bootstrap and validate a
Codex project Harness, while installing
`$engineering-execution-plan` from its own peer directory for ADR and ExecPlan
work. The observable result is that `engineeringctl bootstrap` creates the
project documentation map without overwriting existing files, `epctl` no
longer exposes Harness commands, and all five Skill packages pass the canonical
repository check.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 complete; recording archival evidence.
- Current state: Workflow and EP package boundaries, CLI extraction, templates,
  tests and current documentation have been migrated. All five Skill packages,
  the four test suites, repository validators, links, generated indexes and
  whitespace checks pass at `git:f3524a647c46eb4824897142ecdb5a6858bb8d3f`.
  The implementation is pushed and PR #7 is open.
- Next action: archive EP-003 with the verified revision, local check and PR
  URL, then push the archival commit.
- Open question: the GitHub repository rename is an administrative post-merge
  action and is not performed by this source PR.

## Context and Orientation

The repository root was formerly both the distribution and the
`execution-plan` Skill. Three other professional Skills already lived in
`engineering-benchmark/`, `engineering-research/`, and
`engineering-case-study/`.

The target structure uses:

- root `SKILL.md`, `agents/openai.yaml`, `assets/harness-*.md`,
  `references/bootstrap.md`, and `scripts/engineeringctl.py` for
  `engineering-workflow`;
- `engineering-execution-plan/` for the former root EP package, including its
  own assets, references, CLI, tests, evals and examples;
- root `scripts/check.py` as the distribution-wide validation entrypoint;
- root `docs/` as this distribution repository's governance history rather
  than a bundled Skill resource.

Harness state belongs to `docs/.engineering/`; EP ID and architecture-root
state remains in `docs/.epctl/`. `engineeringctl` may load the bundled EP module
to call its idempotent initialization contract. The four professional Skills
do not import one another.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-004_separate-workflow-orchestration-from-execution-planning.md` | Accepted package, naming and migration boundary | Before moving Skill files |
| `docs/adr/adr-002_codex-project-documentation-bootstrap.md` | Accepted Bootstrap safety and line-budget contract | Before changing `engineeringctl` |
| `docs/design-docs/engineering-workflow-packaging.md` | Exact package, command and state ownership | Before editing paths or checks |
| `docs/design-docs/codex-project-bootstrap.md` | Harness schema, preflight and validation behavior | Before editing Bootstrap |
| `engineering-execution-plan/SKILL.md` | EP lifecycle and decision-authority rules | Before changing ADR/EP behavior |
| `scripts/check.py` | Provider-neutral canonical repository contract | Before final validation |

Preserve existing user files byte-for-byte during Bootstrap. Count all physical
`AGENTS.md` lines, including blanks and comments; 100 passes and 101 fails.
Do not edit accepted ADR or sealed Design input payloads. Do not duplicate
professional Skill logic in the Workflow package.

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-004", "ADR-002"].
- Design document references: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 established that evidence production and execution planning have
different growth, ownership and lifecycle characteristics. Its sealed
Synthesis supports independent Research production and file-contract
consumption rather than one monolithic Skill.

ADR-001 applied that conclusion by separating Engineering Research from
execution planning. Its temporary choice to leave EP at the repository root is
amended by ADR-004; the Research producer/consumer boundary remains current.

ADR-004 requires the root to become `engineering-workflow`, moves EP to
`engineering-execution-plan/`, keeps all four professional Skills independently
installable, and rejects a duplicated `$execution-plan` compatibility package.
CLI call sites must move to the nested path, while `epctl` and artifact schemas
remain stable.

ADR-002 requires preview-first, non-overwriting Bootstrap behavior and a hard
100-line Agent instruction limit. Under ADR-004, Workflow owns
`engineeringctl`, Harness templates and `docs/.engineering/harness.json`;
Bootstrap composes `epctl init` and registers Design Docs without moving EP
state.

There is no implementation-route unknown. The remaining external operation is
renaming the GitHub repository after merge; this plan documents but does not
perform that administrative change.

## Plan of Work

First move the complete EP package into
`engineering-execution-plan/`, then update its Skill identity and remove
Bootstrap commands without changing artifact lifecycle behavior. Replace the
root Skill with the Workflow routing contract.

Extract Bootstrap planning, apply, manifest and Harness validation into
`scripts/engineeringctl.py`. Keep root Harness assets and move the manifest
from `.epctl` to `.engineering`. Compose EP initialization by loading the
bundled EP module rather than copying templates or ID logic.

Finally update repository checks, examples, current architecture documents,
README installation paths, CODEOWNERS and eval catalogs. Split Bootstrap tests
from the EP suite, add independent-install coverage, regenerate indexes, and
run the canonical check before committing.

## Milestones

### Milestone 1: Establish symmetric Skill packages

Move EP-owned files to `engineering-execution-plan/`, create the root
`engineering-workflow` metadata, and update identity contracts. Running EP
unit tests from the nested package must preserve all existing lifecycle
behavior.

### Milestone 2: Transfer project Harness ownership

Create `scripts/engineeringctl.py`, keep Harness templates at root, remove
Bootstrap from `epctl`, and move the manifest to `docs/.engineering`. Workflow
tests must prove dry-run, apply, idempotence, byte preservation, conflict
safety and the 100-line limit.

### Milestone 3: Align repository contracts and deliver

Update paths, docs, evals, canonical checks and independent-install tests.
All Skill validators, unit tests, repository validators, Markdown links,
generated indexes and whitespace checks must pass on the committed revision.

## Concrete Steps

From the repository root:

```bash
python3 -B -m unittest discover \
  -s engineering-execution-plan/tests -p 'test_*.py' -v

python3 -B -m unittest discover -s tests -p 'test_*.py' -v

python3 /absolute/path/to/skill-creator/scripts/quick_validate.py .
python3 /absolute/path/to/skill-creator/scripts/quick_validate.py \
  engineering-execution-plan

python3 -B scripts/check.py
git diff --check
```

The two targeted suites must report no failures. Every Skill validator must
report `Skill is valid!`. The canonical check must finish with
`[check] all integrity checks passed`.

## Validation and Acceptance

- [x] From the repository root, run the eight Workflow tests; expect all pass.
  Evidence: terminal run on 2026-07-30 reported `Ran 8 tests ... OK`.
- [x] Run the nested Engineering Execution Plan suite; expect all 36 lifecycle
  tests to pass after removing Harness ownership. Evidence: terminal run on
  2026-07-30 reported `Ran 36 tests ... OK`.
- [x] Run root Workflow and integration tests; expect all 15 tests to pass,
  including copied-package installation. Evidence: terminal run on 2026-07-30
  reported `Ran 15 tests ... OK`.
- [x] Validate all five `SKILL.md` packages with Skill Creator
  `quick_validate.py`; all five reported `Skill is valid!`.
- [x] Run `python3 -B scripts/check.py`; 29 Research, eight Benchmark,
  36 Engineering Execution Plan and 15 Workflow/integration tests passed,
  followed by repository, link, projection and whitespace checks.
- [x] Run `git diff --check`; the command produced no output.
- [x] Commit the validated tree and rerun the canonical check at
  `git:f3524a647c46eb4824897142ecdb5a6858bb8d3f`; push the branch and record
  [PR #7](https://github.com/XiaoWeiKIN/EngineeringPlan/pull/7).

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

File moves use Git-aware renames so history remains reviewable. Re-running
tests and check commands is read-only except for temporary copied repositories
and ignored bytecode.

`engineeringctl bootstrap` is dry-run by default. Apply performs preflight
before creating managed paths, then repeats preflight under the Workflow lock.
Both Workflow and EP initialization are idempotent. A failed run can be retried
after resolving the reported conflict; existing project files are never
truncated or replaced.

Before the branch was created, the dirty Bootstrap work was placed in a
recoverable Git stash, the branch was switched to the latest remote PR base,
and the stash was applied successfully. No stash remains. Rollback of this
source change is a normal Git revert; no external repository rename is part of
the commit.

## Progress

- [x] (2026-07-30T10:22:00Z) Created EP-003 with dependency-closed Research,
  ADR and Design Doc inputs.
- [x] (2026-07-30T10:31:00Z) Moved EP into
  `engineering-execution-plan/` and created the root Workflow package.
- [x] (2026-07-30T10:39:00Z) Extracted Bootstrap and Harness validation into
  `engineeringctl`; targeted Workflow and EP tests pass.
- [x] (2026-07-30) Completed five-package validation and the canonical
  repository check with no errors.
- [x] (2026-07-30) Committed and revalidated
  `f3524a647c46eb4824897142ecdb5a6858bb8d3f`, pushed
  `codex/engineering-workflow`, and opened PR #7.

## Surprises & Discoveries

- ADR allocation produced ADR-004 rather than ADR-003 because the monotonic ID
  scan had already observed `ADR-003` in repository history. The high-water
  contract correctly prevented reuse; no manual renumbering was attempted.
- The active Benchmark work already has PR #6, so this change uses a stacked
  branch based on its latest remote head to keep the review diff isolated.

## Decision Log

- 2026-07-30 — Use the repository root as the
  `engineering-workflow` aggregation Skill and put EP in
  `engineering-execution-plan/`. Authority: accepted ADR-004.
- 2026-07-30 — Keep Bootstrap separate from `epctl init`; Workflow owns
  `docs/.engineering/harness.json` and composes EP initialization. Authority:
  accepted ADR-002.
- 2026-07-30 — Do not retain a duplicated `$execution-plan` package or root
  CLI wrapper. Reason: one source of truth and an explicit early migration are
  safer than two drifting install surfaces.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The implemented boundary matches ADR-004: the root is a small Workflow
aggregation Skill, all four professional Skills have parallel package
ownership, and no compatibility alias duplicates EP. Bootstrap is separately
testable, preview-first, non-overwriting, and keeps its manifest and lock
outside `.epctl`.

The verified implementation is
`f3524a647c46eb4824897142ecdb5a6858bb8d3f`; review is tracked in
[PR #7](https://github.com/XiaoWeiKIN/EngineeringPlan/pull/7). The GitHub
repository rename remains a post-merge administrative operation, as planned.

Pending final canonical validation and PR creation. The implemented behavior
already demonstrates the intended package and CLI boundaries; this section
will be finalized before archival.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

- Python 3.10+ standard library only.
- `scripts/engineeringctl.py` public commands:
  `bootstrap --profile codex [--dry-run|--apply]` and
  `validate [--harness]`.
- `engineering-execution-plan/scripts/epctl.py` retains its existing artifact
  commands and exposes `init_repo`, `repo_lock`, `load_config`, `save_config`,
  `INIT_DIRECTORIES`, and `INIT_FILE_ASSETS` as the bundled composition
  contract.
- Harness manifest schema version 1 is owned by `engineering-workflow` at
  `docs/.engineering/harness.json`.
- The only cross-Skill runtime dependency is Workflow loading its bundled EP
  component during Bootstrap; professional Skills remain independent.
- Git and GitHub are delivery dependencies, not runtime dependencies of any
  Skill.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-003_restructure-engineering-workflow/EXECPLAN.md`
- Decisions: `docs/adr/adr-004_separate-workflow-orchestration-from-execution-planning.md`
  and `docs/adr/adr-002_codex-project-documentation-bootstrap.md`
- Design entrypoint: `docs/design-docs/index.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-07-30T10:22:00Z — Initial plan created.
- 2026-07-30T10:42:00Z — Replaced all template placeholders with the accepted
  package boundary, actual progress, commands, recovery behavior and pending
  verification.
