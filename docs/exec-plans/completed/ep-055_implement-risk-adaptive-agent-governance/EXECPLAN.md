---
schema_version: "2.7"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-055
title: "Implement risk-adaptive Agent governance"
status: completed
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-004", "ADR-002", "ADR-005", "ADR-010", "ADR-012", "ADR-015"]
adr_constraint_refs: ["ADR-015#C-001", "ADR-015#C-002", "ADR-015#C-003", "ADR-015#C-004", "ADR-015#C-005", "ADR-015#C-006", "ADR-015#C-007", "ADR-015#C-008", "ADR-015#C-009"]
adr_evidence: ["ADR-001@sha256:9866f72aa09c400b36a9993681a73f7131381a28179a1f0832cd6a89a2ca8fae", "ADR-004@sha256:401daee8795f70b9c0816e02e655e874bc20c37603b937fe831009bb5a80ef98", "ADR-002@sha256:a9ced6c6e80b1e246bd8fc7b90e53b7e9e6aff18a590c545f904dbf59ce61ad7", "ADR-005@sha256:4df850ebff7b23b00663ffdd9142ed03633e5c93f6cd61b4e6af3fa38d3f1d69", "ADR-010@sha256:b0a68a290d59d1279f40d8f1937b4d5ae8f85bc1766eb890a7151554adef364e", "ADR-012@sha256:410121e886544b41db4c29b2e757b422fa2c3e1dfcf14e55ff714a2a9e79df86", "ADR-015@sha256:3926c6cb2a99540f2d73119560d36f12fd9d051bf6b96b4a89d921be340d4d83"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md", "docs/design-docs/risk-adaptive-agent-governance.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: satisfied
architecture_decision_gate_reason: ""
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision: "git:6bb9c1af47c8042eea7cf2824c8c918b9049782a"
verification_evidence: ["python3 -B scripts/check.py (exit 0; 35 Research, 9 Benchmark, 53 ExecPlan, 117 integration tests)"]
archive_sha256: 70dc3e6b5188e292441456bb9a5c8267ab32ec7bb8ee3a9a8a14037cc387a5d3
created: 2026-08-13
updated: 2026-08-13
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Implement risk-adaptive Agent governance

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry currently routes ordinary reversible work through the same
activation and handoff ceremony used for durable architecture, data, security,
and reliability decisions. This implementation makes governance proportional
to risk without weakening authority or evidence boundaries.

After completion, a freshly bootstrapped Harness records an adaptive governance
profile. An Agent begins in Explore, can perform bounded reversible work
without a mandatory Spec receipt, promotes to Build for bounded production
changes, and promotes to Governed for public contracts, security, data,
irreversible operations, reliability claims, releases, or durable decisions.
Existing Harnesses remain strict until an explicit previewed profile migration.
Users can observe the behavior through the Harness manifest, Router status and
classification receipts, generated Agent guidance, Hook decisions, and passing
cross-mode contract tests.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 complete — implementation, guidance, and
  repository-wide validation are green.
- Current state: fresh Harnesses default adaptive, old schema-3 Harnesses remain
  strict, the Core Router records monotonic Explore/Build/Governed state, and
  every distributed guidance surface uses the same risk triggers. DD-009 is
  current. The unrelated EP-057 and EP-054 worktree changes remain preserved.
- Next action: retain EP-055 as active until the Repository Owner creates or
  selects a stable verified revision suitable for `archive-ep`; no source or
  validation work remains.
- Open question: none for this implementation. Path-specific policy minima and
  resumable cross-turn receipts are explicitly deferred extensions.

## Context and Orientation

The root distribution contract is `SKILL.md`; Bootstrap, Harness manifests,
component migrations, generated files, and validation live in
`scripts/foundryctl.py`. Fresh schema-3 manifests are built by
`harness_manifest`; older schema-3 manifests are validated by
`validate_harness_v3_manifest_data` and upgraded through
`plan_harness_upgrade`.

The Agent-neutral activation engine is
`assets/core/engineering-specs/spec_router.py`. It owns turn state, Spec
candidates, activation receipts, mutation decisions, context injection, and
completion audit. `assets/adapters/codex/engineering-specs/scripts/spec_router.py`
translates Codex lifecycle payloads into the normalized protocol. Claude and
Portable use explicit CLI guidance rather than native mutation Hooks.

Generated routing and work-selection guidance lives under `assets/core/` and
`assets/adapters/{codex,claude,portable}/`. The independent professional
packages remain `engineering-research/`, `engineering-execution-plan/`,
`engineering-benchmark/`, and `engineering-case-study/`.

In this plan, a governance profile is repository policy (`adaptive` or
`strict`); a governance mode is turn/task state (`explore`, `build`, or
`governed`). Strict profile starts and remains Governed. Adaptive profile starts
Explore and permits monotonic promotion. Hard boundaries are requirements that
remain mandatory independent of mode.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-015_risk-adaptive-agent-governance.md` | Normative mode, promotion, compatibility, and Core/adapter constraints | Before every milestone |
| `docs/design-docs/risk-adaptive-agent-governance.md` | Detailed classification and adapter behavior | Before Router or guidance changes |
| `docs/adr/adr-012_agent-neutral-spec-activation.md` | Keeps semantics in the shared Core and runtime translation in adapters | Before Router/adapter edits |
| `scripts/foundryctl.py` | Canonical Harness manifest, preview/apply, preservation, and rollback behavior | Before profile storage or migration edits |
| `assets/core/engineering-specs/spec_router.py` | Canonical mode and activation state machine | Before lifecycle changes |
| `engineering-execution-plan/SKILL.md` | Current professional artifact routing and authority gates | Before routing changes |
| `python3 -B scripts/check.py` | Repository-wide acceptance entrypoint | At milestone and final validation |

Universal invariants are: preserve existing user changes; do not infer
authority, owners, credentials, SLOs, or project facts; keep accepted/sealed
artifacts immutable; keep task-time Spec use offline and digest-verified; and
never use Explore or Build to bypass a known security, data, compatibility,
destructive-action, or external-persistence boundary.

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture decision gate: `satisfied`.
- Architecture compliance: `applicable`.
- ADR references: ["ADR-001", "ADR-004", "ADR-002", "ADR-005", "ADR-010", "ADR-012", "ADR-015"].
- ADR constraint references: ["ADR-015#C-001", "ADR-015#C-002", "ADR-015#C-003", "ADR-015#C-004", "ADR-015#C-005", "ADR-015#C-006", "ADR-015#C-007", "ADR-015#C-008", "ADR-015#C-009"].
- ADR evidence: ["ADR-001@sha256:9866f72aa09c400b36a9993681a73f7131381a28179a1f0832cd6a89a2ca8fae", "ADR-004@sha256:401daee8795f70b9c0816e02e655e874bc20c37603b937fe831009bb5a80ef98", "ADR-002@sha256:a9ced6c6e80b1e246bd8fc7b90e53b7e9e6aff18a590c545f904dbf59ce61ad7", "ADR-005@sha256:4df850ebff7b23b00663ffdd9142ed03633e5c93f6cd61b4e6af3fa38d3f1d69", "ADR-010@sha256:b0a68a290d59d1279f40d8f1937b4d5ae8f85bc1766eb890a7151554adef364e", "ADR-012@sha256:410121e886544b41db4c29b2e757b422fa2c3e1dfcf14e55ff714a2a9e79df86", "ADR-015@sha256:3926c6cb2a99540f2d73119560d36f12fd9d051bf6b96b4a89d921be340d4d83"].
- Design document references: ["docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md", "docs/design-docs/risk-adaptive-agent-governance.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 is present only because ADR-001 is in the architecture dependency closure;
its concluded finding established that Research and execution planning have
different ownership and lifecycles. This implementation preserves that split.
No new Research was required because the Repository Owner selected the concrete
three-mode direction after reviewing the current repository behavior and its
trade-offs.

ADR-001 and ADR-004 keep professional evidence production separate from root
orchestration. ADR-002 keeps Bootstrap additive and repository-owned. ADR-005
keeps normative Specifications in an independent locked source. ADR-010's one
Router, local-content, auditable activation architecture remains the mechanism
for Build and Governed work; ADR-015 changes its universal strict policy into a
mode-aware policy. ADR-012 requires the shared Core to own mode and activation
semantics while product adapters only translate lifecycle surfaces.

ADR-015 requires machine-readable mode reasons, universal hard boundaries,
receipt-free bounded Explore work, a concise Build contract, full Governed
parity, monotonic promotion, fresh adaptive defaults with strict preservation,
cross-adapter equivalence, and no prescribed artifact graph below its trigger.
The implementation keeps schema 3 readable by treating a missing
`governance` object as strict compatibility. Fresh manifests write the adaptive
object. Existing repositories change profile only through an explicit
preview/apply option. No Benchmark Scenario is required because the acceptance
claim is functional contract behavior, not performance, capacity, or a
measurement-based architecture choice.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-001 | Keep Research lifecycle and outputs independent from execution planning. | Existing Research and EP package tests plus repository contract tests. |
| ADR-004 | Root Skill classifies and routes; professional Skills retain their artifacts and CLIs. | Skill boundary assertions in `tests/test_repository_contracts.py`. |
| ADR-002 | Extend additive Bootstrap and preserve customized repository files. | `tests/test_foundryctl.py` fresh, preserve, conflict, and rollback cases. |
| ADR-005 | Do not move normative Spec content or fetch it during task routing. | Existing Spec state, offline Router, digest, and drift tests. |
| ADR-010 | Retain one local Router, locked content, receipts, and strict activation for Build/Governed, scoped by ADR-015. | Existing strict Router parity tests plus new mode cases. |
| ADR-012 | Implement profile/mode/classification in Core and keep Codex translation thin. | Core scan and Codex/Portable parity tests. |
| ADR-015#C-001 | Add repository profile plus turn mode and reason fields; expose monotonic classification. | Table-driven profile/mode/classification tests. |
| ADR-015#C-002 | Keep authority and integrity rules in every generated instruction surface and do not relax evidence verification. | Skill contract tests and existing tamper/authority suites. |
| ADR-015#C-003 | Allow adaptive Explore file/command mutation without an activation receipt or first-write retry. | Hook tests for receipt-free Explore and hard-boundary guidance. |
| ADR-015#C-004 | Require Build activation and a bounded task/handoff contract without persistent skip artifacts. | Build activation, coverage, and handoff tests. |
| ADR-015#C-005 | Map strict profile and Governed mode to current fail-closed behavior. | Full existing Router and professional Skill suites. |
| ADR-015#C-006 | Reject mode decreases and require reasoned promotion. | `classify` monotonicity, idempotence, and strict downgrade-rejection tests. |
| ADR-015#C-007 | Write adaptive on fresh Bootstrap, read missing governance as strict, and require explicit preview/apply to change an existing profile. | Bootstrap/upgrade/profile preservation and rollback tests. |
| ADR-015#C-008 | Share mode semantics across adapters while adapters retain only translation. | Codex/Portable event parity and source-boundary scans. |
| ADR-015#C-009 | Route low-risk work directly and remove mandatory Research/ADR skip ceremony outside Governed triggers. | Generated guidance and professional Skill contract tests. |

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

First extend the schema-3 Harness contract with a backward-compatible optional
`governance` object. Fresh Bootstrap writes adaptive; old manifests without the
object resolve to strict. Add explicit profile selection to preview/apply flows,
validation, reporting, and component migration without rewriting customized
seeds.

Next add turn governance state to the shared Router. Session start resolves the
repository profile; adaptive starts Explore and strict starts Governed. A
`classify` command records a mode and reasons, permits only monotonic promotion,
and is delegated by adapters. Explore allows bounded reversible mutations
without activation or forced first-write injection. Build and Governed retain
activation/path coverage; Governed retains the full completion audit.

Then update Core, Codex, Claude, and Portable guidance plus the root and
professional Skills so classification happens before artifact routing. Encode
the same triggers and hard boundaries compactly, leaving detailed rules in
DD-009/ADR-015. Finish with focused Router/Harness/contract tests, current
professional Skill tests, and the canonical repository check.

## Milestones

### Milestone 1: Harnesses carry an explicit governance profile

`scripts/foundryctl.py` writes and validates adaptive/strict policy, treats
missing schema-3 policy as strict compatibility, and supports explicit
preview/apply profile changes. Focused `tests/test_foundryctl.py` cases observe
fresh adaptive defaults, legacy strict preservation, invalid policy rejection,
and deterministic manifest output.

### Milestone 2: Router and adapters enforce mode-aware behavior

The shared Router records profile, mode, and reasons; `classify` promotes modes;
Explore avoids the unconditional activation denial and first-write retry; Build
and Governed preserve applicable Spec and path coverage; strict remains current
behavior. `tests/test_spec_router.py` proves the transition matrix and adapter
parity.

### Milestone 3: Product guidance and professional routing match the runtime

Root, Core, Codex, Claude, Portable, Research, Execution Plan, and Benchmark
instructions consistently describe the three modes and universal hard
boundaries. README, examples, design status, version reporting, and repository
contract tests agree. All focused suites and `scripts/check.py` pass with logs
stored under this EP.

## Concrete Steps

All commands run from `/Users/wangxiaowei1/x-otel/EngineeringPlan`.

1. Patch `scripts/foundryctl.py`, `assets/core/engineering-specs/spec_router.py`,
   and the Codex adapter using `apply_patch`; update focused tests alongside
   each behavior.
2. Run `python3 -B -m unittest tests.test_foundryctl tests.test_spec_router`;
   expect exit 0.
3. Patch generated instruction assets, `SKILL.md`, professional Skill routing,
   README surfaces, and repository contract assertions.
4. Run `python3 -B -m unittest tests.test_repository_contracts`; expect exit 0.
5. Run the current professional suites affected by overlapping work:
   `python3 -B -m unittest engineering-execution-plan/tests/test_epctl.py`,
   `python3 -B -m unittest engineering-research/tests/test_researchctl.py`, and
   `python3 -B -m unittest engineering-benchmark/tests/test_benchctl.py` using
   their supported discovery invocation; expect exit 0.
6. Run `python3 -B scripts/check.py`; expect exit 0 and preserve the complete
   transcript in `docs/exec-plans/completed/ep-055_implement-risk-adaptive-agent-governance/artifacts/`.

## Validation and Acceptance

- [x] From the repository root, run the focused Harness tests; fresh manifests
  report adaptive, missing policy remains strict, explicit profile changes are
  preview-first, and invalid profiles fail. Evidence:
  `artifacts/foundryctl-tests.txt`.
- [x] Run the focused Router tests; adaptive Explore writes without an
  activation receipt, promotion is monotonic, Build/Governed require coverage,
  and strict parity remains green. Evidence: `artifacts/spec-router-tests.txt`.
- [x] Run repository contract tests; every generated Agent surface and
  professional Skill exposes compatible mode semantics within line budgets.
  Evidence: `artifacts/repository-contracts.txt`.
- [x] Run affected professional Skill suites; existing Research, ADR, ExecPlan,
  Benchmark, authority, and sealing behavior remains green. Evidence:
  `artifacts/professional-skill-tests.txt`.
- [x] Run `python3 -B engineering-execution-plan/scripts/epctl.py --repo . validate`;
  expect zero errors. Evidence: `artifacts/epctl-validate.txt`.
- [x] Run `python3 -B scripts/check.py`; expect exit 0. Evidence:
  `artifacts/check.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Bootstrap and profile changes remain dry-run by default. Repeating fresh
Bootstrap or an already-applied profile selection must be a no-op. Existing
generated files are replaced only when their bytes still match their recorded
template digest; customized or unknown files produce conflicts and remain
unchanged. A failed apply uses the existing staged write/rollback mechanism.

Router classification writes an atomic ephemeral receipt under the existing
repository-scoped state directory. Repeating the same mode is idempotent;
promotion is monotonic; an attempted decrease fails without changing state.
Deleting ephemeral receipts returns the next turn to the repository profile and
does not alter repository files.

If implementation validation fails, correct only EP-055 changes. Do not discard
or rewrite the pre-existing EP-057/EP-054 worktree changes. Accepted ADR-015 and
the original strict behavior remain recoverable through the strict profile even
if adaptive migration is not applied.

## Progress

- [x] (2026-08-13T09:30:10Z) Plan created.
- [x] (2026-08-13T09:35:00Z) Filled the implementation, architecture,
  verification, and recovery contract before source changes.
- [x] (2026-08-13T09:43:00Z) Implemented Milestone 1 Harness profile behavior
  and focused tests.
- [x] (2026-08-13T09:48:00Z) Implemented Milestone 2 Router/adapter mode
  behavior and focused tests.
- [x] (2026-08-13T09:57:06Z) Implemented Milestone 3 guidance and documentation;
  all focused, professional, contract, and canonical repository checks pass.

## Surprises & Discoveries

- ADR-010 cannot be marked superseded while accepted ADR-012 still declares it
  as an amendment target. The attempted lifecycle transition was rolled back
  before implementation; ADR-015 scopes the enforcement policy while ADR-010
  and ADR-012 remain current mechanism inputs. A future relationship migration
  must preserve the sealed ADR graph rather than invalidating ADR-012.
- The source worktree already contains unrelated EP-057 and EP-054 changes,
  including edits to Execution Plan and Research code. EP-055 must work
  additively on top of them and validate the combined tree.
- The first canonical check passed all executable suites but detected a stale
  `docs/DECISIONS.md` projection after ADR/design updates. `epctl reindex`
  repaired the projection; the complete rerun then passed.

## Decision Log

- 2026-08-13, Repository Owner: explicitly accepted ADR-015 by instructing
  `执行` after reviewing the proposed decision.
- 2026-08-13, Codex: use an optional schema-3 `governance` object rather than a
  schema bump. Missing policy means strict compatibility; new manifests write
  adaptive. This preserves old clones while making fresh behavior observable.
- 2026-08-13, Codex: implement monotonic explicit classification in the shared
  Core first. Semantic risk discovery remains Agent judgment constrained by
  documented triggers and universal hard boundaries; adapters do not duplicate
  it. Policy schema `1` deliberately does not claim path-level risk inference.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The working tree now implements the accepted risk-adaptive route end to end.
Fresh repositories receive `adaptive`; existing manifests without policy retain
`strict`. Adaptive turns begin in Explore, promote monotonically with a reason,
and require existing Spec activation/path coverage once they reach Build or
Governed. Explore no longer fails only because it lacks a receipt or five-label
handoff. Strict behavior remains available and tested.

Generated Core, Codex, Claude, and Portable instructions plus Research,
Execution Plan, and Benchmark routing all distinguish hard boundaries from
process weight. The documentation is explicit that semantic risk recognition
belongs to Agent judgment in this release; the Router records and enforces mode
state but does not pretend to infer arbitrary destructive intent.

Focused Harness/Router tests (61), repository contracts (15), and professional
Skill suites (94) pass. The final canonical check passed all 196 tests and every
repository integrity check with zero validation errors. EP-055 remains active
only because this mixed dirty worktree has no stable verified revision; it must
not be archived against an invented attestation.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

- Harness manifest optional object:
  `governance: {"policy_schema": 1, "profile": "adaptive"|"strict"}`.
- Core Router runtime fields: `governance_profile`, `governance_mode`, and
  `governance_reasons`.
- Core CLI: `classify --adapter-id ID --session-id ID --turn-id ID --mode
  explore|build|governed --reason TEXT`.
- Existing normalized events and protocol remain version 1; adapters load the
  Core's protocol dynamically and do not own classification policy.
- Existing Spec manifest, lock, managed Markdown, dependency closure, and
  digest verification remain unchanged and offline.
- Python 3.10+ standard library only; no new runtime dependency.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-055_implement-risk-adaptive-agent-governance/EXECPLAN.md`
- Harness tests: `artifacts/foundryctl-tests.txt`
- Router tests: `artifacts/spec-router-tests.txt`
- Repository contracts: `artifacts/repository-contracts.txt`
- Professional Skill regressions: `artifacts/professional-skill-tests.txt`
- EP validation: `artifacts/epctl-validate.txt`
- Canonical repository check: `artifacts/check.txt`

## Revision Notes

- 2026-08-13T09:30:10Z — Initial plan created.
- 2026-08-13 — Replaced all required placeholders with the accepted
  risk-adaptive implementation, validation, compatibility, and recovery route.
- 2026-08-13 — Completed all milestones, recorded verification evidence, and
  left archival pending a real verified revision.
