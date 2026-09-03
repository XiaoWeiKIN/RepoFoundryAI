---
schema_version: "2.8"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-095
title: "Implement lossless terminal ADR history packs"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "Approved DD-012 revision 3, accepted ADR-060, existing ADR lifecycle semantics, and the measured DataFox corpus fully determine the implementation route; no unresolved evidence question can change the design."
adr_refs: ["ADR-014", "ADR-016", "ADR-058", "ADR-059", "ADR-060"]
adr_constraint_refs: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008", "ADR-058#C-001", "ADR-058#C-002", "ADR-058#C-003", "ADR-058#C-004", "ADR-058#C-005", "ADR-058#C-006", "ADR-058#C-007", "ADR-058#C-008", "ADR-058#C-009", "ADR-059#C-001", "ADR-059#C-002", "ADR-059#C-003", "ADR-059#C-004", "ADR-059#C-005", "ADR-059#C-006", "ADR-059#C-007", "ADR-059#C-008", "ADR-059#C-009", "ADR-059#C-010", "ADR-060#C-001", "ADR-060#C-002", "ADR-060#C-003", "ADR-060#C-004", "ADR-060#C-005", "ADR-060#C-006", "ADR-060#C-007", "ADR-060#C-008", "ADR-060#C-009"]
adr_evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb", "ADR-058@sha256:7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b", "ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc", "ADR-060@sha256:773f40850444b167611da324f01bbca729ac3621fcfa2ee093b1b4d1d7af8886"]
design_refs: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/dd-012_lossless-adr-context-compaction.md", "docs/design-docs/reversible-adr-effect.md"]
design_evidence: ["DD-012@rev:3@sha256:97cabcae235ebca92f1852e15cc4a3ba286510910a6f4662fdad08aa13ffaae0"]
architecture_entrypoint: "docs/design-docs/dd-012_lossless-adr-context-compaction.md"
architecture_decision_gate: satisfied
architecture_decision_gate_reason: ""
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-09-03
updated: 2026-09-03
author: "Codex"
owner: "Wangxiaowei1"
---

# Implement lossless terminal ADR history packs

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry maintainers can replace several explicitly selected terminal ADR
Markdown files with one lossless, content-addressed History Pack without changing
the logical ADR corpus. The command proves the candidate packed representation
before removing any original, validates again after materialization, and rolls back
all affected bytes on failure. A complementary command restores the exact original
paths and bytes for recovery or downgrade.

The result is observable through the CLI and filesystem: preview reports the exact
pack digest and files that would be removed; apply leaves one verified JSON pack and
fewer live ADR files; `validate`, indexes, relations, capsules, historical ExecPlan
evidence, and `adr-health` continue to resolve every logical ADR offline; unpack
returns the governed tree to its prior byte state.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 4, release and verified DataFox compaction.
- Current state: the unified resolver, strict codec, pack/unpack transactions,
  observability, documentation, 0.8.4 metadata, and rollback/regression tests are
  implemented; 77 EP tests and the canonical repository check pass.
- Next action: commit and publish 0.8.4, install the exact release, upgrade the
  DataFox Harness, then preview/apply the authorized ADR-051..ADR-054 pack.
- Open questions: none that change the approved route. Implementation probes may
  refine private function boundaries but cannot weaken the pack schema or
  transaction contract.

## Context and Orientation

`engineering-execution-plan/scripts/epctl.py` owns ADR discovery, parsing,
lifecycle, relations, current-effect projection, evidence resolution, indexes,
Decision Views, capsules, health, and repository validation. Read-only consumers
now use `AdrSource`, while live-only mutation paths fail with unpack guidance for a
packed source. Tests live in
`engineering-execution-plan/tests/test_epctl.py`; root `scripts/check.py` is the
canonical repository check.

