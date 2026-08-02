---
schema_version: "2.5"
id: EP-007
title: "Pin Engineering Specification releases"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "The user selected the fixed-version tag model after reviewing OpenTelemetry's documented release/versioning practice, and the current resolver and lock behavior are directly inspectable."
adr_refs: []
design_refs: []
architecture_entrypoint: ""
architecture_gate: not_required
architecture_gate_reason: "Accepted ADR-005 already assigns external Git specification resolution and immutable locking to RepoFoundry; this change refines that source contract from an implicit moving branch to an explicit release tag without changing repository ownership or Catalog schema."
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-02
updated: 2026-08-02
owner: "Codex"
---

# Pin Engineering Specification releases

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Make every production Engineering Specification download name a fixed Catalog
version instead of implicitly following `main`. A repository maintainer can
initialize with the documented default release or pass `--spec-version
MAJOR.MINOR.PATCH`; RepoFoundry resolves `refs/tags/vMAJOR.MINOR.PATCH`, proves
the tag's `catalog_version`, and locks the full commit and content digests.
`spec sync` then repairs local files from that immutable commit, while an
explicit, previewed `spec update --spec-version ...` performs an upgrade.

The capability is observable when a generated `specs.json` names a versioned
tag, `specs.lock.json` records the corresponding full commit, a moved remote
branch cannot change `sync`, and a tag/Catalog-version mismatch fails before
any target-repository write.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — exact-revision verification and archival.
- Current state: EngineeringSpecifications release contract is committed at
  `72dbd5f`, immutable remote tag `v1.2.0` resolves to validated Catalog commit
  `49232cd57e9cdd77cbaf79365a555d8cf341dfbd`, RepoFoundry fixed-version
  behavior is implemented, 42 focused/contract tests pass, the full canonical
  check passes, and the public dry-run resolves the expected tag without
  target writes.
- Next action: commit RepoFoundry, verify both exact commits in clean detached
  worktrees, archive EP-007, and create review pull requests.
- Open questions: none that change the selected route.

## Context and Orientation

EngineeringSpecifications is the independent normative-content repository at
`/Users/wangxiaowei1/xiaowei/EngineeringSpecifications`. Its `catalog.json`
declares one Catalog SemVer plus independently versioned Spec entries. ESP-0008
defines an immutable `vX.Y.Z` release tag whose version must equal
`catalog_version`.

RepoFoundry is this repository. `scripts/foundryctl.py` owns CLI defaults and
source options. `scripts/spec_manager.py` parses manifest/lock/Catalog boundary
data, fetches Git objects without checkout, resolves selection, renders local
copies, and validates offline state. `docs/.engineering/specs.json` is
repository-owned policy; `specs.lock.json` is generated immutable resolution.

