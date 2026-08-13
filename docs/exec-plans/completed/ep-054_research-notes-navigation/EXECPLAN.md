---
schema_version: "2.7"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-054
title: "Require a notes navigation entrypoint for Engineering Research"
status: completed
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "The requested navigation invariant is already demonstrated by the repository's active R-002 corpus and the curated Datafox R-006 notes index; no additional research question is needed."
adr_refs: []
adr_constraint_refs: []
adr_evidence: []
design_refs: []
architecture_entrypoint: ""
architecture_decision_gate: not_required
architecture_decision_gate_reason: "This is a local, reversible Research tooling and document-contract refinement that introduces no new long-lived architecture choice."
architecture_compliance: not_applicable
architecture_compliance_reason: "No registered ADR or architecture document controls package-local Research notes navigation."
required_benchmark_scenarios: []
verified_revision: "workspace:notes-navigation-2026-08-07"
verification_evidence: ["python3 scripts/check.py: 35 Research, 9 Benchmark, 50 ExecPlan, 96 integration tests; all integrity checks passed", "RepoFoundry AI 0.3.2 composed package: 35 Research, 9 Benchmark, 50 ExecPlan, 101 integration tests passed", "Datafox Research validation: errors=0 warnings=0; R-001 through R-008 notes README entrypoint audit passed with unchanged README SHA-256 values"]
archive_sha256: 8d69891ec4b4e9e939ba44e98baed92ef1d9bfd60d8e9904753a97511c3e6b71
created: 2026-08-07
updated: 2026-08-07
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Require a notes navigation entrypoint for Engineering Research

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Every active Engineering Research package must have one obvious reading entrypoint at
`notes/README.md`. A new package receives the entrypoint immediately, while
`sync-research` upgrades an older active package without rewriting a hand-curated
index. Users can observe the result by opening any active package's `notes/`
directory or by inspecting its manifest: the README exists and is an `entrypoint`.
Generated indexes route readers to every note document; curated indexes receive a
non-blocking diagnostic when a document is not linked.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 2 complete — package and real-repository migration.
- Current state: the navigation contract is implemented, RepoFoundry AI 0.3.2 is
  installed locally, and all eight active Datafox packages expose the README as a
  manifest entrypoint without changing curated README bytes.
- Next action: archive EP-054 with the recorded verification evidence.

## Context and Orientation

`engineering-research/scripts/researchctl.py` creates Research packages, discovers
their document corpus, refreshes `RESEARCH_MANIFEST.json`, and validates drift.
`engineering-research/assets/` supplies deterministic templates. Today every package
has a `notes` manifest root, but the directory can contain many Markdown documents
without a human navigation page. `SYNTHESIS.md` remains the current conclusion and
handoff; `notes/README.md` is only the corpus reading map.

The README may be generated or curated. Generated pages contain a delimited inventory
that the tool can replace deterministically. A page without those delimiters is
curated: synchronization must preserve its bytes and validation must still report
every package-local note that is not reachable from it.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `engineering-research/SKILL.md` | Canonical Research workflow and user contract | Before changing command behavior |
| `engineering-research/references/research.md` | Multi-document corpus organization rules | When defining the README's responsibility |
| `engineering-research/references/manifest.md` | Active versus sealed manifest integrity contract | When defining migration and validation |
| `engineering-research/scripts/researchctl.py` | Creation, synchronization, discovery, and validation implementation | During implementation |
| `engineering-research/tests/test_researchctl.py` | Executable compatibility and behavior contract | During implementation and acceptance |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `not_required`.
- Architecture compliance: `not_applicable`.
- ADR references: [].
- ADR constraint references: [].
- ADR evidence: [].
- Design document references: [].
- Architecture entrypoint: ``.

No further Research is required because the requested behavior is concrete and the
curated Datafox R-006 index demonstrates the information architecture. No ADR is
required because this is a reversible tool/document convention, not a durable system
architecture decision. No existing architecture input governs this package-local
navigation detail.

