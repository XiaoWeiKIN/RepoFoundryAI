---
schema_version: "2.7"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-013
title: "Implement Requirement-level Specification context activation"
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
architecture_decision_gate_reason: "The approved ESP fixes requirement-level exact-context activation within the existing single-Router and Agent-neutral Core boundaries, so no new durable alternative decision is required."
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-05
updated: 2026-08-05
author: "Codex"
owner: "Unassigned"
---

# Implement Requirement-level Specification context activation

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Large installed Engineering Specifications currently enter an Agent turn as
whole Markdown documents. This plan implements the approved
EngineeringSpecifications requirement-level activation contract so an Agent
first selects applicable Specs, then exact Requirement IDs, and receives a
digest-verifiable context capsule containing only the interpretation frame,
selected Requirement blocks, their dependency closure, and matching
Verification rows. A user can observe the change through Router requirement
cards, protocol-v2 activation receipts, bounded capsule byte counts, and tests
that prove unrelated Requirement text is absent.

```mermaid
flowchart LR
    T["Task and planned paths"] --> S["Applicable Specs"]
    S --> C["Bounded Requirement cards"]
    C --> R["Direct Requirement IDs"]
    R --> D["Exact dependency closure"]
    D --> X["Digest-verified context capsule"]
    X --> W["Implementation or review"]
```

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 complete; verified-revision archival pending.
- Current state: the Catalog 1.5 authoring contract, deterministic Requirement
  index, protocol-v2 Router, exact capsules, epoch rehydration, adapter
  migrations, bilingual documentation, and isolated end-to-end evidence are
  implemented. The two repositories remain intentionally uncommitted.
- Next action: review and commit both working trees, then archive this plan
  against the verified RepoFoundry revision.

## Context and Orientation

EngineeringSpecifications owns normative Markdown, Requirement IDs, versions,
and Catalog digests. Its `scripts/check.py` validates five current Specs under
`specification/`; `catalog.json` supplies Spec dependency and routing metadata.
The approved ESP is
`proposals/0000_requirement-level-context-activation.md` with a synchronized
Chinese rendering beside it.

RepoFoundry owns consumption. `scripts/spec_manager.py` resolves and
materializes locked Specs into a target repository and renders the managed
index. `assets/core/engineering-specs/spec_router.py` is the canonical offline
Activation Engine. Thin entrypoints under `assets/adapters/` expose the same
engine to Codex, Claude, and portable clients. `scripts/foundryctl.py` packages,
migrates, and validates those generated files. `tests/test_spec_router.py`,
`tests/test_spec_manager.py`, and `tests/test_foundryctl.py` are the principal
contract suites.

A *Requirement card* is bounded routing metadata, never normative replacement
text. A *direct Requirement* is explicitly selected for the task. A *resolved
Requirement* is in the exact transitive closure of direct IDs. A *context
capsule* is deterministic UTF-8 content assembled from verified local bytes.
An *interpretation frame* contains the Spec metadata and shared sections needed
to read a Requirement correctly. An *epoch* is a context-lifetime identifier
that changes at a new turn, compaction resume, fork, or subagent start.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| EngineeringSpecifications approved ESP | Fixes metadata, graph, capsule, receipt, budget, and fallback semantics | Before changing either repository |
| `docs/adr/adr-005_external-engineering-specifications.md` | Keeps normative content outside RepoFoundry | Before changing materialization |
| `docs/adr/adr-010_spec-task-activation-router.md` | Preserves one Router, offline bytes, explicit activation, and fail-closed writes | Before changing Router behavior |
| `docs/adr/adr-011_agent-neutral-harness-adapters.md` | Keeps Core and product adapters independently owned | Before changing generated assets |
| `docs/adr/adr-012_agent-neutral-spec-activation.md` | Requires one shared Activation Engine and normalized protocol | Before changing receipts or events |
| `docs/design-docs/engineering-spec-management.md` | Defines Catalog, lock, materialization, and managed-index contracts | Before changing `spec_manager.py` |
| `docs/design-docs/agent-neutral-harness-adapters.md` | Defines version planes, installed layout, migrations, and parity | Before changing `foundryctl.py` or adapters |
| `scripts/check.py` | Canonical RepoFoundry repository validator | Before completion |

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

R-001 establishes the general control-plane pattern used here: a bounded index
and synthesis interface should route into a larger sealed document set instead
of injecting the entire corpus. The selected ESP applies that pattern to
normative Requirements and supplies the missing exact extraction contract.

