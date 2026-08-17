---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: ADR-018
title: "Make technical Design Docs a first-class governed artifact"
status: accepted
research_refs: []
depends_on: ["ADR-001", "ADR-004", "ADR-014"]
amends: []
amends_constraints: []
design_refs: ["docs/design-docs/first-class-technical-design-documents.md"]
supersedes: []
superseded_by:
decision_maker: "User (explicitly accepted ADR-018 Option D via response annotation in the current Codex conversation on 2026-08-17)"
decided: "2026-08-17T01:29:28Z"
decision_outcome: accepted
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256: 578dc79ed9f5fecc2d15a4ea550b63cc18e4e1301131476a4aa4439be81e9e6e
created: 2026-08-16
updated: 2026-08-17
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Make technical Design Docs a first-class governed artifact

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

RepoFoundry separates evidence production from implementation governance.
`engineering-research` owns Research questions, sources, experiments, a
multi-document corpus, and Synthesis. `engineering-execution-plan` consumes the
concluded Research contract, governs ADRs, and creates implementation plans.

The repository also contains `docs/design-docs/`, stable `DD-NNN` metadata, and
`design_refs` on ADRs and ExecPlans. Those files are linked inputs, not a
complete artifact lifecycle. Authors must allocate IDs and invent document
structure manually. `epctl` cannot create a Design Doc from a concluded
Synthesis, distinguish review readiness from architectural currency, require a
technical content profile, organize several documents into one coherent module
design, or show whether a Research result progressed into an implementable
design.

This omission is observable in the UModel research workflow cited by the user:
the Research can explain EntityType semantics in depth while leaving no
repository artifact that defines the target meta-format, registry components,
interfaces, state transitions, failure behavior, migration, and verification.
Treating the Research response as the design would collapse two distinct
review questions and turn an evidence artifact into an implicit system
contract.

Adding a first-class Design Doc changes public commands, artifact schemas,
professional-Skill ownership, architecture gates, and compatibility behavior.
Those interfaces require one explicit durable decision before implementation.

## Decision Drivers

1. Preserve a crisp semantic boundary between evidence, system design,
   decision authority, and delivery planning.
2. Give an Agent a deterministic path from concluded Research to an
   independently reviewable technical design.
3. Let one module design span multiple focused documents without losing a
   single identity, review boundary, or exact revision.
4. Split independently owned or independently released subdesigns into
   composable Design identities instead of one unbounded document tree.
5. Require enough content to describe interfaces, data, flows, failure
   behavior, compatibility, operations, and verification.
6. Keep ADRs as the only normative source of durable architecture constraints
   and explicit Decision Owner authorization.
7. Keep `engineering-research`, `engineering-design`, and
   `engineering-execution-plan` independently installable through versioned
   producer-consumer file contracts.
8. Reuse the existing architecture-root, `design_refs`, metadata, state, and EP
   validation surfaces instead of creating competing sources of truth.
9. Preserve existing Design Docs, accepted ADRs, and completed ExecPlans
   without synthetic provenance or bulk rewrites.
10. Make lifecycle readiness and downstream blockers visible to humans and
   Agents.
11. Keep Design-only requests free from unrelated Task, Checkpoint, Bugfix,
   technical-debt, and EP-archive instructions.

## Research Evidence

No new persistent Research is required for this product decision. The relevant
facts are directly verifiable in the repository and the desired capability is
explicit in the current user request.

- `engineering-research/SKILL.md` states that Research outputs a sealed
  Manifest and Synthesis and does not create ADRs or ExecPlans.
- `engineering-execution-plan/SKILL.md` lists `docs/design-docs/` as an
  optional architecture corpus and describes `DD-NNN` metadata, but its command
  surface has no Design creation or lifecycle operation.
- `epctl.py` validates linked Design Doc metadata, identity, status, and ADR/EP
  reference closure. It does not allocate a `DD` high-water ID, scaffold a
  technical content profile, manage package-local document identities and
  manifests, or consume Research into a Design Doc.
- The existing Design Docs are manually maintained schema `1` files. Their
  Git-backed compatibility behavior is useful and must remain readable.
- The referenced UModel task contains detailed evidence and proposed shapes in
  conversation, demonstrating that a rich Research answer still fails to
  create an architecture fact source.

[DD-011](../design-docs/first-class-technical-design-documents.md) translates
these facts into the proposed lifecycle, content profile, CLI, gates, and
compatibility contract.

## Considered Options

### Option A — Keep Design Docs as manually linked documents

Retain current metadata validation and rely on authors to create arbitrary
files. This has the lowest implementation cost, but it preserves the reported
gap: Research has no explicit technical-design handoff, content remains
inconsistent, and status cannot express review or downstream readiness.

### Option B — Let Engineering Research produce Design Docs

Add Design generation after Synthesis inside `engineering-research`. The
conversion would be convenient, but it would make the evidence producer choose
implementation architecture and would couple Research conclusion to a design
outcome. Research-only consumers would also load an unrelated lifecycle.

### Option C — Add Design Doc lifecycle to Engineering Execution Plan

