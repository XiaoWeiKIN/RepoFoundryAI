---
schema_version: "2.2"
id: EP-002
title: "Split engineering research from execution planning"
status: completed
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001"]
architecture_gate: satisfied
architecture_gate_reason: ""
created: 2026-07-28
updated: 2026-07-28
owner: "XiaoWeiKIN"
---

# Split engineering research from execution planning

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

ExecutionPlan will distribute two independently installable, Agent-independent
skills. `engineering-research` will let a user register an existing directory
such as `index.md + many topic documents`, keep a deterministic manifest,
detect broken references and drift, and conclude it into a sealed,
self-contained Research package. `execution-plan` will consume the resulting
sealed Synthesis and manifest without depending on the producer's installation
path, then govern ADR and implementation planning.

The result is observable when a disposable multi-document corpus can be
registered with `researchctl`, validated, snapshotted on conclusion, and used
by `epctl new-adr` and `epctl new-ep`; both skill directories must pass
standalone skill validation.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 5 complete — final archive and handoff.
- Current state: both independent Skill roots, the manifest producer-consumer
  contract, compatibility validation, public documentation, installed copies,
  45 source tests, 45 installed-copy tests, and the real-corpus forward test
  are complete.
- Next action: no implementation action remains; repository commit and push are
  the final handoff operation.
- Open questions: none that change the accepted architecture. Large binary
  corpus storage remains outside the first document-manifest version.

## Context and Orientation

The repository root is currently the installable `execution-plan` skill:

- `SKILL.md` contains Research through ExecPlan instructions.
- `scripts/epctl.py` is a standard-library CLI for all lifecycle operations.
- `assets/` contains Research, ADR, ExecPlan, Task, Checkpoint, and Bugfix
  templates.
- `references/` contains the detailed workflow contracts.
- `tests/test_epctl.py` is the regression suite.

To preserve existing clones and installed paths, the root stays the
`execution-plan` skill during this compatibility release. A second independent
skill will live at `engineering-research/`; registering that directory must
not require registering the root skill.

Terms:

- **Research control package:** canonical
  `docs/research/{active|completed}/r-NNN_slug/` containing lifecycle metadata,
  Synthesis, notes, artifacts, and the corpus manifest.
- **Managed corpus:** documents already stored inside the control package.
- **Linked corpus:** documents stored elsewhere inside the target repository
  and registered non-destructively while Research is active.
- **Conclusion snapshot:** repository-contained copy of declared linked
  documents stored under the completed Research package.
