---
schema_version: "2.5"
id: EP-008
title: "Let users explicitly select installed Engineering Specs"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "The repository owner fixed the product behavior in this task: detection recommends optional Specs, explicit Spec IDs select them, and existing Git/tag/lock behavior remains unchanged; current code and catalog contracts are directly inspectable."
adr_refs: []
design_refs: []
architecture_entrypoint: ""
architecture_gate: not_required
architecture_gate_reason: "ADR-005 already fixes external Catalog ownership and immutable local locking; this change refines the reversible CLI selection policy without changing repository ownership, manifest schema, lock schema, or remote trust boundaries."
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-02
updated: 2026-08-02
owner: ""
---

# Let users explicitly select installed Engineering Specs

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry users can inspect every Specification published by a fixed Catalog
release and explicitly choose the optional Specification IDs installed into a
project. Repository detection becomes a recommendation signal instead of an
installation decision. Required Specifications and transitive dependencies
remain mechanically included, so a user cannot accidentally create an invalid
selection. A dry-run displays available, required, recommended, configured,
and resolved Specification sets before `--apply` changes the manifest, lock,
managed copies, or routing index.

The behavior is observable by bootstrapping a Go repository: without a
selection override the plan configures only required Core Specifications and
reports `languages/go` as recommended; adding `--spec languages/go` configures
Go and resolves its dependency closure. An existing project can replace its
optional selection through a previewed `spec update`, including returning to
required-only selection.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — exact-revision verification and delivery.
- Current state: ESP-0009 and bilingual selection docs are integrated;
  RepoFoundry implements explicit optional selection, recommendation-only
  detection, Catalog summaries, required/dependency closure, selection
  preservation, and digest-guarded deselection. Both focused and canonical
  checks pass, as does a real public `v1.2.0` smoke flow.
- Next action: commit each repository, verify the exact RepoFoundry
  implementation commit in a clean detached worktree, archive EP-008, push the
  two open-PR branches, and confirm CI.
- Open questions: none that change the selected route.

## Context and Orientation

EngineeringSpecifications owns Catalog metadata and reusable normative
Markdown. Its `catalog.json` marks universal Core Specs with `required: true`,
records dependencies in `requires`, and optionally records deterministic
repository evidence in `detection`. RepoFoundry consumes a fixed release tag
through `scripts/spec_manager.py`; `scripts/foundryctl.py` exposes Bootstrap and
`spec plan|sync|update|validate` commands.

The project manifest `docs/.engineering/specs.json` stores direct configured
Spec IDs. The lock `docs/.engineering/specs.lock.json` stores the resolved
dependency closure, full Git commit, Catalog digest, and per-Spec digests.
Managed Markdown and task routing live under `docs/agent-guides/managed/`.

In the current implementation, `_initial_manifest()` combines required IDs
with `detect_specs()` output. `_prepare_manifest()` repeats that behavior on
every `update`. `resolve_selection()` validates direct IDs and computes the
dependency closure. This EP keeps the manifest and lock schema unchanged but
changes selection ownership: required IDs are automatic, detection is advisory,
and explicit CLI IDs determine optional direct selection.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `scripts/spec_manager.py` | Catalog parsing, detection, manifest selection, dependency closure, planning, materialization, and validation | Before resolver edits |
| `scripts/foundryctl.py` | Public CLI, Bootstrap orchestration, source selection, dry-run/apply boundary | Before CLI edits |
| `tests/test_spec_manager.py` | Resolver boundary and failure-safety contracts | While changing selection logic |
| `tests/test_foundryctl.py` | End-to-end CLI and temporary Git Catalog fixtures | While changing user behavior |
| `docs/design-docs/engineering-spec-management.md` | Existing external Catalog, immutable lock, update, and offline-validation design | Before modifying public semantics |
| `https://github.com/XiaoWeiKIN/EngineeringSpecifications/blob/codex/versioned-catalog-releases/docs/specification-model.md` | Catalog-side selection and task-activation model | Before changing public terminology |
| `https://github.com/XiaoWeiKIN/EngineeringSpecifications/blob/codex/versioned-catalog-releases/proposals/0009_explicit-spec-selection.md` | Approved intent, compatibility, and alternatives for explicit selection | Before integrating behavior |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture gate: `not_required`.
- ADR references: [].
- Design document references: [].
- Architecture entrypoint: ``.