Implementation constraints are: new current-schema manifests acquire the invariant;
active schema 1 packages remain valid until explicit synchronization opts them into
the navigation convention without changing schema; sealed packages remain
byte-stable; synchronization never overwrites a curated README; generated inventory
output is deterministic; and README membership is recorded as a manifest entrypoint
rather than a generic document.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| — | No architecture input applies to this EP. | — |

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

Add a `notes-readme.md` asset with a small reading map and a tool-owned inventory
region. Extend manifest refresh so it creates a missing README, appends the canonical
package entrypoint, and refreshes only that region when present. Extend active
manifest validation so the README, entrypoint role, and well-formed markers are hard
requirements. Generated inventory coverage is also a hard requirement because the
tool owns it; incomplete curated coverage is a warning so `new-topic` does not become
impossible without rewriting user prose. Preserve sealed and legacy-package behavior.
Update the skill/reference documentation, migrate this
repository's active R-002 package, then compose and install a local RepoFoundry
release and synchronize Datafox's active Research packages.

## Milestones

### Milestone 1: Make notes navigation a deterministic active-package invariant

New Research packages contain `notes/README.md` from creation. Synchronizing an older
active package backfills the page and manifest entrypoint. Generated pages gain links
as note files are added; curated pages remain byte-identical. Validation reports a
specific error when the entrypoint or generated coverage is missing, and a warning
when a curated page omits a note. Unit tests prove all paths, including linked corpora
and legacy compatibility.

### Milestone 2: Migrate real repositories and verify the packaged workflow

This repository's R-002 and Datafox's active Research packages satisfy the invariant.
A newly composed local release contains the updated skill, and both the component
test suite and repository-wide checker pass.

## Concrete Steps

From `/Users/wangxiaowei1/x-otel/EngineeringPlan`:

1. Edit the Research asset, controller, tests, skill, and references with focused
   patches.
2. Run `python3 -B -m unittest discover -s engineering-research/tests -p 'test_*.py'`;
   expect all Research tests to pass.
3. Run `python3 engineering-research/scripts/researchctl.py --repo . sync-research R-002`
   and validate the repository.
4. Run the skill validator and `python3 scripts/check.py`; expect zero errors.
5. Compose/install the next local release using the repository's documented release
   commands, then run the installed `researchctl.py` against Datafox R-001 through
   R-008 and validate its Harness.

## Validation and Acceptance

- [x] From the repository root, run the Engineering Research unit suite; expect all
  tests to pass, including creation, backfill, curated preservation, navigation
  coverage, linked corpus, and legacy compatibility cases. Evidence: 35 tests passed
  in both the source tree and composed 0.3.2 package.
- [x] Run the skill package validator for `engineering-research`; expect a valid
  skill. Evidence: `Skill is valid!`.
- [x] Run `python3 scripts/check.py`; expect zero errors. Evidence: the source tree
  passed 35 Research, 9 Benchmark, 50 ExecPlan, and 96 RepoFoundry/installer/Spec
  tests plus all repository integrity checks. The composed 0.3.2 package independently
  passed the corresponding 35, 9, 50, and 101-test suites.
- [x] Validate EngineeringPlan R-002 and all active Datafox Research packages; expect
  every `notes/README.md` to be a manifest entrypoint and no curated README content to
  change. Evidence: both Research validators returned zero errors and zero warnings;
  the Datafox R-001 through R-008 audit returned `readme=True entrypoint=True
  role=True`, and all eight pre/post README SHA-256 values matched.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Creation remains atomic at package granularity: a failure removes the incomplete new
package. Synchronization is idempotent because it adds the canonical entrypoint once
and emits a stable sorted inventory. A README without tool markers is never rewritten;
an incomplete marker pair fails closed. Existing sealed manifests and files are not
refreshed or migrated. If release composition fails, the source tree and currently
installed immutable release remain usable; retry composition after fixing the source.

## Progress

