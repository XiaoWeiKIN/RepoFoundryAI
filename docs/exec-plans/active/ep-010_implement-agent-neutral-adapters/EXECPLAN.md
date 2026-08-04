---
schema_version: "2.5"
id: EP-010
title: "Implement Agent-neutral Harness and Engineering Spec adapters"
status: active
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-004", "ADR-002", "ADR-005", "ADR-010", "ADR-011", "ADR-012"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-04
updated: 2026-08-04
owner: "RepoFoundry Maintainer"
---

# Implement Agent-neutral Harness and Engineering Spec adapters

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry currently installs one Codex-shaped Harness even though its
repository facts, engineering documents, selected Engineering Specifications,
and immutable Spec lock are useful to every coding Agent. This change makes
those shared contracts an Agent-neutral Core and moves product discovery,
lifecycle payloads, context injection, and write interception behind explicit,
capability-declaring adapters.

After this plan, a repository owner can bootstrap `portable`, `codex`, or both
adapters. Portable bootstrap provides the shared Core, one canonical local
Engineering Specs activation engine, and a manual instruction route without
creating `.codex` state. Codex bootstrap preserves the existing `AGENTS.md`,
project Skill, trusted Hook, first-write injection, write gate, subagent, and
Stop-audit behavior. Both flows consume the same Spec selection, lock, local
Markdown, candidate calculation, dependency closure, and activation receipt
semantics. Existing schema 1 and 2 repositories remain readable and migrate to
schema 3 only through an explicit, preview-first upgrade.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 4 complete — repository acceptance is green.
- Current state: schema 3, the neutral activation protocol, Codex and portable
  adapters, explicit schema 1/2 migration, compatibility aliases, documentation,
  and regression coverage are implemented in the isolated worktree.
- Next action: commit the verified implementation, archive EP-010 against that
  exact revision, and run the governance check once more after archival.

## Context and Orientation

RepoFoundry is the root Skill and distribution in `SKILL.md`, with project
Bootstrap, Harness validation, migration, and Engineering Spec orchestration in
`scripts/foundryctl.py`. Its current Harness schema is 2 and contains one
`profile: codex@1.0.0`. Templates under `assets/harness-*.md` plus
`assets/engineering-specs-router/` generate repository documentation,
`AGENTS.md`, a project-local Router Skill, one copied Router executable, and
`.codex/hooks.json`.

`scripts/spec_manager.py` resolves the external Engineering Specifications Git
source, writes `docs/.engineering/specs.json` and `specs.lock.json`,
materializes managed Markdown, and validates content. It currently also checks
the Codex-specific `AGENTS.md` route; this plan removes that responsibility.
`assets/engineering-specs-router/scripts/spec_router.py` currently combines
product-neutral candidate, activation, digest, receipt, and audit logic with
Codex Hook event and output translation. It will become one canonical Core
engine at `.repo-foundry/engineering-specs/spec_router.py`; adapter-owned
entrypoints invoke that engine instead of embedding another implementation.

