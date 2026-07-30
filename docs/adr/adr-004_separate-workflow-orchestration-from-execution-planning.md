---
schema_version: "1.1"
id: ADR-004
title: "Separate workflow orchestration from execution planning"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-001"]
design_refs: ["docs/design-docs/engineering-workflow-packaging.md"]
supersedes: []
superseded_by:
decision_maker: "User (explicit approval in current Codex task on 2026-07-30)"
decided: "2026-07-30T10:21:33Z"
payload_sha256: 401daee8795f70b9c0816e02e655e874bc20c37603b937fe831009bb5a80ef98
created: 2026-07-30
updated: 2026-07-30
owner: "EngineeringWorkflow Maintainer"
---

# Separate workflow orchestration from execution planning

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

The repository root currently has two incompatible identities: it is the
distribution package for Benchmark, Research, Execution Plan, and Case Study,
while its root `SKILL.md`, assets, references, CLI, tests, and evals still make
the root itself the `execution-plan` leaf Skill.

That arrangement was an intentional compatibility choice when Engineering
Research was first split out. The distribution has since grown to four
professional capabilities and a repository-wide Codex Harness bootstrap.
Keeping one leaf at the root makes installation, ownership, documentation and
validation asymmetric. It also causes project-level Harness state and EP state
to share an owner even though they have different lifecycles.

The package boundary, public Skill names, CLI paths and migration contract are
durable interfaces. Changing them therefore requires an explicit architecture
decision.

## Decision Drivers

- Make the repository name and root Skill describe the whole engineering
  workflow rather than one leaf capability.
- Give all four professional Skills an `engineering-` prefix and an explicit
  ownership directory.
- Keep Benchmark, Research, Execution Plan, and Case Study independently
  installable.
- Give project-level Bootstrap an owner that may compose professional
  initialization without absorbing their lifecycle logic.
- Keep `epctl`, `EP-NNN`, and ExecPlan artifact terminology stable.
- Avoid duplicated compatibility packages that could drift into two sources of
  truth.
- Preserve one provider-neutral canonical check and repository-relative
  contracts.
- Make the breaking installation-path migration explicit while adoption is
  still small.

## Research Evidence

No new persistent Research package is required. The user compared the credible
ownership models in the current conversation and explicitly selected a root
`engineering-workflow` aggregation Skill with a nested
`engineering-execution-plan` professional Skill.

Repository evidence is sufficient:

- [ADR-001](adr-001_split-engineering-research.md) separated evidence
  production from execution planning but deliberately kept the repository root
  as `execution-plan` only for that compatibility release. This ADR amends that
  now-expired packaging constraint without changing the Research boundary.
- The current distribution contains `engineering-benchmark/`,
  `engineering-research/`, and `engineering-case-study/` as focused packages,
  while Execution Plan alone occupies root files.
- `docs/design-docs/engineering-workflow-packaging.md` defines the target
  ownership, state and command boundaries.
- The implemented Bootstrap creates repository-wide `AGENTS.md`,
  architecture, quality, reliability and security entrypoints, demonstrating
  that its scope is broader than EP artifact management.

The selected direction fixes the product boundary. Implementation still
requires regression tests for independent installation and composed Bootstrap.

## Considered Options

### Option A — Keep Execution Plan at the repository root

This preserves every path but leaves one professional Skill privileged and
keeps project Harness responsibilities attached to the wrong owner.

### Option B — Make the repository root distribution-only

Place five sibling Skill directories beneath a neutral root. This is maximally
uniform but adds an extra `engineering-workflow/` nesting level and removes the
convenient root aggregation entrypoint.

### Option C — Make the root the Engineering Workflow aggregation Skill

Rename the root Skill to `engineering-workflow`, move Execution Plan into
`engineering-execution-plan/`, and let the root own only Bootstrap, aggregate
routing and repository-wide validation.

### Option D — Add a standalone Engineering Bootstrap leaf Skill