Research is not required because the repository owner selected the behavior in
this task, and every affected fact is directly visible in the current Catalog,
resolver, CLI, and tests. No uncertain library, protocol, security, performance,
or external-system choice can change the route.

Architecture is not required because ADR-005 already establishes the durable
ownership and trust boundary: EngineeringSpecifications owns remote content;
RepoFoundry fetches, validates, locks, materializes, and routes it without
executing remote code. The manifest and lock remain schema version 1, the
fixed-release contract from EP-007 remains unchanged, and selection is a
reversible project configuration. The approved ESP records the public consumer
behavior without introducing a new repository or data boundary.

Implementation constraints:

- `required: true` remains non-optional and is always represented in direct
  project configuration.
- `detection` contributes recommendations only; it MUST NOT change configured
  IDs during initial creation, sync, or version update.
- repeatable `--spec ID` expresses the complete desired optional direct set;
  `--required-only` expresses an empty optional set. The two are mutually
  exclusive.
- dependencies are computed by the existing resolver and appear in the
  resolved selection even when the user did not name them.
- `sync` restores exactly the manifest/lock selection and never accepts a new
  selection. `update` is the only existing-project selection mutation.
- dry-run payloads enumerate the Catalog and distinguish required,
  recommended, configured, and dependency-closed selected sets.
- removing an optional Spec may delete only RepoFoundry-managed Markdown whose
  bytes still match the previous lock; drift or symlinks fail before writes.
- source/tag/commit locking and offline validation remain unchanged.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First add and approve an EngineeringSpecifications ESP, then revise the
selection-model documentation so detection is advisory and explicit selection
is authoritative. No normative Specification Markdown, Catalog schema, Spec
version, or digest changes are required.

In RepoFoundry, add explicit selection data to the planning boundary. Initial
manifest creation will contain required IDs plus requested optional IDs; update
will preserve the manifest unless a selection override is present. Extend the
plan payload with Catalog entries and selection roles. When an explicit update
removes a previously managed optional Spec, plan a digest-guarded removal so
the installed local set matches the reviewed selection without deleting user
content.

Expose repeatable `--spec` and mutually exclusive `--required-only` on fresh
Bootstrap and `spec update`. Keep `spec plan` as the discovery operation and
`spec sync` as a pure reproduction operation. Update Skill metadata, bilingual
README, Bootstrap reference, design documentation, evals, and tests. Finally
validate both repositories, verify exact commits in clean worktrees, archive
this EP, push the two existing PR branches, and wait for CI.

## Milestones

### Milestone 1: Publish the explicit-selection contract

EngineeringSpecifications contains an approved ESP and aligned English/Chinese
model documentation. Running `python3 -B scripts/check.py` from that repository
passes without changing `catalog.json` or normative Spec digests.

### Milestone 2: Implement deterministic user selection

RepoFoundry accepts explicit optional IDs, reports the complete Catalog and
recommendations, preserves selections across sync/version updates, and safely
removes deselected managed copies. Focused resolver and CLI tests prove required
closure, unknown-ID failure, duplicate rejection, required-only selection,
non-destructive drift handling, and detection-without-installation.

### Milestone 3: Integrate, verify, and deliver

Bilingual docs and evals describe the final commands. Both canonical checks
pass; the RepoFoundry implementation revision passes from a detached clean
worktree; EP-008 is archived; both existing PR branches are pushed and their CI
checks succeed.

## Concrete Steps

From `/Users/wangxiaowei1/xiaowei/EngineeringSpecifications`:

