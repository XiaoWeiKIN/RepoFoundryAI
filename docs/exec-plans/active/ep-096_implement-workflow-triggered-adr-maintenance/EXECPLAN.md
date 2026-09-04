---
schema_version: "2.8"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-096
title: "Implement workflow-triggered ADR maintenance"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "ADR-061 and approved DD-013 revision 1 define the complete implementation and verification contract; no unresolved evidence question remains."
adr_refs: ["ADR-014", "ADR-016", "ADR-058", "ADR-059", "ADR-060", "ADR-061"]
adr_constraint_refs: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008", "ADR-058#C-001", "ADR-058#C-002", "ADR-058#C-003", "ADR-058#C-004", "ADR-058#C-005", "ADR-058#C-006", "ADR-058#C-007", "ADR-058#C-008", "ADR-058#C-009", "ADR-059#C-001", "ADR-059#C-002", "ADR-059#C-003", "ADR-059#C-004", "ADR-059#C-005", "ADR-059#C-006", "ADR-059#C-007", "ADR-059#C-008", "ADR-059#C-009", "ADR-059#C-010", "ADR-060#C-001", "ADR-060#C-002", "ADR-060#C-003", "ADR-060#C-004", "ADR-060#C-005", "ADR-060#C-006", "ADR-060#C-007", "ADR-060#C-008", "ADR-060#C-009", "ADR-061#C-001", "ADR-061#C-002", "ADR-061#C-003", "ADR-061#C-004", "ADR-061#C-005", "ADR-061#C-006", "ADR-061#C-007", "ADR-061#C-008", "ADR-061#C-009"]
adr_evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb", "ADR-058@sha256:7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b", "ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc", "ADR-060@sha256:773f40850444b167611da324f01bbca729ac3621fcfa2ee093b1b4d1d7af8886", "ADR-061@sha256:3e130b6287ff330a35489701ba675e6ed4759ce095dc1073cc53d19553c25251"]
design_refs: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md", "docs/design-docs/dd-012_lossless-adr-context-compaction.md", "docs/design-docs/dd-013_policy-driven-adr-maintenance.md"]
design_evidence: ["DD-012@rev:3@sha256:97cabcae235ebca92f1852e15cc4a3ba286510910a6f4662fdad08aa13ffaae0", "DD-013@rev:1@sha256:153e4231008158a5603ec8d5b71b9a1131ad2d083628a5da7ed60a09d3cee287"]
architecture_entrypoint: ""
architecture_decision_gate: satisfied
architecture_decision_gate_reason: ""
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-09-04
updated: 2026-09-04
author: "Codex"
owner: "Wangxiaowei1"
---

# Implement workflow-triggered ADR maintenance

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Ship RepoFoundry 0.9.0 with a built-in, deterministic ADR maintenance policy so
repositories no longer depend on maintainers remembering to inspect `adr-health`.
Users can run `epctl adr-maintenance`, consume the same summary through `status`,
see non-blocking pressure warnings during `validate`, and gate scheduled CI with
`adr-maintenance --check`. The result distinguishes current-decision complexity
from terminal-history storage and recommends typed preview-only actions without
changing an ADR or creating a History Pack.

After release, upgrade the local Codex Skill and DataFox Harness, then run the new
command in DataFox. Success is observable as a deterministic maintenance report
that identifies DataFox's remaining current-context pressure separately from any
mechanically eligible terminal history while leaving the logical ADR corpus
unchanged.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — release and DataFox adoption.
- Current state: Milestones 1–2 are implemented. The full canonical source check,
  including 82 execution-plan tests and 122 distribution/contract tests, passes.
  The implementation remains isolated from the user's older working tree.
- Next action: commit and publish RepoFoundry 0.9.0, update the local Codex Skill,
  then preview/apply the DataFox Harness upgrade and run its maintenance report.

## Context and Orientation