A **live source** is a strict ADR Markdown file under `docs/adr/`. A **packed
source** is the exact decoded byte body of an entry in
`docs/.epctl/adr-packs/sha256-<digest>.json`. A **logical ADR source** carries the
same ID, original path, bytes/text, parsed metadata, document and payload digests,
plus physical kind/container, regardless of storage. Linked legacy ADRs remain
live, read-only sources in registered architecture roots and are never packable.

Packing is physical representation compaction, not semantic consolidation. It
does not reduce the logical or effective ADR count. Lifecycle commands that need to
edit a packed ADR must instruct the operator to unpack first.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/dd-012_lossless-adr-context-compaction.md` | Approved pack schema, resolver, transaction, rollback, compatibility, and rollout design | Before implementation and DataFox rollout |
| `docs/adr/adr-060_lossless-terminal-adr-history-packs.md` | Normative eligibility, fidelity, safety, recovery, and observability constraints | Before every implementation milestone |
| `docs/adr/adr-058_lossless-adr-context-compaction.md` | Existing source fidelity, Decision View, capsule, health, and consolidation contracts | Before resolver and regression changes |
| `docs/adr/adr-059_focused-adr-context-materialization.md` | Complete/focused capsule compatibility that the resolver refactor must preserve | Before capsule regression tests |
| `docs/adr/adr-016_reversible-decision-effect.md` | Immutable decision payload and current-effect lifecycle | Before lifecycle and evidence changes |
| `engineering-execution-plan/scripts/epctl.py` | Canonical implementation surface | During implementation |
| `engineering-execution-plan/tests/test_epctl.py` | Contract and fault-injection suite | During every milestone |
| `scripts/check.py` | Only release-grade repository validation entrypoint | Before commit, release, and archival |

The pack must be deterministic and Git-independent; only exact strict terminal ADRs
are eligible. Candidate validation happens before deletion. Materialized validation
happens after deletion but before commit. Any later failure restores exact source,
pack, and index bytes. Pack loading treats repository JSON as untrusted input and
fails closed on schema, digest, path, Base64, size, identity, or collision errors.

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `satisfied`.
- Architecture compliance: `applicable`.
- ADR references: ["ADR-014", "ADR-016", "ADR-058", "ADR-059", "ADR-060"].
- ADR constraint references: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008", "ADR-058#C-001", "ADR-058#C-002", "ADR-058#C-003", "ADR-058#C-004", "ADR-058#C-005", "ADR-058#C-006", "ADR-058#C-007", "ADR-058#C-008", "ADR-058#C-009", "ADR-059#C-001", "ADR-059#C-002", "ADR-059#C-003", "ADR-059#C-004", "ADR-059#C-005", "ADR-059#C-006", "ADR-059#C-007", "ADR-059#C-008", "ADR-059#C-009", "ADR-059#C-010", "ADR-060#C-001", "ADR-060#C-002", "ADR-060#C-003", "ADR-060#C-004", "ADR-060#C-005", "ADR-060#C-006", "ADR-060#C-007", "ADR-060#C-008", "ADR-060#C-009"].
- ADR evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb", "ADR-058@sha256:7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b", "ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc", "ADR-060@sha256:773f40850444b167611da324f01bbca729ac3621fcfa2ee093b1b4d1d7af8886"].
- Design document references: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/dd-012_lossless-adr-context-compaction.md", "docs/design-docs/reversible-adr-effect.md"].
- Approved Design revision evidence: ["DD-012@rev:3@sha256:97cabcae235ebca92f1852e15cc4a3ba286510910a6f4662fdad08aa13ffaae0"].
- Architecture entrypoint: `docs/design-docs/dd-012_lossless-adr-context-compaction.md`.

Research is not required because the approved design, accepted current-effect
semantics, existing digest and transaction primitives, and measured DataFox corpus
fully determine the route. The remaining work is implementation and verification,
not evidence selection.

ADR-014 keeps authority separate from author/owner metadata and preserves sealed
legacy artifacts. A History Pack is a deterministic source-storage container, not a
new human-governed decision or evidence bundle; it uses explicit `packed_by` and
reason provenance while existing ADR metadata and seals remain embedded unchanged.

ADR-016 requires every decision payload and historic relation to remain immutable,
all effect changes to remain authorized lifecycle operations, and historical
consumers to resolve superseded/retired/rejected decisions. Packing therefore cannot
mutate lifecycle or payload and lifecycle edits of packed records must fail until
unpacked.

ADR-058 and ADR-059 require exact source bytes, complete current-effect validation,
stable Decision View and capsule output, explicit focused partial context, bounded
budgets, preview-only semantic consolidation, and additive installation. The source
refactor must preserve all existing complete/focused golden outputs for repositories
without packs and make packed sources indistinguishable to read-only consumers.

ADR-060 authorizes only explicit strict terminal History Packs. It requires a
canonical self-digesting JSON container, unified offline resolution, candidate
validation before deletion, atomic rollback, exact all-or-nothing unpack, no
lifecycle or semantic authority, explicit downgrade preparation, strict path and
resource limits, and separate logical/effective/physical health counts.

DD-012 revision 3 fixes the public commands, schema, limits, two-stage validation,
rollback, and release/DataFox sequence. DD-008 and DD-010 remain explanatory legacy
design inputs. No Benchmark Scenario is needed because acceptance is exact contract,
round-trip, fault-injection, regression, and end-to-end behavior rather than a
performance threshold.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-014#C-001 | Preserve common metadata on ADR, Design, and EP Markdown; the pack is a deterministic storage container, not a new human-governed Markdown decision. | Existing metadata-contract validation plus EP/ADR validation. |
| ADR-014#C-002 | Preserve raw/generated evidence manifest rules; a History Pack stores normative ADR bytes and is not treated as a Benchmark or Research evidence bundle. | Existing Research/Benchmark manifest suites and pack-classification tests. |
| ADR-014#C-003 | Record `packed_by` only as operation provenance and never infer decision or lifecycle authority from it. | CLI authority/lifecycle audit tests. |
| ADR-014#C-004 | Verify every embedded ADR's existing metadata and sealed payload without resealing or inventing container lifecycle authority. | Metadata tamper, pack digest, and embedded ADR validation tests. |
| ADR-014#C-005 | Exclude legacy sources from packing and preserve all decided ADR bytes under their original schema. | Legacy eligibility and mixed-corpus compatibility suites. |
| ADR-014#C-006 | Keep generated indexes free of decorative authorship and link packed rows to deterministic container provenance. | Reindex golden and generated-file classification tests. |
| ADR-016#C-001 | Store and restore exact decided ADR bytes; current-effect fields and payload are never rewritten. | Document/payload digest equality and pack-unpack round-trip tests. |
| ADR-016#C-002 | Packing is not an effect transition; existing authorized transition commands remain unchanged and reject packed mutation until unpacked. | Lifecycle preview/apply regression and packed-mutation rejection tests. |
| ADR-016#C-003 | Resolve under-review and transitive currentness from the logical source model exactly as before. | Mixed live/packed currentness-chain fixtures. |
| ADR-016#C-004 | Permit retired ADR storage compaction without claiming code rollback or altering retirement. | Retired eligibility and parsed-model equality tests. |
| ADR-016#C-005 | Resolve supersession backlinks and historical consumers through packed entries. | Packed supersession-chain and archived-evidence tests. |
| ADR-016#C-006 | Keep active ExecPlan architecture-review projection unchanged when a referenced ADR is packed. | Active-plan status and archive-block regression tests. |
| ADR-016#C-007 | Preserve accepted/current-only selection for new plans and scoped amendments across the unified resolver. | New-EP and amendment-selection mixed-source tests. |
| ADR-016#C-008 | Never pack linked legacy ADRs; validate their original schemas and digests unchanged. | Legacy schema 1-1.3 and pack-eligibility tests. |
| ADR-058#C-001 | As amended by ADR-060, keep exact logical ADR sources normative while allowing explicit terminal bytes to move into a verified pack; derived outputs remain non-normative. | Source-fidelity, generated-header, and mutation-audit tests. |
| ADR-058#C-002 | Run the unchanged current-effect algorithm over logical sources rather than raw paths. | Existing graph suite repeated with mixed live/packed fixtures. |
| ADR-058#C-003 | Extract capsule text from exact decoded bytes and verify the embedded sealed payload before use. | Substring, CRLF, Unicode, document/payload digest, and legacy fallback tests. |
| ADR-058#C-004 | Leave complete/focused budget and no-truncation behavior unchanged. | Existing budget boundary and overflow diagnostics golden tests. |
| ADR-058#C-005 | Rebuild Decision Views and indexes from logical sources with the existing lock/rollback/idempotency rules. | View preview/apply/reindex/drift tests with packed inputs. |
| ADR-058#C-006 | Feed capsules from the logical source model while preserving their ephemeral architecture-aid contract. | Complete/focused CLI schema and golden capsule regression tests. |
| ADR-058#C-007 | Extend health with physical storage dimensions without changing existing dimensions or triggering mutation. | Metric schema, count fixture, and mutation-free command tests. |
| ADR-058#C-008 | As amended by ADR-060, keep consolidation preview-only; only the explicit History Pack command may remove verified terminal physical files. | Consolidation tree-digest equality and pack command isolation tests. |
| ADR-058#C-009 | As amended by ADR-060, keep installation additive and require explicit unpack before a pack-unaware downgrade. | Installer, upgrade, zero-auto-pack, old-version failure, and downgrade tests. |
| ADR-059#C-001 | Validate the identical complete closure before any focused materialization, using logical sources. | Complete/focused validated-manifest parity with packed source fixtures. |
| ADR-059#C-002 | Preserve byte-for-byte complete-mode behavior for repositories without packs. | Existing 0.8.0/0.8.3 golden outputs. |
| ADR-059#C-003 | Preserve explicit constraints/reason and no overflow fallback for focused mode. | CLI argument and overflow-no-fallback regressions. |
| ADR-059#C-004 | Preserve directional row-to-amender selection independent of physical source kind. | Branching amendment fixtures with a packed historical target. |
| ADR-059#C-005 | Report decoded logical source digests and deterministic closure digest without container-byte leakage. | Exact substring and canonical closure digest tests. |
| ADR-059#C-006 | Preserve validated/materialized/omitted boundaries and hydration guidance. | Human/JSON focused golden tests. |
| ADR-059#C-007 | Preserve fail-closed legacy and unscoped amendment behavior. | Existing ambiguity fixtures plus mixed-source variants. |
| ADR-059#C-008 | Preserve no-summary, no-truncation, fixed-mode budget behavior. | Focused boundary and repository-mutation audit tests. |
| ADR-059#C-009 | Keep focused capsules non-authoritative and mutation-free. | Warning contract, lifecycle audit, and source-byte equality tests. |
| ADR-059#C-010 | Keep focused output ephemeral and unchanged across the 0.8.4 additive tool upgrade. | Install/upgrade and complete/focused downgrade regression tests. |
| ADR-060#C-001 | Implement explicit-ID pack preview/apply with terminal strict live-source eligibility and whole-operation rejection. | Full eligibility matrix and preview side-effect tests. |
| ADR-060#C-002 | Implement canonical single-file JSON, exact Base64 bytes, original path, metadata/digests, provenance, ordering, and self-addressed filename. | Golden serialization, independent digest, ordering, and exact-byte tests. |
| ADR-060#C-003 | Replace Path-only read consumers with a live/legacy/packed logical source model and fail on every collision or drift. | Mixed-corpus validation, relations, evidence, index, and no-Git tests. |
| ADR-060#C-004 | Validate the in-memory candidate before deletion, materialize under lock, validate again, and restore exact snapshots on any later failure. | Deletion-order, race, fault-injection, rollback, and idempotency tests. |
| ADR-060#C-005 | Implement all-or-nothing unpack preview/apply with conflict rejection, exact restore, validation, and delayed pack removal. | Unpack conflict, round-trip, failure, and rollback tests. |
| ADR-060#C-006 | Keep payload/current effect immutable and require unpack before any lifecycle edit of a packed ADR. | Parsed-model equality and lifecycle/consolidation command audits. |
| ADR-060#C-007 | Ship 0.8.4 without automatic packing and document/test unpack-before-downgrade. | Release installer, Harness upgrade, compatibility, and DataFox tests. |
| ADR-060#C-008 | Enforce strict JSON/Base64/path/symlink/case rules and 256-entry, 16 MiB-entry, 64 MiB-pack limits under repository locking. | Malformed input, traversal, collision, resource, and injection tests. |
| ADR-060#C-009 | Report logical, effective, live-file, pack, packed-entry, and net-reduction measures separately. | Human/JSON health and pack/unpack delta fixtures. |

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

First introduce a logical ADR source record and a strict History Pack codec in
`epctl.py`. Convert read-only discovery, parsing, relation/evidence resolution,
current-effect projection, indexes, views, capsules, health, status, and validation
to consume logical sources. Keep mutation functions path-based and make them reject
packed sources with an unpack instruction.

Next add preview-first pack and unpack commands. Packing builds and validates a
candidate overlay before source deletion, then snapshots and materializes the exact
target set under the repository lock, reindexes, validates, and rolls back on any
failure. Unpacking performs the inverse transaction without overwriting an existing
destination. Add deterministic JSON result contracts and human output.

Then extend tests and documentation, update all distributed core/adapter Skill
copies and release metadata to 0.8.4, and run the canonical check plus clean-install
smokes. Finally publish/install 0.8.4, preview and apply the DataFox Harness upgrade,
validate the unchanged DataFox logical corpus, and only then preview/apply the
explicit ADR-051 through ADR-054 pack. Capture logical digest equality, one-pack
presence, original-file absence, and net physical reduction as integration evidence.

## Milestones

### Milestone 1: Unified logical sources and strict pack codec

`epctl.py` can load a mixed live/legacy/packed corpus into one deterministic logical
model, independently verify canonical pack JSON and every embedded source, and fail
closed on collision, drift, unsafe paths, or resource overflow. All existing
read-only consumers pass unchanged golden tests for repositories without packs.

Run the Engineering Execution Plan unit suite; expect existing tests plus new pack
parse/discovery tests to pass with no changed complete/focused golden output.

### Milestone 2: Atomic pack and unpack commands

`pack-historical-adrs` and `unpack-adr-history-pack` expose pure previews and locked
all-or-nothing apply. Tests prove candidate validation precedes deletion, injected
failures restore byte-identical snapshots, conflicts never overwrite files, and a
pack/unpack round trip returns governed and generated targets to prior bytes.

Run targeted CLI integration and fault-injection tests; expect zero errors and no
filesystem diff after every failed transaction or completed round trip.

### Milestone 3: Complete consumer, distribution, and compatibility coverage

Validation, relations, evidence, indexes, views, capsules, health, and lifecycle
diagnostics work for mixed corpora. Documentation and every distributed RepoFoundry
Skill copy describe History Packs and the unpack-before-downgrade boundary. Version
and release metadata identify 0.8.4; canonical checks and clean-install/Harness
upgrade fixtures pass.

Run `python3 -B scripts/check.py`; expect exit 0 and deterministic reindex with no
unexplained diff.

### Milestone 4: Release and verified DataFox compaction

Publish and install the verified 0.8.4 release, preview/apply the DataFox Harness
upgrade, and validate before changing ADR storage. After ADR-051 through ADR-054 are
confirmed terminal, preview and apply their single History Pack. Expect 51 logical
ADRs to remain resolvable, four live files to become one pack, and physical file
count to fall by three. Run DataFox canonical validation and unpack preview; any
pre-existing unrelated validation failure must be reported rather than bypassed.

## Concrete Steps

From the RepoFoundry worktree root:

1. Edit `engineering-execution-plan/scripts/epctl.py` and
   `engineering-execution-plan/tests/test_epctl.py` using the existing parser,
   canonical JSON, lock, atomic-write, snapshot, index, and validation helpers.
2. Run:

       python3 -B -m unittest discover -s engineering-execution-plan/tests -p 'test_*.py' -v

   Expect all tests to pass.
3. Update `VERSION`, root and distributed Skill/documentation assets, installer and
   upgrade fixtures required by the existing release contract. Run:

       python3 -B scripts/check.py

   Expect exit 0.
4. Use the repository's existing release workflow to publish 0.8.4, then install
   that exact release with the reviewed installer and verify `repofoundry --version`.
5. From the sibling DataFox checkout, preview before every mutation:

       repofoundry --repo . upgrade --to 0.8.4
       repofoundry --repo . upgrade --to 0.8.4 --apply
       repofoundry --repo . reindex
       repofoundry --repo . validate --harness
       python3 <installed-repo-foundry-dir>/engineering-execution-plan/scripts/epctl.py \
         --repo . pack-historical-adrs ADR-051 ADR-052 ADR-053 ADR-054 \
         --packed-by Wangxiaowei1 \
         --reason "Superseded by accepted ADR-055"

   Review the exact candidate digest and deletion set, repeat with `--apply`, then
   rerun Harness and EP validation plus DataFox's canonical repository check. Exact
   installed command spelling will be reconciled with the generated 0.8.4 CLI help
   before the integration step.

## Validation and Acceptance

- [x] From the RepoFoundry root, run the Engineering Execution Plan unittest suite;
  expect exit 0 with pack codec, mixed-source, transaction, health, and regression
  cases passing. Evidence: concise transcript or
  `docs/exec-plans/active/ep-095_implement-lossless-terminal-adr-history-packs/artifacts/epctl-tests.txt`.
- [x] Run targeted preview/apply fault injections; expect previews to create no
  paths, candidate validation to occur before deletion, and every failure/round trip
  to preserve exact before-state hashes. Evidence: `artifacts/transaction-tests.txt`.
- [x] Run `python3 -B scripts/check.py`; expect exit 0 across metadata, links, all
  Skill suites, package portability, release, and end-to-end checks. Evidence:
  `artifacts/canonical-check.txt`.
- [ ] Install the exact 0.8.4 release and run version plus clean fixture Harness
  upgrade/validation; expect no automatic pack and no customized-file overwrite.
  Evidence: `artifacts/release-install.txt`.
- [ ] In DataFox, validate the 0.8.4 Harness and logical corpus before packing;
  expect no new error relative to the unchanged pre-pack baseline. Evidence:
  `artifacts/datafox-preflight.txt`.
- [ ] Preview/apply the explicit ADR-051..ADR-054 pack; expect one self-verified pack,
  unchanged logical document/payload digests, four absent live files, net physical
  reduction 3, preserved relations/evidence/indexes/capsules, and a successful
  unpack preview. Evidence: `artifacts/datafox-pack.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Codec and resolver work is additive for repositories without packs. Re-running