- **Producer-consumer contract:** file format emitted by `researchctl` and
  validated by `epctl`; no runtime skill-to-skill call is allowed.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/research/completed/r-001_multi-document-research/SYNTHESIS.md` | Sealed evidence and recommended corpus model | Before changing the manifest design |
| `docs/adr/adr-001_split-engineering-research.md` | Accepted ownership, compatibility, and dependency boundary | Before changing package layout or command ownership |
| `SKILL.md` | Current root skill triggers and orchestration | Before editing the execution-plan surface |
| `scripts/epctl.py` | Current artifact parsing and Research consumer behavior | Before implementing compatibility validation |
| `references/research.md` | Existing v1 Research semantics | Before writing the v2 producer contract |
| `tests/test_epctl.py` | Backward-compatibility evidence | Before and after implementation |
| `README.md` | Public, Agent-independent installation contract | Before handoff |

Constraints:

- Use Python 3.10+ standard library only.
- Keep both skill packages self-contained; shared behavior is a file contract,
  not a relative import across skill directories.
- Keep old Research packages without a manifest valid.
- Reject path traversal and symlink escapes.
- Accept absolute CLI input only when it resolves inside the target repository,
  then persist a repository-relative path.
- Snapshot declared research documents, not arbitrary binary artifact trees.
- Preserve the bounded, sealed `SYNTHESIS.md` interface.
- Keep ADR acceptance under explicit human authority.
- Do not bind installation instructions to Codex or another Agent directory.

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001"].

R-001 establishes with high confidence that a Research is an identity and
lifecycle around a document set. The supplied real corpus has 11 Markdown
documents, 4,868 lines, one natural `index.md` entrypoint, inter-document
dependencies, one missing repository reference, and non-portable absolute
source paths. The current tool creates `notes/` but neither inventories nor
seals their contents. One Synthesis must remain the small downstream interface.

ADR-001 accepts an independent producer-consumer split:

- `engineering-research` owns Research creation, corpus registration,
  manifest refresh, evidence/link diagnostics, Synthesis, snapshot, and
  conclusion.
- `execution-plan` owns ADR, ExecPlan, Task, Checkpoint, Bugfix, and technical
  debt, and validates Research only as a consumer.
- The repository temporarily retains legacy Research commands in `epctl` for
  compatibility; primary instructions route new Research to the companion.
- Both skills are independently installable. The contract is versioned files,
  never a hardcoded skill path.

Negative consequences that enter implementation and acceptance are the
temporary command overlap, duplicated schema-reading logic, two registration
targets, and the need for producer-consumer contract tests. A future
content-addressed or Git-pinned binary corpus design is intentionally deferred
and does not change the Markdown-first route.

## Plan of Work

First add `engineering-research/` as a complete skill package. Its compact
`SKILL.md` will route detailed behavior to `references/research.md`; assets
will create the controller, Synthesis, root index, and JSON manifest.

Implement `engineering-research/scripts/researchctl.py` as a deterministic
standard-library CLI. Reuse the established repository artifact shape but own
only Research commands. Support managed Research by default and linked corpus
roots through `new-research --corpus-root ... --entrypoint ...`. Persist only
normalized repository-relative paths. `sync-research` discovers declared
Markdown documents, records sizes and SHA-256 values, identifies entrypoints,
checks Markdown links and `inputDocuments` references, and reports manifest
drift.

At conclusion, refresh and validate the active corpus. Managed documents stay
in place. Linked documents are copied transactionally under
`artifacts/research-snapshot/`, the manifest is rewritten to the snapshot,
per-file digests and the canonical manifest payload are sealed, Synthesis is
sealed, and the complete control package moves to `completed/`. Cancellation
retains the control record without pretending to satisfy the Research Gate.

Then narrow the root `execution-plan` instructions to the consumer and
governance role. Extend `epctl` validation so a manifest-bearing concluded
Research must have a sealed, untampered manifest; continue accepting legacy
packages with no manifest. Add a cross-contract test in which `researchctl`
creates and concludes a Research and `epctl` consumes it for an ADR.

Finally update README, examples, UI metadata, and installation synchronization.
Forward-test on a disposable copy of the supplied corpus: initial validation
must identify the missing `07-api-contract.md`; after correcting only the
fixture reference, conclusion and `epctl` consumption must succeed.

## Milestones

### Milestone 1: Independent Research skill foundation

`engineering-research/` exists as a valid standalone skill with concise
instructions, references, assets, UI metadata, a CLI entrypoint, and isolated
tests. Running its `init` and `new-research` commands in an empty temporary
repository produces a valid managed control package and root index.

### Milestone 2: Multi-document corpus lifecycle

`researchctl` registers one or more existing repository directories, maintains
an explicit manifest, checks local document dependencies and portability,
detects membership drift, snapshots linked documents on conclusion, and
detects snapshot or manifest tampering. Unit tests cover managed, linked,
multi-root, traversal, symlink, broken-link, drift, archive, and cancellation
behavior.

### Milestone 3: Producer-consumer compatibility

The root skill's primary instructions no longer teach evidence acquisition.
`epctl` accepts legacy Research and validates new sealed manifests. A Research
created by `researchctl` can satisfy `new-adr` and `new-ep` gates without either
CLI importing or locating the other.

### Milestone 4: Public documentation and installation

README describes the two independent registration targets and the complete
Research-to-ADR-to-ExecPlan flow without an Agent-specific directory. Both UI
metadata files match their skills. The source and installed copies validate.

### Milestone 5: Full regression and real-corpus forward test

All existing `epctl` tests, new `researchctl` tests, contract tests, skill
validation, repository validation, and a disposable DataFox corpus test pass.
The real-corpus test first proves that the known missing dependency is detected
and then proves successful sync/conclusion after fixture-only correction.

## Concrete Steps

All commands run from `/Users/wangxiaowei1/x-otel/ExecutionPlan`.

Create and exercise the companion:

```bash
python3 -B engineering-research/scripts/researchctl.py --repo /tmp/research-fixture init
python3 -B engineering-research/scripts/researchctl.py --repo /tmp/research-fixture \
  new-research --slug example --title "Example research"
