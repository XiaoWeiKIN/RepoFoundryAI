---
schema_version: "1.1"
metadata_schema: "1"
artifact_type: design-doc
id: DD-012
doc_type: design
layout: single
title: "Lossless ADR context compaction"
status: current
working_revision: "2"
published_revision: "2"
research_refs: []
research_not_required_reason: "DataFox corpus measurements, accepted ADR-016 current-effect semantics, and the existing digest-verified Engineering Specifications capsule establish the problem and reusable safety pattern; no unresolved evidence question changes the design route."
adr_refs: ["ADR-014", "ADR-016", "ADR-058"]
design_dependencies: ["uses:DD-010"]
decision_not_required_reason: ""
approved_by: "Wangxiaowei1"
approved_at: "2026-09-03T04:37:04Z"
approval_ref: "conversation:2026-09-03-dd-012-revision-2"
superseded_by: ""
terminal_reason: ""
revision_reason: "DataFox task-partitioned OQL constraint capsules still expand a 29-ADR amendment component and exceed the 32 KiB budget; add explicit focused materialization while preserving full closure validation and the published revision 1 contract."
author: "Codex"
owner: "Wangxiaowei1"
created: 2026-08-31
updated: 2026-09-03
---

# Lossless ADR context compaction

This document is the entrypoint for `DD-012`. The logical Design and all
managed package members share one review and approval boundary.

## Design Summary

RepoFoundry treats ADR compression as a retrieval projection, not as history
deletion or semantic rewriting. Atomic ADR files remain the normative and auditable
source. A deterministic resolver derives the recursively current decision set,
current amendment annotations, stable provenance, and exact structured constraint
rows. Three consumers sit above that resolver:

1. `adr-health` reports corpus pressure as separate, explainable dimensions;
2. persistent Decision Views group current ADRs into named working contexts; and
3. `decision-capsule` compiles an exact, digest-verifiable task context under an
   explicit byte budget.

Revision 2 separates **closure validation** from **context materialization**.
`complete` materialization remains the default and preserves the revision 1 output.
An explicitly requested `focused` materialization first validates the same complete
current-effect closure, then emits only requested structured constraints and the
complete constraint sets of current amendments that directly or recursively target
those rows. It never walks backward from a materialized amendment to all unrelated
historical targets. The capsule declares itself partial, records why focus was
chosen, lists omitted-but-validated ADRs, and provides a digest of the complete
validated closure so an Agent can hydrate more context when task scope expands.

`adr-consolidation-plan` remains preview-only. It identifies amendment chains,
legacy contracts, proposed overlap, and active ExecPlan impact, but it never merges,
retires, supersedes, accepts, or rewrites an ADR. Semantic consolidation still
requires a new atomic ADR and explicit Decision Owner authority.

The design is valid while RepoFoundry ADRs have stable IDs and lifecycle metadata,
strict ADRs expose stable `Decision Statement` and `Normative Constraints` sections,
and focused retrieval is treated as a task aid rather than evidence of complete
architecture compliance. Linked legacy ADRs remain conservative whole-document
inputs to complete capsules and cannot be guessed into a structured focus boundary.

## Goals and Non-goals

Goals:

- make a corpus with dozens of ADRs navigable without weakening historical audit;
- separate corpus health, reusable domain navigation, and task-specific context;
- resolve current effect from accepted ADR relationships instead of trusting a
  manually maintained summary;
- keep selected normative bytes exact and attributable to repository sources;
- let a caller materialize a small exact constraint focus without skipping
  validation of the complete current-effect closure;
- make complete versus focused context explicit and machine-readable;
- fail closed when a capsule exceeds its reviewed context budget;
- make every persistent change preview-first, deterministic, and idempotent; and
- give maintainers evidence for later semantic consolidation without performing it.

Non-goals:

- deleting, archiving, retiring, superseding, accepting, or rejecting ADRs based on
  age, count, size, graph position, or an LLM recommendation;
- treating a Decision View or capsule as a new normative decision;
- inventing a universal numeric architecture quality score;
- summarizing or truncating normative text to fit a model context window;
- automatically switching from complete to focused context after an overflow;
- claiming that a focused capsule proves compliance with omitted decisions;
- inferring a safe partial extract from a linked legacy ADR that lacks structured
  normative sections; or
