---
schema_version: "2.5"
id: EP-012
title: "Add project-scoped RepoFoundry AI Skill registration"
status: completed
latest_checkpoint: CP-001
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-002", "ADR-004", "ADR-005", "ADR-010", "ADR-011", "ADR-012"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
required_benchmark_scenarios: []
verified_revision: "git:666d546cdcebbbc982dd7e69cd2bdcd5e97db972"
verification_evidence: ["docs/exec-plans/completed/ep-012_project-skill-registration/artifacts/check.txt", "docs/exec-plans/completed/ep-012_project-skill-registration/artifacts/bootstrap-smoke.txt", "docs/exec-plans/completed/ep-012_project-skill-registration/artifacts/focused-tests.txt", "https://github.com/XiaoWeiKIN/RepoFoundryAI/actions/runs/30885559441", "https://github.com/XiaoWeiKIN/RepoFoundryAI/pull/23"]
archive_sha256: ade7f308a364216e6588b9778f73ea6544f5c04c0ae30d6fcadf826a45356b9f
created: 2026-08-04
updated: 2026-08-04
owner: "RepoFoundry Maintainer"
---

# Add project-scoped RepoFoundry AI Skill registration

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry AI must be installable once as a product-neutral CLI while each
repository can carry the Skills that make its Harness discoverable to multiple
Coding Agents. After this plan, a maintainer can preview and apply
`repofoundry --repo . bootstrap --all-adapters --apply`; the repository will
contain one canonical project-local RepoFoundry workflow plus thin Codex and
Claude Code Skill entrypoints. A clone does not depend on the original
maintainer's home directory or an absolute symlink, and both Agents route
Engineering Specifications through the same project-local Core Router and
lock.

The observable result is a schema 3 Harness whose adapter list contains
`codex`, `claude`, and `portable`, whose managed-file records identify every
project Skill seed, and which passes scoped and full validation after repeated
bootstrap runs.

## Current Snapshot

- Latest checkpoint: [CP-001](history/cp-001_project-skill-local-acceptance.md).
- Current milestone: Milestone 4: release-ready delivery
- Current state: Implementation revision `666d546cdcebbbc982dd7e69cd2bdcd5e97db972`
  passed Python 3.10, Python 3.14, and `ep-integrity` in PR #23 after all local
  acceptance completed.
- Next action: Archive EP-012 with the verified revision and evidence URLs,
  then push the sealed plan state and confirm final PR checks.
- Open blockers: none.

## Context and Orientation

`install.py` owns distribution installation under the user's data directory
and may register a personal Skill. It deliberately reports
`project_harnesses_modified: false`. Project mutation belongs to
`scripts/foundryctl.py`, whose `bootstrap` command already provides dry-run,
conflict preflight, managed-file provenance, idempotent apply, rollback, and
the ability to union multiple adapters into `docs/.engineering/harness.json`.

The schema 3 Core owns repository documents, the Engineering Spec lock, and
the canonical Router at `.repo-foundry/engineering-specs/spec_router.py`.
Adapter assets live under `assets/adapters/{adapter-id}/`; `scripts/foundryctl.py`
declares their versions, capabilities, directories, files, template IDs, and
validation. Before EP-012, Codex created `AGENTS.md`,
`.agents/skills/engineering-specs/`, and `.codex/hooks.json`, while Portable
created only `docs/agent-guides/README.md`.

