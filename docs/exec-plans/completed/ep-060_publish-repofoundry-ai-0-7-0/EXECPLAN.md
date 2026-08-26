---
schema_version: "2.8"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-060
title: "Publish RepoFoundry AI 0.7.0"
status: completed
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "Release scope and compatibility are established by the completed implementation plans, repository history, and deterministic validation evidence; no new research question is open."
adr_refs: []
adr_constraint_refs: []
adr_evidence: []
design_refs: ["docs/design-docs/repo-foundry-versioning-and-migrations.md"]
design_evidence: []
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: not_required
architecture_decision_gate_reason: "The accepted versioning design and SemVer-compatible feature scope determine a 0.7.0 minor release without a new durable architecture decision."
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision: "df2cb6b197b5d0815f18dde922e8f8ca79331bf9"
verification_evidence: ["python3 scripts/check.py: Research 35, Benchmark 9, Design 16, Execution Plan 59, integration 118; all passed", "GitHub Actions run 32921152852: Python 3.10, Python 3.14, and ep-integrity passed", "PR #34 merged: https://github.com/XiaoWeiKIN/RepoFoundryAI/pull/34", "GitHub Release v0.7.0: https://github.com/XiaoWeiKIN/RepoFoundryAI/releases/tag/v0.7.0", "Public installer smoke: release 0.7.0-df2cb6b197b5, CLI RepoFoundry AI 0.7.0, package SHA-256 2d52535c4959dec67fefaac28bc35f6b3461a6eff479dcc8ace4088563051180"]
archive_sha256: 931a7f07b5fbe00489605cbdd1508dfa5f45527aebf3c460a5db7a256910ecca
created: 2026-08-26
updated: 2026-08-26
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Publish RepoFoundry AI 0.7.0

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Publish the unreleased collaborative workflow and effective-ADR projection work
as RepoFoundry AI `0.7.0`. After publication, users can install the stable
GitHub Release, run `repofoundry --version`, and explicitly upgrade a repository
to distribution `0.7.0`; existing Harness schema, Core, adapters, governance
policy, and activation protocol remain compatible.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: seal verified public release evidence.
- Current state: PR #34 is merged at `df2cb6b197b5d0815f18dde922e8f8ca79331bf9`;
  tag and latest GitHub Release `v0.7.0` are published; an isolated public
  Release install reports `RepoFoundry AI 0.7.0`.
- Next action: archive EP-060 against the verified merge revision, then merge
  the documentation-only evidence update.

## Context and Orientation

`VERSION` is the authoritative distribution version read by
`scripts/foundryctl.py` and checked by `install.py`. This repository release
publishes through GitHub tag and Release `v0.7.0`. The stable installer resolves
that Release and validates the package before activation.

The release contains two feature groups since `v0.6.0`: commit `47d1fe2` adds
collaborative calibration across the four engineering authoring Skills, and
EP-059 adds derived effective/current/review/historical ADR projections in
`engineering-execution-plan/scripts/epctl.py`. Neither changes repository
Harness templates, manifest schema, Core files, adapter bytes, governance
policy, or activation protocol.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Defines independent version planes and release invariants | Before version selection and release validation |
| `VERSION` | Authoritative distribution SemVer | Before building or tagging the candidate |
| `install.py` | Stable Release acquisition and package validation | Before public installer verification |
| `.github/workflows/integrity.yml` | Required supported-Python and EP integrity checks | Before merging PR #34 |
| `docs/exec-plans/completed/ep-059_effective-adr-index-projection/EXECPLAN.md` | Completed implementation and compatibility evidence for ADR projections | Before composing release notes |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `not_required`.
- Architecture compliance: `applicable`.
- ADR references: [].
- ADR constraint references: [].
- ADR evidence: [].
- Design document references: ["docs/design-docs/repo-foundry-versioning-and-migrations.md"].
- Approved Design revision evidence: [].
- Architecture entrypoint: `docs/design-docs/index.md`.