```bash
python3 -B scripts/check.py
```

Expect the Catalog and all repository contracts to pass with three published
Specifications and no digest drift.

From `/Users/wangxiaowei1/x-otel/EngineeringPlan`:

```bash
python3 -B -m unittest \
  tests.test_spec_manager tests.test_foundryctl tests.test_repository_contracts
python3 -B scripts/check.py
python3 engineering-execution-plan/scripts/epctl.py --repo . validate
```

Expect all focused tests, the canonical aggregate check, and EP integrity to
pass. Use temporary repositories in tests and smoke checks; do not modify
Datafox or another product repository.

## Validation and Acceptance

- [x] From EngineeringSpecifications, run `python3 -B scripts/check.py`;
  expect every Catalog/document/test check to pass and the three normative Spec
  digests to remain unchanged. Evidence:
  `artifacts/engineering-specifications-check.txt`.
- [x] From RepoFoundry, run the focused unittest command in Concrete Steps;
  expect explicit-selection, recommendation-only detection, safe deselection,
  source locking, and offline-validation tests to pass. Evidence:
  `artifacts/focused-tests.txt`.
- [x] On an empty temporary Go repository, run fixed-version `spec plan`;
  expect Core in configured/selected, Go in recommended/available, and Go absent
  from configured/selected. Evidence: `artifacts/required-only-preview.json`.
- [x] On the same repository, run Bootstrap dry-run with
  `--spec languages/go`; expect Go in configured/selected and its dependencies
  in the resolved closure, with zero target writes. Evidence:
  `artifacts/explicit-go-preview.json`.
- [x] Apply the Go selection, then run `spec update --required-only` dry-run;
  expect manifest/lock/index updates and a digest-guarded removal action for the
  managed Go document. Evidence: `artifacts/required-only-update.json`.
- [x] From RepoFoundry, run `python3 -B scripts/check.py`; expect every
  canonical repository check to pass. Evidence: `artifacts/repo-foundry-check.txt`.
- [x] From RepoFoundry, run `epctl validate`; expect zero errors. Evidence:
  `artifacts/epctl-validate.txt`.