- [x] (2026-08-07T07:44:23Z) Plan created with explicit no-Research and no-ADR gates.
- [x] (2026-08-07T07:50:00Z) Audited EngineeringPlan R-002 and Datafox R-001 through
  R-008; all Datafox packages already have curated READMEs, while R-008 lacks the
  manifest entrypoint and EngineeringPlan R-002 lacks the README entirely.
- [x] (2026-08-07T08:10:00Z) Implemented the controller, asset, validation, 35-test
  regression suite, package documentation, executable cache-topology example, and
  EngineeringPlan R-002 migration.
- [x] (2026-08-07T08:25:00Z) Composed RepoFoundry AI 0.3.2 on the installed 0.3.1
  baseline, passed its complete checker, and activated immutable release
  `0.3.2-471da08b5cad` without changing project Harnesses or host registrations.
- [x] (2026-08-07T08:30:00Z) Explicitly synchronized legacy-schema Datafox R-008,
  audited all eight active packages, preserved every curated README digest, and
  validated Research with zero errors and warnings.
- [x] (2026-08-07T08:40:00Z) Final source-tree checker passed all component,
  repository validation, index projection, and whitespace checks with zero errors;
  only the pre-existing EP-006 and EP-013 archive-readiness warnings remain.

## Surprises & Discoveries

- The allocator selected EP-054 because `docs/.epctl/state.json` already records EP
  high-water 53 even though only a smaller visible subset is present in this worktree.
- Existing Datafox navigation pages are curated and materially richer than a generated
  filename list, so marker absence must mean "preserve", not "replace".
- Datafox R-008 still uses manifest schema 1. The first implementation correctly kept
  legacy validation compatible but also skipped explicit synchronization. Separating
  passive validation from explicit migration lets `sync-research` add the entrypoint
  without relabeling the manifest or weakening sealed compatibility.

## Decision Log

- 2026-08-07 — Require the invariant during validation only for active schema 1.1
  manifests. Sealed historical packages remain immutable and schema 1 packages stay
  validation-compatible; an explicit sync may add the navigation entrypoint without
  relabeling their schema.
- 2026-08-07 — Treat `notes/README.md` as navigation, not synthesis. It must link all
  package-local note documents, but normative conclusions remain in `SYNTHESIS.md`.
- 2026-08-07 — Tool markers authorize deterministic inventory replacement. Their
  absence identifies a curated page whose bytes synchronization must preserve.
- 2026-08-07 — Missing links are errors for a tool-managed inventory and warnings for
  a curated README. This preserves a hard generated contract without making
  `new-topic` rewrite or reject an otherwise valid human information architecture.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

Engineering Research now creates a useful reading entrypoint before the first note,
keeps its generated inventory deterministic as the corpus grows, and respects richer
human information architecture. Explicit synchronization is the migration boundary:
it can opt an active schema 1 package into the convention, while validation alone and
all sealed packages remain non-mutating. The real Datafox corpus confirmed the design:
seven packages already met the contract, R-008 needed only manifest registration, and
none of the eight curated navigation documents changed.

### Knowledge promotion candidates

- The generated-versus-curated marker ownership pattern is reusable for other
  RepoFoundry indexes that need deterministic defaults without taking ownership of
  human structure.

## Interfaces and Dependencies

No new runtime dependency is allowed. The implementation uses Python's standard
library and the existing `researchctl.py` Markdown-link parser, manifest locator
model, atomic writer, and SHA-256 discovery. Public command names and arguments stay
unchanged; only `new-research`, `sync-research`, and `validate` behavior is refined.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-054_research-notes-navigation/EXECPLAN.md`
- Navigation asset: `engineering-research/assets/notes-readme.md`
- Controller: `engineering-research/scripts/researchctl.py`
- Tests: `engineering-research/tests/test_researchctl.py`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-07T07:44:23Z — Initial plan created.
- 2026-08-07T07:50:00Z — Filled execution, compatibility, validation, and migration
  contract after auditing real active Research packages.