- replacing Architecture Input Sets, Compliance Matrices, ADR seals, or explicit
  decision authority in ExecPlans.

## Research and Decision Inputs

### Supported Findings and Confidence

The DataFox corpus observed on 2026-08-31 contains 51 ADRs and 10,228 lines. Its
current projection contains 46 effective ADRs, 18 partially amended decisions, 86
typed relationship edges, 279 structured current constraint rows, and a largest
weakly connected component of 38 ADRs. One active ExecPlan references 28 ADRs and
225 constraints. These measurements establish high confidence that flat file count
and the current `DECISIONS.md` table are no longer sufficient task entrypoints.

The existing Engineering Specifications Router already demonstrates the relevant
safety pattern: select stable IDs, resolve an exact closure, read local verified
source bytes, compile a bounded context capsule, and fail rather than summarize or
truncate on overflow. Confidence is high that the same separation applies to ADR
retrieval, while ADR current-effect relationships require an ADR-specific resolver.

ADR-016 already separates immutable decision outcome from reversible current
effect. Therefore compaction can be built as a projection above that effect model
without changing or weakening the accepted lifecycle.

The follow-up DataFox measurement on 2026-09-02 exercises the revision 1 mechanism
against seven Decision Views covering all 47 current ADRs. The
`span-query-oql-lineage` view resolves 29 current ADRs. Its complete capsule is
144,285 bytes; selecting only `ADR-049#C-001` or `ADR-049#C-003` still produces a
112,668-byte capsule because the current selector expands backward through every
target named by a materialized amendment and keeps every resolved Decision
Statement.

A read-only design probe retained validation of all 29 source ADRs but applied the
revision 2 one-way materialization boundary. Four representative task focuses
materialized one or two ADRs and produced exact prototype contexts of 1,764 bytes
(`ADR-049#C-001`), 6,236 bytes (`ADR-049#C-003`), 6,456 bytes
(`ADR-049#C-009`), and 6,141 bytes (`ADR-049#C-010` plus `C-011`). These are
high-confidence feasibility measurements, not released implementation evidence;
the final format will add a compact closure manifest and must be remeasured by the
ExecPlan.

### Negative Evidence and Rejected Hypotheses

The DataFox corpus rejects several tempting shortcuts:

- retiring by age or count would hide current decisions and confuse lifecycle with
  retrieval cost;
- one mega ADR would destroy atomic acceptance, amendment, supersession, and stable
  constraint references;
- an LLM summary cannot prove semantic equivalence and would silently create a
  second, unauthorised source of architectural truth;
- using graph centrality as an automatic consolidation decision would confuse
  structural coupling with common decision ownership; and
- extracting selected paragraphs from legacy ADRs is unsafe because those documents
  do not expose a machine-verifiable normative boundary.
- splitting the OQL corpus into more views or choosing a single ADR seed does not
  bound context when every seed resolves the same amendment component; and
- filtering constraint rows only after bidirectional amendment expansion cannot
  solve the pressure because one requested row expands to 20 constraint-owning ADRs.

The design therefore allows generated navigation and exact extraction, while
keeping semantic consolidation as an explicit later decision.

### Remaining Unknowns and Validity Conditions

Domain membership is a human architectural classification. RepoFoundry will store
explicit Decision View seed ADRs and resolve their current closure; it will not infer
domain names from embeddings or filenames. A future evidence-backed classifier may
propose view membership, but automatic application is outside this revision.

The 32 KiB default capsule budget remains an operational default, not a semantic
limit; a caller may raise it only with an explicit reviewed reason. Focus is chosen
before byte accounting and never as an automatic reaction to overflow. The final
closure manifest adds bytes beyond the design probe, so DataFox integration must
prove the representative focused capsules remain under budget.

Legacy ADRs remain readable but are whole-document-only in capsules. Evidence that
a repository has a stable, mechanically identifiable legacy decision section may
justify an explicit migration adapter later; this design does not guess one.

ADR-level amendments without stable `amends_constraints` targets make row-level
focus unprovable. Focused materialization fails closed when such a current amendment
could affect a requested row. Complete materialization remains available, and a
future richer amendment mapping may reduce this limitation.

### ADR Constraints

- ADR-014 C-001 and C-004 require stable identity, lifecycle visibility, and
  repository-backed provenance for governed artifacts. Decision Views are explicitly
  non-normative projections, but their registry and generated paths still use stable
  slugs, deterministic source references, and validation.