ADR-001 and ADR-004 keep research, execution planning, and workflow
orchestration as separate owners. ADR-002 assigns project bootstrap and short
instruction routing to RepoFoundry. ADR-005 keeps normative Spec authorship,
versions, and digests in EngineeringSpecifications while RepoFoundry owns Git
resolution, locking, local materialization, and validation. ADR-010 requires
exactly one project Router, local-only task activation, explicit no-Spec
decisions, digest verification, write gating, and manual fallback. ADR-011
requires an Agent-neutral Core plus independently versioned adapters. ADR-012
requires candidate, activation, dependency, receipt, injection, and audit
semantics to remain in one Core engine.

No new ADR is required because the user-approved ESP selects requirement-level
exact-context activation and explicitly preserves those accepted boundaries.
Implementation choices must therefore be deterministic formats and internal
interfaces, not competing durable architectures. The main validation unknown
is the exact smallest useful interpretation-frame extraction; the ESP resolves
it by naming mandatory headings and permitting only explicitly selected
supporting sections. Tests, not a new decision record, will settle parser edge
cases.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-001 | Keep Research evidence and execution state outside Router runtime artifacts. | EP validation proves only references to sealed R-001; repository tests prove no Research mutation. |
| ADR-004 | Keep requirement activation in RepoFoundry orchestration, not the execution-plan package. | Diff inspection and canonical checks show no activation code under `engineering-execution-plan/`. |
| ADR-002 | Preserve bounded project instructions, preview-first bootstrap, and non-overwrite behavior. | `tests/test_foundryctl.py` migration, preservation, and idempotence cases pass. |
| ADR-005 | EngineeringSpecifications owns normative metadata; RepoFoundry consumes immutable local bytes and lock digests. | Both canonical checks plus tamper/drift tests pass with no bundled normative Spec copies. |
| ADR-010 | Preserve one Router, offline activation, dependency closure, explicit none, path gate, and manual fallback while narrowing injection. | Router unit/integration tests cover candidates, cards, activation, first-write injection, none, status, and audit. |
| ADR-011 | Add the capability in Core and keep adapter assets thin and independently versioned. | Repository contract tests and multi-adapter bootstrap/validation pass. |
| ADR-012 | Use protocol v2 in the single Core engine; adapters only translate lifecycle events and outputs. | Core/manual/Codex parity tests produce identical direct/resolved IDs and capsule digest. |

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

First, amend the approved ESP status and implement its authoring contract in
EngineeringSpecifications. Add `Activation` and `Context dependencies` metadata
to every current Requirement, teach `scripts/check.py` to validate size,
references, allowed cross-Spec edges, and graph acyclicity, update the template
and explanatory documents, bump affected Spec and Catalog versions, refresh
SHA-256 values, and add negative tests.

Second, extend RepoFoundry materialization with a deterministic requirement
index derived from exact managed/project Spec bytes. The index records cards,
owners, source digests, block byte ranges/hashes, dependencies, and verification
coordinates without duplicating normative block text. Validation regenerates
the index and compares exact bytes.

Third, upgrade the shared Activation Engine to protocol v2. Add two-stage card
discovery, exact Requirement selection and closure, deterministic frame/block/
verification extraction, configurable 16 KiB card and 32 KiB capsule budgets,
explicit overflow/fallback modes, epoch-aware receipts, and exact rehydration.
Preserve whole-Spec fallback for legacy documents and existing explicit-none,
path-coverage, mutation-gate, and audit semantics. Update thin adapter
instructions, generated template versions/migrations, docs, and tests.

Finally, run targeted suites while iterating, both canonical checks, and an
isolated end-to-end fixture that materializes the changed Catalog into a
bootstrapped project and proves unrelated Requirement text is not injected.

## Milestones

### Milestone 1: Normative Requirement routing contract is mechanically valid

Every cataloged Requirement has bounded activation metadata and an exact,
acyclic dependency declaration. Invalid references, wildcards, missing
metadata, oversized blocks, and illegal cross-Spec dependencies fail the
central checker. `python3 -B scripts/check.py` passes in
EngineeringSpecifications.

### Milestone 2: RepoFoundry materializes and activates exact Requirements

The managed requirement index is deterministic and validated; Router card
selection, exact closure, capsule assembly, budget handling, receipt v2, epoch
rehydration, and legacy fallback work through the shared Core. Targeted
RepoFoundry tests pass.