Today `_prepare_manifest` resolves the configured manifest ref and treats
`sync` specially when a lock exists. This change retains that state machine,
adds a release-version source constructor and version/tag integrity check, and
allows only explicit `update` to replace an existing manifest source.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-005_external-engineering-specifications.md` | Owns the external Git source, immutable lock, pinned sync, explicit update, and offline validation boundary | Before changing resolver ownership or lock behavior |
| `docs/design-docs/engineering-spec-management.md` | Current manifest, lock, Git safety, CLI, and materialization contract | Before editing the CLI or resolver |
| `scripts/foundryctl.py` | Public CLI source selection and Bootstrap orchestration | During implementation |
| `scripts/spec_manager.py` | Untrusted Git/Catalog parsing and state planning | During implementation and security review |
| `tests/spec_git_fixture.py` | Isolated versioned Git source used by consumer tests | While adding release-tag scenarios |
| `tests/test_foundryctl.py` | End-to-end CLI and local-state contract | Before completion |
| `../EngineeringSpecifications/proposals/0008_versioned-catalog-releases.md` | Approved cross-repository release intent and OpenTelemetry prior art | Before changing either public contract |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture gate: `not_required`.
- ADR references: [].
- Design document references: [].
- Architecture entrypoint: ``.

Research is not required because the user selected the fixed-version model
after the OpenTelemetry primary release/versioning contract was examined, and
the complete current resolver behavior is testable in these two local
repositories. Relevant conclusions are: a human-facing SemVer needs an
immutable fetch identity; a full commit and content digests remain the
reproducibility proof; stability/maturity and release version are separate;
and production consumers must not silently advance with a branch.

A new architecture decision is not required. Accepted ADR-005 already fixes
repository ownership, Git transport, ephemeral object resolution, manifest and
lock ownership, pinned `sync`, explicit `update`, and offline validation. The
user-selected refinement changes initial source identity from `main` to an
immutable version tag without changing Catalog schema version 1 or those
boundaries. ESP-0008 records the public-contract intent in the specification
repository. If implementation requires new source kinds, multiple Catalogs,
signed-artifact trust, or a lock schema change, stop and return to architecture
decision work.

No Benchmark Scenario is required: acceptance is deterministic protocol and
state-transition behavior covered by isolated Git fixtures, exact-revision
checks, and both repositories' canonical validators.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First, integrate ESP-0008 in EngineeringSpecifications by adding a release
guide and changing the bilingual README, contribution, governance, model, and
Changelog language from optional tags/branches to immutable production tags
plus explicit development refs. Add a canonical release checker so a release
version must be SemVer, equal `catalog_version`, represented in the Changelog,
and point at the expected commit when the tag exists.

Second, update RepoFoundry CLI source selection. Add `--spec-version` as the
fixed production selector, make it mutually exclusive with `--spec-ref`, and
use Catalog `1.2.0` as the default only when creating policy for a repository
that has no manifest. Preserve `--spec-ref` for explicit development sources.
Allow an explicit version/ref override on `spec update` to rewrite the manifest
only after the dry-run; `sync` continues to obey the lock.

Third, enforce release integrity in the resolver. An exact
`refs/tags/vX.Y.Z` source must contain a Catalog whose `catalog_version` is
exactly `X.Y.Z`. Reject absent refs, malformed versions, and mismatches before
writing. Keep legacy schema-v1 manifests and locks valid.

Finally, add local tag fixtures and tests for fixed defaults, explicit
versions, tag mismatch, pinned repair, version upgrade, development refs,
offline validation, and no-write failure. Update the design doc, Skill,
bilingual READMEs, Bootstrap reference, and eval contract; run both canonical
checks on exact commits before archival.

## Milestones

### Milestone 1: Publish a mechanically verifiable Catalog release contract

EngineeringSpecifications documents `vX.Y.Z` as the only production release
identity and provides a checker that rejects a Catalog/tag mismatch. Its
canonical check remains green. Catalog `1.2.0` is validated at the exact
release commit and published as immutable tag `v1.2.0`.

### Milestone 2: Select and upgrade fixed releases through RepoFoundry

RepoFoundry initializes absent manifests with `refs/tags/v1.2.0`, accepts an
explicit `--spec-version`, rejects mismatched content, keeps `sync` pinned, and
changes versions only through explicit previewed update. Existing development
refs and schema-v1 local state remain supported.

### Milestone 3: Prove exact revisions and archive

Both repositories pass focused and canonical checks. A real public-source
preview resolves `v1.2.0` to its full tagged commit without target writes.
Implementation evidence is captured below this EP, the verified RepoFoundry
revision is recorded through archival, and both review branches are pushed.

## Concrete Steps

From `/Users/wangxiaowei1/xiaowei/EngineeringSpecifications`:

```bash
python3 -B scripts/check.py
python3 -B scripts/check_release.py 1.2.0
git rev-list -n 1 v1.2.0
```

Expect the canonical check and release check to pass and the tag to identify a
commit whose `catalog.json` declares `1.2.0`.

From `/Users/wangxiaowei1/x-otel/EngineeringPlan`:

```bash
python3 -B -m unittest tests.test_spec_manager tests.test_foundryctl
python3 -B -m unittest tests.test_repository_contracts
python3 -B scripts/check.py
```

Expect all focused, packaging, documentation, and canonical checks to pass.
Use a temporary empty repository for the real remote dry-run:

```bash
python3 -B scripts/foundryctl.py --repo /tmp/repofoundry-version-preview spec plan
```

Expect source ref `refs/tags/v1.2.0`, Catalog version `1.2.0`, a full resolved
commit matching the release tag, and no files in the temporary repository.

## Validation and Acceptance

- [x] From EngineeringSpecifications, run `python3 -B scripts/check.py`; expect
  all Catalog, Requirement, link, schema, and unit checks to pass. Evidence:
  `artifacts/engineering-specifications-check.txt`.
- [x] From EngineeringSpecifications, run `python3 -B scripts/check_release.py
  1.2.0 --require-tag`; expect the Catalog version, Changelog release, and tag
  target contract to pass. Evidence: `artifacts/specification-release-check.txt`.
- [x] From RepoFoundry, run `python3 -B -m unittest tests.test_spec_manager
  tests.test_foundryctl tests.test_repository_contracts`; expect fixed-version, pinned
  sync, explicit update, mismatch, development-ref, and failure-safety tests to
  pass. Evidence: `artifacts/focused-version-tests.txt`.
- [x] From RepoFoundry, run `python3 -B -m unittest
  tests.test_repository_contracts`; expect package and public documentation
  contracts to pass. Evidence: `artifacts/repository-contracts.txt`.
- [x] From RepoFoundry, run `python3 -B scripts/check.py`; expect the complete
  canonical check to pass. Evidence: `artifacts/repofoundry-check.txt`.
- [x] Run a real public `spec plan` against an empty temporary repository;
  expect `refs/tags/v1.2.0`, Catalog `1.2.0`, the release commit, and zero
  target writes. Evidence: `artifacts/public-version-preview.txt`.
- [ ] Validate exact committed revisions in clean detached worktrees; expect
  both canonical checks to pass. Evidence:
  `artifacts/exact-revision-checks.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Documentation and tests are ordinary version-controlled edits. The release
checker and all RepoFoundry plans are read-only. Bootstrap and Spec commands
remain dry-run by default, replan under the repository lock before apply, and
write atomically only after complete source validation.