This plan adds a canonical project workflow at
`.repo-foundry/skills/repo-foundry-ai/SKILL.md`. The Codex adapter adds the thin
entrypoint `.agents/skills/repo-foundry-ai/SKILL.md`. The new Claude adapter
adds `.claude/skills/repo-foundry-ai/SKILL.md` and
`.claude/skills/engineering-specs/SKILL.md`. Thin entrypoints instruct the
Agent to read the canonical repository-local workflow or invoke the canonical
Router; they do not embed a second Core implementation or point at a user home
directory.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/agent-neutral-harness-adapters.md` | Accepted Core/adapter capability, ownership, versioning, and coexistence contract | Before changing adapter descriptors or generated paths |
| `docs/adr/adr-011_agent-neutral-harness-adapters.md` | Requires repository-owned Core state and independently versioned product adapters | Before implementation and compatibility review |
| `docs/adr/adr-012_agent-neutral-spec-activation.md` | Requires one activation engine and product-specific thin translation only | Before creating the Claude Engineering Specs Skill |
| `references/bootstrap.md` | Defines dry-run, conflict, migration, idempotence, and rollback behavior | Before editing bootstrap or upgrade paths |
| `scripts/foundryctl.py` | Canonical Harness CLI, descriptor registry, manifest generation, apply, migration, and validation | During implementation |
| `tests/test_foundryctl.py` | Executable bootstrap, migration, drift, rollback, and adapter behavior contract | During every milestone |
| `tests/test_spec_router.py` | Shared activation and adapter-isolated receipt contract | When adding Claude activation coverage |
| `tests/test_repository_contracts.py` | Enforces product-neutral boundaries and packaged asset completeness | Before completion |

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-002", "ADR-004", "ADR-005", "ADR-010", "ADR-011", "ADR-012"].
- Design document references: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 is included because ADR-001 belongs to the accepted ADR dependency and
amendment closure. Its durable conclusion is that research evidence and
execution governance remain independently owned; this feature must not move
Research or ExecPlan lifecycle logic into the root Skill or Harness adapter.

ADR-011 requires one Agent-neutral Core with independently versioned adapters,
allows multiple products to coexist over one repository Harness, and prohibits
the Core from embedding product events, trust models, or configuration paths.
Its negative consequence is additional adapter version and validation state;
the implementation must report enforcement honestly. ADR-012 and ADR-010
require one canonical project-local Spec Router, explicit activation receipts,
and thin runtime translation. Claude phase 1 therefore provides native Skill
discovery but only CLI/advisory activation enforcement; it does not claim
native mutation gates or install Claude Hooks.

ADR-002, ADR-004, and ADR-005 preserve the project bootstrap boundary,
independent professional Skills, and external locked Engineering
Specifications. Generated project files must be regular repository-relative
files recorded with template and installed SHA-256 values. Existing customized
paths are preserved as conflicts rather than overwritten.

No route-changing unknown remains. The local choices are reversible within
the accepted adapter model: reuse `bootstrap` instead of adding a parallel
`register` command; add deterministic `--all-adapters` rather than machine
detection; and exclude Claude Hooks and `CLAUDE.md` from this phase.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First add canonical and adapter-specific Skill assets. Extend the Core file
registry and bump the Core version because the canonical project workflow is a
new managed seed. Bump the Codex adapter because it gains a root Skill
entrypoint. Add `claude@1.0.0` with an explicit capability descriptor that
advertises native Skill discovery, no lifecycle events, CLI mutation gate and
completion audit, and advisory context injection.

Next extend `scripts/foundryctl.py` so Claude participates in deterministic
adapter ordering, manifest generation, template ownership, bootstrap apply,
scoped validation, and drift reporting. Add `--all-adapters` to bootstrap as a
selection convenience that expands to the complete ordered adapter set and
cannot be combined with `--profile` or explicit `--adapter`. Keep the existing
deprecated omitted-adapter behavior for compatibility.

Then add tests for Claude-only bootstrap, all-adapter coexistence, canonical
Skill ownership, conflict safety, idempotence, scoped drift, normalized Spec
activation with `adapter_id: claude`, and existing schema 3 adapter additions.
Update the README, Chinese README, root Skill, bootstrap reference, adapter
design document, and repository contracts without rewriting sealed ADRs or
completed plans.

Finally run focused tests, temporary-repository end-to-end bootstrap and
validation, the canonical `python3 -B scripts/check.py`, and remote CI. Record
full evidence under this EP before archiving it against the verified commit.

## Milestones

### Milestone 1: Project-local canonical Skill and adapter assets

Add regular-file assets for the canonical RepoFoundry project workflow, the
Codex root Skill entrypoint, and the Claude root and Engineering Specs Skill
entrypoints. Register them with independent Core/adapter versions and exact
template ownership. `adapter list` must report `codex`, `claude`, and
`portable`, while the Core asset contains no Agent product paths or event
names.

### Milestone 2: Deterministic project registration and validation

Implement `bootstrap --all-adapters` and `validate --adapter claude` by reusing
the existing schema 3 bootstrap transaction. A dry-run must show all new
paths; apply must create them atomically; a repeat must have no create or
conflict actions. A pre-existing Claude Skill must produce a conflict and no
partial writes.

### Milestone 3: Shared Engineering Spec activation and compatibility

Exercise the Claude Skill against the canonical Router with `adapter_id:
claude`, proving candidates, activation, explicit-none, receipts, and audit are
shared with other adapters but receipt state remains isolated. Existing
Codex-only, portable-only, legacy schema migration, customized-seed, and
installer contracts must remain green. Schema 3 does not change; Core and
adapter versions express the new generated files.

### Milestone 4: Documentation, evidence, and release-ready delivery

Document global versus project scope, deterministic all-adapter registration,
generated layout, enforcement level, and upgrade behavior. Run all local and
remote checks, save concise evidence, update this living plan, and archive it
only after the verified implementation revision passes every acceptance item.

## Concrete Steps

All commands run from the repository root.

1. Edit assets and descriptor/validation logic:

   ```text
   assets/core/repo-foundry-ai/SKILL.md
   assets/adapters/codex/repo-foundry-ai/SKILL.md
   assets/adapters/claude/repo-foundry-ai/SKILL.md
   assets/adapters/claude/engineering-specs/SKILL.md
   scripts/foundryctl.py
   ```

2. Run focused contracts:

   ```bash
   python3 -m unittest -v \
     tests.test_foundryctl \
     tests.test_spec_router \
     tests.test_repository_contracts
   ```

3. Exercise a temporary repository, first without `--apply`, then with it:

   ```bash
   python3 scripts/foundryctl.py --repo "$TEMP_REPO" \
     bootstrap --all-adapters
   python3 scripts/foundryctl.py --repo "$TEMP_REPO" \
     bootstrap --all-adapters --apply
   python3 scripts/foundryctl.py --repo "$TEMP_REPO" validate --harness
   python3 scripts/foundryctl.py --repo "$TEMP_REPO" \
     validate --adapter claude
   ```

   The preview reports `create` actions without writing. Apply reports the
   ordered adapter set `codex`, `claude`, `portable`. Both validation commands
   exit zero.

4. Run the canonical repository check:

   ```bash
   python3 -B scripts/check.py
   ```

   Expected final line: `[check] all integrity checks passed`.

## Validation and Acceptance

- [x] From the repository root, run `python3 scripts/foundryctl.py --repo
  "$TEMP_REPO" bootstrap --all-adapters`; expect a no-write preview containing
  the canonical Core Skill, Codex root Skill, both Claude Skills, and the
  ordered adapter set. Evidence:
  `docs/exec-plans/completed/ep-012_project-skill-registration/artifacts/bootstrap-smoke.txt`.
- [x] Apply the same command with `--apply`, repeat it, and run `validate
  --harness`, `validate --adapter codex`, `validate --adapter claude`, and
  `validate --adapter portable`; expect zero exits and no second-run create or
  conflict actions. Evidence: `artifacts/bootstrap-smoke.txt`.
- [x] Inspect every generated project Skill; expect regular repository-local
  files, no symlinks, no user-home absolute paths, and only thin product
  entrypoints outside the Core. Evidence: repository contract tests and
  `artifacts/focused-tests.txt`.
- [x] Run the Claude activation integration test; expect the same candidate
  and activated Spec IDs as portable/Codex and an isolated `claude` receipt.
  Evidence: `artifacts/focused-tests.txt`.
- [x] Run `python3 -B scripts/check.py`; expect all repository, Research,
  Benchmark, Execution Plan, Harness, migration, Spec, Markdown, and whitespace
  checks to pass. Evidence: `artifacts/check.txt`.
- [x] Verify GitHub CI for Python 3.10, Python 3.14, and `ep-integrity`; all
  required checks passed. Evidence:
  `https://github.com/XiaoWeiKIN/RepoFoundryAI/actions/runs/30885559441`,
  jobs `91915869789`, `91915869820`, and `91917449062`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Bootstrap remains dry-run by default and preflights the full Core plus adapter