validation or reindex is byte-stable. Preview creates no directory, lock, pack,
index, or source mutation. A pack apply repeats preflight under lock and may commit
only the preview-equivalent candidate; a state change aborts. Repeating an applied
request finds already-packed inputs and fails without mutation, as required by
ADR-060#C-001.

Before materialization, apply snapshots every selected source, target pack, and
generated index. Candidate-overlay failure leaves sources untouched. Any write,
delete, reindex, or materialized-validation failure restores the snapshot and
removes only newly created targets. A rollback failure is fatal and must retain its
diagnostics; it must never be reported as success.

Unpack refuses existing destinations, restores every entry, validates, and removes
the pack last. Pack then unpack must reproduce prior bytes exactly. Git can recover
operator mistakes but is not part of normal validation or the recovery contract.
Downgrade requires unpacking every pack and confirming zero packed entries first.
No release or Harness upgrade automatically packs DataFox.

## Progress

- [x] (2026-09-03T09:35:14Z) Plan created with accepted ADR and approved Design inputs.
- [x] (2026-09-03T09:48:00Z) Filled the self-contained plan, compliance matrix,
  milestones, validation, and recovery contract before implementation.
- [x] (2026-09-03T10:08:00Z) Implemented Milestone 1 logical live/legacy/packed
  sources, strict canonical pack parsing, collision/path/resource validation, and
  offline resolver integration.
