---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: ADR-058
title: "Separate ADR history from lossless decision working context"
status: accepted
research_refs: []
depends_on: ["ADR-014", "ADR-016"]
amends: []
amends_constraints: []
design_refs: ["docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
supersedes: []
superseded_by:
decision_maker: "Wangxiaowei1"
decided: "2026-09-01T00:49:43Z"
decision_outcome: accepted
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256: 7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b
created: 2026-08-31
updated: 2026-09-01
author: "Codex"
owner: "Wangxiaowei1"
---

# Separate ADR history from lossless decision working context

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

RepoFoundry currently preserves atomic ADR history and projects current effect, but
its default retrieval unit is still either the flat `DECISIONS.md` index or complete
ADR documents. That works for a small corpus. It becomes inefficient when a mature
repository has dozens of current ADRs, long amendment chains, hundreds of structured
constraints, and ExecPlans that reference a large portion of the graph.

The DataFox corpus observed on 2026-08-31 makes the pressure concrete: 51 ADRs, 46
effective decisions, 18 partially amended decisions, 86 typed relationship edges,
279 structured current constraint rows, a 38-ADR largest connected component, and an
active ExecPlan referencing 28 ADRs and 225 constraints. Retiring decisions merely to
reduce this working set would misuse lifecycle and erase current authority. Loading
every current ADR into every Agent turn wastes context and makes relevant constraints
harder to identify.

RepoFoundry therefore needs a durable boundary between normative ADR history and
bounded working context. The choice affects persistent repository files, public CLI
commands, source verification, context overflow behavior, Harness upgrades, and the
authority required for later semantic consolidation, so it cannot remain an
implementation detail.

## Decision Drivers

- Atomic ADRs, stable constraint IDs, decision seals, and lifecycle authority must
  remain the normative audit source.
- Working context must reflect recursively current accepted decisions and current
  amendments, not a stale hand-written summary.
- Normative text supplied to an Agent must be exact, attributable to local source
  bytes, and digest-verifiable.
- Context limits must fail explicitly instead of silently truncating or summarizing.
- Domain organization must be reusable and repository-owned, while task selection
  must remain narrow and ephemeral.
- Legacy linked ADRs must remain usable without pretending that an unsafe partial
  normative boundary can be inferred.
- Corpus pressure must be observable by dimension rather than hidden behind one
  quality score.
- Semantic consolidation must retain normal ADR review and Decision Owner authority.
- Existing repositories and Harness manifests must upgrade additively and be able to
  downgrade without losing ADR history.

## Research Evidence

No new Research package is required. The route is bounded by repository facts,
accepted architecture, and explicit product direction:

- the DataFox corpus measurements above demonstrate the retrieval pressure and the
  amendment/active-plan coupling that a solution must handle;
- ADR-016 already separates immutable decision outcome from reversible current
  effect and prohibits inferred lifecycle mutation;
- ADR-014 establishes stable artifact identity, ownership, lifecycle visibility,
  and repository provenance; and
- the existing Engineering Specifications Router proves a reusable safety pattern:
  stable-ID selection, exact dependency resolution, digest-verified local source
  ranges, an explicit byte budget, and fail-closed overflow.

These facts do not prove that automatic semantic merging is safe. That absence is
negative evidence in favor of retrieval compaction first and owner-reviewed
consolidation later.

## Considered Options

### A. Keep only the flat index and load complete ADRs

This preserves authority but does not bound task context or organize a large corpus.

### B. Retire, archive, or delete ADRs when count or age crosses a threshold

This reduces visible files by confusing current effect with retrieval cost. It can
remove decisions that still constrain the implementation and cannot be automated
safely.

### C. Generate LLM summaries or merge each domain into one mega ADR

Summaries create a second, unverifiable source of truth. A mega ADR destroys atomic
acceptance, amendment, supersession, and stable constraint references. Either shape
requires semantic authority that a context-management command does not have.

### D. Add lossless Decision Views and task capsules above the current-effect model

Persistent views provide domain navigation, task capsules select exact normative
bytes under a budget, health exposes corpus pressure, and a consolidation command is
limited to impact preview. Source ADRs and their lifecycle remain unchanged.

## Decision Outcome

Propose **Option D**.

RepoFoundry will compress ADR context through derived, non-normative retrieval
projections. A Decision View stores explicit current ADR seeds and is regenerated
from repository source. A task capsule resolves current effect and emits exact
Decision Statements and structured constraint rows, falling back to the whole source
document for legacy ADRs. The compiler enforces a byte budget without summarization
or truncation. Health and consolidation analysis remain read-only.

This option bounds working context while preserving the only safe authority chain:
source ADR -> explicit current effect -> exact derived view/capsule. It is additive,
reversible, mechanically verifiable, and does not grant lifecycle authority to a
retrieval mechanism.

## Decision Statement

RepoFoundry must compact ADR working context through deterministic, non-normative Decision Views and exact digest-verifiable task capsules over the current-effect graph, must fail rather than summarize or truncate on budget overflow, and must keep semantic consolidation preview-only until a new atomic ADR receives explicit Decision Owner authority.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | authority boundary | ADR source documents, stable constraint IDs, decision payload seals, explicit authority, and lifecycle status must remain the normative source; Decision Views, capsules, health output, and consolidation previews must declare themselves non-normative and must not modify those sources. | ADR byte-diff tests, lifecycle command audit, and generated-output headers |
| C-002 | must | current-effect resolution | A view or capsule must accept current `accepted` ADR seeds only, expand typed `depends_on` and `amends` closure, add current scoped amendments, reject non-current or cyclic inputs, and preserve amendment annotations instead of silently deleting amended source rows. | graph fixtures covering accepted, proposed, review, retired, superseded, cycles, and partial amendments |
| C-003 | must | source fidelity | Strict ADR context must be copied exactly from its `Decision Statement` and selected `Normative Constraints` source bytes and tied to the sealed ADR payload; linked legacy ADR context must use the exact whole document unless it is explicitly migrated to a strict contract. | substring equality, payload/document SHA-256, drift, UTF-8, and legacy fallback tests |
| C-004 | must_not | context budget | Capsule compilation must not summarize, paraphrase, omit required selected bytes, or truncate to satisfy a budget; overflow must fail with total and per-source byte costs, and a budget above the default must require an explicit reviewed reason. | budget boundary and overflow diagnostics tests |
| C-005 | must | persistent navigation | Decision View configuration must use stable kebab-case identity, explicit direct ADR seeds, deterministic generated repository projections, preview/apply mutation, repository locking, atomic rollback, idempotent reindex, and validation of projection drift. | CLI preview/apply/idempotency, rollback, reindex, validation, path, and symlink tests |
| C-006 | must | task capsule | A task capsule must support a named view or explicit ADR seeds plus optional stable constraint selection, report direct and resolved ADRs, source digests, exact selected constraint IDs, capsule bytes and SHA-256, and remain an ephemeral Architecture Input aid rather than a replacement for an ExecPlan Compliance Matrix. | CLI schema and golden capsule tests plus EP contract regression tests |
| C-007 | must | health model | ADR health must expose separate corpus, contract, graph, constraint, amendment, active-plan, view-coverage, and context-cost dimensions with explainable thresholds; it must not collapse them into an opaque score or trigger lifecycle changes. | metric fixture tests and mutation-free command audit |
| C-008 | must_not | semantic consolidation | Consolidation analysis must be preview-only and must not merge, accept, retire, supersede, rewrite, or delete ADRs; any semantic consolidation must create a new atomic ADR and use normal explicit Decision Owner authorization and effect-transition rules. | consolidation impact fixtures and before/after repository digest equality |
| C-009 | must | compatibility and rollout | The capability must be additive to existing ADR/config/Harness schemas, install through a versioned RepoFoundry release, create only empty view infrastructure during explicit Harness upgrade, preserve customized project files, and leave source ADRs usable after downgrade. | installer, bootstrap, upgrade dry-run/apply, downgrade-readability, and DataFox integration tests |

## Consequences

Positive consequences:

- mature repositories can keep complete ADR history while giving Agents bounded,
  task-relevant context;
- generated context stays traceable to stable IDs and verified repository bytes;
- domain taxonomy becomes reusable without turning it into a normative decision;
- pressure signals identify whether the problem is legacy format, amendment depth,
  graph coupling, active-plan scope, missing views, or raw context size; and
- future consolidation begins from explicit impact evidence rather than file count.

Costs and risks:

- maintainers must curate view membership; automatic semantic classification is not
  part of the authority model;
- a large legacy ADR consumes whole-document budget until migrated;
- partial amendments remain visible as multiple exact constraints and require human
  interpretation; the resolver cannot claim that every amendment fully replaces its
  target row;
- view/capsule commands add a new registry and generated index to validation; and
- callers may need to partition tasks or select stable constraints when a domain view
  exceeds the default capsule budget.

Migration is additive. RepoFoundry 0.8.0 creates an empty view registry and index on
explicit Harness upgrade. Repositories opt into views through preview/apply commands;
no ADR lifecycle changes occur during migration.

## Confirmation

- `python3 -B scripts/check.py` passes the complete provider-neutral integrity suite.
- `epctl` fixtures prove current-effect closure, exact source extraction, digests,
  budget failure, view idempotency, rollback, health metrics, and mutation-free
  consolidation preview.
- Harness installer/bootstrap/upgrade tests prove additive file creation and preserve
  customized repository content.
- Repeated `epctl reindex` produces no diff and `epctl validate` detects generated
  view drift without changing ADR sources.
- A released distribution is installed into the local Codex host, DataFox previews
  and applies the Harness upgrade, and DataFox view/health/capsule commands validate
  against its real mixed strict/legacy corpus.

## Revisit Triggers

- Typed amendments gain an explicit replace/extend semantic that permits stronger
  automatic effective-constraint reduction.
- Exact capsules routinely exceed reviewed budgets after task partitioning.
- Repositories require cross-repository views with multiple decision authorities.
- View configuration itself becomes normative and needs owner approval lifecycle.
- A verified classifier can propose domain membership with useful precision and a
  safe preview/apply human review boundary.
- Legacy ADRs acquire a common mechanically verifiable normative-section contract.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-014", "ADR-016"]
- Amended ADRs: []
- Amended constraints: []
- Design documents: ["docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-08-31T23:57:24Z — Proposed ADR created.
