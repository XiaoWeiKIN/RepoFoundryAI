---
schema_version: "2.5"
id: EP-005
title: "Externalize engineering specifications and fetch by Git revision"
status: completed
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-002", "ADR-004", "ADR-005"]
design_refs: ["docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/engineering-spec-management.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
required_benchmark_scenarios: []
verified_revision: "git:5e7e4a8"
verification_evidence: ["artifact:docs/exec-plans/completed/ep-005_externalize-engineering-specifications/artifacts/exact-revision-check.txt"]
archive_sha256: 65a94d21a6ec4930cfeaaab87586224a7bb8ed0f1a68c937947506a831b0f678
created: 2026-07-30
updated: 2026-07-30
owner: "EngineeringWorkflow Maintainer"
---

# Externalize engineering specifications and fetch by Git revision

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Engineering Specs no longer ship inside EngineeringWorkflow. Their normative
Markdown, versions, digests, schema, and contribution lifecycle live in the
independent public `XiaoWeiKIN/EngineeringSpecifications` repository.

A user can Bootstrap a repository with the default source or a configured Git
URL/ref. EngineeringWorkflow fetches the requested remote revision without
checking out its working tree, parses and verifies the Catalog, detects
languages, materializes exact local copies, and records the resolved immutable
commit in `docs/.engineering/specs.lock.json`. Normal Codex work reads only
those local files. `spec sync` remains pinned to an existing lock, `spec update`
resolves the configured ref again, and `spec validate` remains completely
offline.

The result is observable by cloning or opening EngineeringSpecifications,
running its canonical check, then running Workflow Spec plan/sync/update tests
against isolated Git fixtures and one real public-source preview.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 4 — exact-revision verification and archival.
- Current state: ADR-005 is accepted. The public EngineeringSpecifications
  repository main is at `e93a0a3043d26be15a74d7f65c310f873a9569d0`
  with four validated Specs, contribution rules, changelog, and CI. Workflow
  has no bundled normative content; implementation commit `5e7e4a8` passes the
  canonical check in a clean detached worktree, and the real public-source
  preview resolves the full remote commit.
- Next action: archive EP-005 with `git:5e7e4a8` and the exact-revision check as
  evidence.
- Open questions: none that change the selected route. Exact error wording and
  test-fixture helpers remain local implementation choices.

## Context and Orientation

EngineeringWorkflow is the current repository. Its root Skill owns
`scripts/engineeringctl.py`, which composes project Harness Bootstrap with the
nested `engineering-execution-plan` initializer. `scripts/spec_manager.py`
currently loads `engineering-specs/catalog.json` or a project-relative copied
Catalog. It writes:

- `docs/.engineering/specs.json`: project-owned source, selection, and project
  Spec references;
- `docs/.engineering/specs.lock.json`: generated resolution;
- `docs/agent-guides/managed/<spec-id>.md`: exact managed copies;
- `docs/agent-guides/managed/index.md`: the routing map used by `AGENTS.md`.

EngineeringSpecifications is a sibling local repository at
`/Users/wangxiaowei1/x-otel/EngineeringSpecifications` and a public GitHub
repository at
`https://github.com/XiaoWeiKIN/EngineeringSpecifications`. It owns
`catalog.json`, `specification/`, `schemas/`, `scripts/check.py`, and tests.
It is not packaged inside the Workflow Skill.

A **source ref** is the branch, tag, or commit expression stored in
`specs.json`. A **resolved revision** is the full commit hash produced by Git
and stored in the lock. **Sync** consumes the resolved revision already in the
lock; **update** resolves the source ref anew.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-005_external-engineering-specifications.md` | Accepted ownership, Git, lock, security, and migration decision | Before changing the source or update model |
| `docs/design-docs/engineering-spec-management.md` | Exact manifest, lock, resolution, CLI, and validation contracts | Before editing resolver or tests |
| `docs/design-docs/codex-project-bootstrap.md` | Bootstrap preservation and Harness composition rules | Before changing Bootstrap |
| `scripts/spec_manager.py` | Boundary parsing, selection, materialization, and offline validation | During implementation |
| `scripts/engineeringctl.py` | Public CLI and preflight/apply integration | During implementation |
| `AGENTS.md` | Repository instruction and Mermaid requirement; also preserves user changes | Before completion |

Task invariants:

- Preserve all unrelated dirty worktree changes and never stage them.
- Keep the generated `AGENTS.md` template at no more than 80 lines and enforce
  the hard limit of 100.
- Use no third-party Python dependency; Git is the only new runtime
  prerequisite.
- Never invoke a shell with remote-controlled URL, ref, or path data.
- Never log credential output or persist credentials.
- Do not check out or execute remote repository content.
- Preserve dry-run as the default and preflight all Bootstrap writes.
- Leave historical EP-004 unchanged.

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-002", "ADR-004", "ADR-005"].
- Design document references: ["docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/engineering-spec-management.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 established the broader Agent-first repository model: concise
instruction entrypoints should route to versioned repository-local knowledge,
and deterministic scripts should validate artifact contracts. That evidence is
sealed under `docs/research/completed/r-001_multi-document-research/`.
External fetching does not change the task-time rule: Codex reads local managed
copies, not mutable network content.

ADR-001 separates evidence production from execution planning. ADR-004 moves
project-wide orchestration into EngineeringWorkflow, and ADR-002 gives that
owner the Codex Harness Bootstrap, dry-run, preservation, manifest, and
100-line AGENTS contract. Their closure must remain intact.

ADR-005 adds the current direction:

- EngineeringSpecifications owns normative Catalog content.
- Workflow contains only the consumer and has no bundled fallback.
- Project manifest source is `{kind: "git", url, ref}`.
- Lock stores the full resolved commit and content digests.
- Sync is lock-pinned; update re-resolves the ref.
- Validation is offline.
- Remote bytes and paths are parsed at the boundary and never executed.
- Git authentication remains external to Workflow.

The design documents translate those decisions into the concrete file and CLI
contracts. Remaining implementation unknowns—temporary bare-repository command
sequence, bounded error messages, and test helpers—are reversible details and
cannot alter the accepted boundary.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First complete EngineeringSpecifications as an independently valid repository:
Catalog schema, Core/language Markdown, bilingual documentation, deterministic
check, tests, public remote, and initial commit.

Then replace filesystem-root Catalog loading in `scripts/spec_manager.py` with
a byte-oriented Catalog representation and a `GitCatalogSource`. The source
must fetch into an ephemeral bare repository, resolve a full commit, read blobs
through Git plumbing, cap output, and expose the Catalog bytes plus selected
content. Manifest parsing accepts only the strict Git source. Lock generation
records source and revision. Plan preparation chooses a locked revision for
plan/sync and the configured ref for initial/update operations. Offline
validation parses lock and compares only local bytes and generated projections.

Update `scripts/engineeringctl.py` to remove `SPEC_CATALOG_DIR`, define the
public default repository/ref, pass initial source overrides into Bootstrap and
Spec commands, and convert Git errors into stable CLI failures without writes.

Delete `engineering-specs/`. Replace bundled-fixture tests with temporary Git
repositories whose branch can move during a test. Update repository contracts,
README files, Skill instructions, Bootstrap reference, design documents, and
UI metadata so packaging no longer claims embedded content.

Finally run both repositories' canonical checks, a real public-source dry-run,
independent-install checks, and `epctl validate`. Record the exact Workflow
revision and archive this plan with generated evidence.

## Milestones

### Milestone 1: Independent specification repository

EngineeringSpecifications contains the Catalog, four initial Specs, schema,
English/Chinese README, AGENTS route, check script, and tests. Its public main
branch is readable without Workflow.

Validation: from the sibling repository run
`python3 -B scripts/check.py`; expect `CHECK_OK` and four specifications.

### Milestone 2: Git-backed resolver and immutable lock

Workflow accepts only Git Catalog sources, resolves refs safely, records full
commits, implements lock-pinned sync and explicit update, and validates local
state offline. No normative content remains in the package.

Validation: run focused `tests/test_spec_manager.py` and
`tests/test_engineeringctl.py`; expect temporary-Git lifecycle cases to pass.

### Milestone 3: Packaging and documentation migration

Root Skill, double-language README, Bootstrap reference, design docs, examples,
and repository contracts consistently describe the independent repository and
default source. Independently copied Workflow still resolves a Git fixture.

Validation: run `tests/test_repository_contracts.py` and Skill validation;
expect no bundled Catalog dependency or broken link.

### Milestone 4: End-to-end proof and archival

Both canonical checks pass, a real public-source preview reports a 40-character
commit without writes, no unrelated worktree files are staged, and EP-005 is
archived with actual evidence.

## Concrete Steps

From `/Users/wangxiaowei1/x-otel/EngineeringSpecifications`:

```bash
python3 -B scripts/check.py
git status --short
```

Expected: `CHECK_OK: ... (4 specifications)` and no uncommitted files after
the repository commit.

From `/Users/wangxiaowei1/x-otel/EngineeringPlan`:

```bash
python3 -B -m unittest tests.test_spec_manager tests.test_engineeringctl
python3 -B -m unittest tests.test_repository_contracts
python3 -B scripts/check.py
python3 scripts/engineeringctl.py --repo <empty-temp-repo> spec plan
python3 engineering-execution-plan/scripts/epctl.py --repo . validate
```

The real preview must report Catalog ID
`io.github.xiaoweikin.engineering-specifications`, source URL/ref, a full Git
commit, and only `create` actions. The empty target repository must remain
empty because preview is non-mutating.

## Validation and Acceptance

- [x] From EngineeringSpecifications, run `python3 -B scripts/check.py`; expect
  all unit tests and four Catalog entries to pass. Evidence:
  `artifacts/engineering-specifications-check.txt`.
- [x] From Workflow, run
  `python3 -B -m unittest tests.test_spec_manager
  tests.test_engineeringctl`; expect Git source, lock, sync/update, attack, and
  offline validation tests to pass. Evidence:
  `artifacts/workflow-spec-tests.txt`.
- [x] Run `python3 -B -m unittest tests.test_repository_contracts`; expect
  package and documentation contracts to pass without `engineering-specs/`.
  Evidence: `artifacts/repository-contracts.txt`.
- [x] Run `python3 -B scripts/check.py`; expect the canonical aggregate check
  to pass. Evidence: `artifacts/workflow-check.txt`.
- [x] Run a real default-source `spec plan` against a new temporary target;
  expect a full resolved commit and zero created files. Evidence:
  `artifacts/public-source-preview.txt`.
- [x] Run `python3 engineering-execution-plan/scripts/epctl.py --repo .
  validate`; expect no errors. Evidence:
  `artifacts/epctl-validate.txt`.
- [x] Confirm the generated AGENTS template is at most 80 lines and the hard
  validator still rejects 101 lines. Evidence: Workflow tests and canonical
  check.
- [x] Confirm `git diff --cached --name-only` excludes the four pre-existing
  unrelated worktree modifications.
- [x] Check implementation commit `5e7e4a8` in an isolated detached worktree
  with `python3 -B scripts/check.py`; expect all integrity checks to pass.
  Evidence: `artifacts/exact-revision-check.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

EngineeringSpecifications checks and Workflow previews are read-only and safe
to repeat. Spec apply operations continue to use the existing repository lock
and atomic replace behavior. A Git failure occurs before planned project writes
and leaves the target byte-identical. Temporary bare repositories are deleted
by context-manager cleanup on success and failure.

If Workflow implementation fails, retain the accepted ADR and active EP, fix
the consumer, and rerun isolated tests. Do not restore a bundled fallback.
Because the old feature commits have not been pushed, the corrective commit can
follow them without data migration. Existing test targets are temporary.

Remote repository creation is idempotently checked by URL. A failed initial
push can be repeated. Once public history exists, correct it with new commits;
do not force-push or delete the repository. The initial tag is created only
after end-to-end compatibility passes.

## Progress

- [x] (2026-07-30T14:59:03Z) Plan created with closed Research and
  Architecture input sets.
- [x] (2026-07-30T15:08:00Z) Created and accepted ADR-005 from the user's
  explicit repository-boundary decision.
- [x] (2026-07-30T15:12:00Z) Created and pushed the initial public
  EngineeringSpecifications repository at commit `1d3c04b`.
- [x] (2026-07-30T15:16:00Z) Filled all REQUIRED EP sections before Workflow
  implementation.
- [x] (2026-07-30T15:08:00Z) Implemented the temporary-bare-Git resolver,
  strict remote boundary parsing, immutable lock, pinned sync, explicit update,
  and offline validation; deleted bundled normative content.
- [x] (2026-07-30T15:12:00Z) Replaced bundled fixtures with isolated Git
  repositories and updated Skill metadata, evals, bilingual README, Bootstrap
  reference, design docs, and package contracts.
- [x] (2026-07-30T15:15:00Z) Passed 23 focused Spec tests, 8 repository
  contract tests, both repository checks, the full Workflow canonical check,
  EP validation, and a real GitHub-source dry-run.
- [x] (2026-07-30T15:19:00Z) Added and pushed EngineeringSpecifications
  contribution rules, changelog, and independent GitHub Actions check at
  `e93a0a3043d26be15a74d7f65c310f873a9569d0`.
- [x] (2026-07-30T15:18:00Z) Staged only EP-005 implementation and evidence;
  preserved the four pre-existing files matching incoming origin/main as
  unstaged changes.
- [x] (2026-07-30T15:20:00Z) Committed Workflow implementation as `5e7e4a8`,
  passed the full canonical check on that exact detached revision, and pushed
  EngineeringSpecifications tag `v0.1.0`.

## Surprises & Discoveries

- (2026-07-30T14:43:00Z) The host has no GitHub CLI, but the authenticated
  Chrome session could create the empty public repository and normal Git
  credentials could push successfully. Impact: no new plugin or stored token
  was required.
- (2026-07-30T14:59:00Z) ADR-005 depends on ADR-002, whose transitive
  Architecture closure reaches ADR-004 and ADR-001; ADR-001 in turn requires
  Research R-001 in EP-005. Impact: the plan explicitly carries the complete
  validated input closure.
- (2026-07-30T15:15:00Z) The first GitHub fetch attempt during legacy tests
  saw a transient connection reset, while the isolated file-URL tests and the
  final public preview succeeded. Impact: canonical tests use local Git
  fixtures, and public network resolution remains a separate end-to-end check.

## Decision Log

- (2026-07-30, user / Codex) Use
  `XiaoWeiKIN/EngineeringSpecifications` as a public, independently governed
  repository. Reason: the user explicitly requested a specification repository
  analogous to OpenTelemetry's.
- (2026-07-30, Codex) Default new projects to the public `main` ref while
  pinning the resolved commit in each lock. Alternative: default to a release
  tag. Reason: following `main` enables explicit `spec update`, while sync and
  task-time reads remain reproducible.
- (2026-07-30, Codex) Read remote blobs from a temporary bare repository
  without checkout. Alternative: clone a working tree. Reason: this minimizes
  executable/filter surface and leaves no project-local cache.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The implementation now matches the user-selected repository boundary:
EngineeringSpecifications owns all normative content, while Workflow owns only
fetching, strict parsing, detection, locking, local materialization, routing,
and offline validation.

The lock/update distinction is stronger than the original bundled design.
Projects can repair content reproducibly from the locked commit and opt into a
moved branch only through an explicit previewed update. Remote data is never
checked out or executed. Tests prove failure safety for missing refs, digest
drift, path traversal, symlinks, embedded credentials, managed drift, and
unavailable remotes during validation.

The verified Workflow implementation revision is `git:5e7e4a8`. The
EngineeringSpecifications v0.1.0 tag points to
`e93a0a3043d26be15a74d7f65c310f873a9569d0`. The only intentional unresolved
item is license selection, which remains a repository-owner legal choice and
does not affect Catalog consumption.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

Runtime dependencies:

- Python 3 standard library only.
- Git CLI available on `PATH`.
- A reachable Git URL for initial sync/update; credentials may be supplied only
  by existing Git credential helper or SSH agent.

Required public data interfaces:

```text
SpecManifest.catalog:
  {"kind": "git", "url": <non-empty Git URL>, "ref": <non-option ref>}

Catalog:
  catalog_id, catalog_version, digest, resolved_revision,
  ordered_specs, by_id, and a content reader

GitCatalogSource.resolve(revision_or_ref) -> Catalog

plan_spec_state(repo, operation, initial_source) -> SpecPlan
validate_spec_state(repo) -> (errors, warnings)
```

`SpecPlan` and JSON CLI payloads must expose Catalog ID/version/digest and
resolved revision. `engineeringctl` owns default URL/ref and CLI options;
`spec_manager` owns strict source parsing and Git execution.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-005_externalize-engineering-specifications/EXECPLAN.md`
- EngineeringSpecifications check:
  `artifacts/engineering-specifications-check.txt`
- Focused Workflow Spec tests: `artifacts/workflow-spec-tests.txt`
- Repository contracts: `artifacts/repository-contracts.txt`
- Canonical Workflow check: `artifacts/workflow-check.txt`
- Public GitHub source preview: `artifacts/public-source-preview.txt`
- EP validation: `artifacts/epctl-validate.txt`
- Exact Workflow revision check: `artifacts/exact-revision-check.txt`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-07-30T14:59:03Z — Initial plan created.
- 2026-07-30T15:16:00Z — Replaced every placeholder with the accepted external
  repository architecture, exact implementation surfaces, milestones,
  commands, evidence, recovery, and interface contracts.
- 2026-07-30T15:16:00Z — Updated current facts, completed validation evidence,
  discoveries, progress, and retrospective after implementation.