This separates initialization but creates a fifth professional-looking leaf
for a one-time cross-cutting operation and still leaves the old root ambiguity
unresolved.

## Decision Outcome

Adopt Option C.

The repository presentation becomes **EngineeringWorkflow** and the root
`SKILL.md` becomes `engineering-workflow`. Execution Plan moves as one package
to `engineering-execution-plan/` and exposes the Skill name
`engineering-execution-plan`.

The root aggregation Skill owns:

- `scripts/engineeringctl.py`;
- Codex Harness templates and `references/bootstrap.md`;
- project-level `docs/.engineering/harness.json`;
- routing to the four professional Skills;
- the provider-neutral repository check.

Engineering Execution Plan owns `epctl.py`, ADR/ExecPlan/Bugfix templates,
references, tests and evals. It no longer exposes `bootstrap` or
`validate --harness`. `engineeringctl bootstrap` composes the bundled
`epctl init` contract and registers Design Docs without duplicating EP logic.

The four professional Skills remain independently installable. The aggregation
Skill is intentionally distribution-aware and may load the bundled EP
component only for project initialization.

Do not retain a second `$execution-plan` package or a root `epctl.py` wrapper.
Document the one-time registration and path migration instead. Keep the short
CLI name `epctl`, ExecPlan terminology and all artifact schemas unchanged.

## Consequences

### Positive

- Repository, root Skill and project-level Bootstrap share one coherent
  Engineering Workflow identity.
- All professional Skills have parallel names and ownership directories.
- Harness state and EP state have separate schemas and locks.
- Independent installation tests can copy each professional package directly.
- Future workflow-level capabilities have a clear owner without expanding EP.

### Negative

- Existing users must re-register the root as `engineering-workflow` and
  register `engineering-execution-plan/` separately.
- Existing commands using root `scripts/epctl.py` must update their path.
- The aggregation Skill has one deliberate bundled-component dependency during
  Bootstrap.
- Renaming the GitHub repository is a post-merge administrative action rather
  than a change enforceable by Git content.

### Neutral and migration

- Existing target-repository ADR, Research, ExecPlan, Benchmark and Bugfix
  schemas do not change.
- `epctl`, `researchctl`, and `benchctl` command semantics remain stable.
- GitHub redirects the old repository URL after a rename, but maintainers
  should update local remotes and documentation. See
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository>.
- Historical ADRs and completed ExecPlans retain their original path claims as
  historical evidence; current documentation uses the new paths.

## Confirmation

- The canonical check validates five Skill metadata packages and both Workflow
  and Engineering Execution Plan eval catalogs.
- Engineering Execution Plan tests run from
  `engineering-execution-plan/tests/`.
- Repository contract tests copy each professional Skill independently.
- A composed-install test copies the root Workflow package plus its bundled EP
  component and runs Bootstrap and Harness validation.
- `engineeringctl` tests prove preview, idempotence, preservation, state
  separation and the 100-line `AGENTS.md` limit.
- Markdown link validation catches stale paths after the move.
- `python3 -B scripts/check.py` remains the only CI entrypoint.

## Revisit Triggers

- The aggregation Skill needs to compose multiple independently versioned
  distributions rather than bundled sibling components.
- A plugin/package manager requires every Skill, including the aggregator, to
  live in a same-level child directory.
- Compatibility data shows that removing `$execution-plan` or the root CLI
  path causes unacceptable adoption breakage.
- Project Harness expands into runtime environment provisioning with an
  independently deployable lifecycle.
- The repository contains unrelated engineering capabilities that no longer
  form one navigable workflow.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-001"]
- Design documents: ["docs/design-docs/engineering-workflow-packaging.md"]
- Related ExecPlans: to be created after acceptance.

## Revision Notes

- 2026-07-30T10:16:24Z — Proposed ADR created.
- 2026-07-30T10:24:00Z — Added the user-approved aggregation and professional
  Skill boundary, migration consequences, and mechanical confirmation.