- ADR-016 C-001 through C-008 require outcome history to remain immutable, current
  effect to be derived from lifecycle and typed relations, historical decisions to
  stay discoverable, and lifecycle transitions to retain explicit authority. The
  resolver consumes these rules; none of the new commands may mutate ADR lifecycle.
- ADR-058 C-001 through C-009 authorize revision 1 lossless Decision Views, complete
  capsules, health, and preview-only consolidation. Its C-006 task-capsule contract
  currently materializes the resolved context as the interpretation frame.
- A new amending ADR is required before release because a declared partial
  materialization mode changes the durable task-capsule boundary. Until that ADR is
  accepted and this exact revision is approved, focused implementation cannot be
  merged or released.

## System Context and Invariants

```mermaid
flowchart TB
    A["Atomic ADR corpus\nimmutable outcome + reversible effect"] --> R["Complete current-effect resolver"]
    R --> X["Validated closure\nall sources, seals, relations"]
    X --> C["Complete materializer\ndefault revision 1 behavior"]
    X --> F["Focused materializer\nexplicit partial task context"]
    F --> Q["Requested rows + downstream scoped amendments"]
    X --> H["ADR Health\npressure dimensions"]
    X --> V["Decision Views\npersistent non-normative maps"]
    X --> P["Consolidation Plan\npreview only"]
    P -.->|"explicit new ADR + owner authority"| A
    V -.->|"never normative"| A
    C -.->|"exact complete projection"| A
    Q -.->|"exact partial projection + hydration manifest"| A
```

Invariants:

- an ADR path, decision payload, stable constraint ID, and decision authority remain
  owned by the ADR lifecycle;
- a view contains current accepted ADRs only and stores direct seeds separately from
  the derived closure;
- dependency and amendment closure is resolved from repository bytes on every
  render, so a view cannot freeze stale current-effect claims;
- complete materialization remains the default and stays byte-compatible with the
  revision 1 capsule for identical repository bytes and arguments;
- focused materialization is available only with explicit stable constraints and a
  non-empty focus reason; overflow never changes the materialization mode;
- a focused capsule validates every ADR in the complete closure but materializes
  only requested rows and complete constraint sets from downstream current scoped
  amendments; it lists every omitted-but-validated ADR and declares that the
  context is partial;
- focused amendment traversal follows target row -> current amender rows only. It
  never treats an amender's other historic targets as newly requested rows;
- original constraint rows targeted by current amendments remain visible when they
  are selected and are annotated; no mode silently replaces them as if every
  amendment were total;
- proposed, review-required, retired, rejected, and superseded ADRs never enter a
  current capsule through default resolution;
- generated source excerpts are exact UTF-8 substrings or whole documents, and every
  source carries a digest; and
- health or preview output cannot call lifecycle mutation commands.

## Proposed Architecture

`epctl.py` has five bounded components; revision 2 extends only the capsule compiler
and keeps parser, lifecycle, registry, health, and consolidation ownership intact:

1. **Decision registry** — `docs/.epctl/decision-views.json`, schema version 1,
   stores `{id, title, adr_refs}` for each stable kebab-case view. It is the only
   persistent source owned by the view feature.
2. **Current-effect resolver** — validates requested current ADRs, expands
   `depends_on` and `amends`, recursively adds current scoped amendments, and returns
   ordered source metadata, relationship annotations, and structured constraints.
3. **View renderer** — writes deterministic generated documents under
   `docs/decision-views/` and a rebuildable `docs/DECISION-VIEWS.md` entrypoint. A
   view contains exact Decision Statements for strict ADRs, constraint identities,
   current amendment annotations, and links to source documents.
4. **Capsule compiler** — accepts a view or explicit ADR selection, optional exact
   constraint IDs, and a materialization mode. `complete` emits the revision 1 exact
   Decision Statement/constraint or whole-document bytes. `focused` keeps the full
   validated closure but materializes a directional constraint subgraph, a compact
   closure digest, omitted source IDs, and exact bytes only from participating strict
   ADRs. Overflow is an error with per-materialized-source byte costs.
5. **Health and consolidation analyzers** — read the same resolver model and active
   ExecPlans. Health exposes independent counts and graph pressure. Consolidation
   output is a read-only impact preview.