In this plan, **Core** means repository facts, neutral documentation, Harness
state, Spec state, migrations, normalized activation semantics, and validation
that has no product path or event knowledge. An **adapter** is a versioned
descriptor plus generated entrypoints that maps Core capabilities into a
specific runtime. `codex` is the native first-party adapter and `portable` is
the runtime-independent CLI/advisory adapter. **Enforcement** is reported as
`native`, `cli`, or `advisory`; it is a tested property, not a marketing label.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/index.md` | Current architecture map | Before changing boundaries |
| `docs/design-docs/agent-neutral-harness-adapters.md` | Accepted schema, adapter, activation, and migration design | Before every milestone |
| `docs/adr/adr-011_agent-neutral-harness-adapters.md` | Accepted Core/adapter ownership decision | Before Harness changes |
| `docs/adr/adr-012_agent-neutral-spec-activation.md` | Accepted activation-engine boundary | Before Router changes |
| `docs/adr/adr-010_spec-task-activation-router.md` | Codex parity and trusted-Hook safety contract | Before adapter extraction |
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Preview, provenance, rollback, and fail-closed rules | Before migration changes |
| `scripts/foundryctl.py` | Current Harness implementation and public CLI | During milestones 1 and 2 |
| `scripts/spec_manager.py` | Provider-neutral Spec lifecycle boundary | During milestone 3 |
| `assets/engineering-specs-router/scripts/spec_router.py` | Existing combined Router behavior to split | During milestone 2 |
| `tests/test_foundryctl.py` | Bootstrap, validation, and migration contracts | During milestones 1–3 |
| `tests/test_spec_router.py` | Activation and Codex Hook parity contracts | During milestones 2–3 |
| `scripts/check.py` | Canonical repository acceptance entrypoint | At every milestone and completion |

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-004", "ADR-002", "ADR-005", "ADR-010", "ADR-011", "ADR-012"].
- Design document references: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 established the repository's general evidence model: bounded control
records point to independently versioned content, downstream consumers use a
sealed interface, and compatibility is explicit. It enters this plan only
through ADR-001 and ADR-004's historical dependency closure; this plan does not
change Research storage or conclusions. No new empirical Research is required
because the relevant runtime boundaries, compatibility surface, and accepted
trade-offs are already fixed by ADR-011 and ADR-012.

ADR-001 and ADR-004 require independently installable professional Skills and
keep orchestration separate from execution planning. ADR-002 requires safe,
preview-first project bootstrap and a bounded Codex entrypoint, while ADR-011
amends it so Codex becomes one adapter over a neutral Core. ADR-005 keeps
normative Engineering Specifications external, immutable, and locally locked.
ADR-010 requires one local Router, explicit activation, digest verification,
first-write injection, supported-write gating, Stop audit, and a manual path;
ADR-012 amends it by assigning common semantics to the Activation Engine and
all product event/payload/output formats to adapters.

The accepted constraints are: schema 3 is strict and forward-failing; schema 1
and 2 remain readable; migration is explicit and rollback-safe; existing Spec
selection, lock, and Markdown bytes cannot change as a Harness side effect;
Core and adapter versions are independent; generated paths have one owner;
multiple adapters can coexist; receipts include adapter identity; adapter
inputs are untrusted; and enforcement claims cannot exceed tested capability.
Adapter removal, a Claude-specific adapter, and a cross-product lifecycle
standard are deliberately outside this plan.

No Benchmark Scenario is required because this is a deterministic contract and
migration change, not a performance, capacity, or comparative implementation
decision. Unit, integration, fixture, and canonical repository checks provide
the required evidence.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First, introduce immutable Core and adapter descriptors in
`scripts/foundryctl.py`, reorganize templates under Core and adapter ownership,
and emit strict Harness schema 3 records with ownership and capability data.
Add repeatable `--adapter`, `adapter list`, adapter-scoped validation, the
temporary `--profile codex` alias, and the omitted-option compatibility warning.
Keep legacy manifests readable and make the schema 2 to 3 migration explicit,
provenance-aware, preview-first, idempotent, and transactional.

Second, split the current Router so its canonical Core executable owns local
lock verification, candidates, activation, dependency closure, adapter-keyed
receipts, normalized lifecycle decisions, and audit. Keep a thin Codex adapter
responsible for Codex event names, tool input/path extraction, Hook output,
Skill discovery, trust instructions, and `.codex/hooks.json`. Add a portable
instruction entrypoint that calls the same Core commands without claiming
native interception.

Third, remove route ownership from `scripts/spec_manager.py`. Core validation
must pass with no `AGENTS.md`, `.codex/hooks.json`, or OpenAI metadata; selected
adapter validators check only their own routes and generated paths. Extend
tests with shared fixtures that prove Codex and portable compute identical Spec
results and coexist over one lock and engine.

Finally, update `SKILL.md`, README/reference documentation, asset metadata,
version declarations, and distribution contracts. Run focused tests, Skill
validation, ExecPlan/ADR validation, and the canonical repository check. Record
the exact revision and evidence only when every acceptance item is green.

## Milestones

### Milestone 1: Schema 3 and adapter-aware Harness

`foundryctl` exposes Core, Codex, and portable descriptors; bootstrap accepts
repeatable adapters; schema 3 records Core/adapter ownership; compatibility
inputs still work; schema 1/2 validation is read-only. Focused foundryctl tests
show portable bootstrap creates no Codex path, combined bootstrap has no
ownership collision, preview has no writes, and repeated apply is idempotent.

### Milestone 2: Shared Spec Activation Engine

One generated `.repo-foundry/engineering-specs/spec_router.py` implements the
neutral commands and normalized events. Codex Hook behavior moves behind a
thin adapter and portable instructions use the same engine. Focused Router
tests prove candidate, activation, dependency, digest, receipt, first-write,
mutation-gate, and Stop behavior, including adapter-isolated receipts.

### Milestone 3: Neutral validation and migration parity

Spec Manager validation no longer knows about Codex routes. Core-only,
portable-only, Codex-only, and coexistence repositories validate independently.
Explicit schema 2 migration installs/reclassifies generated paths only when
provenance permits it, preserves customized bytes and all Spec state, fails
closed on unknown versions, and rolls back on post-validation failure.

### Milestone 4: Product surface and repository acceptance

Root Skill and documentation describe an Agent-native, product-neutral system;
versions and generated metadata are synchronized. Both Skill packages validate,
all tests pass, `epctl validate` is clean, and `python3 -B scripts/check.py`
returns zero.

## Concrete Steps

Run every command from the repository root in the isolated implementation
worktree:

    cd /private/tmp/repofoundry-agent-adapters.omlsdZ/foundry

Inspect the public CLI and run focused tests while changing Harness behavior:

    python3 -B scripts/foundryctl.py adapter list
    python3 -B -m unittest tests.test_foundryctl

Expected: deterministic JSON lists `codex` and `portable`; tests finish with
`OK`. Exercise Router and Spec lifecycle changes with:

    python3 -B -m unittest tests.test_spec_router tests.test_spec_manager

Expected: all tests finish with `OK`, including Codex parity and adapter-neutral
fixtures. Validate repository contracts and Skills with:

    python3 -B -m unittest tests.test_repository_contracts
    python3 -B /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
    python3 -B /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py assets/adapters/codex/engineering-specs

Expected: repository contracts report `OK`; each Skill validator reports a
valid Skill. Before changing `agents/openai.yaml`, read
`/Users/wangxiaowei1/.codex/skills/.system/skill-creator/references/openai_yaml.md`
and regenerate or edit metadata to that contract.

Validate governance and the complete repository:

    python3 engineering-execution-plan/scripts/epctl.py --repo . validate
    python3 -B scripts/check.py

Expected: epctl reports `errors: 0`; the canonical check exits 0. Store any
long transcript or migration fixture output under
`docs/exec-plans/active/ep-010_implement-agent-neutral-adapters/artifacts/` and
link it from Progress rather than pasting it into this plan.

## Validation and Acceptance

- [x] From the repository root, run
  `python3 -B scripts/foundryctl.py bootstrap --adapter portable` against a
  clean fixture; expect a Core/portable preview with no `AGENTS.md` or `.codex`
  path and no writes. Evidence: `tests/test_foundryctl.py`.
- [x] Apply Codex and portable together, then repeat apply; expect one schema 3
  manifest, one canonical Activation Engine, unique generated-path ownership,
  unchanged bytes on the second run, and both adapter capability reports.
  Evidence: `tests/test_foundryctl.py`.
- [x] Exercise `--profile codex` and omitted adapter selection; expect Codex
  compatibility plus structured deprecation warnings, with no silent schema
  rewrite. Evidence: `tests/test_foundryctl.py`.
- [x] Migrate schema 2 fixtures in preview and apply modes; expect preview to
  make no writes, apply to preserve Spec manifest/lock/Markdown bytes, preserve
  customized generated bytes as a deterministic conflict, and rollback all
  touched paths after injected validation failure. Evidence:
  `tests/test_foundryctl.py`.
- [x] Run the same candidate paths and activation choices through portable Core
  commands and Codex events; expect identical direct IDs, dependency closure,
  requirements, digest checks, and audit outcomes, with receipts isolated by
  adapter ID. Evidence: `tests/test_spec_router.py`.
- [x] Validate Core Spec state in a fixture without `AGENTS.md`, OpenAI metadata,
  or `.codex/hooks.json`; expect success. Corrupt only a Codex route and expect
  Core validation to remain green while `validate --adapter codex` fails.
  Evidence: `tests/test_spec_manager.py` and `tests/test_foundryctl.py`.
- [x] Run `python3 -B -m unittest tests.test_foundryctl tests.test_spec_router tests.test_spec_manager tests.test_repository_contracts`; expect `OK`. Evidence: concise Progress transcript.
- [x] Run both required `quick_validate.py` commands; expect both Skill packages
  to validate. Evidence: concise Progress transcript.
- [x] Run `python3 engineering-execution-plan/scripts/epctl.py --repo . validate`;
  expect `errors: 0` and `warnings: 0`. Evidence: concise Progress transcript.
- [x] Run `python3 -B scripts/check.py`; expect exit code 0. Evidence: concise
  Progress transcript and archived `verification_evidence`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Bootstrap and upgrade are previews unless `--apply` is explicit. Planning reads
all Core and selected-adapter descriptors, rejects duplicate or conflicting
ownership, snapshots every path it may touch, and validates the complete
candidate state before publishing the manifest. A failed write or
post-validation restores original bytes and removes only files created by the
failed transaction. Re-running a successful apply is byte-idempotent.

Schema 1/2 readers never mutate. Schema 2 migration uses recorded template and
installed SHA-256 provenance: an unmodified generated Router may be split into
the canonical engine and Codex entrypoint; customized or legacy-unversioned
bytes are preserved and reported for manual reconciliation. The Spec manifest,
lock, managed Markdown, and Catalog release are copied neither forward nor
backward because Harness migration does not own them. Unknown future schema,
Core, adapter, protocol, template, or migration versions fail closed.

If implementation must be abandoned before apply tests pass, source changes in
this isolated branch can be reverted without touching the user's dirty primary
worktree. Generated test repositories live under test temporary directories.
Adapter removal is not implemented because safely deleting customized runtime
configuration requires a separate accepted decision.

## Progress

- [x] (2026-08-04T02:11:10Z) Created EP-010 with the dependency-closed Research,
  ADR, design, and architecture references.
- [x] (2026-08-04T02:11:50Z) Filled the execution, migration, recovery, and
  observable acceptance contract before product-code changes.
- [x] (2026-08-04T02:35:00Z) Implemented Milestone 1: strict schema 3,
  independently versioned Core/adapters, repeatable adapter selection,
  capability discovery, scoped validation, and compatibility warnings.
- [x] (2026-08-04T02:41:00Z) Implemented Milestone 2: one normalized Activation
  Engine plus thin Codex and portable entrypoints, with adapter-isolated
  receipts and Codex behavior parity.
- [x] (2026-08-04T02:47:00Z) Implemented Milestone 3: adapter-neutral Spec
  validation and transactional, preview-first schema 1/2 to 3 migration that
  preserves Spec state and refuses unsafe overwrites.
- [x] (2026-08-04T02:56:03Z) Completed Milestone 4 documentation and validation.
  The focused suite passed 72 tests; both Skill validators reported valid;
  `epctl validate` reported 0 errors and 0 warnings; the canonical check passed
  Research 29, Benchmark 8, Execution Plan 37, and RepoFoundry 72 tests. See
  `artifacts/validation-summary.txt`.

## Surprises & Discoveries

- EP creation required R-001 and ADR-001 because ADR-004 amends ADR-001; the
  dependency closure is historical and introduces no new Research question.
- Legacy schema 1/2 migration needs the old planning algorithms as frozen,
  private executable references until the compatibility window closes; public
  schema 3 entrypoints are separate and covered by regression tests.
- Bootstrap can modify existing repository guidance as well as generated
  Harness files, so transactional rollback must snapshot the complete planned
  write set rather than only the manifest and newly generated files.

## Decision Log

- 2026-08-04 — Implement Codex and portable as the first adapters, keep the
  compatibility alias for one release, and defer adapter removal exactly as
  accepted in ADR-011 and ADR-012.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry 0.2.0 now has one Agent-neutral Core and explicit Codex 2.0.0 and
portable 1.0.0 adapters. Engineering Spec selection, locking, dependency
closure, activation, digest checking, receipts, and audit remain common; only
runtime discovery and lifecycle translation are adapter-owned. This makes the
system usable without Codex paths while preserving the native Codex write gate
and Stop audit when that adapter is selected.

Compatibility is explicit: existing schema 1/2 repositories remain readable,
upgrade only through preview then apply, and retain their Spec bytes. Existing
`--profile codex` and omitted-selection behavior continue for the documented
window with machine-readable deprecation warnings. Unknown future component
versions and unsafe customized generated files fail closed.

The principal trade-off is temporary implementation weight: frozen v0.1
migration logic remains private alongside schema 3 until the compatibility
window can be retired by a future decision. The benefit is deterministic,
offline migration without weakening provenance or silently rewriting user
content.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

The implementation uses only Python's standard library and the existing local
Git-based Spec fixtures; it adds no network or runtime dependency. Public CLI
compatibility covers `bootstrap --profile codex`, default Codex selection,
`validate --harness`, legacy schema readers, and existing Spec commands.

Harness schema 3 exposes `producer`, `core`, `adapters`, `components`,
`instruction_files`, `files`, and `applied_migrations`. Each adapter descriptor
has a stable ID, semantic version, enforcement level, capability declaration,
owned template records, and validator. File records retain template and
installed digests and add `owner_kind: core|adapter`; adapter-owned records also
carry `owner_id`.

The activation protocol is version 1. Its normalized envelope contains
`protocol_version`, `event`, `adapter_id`, opaque `session_id` and `turn_id`,
optional prompt/planned paths, and a neutral tool category/name/input.
Supported events are `session_start`, `subagent_start`, `before_mutation`, and
`stop`. Receipts are keyed by repository identity, adapter ID, session ID, and
turn ID. Codex-specific event names and Hook JSON cannot appear in Core event
handling; portable callers use `begin`, `candidates`, `activate`, `status`, and
`audit` against the same engine.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-010_implement-agent-neutral-adapters/EXECPLAN.md`
- Validation summary: `docs/exec-plans/active/ep-010_implement-agent-neutral-adapters/artifacts/validation-summary.txt`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-04T02:11:10Z — Initial plan created.
- 2026-08-04T02:56:03Z — Recorded completed implementation, compatibility
  behavior, rollback coverage, and green acceptance evidence before archival.
