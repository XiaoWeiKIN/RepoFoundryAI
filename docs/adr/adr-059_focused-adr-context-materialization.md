---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: ADR-059
title: "Add explicit focused materialization to ADR task capsules"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-058"]
amends_constraints: ["ADR-058#C-006"]
design_refs: ["docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
supersedes: []
superseded_by:
decision_maker: "Wangxiaowei1"
decided: "2026-09-03T04:37:04Z"
decision_outcome: accepted
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256: 9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc
created: 2026-09-02
updated: 2026-09-03
author: "Codex"
owner: "Wangxiaowei1"
---

# Add explicit focused materialization to ADR task capsules

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-058 introduced lossless Decision Views and task capsules so a large ADR corpus
could retain atomic history while giving an Agent bounded exact context. Its complete
current-effect resolver is deliberately conservative: a seed expands dependencies,
whole-ADR amendments, scoped amendments, and source Decision Statements before
constraint rows are filtered.

DataFox now provides the first production-scale feedback on that contract. Seven
views cover all 47 current ADRs, but the `span-query-oql-lineage` view resolves a
29-ADR amendment component. The complete capsule is 144,285 bytes. Selecting only
`ADR-049#C-001` or `ADR-049#C-003` still produces 112,668 bytes and expands to
constraint rows owned by 20 ADRs, so neither more views nor the existing constraint
filter meets the 32 KiB default budget.

The pressure is caused by conflating two operations: validating that a requested
decision is current within its complete closure, and materializing every resolved
Decision Statement into an Agent prompt. RepoFoundry needs a narrower task retrieval
mode without weakening complete validation, changing default output, summarizing
normative text, or presenting partial context as complete architecture compliance.
The distinction affects a public CLI, exact-source guarantees, omission semantics,
compatibility, and Agent safety, so it requires a durable decision rather than an
implementation-only optimization.

## Decision Drivers

- Every source in the current-effect closure must still be validated for lifecycle,
  relation integrity, cycles, seals, encoding, and currentness.
- Existing complete capsule calls and exact output must remain compatible.
- Focus selection must be deterministic, explainable, stable-ID based, and explicit.
- Materialized normative bytes must remain exact source substrings with verifiable
  source and closure digests.
- A partial retrieval boundary must be unmistakable to both humans and machines.
- Ambiguous whole-ADR amendments and legacy documents must fail closed rather than
  be assigned an invented row-level meaning.
- Overflow must never trigger hidden omission, summarization, or a mode change.
- Retrieval must not gain authority to accept, retire, supersede, or semantically
  consolidate ADRs.
- The capability should require no persisted schema migration and remain reversible
  by downgrading the tool.

## Research Evidence

No new Research package is required. The decision is bounded by accepted ADR-058,
the approved DD-012 revision 1 contract, repository-local DataFox measurements, and
the explicit requirement to improve RepoFoundry before changing DataFox ADR effect.

A read-only prototype kept all 29 OQL ADRs in the validated closure but followed
only requested constraint -> current scoped amender edges for materialization. Four
representative focuses materialized one or two ADRs and measured 1,764, 6,236,
6,456, and 6,141 bytes before adding the final compact closure manifest. This is
strong feasibility evidence for a two-tier resolver/materializer boundary. It is not
release evidence; an ExecPlan must implement the exact contract and reproduce the
measurements against DataFox.

Negative evidence is equally important. Raising the budget does not change growth,
splitting views does not split a connected amendment closure, and filtering source
bodies after the existing bidirectional constraint expansion still retains 20 ADR
owners. Automatic semantic consolidation is not a safe substitute because current
DataFox work still depends on the affected decisions and owner authorization has not
been granted for a successor decision.

## Considered Options

### A. Keep complete materialization and raise the budget

This preserves semantics but makes prompt cost scale with the connected component
and only postpones the same failure.

### B. Materialize only owners from the existing selected-constraint expansion

This removes Decision Statements from nine OQL sources, but the bidirectional
expansion still reaches 20 owners because each amender leads backward to every target
it declares. It does not meet the measured bound.

### C. Change existing `--constraint` behavior to directional partial context

This is compact, but silently changes an existing complete interpretation frame into
a partial one and breaks output hashes and caller expectations.

### D. Add an explicit focused materialization after complete validation

Keep complete mode as the default. Focused mode requires stable constraints and a
reason, validates the full closure, follows only downstream scoped amendment edges,
emits exact participating source bytes, and declares everything omitted.

### E. Semantically consolidate the DataFox ADR component immediately

A successor ADR may ultimately reduce graph coupling, but that is a separate design
and authority action. It cannot safely serve as a retrieval optimization while
active plans and draft designs still depend on the existing decisions.

## Decision Outcome

Propose **Option D**.

Separating validation from materialization retains RepoFoundry's fail-closed trust
boundary while making task context proportional to the explicitly selected current
effect. The non-default mode and omission manifest prevent it from masquerading as a
complete architecture input. Existing callers keep revision 1 behavior, and no
repository state or ADR lifecycle changes are introduced.

## Decision Statement

RepoFoundry must preserve complete ADR task-capsule materialization as the default and may add an explicitly requested focused-partial mode that validates the entire current-effect closure but materializes only requested structured constraints and their downstream scoped amendments, using exact source bytes, an auditable omission manifest, and fail-closed ambiguity and budget behavior.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | validation boundary | Every focused invocation must first resolve and validate the same complete current-effect closure as complete mode, including accepted/current status, dependencies, amendments, cycles, exact source bytes, UTF-8, and decision seals; focus may change materialization only. | parity fixtures comparing complete and focused validated ADR/digest manifests plus invalid-source failures |
| C-002 | must | compatibility | `complete` must remain the default, and an invocation using only revision 1 arguments must preserve its Markdown bytes, JSON contract, source costs, budget behavior, and capsule SHA-256. | 0.8.0 golden-output compatibility tests |
| C-003 | must | explicit focus | Focused materialization must require one or more in-closure stable constraint references and a non-empty focus reason, must declare `focused_partial`, and must never be selected automatically after overflow. | CLI argument, header, JSON, and overflow-no-fallback tests |
| C-004 | must | directional selection | Focused selection must begin with requested rows, recursively add the complete structured constraint set of every current ADR that explicitly amends a selected row, and must not add other historical target rows merely because a participating ADR declares them in `amends_constraints`. | branching amendment fixtures proving downstream recursion and no reverse-target expansion |
| C-005 | must | fidelity and provenance | A focused capsule must copy each participating ADR Decision Statement and selected constraint row exactly, expose materialized source digests, list the complete validated source digest manifest, and bind that manifest to a deterministic closure SHA-256. | byte-substring, CRLF, Unicode, canonical JSON, drift, and digest tests |
| C-006 | must | omission boundary | Focused output must distinguish validated, materialized, and omitted ADRs, identify unmaterialized dependency and amendment relation references, and instruct the consumer to hydrate more constraints or use complete mode when task scope crosses that boundary. | human/JSON golden capsules and scope-expansion fixtures |
| C-007 | must | ambiguity failure | Focused mode must fail without output when a requested boundary is legacy/whole-document or when a current whole-ADR amendment could affect a selected row without stable scoped targets; it must not infer row-level semantics. | legacy and unscoped-amendment failure fixtures |
| C-008 | must_not | budget behavior | No focused budget path may summarize, paraphrase, truncate, adaptively omit a selected row or participating source, raise its own budget, or change materialization mode; overflow must report exact materialized costs. | boundary, overflow, and repository-mutation audit tests |
| C-009 | must_not | authority boundary | A focused capsule must not be treated as a full Architecture Input Set or Compliance Matrix and must not accept, retire, supersede, rewrite, delete, or semantically consolidate any ADR. | generated warning contract, lifecycle call audit, and source-tree digest equality |
| C-010 | must | rollout | The change must ship additively in a versioned RepoFoundry release without a persisted schema migration; complete mode and Decision Views must remain usable after downgrade, and focused output must remain ephemeral. | install, upgrade, downgrade-readability, and DataFox integration tests |

## Consequences

Positive consequences:

- task context size becomes proportional to a named constraint focus rather than the
  largest connected amendment component;
- every source is still validated before any byte is omitted from materialization;
- exact bytes and digests preserve provenance without introducing an LLM summary;
- default callers and stored Decision Views remain compatible; and
- omitted boundaries become inspectable hydration choices instead of invisible loss.

Costs and risks:

- focused context is intentionally incomplete and can be misused if a task expands
  without hydration;
- current broad amendments and legacy ADRs cannot participate in row-level focus;
- an amending ADR is still atomic for materialization, so all of its constraint rows
  are included even if only one target triggered it;
- CLI and JSON contracts gain a second materialization mode and closure manifest; and
- true graph reduction still requires a separately accepted successor ADR and
  authorized effect transitions.

Migration is additive. RepoFoundry 0.8.1 can expose the new ephemeral mode without
changing ADR files, view configuration, Harness schema, or existing capsule calls.
Downgrading removes the command capability but loses no repository information.

## Confirmation

- Existing 0.8.0 complete-capsule goldens remain byte-identical.
- Unit fixtures cover directional amendment traversal, recursive current amenders,
  reverse-target non-expansion, broad amendments, legacy sources, cycles, drift,
  exact bytes, canonical closure digests, missing reasons, and budget failures.
- `python3 -B scripts/check.py` passes the complete provider-neutral suite.
- Installation and upgrade tests prove no persisted schema migration and safe
  downgrade to 0.8.0.
- DataFox replays the four representative OQL focuses, validates the same 29 ADRs,
  stays below 32 KiB, and preserves the aggregate hash of every source ADR.

## Revisit Triggers

- Focused capsules frequently need immediate hydration before a task can proceed.
- Broad amendment ambiguity prevents focus in a material fraction of repositories.
- Amendment metadata gains a verified row-to-row replace/extend mapping that can
  safely narrow an amender's atomic constraint set.
- The compact validated-closure manifest itself approaches the default budget.
- Consumers need a normative partial-compliance artifact rather than a
  non-normative retrieval aid.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-058"]
- Amended constraints: ["ADR-058#C-006"]
- Design documents: ["docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-09-02T10:12:51Z — Proposed ADR created.