python3 -B engineering-research/scripts/researchctl.py --repo /tmp/research-fixture validate
```

Run isolated and compatibility tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s engineering-research/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s tests -p 'test_*.py' -v
```

Validate both skill packages and repository artifacts:

```bash
python3 -B /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 -B /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py engineering-research
python3 -B scripts/epctl.py --repo . validate
git diff --check
```

Synchronize installable payloads only after all source checks pass:

```bash
rsync -a --delete <reviewed-root-skill-files> \
  /Users/wangxiaowei1/.codex/skills/execution-plan/
rsync -a --delete engineering-research/ \
  /Users/wangxiaowei1/.codex/skills/engineering-research/
```

The actual synchronization command must enumerate the reviewed root skill
files instead of deleting unrelated repository documentation.

## Validation and Acceptance

- [x] From the repository root, validate `.` and
  `engineering-research/` with `quick_validate.py`; expect `Skill is valid!`
  twice. Evidence: terminal summary.
- [x] Run both unittest discovery commands; expect zero failures and zero
  errors. Evidence: terminal summary and
  `docs/exec-plans/completed/ep-002_split-engineering-research/artifacts/`.
- [x] Register a temporary `index.md + topic documents` corpus; expect the
  manifest to contain all declared Markdown documents and the entrypoint.
- [x] Add an untracked document after sync; expect `validate` to report
  manifest drift until `sync-research` is rerun.
- [x] Include a missing Markdown or `inputDocuments` reference; expect
  validation to identify the source file and missing target.
- [x] Attempt an outside-repository root and a symlinked document; expect both
  to be rejected without writes outside the target repository.
- [x] Conclude a linked Research; expect source documents unchanged, snapshot
  files under the completed package, sealed Synthesis, and sealed manifest.
- [x] Modify a concluded snapshot or manifest; expect validation to report a
  digest mismatch.
- [x] Use `epctl new-adr --research R-NNN` on a `researchctl`-produced
  concluded package; expect success without cross-skill imports.
- [x] Run all existing `epctl` tests; expect legacy Research packages and
  commands to remain compatible.
- [x] Search README and active skill instructions for `~/.codex/skills`;
  expect no installation contract tied to an Agent-owned directory.
- [x] Run `python3 -B scripts/epctl.py --repo . validate`; expect
  `{"errors": 0, "warnings": 0}` before archive.

## Idempotence and Recovery

`init`, manifest refresh, index rebuild, validation, and installation sync must
be idempotent. ID allocation keeps a high-water mark and never reuses an ID.

`new-research` writes the control package and index under a repository lock;
on failure it restores the index and removes only files it created.
`sync-research` builds the next manifest in memory and replaces it atomically.
It never edits linked source documents.

Linked conclusion copies into a temporary snapshot directory first. It must
validate the complete candidate package before moving the Research directory.
On any error, delete only the temporary snapshot, restore original controller,
Synthesis, manifest, and indexes, and leave source documents untouched.

Existing packages without `RESEARCH_MANIFEST.json` follow the legacy consumer
path. No bulk migration is performed. If the companion installation fails,
remove only its new installed directory; the root execution-plan installation
continues to work.

Never use recursive deletion against a repository root, home directory, or
unresolved variable. Test cleanup uses `tempfile.TemporaryDirectory`.

## Progress

- [x] (2026-07-28T08:42:48Z) Plan created with satisfied Research and
  Architecture Gates.
- [x] (2026-07-28T08:48:00Z) R-001 sealed and ADR-001 accepted after explicit
  user confirmation of the dual-skill boundary.
- [x] (2026-07-28T09:02:00Z) Filled the self-contained implementation,
  validation, compatibility, and recovery plan.
- [x] (2026-07-28T09:13:19Z) Implemented Milestone 1: standalone companion
  Skill, assets, references, UI metadata, CLI, and managed workflow.
- [x] (2026-07-28T09:13:19Z) Implemented Milestone 2: multi-root linked corpus,
  manifest drift and reference diagnostics, snapshot sealing, and tamper
  detection.