Research is not required because the release inputs are already implemented and
verified by their repository history and completed plans; there is no unresolved
technical question. A new ADR is not required because DD-006 already fixes the
version-plane rules and SemVer class: two backward-compatible feature additions
produce minor release `0.7.0`. Only the distribution version advances. Harness
schema stays `3`, Core `1.5.0`, Codex adapter `2.4.0`, Claude adapter `1.3.0`,
Portable adapter `1.3.0`, governance policy schema `1`, and activation protocol
`2`. No unknown migration input remains.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| docs/design-docs/repo-foundry-versioning-and-migrations.md | Advance only `VERSION` and distribution-facing references to `0.7.0`; preserve all component and protocol versions because no owned template bytes or persistent Harness interpretation changes. Publish the source-addressed tag and stable GitHub Release. | `python3 scripts/check.py`; PR #34 checks; `gh release view v0.7.0`; isolated stable-installer smoke test reporting `RepoFoundry AI 0.7.0`. |

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

First update `VERSION`, root Skill examples, bilingual README upgrade examples,
the current-version parts of DD-006, and tests whose assertions represent the
installed distribution. Preserve historical `0.6.0` release records and old
fixture inputs. Add concise release notes under this plan's `artifacts/`.

Then run the canonical repository check and review the complete diff. Commit and
push the candidate to PR #34, update the PR description to cover both feature
groups, and wait for every required check. Merge without force-push, resolve the
new `main` commit, create annotated tag and GitHub Release `v0.7.0`, and verify
the Release plus an isolated installer invocation. Finally record public URLs
and immutable identifiers here, archive the EP against the verified release
commit, and merge that documentation-only evidence update separately.

## Milestones

### Milestone 1: Produce a coherent `0.7.0` candidate

The candidate consistently reports distribution `0.7.0`, documents both feature
groups, preserves all independent component versions, and passes the canonical
local check.

### Milestone 2: Merge and publish the immutable release

PR #34 passes supported-Python and EP integrity checks and merges to `main`.
Tag and GitHub Release `v0.7.0` point to that merged commit.

### Milestone 3: Verify installation and seal release evidence

An isolated stable installation reports `RepoFoundry AI 0.7.0`; public URLs,
commit, tag, and verification results are recorded before EP archival.

## Concrete Steps

Work from `/Users/wangxiaowei1/x-otel/EngineeringPlan`.

1. Edit `VERSION`, `SKILL.md`, `README.md`, `README.zh-CN.md`, DD-006, and
   current-distribution assertions in `tests/`; expect no component-version bump.
2. Run `python3 scripts/check.py`; expect every unit, integration, and integrity
   suite to pass.
3. Commit and `git push origin codex/collaborative-engineering-workflows`; update
   PR #34 and wait for `gh pr checks 34 --watch` to report all checks passing.
4. Merge PR #34, fetch `origin/main`, and create GitHub Release `v0.7.0` from the
   resolved merge commit using this plan's `artifacts/release-notes.md`.
5. In a new temporary prefix, run `install.py --version 0.7.0 --host none`, then
   invoke the installed `repofoundry --version`; expect `RepoFoundry AI 0.7.0`.
6. Update outcomes with immutable evidence, archive EP-060, validate, and merge
   the release-evidence-only follow-up.

## Validation and Acceptance

- [x] From the repository root, run `python3 scripts/check.py`; expect all
  canonical suites and integrity checks to pass. Evidence: concise transcript in
  this plan and GitHub Actions on PR #34.
- [x] Run `gh pr checks 34 --repo XiaoWeiKIN/RepoFoundryAI`; expect every check
  to pass before merge. Evidence: PR #34 check rollup.
- [x] Run `gh release view v0.7.0 --repo XiaoWeiKIN/RepoFoundryAI`; expect a
  published, non-draft, non-prerelease Release targeting the merged `main`
  commit. Evidence: Release URL and tag commit recorded below.
- [x] Run the stable installer into an isolated temporary prefix with
  `--version 0.7.0 --host none`; expect its launcher to print
  `RepoFoundry AI 0.7.0`. Evidence: concise transcript recorded below.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Version and documentation edits are deterministic and repeatable. Local checks
are read-only apart from generated caches. A failed PR check blocks merge; fix it
on the same branch and rerun. Do not move or overwrite an existing tag. If tag
creation succeeds but Release creation fails, retry `gh release create` against
the already verified tag. If public installer verification fails, leave the
release visible only after diagnosing package identity; because v0.7.0 is
backward compatible and does not mutate repositories automatically, existing
v0.6.0 installations remain usable. The smoke test uses a unique temporary
prefix and does not register host Skills.

