---
schema_version: "2.5"
id: EP-004
title: "Add Engineering Spec management to Harness bootstrap"
status: active
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-002", "ADR-004"]
design_refs: ["docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/engineering-spec-management.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-07-30
updated: 2026-07-30
owner: "EngineeringWorkflow Maintainer"
---

# Add Engineering Spec management to Harness bootstrap

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Engineering Workflow users can initialize a repository and receive a
versioned, locally readable set of engineering Specs instead of copying
language and naming guidance by hand. Every bootstrapped project receives the
required semantic-naming Spec; repositories with Go, TypeScript, or Python
evidence additionally receive only the applicable language Specs. The project
records its selection in a manifest, exact content in a lock, and routes Codex
through a generated local index.

The capability is observable through `engineeringctl spec plan`, `spec sync`,
`spec update`, and `spec validate`, and through the existing Codex Bootstrap.
Dry-run remains the default and an applied operation is deterministic,
reviewable, and byte-idempotent.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — packaged workflow and complete verification.
- Current state: Catalog, resolver, CLI, Bootstrap integration, documentation,
  evals, and tests are complete. Skill validation, EP validation, and the
  canonical check pass.
- Next action: commit the implementation, verify that exact revision from an
  isolated checkout, and archive EP-004 with the resulting evidence.
- Open questions: none. A provider-managed
  remote Git fetcher is explicitly outside V1; a project-relative catalog
  checkout preserves that extension point.

## Context and Orientation

`engineering-workflow` is the root aggregation Skill. Its
`scripts/engineeringctl.py` currently owns a preview-first Codex Harness
Bootstrap, creates a short root `AGENTS.md`, composes
`engineering-execution-plan/scripts/epctl.py::init_repo`, writes
`docs/.engineering/harness.json`, and validates required entrypoints.

An Engineering Spec is versioned Markdown plus catalog metadata describing its
stable ID, content digest, dependency set, file scopes, routing description,
and optional language-detection evidence. Specs are guidance data, not Codex
Skills. The distribution-level catalog will live in `engineering-specs/`.

`scripts/spec_manager.py` will be a deterministic internal module used by
`scripts/engineeringctl.py`. It will load and validate catalogs, detect
languages, resolve dependency closure, plan writes, materialize files beneath
`docs/agent-guides/managed/`, and validate project state.

Target repositories will contain:

- `docs/.engineering/specs.json`: repository-owned selection and local project
  Spec references;
- `docs/.engineering/specs.lock.json`: generated catalog and content lock;
- `docs/agent-guides/managed/index.md`: generated routing map;
- `docs/agent-guides/managed/<spec-id>.md`: exact catalog content.

The existing Harness lock serializes both Bootstrap and explicit Spec writes.
The existing `epctl init` interface and `.epctl` state do not change.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/engineering-spec-management.md` | V1 schemas, commands, ownership, and safety | Before all implementation |
| `docs/design-docs/codex-project-bootstrap.md` | Existing preflight and non-overwrite contract | Before Bootstrap integration |
| `docs/design-docs/engineering-workflow-packaging.md` | Workflow versus EP ownership | Before changing package layout |
| `scripts/engineeringctl.py` | Current Harness implementation and public CLI | Before modifying runtime behavior |
| `tests/test_engineeringctl.py` | Existing Bootstrap regression contract | Before changing plans or output |
| `tests/test_repository_contracts.py` | Independent-install packaging contract | Before adding catalog files |

Task invariants:

- Root `AGENTS.md` stays at or below 100 physical lines; the bundled template
  stays at or below 80.
- Bootstrap remains dry-run by default and performs a complete conflict check
  before writing.
- Bootstrap only creates missing content and never replaces existing project or
  managed files with different bytes.
- Explicit `spec sync --apply` and `spec update --apply` may replace only
  generated files under `docs/agent-guides/managed/` plus the generated lock
  and index after preview.
- All catalog, manifest, lock, source, destination, and project Spec paths stay
  within their owning root and reject symlinks.
- Use the Python standard library only.
- Do not add Spec behavior to `engineering-execution-plan`.

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-002", "ADR-004"].
- Design document references: ["docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/engineering-spec-management.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 established that evidence production and execution planning need
independent, versioned contracts. It is part of the ADR closure through ADR-001;
this change does not alter its sealed Research or Research Skill boundary.

ADR-001 separates Engineering Research from Execution Plan. The new catalog is
guidance content and must not reintroduce Research production into EP.

ADR-004 makes the repository root `engineering-workflow` the owner of aggregate
routing, project Bootstrap, Harness state, and the provider-neutral canonical
check. It requires professional Skills to remain independently installable and
keeps `engineering-execution-plan` focused on execution artifacts.

ADR-002 selects a preview-first Codex Bootstrap owned by Engineering Workflow.
It requires missing-only creation, byte preservation of existing documents,
separate Harness state, bounded `AGENTS.md`, atomic preflight, and mechanical
validation. Spec selection and materialization are an extension of this
accepted Harness boundary, not a new Skill or an EP-core responsibility.

The three Design Docs fix the V1 interface: a bundled catalog that can later be
split into another repository, a repository-relative external catalog checkout,
Core plus detected language selection, local manifest/lock/managed copies,
project-owned overlays, and subcommands under `engineeringctl`.

Remaining implementation choices—function boundaries, JSON rendering details,
and test fixture construction—are local and reversible. Remote network fetch,
credential management, Spec publication governance, automatic framework
inference, and deletion of stale managed files remain outside the plan.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First, add the bundled catalog and four concise Specs: semantic naming plus Go,
TypeScript, and Python implementation guidance. Catalog entries carry exact
digests, dependencies, detection markers, scopes, and route descriptions.

Second, implement `scripts/spec_manager.py` as a pure planning and validation
surface. Parse external data into strict internal structures at the boundary;
reject invalid schemas, duplicate IDs, traversal, symlinks, digest mismatch,
unknown dependencies, and cycles before returning a resolved catalog. Detect
languages while pruning VCS, dependencies, generated outputs, and managed
Harness paths.

Third, extend `engineeringctl` with a `spec` command group. Keep preview as the
default for `sync` and `update`, use the Harness lock for applied operations,
and merge the Spec plan into Bootstrap. Bootstrap will reject replacements;
explicit Spec operations may apply reported replacements in the managed
namespace.

Fourth, update the root AGENTS template, Workflow Skill instructions,
Bootstrap reference, Design Doc index, README surfaces, and independent-install
packaging contract. The root route points to one managed index instead of
embedding per-language rules.

Finally, add unit and integration coverage for empty, single-language,
polyglot, custom-project, invalid-catalog, content-drift, replacement,
idempotence, existing-AGENTS, and independent-install scenarios. Run targeted
tests, Skill validation, EP validation, and the canonical check.

## Milestones

### Milestone 1: Catalog and deterministic resolver

`engineering-specs/` and `scripts/spec_manager.py` exist. Unit tests prove that
Core is always selected, Go/TypeScript/Python evidence selects the corresponding
entries, polyglot selection composes them, and malformed or unsafe catalogs are
rejected before writes.

### Milestone 2: CLI and Bootstrap integration

`engineeringctl spec plan|sync|update|validate` exists and Codex Bootstrap
includes the same plan. Applied operations create manifest, lock, exact managed
copies, and the routing index. Repeated operations produce no byte changes;
Bootstrap preserves or conflicts on existing content.

### Milestone 3: Packaged workflow and complete verification

Skill/reference/README documentation describes the commands and boundaries.
Independent installation contains `engineering-specs/`. Targeted tests and
`python3 -B scripts/check.py` pass, and EP validation shows no missing sections
or broken architecture inputs.

## Concrete Steps

Work from the repository root.

1. Add catalog files and calculate their SHA-256 values:

   ```bash
   python3 -B scripts/spec_manager.py --check-catalog engineering-specs
   ```

   Expect a zero exit status and a summary naming four valid Specs.

2. Implement the module and CLI integration, then run:

   ```bash
   python3 -B -m unittest tests.test_engineeringctl
   ```

   Expect all Engineering Workflow CLI tests to pass.

3. Exercise a real temporary polyglot fixture through the integration tests:

   ```bash
   python3 -B -m unittest \
     tests.test_engineeringctl.EngineeringctlTestCase.test_spec_polyglot_selection
   ```

   Expect Core, Go, TypeScript, and Python in the lock and only local,
   digest-matching Markdown paths.

4. Validate all repository contracts:

   ```bash
   python3 -B scripts/check.py
   ```

   Expect every `[check]` phase to complete with a zero exit status.

5. Validate the Skill and EP:

   ```bash
   python3 /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
   python3 -B engineering-execution-plan/scripts/epctl.py --repo . validate
   ```

   Expect Skill validation success and no EP validation errors.

## Validation and Acceptance

- [x] From the repository root, run
  `python3 -B -m unittest tests.test_engineeringctl`; expect all Spec and
  existing Bootstrap tests to pass. Evidence:
  `docs/exec-plans/active/ep-004_add-spec-management/artifacts/test-engineeringctl.txt`.
- [x] Run `python3 -B -m unittest tests.test_repository_contracts`; expect the
  catalog and independently installed Workflow package contracts to pass.
  Evidence:
  `docs/exec-plans/active/ep-004_add-spec-management/artifacts/test-repository-contracts.txt`.
- [x] Run `python3 -B scripts/check.py`; expect a zero exit status across the
  provider-neutral canonical suite. Evidence:
  `docs/exec-plans/active/ep-004_add-spec-management/artifacts/check.txt`.
- [x] Run the Skill Creator `quick_validate.py` against the repository root;
  expect `Skill is valid!`. Evidence: concise transcript in this document.
- [x] In a polyglot fixture, apply Bootstrap and inspect
  `docs/.engineering/specs.lock.json`; expect Core plus Go, TypeScript, and
  Python, matching local files, and successful `engineeringctl spec validate`.
  Evidence: covered by the named integration test.
- [x] Existing Harness behavior remains compatible: dry-run makes no writes,
  repeated apply is byte-idempotent, a 101-line `AGENTS.md` conflicts, and
  `epctl --help` contains no Harness or Spec commands. Evidence: regression
  tests in `tests/test_engineeringctl.py`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

All writes use temporary files plus atomic replacement while holding
`docs/.engineering/lock`. Planning and validation are read-only. Bootstrap
recomputes its plan after acquiring the lock and stops if the result changed.

Catalog parsing and full action planning occur before writes. Bootstrap treats
an existing path with unexpected bytes or type as a conflict and therefore
does not partially initialize a repository. Explicit applied Spec commands can
replace only the lock, index, and managed Spec namespace described by their
preview. Project Specs and an existing `AGENTS.md` are never rewritten.

Retrying after an interrupted atomic write is safe: either the previous file or
the complete replacement exists. Rerun `spec validate`, then the same dry-run
and applied command. A user can roll back with version control; the resolver
does not delete stale managed files. If the manifest is invalid, restore or
edit it explicitly before rerunning. If a path catalog is unavailable, restore
the project-relative checkout; no host-specific absolute path is recorded.

## Progress

- [x] (2026-07-30T14:20:24Z) Plan created with the accepted Research and
  architecture input closure.
- [x] (2026-07-30T14:27:00Z) Filled the V1 Design Doc and every required
  ExecPlan section before production implementation.
- [x] (2026-07-30T14:58:00Z) Implemented and validated the Catalog, strict
  boundary parser, dependency resolver, language detection, lock, local
  materialization, and routing index.
- [x] (2026-07-30T15:04:00Z) Integrated `spec plan|sync|update|validate` and
  Codex Bootstrap while preserving preview-first and missing-only Bootstrap
  behavior.
- [x] (2026-07-30T15:18:00Z) Updated Skill metadata, English and Chinese
  documentation, Design Docs, evals, independent-install packaging, and
  repository checks.
- [x] (2026-07-30T15:22:00Z) Passed Skill validation, EP validation, 99 tests
  across all suites, catalog/link/index checks, and Git whitespace validation.
- [ ] Commit the verified implementation revision and archive EP-004.

## Surprises & Discoveries

- (2026-07-30T14:22:00Z) ADR-002 depends on ADR-004, which amends ADR-001, so
  the v2.5 dependency-closed Architecture Gate also requires ADR-001 and its
  concluded R-001 input. This changes only the audit closure; the implementation
  remains within Workflow Bootstrap.
- (2026-07-30T15:08:00Z) A static root `AGENTS.md` route is more stable than
  generated per-language instructions. The generated managed index can change
  with the lock while `AGENTS.md` remains bounded and byte-preserved.
- (2026-07-30T15:14:00Z) Shared-worktree documentation changes appeared outside
  this feature's file set. They were preserved and excluded from the feature
  commit; validation included the current working tree and isolated-revision
  validation will prove the committed feature independently.

## Decision Log

- (2026-07-30, Codex) Keep Spec management inside `engineering-workflow` and
  outside `epctl`. Reason: accepted ADR ownership and one unambiguous
  initialization trigger.
- (2026-07-30, Codex) Package a default catalog under `engineering-specs/` and
  support a repository-relative `path` catalog in V1. Reason: deliver a
  portable working feature without adding implicit network, credentials, or a
  Git-provider dependency; retain a clean extraction path to a dedicated repo.
- (2026-07-30, Codex) Separate installation time from task-time loading.
  Materialize and lock Specs during Bootstrap/Spec commands; route Codex to
  applicable local content through a generated index.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

Engineering Workflow now installs versioned Engineering Specs as part of the
Codex Harness rather than requiring users or Codex to copy conventions
manually. Empty repositories receive Core semantic naming. Go, TypeScript, and
Python repositories receive only matching language guidance, and polyglot
repositories compose all applicable entries.

The project manifest remains editable policy; the generated lock captures
catalog and content digests; exact local Markdown and one generated scope index
make task-time reading independent of remote state. Project guidance stays
project-owned and is routed without being copied. Explicit Spec operations can
repair or update the managed namespace after a reviewable preview, while
Bootstrap still refuses content replacement.

The implementation met every planned acceptance condition. The deliberate V1
gap is remote Git acquisition and Catalog publication governance. A separate
Catalog repository can already be checked out inside a project and selected
through the `path` source. A direct Git source should be added only when its
credential, caching, trust, and release lifecycle is decided.

### Knowledge promotion candidates

- Extract `engineering-specs/` into a separately released content repository
  when its owners or release cadence diverge from Engineering Workflow.
- Promote additional language or framework guidance only after repeated
  project evidence identifies a stable reusable contract.

## Interfaces and Dependencies

Use Python 3 standard-library modules only. `scripts/spec_manager.py` must expose
typed planning functions callable by `scripts/engineeringctl.py`; it must not
import `epctl`.

Required public CLI:

```text
engineeringctl spec plan
engineeringctl spec sync [--dry-run | --apply]
engineeringctl spec update [--dry-run | --apply]
engineeringctl spec validate
```

Required state:

```text
docs/.engineering/specs.json
docs/.engineering/specs.lock.json
docs/agent-guides/managed/index.md
docs/agent-guides/managed/<spec-id>.md
```

Catalog schema version 1, project manifest version 1, and lock version 1 are
strict external-data boundaries. Catalog dependencies must be closed and
acyclic. All managed content hashes use SHA-256. The root Skill package must
include `engineering-specs/`, `scripts/spec_manager.py`, and the existing
bundled `engineering-execution-plan` component.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-004_add-spec-management/EXECPLAN.md`
- Workflow tests:
  `docs/exec-plans/active/ep-004_add-spec-management/artifacts/test-engineeringctl.txt`
- Repository contract tests:
  `docs/exec-plans/active/ep-004_add-spec-management/artifacts/test-repository-contracts.txt`
- Canonical check:
  `docs/exec-plans/active/ep-004_add-spec-management/artifacts/check.txt`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-07-30T14:20:24Z — Initial plan created.
- 2026-07-30T14:27:00Z — Added the complete current-state implementation and
  acceptance contract after recording the Spec V1 Design Doc.
- 2026-07-30T15:22:00Z — Updated current truth, acceptance, evidence, and
  retrospective after implementation and complete validation.
