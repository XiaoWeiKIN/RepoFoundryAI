---
schema_version: "1.1"
id: ADR-002
title: "Add a Codex project documentation bootstrap"
status: accepted
research_refs: []
depends_on: ["ADR-004"]
amends: []
design_refs: ["docs/design-docs/codex-project-bootstrap.md"]
supersedes: []
superseded_by:
decision_maker: "User (explicit approval in current Codex task on 2026-07-30)"
decided: "2026-07-30T10:21:42Z"
payload_sha256: a9ced6c6e80b1e246bd8fc7b90e53b7e9e6aff18a590c545f904dbf59ce61ad7
created: 2026-07-30
updated: 2026-07-30
owner: "EngineeringWorkflow Maintainer"
---

# Add a Codex project documentation bootstrap

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

Engineering Execution Plan exposes `epctl init`, which safely creates only the
directories, indexes, and state needed for Research, ADR, ExecPlan, Bugfix, and
technical-debt artifacts. It does not establish the repository-level knowledge
entrypoints that let Codex discover architecture, engineering controls, and the
EP lifecycle.

The project needs an initialization workflow that combines Codex's
map-oriented repository guidance with EP's versioned decision and execution
artifacts. This changes the public CLI, packaged templates, validation contract,
and the boundary between EP-owned files and repository-owned documentation, so
the choice must be durable and explicit.

## Decision Drivers

- Preserve the existing idempotent, non-overwriting `init` contract.
- Make preview the default and require explicit authorization for writes.
- Keep the EP file contract usable by Agents other than Codex.
- Give Codex a short repository map instead of a monolithic instruction manual.
- Enforce `AGENTS.md` at no more than 100 physical lines.
- Never invent project facts or overwrite an existing source of truth.
- Make the initialized structure and instruction budget mechanically
  verifiable in local development and CI.
- Keep runtime Harness concerns such as worktrees, observability, permissions,
  deployment, and auto-merge outside this decision.

## Research Evidence

No persistent Research package is required. The Decision Owner has fixed the
desired direction in the current conversation: add project initialization that
creates Codex-practice documentation combined with EP, and enforce
`AGENTS.md <= 100` lines.

Repository evidence is sufficient to define the change:

- `engineering-execution-plan/scripts/epctl.py::init_repo` provides the safe
  EP-owned initialization primitive and creates only missing paths.
- The root `SKILL.md` defines `AGENTS.md` as a short entrypoint and routes detailed
  knowledge to ADRs, Design Docs, Research, and ExecPlans.
- `docs/design-docs/codex-project-bootstrap.md` specifies the proposed public
  interface, file ownership, manifest, validation, and acceptance behavior.
- OpenAI's Harness Engineering case study describes the operating principle:
  keep `AGENTS.md` as a map, use structured repository documentation as the
  system of record, and validate knowledge mechanically:
  <https://openai.com/index/harness-engineering/>.

These inputs settle the route. Implementation details remain testable and do
not require comparative external investigation.

## Considered Options

### Option A — Extend `init` to create all Codex documents

This offers one command but changes a low-level, Agent-neutral operation into a
Codex-specific, repository-wide mutation. Existing callers could receive new
files without requesting them, and preview semantics would be unclear.

### Option B — Keep `init` and add `bootstrap` to Execution Plan

`init` remains the deterministic EP artifact initializer. `bootstrap` performs
a preflighted, preview-first initialization of repository knowledge entrypoints.
The `codex` profile owns a separate Harness manifest and validation rules.

### Option C — Put `bootstrap` in the Engineering Workflow aggregation Skill

The root aggregation Skill owns repository-wide Harness entrypoints and
composes `epctl init`. Project state remains separate from EP state, and no
single-purpose Bootstrap leaf Skill is introduced.

### Option D — Keep the current behavior

Projects continue assembling `AGENTS.md`, architecture navigation, governance
documents, and EP indexes manually. The result is inconsistent and cannot be
validated as one contract.

## Decision Outcome

Adopt Option C, conditional on the package boundary accepted in ADR-004.

Engineering Execution Plan retains the current `init` behavior.
Engineering Workflow adds a preview-by-default
`engineeringctl bootstrap --profile codex` command. Applying bootstrap will:

1. invoke the existing EP initialization primitive;
2. create only missing Codex Harness entrypoints and governance scaffolds;
3. register `docs/design-docs` without moving existing documents;
4. write a separate `docs/.engineering/harness.json` contract;
5. preserve existing documentation/content files byte-for-byte;
6. reject path conflicts, symlink traversal, and an existing
   `AGENTS.md` over 100 physical lines before making changes;
7. make normal `engineeringctl validate` check an enabled Harness, while
   `engineeringctl validate --harness` requires it explicitly.

The EP core remains Agent-neutral and exposes no Codex profile or Harness
validator. `AGENTS.md` is an optional Codex adapter that points to universal
architecture and EP artifacts.

## Consequences

### Positive

- A new or existing repository can establish a consistent documentation
  control plane through one guarded workflow.
- `AGENTS.md` remains a bounded map; detailed rules stay in versioned sources of
  truth.
- Existing EP callers and repositories retain their current `init` behavior.
- CI can detect missing Harness files and instruction growth.
- The Harness manifest makes validation ownership explicit without expanding
  the existing architecture-root config schema.

### Negative

- Engineering Workflow gains a bundled-component dependency on EP during
  Bootstrap.
- Scaffold documents require repository-specific completion before becoming
  authoritative.
- A strict physical-line limit can require restructuring otherwise useful
  instructions.
- Bootstrap must maintain non-destructive behavior across both greenfield and
  brownfield repositories.

### Neutral and migration

- Repositories that never invoke bootstrap are unaffected.
- Existing files are registered or preserved; they are never silently
  migrated.
- `docs/.epctl/config.json` is the sole existing managed file Bootstrap may
  update, only to register `docs/design-docs`; index rebuilding remains
  explicit.
- Runtime Harness capabilities remain candidates for a future independent
  professional Skill if their scope grows.

## Confirmation

The accepted decision will be encoded and continuously checked through:

- CLI tests proving preview has no writes;
- apply and repeated-apply tests proving creation and idempotence;
- byte-preservation tests for existing documents;
- conflict and symlink preflight tests;
- Harness manifest schema and required-file validation;
- boundary tests proving 100 lines pass and 101 lines fail;
- a repository-contract test ensuring the bundled `AGENTS.md` template stays at
  or below 80 physical lines;
- the repository canonical check, `python3 -B scripts/check.py`.

## Revisit Triggers

- Bootstrap begins configuring runtime environments, permissions,
  observability, deployment, or merge automation.
- Two or more non-Codex profiles require materially different lifecycle or
  ownership semantics.
- The 100-line physical limit proves incompatible with required Codex
  instruction discovery.
- The separate Harness manifest duplicates enough EP configuration to justify
  a versioned unified config schema.
- Non-destructive preflight cannot support common brownfield layouts without a
  migration protocol.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-004"]
- Amended ADRs: []
- Design documents: ["docs/design-docs/codex-project-bootstrap.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-07-30T09:30:15Z — Proposed ADR created.
- 2026-07-30T09:34:00Z — Filled the proposal with the user-selected bootstrap
  boundary, alternatives, consequences, and mechanical confirmation.
- 2026-07-30T10:27:00Z — Moved project-level Bootstrap ownership from EP to the
  Engineering Workflow aggregation Skill after the user explicitly selected
  the new package boundary.