path set before writing. `--apply` uses the existing transaction and
post-validation rollback, so a failure restores every created file and
manifest byte. Repeating a successful bootstrap preserves all installed
paths. Existing unowned or customized target files become conflicts and block
the entire apply; no automatic backup or overwrite occurs in project scope.

The implementation does not add symlinks, delete adapters, edit user home
directories, or remove project configuration. Existing schema 3 repositories
can add Claude through another previewed bootstrap. Existing versioned seeds
are replaced only by explicit distribution upgrade when their current digest
matches the recorded installed digest; customized seeds require manual merge.
Recovery consists of fixing the reported conflict or reverting the feature
commit, rerunning the preview, and applying again. Temporary smoke repositories
are disposable and never serve as evidence sources beyond captured output.

## Progress

- [x] (2026-08-04T06:50:22Z) Verified official Claude personal/project Skill
  precedence, added canonical-project delegation to the distribution Skill,
  required every new entrypoint during package validation, and reran the
  canonical check with 95 repository tests passing.
- [x] (2026-08-04T07:01:11Z) Created PR #23 and verified implementation commit
  `666d546cdcebbbc982dd7e69cd2bdcd5e97db972` on Python 3.10, Python 3.14,
  and the aggregate `ep-integrity` job.

## Surprises & Discoveries

