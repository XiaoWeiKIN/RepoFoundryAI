---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: ADR-019
title: "Organize Design packages as technical architecture documentation"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-018"]
amends_constraints: ["ADR-018#C-006", "ADR-018#C-008"]
design_refs: []
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicitly accepted ADR-019 in the current Codex conversation on 2026-09-04)"
decided: "2026-09-04T07:33:04Z"
decision_outcome: accepted
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256: 8c867f1cf7c10a58aa86e6813640a9a47682eac7e31b4060c0b117d00987f62a
created: 2026-09-04
updated: 2026-09-04
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Organize Design packages as technical architecture documentation

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-018 models a Design Package around governance concerns and `designctl` maps member roles
onto `architecture/`, `contracts/`, `data/`, `operations/`, `migration/`, and `verification/`.
That contract is mechanically sound but shapes authored documentation around a review checklist.
In real use it produced a directory per concern, duplicated overview material across `DESIGN.md`
and members, and encouraged migration or verification documents even when the requested artifact
was only contributor-facing technical architecture documentation.

The product now has a separate `detailed-design` authoring skill whose purpose is to establish a
reader's mental model from flows, abstractions, boundaries, and code mappings. The governed Design
Package envelope should use the same information architecture when multiple architecture documents
are actually needed. Governance metadata must not determine the reader-facing document tree.

## Decision Drivers

- A contributor should enter through one overview and follow system behavior before source layout.
- Package directories should represent architecture reading routes, not governance concerns.
- Optional concerns must appear only when they materially shape the architecture.
- Existing schema-1.1 packages must remain readable and verifiable without bulk rewriting.
- Manifest, stable identity, atomic approval, and immutable snapshot guarantees must remain intact.
- The authoring skill and lifecycle skill must retain separate responsibilities.

## Research Evidence

No new Research package is required. The decision is grounded in the observed DD-008 output,
the existing `detailed-design` method, and the Repository Owner's explicit direction on
2026-09-04 that the desired artifact is Technical Architecture Docs and does not require default
migration or verification document categories.

## Considered Options

1. Keep the ADR-018 concern-oriented package tree and improve wording only. This preserves the
   generator but leaves the directory taxonomy as a strong authoring prompt.
2. Remove package structure entirely and allow arbitrary files. This maximizes freedom but loses a
   stable entry path and predictable navigation for large architecture sets.
3. Keep the governed package envelope while replacing its content taxonomy with reader-oriented
   Technical Architecture Docs routes and preserving legacy package compatibility.

## Decision Outcome

Propose option 3. It preserves the integrity guarantees that justify a governed package while
removing migration, verification, operations, data, and interface concerns from the physical
document topology. New packages follow how engineers learn a system: overview, behavior, concepts,
subsystems, extension points, deep dives, and contributor navigation.

## Decision Statement

RepoFoundry shall organize new governed multi-document Designs as Technical Architecture Docs with
reader-oriented navigation, while treating concern coverage as optional content rather than a
required directory structure and preserving existing packages as compatible legacy layouts.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | new package information architecture | A new multi-document Design must use `DESIGN.md` as its overview and may organize focused members under `how-it-works/`, `core-concepts/`, `subsystems/`, `extension-points/`, `deep-dives/`, and `contributor-guide/`. | package creation and manifest tests |
| C-002 | must_not | authoring topology | The generator and review workflow must not create or require `contracts/`, `data/`, `operations/`, `migration/`, or `verification/` merely to mirror coverage concerns. | new-package filesystem fixture and routing eval |
| C-003 | must | concern selection | Migration, verification, operations, security, data, and compatibility content appears only when it materially shapes the selected architecture; absent concerns require neither empty sections nor `Not applicable` prose. | authoring evals and review fixtures |
| C-004 | must | package navigation | A package must expose one root `README.md` reading map and stable package-local member identities; role metadata describes a reading route and must not force a concern-oriented physical path. | manifest, sync, move, and snapshot tests |
| C-005 | must | compatibility | Existing packages using `docs/README.md` and the ADR-018 managed roots remain readable, synchronizable, publishable, and verifiable without byte rewriting. | legacy package compatibility fixtures |
| C-006 | must | capability boundary | `detailed-design` owns ordinary architecture-document authoring and review; `engineering-design` adds DD identity and lifecycle only when governed publication is explicitly required. | root and skill routing evals |

## Consequences

Positive consequences:

- package navigation follows reader intent and the architecture narrative;
- ordinary designs stop accumulating empty or low-value concern documents;
- the same authoring model works for a single Markdown file and a larger documentation set;
- governance remains available without dominating content structure.

Negative consequences:

- `designctl` must recognize both new and legacy reading-map locations and managed roots;
- role values and generated examples change, so downstream tests and documentation require updates;
- heterogeneous old and new package layouts coexist until authors explicitly reorganize old packages.

Existing packages are not automatically moved or rewritten.

## Confirmation

- A new-package test asserts the Technical Architecture Docs directories and root reading map.
- Legacy fixtures prove existing concern-oriented packages still sync, validate, and snapshot.
- Routing evals distinguish ordinary architecture authoring from DD lifecycle work.
- The repository integrity check validates Skill metadata, links, eval catalogs, and all lifecycle tests.

## Revisit Triggers

- Architecture readers cannot find material by lifecycle or subsystem without another stable route.
- Real packages require a content type that cannot fit the reader-oriented member model.
- Maintaining dual legacy/current layouts creates more risk than an explicit repository migration.
- The manifest and snapshot envelope is no longer needed by any downstream consumer.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-018"]
- Amended constraints: ["ADR-018#C-006", "ADR-018#C-008"]
- Design documents: []
- Related ExecPlans: none yet.

## Revision Notes

- 2026-09-04T07:08:44Z — Proposed ADR created.
