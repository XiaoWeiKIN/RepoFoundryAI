---
schema_version: "1.3"
metadata_schema: "1"
artifact_type: adr
id: ADR-014
title: "Require semantic metadata for governed engineering artifacts"
status: accepted
research_refs: []
depends_on: []
amends: []
amends_constraints: []
design_refs: ["docs/design-docs/artifact-metadata-contract.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicitly accepted ADR-014 in the current Codex conversation on 2026-08-04)"
decided: "2026-08-04T07:33:38Z"
payload_sha256: bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7
created: 2026-08-04
updated: 2026-08-04
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Require semantic metadata for governed engineering artifacts

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

RepoFoundry governs long-lived Research, architecture decisions, execution
plans, tasks, checkpoints, benchmarks, case studies, and design documents.
Those artifacts currently use related but inconsistent frontmatter. Some name
an owner but not an author; some omit a stable artifact class or ID; some
derived evidence carries hashes but no portable attribution. A reader can use
Git to reconstruct part of the history, but copies, exports, snapshots, and
installed Skill templates may be consumed outside the original checkout.

Adding arbitrary headers to every file would create noise and stale
duplication. The durable boundary must distinguish semantically governed
artifacts from source code, configuration, raw evidence, and generated
projections, while retaining each artifact type's independent lifecycle and
integrity rules.

## Decision Drivers

- Make artifact identity and provenance portable outside Git history.
- Distinguish writing, stewardship, decision authority, approval, generation,
  and execution rather than collapsing them into one actor field.
- Give humans and agents one predictable metadata vocabulary across Skills.
- Keep artifact-specific schemas and lifecycle states independently evolvable.
- Include metadata in immutable evidence boundaries so attribution cannot be
  changed silently after a decision or seal.
- Preserve valid sealed historical artifacts without mass rewrites.
- Avoid decorative metadata on source code, generated indexes, and other files
  whose canonical provenance already comes from Git or a generator.

## Research Evidence

No additional Research package is required. The repository already exposes the
affected artifact schemas, seal boundaries, and compatibility tests, and the
Repository Owner explicitly requested common author/date metadata for important
files in the current Codex conversation. The open question is a governance
choice over known local contracts, not an evidence-dependent technology
selection. The detailed inventory and migration design are recorded in
`docs/design-docs/artifact-metadata-contract.md`.

## Considered Options

### Rely only on Git history

This avoids schema changes but loses semantic authorship and ownership when an
artifact is copied, rendered, snapshotted, installed, or reviewed without its
repository history. Commit authorship also cannot represent decision authority
or ongoing accountability.

### Let every artifact type define unrelated metadata

This minimizes immediate coordination but preserves vocabulary drift and makes
cross-Skill validation and agent consumption conditional on artifact-specific
guessing.

### Add author headers to every repository file

This is superficially uniform but creates duplicated, stale comments in source,
configuration, and generated projections. It obscures the smaller set of files
that carry governance meaning.

### Use one common metadata layer with artifact profiles

Governed Markdown carries common frontmatter; structured and raw evidence uses
equivalent manifest metadata plus hashes. Artifact-specific schemas retain
their own fields, lifecycle, authority records, and compatibility rules.

## Decision Outcome

Adopt the common metadata layer with artifact profiles. It provides portable
identity and responsibility without pretending that all files have the same
lifecycle. It also lets current schemas fail closed while legacy sealed
artifacts remain readable under their original contract.

## Decision Statement

RepoFoundry will require versioned semantic metadata on governed engineering
artifacts, use manifests for raw or binary evidence, and preserve distinct
fields for authorship, ownership, authority, generation, and execution.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | current human-governed Markdown artifacts | Carry `metadata_schema`, `artifact_type`, stable `id`, `title`, `status`, `author`, `owner`, `created`, and `updated` using the meanings in DD-008. | Template contract tests and each Skill validator |
| C-002 | must | raw, binary, and generated evidence bundles | Carry equivalent identity, authorship, ownership, lifecycle, and time metadata in a manifest whose inventory binds evidence files with SHA-256. | Research and Benchmark manifest validation plus tamper tests |
| C-003 | must_not | all governed artifacts | Do not infer `decision_maker`, `approved_by`, `executed_by`, or `generated_by` from `author` or `owner`; event authority remains explicit. | Lifecycle command tests and sealed payload validation |
| C-004 | must | current schemas and immutable lifecycle states | Validators must enforce the common contract, and metadata must enter the applicable ADR, Checkpoint, Research, ExecPlan, or Benchmark integrity boundary when sealed. | Missing-field and metadata-tampering tests |
| C-005 | must | legacy and active artifacts | Preserve valid sealed legacy artifacts under their original schemas; migrate mutable active artifacts in place and never rewrite sealed history solely to add metadata. | Legacy compatibility suites and active R-002 validation |
| C-006 | should | source, configuration, generated indexes, and projections | Use Git, CODEOWNERS, generator provenance, and canonical source links instead of decorative per-file author headers unless the file is independently governed. | Repository contract classification test and design review |

## Consequences

### Positive

- Humans and agents can identify a governed artifact without its original Git
  checkout.
- Shared actor semantics prevent authorship from becoming accidental approval.
- Cross-Skill tooling can validate one common layer while artifact profiles
  evolve independently.
- Sealed attribution becomes tamper-evident.

### Negative

- Current artifact schemas and test fixtures must advance together.
- Authors and owners must be supplied or inherited; `Unassigned` is visible
  technical debt rather than hidden absence.
- Maintainers must update both the common contract and affected profiles when a
  shared field changes meaning.

### Migration and operations

- Active R-002 migrates in place to the current Research metadata profiles.
- Existing accepted ADRs, completed Research, completed ExecPlans, and sealed
  Benchmark runs retain their historical schemas and bytes.
- Existing Design Docs receive stable `DD-NNN` identities because they are
  mutable architecture explanations, not sealed decisions.
- New Skill commands accept `--author`; child artifacts inherit a parent actor
  only where that relationship is explicit.

## Confirmation

- `researchctl`, `epctl`, and `benchctl` reject missing or mismatched common
  metadata on their current schemas.
- ADR and Checkpoint tests prove that changing sealed metadata breaks the
  recorded digest.
- Repository contract tests prove all governed templates expose the common
  fields and all Design Docs have unique `DD-NNN` IDs.
- Legacy schema fixtures remain valid without retroactive metadata injection.
- `python3 -B scripts/check.py` and each modified Skill's quick validator pass.

## Revisit Triggers

- A standard provenance format can represent artifact identity, responsibility,
  lifecycle authority, and integrity without RepoFoundry-specific fields.
- Real repositories show that embedded metadata causes more drift than portable
  value even with mechanical validation.
- Artifact storage moves to a system that guarantees equivalent portable
  metadata and content-addressed export at every boundary.
- A profile needs actor or time semantics that cannot be represented without
  changing the common metadata schema.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: []
- Amended constraints: []
- Design documents: ["docs/design-docs/artifact-metadata-contract.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-08-04T06:51:58Z — Proposed ADR created.
- 2026-08-04 — Defined the common metadata boundary, six normative
  constraints, migration policy, and mechanical confirmation suite.