- [x] (2026-09-03T10:12:00Z) Implemented Milestone 2 preview/apply pack and unpack
  transactions with candidate validation, locked preflight, exact snapshots,
  post-materialization validation, and rollback fault injection.
- [x] (2026-09-03T10:21:10Z) Completed Milestone 3 documentation, 0.8.4 metadata,
  77-test EP regression, installer/Harness fixtures, and canonical repository check.
- [ ] Complete Milestone 4 release and DataFox integration.

## Surprises & Discoveries

- The existing Design review gate requires a referenced ADR to be current before a
  revision can become review-ready. ADR-060 therefore had to be accepted before
  DD-012 revision 3 could be published; the explicit combined authorization safely
  satisfied both lifecycle boundaries.
- The root contract suite grew beyond the canonical check's legacy 300-second suite
  budget on this host even though every completed assertion passed. Raising only the
  outer suite budget to 600 seconds retained all individual command/test timeouts and
  produced a complete passing canonical run.
- DD-012 describes a provably identical repeated apply as a possible no-op, while
  accepted ADR-060#C-001 explicitly requires already-packed sources to be rejected.
  The implementation follows the normative ADR: the repeat fails closed with no
  byte change.

## Decision Log

- 2026-09-03, Codex: use one canonical JSON pack instead of manifest plus payload;
  this maximizes physical reduction and avoids a second atomicity boundary.