## Progress

- [x] (2026-08-26T01:53:51Z) Plan created; all required sections were filled
  before release implementation began.
- [x] (2026-08-26) Confirmed `main` and latest Release are `v0.6.0`, PR #34 is
  open and mergeable, and tag `v0.7.0` does not exist.
- [x] (2026-08-26) Selected minor release `0.7.0` from the two
  backward-compatible feature groups and confirmed no independent component
  plane changes.
- [x] (2026-08-26) Filled the executable release plan before release edits.
- [x] (2026-08-26) Advanced the distribution surface to `0.7.0`, documented
  both feature groups, preserved all component planes, and added release notes.
- [x] (2026-08-26) Ran `python3 scripts/check.py`: Research 35, Benchmark 9,
  Design 16, Execution Plan 59, and integration 118 tests passed; every
  integrity check passed.
- [x] (2026-08-26) Pushed candidate `258b19c`; GitHub Actions run `32921152852`
  passed Python 3.10, Python 3.14, and ep-integrity.
- [x] (2026-08-26) Squash-merged PR #34 as
  `df2cb6b197b5d0815f18dde922e8f8ca79331bf9`; its tree
  `0ca92508b2c32627c67802a999d0d789d0235c30` exactly matches the verified
  candidate tree.
- [x] (2026-08-26) Published annotated tag and latest GitHub Release `v0.7.0`;
  the tag dereferences to the merge commit and the Release is neither draft nor
  prerelease.
- [x] (2026-08-26) Installed from the public GitHub Release into
  `/tmp/repofoundry-v070-smoke.kVnpZM` with no host registration or project
  mutation. The launcher reported `RepoFoundry AI 0.7.0`; provenance recorded
  release ID `0.7.0-df2cb6b197b5`, package SHA-256
  `2d52535c4959dec67fefaac28bc35f6b3461a6eff479dcc8ace4088563051180`, and
  archive SHA-256
  `b830189118c497fa9434de21d97997e59b65388cf31ad25720e9d14630c34578`.

## Surprises & Discoveries

- PR #34 was already open with passing checks for the collaborative workflow
  commit, so the release candidate can extend that PR without creating a
  parallel integration path.

## Decision Log

- 2026-08-26 — Publish `0.7.0`, not `0.6.1`: the branch adds user-visible
  collaboration and ADR lifecycle projection features while remaining backward
  compatible.
- 2026-08-26 — Keep Harness schema/Core/adapters/governance/activation versions
  unchanged because this release changes distribution Skills and tooling, not
  owned repository template bytes or persistent Harness interpretation.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry AI `0.7.0` is publicly available from
`https://github.com/XiaoWeiKIN/RepoFoundryAI/releases/tag/v0.7.0`. It combines
collaborative engineering authoring with effective/current/review/historical ADR
projections, and the public installer resolves the release to the exact verified
merge commit. All local and GitHub checks passed. Compatibility matched the
plan: only the distribution version advanced; no Harness schema, Core, adapter,
governance-policy, or activation-protocol migration was introduced.

No product gap remains. EP archival evidence is intentionally merged after the
release tag so the plan can truthfully record the public Release and installer
result; that follow-up changes documentation only and does not alter v0.7.0.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

Local release preparation requires Python 3.10+ and the repository's standard
library-only test suites. Publication uses authenticated `git` and GitHub CLI
access to `XiaoWeiKIN/RepoFoundryAI`. The public contract is the immutable Git
tag `v0.7.0`, its GitHub Release, repository-root `install.py`, and the CLI
version surface `repofoundry --version`. No new runtime dependency is added.

## Artifacts and Notes

- Plan after archival: `docs/exec-plans/completed/ep-060_publish-repofoundry-ai-0-7-0/EXECPLAN.md`
- Release notes after archival: `docs/exec-plans/completed/ep-060_publish-repofoundry-ai-0-7-0/artifacts/release-notes.md`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-26T01:53:51Z — Initial plan created.
- 2026-08-26 — Replaced all required placeholders with the bounded `0.7.0`
  release, verification, recovery, and evidence workflow.
- 2026-08-26 — Recorded the merged commit, public tag and Release, CI run, and
  isolated installer provenance before archival.