- [x] (2026-07-28T09:13:19Z) Implemented Milestone 3: legacy compatibility and
  sealed producer-consumer Gate checks through both ADR and ExecPlan creation.
- [x] (2026-07-28T09:13:19Z) Implemented Milestone 4: Agent-independent README,
  two registration roots, generated UI metadata, and validated installed
  copies.
- [x] (2026-07-28T09:13:19Z) Completed Milestone 5: 45 source tests, 45
  installed-copy tests, two source and two installed Skill validations, clean
  repository validators, and the disposable spans-aggregate forward test.

## Surprises & Discoveries

- The supplied corpus contains one stale `07-api-contract.md` input reference
  and several valid-but-non-portable absolute source paths; the new diagnostics
  distinguish the missing dependency from portability warnings.
- A sealed document symlinked to equal content inside the repository could
  preserve its digest while breaking package ownership. Producer and consumer
  now reject symlinks using the unresolved path before reading bytes.
- Cross-contract tests initially assumed the nested source distribution.
  Test-only discovery now supports both source layout and two sibling installed
  Skill roots, while runtime code remains uncoupled.

## Decision Log

- 2026-07-28 — Keep the repository root as the execution-plan skill for this
  compatibility release and add `engineering-research/` as the second
  self-contained skill. This preserves existing clone and installation paths
  while enforcing the accepted runtime boundary. Author: Codex; constrained by
  ADR-001.
- 2026-07-28 — Keep legacy Research commands in `epctl` temporarily but remove
  them from the primary execution-plan workflow. Compatibility is safer than
  deleting a working surface in the same release. Author: Codex.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The repository now distributes two independently registered Skills with a
one-way, versioned file boundary. Engineering Research can manage new notes or
adopt one or more existing document roots, preserve entrypoints, diagnose
reference and membership drift, snapshot linked content, and seal the manifest
and Synthesis. Execution Plan consumes that output without importing or locating
the producer and continues to accept legacy Research packages.

The compatibility choice avoided breaking existing `execution-plan`
installations but temporarily leaves Research commands in `epctl`. Public
instructions consistently route new Research to the companion, making later
removal a separately versioned migration. The Markdown-first manifest is
deliberately bounded; large binary evidence still belongs in artifacts or a
future content-addressed extension.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No third-party runtime libraries or services are allowed.

The producer CLI must expose:

```text
researchctl.py --repo PATH init
researchctl.py --repo PATH new-research --slug SLUG --title TITLE
    [--corpus-root PATH ...] [--entrypoint PATH ...]
researchctl.py --repo PATH sync-research R-NNN
researchctl.py --repo PATH validate
researchctl.py --repo PATH status
researchctl.py --repo PATH archive-research R-NNN
    --outcome concluded|cancelled [--reason TEXT]
```

`RESEARCH_MANIFEST.json` must contain a schema version, parent Research ID,
lifecycle status, mode, declared roots and entrypoints, document inventory,
per-document bytes and SHA-256, and a sealed payload digest. Active linked
paths are repository-relative. Concluded linked documents resolve to
package-relative snapshot paths.

`SYNTHESIS.md` retains the existing schema-1 fields and body hash contract so
`epctl` can consume it. The Research controller retains `id`, `status`,
`synthesis`, and the existing required sections, adding only an optional
`manifest` field. This makes the new contract a compatible extension.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-002_split-engineering-research/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.
- Research: `docs/research/completed/r-001_multi-document-research/`
- Decision: `docs/adr/adr-001_split-engineering-research.md`
- Validation evidence:
  `docs/exec-plans/completed/ep-002_split-engineering-research/artifacts/validation-summary.md`

## Revision Notes

- 2026-07-28T08:42:48Z — Initial plan created.
- 2026-07-28T09:02:00Z — Replaced all placeholders with the accepted
  dual-skill architecture, compatibility strategy, milestones, commands,
  acceptance evidence, and recovery behavior.
- 2026-07-28T09:13:19Z — Completed both Skill packages, compatibility and
  security checks, documentation, installed-copy validation, regression tests,
  and the real-corpus forward test.
- 2026-07-28T09:16:07Z — Archived EP-002 after all acceptance checks passed.