Extend `epctl` and `engineering-execution-plan` with `DD-NNN` creation,
Research-input validation, a technical content profile, review/current states,
single and package layouts, manifest-backed revisions, dependency composition,
status reporting, and EP gates. This package already owns architecture inputs,
ADR references, plan compliance, and the `.epctl` state boundary.

### Option D — Add an independent Engineering Design skill

Create `engineering-design` and `designctl` as a fifth professional package.
It owns Design Package production, lifecycle, integrity, and publication.
`engineering-execution-plan` consumes the versioned Design contract and retains
ADR/EP closure. This adds installer, routing, documentation, test, and
compatibility surfaces, while keeping each user intent and artifact lifecycle
independently loadable.

## Decision Outcome

Propose Option D.

Add an independently installable `engineering-design` professional skill. It
scaffolds and validates the semantic translation from concluded Research into
an implementation-level architecture, manages Design Package membership and
revisions, and publishes an approved file contract. `engineering-research`
remains the evidence producer. `engineering-execution-plan` retains ADR and
delivery governance and consumes approved Design revisions without invoking
`designctl`.

One `DD-NNN` identifies one logical review and publication boundary. Bounded
designs may use a single Markdown file. Module and system designs use a stable
package directory with `DESIGN.md`, `DESIGN_MANIFEST.json`, a reading map,
package-local `DOC-NNN` members, linked artifacts, and sealed revision
snapshots. Subdesigns that require independent ownership, reuse, approval, or
rollout receive separate `DD-NNN` identities and compose through typed Design
dependencies.

The first release does not introduce partial package publication or an
automatic semantic generation engine.

## Decision Statement

RepoFoundry shall make each `DD-NNN` a first-class logical technical Design,
represented by either one document or a manifest-managed multi-document
package and owned by an independently installable `engineering-design` skill,
with an explicit concluded-Research handoff and revision lifecycle, while
`engineering-execution-plan` consumes the approved Design contract and retains
exclusive ownership of ADR authorization and delivery planning.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | Design producer ownership | `engineering-design` must exclusively own Design creation, lifecycle transitions, global and package-local ID state, manifests, snapshots, indexing, and publication validation. | independent Design package tests and ownership-contract tests |
| C-002 | must_not | Research producer boundary | `engineering-research` must not create, approve, supersede, or mutate Designs; it exports only its versioned Research package contract. | Research package tests and cross-package dependency scan |
| C-003 | must_not | execution consumer boundary | `engineering-execution-plan` must not allocate or mutate Design artifacts; it may parse and validate the approved Design contract for ADR and EP gates. | EP ownership tests and mutation-surface scan |
| C-004 | must | logical Design identity | Every new logical Design must use one repository-unique `DD-NNN`, common artifact metadata, a versioned Design schema, an explicit lifecycle state, and either a `single` or `package` layout. File count must not determine artifact identity. | `designctl new-design`, both-layout fixtures, duplicate-ID tests, and `designctl validate` |
| C-005 | must | Research-to-design handoff | A new Design must reference all relevant concluded and sealed Research packages or record a concrete Research-not-required reason, and must reproduce the findings, confidence boundaries, negative evidence, and remaining unknowns that shape the design. | Research fixture tests and required-concern validation |
| C-006 | must | technical content profile | A review-ready Design must cover scope, system context, components, interfaces, data ownership, flows, failure and recovery semantics, compatibility and migration, security and operations, and verification across its declared members; `Not applicable` requires a concrete reason. | coverage-map, template, and placeholder tests |
| C-007 | must | architecture authority | Design approval may confirm coherence and currency but must not accept an ADR, create normative constraints, or override `ADR-NNN#C-NNN`; durable choices require explicit ADR authorization. | cross-skill authority tests and EP compliance-matrix validation |
| C-008 | must | package membership | A package layout must have one stable `DESIGN.md` entrypoint, one manifest, one reading map, unique package-local `DOC-NNN` identities, typed member roles, and exact path/byte/SHA-256 membership. Unregistered or drifting managed files must fail review readiness. | manifest, identity, drift, traversal, and symlink tests |
| C-009 | must | design granularity | A member that requires independent ownership, reuse, approval, revision, or rollout must become another `DD-NNN`; Design dependencies must be typed, acyclic, and included in downstream closure. | dependency graph and independent-lifecycle fixtures |
| C-010 | must | revision integrity | Approval must atomically seal one complete Design revision and preserve an independently readable snapshot; revision work must not invalidate the last published revision used by existing consumers. | publish, revise, snapshot-tamper, and working/published revision tests |
| C-011 | must | delivery gate | New work must reject terminal Designs, warn on unpublished inputs, and prevent completed EP archival until every required Design and dependency has approved revision evidence and every applicable ADR is accepted and current. | cross-skill `new-ep`, `validate`, and `archive-ep` state/evidence tests |
| C-012 | must | compatibility | Existing schema `1` Design Docs must remain readable as legacy single-file architecture inputs and must not be bulk-rewritten solely to add manifests, lifecycle fields, snapshots, or inferred actors. | legacy fixtures and byte-preservation tests |
| C-013 | must | skill independence | `engineering-design` must consume Research and ADR facts through repository file contracts; `engineering-execution-plan` must consume Design facts the same way. Neither consumer may import a sibling professional Skill or depend on its installation path. | independently copied Research→Design→ADR/EP contract tests |
| C-014 | must | derived state | Global `DD` and package-local `DOC` high-water allocation must never reuse IDs; Design indexes and reading projections must be rebuildable while preserving human-authored content outside explicit managed markers. | gap-allocation, reindex idempotence, and index-preservation tests |