- [ ] Verify the final RepoFoundry implementation commit in a detached clean
  worktree with `python3 -B scripts/check.py`; expect the canonical check to
  pass. Evidence: `artifacts/exact-revision-check.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Every mutating command remains dry-run by default and recomputes the plan while
holding the repository lock before applying. Repeating the same selection is
idempotent. Invalid/duplicate IDs, unavailable releases, dependency failures,
or managed-file drift fail before writes.

Existing manifests require `spec update` for selection changes. `sync` remains
a repair/reproduction operation. Deselection removes only files tracked by the
old lock whose current SHA-256 equals the locked SHA-256; otherwise the update
reports a conflict and retains all files. Empty managed directories may be
cleaned only below `docs/agent-guides/managed/` after their last managed file is
removed.

Rollback is another explicit `spec update --spec ... --apply` using the prior
direct optional IDs and, if needed, the prior fixed `--spec-version`. Git can
also revert the project manifest/lock/managed-copy commit. No migration rewrites
schema-v1 data.

## Progress

- [x] (2026-08-02T07:11:08Z) Plan created with explicit Research and
  Architecture Gate reasons.
- [x] (2026-08-02T07:12:36Z) Filled every required section before
  implementation and fixed the user-visible selection, dependency, update, and
  removal contracts.
- [x] (2026-08-02T07:35:30Z) Added approved ESP-0009 and integrated the
  recommendation-versus-selection contract into English/Chinese specification
  model, README, contribution guidance, and Changelog.
- [x] (2026-08-02T07:35:30Z) Implemented and tested RepoFoundry explicit
  selection, Catalog summaries, selection-preserving update, required-only
  update, and digest-guarded managed-file removal.
- [x] (2026-08-02T07:35:30Z) Passed 13 EngineeringSpecifications tests, 45
  focused RepoFoundry tests, both canonical checks, EP validation, and a real
  public-tag smoke flow.
- [ ] Run canonical checks, exact-revision verification, archive, push, and
  confirm CI.

## Surprises & Discoveries

- (2026-08-02T07:35:30Z) The released Catalog has two required Core Specs,
  while local unit fixtures intentionally keep one required Core entry. The
  real public smoke flow confirmed the generic resolver correctly reports and
  installs both without fixture-specific assumptions.
- (2026-08-02T07:38:00Z) A separate active R-002 Research workspace appeared
  concurrently and produces expected placeholder warnings in the canonical
  check. Impact: retain it as user-owned work, exclude `docs/RESEARCH.md` and
  `docs/research/active/r-002_*` from EP-008 commits, and record only the
  canonical exit-zero result for this EP.

## Decision Log

- (2026-08-02, repository owner) Detection is advisory; users explicitly choose
  optional Specs at installation/update time. Required Specs and dependency
  closure remain automatic. Reason: repository evidence can recommend relevant
  rules but cannot decide a project's intended engineering contract.
- (2026-08-02, Codex) Use repeatable non-interactive Spec IDs and a
  required-only flag instead of a terminal menu. Reason: the same command must
  be reviewable in dry-run output and reproducible in Codex, CI, and shell
  automation.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The user-visible behavior and local validation are complete. Detection no
longer makes a project-governance decision; it reports recommendations while
the manifest records explicit optional choices. Required and dependency
closure remain safe defaults. Final exact-revision evidence, archival, remote
push, and CI confirmation remain.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No new runtime dependency is allowed. Python 3.10+ standard library and Git
remain sufficient.

`scripts/spec_manager.py` will extend:

```python
def plan_spec_state(
    repo: Path,
    initial_source: dict[str, str],
    *,
    operation: str,
    allow_replace: bool,
    update_source: dict[str, str] | None = None,
    requested_spec_ids: tuple[str, ...] | None = None,
) -> SpecPlan: ...
```

`None` means preserve existing selection or use required-only for a new
manifest; an empty tuple means an explicit required-only selection; a non-empty
tuple is the complete desired optional direct set. `resolve_selection()`
continues to produce required dependency closure. `SpecPlan` must expose enough
Catalog metadata to render `available_specs`, configured IDs, recommendations,
and selected closure without rereading remote content.

Public CLI additions:

```text
foundryctl bootstrap [--spec ID ... | --required-only]
foundryctl spec update [--spec ID ... | --required-only]
```

`spec plan` discovers available and recommended Specs. `spec sync` does not
accept selection mutation. Fixed `--spec-version`, development `--spec-ref`,
manifest schema 1, lock schema 1, and `spec validate` offline behavior remain
unchanged.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-008_explicit-spec-selection/EXECPLAN.md`
- Approved consumer-contract ESP:
  `https://github.com/XiaoWeiKIN/EngineeringSpecifications/blob/codex/versioned-catalog-releases/proposals/0009_explicit-spec-selection.md`
- EngineeringSpecifications check:
  `artifacts/engineering-specifications-check.txt`
- Focused RepoFoundry tests: `artifacts/focused-tests.txt`
- Public required-only preview: `artifacts/required-only-preview.json`
- Public explicit-Go preview: `artifacts/explicit-go-preview.json`
- Public required-only update preview: `artifacts/required-only-update.json`
- Canonical RepoFoundry check: `artifacts/repo-foundry-check.txt`
- EP validation: `artifacts/epctl-validate.txt`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-02T07:11:08Z — Initial plan created.
- 2026-08-02T07:12:36Z — Replaced every placeholder with the selected public
  behavior, exact files/interfaces, safe deselection rules, milestones, and
  observable validation evidence before implementation.
- 2026-08-02T07:35:30Z — Updated current facts, validation evidence, progress,
  discovery, and retrospective after implementation and public-tag smoke
  verification.