### Milestone 3: Generated consumers and end-to-end evidence agree

Codex, Claude, and portable instructions expose the same protocol truthfully;
template versions and explicit migrations protect existing custom bytes. Both
canonical checks and an isolated materialize/activate/audit flow pass.

## Concrete Steps

1. In `/Users/wangxiaowei1/xiaowei/EngineeringSpecifications`, edit
   `specification/`, `scripts/check.py`, `tests/test_catalog.py`, the Catalog,
   proposal status, and model/readme/changelog documents. Run:

       python3 -B scripts/check.py

   Expect exit code 0 and the repository success summary.

2. In `/Users/wangxiaowei1/xiaowei/RepoFoundryAI`, edit
   `scripts/spec_manager.py`, `assets/core/engineering-specs/spec_router.py`,
   `scripts/foundryctl.py`, adapter instructions, design/reference docs, and
   focused tests. Run:

       python3 -B -m unittest tests.test_spec_router tests.test_spec_manager tests.test_foundryctl

   Expect all selected tests to pass.

3. Run the complete RepoFoundry contract:

       python3 -B scripts/check.py

   Expect exit code 0 with no schema, template, migration, adapter, or test
   failure.

4. Create an isolated Git fixture from the local EngineeringSpecifications
   working tree, bootstrap a temporary target, activate one Go Requirement, and
   inspect the receipt/capsule JSON. Expect exact direct and resolved IDs,
   matching SHA-256/byte counts, no unrelated sentinel Requirement, and no
   network access during Router commands.

## Validation and Acceptance

- [x] From EngineeringSpecifications, run `python3 -B scripts/check.py`; expect
  all catalog, metadata, dependency, digest, link, and unit checks to pass.
  Evidence: 20 tests passed and
  `CHECK_OK: io.github.xiaoweikin.engineering-specifications@1.5.0 (5 specifications)`.
- [x] From RepoFoundryAI, run the focused `unittest` command in Concrete Steps;
  expect zero failures. Evidence: 72 tests passed in 55.966 seconds.
- [x] From RepoFoundryAI, run `python3 -B scripts/check.py`; expect the complete
  canonical check to pass. Evidence: all integrity stages passed, including 101
  RepoFoundry/repository-contract tests; one unrelated pre-existing EP-006
  archive-readiness warning remains.
- [x] Run the isolated end-to-end fixture; expect a protocol-v2 receipt with
  exact IDs, deterministic digest/bytes, bounded mode, and unrelated text
  absent. Evidence: `artifacts/requirement-context-e2e.json`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

All source edits are additive or version-bumped and remain reviewable in Git.
Central digest refresh is repeated only after Markdown stabilizes. Generated
requirement-index rendering is pure and byte-deterministic, so repeated sync is
idempotent. Bootstrap/upgrade keeps the existing preview, provenance, atomic
write, rollback, and customization-conflict behavior; it may replace only
unmodified generated assets with recorded provenance. Runtime receipt writes
use atomic replacement and can be deleted safely because receipts are
ephemeral. A malformed index, digest drift, unsupported protocol, graph cycle,
or budget overflow fails before mutation/context injection and reports a
deterministic remediation. Legacy Specs without routing metadata use explicit
whole-Spec fallback instead of partial parsing.

## Progress

- [x] (2026-08-05T08:43:48Z) Plan created with sealed Research and accepted architecture inputs.
- [x] (2026-08-05T08:52:00Z) Read the referenced Synthesis, ADR consequences, and four Design Docs; filled the executable plan before source implementation.
- [x] (2026-08-05T09:05:00Z) Implemented Milestone 1: 32 Requirements now carry bounded Activation metadata and an exact acyclic context graph; Catalog 1.5.0 and its 20-test canonical check pass.
- [x] (2026-08-05T09:28:00Z) Implemented Milestone 2: materialization emits a verified exact-range index and the protocol-v2 Router tests pass for cards, closure, capsules, budgets, drift, and rehydration.
- [x] (2026-08-05T09:46:53Z) Built a fresh local Git Catalog fixture and proved a 16,308-byte factory-absence capsule, five-ID closure, exact digest replay, epoch 2 rehydration, and unrelated Requirement exclusion.
- [x] (2026-08-05T09:51:00Z) Completed Milestone 3: 72 focused tests, 101 full
  RepoFoundry/repository-contract tests, both canonical checks, adapter/package
  validation, and isolated Catalog-to-capsule evidence pass.

