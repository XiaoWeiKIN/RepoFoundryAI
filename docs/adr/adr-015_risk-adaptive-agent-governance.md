---
schema_version: "1.3"
metadata_schema: "1"
artifact_type: adr
id: ADR-015
title: "Adopt risk-adaptive Agent governance modes"
status: accepted
research_refs: []
depends_on: ["ADR-004", "ADR-012"]
amends: []
amends_constraints: []
design_refs: ["docs/design-docs/risk-adaptive-agent-governance.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicitly instructed '执行' for ADR-015 in the current conversation on 2026-08-13)"
decided: "2026-08-13T09:28:55Z"
payload_sha256: 3926c6cb2a99540f2d73119560d36f12fd9d051bf6b96b4a89d921be340d4d83
created: 2026-08-13
updated: 2026-08-13
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Adopt risk-adaptive Agent governance modes

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

RepoFoundry currently applies a high-assurance governance model to most Agent
implementation and review work. Engineering Specification activation is
recorded before mutation, a no-Spec result requires justification, complex work
defaults toward concluded Research, and resumable implementation carries a
self-contained ExecPlan with compliance and evidence mapping.

These controls improve auditability, recovery, and cross-Agent consistency, but
they also make process compliance consume attention before a model can explore
alternatives. The same default is applied to local experiments, ordinary
reversible implementation, and irreversible architecture or data changes even
though those activities have materially different risk.

The affected boundary spans the root routing Skill, professional Skill
activation, Engineering Specification routing, Agent adapters, Harness policy,
and completion handoff. A durable decision is required because relaxing one
prompt or template without a shared risk model would create inconsistent
behavior across Agents and could silently weaken real authority, safety, or
evidence controls.

## Decision Drivers

- Preserve explicit human authority for durable decisions and externally
  persistent or destructive actions.
- Preserve integrity checks for locked Specifications, accepted ADRs, sealed
  Research, Benchmarks, Checkpoints, and completed ExecPlans.
- Let models inspect alternatives and perform bounded reversible work without
  first constructing a persistent governance graph.
- Scale process cost to public impact, reversibility, security, data,
  reliability, compatibility, and external side effects.
- Make escalation deterministic enough to test while retaining task-semantic
  judgment that cannot be inferred from paths alone.
- Keep the Agent-neutral Core and thin-adapter boundary selected by ADR-012.
- Avoid silently weakening existing repositories during Harness upgrade.
- Keep the current strict workflow available for high-assurance repositories
  and tasks.

## Research Evidence

No additional persistent Research package is required. The decision direction
was fixed by the Repository Owner in the current conversation after reviewing
the concrete Explore, Build, and Governed proposal. Repository-local evidence
is sufficient to define the problem and implementation boundary:

- `assets/adapters/codex/engineering-specs/SKILL.md` routes every implementation
  and review task through a recorded activation or justified `none` result.
- `engineering-execution-plan/SKILL.md` defaults complex features toward
  concluded Research and requires explicit reasons for skipped gates.
- `engineering-execution-plan/assets/execplan.md` requires a complete,
  self-contained execution and compliance record before implementation.
- ADR-010 records the existing strict activation policy; ADR-012 separates the
  shared activation engine from runtime adapters, which remains valid.
- The existing lightweight thread-plan route proves that the product already
  recognizes different work sizes, but it does not currently propagate that
  distinction consistently into activation and handoff enforcement.

The implementation questions are bounded to classification, policy storage,
adapter behavior, and migration. They do not require further evidence to choose
between universal strictness and risk-adaptive governance.

## Considered Options

### Keep the current universal high-assurance workflow

This maximizes uniformity and auditability, but continues to charge exploration
and ordinary reversible work the same coordination cost as durable engineering
decisions. It encourages template completion over alternative discovery.

### Remove most workflow gates and rely on final tests

This maximizes local freedom, but loses explicit decision authority,
predeclared measurement rules, cross-session recovery, and integrity evidence
exactly where those controls are valuable.

### Let every Skill independently decide when to be strict

This permits incremental changes, but produces inconsistent task
classification, adapter behavior, and user expectations. The same request may
be light in one Agent and fail closed in another.

### Adopt shared risk-adaptive governance modes

Define Explore, Build, and Governed once; keep hard boundaries active in all
modes; and scale professional artifacts, Spec activation, mutation gates, and
handoff evidence to the effective mode. Preserve current strict behavior as the
Governed mode and as an explicit repository profile.

## Decision Outcome

Adopt shared risk-adaptive governance modes as defined in
`docs/design-docs/risk-adaptive-agent-governance.md`.

Explore permits bounded reversible work without mandatory persistent artifacts
or a manual no-Spec receipt. Build requires a concise task contract, directly
applicable requirements, and proportional verification. Governed retains the
full Research, ADR, ExecPlan, Benchmark, sealing, and strict handoff workflow
when a durable risk trigger applies.

The effective mode is the highest minimum selected by the user, repository
policy, applicable Specification, and observed task risk. Tasks promote when
new evidence crosses a boundary. Hard authority, destructive-action, security,
data-integrity, and evidence-integrity controls never become advisory.

Fresh Harnesses use the adaptive profile. Existing Harnesses preserve their
installed strict behavior until an explicit previewed migration selects
adaptive. After this ADR is accepted, ADR-010's universal strict enforcement
policy is superseded by this mode-aware policy; ADR-012's Agent-neutral Core
and adapter separation remains a prerequisite.

## Decision Statement

RepoFoundry will govern Agent work through shared Explore, Build, and Governed
modes selected by observable risk, keeping hard authority and integrity
boundaries universal while scaling process gates and artifacts to the work.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | task governance classification | Resolve an effective `explore`, `build`, or `governed` mode from the highest user, repository-policy, applicable-requirement, and observed-risk minimum, and retain machine-readable reasons. | Classifier fixtures and cross-adapter parity tests |
| C-002 | must | every governance mode | Preserve explicit authority, destructive/external-action controls, security and data-integrity stops, locked/sealed evidence verification, user-change preservation, and honest observable verification. | Safety, authority, tamper, and destructive-action tests |
| C-003 | must | Explore mode | Permit bounded reversible inspection, experiments, and local edits without mandatory persistent governance artifacts, manual Spec activation, or a justified no-Spec receipt; promote before crossing a Build or Governed trigger. | Explore mutation, no-receipt, hard-boundary, and promotion tests |
| C-004 | must | Build mode | Require only a concise intent/path/acceptance contract, directly applicable Engineering Specification requirements, proportional verification, and compatibility reporting; absence of a Research or ADR trigger needs no persistent skip artifact. | Build contract, requirement-selection, and handoff tests |
| C-005 | must | Governed mode | Retain explicit Research conclusion, ADR authority, resumable ExecPlan, predeclared Benchmark, compliance mapping, and sealed completion gates whenever their existing applicability trigger is present. | Existing governed workflow parity suites and repository validation |
| C-006 | must_not | classification and promotion | Do not lower mode or split scope to bypass an established hard boundary or applicable repository policy; record reasoned promotion when risk grows without fabricating prior Research history. | Downgrade-rejection and mid-task promotion tests |
| C-007 | must | Harness compatibility | Default fresh Harnesses to adaptive governance, preserve existing strict behavior until an explicit previewed migration, and retain a repository-selectable strict profile. | Bootstrap, upgrade preview/apply, preservation, and rollback tests |
| C-008 | must | Core and Agent adapters | Keep classification, policy evaluation, Spec semantics, and receipts in the Agent-neutral Core; adapters translate runtime events and enforcement surfaces without changing effective mode semantics. | Core product-name scan and multi-adapter parity fixtures |
| C-009 | must_not | Agent workflow contracts | Do not require one prescribed reasoning sequence or persistent artifact graph when the effective mode's observable contract and universal hard boundaries are satisfied. | Skill contract tests and low-risk end-to-end scenarios |

## Consequences

### Positive

- Models regain room to compare, prototype, and correct course before committing
  to a durable workflow.
- Ordinary implementation carries a smaller context and documentation tax.
- High-risk work retains the current evidence and authorization guarantees.
- A shared classifier makes the behavior explainable and testable across Agent
  runtimes.
- Professional Skills remain independently useful instead of becoming
  mandatory ceremony for every non-trivial request.

### Negative

- Classification adds a policy surface and can be wrong; promotion and
  repository minimums must compensate for under-classification.
- Adaptive behavior is less uniform than universal strictness and requires
  scenario-based tests rather than one unconditional write gate.
- Router receipts, Hooks, handoffs, templates, examples, and migrations all
  need coordinated changes.
- Users may need to understand why a task promoted modes even though they did
  not explicitly request more process.

### Migration and operations

- Existing accepted and sealed artifacts remain unchanged.
- Existing repositories remain strict unless their owner applies an adaptive
  migration after preview.
- New repositories record the adaptive profile and policy schema in the
  Harness manifest.
- Runtime receipts are ephemeral and are not migrated.
- Repositories can pin strict mode or declare minimum modes for sensitive paths
  and requirements.

## Confirmation

- Add table-driven classification tests for low-risk, production, public API,
  security, data, migration, reliability, release, and explicit-user cases.
- Prove Explore can make a reversible local edit without a Spec receipt while
  destructive, external, security, and evidence-integrity violations still
  stop.
- Prove Build activates the smallest complete direct Requirement set and emits
  the concise contract without Research/ADR skip artifacts.
- Re-run all current governed Router, Research, ADR, ExecPlan, Benchmark,
  evidence, and completion tests as strict-mode parity coverage.
- Prove fresh adaptive Bootstrap, strict upgrade preservation, explicit
  migration, customized-file conflict handling, idempotence, and rollback.
- Run `python3 -B scripts/check.py` as the repository-wide acceptance entrypoint.

## Revisit Triggers

- Production evidence shows adaptive classification regularly misses security,
  data, compatibility, or irreversible-operation boundaries.
- The process cost of classification and promotion approaches the current
  universal strict workflow.
- Agent runtimes expose a standard, trustworthy risk and policy protocol that
  can replace RepoFoundry's classifier.
- Repositories consistently choose strict mode, showing that adaptive defaults
  do not match the target audience.
- Governed evidence becomes cheap enough to apply universally without reducing
  solution quality or useful context.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-004", "ADR-012"]
- Amended ADRs: []
- Amended constraints: []
- Design documents: ["docs/design-docs/risk-adaptive-agent-governance.md"]
- Related ExecPlans: none yet; create one only after this decision is explicitly
  accepted.

## Revision Notes

- 2026-08-13T09:25:23Z — Proposed ADR created.
- 2026-08-13 — Defined the three governance modes, universal hard boundaries,
  promotion rules, strict compatibility profile, and cross-adapter
  confirmation contract.