## Consequences

### Positive

- Users can request a technical design after Research and receive a stable,
  reviewable repository artifact instead of another research summary.
- Architecture reviewers can evaluate system behavior before authorizing an
  ADR or starting an ExecPlan.
- Agents can recover the system contract without replaying the Research chat
  or inferring design from evidence notes.
- Existing `design_refs` become produced and governed artifacts rather than
  loosely validated links.
- Large module designs can separate architecture, contracts, data, operations,
  migration, and verification without losing one approval boundary.
- Independently evolving subdesigns remain reusable through explicit Design
  dependencies rather than copied Markdown.
- The UModel workflow gains a clear place for the EntityType meta-format,
  registry architecture, publication state machine, compatibility rules, and
  failure semantics.

### Negative

- The distribution gains a fifth professional Skill, CLI, eval catalog,
  installer surface, routing entry, and compatibility contract.
- Producer and consumer packages must each parse the Design file contract,
  creating deliberate schema-validation overlap.
- Design review adds an explicit lifecycle gate before high-risk implementation
  can complete.
- Author and reviewer roles must distinguish Design currency from ADR decision
  authority.
- Package manifests, snapshots, and dependency closure add storage and
  validation cost beyond a single Markdown file.
- Atomic package approval requires cross-discipline review to converge before a
  new module revision becomes current.
- Rebuilding indexes without overwriting manual navigation requires managed
  marker and compatibility logic.

### Migration and operational impact

- Existing Design Docs remain legacy-current inputs; no immediate migration is
  required.
- Fresh repositories receive the Design skill registration, template, state,
  and index projection when the accepted change is implemented through a
  previewed Harness migration.
- Existing accepted ADRs and completed ExecPlans remain sealed and are not
  updated to add new Design lifecycle evidence.
- Root RepoFoundry bootstrap composes independently owned `designctl init` and
  `epctl init`; it does not absorb either lifecycle.

## Confirmation

Implementation must prove the constraints with:

1. focused `designctl` tests for ID allocation, traversal and symlink safety,
   lifecycle transitions, explicit actors, Research state and seal validation,
   both layouts, manifest drift, package-local document identities, immutable
   revision snapshots, Design dependency closure, ADR reference validation,
   supersession cycles, and index preservation;
2. template and repository-contract tests for every required technical section,
   metadata field, Skill instruction, README example, and eval trigger;
3. a copied-package producer/consumer test that creates concluded Research,
   creates and approves a multi-document Design Package, accepts an ADR with
   explicit authority, creates an EP, and validates the complete graph without
   importing sibling packages;
4. legacy schema `1` fixtures that remain byte-identical and usable;
5. independent `engineering-design` metadata, eval, portability, and copied
   installation tests;
6. `designctl validate` plus `epctl validate`, including Design revision and
   dependency evidence consumed by ADRs and EPs;
7. focused `test_designctl.py`, `test_epctl.py`, installer, routing, and
   repository-contract tests; and
8. `python3 -B scripts/check.py` as the canonical repository check.

## Revisit Triggers

- Design lifecycle collapses to metadata-only single files and no longer
  justifies an independent context or CLI.
- Producer-consumer contract evolution repeatedly requires synchronized
  breaking releases and cannot remain version-compatible.
- Design and execution governance require incompatible release cadences or
  ownership teams.
- Mutable current Design Docs cannot provide sufficient auditability through
  package snapshots and revision evidence, requiring a stronger external
  transparency log or signed approval evidence.
- Typical package revisions become too large for atomic review and cannot be
  decomposed into independently governed `DD-NNN` dependencies.
- Real use shows that `review_ready` versus `current` creates process weight
  without improving architecture or delivery outcomes.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-001", "ADR-004", "ADR-014"]
- Amended ADRs: []
- Amended constraints: []
- Design documents: ["docs/design-docs/first-class-technical-design-documents.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-08-16T09:47:38Z — Proposed ADR created.
- 2026-08-16 — Added the repository-gap evidence, four ownership options,
  proposed `engineering-execution-plan` ownership, normative constraints,
  compatibility rules, verification, and revisit triggers.
- 2026-08-16 — Revised the proposal after module-design review: one `DD-NNN`
  now supports single and manifest-managed package layouts, stable member
  identities, atomic revision snapshots, and typed composition of independent
  Designs.
- 2026-08-17 — Changed the proposed outcome from Option C to Option D after the
  multi-document model established an independent Design bounded context;
  Design production moves to `engineering-design`, while
  `engineering-execution-plan` becomes a contract consumer.