- (2026-08-04T06:44:53Z) Official Claude Code documentation confirms project
  discovery at `.claude/skills/<name>/SKILL.md`, but personal Skills override
  project Skills with the same name. A generated same-name project entrypoint
  alone would therefore be bypassed on the most common globally installed
  setup.

## Decision Log

- (2026-08-04, Codex) Keep the public `repo-foundry-ai` name at personal and
  project scope, and make the distribution root Skill delegate to
  `.repo-foundry/skills/repo-foundry-ai/SKILL.md` when present. This preserves
  one marketing command while ensuring both Claude precedence branches
  converge on the versioned repository contract.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry AI now installs one canonical project workflow and exposes it
through regular, repository-relative Codex and Claude Skill entrypoints. The
Claude adapter reports native discovery but honest CLI/advisory activation;
all adapters share one Core Router, Spec lock, receipt protocol, and manifest.
`bootstrap --all-adapters` is deterministic, preview-first, idempotent, and
conflict-atomic.

The most important migration result is that schema 3 remains stable while its
independently versioned file contract evolves. Old Core 1.0.0 and Codex 2.0.0
manifests remain valid inputs; upgrade or adapter adoption can add the new
generated Skills with explicit component migration records. Customized bytes
still fail closed. Official Claude precedence required the distribution root
Skill to delegate to the repository canonical Skill when a personal same-name
entrypoint wins discovery.

Local canonical validation, a disposable three-adapter repository smoke, and
all three remote gates passed at
`666d546cdcebbbc982dd7e69cd2bdcd5e97db972`. The local one-command installer
was also re-run: Codex and Claude personal registrations now point to the new
immutable `0.2.0` package, and no project Harness was modified by installation.

### Knowledge promotion candidates

- Preserve the component-version-aware schema reader and personal-to-project
  Skill delegation pattern in future adapter authoring guidance.

## Interfaces and Dependencies

No new third-party runtime dependency is allowed. Python 3.10+ standard library
remains the implementation baseline.

`scripts/foundryctl.py` must expose these effective interfaces:

```text
ADAPTER_ORDER = ("codex", "claude", "portable")
bootstrap --adapter claude [--apply]
bootstrap --all-adapters [--apply]
validate --adapter claude
adapter list
```

The manifest remains schema 3. Planned component versions are Core `1.1.0`,
Codex adapter `2.1.0`, Claude adapter `1.0.0`, Portable adapter `1.0.0`, and
activation protocol `1`. `--all-adapters` is a CLI selector only and is never
stored as an adapter ID. Adapter entrypoints may invoke only the canonical
`.repo-foundry/engineering-specs/spec_router.py`; no adapter carries a second
activation engine.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-012_project-skill-registration/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-04T06:41:51Z — Sealed CP-001; refreshed Current Snapshot and preserved historical detail.
- 2026-08-04T07:01:11Z — PR #23 remote gates passed for implementation commit
  `666d546cdcebbbc982dd7e69cd2bdcd5e97db972`; completion evidence is ready for
  archive sealing.
