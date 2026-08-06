---
schema_version: "2.7"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-014
title: "Require an explicit decision for new optional Specs"
status: active
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-004", "ADR-002", "ADR-005", "ADR-010", "ADR-011", "ADR-012"]
adr_constraint_refs: []
adr_evidence: ["ADR-001@sha256:9866f72aa09c400b36a9993681a73f7131381a28179a1f0832cd6a89a2ca8fae", "ADR-004@sha256:401daee8795f70b9c0816e02e655e874bc20c37603b937fe831009bb5a80ef98", "ADR-002@sha256:a9ced6c6e80b1e246bd8fc7b90e53b7e9e6aff18a590c545f904dbf59ce61ad7", "ADR-005@sha256:4df850ebff7b23b00663ffdd9142ed03633e5c93f6cd61b4e6af3fa38d3f1d69", "ADR-010@sha256:b0a68a290d59d1279f40d8f1937b4d5ae8f85bc1766eb890a7151554adef364e", "ADR-011@sha256:82b6ab8dc9cec0a0c9f8951198de43cc5bbd17510913d5a061b91d363231a6df", "ADR-012@sha256:410121e886544b41db4c29b2e757b422fa2c3e1dfcf14e55ff714a2a9e79df86"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: not_required
architecture_decision_gate_reason: "This patch enforces the already accepted explicit-selection and preview-first contracts without changing Catalog ownership, manifest or lock schemas, adapter boundaries, or activation semantics."
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-06
updated: 2026-08-06
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Require an explicit decision for new optional Specs

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

When a Catalog update exposes optional Engineering Specifications that are not
part of the project's configured set, RepoFoundry must stop treating silent
selection preservation as sufficient authorization. The dry-run will report a
machine-readable selection decision with every candidate's ID, description,
dependencies, recommendation state, and current configuration. Apply will fail
before writes until the repository owner explicitly selects the complete
optional set, chooses required-only, or confirms that the current selection
must be kept.

The behavior is observable by updating an existing fixture from a Catalog that
contains only `languages/go` to a later Catalog that also contains
`languages/go/functional-options` and `languages/go/factory-delegation`.
`spec update --spec-version ...` must return
`selection_decision.status: required`; the same command with `--apply` must
return `SPEC_SELECTION_DECISION_REQUIRED` and leave the repository byte
unchanged. `--keep-selection`, `--required-only`, or the complete repeated
`--spec` set resolves the decision and permits the normal preview/apply flow.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — deliver and publish `v0.3.1`.
- Current state: Core and CLI enforce the explicit selection decision; Skills,
  bilingual docs, migration coverage and evidence are updated. Focused tests,
  the 103-test RepoFoundry suite, canonical integrity and EP validation pass.
- Next action: commit, open the PR, verify CI, merge, tag and validate the public
  installer against the merged release.
- Open questions: none that change the route.

## Context and Orientation

`scripts/spec_manager.py` resolves an external Git Catalog, computes the
configured direct IDs and dependency-closed selected IDs, plans manifest/lock
and managed-file writes, and renders the public dry-run payload.
`scripts/foundryctl.py` owns CLI parsing, the dry-run/apply boundary, Harness
Bootstrap, upgrade migrations, and distribution/Core version planes.

An optional Spec is a Catalog entry with `required: false`. The manifest stores
the complete direct project selection; dependencies are added only to the lock.
`requested_spec_ids is None` currently means preserve an existing selection,
while `()` means explicit required-only and a non-empty tuple means the complete
optional direct set. The defect occurs when a source-changing update introduces
unconfigured optional entries and `None` reaches apply without a human decision.

The generated project workflow in
`assets/core/repo-foundry-ai/SKILL.md` governs every adapter because Codex and
Claude adapter Skills delegate to it. The distribution root `SKILL.md` governs
personal installation and Spec management before a project Harness exists.
Both must require agents to consume the structured decision instead of
inventing `--keep-selection`.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/exec-plans/completed/ep-008_explicit-spec-selection/EXECPLAN.md` | Accepted explicit-selection behavior and prior evidence | Before changing semantics |
| `scripts/spec_manager.py` | Catalog, selection, planning, apply and JSON payload boundary | Before Core edits |
| `scripts/foundryctl.py` | Public CLI, mode boundary, Bootstrap and version migration | Before CLI/version edits |
| `tests/test_foundryctl.py` | Isolated Git Catalog integration contract | While implementing |
| `docs/design-docs/engineering-spec-management.md` | Authoritative selection/update design | Before docs or behavior changes |
| `docs/design-docs/agent-neutral-harness-adapters.md` | Core/adapter ownership and version planes | Before generated Skill/version edits |
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Distribution and Harness upgrade compatibility | Before preparing `0.3.1` |
| `SKILL.md`, `assets/core/repo-foundry-ai/SKILL.md` | Agent-facing decision workflow | Before delivery |

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture decision gate: `not_required`.
- Architecture compliance: `applicable`.
- ADR references: ["ADR-001", "ADR-004", "ADR-002", "ADR-005", "ADR-010", "ADR-011", "ADR-012"].
- ADR constraint references: [].
- ADR evidence: ["ADR-001@sha256:9866f72aa09c400b36a9993681a73f7131381a28179a1f0832cd6a89a2ca8fae", "ADR-004@sha256:401daee8795f70b9c0816e02e655e874bc20c37603b937fe831009bb5a80ef98", "ADR-002@sha256:a9ced6c6e80b1e246bd8fc7b90e53b7e9e6aff18a590c545f904dbf59ce61ad7", "ADR-005@sha256:4df850ebff7b23b00663ffdd9142ed03633e5c93f6cd61b4e6af3fa38d3f1d69", "ADR-010@sha256:b0a68a290d59d1279f40d8f1937b4d5ae8f85bc1766eb890a7151554adef364e", "ADR-011@sha256:82b6ab8dc9cec0a0c9f8951198de43cc5bbd17510913d5a061b91d363231a6df", "ADR-012@sha256:410121e886544b41db4c29b2e757b422fa2c3e1dfcf14e55ff714a2a9e79df86"].
- Design document references: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 is audit-only for this patch. Its sealed conclusion requires bounded,
versioned file contracts between independently installable Skills; the patch
therefore keeps the decision in provider-neutral JSON and does not call another
Skill at runtime.

No new architecture decision is required. The repository owner fixed the
desired fail-closed behavior, while EP-008 and the accepted ADR set already
establish: external Catalog ownership, explicit project selection,
preview-before-apply, one shared Core, thin product adapters, immutable locks,
and truthful enforcement. This patch adds an acknowledgement state inside that
boundary. It does not change Catalog, manifest, lock, Requirement index, or
activation protocol schemas.

Implementation constraints:

- A dry-run must always succeed when the Catalog and repository are valid, so
  an Agent can present the unresolved candidates.
- Apply must fail before acquiring or mutating managed paths when the decision
  is unresolved.
- A decision is required only for an existing-manifest `spec update` whose
  resolved Catalog source, identity, version, digest or revision changes and
  whose Catalog contains optional IDs absent from the prior dependency-closed
  selection.
- The candidates are every unconfigured optional ID in deterministic Catalog
  order, including entries without detection metadata. This covers newly
  published specialized Specs such as functional options and factory
  delegation.
- `--keep-selection` is mutually exclusive with `--spec` and
  `--required-only`. It resolves only the human acknowledgement; it never
  changes manifest IDs.
- Agents must not infer `--keep-selection`. They must show candidates and
  dependencies and obtain an explicit user choice first.
- Existing source refreshes, `spec sync`, validation, initial required-only
  Bootstrap, and updates with no unconfigured optional entries remain
  compatible.
- Distribution `0.3.1` and Core `1.2.1` are patch increments. Adapter and
  activation protocol versions remain unchanged because adapter entrypoints and
  task-time activation semantics do not change.
- No Benchmark gate is required: this is deterministic control-flow and JSON
  behavior verified by unit, integration, migration, and real-install checks.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-001 | Keep the selection decision as a versioned Core file/CLI contract; do not introduce runtime Skill coupling. | Independent-package and repository-contract tests remain green. |
| ADR-004 | Keep Spec orchestration in root RepoFoundry; EP owns only this evidence document. | Repository ownership tests and canonical check. |
| ADR-002 | Preserve preview-first, non-overwriting Bootstrap and the 100-line instruction boundary. | Bootstrap and migration regression tests. |
| ADR-005 | Resolve only untrusted external Catalog data, retain immutable lock and offline validation, and never persist credentials. | Git fixture, drift, source-lock and offline validation tests. |
| ADR-010 | Preserve one local Router and task-time activation; selection management remains a separate pre-task workflow. | Router parity tests and unchanged activation protocol version. |
| ADR-011 | Put decision semantics in the Core and keep product adapters thin and capability-honest. | Core `1.2.1` migration plus multi-adapter tests. |
| ADR-012 | Do not fork selection or activation behavior per runtime; every adapter consumes the same project Core Skill. | Codex/Claude delegation asset tests and portable contract checks. |

Every structured constraint from every referenced ADR must appear exactly once.
For a legacy ADR without structured constraints, restate its applicable decision
at document level. Design Docs are explanatory inputs and cannot override an ADR.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First extend `SpecPlan` with a deterministic selection-decision record. Capture
whether an existing update changes the Catalog source, compute unconfigured
optional candidates in Catalog order, record how the decision was resolved,
and expose the record through `plan_payload`. Add a pre-write check to
`apply_spec_plan` so every current and future caller inherits the same gate.

Then add `--keep-selection` to only `spec update` and thread the explicit
acknowledgement through `manage_specs` and locked re-planning. Keep the three
selection controls mutually exclusive. Add focused integration tests for the
unresolved preview, rejected apply with byte-identical repository state, each
resolution path, irrelevant operations, and deterministic candidates that have
no detection metadata.

Finally update the distribution and generated Core Skills, bilingual docs,
design and migration contracts, eval/repository assertions, and version planes
to `0.3.1` / Core `1.2.1`. Run focused and canonical validation, deliver through
a reviewed PR, publish an annotated `v0.3.1` tag and Latest GitHub Release, then
verify explicit and `latest` installation in an isolated prefix.

## Milestones

### Milestone 1: Make the selection decision mechanical

The Core payload identifies unresolved candidates and apply fails closed until
one of the three explicit resolution paths is present. Focused
`tests.test_foundryctl` cases pass and prove no bytes change on refusal.

### Milestone 2: Propagate the contract through the Harness

Root and generated Core Skills require user confirmation, public English and
Chinese docs describe the flow, and a `0.3.0 -> 0.3.1` Harness upgrade replaces
only provenance-matching Core Skill bytes. Adapter and protocol versions remain
stable.

### Milestone 3: Verify and publish `v0.3.1`

Focused tests, canonical integrity, EP validation and an isolated end-to-end
Catalog upgrade pass. A PR is merged, annotated tag and Latest Release are
published, and the public installer resolves the exact merge commit and is
idempotent through `latest`.

## Concrete Steps

From `/Users/wangxiaowei1/xiaowei/RepoFoundryAI`:

```bash
python3 -B -m unittest tests.test_foundryctl tests.test_installer tests.test_repository_contracts
python3 -B scripts/check.py
python3 engineering-execution-plan/scripts/epctl.py --repo . validate
```

Before commit, run an isolated Git fixture that starts with an old Catalog,
updates to a new Catalog with two specialized optional Specs, captures the
unresolved dry-run, proves rejected apply has no diff, and applies an explicit
resolution. Store the concise JSON evidence under this EP's `artifacts/`.

After merge, create and push annotated `v0.3.1`, publish the GitHub Release,
then run `install.py --version 0.3.1 --host none --json` and repeat with
`--version latest` in an exact temporary prefix.

## Validation and Acceptance

- [x] Run the focused unittest command above; expect every selection,
  installer, migration, asset and repository-contract test to pass. Evidence:
  `artifacts/focused-tests.txt`.
- [x] Preview an old-to-new Catalog update without selection arguments; expect
  `selection_decision.status == "required"`, deterministic specialized
  candidates, descriptions and dependency metadata. Evidence:
  `artifacts/selection-decision-e2e.json`.
- [x] Apply the unresolved preview; expect
  `SPEC_SELECTION_DECISION_REQUIRED`, a non-zero exit, and byte-identical
  manifest, lock, managed content and Git status. Evidence:
  `artifacts/selection-decision-e2e.json`.
- [x] Resolve with explicit repeated `--spec`, `--required-only`, and
  `--keep-selection` in isolated resolution steps; expect each dry-run/apply pair to
  report its resolution and preserve dependency closure. Evidence:
  `artifacts/selection-decision-e2e.json`.
- [x] Run `python3 -B scripts/check.py`; expect 32 Research, 9 Benchmark, 48
  Execution Plan and all RepoFoundry tests plus integrity checks to pass.
  Evidence: `artifacts/canonical-check.txt`.
- [x] Run `epctl validate`; expect zero errors, allowing only existing
  ready-to-archive warnings for unrelated active plans. Evidence:
  `artifacts/epctl-validate.txt`.
- [ ] Verify the PR's Python 3.10, Python 3.14 and `ep-integrity` checks all
  succeed before merge. Evidence: GitHub Actions URL in this plan.
- [ ] Install the published `0.3.1` Release in an isolated prefix, repeat with
  `latest`, and expect the exact merge commit, `unchanged` on repetition, CLI
  version `0.3.1`, and no project Harness changes. Evidence recorded in the
  Release and `artifacts/post-publication-install.json`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Dry-run remains side-effect free. The unresolved decision is data in the plan,
not repository state. Apply checks it before writes, then recomputes the same
plan under the existing repository lock; a changed plan still aborts.

`--keep-selection` is idempotent because it preserves direct IDs. Explicit
`--spec` and `--required-only` retain existing atomic write, digest-guarded
removal and rollback behavior. A failed update can be retried after choosing a
resolution. Rollback uses the previous explicit Spec set/source through another
previewed update or a Git revert of repository-owned state.

Harness upgrade replaces the generated Core Skill only when its installed
digest proves it is unmodified. Customized bytes remain a deterministic
manual-merge conflict. Distribution installation retains immutable `0.3.0`
alongside `0.3.1`, so users can activate the prior release if necessary.

## Progress

- [x] (2026-08-06T04:48:23Z) Plan created with the accepted architecture input set.
- [x] (2026-08-06T05:02:00Z) Reproduced the root cause from EP-008, CLI code,
  Catalog `1.5.0`, and the referenced task; fixed the fail-closed contract and
  completed every required plan section before implementation.
- [x] (2026-08-06T06:02:00Z) Implemented the structured decision payload,
  pre-write failure, `--keep-selection`, deterministic candidate enumeration
  and all three resolution paths; focused and canonical tests pass.
- [x] (2026-08-06T06:08:00Z) Updated root/project Skills, bilingual docs,
  design contracts, distribution `0.3.1`, Core `1.2.1`, and verified the
  provenance-safe `0.3.0` migration without changing locked Spec state.
- [ ] Merge the reviewed PR and publish the verified release.

## Surprises & Discoveries

- (2026-08-06T04:52:00Z) The specialized Go Specs have no Catalog detection
  rules, so recommendation-only gating would repeat the original failure.
  Source-changing update review must enumerate every unconfigured optional ID.

## Decision Log

- (2026-08-06, repository owner) New optional Specs exposed by a Catalog update
  require a user choice before apply. Reason: project engineering policy cannot
  be inferred from the update command or repository evidence.
- (2026-08-06, Codex) Keep the CLI non-interactive and add a structured
  decision plus `--keep-selection`. Reason: the same contract must work in
  Codex, Claude, portable CLI and automation while still producing a reviewable
  dry-run.
- (2026-08-06, Codex) Bump distribution to `0.3.1` and Core to `1.2.1`; keep
  adapter and activation protocol versions stable because their files and
  task-time semantics do not change.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

Implementation and local verification are complete. The mechanical gate closes
the authorization gap without changing the manifest, lock, adapter or
activation-protocol schemas. Publication evidence and the final verified
revision remain pending until the reviewed PR is merged.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No new dependency is permitted; Python 3.10+ standard library and Git remain
sufficient.

`SpecPlan` gains immutable fields equivalent to:

```python
selection_decision_status: str
selection_decision_reason: str
selection_candidate_ids: tuple[str, ...]
selection_resolution: str
```

`plan_spec_state(..., keep_selection: bool = False)` determines the state.
`plan_payload` emits one strict `selection_decision` object. `apply_spec_plan`
raises `SPEC_SELECTION_DECISION_REQUIRED` when status is `required`.

Public CLI resolution controls are mutually exclusive:

```text
foundryctl spec update [--spec ID ... | --required-only | --keep-selection]
```

`--keep-selection` is valid only on `spec update`. It acknowledges the
displayed candidates without changing the manifest's direct IDs.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-014_explicit-spec-decision-gate/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-06T04:48:23Z — Initial plan created.
- 2026-08-06T05:02:00Z — Replaced template placeholders with the bounded
  fail-closed selection, compatibility, versioning, validation and publication
  contract after inspecting EP-008 and current Catalog metadata.
- 2026-08-06T06:08:00Z — Recorded passing Core, migration, installer,
  repository-contract, canonical and EP validation evidence; advanced the plan
  to PR and release delivery.