`engineering-execution-plan/scripts/epctl.py` owns the logical ADR resolver,
`adr_health()`, Decision Views, capsules, consolidation previews, lifecycle
commands, History Pack transactions, repository validation, status projection, and
the CLI parser. `adr_health()` already returns independent corpus, storage,
contract, graph, constraint, amendment, active-plan, view, and context-cost facts.
The new evaluator consumes that payload and validated logical sources; it does not
rescan Markdown through a second model.

The **fast path** decorates fixed signals and returns immediately when no numeric
review boundary is crossed and fewer than three terminal strict live files are
eligible. The **slow path** groups crossed signals into stable action families and
constructs read-only next-command hints. `--explain` may select the slow path for a
healthy repository, but neither path writes files.

`scripts/foundryctl.py` and `VERSION` own distribution and Harness component
versions. Root/project Skills under `SKILL.md` and `assets/{core,adapters}` own Agent
workflow guidance. `tests/test_foundryctl.py`, `tests/test_installer.py`, and
`tests/test_repository_contracts.py` verify that versioned seeds upgrade only when
unmodified. DataFox is a downstream repository upgraded only after the RepoFoundry
release and local Skill installation succeed.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-061_workflow-triggered-adr-maintenance.md` | Accepted cadence, thresholds, action routing, authority and compatibility contract | Before every implementation or scope change |
| `docs/design-docs/dd-013_policy-driven-adr-maintenance.md` | Approved component, schema, fast/slow path, rollout and verification design | Before implementation and review |
| `engineering-execution-plan/scripts/epctl.py` | Canonical logical ADR, health, validation, status and CLI implementation | During Milestones 1–2 |
| `engineering-execution-plan/tests/test_epctl.py` | Behavioral and mutation-safety fixtures | Before and after each `epctl` edit |
| `SKILL.md` and `assets/core/repo-foundry-ai/SKILL.md` | Distribution and project workflow cadence | During Milestone 2 |
| `scripts/foundryctl.py` and `VERSION` | Release and versioned-seed ownership | During Milestone 3 |
| `scripts/check.py` | Canonical source-repository verification | Before release |

Invariants: output is non-normative and scoreless; numeric boundaries are crossed
only by `value > boundary`; terminal readiness is `candidate_count >= 3`; all IDs,
paths, signals, and actions are deterministically ordered; invalid logical sources
fail before output; default validation remains non-blocking for pressure; and every
mutation continues through its existing explicit authority and preview/apply path.

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `satisfied`.
- Architecture compliance: `applicable`.
- ADR references: ["ADR-014", "ADR-016", "ADR-058", "ADR-059", "ADR-060", "ADR-061"].
- ADR constraint references: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008", "ADR-058#C-001", "ADR-058#C-002", "ADR-058#C-003", "ADR-058#C-004", "ADR-058#C-005", "ADR-058#C-006", "ADR-058#C-007", "ADR-058#C-008", "ADR-058#C-009", "ADR-059#C-001", "ADR-059#C-002", "ADR-059#C-003", "ADR-059#C-004", "ADR-059#C-005", "ADR-059#C-006", "ADR-059#C-007", "ADR-059#C-008", "ADR-059#C-009", "ADR-059#C-010", "ADR-060#C-001", "ADR-060#C-002", "ADR-060#C-003", "ADR-060#C-004", "ADR-060#C-005", "ADR-060#C-006", "ADR-060#C-007", "ADR-060#C-008", "ADR-060#C-009", "ADR-061#C-001", "ADR-061#C-002", "ADR-061#C-003", "ADR-061#C-004", "ADR-061#C-005", "ADR-061#C-006", "ADR-061#C-007", "ADR-061#C-008", "ADR-061#C-009"].
- ADR evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb", "ADR-058@sha256:7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b", "ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc", "ADR-060@sha256:773f40850444b167611da324f01bbca729ac3621fcfa2ee093b1b4d1d7af8886", "ADR-061@sha256:3e130b6287ff330a35489701ba675e6ed4759ce095dc1073cc53d19553c25251"].
- Design document references: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md", "docs/design-docs/dd-012_lossless-adr-context-compaction.md", "docs/design-docs/dd-013_policy-driven-adr-maintenance.md"].
- Approved Design revision evidence: ["DD-012@rev:3@sha256:97cabcae235ebca92f1852e15cc4a3ba286510910a6f4662fdad08aa13ffaae0", "DD-013@rev:1@sha256:153e4231008158a5603ec8d5b71b9a1131ad2d083628a5da7ed60a09d3cee287"].
- Architecture entrypoint: ``.

No Research package is required because the accepted lifecycle, health, focused
context, and History Pack contracts plus the verified DataFox rollout fully bound
the implementation. The open question is operational usefulness of the default
thresholds, not an unresolved architecture choice; boundary fixtures and the
DataFox run provide that evidence.

ADR-061 requires one versioned `default-v1` policy, independent signal severities,
maximum-severity aggregation, typed preview actions, a mutation-free fast path,
deterministic human/JSON output, and exit code 1 only for `--check` with
`action_required`. ADR-058 and ADR-059 require all context to remain lossless and
scoreless. ADR-016 preserves explicit lifecycle authority. ADR-060 allows discovery
of eligible terminal IDs but forbids automatic selection or packing. DD-013 fixes
the command/schema shape and makes scheduled systems consumers of the repository
command rather than alternate policy owners.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-014#C-001 | Keep the maintenance result ephemeral and non-normative; add no governed Markdown artifact type. | CLI schema assertions and canonical artifact validators. |
| ADR-014#C-002 | Store release and downstream verification only as normal EP evidence; create no new binary evidence format. | EP artifact inspection and repository checks. |
| ADR-014#C-003 | Expose `authority_required` explicitly and never infer an actor from owner or author metadata. | Mutation-spy plus lifecycle and pack authorization regressions. |
| ADR-014#C-004 | Validate the sealed logical corpus before policy evaluation and leave all integrity boundaries unchanged. | Malformed and tampered ADR/Pack fixtures fail before output. |
| ADR-014#C-005 | Consume legacy and strict ADRs through the existing mixed-corpus resolver without migration. | Legacy, strict, and packed compatibility fixtures. |
| ADR-014#C-006 | Keep policy and generated guidance in versioned canonical sources with Git provenance. | `tests/test_repository_contracts.py` and Markdown checks. |
| ADR-016#C-001 | Read projected decision effect only; never rewrite decided ADR payloads. | ADR byte-map equality before and after every maintenance command. |
| ADR-016#C-002 | Keep all lifecycle mutations behind existing authority, reason, preview, lock, and apply commands. | Existing transition/supersession tests plus mutation spies. |
| ADR-016#C-003 | Use existing current-effect projection so under-review closures remain excluded. | Currentness graph regressions and maintenance signal fixture. |
| ADR-016#C-004 | Report retired sources only as possible terminal storage; never infer implementation rollback. | Terminal eligibility and terminology tests. |
| ADR-016#C-005 | Resolve superseded links through existing projection and never manufacture a replacement. | Supersession and packed-corpus regressions. |
| ADR-016#C-006 | Preserve active-plan architecture review behavior; maintenance adds only a separate warning. | Validation/status compatibility tests. |
| ADR-016#C-007 | Leave new-EP closure validation unchanged and derive plan pressure from valid active plans. | Existing new-EP tests plus active-plan signal boundaries. |
| ADR-016#C-008 | Use the existing cross-schema resolver and avoid mass rewriting any ADR. | Legacy schema and repository validation suites. |
| ADR-058#C-001 | Mark every maintenance result and action non-normative and perform no writes. | JSON/human golden output and repository byte-map audit. |
| ADR-058#C-002 | Reuse the validated current-effect resolver; do not create another closure algorithm. | View/capsule graph regressions and evaluator fixtures. |
| ADR-058#C-003 | Read health facts without copying or transforming normative source prose. | Exact capsule and digest regression suite. |
| ADR-058#C-004 | Do not alter capsule budgets or add an adaptive summary fallback. | Budget boundary and overflow regressions. |
| ADR-058#C-005 | Keep Decision View identity, projection, preview/apply, locking, and reindex behavior intact. | Decision View fixture suite. |
| ADR-058#C-006 | Do not change capsule inputs or output; only consume existing view-cost metrics. | Complete/focused capsule golden regressions. |
| ADR-058#C-007 | Decorate independent health signals with visible action thresholds and severity; aggregate only by maximum severity. | Threshold, ordering, and no-score tests. |
| ADR-058#C-008 | Emit `consolidate_current` as a preview action only and never synthesize or apply semantic changes. | Mutation-spy and repository digest equality tests. |
| ADR-058#C-009 | Ship additively through versioned Skill/Harness upgrades and create no maintenance state. | Installer, upgrade, customized-seed, and downgrade-readability tests. |
| ADR-059#C-001 | Leave complete closure validation ahead of all focused materialization and consume only its health outputs. | Focused/complete validation parity regressions. |
| ADR-059#C-002 | Do not change complete-mode bytes, schema, costs, budget, or digest behavior. | Existing complete-mode golden compatibility test. |
| ADR-059#C-003 | Never select focused mode from maintenance output or overflow. | CLI action schema and overflow-no-fallback tests. |
| ADR-059#C-004 | Leave focused directional selection unchanged. | Branching amendment regression fixtures. |
| ADR-059#C-005 | Leave focused source and closure digests unchanged. | Byte, Unicode, CRLF, and digest regressions. |
| ADR-059#C-006 | Keep validated/materialized/omitted boundaries visible; maintenance only reports view cost. | Focused human/JSON output regressions. |
| ADR-059#C-007 | Preserve ambiguity fast failure for legacy and unscoped amendment boundaries. | Existing ambiguity failure fixtures. |
| ADR-059#C-008 | Do not add summarization, truncation, adaptive omission, or automatic budget changes. | Focused budget and mutation-audit tests. |
| ADR-059#C-009 | Keep focused capsules non-authoritative; maintenance never treats one as a compliance matrix. | Warning contract and lifecycle call audit. |
| ADR-059#C-010 | Release without persisted schema migration and retain downgrade-readable repositories. | Install, upgrade, and DataFox integration checks. |
| ADR-060#C-001 | Discover mechanically eligible IDs read-only, but require explicit IDs, actor, reason, preview, and apply in the pack command. | Eligibility matrix and explicit-selection regressions. |
| ADR-060#C-002 | Read verified logical sources and never create or modify Pack JSON during evaluation. | Canonical Pack/tamper tests and byte-map audit. |
| ADR-060#C-003 | Use the single live/packed logical resolver for health, status, and maintenance. | Mixed-corpus, collision, and no-Git fixtures. |
| ADR-060#C-004 | Never enter the pack transaction from maintenance; existing validate-before-delete logic stays unchanged. | Apply rollback tests and pack-function spies. |
| ADR-060#C-005 | Leave exact all-or-nothing unpack behavior unchanged. | Unpack round-trip/conflict regression suite. |
| ADR-060#C-006 | Report storage advice without changing lifecycle, semantics, payload, or current effect. | Parsed-model equality and lifecycle audit. |
| ADR-060#C-007 | Install detection only; create no Pack and preserve unpack-before-downgrade guidance. | Installer/Harness zero-auto-pack tests and documentation assertions. |
| ADR-060#C-008 | Reuse strict Pack/source parsing, path limits, and symlink rejection; interpolate no source prose into commands. | Safety boundary and injection fixtures. |
| ADR-060#C-009 | Retain separate logical, effective, live-file, Pack, entry, and reduction measures in maintenance output. | Schema, count, and terminology tests. |
| ADR-061#C-001 | Wire one evaluator into `adr-maintenance`, `status`, `validate`, and distributed Governed handoff guidance. | CLI integration, Skill assertions, and scheduled-check documentation. |
| ADR-061#C-002 | Add value, review boundary, action boundary, severity, and explanation per signal; use maximum severity and no score. | Exact JSON schema, ordering, and no-score tests. |
| ADR-061#C-003 | Encode exclusive numeric boundaries 40/24/24/192/16/8/8/64 KiB and inclusive terminal count 3 in `default-v1`. | Boundary-minus/equal/plus fixtures for every signal. |
| ADR-061#C-004 | Return an empty-action fast path before impact/action planning unless a boundary crosses or `--explain` is set. | Planner-spy fast-path and forced-explain tests. |
| ADR-061#C-005 | Map storage, current graph/amendment, coverage, view cost, legacy, and plan pressure to distinct typed action families. | Independent and combined routing fixtures with affected IDs. |
| ADR-061#C-006 | Make evaluation pure and prohibit calls to lifecycle, consolidation creation, pack, unpack, or apply paths. | Repository byte-map and mutation-function spy tests. |
| ADR-061#C-007 | Add deterministic human/JSON output and `--check` exit 1 only for `action_required`; retain error exit 2. | Golden output, exit matrix, malformed corpus, and invalid-argument tests. |
| ADR-061#C-008 | Ship as additive 0.9.0 code and versioned Skill seeds with no timestamp, acknowledgement, policy file, or automatic Pack. | Upgrade/downgrade, zero-state, customized-seed, and zero-Pack tests. |
| ADR-061#C-009 | Expose policy ID, path, thresholds, state, eligible IDs, affected objects, authority, commands, and distinct count types. | Schema/terminology golden tests and DataFox report. |

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

Begin with executable policy tests in `test_epctl.py`: healthy and threshold
boundaries, combined routing, terminal eligibility, fast-path isolation, CLI exit
codes, invalid-corpus failure, status/validate integration, deterministic output,
and repository byte equality. Implement immutable policy constants and pure helper
functions adjacent to `adr_health()` in `epctl.py`, then add the parser and main
dispatch. `status` will carry only a bounded summary; the dedicated command owns
complete actions. `validate` will emit one concise warning without changing its exit
status for structural pressure.

Next update the root and distributed project Skills so Governed work invokes the
command after successful ADR lifecycle/storage changes and before handoff. Update
English and Chinese CLI documentation and release/version contracts. Bump the Core
and adapter seed versions only where managed file bytes change, leaving Harness
schema 3 unchanged.

Finally run focused and complete suites, record release evidence, commit and merge
the implementation, tag and publish 0.9.0, install it locally, and upgrade DataFox
through normal preview/apply. Run DataFox validation and maintenance reporting,
then apply only independently authorized physical packing or semantic/lifecycle
work; the new detector itself performs no cleanup mutation.

## Milestones

### Milestone 1: Pure policy evaluator and CLI

`epctl adr-maintenance` returns schema 1 human/JSON output with exact boundary
semantics, a proven healthy fast path, typed slow-path actions, and `--check` exit
behavior. Focused unit tests pass and prove byte-for-byte read-only behavior.

### Milestone 2: Workflow, distribution, and compatibility integration

`status` exposes a bounded maintenance summary, `validate` emits one non-blocking
warning, and root/Codex/Claude/portable guidance invokes the canonical check at
defined events. Installer, Harness upgrade, customized-seed, and no-auto-pack tests
pass. README documentation explains local and scheduled use.

### Milestone 3: Release and DataFox adoption

The canonical source check passes, RepoFoundry 0.9.0 is committed, merged, tagged,
published, and locally installed. DataFox upgrades to 0.9.0, validates, and reports
its current ADR pressure and terminal candidates without an implicit ADR mutation.
EP-096 records commands, revisions, and downstream evidence before archival.

## Concrete Steps

From `/Users/wangxiaowei1/x-otel/EngineeringPlan-adr-maintenance-policy`:

1. Edit `engineering-execution-plan/tests/test_epctl.py` and
   `engineering-execution-plan/scripts/epctl.py`; run
   `python3 -m unittest engineering-execution-plan/tests/test_epctl.py` and expect
   all tests to pass.
2. Run representative commands against temporary fixtures:
   `python3 engineering-execution-plan/scripts/epctl.py --repo FIXTURE
   adr-maintenance --json`, then repeat with `--check`; expect deterministic schema
   1 output and exit 1 only for hard pressure.
3. Update `SKILL.md`, `assets/core/repo-foundry-ai/SKILL.md`, adapter Skills,
   `README.md`, `README.zh-CN.md`, `VERSION`, and matching constants/tests.
4. Run `python3 -m unittest discover -s engineering-execution-plan/tests`, focused
   installer/foundry tests, then `python3 -B scripts/check.py`; expect zero failures.
5. Commit, merge to `main`, create and push tag `v0.9.0`, and publish the release
   through the repository's established release workflow; verify the remote tag and
   release asset/source availability.
6. Install 0.9.0 through `install.py`, verify `repofoundry --version`, and upgrade
   DataFox first in preview then apply mode. Run the installed `epctl validate` and
   `epctl adr-maintenance --json` from DataFox and save concise evidence under this
   plan's `artifacts/` directory.

## Validation and Acceptance

- [x] From the RepoFoundry worktree, run
  `python3 -m unittest discover -s engineering-execution-plan/tests`; expect every
  `epctl` test to pass, including boundary, routing, no-score, fast-path, no-mutation,
  status, validate, and exit-code fixtures. Evidence: test transcript.
- [x] Run focused distribution tests under `tests/`; expect versioned seed upgrades,
  customized-file preservation, no new policy state, and no automatic Pack.
  Evidence: test transcript.
- [x] Run `python3 -B scripts/check.py`; expect all source suites, repository
  validators, Markdown links, generated indexes, and packaging checks to pass.
  Evidence: `artifacts/check-0.9.0.txt`.
- [x] Run `git diff --check` and verify the release diff contains no whitespace,
  generated cache, or credential material. The worktree remains intentionally
  modified until the release commit is created. Evidence: concise transcript in
  `artifacts/check-0.9.0.txt`.
- [ ] Verify `repofoundry --version` reports `0.9.0` after local installation and a
  clean fixture can invoke `adr-maintenance`. Evidence:
  `artifacts/release-install-0.9.0.txt`.
- [ ] In DataFox, preview and apply `repofoundry --repo . upgrade --to 0.9.0`, then
  run Harness and `epctl` validation; expect zero errors and no automatic ADR/Pack
  mutation. Evidence: `artifacts/datafox-upgrade-0.9.0.txt`.
- [ ] In DataFox, run `epctl adr-maintenance --json`; expect current-context pressure
  and terminal archive readiness to be reported independently with typed preview
  actions. Evidence: `artifacts/datafox-adr-maintenance.json`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

The evaluator is pure and deterministic, so all maintenance and validation commands
are safe to repeat. Tests use temporary repositories. `status` and `validate` write
no acknowledgement or clock state. Installer and Harness upgrades remain
preview-first, replace only byte-identical managed seeds, and can be retried after a
failed apply. DataFox must be clean or its existing changes must be inventoried
before upgrade; unrelated changes are preserved.

Do not delete or rewrite ADRs to recover from a detector failure: fix the policy or
invalid source and rerun. A failed release is corrected with a new commit/tag only
if the existing tag was not published; published tags are immutable. A failed
DataFox upgrade is diagnosed from its preview and manifest rather than by resetting
the repository. Existing History Pack atomic rollback and unpack contracts remain
the only recovery paths for physical packing.

## Progress

- [x] (2026-09-04T03:28:04Z) EP-096 created with the complete ADR and Design
  dependency closure.
- [x] (2026-09-04T03:26:50Z) Wangxiaowei1 approval recorded for DD-013 revision 1
  and acceptance recorded for ADR-061.
- [x] (2026-09-04T03:34:00Z) Execution plan calibrated with file-level work,
  constraint mapping, acceptance commands, and release/DataFox rollout.
- [x] (2026-09-04T04:42:00Z) Milestone 1 completed: implemented the immutable
  `default-v1` evaluator, fast/slow paths, typed preview actions, CLI, exit
  behavior, and deterministic mutation-safety fixtures.
- [x] (2026-09-04T05:08:00Z) Milestone 2 completed: integrated bounded status and
  non-blocking validation output, updated versioned Skills/docs, advanced managed
  seed versions, and added zero-auto-pack upgrade coverage.
- [x] (2026-09-04T05:16:00Z) Canonical `scripts/check.py` completed with every
  source suite and integrity validator passing; `git diff --check` also passed.
- [ ] Publish RepoFoundry 0.9.0 and complete local/DataFox adoption.

## Surprises & Discoveries

- EP creation correctly failed fast until the full transitive Design closure
  (DD-013, DD-012, DD-010) and ADR/current-amendment closure (including ADR-059)
  were included; the final plan now pins all required evidence.
- `status` classifies any ADR that satisfies strict parsing as `strict`, while ADR
  health classifies only schema 1.2–1.4 sources as structured. Legacy migration
  routing therefore must consume `contracts.whole_document_current_ids` rather
  than infer candidates from the status contract label.

## Decision Log

- 2026-09-04 — Use one event-driven repository evaluator plus an externally
  schedulable `--check`; do not add a resident daemon.
- 2026-09-04 — Keep default validation non-blocking and reserve exit 1 for explicit
  `adr-maintenance --check` hard-pressure gates.
- 2026-09-04 — Use fixed `default-v1` thresholds without repository-local override
  or persisted acknowledgement state in this release.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

Pending implementation and downstream verification. At completion, record the
released behavior, exact RepoFoundry/DataFox revisions, observed DataFox actions,
any intentionally deferred ADR cleanup, and whether the default thresholds produced
useful routing without conflating history storage and current context.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No new third-party runtime dependency is permitted. The implementation uses Python
standard-library types and the existing logical source/status/health functions.
Planned internal interfaces are `adr_maintenance(repo: Path, explain: bool = False)
-> dict[str, object]`, a pure signal decorator, a terminal-eligibility selector, a
slow-path action planner, and human/summary renderers. Public CLI is
`adr-maintenance [--json] [--check] [--explain]`; JSON carries
`schema_version: 1`, `non_normative: true`, `state`, `fast_path`, `policy`,
`signals`, `eligible_terminal_adrs`, and `actions`.

`status --json` adds a bounded `adr_maintenance` object. `validate` adds warnings
only and preserves existing structural error codes. `pack-historical-adrs`,
`transition-adr`, `supersede-adr`, Decision Views, capsules, and consolidation
interfaces remain byte- and behavior-compatible. Distribution continues through
the current GitHub repository, `install.py`, Harness manifest schema 3, and
versioned Core/adapter seeds.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-096_implement-workflow-triggered-adr-maintenance/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-09-04T03:28:04Z — Initial plan created.
- 2026-09-04T03:34:00Z — Filled the implementation, compliance, validation,
  release, recovery, and downstream rollout contract before code changes.
- 2026-09-04T05:16:00Z — Completed Milestones 1–2, recorded canonical check
  evidence, and advanced the live snapshot to release and downstream adoption.