- 2026-09-03, Codex: exclude wall-clock time from pack identity; Git records commit
  time while identical bytes, actor, and reason remain deterministic.
- 2026-09-03, Wangxiaowei1: accept ADR-060 and approve DD-012 revision 3, authorizing
  exact terminal packing with validation-before-delete and unpack recovery.
- 2026-09-03, Codex: follow ADR-060#C-001 for repeated apply and reject an
  already-packed source without mutation instead of reporting a successful no-op.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

Pending implementation and verified release.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

Use only the Python standard library already supported by RepoFoundry: `base64`,
`hashlib`, `json`, `dataclasses`, and `pathlib`; no network or archive dependency is
allowed for normal pack resolution.

Planned internal interfaces in `epctl.py`:

- immutable logical ADR source with original path, exact bytes/text, parsed
  frontmatter, document/payload digests, physical kind, and container path;
- strict pack loader/validator returning ordered logical sources;
- unified discovery/find functions for read-only consumers and live-only find for
  mutation commands;
- deterministic candidate builder and in-memory overlay validator;
- pack/unpack preview result objects used by both human and JSON renderers; and
- snapshot-backed transaction helpers using the existing repository lock and atomic
  write primitives.

Public interfaces are the two CLI commands defined by DD-012 revision 3 plus additive
`adr-health` JSON fields. Existing command arguments and JSON fields remain backward
compatible. The persisted pack schema is version 1 and requires RepoFoundry 0.8.4 or
newer until unpacked.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-095_implement-lossless-terminal-adr-history-packs/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-09-03T09:35:14Z — Initial plan created.
- 2026-09-03T09:48:00Z — Added the approved architecture summary, exact constraint
  mapping, four implementation/release milestones, validation evidence, and atomic
  recovery behavior.