## Surprises & Discoveries

- The first exact factory-absence capsule was 17,688 bytes: valid under the
  32 KiB protocol budget and 81.25% smaller than whole-Spec injection, but above
  the ESP prototype's 16 KiB scenario target. Repeated non-normative text in the
  factory interpretation frame accounted for the difference. Compacting that
  frame without changing any Requirement behavior produced a 16,308-byte
  capsule and an 82.5% reduction from the current 93,194-byte Spec closure.
- Older installed projects can lack `requirements.json`. Runtime routing keeps
  them usable in whole-Spec compatibility mode, while offline Spec validation
  deliberately asks for a previewed `spec sync --apply` to generate the exact
  index.

## Decision Log

- 2026-08-05 — Keep `requirements.json` derived and outside the Spec lock
  schema. Exact local source digests and byte ranges make regeneration and drift
  detection sufficient without changing Catalog or manifest schema.
- 2026-08-05 — Require a recorded reason only when raising the 32 KiB capsule
  default. Lower diagnostic budgets remain directly configurable; normative
  bytes are never truncated at either setting.
- 2026-08-05 — Preserve the old `activate --spec` spelling as a legacy
  whole-Spec alias so existing generated consumers remain readable, while all
  new instructions require exact IDs or an explicit reasoned fallback.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The implementation changes the normal context unit from an installed Markdown
document to an exact Requirement closure. The representative factory task
loads 16,308 bytes instead of 93,194 whole-Spec bytes, preserves all five
dependency Requirements and their interpretation frames, and excludes an
unrelated factory-test Requirement. The capsule survives rehydration with the
same SHA-256 while its context epoch advances.

The central repository now rejects missing/oversized activation metadata,
unknown or wildcard edges, out-of-scope cross-Spec edges, cycles, and missing
Verification coverage. RepoFoundry regenerates and byte-compares the derived
index, verifies every range/hash at routing time, exposes bounded cards, and
records source coordinates, dependency edges, reasons, budgets, and capsule
identity in the receipt. Codex, Claude, and Portable remain thin consumers of
one Core engine.

The intentionally retained path is explicit whole-Spec compatibility for
legacy documents and old `activate --spec` callers. It is observable in the
receipt and does not weaken exact mode for formal Requirements. The plan stays
active until these uncommitted changes have a verified revision suitable for
`archive-ep`.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No new third-party runtime dependency is allowed. Python standard-library
parsing, hashing, JSON, path, and atomic-file primitives remain sufficient.

- EngineeringSpecifications exposes two exact paragraphs immediately after
  each `### Requirement <ID>: ...` heading: `**Activation:** Load when ...` and
  `**Context dependencies:** None` or comma-separated backticked IDs.
- The generated requirement index is strict versioned JSON and includes source
  Spec identity/version/digest, normalized activation text, exact dependency
  IDs, UTF-8 byte offsets/lengths, block SHA-256, and Verification coordinates.
- The Core Router exposes `begin`, `candidates`, `requirements`, `activate`,
  `status`, `rehydrate`, `audit`, and normalized-event operations without
  placing product event names in Core.
- Receipt v2 records adapter/session/turn/context epoch, planned paths,
  applicable Specs, direct/resolved Requirement IDs with reasons and sources,
  capsule mode/digest/bytes/budget, and injection/rehydration state.
- Managed central Requirements may depend only on the same Spec or a transitive
  Catalog Spec dependency. Project Specs may use only locally resolvable exact
  IDs. All graphs are acyclic.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-013_requirement-context-activation/EXECPLAN.md`
- End-to-end evidence: `docs/exec-plans/active/ep-013_requirement-context-activation/artifacts/requirement-context-e2e.json`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-05T08:43:48Z — Initial plan created.
- 2026-08-05T08:52:00Z — Filled the executable plan from the approved ESP,
  sealed R-001 Synthesis, accepted ADR closure, and current Design Docs.
- 2026-08-05T09:46:53Z — Implemented all three code paths, added bilingual
  operational documentation, and recorded isolated exact-capsule evidence;
  final RepoFoundry canonical verification remains.
- 2026-08-05T09:51:00Z — Final RepoFoundry canonical check passed; the plan
  remains active only because the implementation is not yet committed to a
  verified revision.
