---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: ADR-060
title: "Physically compact terminal ADRs into lossless history packs"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-058"]
amends_constraints: ["ADR-058#C-001", "ADR-058#C-008", "ADR-058#C-009"]
design_refs: ["docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
supersedes: []
superseded_by:
decision_maker: "Wangxiaowei1"
decided: "2026-09-03T09:34:06Z"
decision_outcome: accepted
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256: 773f40850444b167611da324f01bbca729ac3621fcfa2ee093b1b4d1d7af8886
created: 2026-09-03
updated: 2026-09-03
author: "Codex"
owner: "Wangxiaowei1"
---

# Physically compact terminal ADRs into lossless history packs

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-058 introduced lossless Decision Views, capsules, health metrics, and
preview-only consolidation so a large ADR corpus would not overload an Agent's
working context. Those projections reduce retrieval cost but intentionally leave
every ADR as an independent Markdown file. DataFox therefore still exposes 51 ADR
documents even though only 45 currently have effect and four implementation
decisions are intended to become historical under ADR-055.

The repository owner has authorized a second kind of compression: package explicit
historical ADRs and delete their independent files only after the packed
representation validates. That capability conflicts with ADR-058 C-001, C-008, and
C-009, which currently prohibit modification or deletion of source ADRs and require
the stored state to remain readable after downgrade. A durable amendment is needed
to distinguish physical representation from semantic consolidation, preserve the
authority and exact bytes of every logical ADR, and define the destructive boundary
before implementation.

## Decision Drivers

- Reduce physical document count without reducing logical ADR count, altering
  lifecycle, or inventing a replacement decision.
- Preserve exact original UTF-8 bytes, original repository-relative paths, document
  digests, sealed payload digests, stable IDs, relations, and historical evidence.
- Require explicit ADR IDs, actor, reason, and preview before any source file can be
  removed; selection by age, count, graph shape, or model inference is unsafe.
- Prove the candidate packed corpus before deleting an original and roll back every
  affected byte if the materialized state cannot validate.
- Keep validation, evidence resolution, indexes, and current-effect calculation
  offline and independent of Git object availability.
- Provide exact-byte unpacking as recovery and as the explicit preparation for
  downgrade to a pack-unaware RepoFoundry version.
- Make the compatibility boundary honest: applying a pack changes persisted schema
  even though installing the capability alone is additive.
- Keep semantic consolidation under normal Decision Owner authority.

## Research Evidence

No separate Research package is required. Approved DD-012 revisions 1 and 2, the
accepted ADR-016 current-effect model, existing digest-verified capsule behavior,
and direct DataFox corpus measurements establish the necessary boundary and safety
patterns. DD-012 working revision 3 records the detailed format, transaction,
security, validation, rollout, and recovery design.

The measured DataFox case is concrete: after the planned ADR-055 effect transition,
ADR-051 through ADR-054 are four historical logical decisions. Replacing their four
independent Markdown files with one exact-byte History Pack yields a net reduction
of three physical files while retaining all four IDs and payloads. It does not
address the 45 effective ADRs; further reduction there would require separate
semantic decisions.

## Considered Options

### A. Keep context compaction only

This preserves the ADR-058 storage contract but does not reduce filesystem document
count. It is safe but does not satisfy the authorized DataFox objective.

### B. Move, summarize, or delete historical Markdown files

A human- or model-written summary cannot prove byte fidelity. Moving files breaks
stable paths, and relying on Git history makes ordinary validation depend on
external object retention. Deletion without an embedded source is irreversible.

### C. Store exact terminal sources in one content-addressed History Pack

A deterministic JSON pack can embed exact original bytes and paths, independent
digests, actor, and reason. A unified resolver can expose live and packed records as
one logical corpus. Preview, candidate-state validation, an atomic apply transaction,
and exact-byte unpacking provide bounded destructive behavior and recovery.

### D. Store a manifest and payload as separate files or use an opaque archive

Two files reduce the physical count less and introduce another atomicity boundary.
An opaque archive makes review, schema validation, diffing, and selective logical
resolution harder without improving fidelity.

## Decision Outcome

Select **Option C**, subject to Decision Owner acceptance.

RepoFoundry will support explicit physical compaction of strict terminal ADRs into a
single deterministic, content-addressed History Pack. Packed bytes remain the
normative source representation for those logical ADRs and must resolve everywhere
their former live files resolved. Packing is not semantic consolidation and grants
no lifecycle authority. Original files may be removed only after the candidate
packed corpus validates; unpacking restores the exact files and is required before
a downgrade to a pack-unaware version.

This option is the only one that reduces the physical file count while preserving
offline auditability, stable identity, exact content, validation, and an explicit
recovery path.

## Decision Statement

RepoFoundry may physically compact explicitly selected strict terminal ADRs into deterministic content-addressed History Packs only when their exact bytes, original paths, seals, identities, relations, and lifecycle remain offline-resolvable, the candidate packed corpus validates before original files are deleted, the materialized change is atomic and rollback-safe, and exact-byte unpacking is available for recovery and downgrade preparation.

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | eligibility and authority | A pack command must require explicit ADR IDs, actor, reason, and preview, and may accept only live, regular, non-symlink strict ADRs under `docs/adr/` whose status is `rejected`, `retired`, or `superseded`; it must reject automatic selection and every current, proposed, review, linked-legacy, malformed, unsealed, duplicate, or already-packed source. | eligibility matrix, preview side-effect, and explicit-selection CLI tests |
| C-002 | must | exact pack representation | A schema-versioned History Pack must be one canonical content-addressed JSON file that records each ADR's ID, title, terminal status, normalized original path, exact original UTF-8 bytes encoded as Base64, document SHA-256, sealed payload SHA-256, actor, and reason, and must verify its own digest before exposing entries. | canonical serialization, golden pack, exact-byte, document/payload/self-digest, and ordering tests |
| C-003 | must | logical source resolution | Validation, indexes, relations, current-effect projection, capsules, health, and historical artifact evidence must resolve live and packed sources through one offline logical ADR model; duplicate IDs or logical paths, live/packed collisions, unsupported schemas, or any manifest/source mismatch must fail closed rather than choose a representation. | mixed-corpus integration, collision, drift, evidence, relation, index, and no-Git tests |
| C-004 | must | validate-before-delete transaction | Apply must repeat preflight under the repository lock, validate an in-memory candidate corpus from packed bytes before deleting any original, then atomically materialize the pack, remove only the selected files, rebuild generated projections, and validate the filesystem state; any failure after materialization must restore exact original, pack, and index bytes. | race, candidate-overlay, deletion-order, fault-injection, rollback-byte-equality, and idempotency tests |
| C-005 | must | unpack and recovery | RepoFoundry must provide preview-first, all-or-nothing unpacking that rejects destination conflicts, restores every recorded path with exact verified bytes, validates the live-source corpus, and removes the pack only after successful restoration; selective overwrite or lossy reconstruction is forbidden. | unpack preview/apply, conflict, exact round-trip, validation failure, and rollback tests |
| C-006 | must_not | lifecycle and semantic authority | Packing or unpacking must not accept, reject, retire, supersede, amend, merge, renumber, rewrite, or otherwise change any ADR payload or current effect; lifecycle mutation of a packed ADR must fail with an instruction to unpack first, and semantic consolidation remains subject to a new atomic ADR and explicit Decision Owner authority. | before/after parsed-model equality, lifecycle command audit, and semantic-consolidation regression tests |
| C-007 | must | compatibility and rollout | Installing or upgrading to the pack-aware release must preserve existing files and create no pack automatically; after a pack is applied, older pack-unaware versions are unsupported until every pack is successfully unpacked, and CLI/Harness upgrade and downgrade guidance must disclose this persisted-schema boundary. | installer, upgrade preview/apply, zero-auto-pack, old-version failure, and unpack-before-downgrade tests |
| C-008 | must | path and resource safety | Pack parsing and apply must use strict JSON and Base64 validation, canonical repository-relative POSIX paths strictly beneath `docs/adr/`, symlink and case-fold collision rejection, a maximum of 256 entries, 16 MiB decoded bytes per entry, and 64 MiB decoded bytes per pack, atomic writes, and repository locking; embedded Markdown is data and must never be executed or interpolated. | malformed-input, duplicate-key, path traversal, symlink, case collision, resource-boundary, and injection tests |
| C-009 | must | truthful observability | ADR health and pack results must report logical ADR count, effective ADR count, live ADR file count, pack count, packed-entry count, and net physical file reduction separately, and must never present physical packing as retirement or semantic consolidation. | health schema, count fixtures, pack/unpack delta, and human-output terminology tests |

## Consequences

Positive consequences:

- historical ADRs remain exact and auditable while occupying fewer independent
  source documents;
- every historical consumer sees one logical corpus instead of learning a special
  archive path;
- validate-before-delete, atomic rollback, and exact unpacking bound the destructive
  risk; and
- logical, effective, and physical pressure become separately observable.

Costs and risks:

- all ADR readers must use the logical source abstraction instead of assuming a
  real Markdown `Path`;
- packed repositories require a pack-aware RepoFoundry version until unpacked;
- a JSON pack is less convenient for direct Markdown browsing and editing, so
  packed ADRs must be unpacked before lifecycle mutation;
- implementation and tests must cover mixed live/packed corpora, transaction fault
  boundaries, path attacks, and resource exhaustion; and
- packing only historical decisions produces modest file reduction when most ADRs
  are still effective.

Neutral and migration consequences:

- installing the capability changes no repository state; packing remains a separate
  explicit operation;
- Git continues to provide useful review and commit history but is not needed to
  read or recover packed bytes;
- one pack may contain one ADR, though the command reports zero net file reduction;
  and
- DataFox can pack ADR-051 through ADR-054 only after all four have a valid terminal
  state and the upgraded Harness validates the unchanged corpus.

## Confirmation

Compliance is confirmed by unit, integration, property, and fault-injection tests
for deterministic serialization, exact-byte round trips, eligibility, mixed source
resolution, evidence and relation closure, collision and digest failures, preview
purity, candidate validation before deletion, atomic rollback, unpack conflicts,
path and resource safety, truthful health counts, and downgrade preparation.

Release verification must run `python3 -B scripts/check.py`, install the produced
RepoFoundry release, upgrade a fixture Harness, prove that an unchanged corpus has
identical logical resolution, and execute pack -> validate -> unpack -> validate
with byte equality. DataFox verification must show ADR-051 through ADR-054 resolve
with unchanged document and payload digests from exactly one pack, their four live
files are absent only after validation, the physical document count falls by three,
and the complete current Decision Capsule remains byte-compatible.

## Revisit Triggers

- Packed ADRs routinely need lifecycle mutation or selective restoration.
- Legitimate repositories exceed the reviewed entry or decoded-byte bounds.
- Exact-byte recovery cannot be completed without Git despite a valid pack.
- A future storage format provides equal auditability with simpler atomicity or
  materially better physical reduction.
- Pack-aware downgrade support becomes a product requirement.
- Evidence shows that physical document count no longer affects navigation or Agent
  effectiveness enough to justify the persisted-schema cost.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-058"]
- Amended constraints: ["ADR-058#C-001", "ADR-058#C-008", "ADR-058#C-009"]
- Design documents: ["docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
- Related ExecPlans: none yet.
- Amends ADR-058 only for lossless physical representation. ADR-058's retrieval,
  exact-context, health, and semantic-authority constraints remain in force, as
  amended separately by ADR-059 for focused capsules.

## Revision Notes

- 2026-09-03T09:25:03Z — Proposed ADR created.