The dependency direction is parser -> complete resolver -> materialization policy ->
renderer/analyzer. The focus policy consumes the validated resolver result; it
cannot bypass source validation, currentness, cycle checks, or seals. Renderers do
not introduce another lifecycle model, and ADR transition code does not depend on
views or capsules.

## Interfaces and Contracts

Public CLI contracts:

```text
epctl adr-health [--json]
epctl set-decision-view VIEW --title TITLE --adr ADR-NNN [--adr ...] [--apply]
epctl remove-decision-view VIEW [--apply]
epctl decision-capsule (--view VIEW | --adr ADR-NNN [--adr ...])
    [--constraint ADR-NNN#C-NNN ...] [--budget-bytes N]
    [--budget-reason TEXT]
    [--materialization complete|focused] [--focus-reason TEXT] [--json]
epctl adr-consolidation-plan (--view VIEW | --adr ADR-NNN [--adr ...]) [--json]
```

`set-decision-view` and `remove-decision-view` are preview-first. Preview returns the
exact registry and generated-file delta but writes nothing. `--apply` executes under
the existing repository lock and rolls back registry/index/view bytes if rendering
or validation fails. Repeating the same applied command is byte-stable.

`decision-capsule` is read-only. `--materialization complete` is the default and
retains revision 1 behavior: `--constraint` filters constraint rows only, every
resolved strict ADR Decision Statement remains an interpretation frame, and every
resolved legacy ADR is included as its exact whole document. Without
`--constraint`, all strict constraints in the resolved context are included. The
command rejects unknown, non-current, out-of-view, or duplicate references.

`--materialization focused` requires at least one `--constraint` and a non-empty
`--focus-reason`. It uses this deterministic algorithm:

1. resolve and validate the complete current-effect closure exactly as complete
   mode does;
2. initialize the selected row set with the explicitly requested constraints;
3. for each selected row, find every current accepted ADR whose
   `amends_constraints` explicitly contains that row, materialize that ADR's exact
   Decision Statement and complete structured constraint set, and enqueue those
   constraint rows for the same downstream lookup;
4. materialize each requested-row owner with its exact Decision Statement and only
   its selected rows; and
5. stop without following a participating ADR's other `amends_constraints` targets
   backward into unrelated historical rows.

The result is a directional current-effect focus, not a claim that omitted
dependencies or historical targets are irrelevant. If any current whole-ADR
amendment could affect a requested row but lacks stable scoped targets, focused mode
fails with `FOCUSED_CONTEXT_AMENDMENT_SCOPE_UNPROVABLE`. A caller must use complete
mode or migrate the amendment contract; the compiler never guesses.

Budgets below or equal to 32 KiB need no reason. A larger budget requires
`--budget-reason`; no budget permits truncation. Complete overflow never retries as
focused. JSON mode retains the revision 1 fields and, for focused mode, adds a
`focus` object with schema version 1, the reason, `context_completeness`, validated,
materialized and omitted ADR IDs, omitted relation references, and the complete
closure digest. `sources` and `source_costs` describe materialized bytes;
`validated_sources` records the digest metadata for the full closure.

`adr-health` and `adr-consolidation-plan` expose stable JSON schema version 1 and a
human-readable table. Health has no opaque aggregate score. Consolidation output
always declares `preview_only: true`.

## Data Model and State Ownership

`decision-views.json` uses this shape:

```json
{
  "version": 1,
  "views": [
    {
      "id": "oql-compiler",
      "title": "OQL compiler decisions",
      "adr_refs": ["ADR-049", "ADR-056", "ADR-057"]
    }
  ]
}
```

View identity is a stable kebab-case slug. View records have no accepted/rejected
lifecycle because they are navigation configuration, not decisions. Updating a view
replaces its title and direct seeds atomically; deleting a view requires the explicit
preview/apply remove command. The renderer owns `docs/decision-views/<id>.md` and the
managed region in `docs/DECISION-VIEWS.md`.

ADR documents, their seals, and `.epctl/adr-revisions` remain untouched. Digests in a
view or capsule are derived from current repository bytes. No secrets, network
content, model output, or user data are persisted by this feature.

Focused output owns no repository state. Its `validated_closure_sha256` is computed
over canonical UTF-8 JSON containing ordered direct and resolved ADR IDs plus each
validated source's ADR ID, repository-relative path, document SHA-256, and sealed
payload SHA-256. Canonical JSON sorts object keys, uses compact separators, preserves
Unicode, and has no trailing newline. This digest proves which complete validated
closure the partial materialization came from without copying every source body into
the Agent context.

