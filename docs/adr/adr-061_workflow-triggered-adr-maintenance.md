---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: ADR-061
title: "Trigger ADR maintenance from deterministic workflow thresholds"
status: accepted
research_refs: []
depends_on: ["ADR-060"]
amends: []
amends_constraints: []
design_refs: ["docs/design-docs/dd-013_policy-driven-adr-maintenance.md"]
supersedes: []
superseded_by:
decision_maker: "Wangxiaowei1"
decided: "2026-09-04T03:26:50Z"
decision_outcome: accepted
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256: 3e130b6287ff330a35489701ba675e6ed4759ce095dc1073cc53d19553c25251
created: 2026-09-04
updated: 2026-09-04
author: "Codex"
owner: "Wangxiaowei1"
---

# Trigger ADR maintenance from deterministic workflow thresholds

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-058 added explainable ADR health signals, Decision Views, exact capsules, and a
preview-only consolidation analysis. ADR-060 added explicit lossless packing for
strict terminal ADRs. Both capabilities are operator-invoked. A repository can cross
the reviewed current-ADR, graph, view, active-plan, or terminal-file boundaries and
remain there indefinitely unless a maintainer remembers to inspect `adr-health` and
select the correct follow-up command.

The DataFox rollout demonstrates the gap. Its four-to-one History Pack correctly
reduced physical sources by three, but 44 current ADRs remained. The operation was
successful while the larger context-maintenance problem still required action. A
plain total count, an automatic pack, or a green repository validation cannot
distinguish those outcomes.

RepoFoundry needs a built-in maintenance trigger that repeatedly evaluates the hard
indicators and routes pressure to the correct workflow. That choice affects public
CLI and JSON contracts, validation behavior, Agent handoff rules, CI integration,
threshold ownership, compatibility, and the boundary between automated detection
and human decision authority. It is therefore a durable architecture decision.

## Decision Drivers

- ADR pressure must be detected during normal work instead of relying on operator
  memory.
- Signals must remain independent and explainable; no aggregate score may obscure
  why maintenance is required.
- Hard thresholds must lead to actionable, typed next steps rather than another
  passive dashboard.
- Terminal physical history and excessive current-decision complexity must route to
  different remedies.
- Automatic detection must not gain authority to change decision outcome, current
  effect, semantic content, or physical storage.
- Healthy repositories need a clean fast path; expensive impact planning should run
  only when a signal crosses a boundary or an operator requests explanation.
- Local, Agent, CI, and scheduled execution must share one deterministic policy.
- Existing repositories, Harnesses, ADRs, Packs, and default validation exit codes
  must remain compatible.

## Research Evidence

No separate Research package is required. The relevant evidence is already local,
released, and decision-ready:

- ADR-058 established independent health dimensions, a 24-current-ADR navigation
  target, 12-ADR graph and active-plan targets, a 96-constraint active-plan target,
  an eight-partial-amendment target, complete view coverage, and a 32 KiB capsule
  budget. It also prohibits automatic lifecycle change.
- ADR-060 established exact terminal eligibility, explicit IDs/actor/reason,
  preview-before-apply, candidate validation before deletion, atomic rollback, and
  zero automatic packing during install or Harness upgrade.
- DataFox retained 51 logical ADRs and 44 current ADRs after packing four terminal
  sources into one container. This proves with high confidence that physical archive
  readiness and current-context pressure are independent.
- RepoFoundry already has deterministic status, validation, generated project Skill,
  and Agent lifecycle boundaries where the same evaluator can run.

There is no evidence that count, age, graph centrality, or an LLM recommendation can
identify a safe semantic retirement. That negative evidence requires an explicit
human authority boundary after automatic detection.

## Considered Options

### A. Keep `adr-health` on demand

This preserves all existing contracts but relies on maintainer memory and produces
no durable workflow response when thresholds are crossed.

### B. Automatically retire, supersede, consolidate, or pack ADRs

This produces visible reduction with minimal interaction, but a metric cannot prove
that a current decision is obsolete. Automatic packing also violates ADR-060's
explicit selection and apply boundary.

### C. Add a deterministic maintenance gate with typed preview actions

Evaluate versioned thresholds at validation and workflow boundaries, expose a
machine-readable state, and route each crossed dimension to an exact read-only next
action. Require the existing explicit authority and preview/apply commands for every
mutation.

### D. Add a RepoFoundry background daemon or platform-specific scheduled jobs

Literal time scheduling is useful when a repository is idle, but a resident process
is not portable and platform-specific jobs would duplicate the policy. External
schedulers can call a shared check command without owning its rules.

## Decision Outcome

Propose **Option C**.

RepoFoundry will automatically evaluate a built-in, versioned ADR maintenance policy
at deterministic workflow boundaries. It will surface `review_due` and
`action_required` states and generate typed, preview-only next actions. An external
scheduler may invoke the same check, but no daemon or adapter owns another policy.

The discriminating case is a repository with both 44 current ADRs and four terminal
strict files. The selected model reports `consolidate_current` for the first pressure
and `pack_history` for the second. It does not claim that automatically packing the
four files resolves the current working set. This retains the user's desired
automatic trigger while preserving the authority and recovery contracts already
accepted.

## Decision Statement