If Git resolution or version validation fails, no target files are written.
Retry with the same release version after restoring remote access. `sync` can
be repeated to repair managed files from the lock without upgrading. Roll back
an upgrade by running `spec update --spec-version 1.2.0`, reviewing
the plan, and applying it; do not move or delete a published release tag.

The existing `v0.1.0` tag is untouched. Tag `v1.2.0` was created only after
validating exact `origin/main` commit `49232cd`. After publication, neither tag
may be rewritten; correct any defect with a new patch release instead.

## Progress

- [x] (2026-08-02T03:31:20Z) Created EP-007 with explicit Research and
  architecture not-required rationale.
- [x] (2026-08-02T03:38:00Z) Audited both repository heads, Catalog `1.2.0`,
  the sole historical `v0.1.0` tag, moving-`main` CLI default, immutable lock,
  pinned `sync`, explicit `update`, and offline validation behavior.
- [x] (2026-08-02T03:42:00Z) Isolated new branches from each latest
  `origin/main` and approved ESP-0008 without modifying the existing Go Spec
  pull request.
- [x] (2026-08-02T05:42:00Z) Implemented and committed the
  EngineeringSpecifications release guide, release checker, bilingual version
  contract, governance integration, and tests at `72dbd5f`.
- [x] (2026-08-02T05:48:00Z) Validated exact merged Catalog `1.2.0` commit
  `49232cd57e9cdd77cbaf79365a555d8cf341dfbd`, published immutable annotated
  tag `v1.2.0`, and verified the remote peeled tag target.
- [x] (2026-08-02T05:54:00Z) Implemented canonical release refs,
  tag/Catalog-version validation, fixed default `1.2.0`, source-preserving
  version upgrades, explicit development refs, and source-change misuse gates.
- [x] (2026-08-02T06:00:00Z) Passed 42 focused/contract tests, both
  specification checks, RepoFoundry's full canonical check, EP validation, and
  a real public no-write version preview.
- [ ] Commit RepoFoundry, validate exact revisions, archive, push, and create
  pull requests.

## Surprises & Discoveries

- The Catalog has advanced through `1.0.0`, `1.1.0`, and `1.2.0` in metadata,
  but only `v0.1.0` was published as a Git tag. This proves SemVer metadata and
  release identity have evolved independently and require reconciliation.
- Existing schema-v1 locks already contain the requested source and resolved
  commit. No lock migration is needed to make released versions reproducible.
- Fetching a fully qualified annotated tag with `--no-tags` works through the
  existing one-ref bare-Git path; no checkout or extra fetch mode is needed.

## Decision Log

- (2026-08-02) Use fully qualified `refs/tags/vX.Y.Z` in generated manifests,
  validate it against `catalog_version`, and keep `--spec-ref` only as an
  explicit development escape hatch. Rationale: preserve the existing Git
  source shape while making release intent machine-detectable.
- (2026-08-02) Default new projects to Catalog `1.2.0`; do not make an open,
  unmerged Catalog `1.3.0` the consumer default. Rationale: defaults must name
  an actually published and reviewable release.
- (2026-08-02) Preserve an existing custom repository URL when
  `spec update --spec-version ...` omits `--spec-repository`; reject source
  options on `sync`, `plan`, or Bootstrap once a manifest exists. Rationale:
  version selection must not silently switch repositories or be silently
  ignored.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The implementation now provides the intended user-visible state machine:
production installation selects a semantic release, the manifest preserves its
canonical tag, the lock proves the commit and bytes, sync stays pinned, and
only an explicit previewed update changes release. Legacy explicit branch
sources remain usable for development, but are no longer the default.

The remaining work is procedural: commit the RepoFoundry tree, validate both
exact commits in detached worktrees, seal this plan, and publish pull requests.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

No new Python dependency is allowed. RepoFoundry continues to use Python 3.10+
standard library and the `git` executable. EngineeringSpecifications release
validation also uses Python standard library and read-only Git commands.

Public CLI additions:

```text
foundryctl bootstrap --spec-version MAJOR.MINOR.PATCH
foundryctl spec plan --spec-version MAJOR.MINOR.PATCH
foundryctl spec update --spec-version MAJOR.MINOR.PATCH
```

`--spec-version` and `--spec-ref` are mutually exclusive. Manifest and lock
schema version 1 remain unchanged. The release helper normalizes a version to
`refs/tags/vMAJOR.MINOR.PATCH`; the resolver rejects a release-tag/Catalog
version mismatch with a stable labeled error. `spec validate` must not invoke
Git or access the network.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-007_versioned-spec-releases/EXECPLAN.md`
- EngineeringSpecifications proposal:
  `proposals/0008_versioned-catalog-releases.md` in the specification
  repository.
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-02T03:31:20Z — Initial plan created.
- 2026-08-02T03:45:00Z — Filled purpose, current facts, inputs, milestones,
  concrete commands, validation, recovery, progress, decisions, interfaces,
  and evidence paths before implementation.
- 2026-08-02T06:03:00Z — Recorded the implemented contracts, release tag,
  focused and canonical validation, public preview, evidence paths,
  discoveries, decisions, and remaining exact-revision work.