The Markdown capsule includes a prominent `focused_partial` declaration, focus
reason, validated/materialized/omitted IDs, closure digest, selected rows, and exact
materialized source blocks. `unmaterialized_relation_refs` names dependency or
historic amendment targets reachable from participating ADRs but intentionally not
hydrated. An Agent must request additional constraints or complete materialization
when its task crosses one of those boundaries.

## Control and Data Flows

```mermaid
sequenceDiagram
    participant U as Agent
    participant E as epctl
    participant R as ADR resolver
    participant S as Repository sources
    participant M as Materializer

    U->>E: decision-capsule + selection + mode
    E->>R: resolve complete current-effect closure
    R->>S: read once; validate lifecycle, relations, seals
    S-->>R: exact bytes and digest metadata
    R-->>E: complete validated closure
    alt complete materialization
        E->>M: materialize revision 1 context
    else explicit focused materialization
        E->>M: directional row-to-amender traversal
        M->>M: build closure manifest and omitted boundary
    end
    M->>M: enforce budget without adaptive omission
    M-->>U: exact capsule + digests, or fail closed
```

Capsule compilation is read-only. Each source body and digest come from the same
in-memory bytes. Concurrent writers serialize through the existing `.epctl/lock` for
mutations; capsule reads fail on invalid intermediate state instead of returning a
partially trusted result. A retry recomputes the complete closure and may therefore
produce a new closure digest after a legitimate repository change.

## Failure Semantics and Recovery

The resolver fails closed for duplicate IDs, unknown ADRs, invalid seals, non-current
seeds, relationship cycles, missing amendment targets, invalid constraint rows,
symlink escapes, non-UTF-8 data, and unsupported registry schema. Capsule compilation
fails with an actionable cost breakdown when bytes exceed budget.

Focused materialization additionally fails for missing constraints, missing focus
reason, a requested legacy/whole-document boundary, any current broad amendment that
could affect a selected row without a stable constraint target, or inconsistent
validated/materialized manifests. Failure emits no partial context. It never falls
back to complete mode, raises the budget, summarizes text, or silently omits another
selected row. The operator may choose complete mode, add constraints, migrate the
ambiguous ADR contract, or provide a reviewed larger budget and retry.

Preview commands never create `docs/.epctl`, indexes, directories, or lock files.
Apply takes snapshots of every managed target before writing. A failure restores
existing files and removes only newly created generated targets. `reindex` rebuilds
all registered views from source bytes; `validate` reports registry or projection
drift and may use `--fix-index` for generated projections only. Neither command
changes ADR documents or lifecycle.

## Compatibility, Migration, and Rollout

The feature is additive. Existing `.epctl/config.json`, ADR schemas, `DECISIONS.md`,
and Harness manifests remain readable. `epctl init` and an explicit RepoFoundry
Harness upgrade create an empty schema-1 view registry, `docs/decision-views/`, and
`docs/DECISION-VIEWS.md` without creating any domain view.

Distribution version 0.8.0 carries the revision 1 components. Revision 2 targets an
additive 0.8.1 release. It changes no ADR, Decision View, Harness, or persisted
repository schema. Existing calls default to `complete`, and their Markdown bytes,
JSON fields, validation behavior, and budget semantics remain unchanged. Focus-only
fields are additive and appear only when the caller explicitly requests focused
materialization.

A project previews and applies `repofoundry upgrade --to 0.8.1`, then may use the new
flag with its existing Decision Views. Downgrading to 0.8.0 leaves all project files
readable because focused capsules are ephemeral and no migration state persists.
The local Codex Skill and project Harness producer version advance through the normal
release and upgrade workflow; a project does not need to recreate its views.

No migration automatically retires or consolidates ADRs. Any later consolidation is
a separate proposed ADR, explicit owner decision, implementation/migration, and
supersession or retirement operation.

## Security, Privacy, and Operations

All inputs are repository-local. Existing path normalization, symlink rejection,
repository locking, atomic writes, and strict UTF-8 parsing apply. The capsule is
Markdown data, never executable instructions; consumers must treat source text as
architecture context rather than shell input.