RepoFoundry must evaluate a deterministic versioned ADR maintenance policy at normal validation and governed-workflow boundaries, must translate crossed hard indicators into explainable typed preview actions, and must require the existing explicit human authority and preview/apply contracts before any ADR lifecycle, semantic, or physical-storage mutation.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | maintenance cadence | The same maintenance evaluator must run through `adr-maintenance`, contribute a summary to `status`, emit concise signals during `validate`, and be invoked by distributed Agent workflow guidance after successful ADR lifecycle/storage changes and before a Governed handoff; external schedules must call the same repository-owned command. | CLI integration fixtures, generated-Skill assertions, and end-to-end handoff/CI command tests |
| C-002 | must | explainability | Every health dimension must retain its own value, review threshold, action threshold, severity, and explanation; overall state may be the maximum visible severity but must not be a weighted or opaque aggregate score. | JSON schema, threshold-boundary, ordering, and no-score tests |
| C-003 | must | default policy v1 | Review thresholds must retain the ADR-058 values; numeric pressure must become `review_due` only when its value exceeds the review boundary and `action_required` only when it exceeds the action boundary. The action boundaries must be 40 effective ADRs, 24 for the largest current component or active-plan ADR references, 192 active-plan constraint references, 16 partially amended ADRs, eight current legacy or uncovered current ADRs, and 64 KiB for a complete view. Three or more mechanically eligible terminal strict live ADRs must produce an independent archive-ready action. | exact boundary-minus/equal/plus fixtures for every dimension and a three-terminal-source fixture |
| C-004 | must | fast and slow paths | When no review boundary is crossed and fewer than three eligible terminal sources exist, evaluation must return a deterministic empty-action fast path; impact analysis and command construction must run only on the slow path or explicit explain mode. | collaborator-spy fast-path test, slow-path action tests, and deterministic output comparison |
| C-005 | must | action routing | Terminal strict live history must route to `pack_history`; excessive current decisions, graph coupling, or amendments to `consolidate_current`; missing coverage to `repair_views`; excessive view cost to `narrow_view_context`; and excessive active-plan inputs to `narrow_plan_context`; one pressure family must not be represented as another. | independent and combined pressure fixtures with exact action types and affected IDs |
| C-006 | must_not | authority boundary | Maintenance evaluation must not accept, reject, transition, retire, supersede, consolidate, rewrite, pack, unpack, create a governed replacement, or invoke an apply path; History Pack execution must still receive explicit IDs, actor, reason, reviewed preview, and separate apply authority. | repository byte-map audit, mutation-function spies, and pack/lifecycle authorization regressions |
| C-007 | must | public check contract | `adr-maintenance` must expose deterministic human and schema-versioned JSON output; default mode must exit 0, `--check` must exit 1 only for `action_required`, and invalid repository or arguments must fail before emitting a trustworthy maintenance result using the existing error contract. | human/JSON golden tests, exit-code matrix, malformed corpus, and invalid-argument tests |
| C-008 | must | compatibility and rollout | The capability must be additive, persist no maintenance timestamp or acknowledgement state in v1, preserve existing ADR/Pack/View/Harness schemas and default validation exit behavior, install through a versioned RepoFoundry release, and never create a Pack during installation or Harness upgrade. | old-fixture upgrade, downgrade-readability, zero-new-state, customized-seed, and zero-auto-pack tests |
| C-009 | must | truthful observability | Output must identify the policy version, fast/slow path, per-signal thresholds, overall state, mechanically eligible terminal IDs, typed preview actions, affected IDs/views/plans, authority requirement, and next command, and must distinguish logical, effective, and physical pressure. | schema/golden output, DataFox integration, and terminology tests |

## Consequences

Positive consequences:

- ADR maintenance becomes a default workflow behavior rather than optional operator
  memory;
- repositories receive the correct next action for the kind of pressure observed;
- scheduled automation, local agents, and CI consume one policy and one result
  schema;
- DataFox-scale current pressure becomes visible even after terminal files are
  correctly packed; and
- healthy repositories avoid unnecessary consolidation analysis.

Costs and risks:

- validation and handoff output gain another warning surface;
- fixed v1 defaults may be noisy for unusually large but well-partitioned systems;
- `action_required` means maintenance must be planned, not that a safe replacement
  decision can be generated automatically; and
- platform adapters cannot guarantee wall-clock execution when no external
  scheduler runs.

Neutral and migration consequences:

- default repository validation remains non-blocking for structural pressure;
- teams that want a CI gate opt into `adr-maintenance --check`;
- no repository data migration or cleanup is required; and
- packed repositories retain the independent unpack-before-downgrade obligation.

## Confirmation

Implementation must pass the complete `epctl` suite and canonical
`python3 -B scripts/check.py`. Dedicated tests must prove threshold boundaries,
maximum-severity derivation, fast-path isolation, typed slow-path routing,
deterministic human/JSON output, exit codes, invalid-corpus fast failure, zero
repository mutation, and no calls to lifecycle or pack apply functions.

Installer and Harness fixtures must prove that the new project Skill is upgraded by
normal versioned-seed rules while customized seeds remain untouched and no Pack or
maintenance-state file is created. DataFox integration must report its current ADR
pressure separately from terminal archive readiness and must leave its logical ADR
corpus unchanged.

## Revisit Triggers

- Large, well-partitioned repositories repeatedly cross an action threshold without
  producing a useful maintenance action.
- Teams require repository-specific thresholds or an auditable acknowledgement and
  snooze lifecycle.
- A portable scheduler becomes part of RepoFoundry's supported runtime boundary.
- Maintenance evaluation adds material latency to routine validation despite the
  fast path.
- Evidence demonstrates a mechanically safe class of semantic consolidation that
  warrants a separately authorized proposal.
- Default validation needs to enforce rather than warn on unresolved maintenance.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-060"]
- Amended ADRs: []
- Amended constraints: []
- Design documents: ["docs/design-docs/dd-013_policy-driven-adr-maintenance.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-09-04T03:19:11Z — Proposed ADR created.
- 2026-09-04T03:26:00Z — Defined workflow cadence, default-v1 review/action
  thresholds, fast/slow paths, typed action routing, CLI exit semantics, explicit
  authority boundary, compatibility, and verification.