The principal revision 2 risk is scope misuse: exact bytes can still be incomplete
for a broader task. The explicit non-default mode, mandatory reason,
`focused_partial` marker, complete validated-closure digest, omitted ADR list, and
unmaterialized relation list make that boundary visible. Focused output is suitable
for task-local reasoning and progressive hydration; it is not sufficient evidence
for a full architecture review, an ExecPlan Architecture Input Set, or a Compliance
Matrix. A task whose files, behavior, or acceptance criteria expand must hydrate the
new constraints or rerun complete mode.

Operational visibility comes from `adr-health --json`, which reports corpus counts,
contract mix, relation edges, connected-component sizes, structured constraints,
amendment pressure, active-plan load, view coverage, and estimated capsule bytes.
Signals identify the exceeded dimension and threshold; they do not mutate state or
page an operator. The repository owner owns view taxonomy and any decision to begin
semantic consolidation.

## Verification Strategy

Unit and integration tests will prove:

- view preview is side-effect free and apply is idempotent;
- current dependency/amendment closure and annotations are deterministic;
- proposed, under-review, retired, rejected, and superseded ADRs are rejected as
  direct current view inputs;
- strict excerpts are exact source substrings and sealed source drift fails;
- selected constraint filtering rejects out-of-view or unknown IDs;
- linked legacy ADRs use whole-document mode and participate in byte budgets;
- default overflow and unjustified raised budgets fail with cost details;
- identical complete-mode invocations remain byte-for-byte compatible with 0.8.0;
- focused mode requires constraints and reason, validates the full closure, and
  reports deterministic validated/materialized/omitted partitions;
- directional selection follows requested row -> scoped amender rows recursively
  but does not expand backward to unrelated targets named by an amender;
- every focused Decision Statement and constraint row is an exact source substring,
  and the canonical closure digest changes when any validated source digest changes;
- broad whole-ADR amendments and legacy focus boundaries fail closed;
- focused overflow reports materialized costs and never changes mode or drops rows;
- registry/schema/path/symlink errors fail closed and partial writes roll back;
- reindex is byte-stable and validation detects generated drift;
- health metrics and consolidation impact match fixture graphs and active plans;
- consolidation commands never change ADR or ExecPlan bytes; and
- Harness bootstrap/upgrade creates the additive files while preserving customized
  existing project content.

Final verification runs `python3 -B scripts/check.py`, direct CLI smoke tests against
a fixture corpus, RepoFoundry self-validation, installation from the release source,
and a real DataFox preview/apply/validate sequence. DataFox evidence must show the
same 29-ADR closure was validated, representative OQL focuses materialize only their
directional owners, each capsule remains below 32 KiB, no ADR source hash changes,
and the pre-existing complete-mode output remains unchanged.

## Alternatives, Open Questions, and Revisit Triggers

Rejected alternatives remain deletion/retirement by pressure, generated prose
summaries, a consolidated mega ADR, and automatic semantic clustering. Raising the
budget alone only postpones context pressure. Automatically changing existing
`--constraint` behavior would turn a previously complete interpretation frame into
an undeclared partial one. Filtering source bodies after the current bidirectional
selection still materializes 20 OQL ADR owners. The explicit directional focus is
the smallest additive boundary that addresses the measured failure while preserving
the complete path.

Open follow-ups, none of which block revision 2:

- a future view membership recommender may produce preview-only suggestions;
- a future task router may activate a view from planned paths after the project has
  an explicit path-to-view mapping contract; and
- a future legacy migration may convert selected documents to strict ADRs so their
  capsules no longer require whole-document fallback.
- a future amendment contract may map each amender constraint to one or more target
  constraints, allowing a narrower focus than today's atomic amender constraint set;
  and
- `adr-health` may later report representative focused costs, after production use
  establishes stable and explainable thresholds.

Revisit this design if focused capsules routinely require immediate hydration, if
broad amendment ambiguity is common, if typed amendments gain explicit row-to-row
replace/extend semantics, if focused closure manifests approach the budget, or if
repositories need views spanning multiple independent ADR authorities.

## Package Document Map

Single-file layout; every required concern is covered in this entrypoint.

## Revision Notes

- 2026-08-31 — Created working revision 1.
- 2026-09-02 — Opened working revision 2 after DataFox constraint selection still
  expanded to a 29-ADR, 112,668-byte context; specified explicit focused
  materialization with complete closure validation and directional amendment
  hydration.
