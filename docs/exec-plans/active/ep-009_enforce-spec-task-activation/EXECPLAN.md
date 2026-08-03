---
schema_version: "2.5"
id: EP-009
title: "Enforce Engineering Spec task activation"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "ESP-0007, ESP-0009, the current EngineeringSpecifications model, and the current official Codex manuals define the needed selection, activation, Skill discovery, AGENTS, and Hook interfaces; no decision-relevant factual unknown remains."
adr_refs: []
design_refs: []
architecture_entrypoint: ""
architecture_gate: not_required
architecture_gate_reason: "The repository owner explicitly selected one generated engineering-specs Router Skill plus AGENTS and trusted project Hook enforcement; accepted ADR-002 and ADR-005 already assign Harness routing to RepoFoundry and normative content to EngineeringSpecifications, so implementation introduces no unresolved architecture alternative."
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-03
updated: 2026-08-03
owner: "Codex"
---

# Enforce Engineering Spec task activation

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

After RepoFoundry bootstraps a trusted Codex project, every implementation or
review task has one discoverable `$engineering-specs` Router Skill. The Router
selects from the project's already locked local Specifications, records the
turn's decision and planned paths, and ensures applicable full documents reach
developer context before the first write. A project Hook blocks writes that
skip activation or target an undeclared path, while the Stop Hook checks the
changed-path set and evidence handoff.

The user can observe the feature in an isolated target repository: Bootstrap
creates `.agents/skills/engineering-specs/` and `.codex/hooks.json`; a prompt
Hook names the Router; `apply_patch` is denied before activation; the first
post-activation edit is retried after local Spec injection; and a complete
handoff passes the Stop audit. Normative Markdown stays exclusively in the
independent EngineeringSpecifications repository and its locked managed
copies.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 4 — exact-revision verification and archival.
- Current state: ESP-0010, the generated Router Skill, four trusted Codex Hook
  groups, Bootstrap/validation integration, manual fallback, bilingual docs,
  evals, and focused/canonical tests are complete. The isolated forward test
  passed and its manual-fallback discovery was fixed.
- Next action: commit the two repository changes, validate the exact
  RepoFoundry implementation revision in a clean worktree, archive EP-009, and
  create stacked pull requests.
- Open questions: none that change the selected route. Exact stable error
  labels and the minimal read-only Bash allowlist remain implementation detail.

## Context and Orientation

EngineeringSpecifications owns reusable normative content, Catalog metadata,
versions, dependency edges, scopes, descriptions, and digests. RepoFoundry
owns `scripts/spec_manager.py`, which fetches and locks selected content under
`docs/.engineering/` and materializes exact copies below
`docs/agent-guides/managed/`. `render_index()` produces the task routing map.

`scripts/foundryctl.py` owns the Codex Bootstrap, bundled templates in
`assets/`, `docs/.engineering/harness.json`, and Harness validation. The
current `assets/harness-agents.md` tells an Agent to inspect the generated
index, but missing task-time activation is only advisory.

This EP adds one generated repository Skill at
`.agents/skills/engineering-specs/`. Its self-contained
`scripts/spec_router.py` reads only the target repository's manifest, lock,
managed Markdown, and project-owned Spec references. It also handles Codex
Hook events defined by `.codex/hooks.json`. Runtime receipts are stored outside
the working tree, keyed by repository, Codex session, and turn, so they do not
pollute Git history or collide across turns.

An activation decision is either a non-empty set of selected Specification IDs
or an explicit `none` decision with a reason. It also records planned exact
paths or globs. `applies_to` determines candidates; Catalog descriptions and
the full Applicability sections remain the Agent's semantic decision surface.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/engineering-spec-management.md` | Existing installation, lock, routing, and ownership contract | Before changing resolver or Bootstrap behavior |
| `assets/harness-agents.md` | Root Codex instruction template and 100-line budget | Before changing the mandatory route |
| `scripts/foundryctl.py` | Bootstrap and Harness validation owner | Before adding generated files |
| `scripts/spec_manager.py` | Manifest, lock, managed content, and index contracts | Before reading target Spec state |
| `references/bootstrap.md` | Public Bootstrap and non-overwrite behavior | Before documenting migration |
| `https://learn.chatgpt.com/docs/build-skills` | Official repository Skill discovery and progressive disclosure | Before packaging the Router |
| `https://learn.chatgpt.com/docs/agent-configuration/agents-md` | Official instruction loading and precedence | Before changing AGENTS routing |
| `https://learn.chatgpt.com/docs/hooks` | Official Hook discovery, trust, events, and wire formats | Before implementing Hook handlers |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture gate: `not_required`.
- ADR references: [].
- Design document references: [].
- Architecture entrypoint: ``.

Research is not required because approved EngineeringSpecifications ESP-0007
already fixes the three-stage model: installation, file candidacy, then
task-intent activation. ESP-0009 fixes explicit optional installation.
Official current Codex documentation establishes repository Skills under
`.agents/skills`, root-to-working-directory AGENTS loading, and project Hooks
with `UserPromptSubmit`, `SubagentStart`, `PreToolUse`, and `Stop`. No unknown
external fact can change the route; implementation tests cover the remaining
wire details.

Architecture is not required because the repository owner explicitly selected
one generated Router Skill plus AGENTS and trusted Hooks. Accepted ADR-002
assigns the Codex project documentation Harness to the root workflow, and
ADR-005 keeps normative content in EngineeringSpecifications while RepoFoundry
owns fetching and routing. This change composes those decisions without moving
their boundary or choosing between credible alternatives.

The implementation constraints are:

- do not create one Skill per Specification or copy normative content into the
  RepoFoundry distribution;
- keep `AGENTS.md` at or below 100 physical lines and use it only as a hard
  route;
- parse manifest, lock, Hook input, paths, and managed content as untrusted
  boundary data;
- verify locked SHA-256 before injecting local content;
- do not fetch network content or run remote code at task time;
- preserve existing `.codex/hooks.json` bytes and report a merge conflict when
  the required Hook groups are absent;
- state that project Hooks require project trust and exact Hook review;
- treat tool Hooks as a strong Codex guardrail, not a universal Agent sandbox.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First, integrate the approved activation contract into the independent
EngineeringSpecifications model without changing normative files or Catalog
metadata. Then add generated Skill, UI metadata, runtime script, and Hook JSON
assets to RepoFoundry. Extend Bootstrap preflight/apply and validation so new
projects receive the files and existing custom Hook configurations fail with a
manual-merge instruction rather than being overwritten.

The runtime script will expose deterministic `candidates`, `activate`,
`status`, and `audit` commands and handle the four Hook events from stdin.
Prompt/subagent events capture the baseline repository state and inject a
compact route. PreToolUse denies mutation until the active turn has a valid
receipt, enforces path coverage, validates digests, and forces one retry after
full content injection. Stop compares current Git state with the prompt-time
baseline and requires the evidence handoff.

Finally, add unit and integration tests, validate the generated Skill with the
canonical Skill validator, forward-test it in an isolated repository, update
bilingual documentation and evals, run both repositories' canonical checks,
and archive this plan against the exact verified RepoFoundry revision.

## Milestones

### Milestone 1: Publish the activation adapter contract

EngineeringSpecifications contains approved ESP-0010 and bilingual model text
that names one Router Skill, the activation receipt, Hook enforcement, and its
trust boundary without changing Catalog schema or normative digests. Running
`python3 -B scripts/check.py` in that repository succeeds.

### Milestone 2: Generate and validate the Router surface

RepoFoundry Bootstrap previews and creates the project-local Skill and Hook
configuration. Existing custom Hook files remain byte-identical and block
apply until explicitly composed. Harness and Spec validation require a valid
Skill package, runtime script, AGENTS route, and required Hook groups.

### Milestone 3: Enforce turn activation behavior

The Router returns deterministic file candidates, validates explicit
activations/no-Spec decisions, records isolated receipts, includes dependency
closure, verifies local digests, blocks unactivated or uncovered edits,
injects content before the first write, and audits completion handoff. Focused
tests exercise successful and failing Hook wire examples.

### Milestone 4: Prove packaging and end-to-end behavior

Bilingual docs, evals, package contracts, generated-Skill validation, isolated
forward testing, and the canonical RepoFoundry check all pass. The exact
implementation revision is verified in a clean worktree and EP-009 is archived.

## Concrete Steps

From `/private/tmp/engineering-spec-router.tZUjXd/specifications`, update the
Proposal and model documents with `apply_patch`, then run:

```bash
python3 -B scripts/check.py
```

From `/private/tmp/engineering-spec-router.tZUjXd/foundry`, modify
`assets/`, `scripts/foundryctl.py`, focused tests, design docs, Bootstrap
reference, README files, Skill metadata, and evals with `apply_patch`. Run:

```bash
python3 -B -m unittest tests.test_spec_router tests.test_foundryctl tests.test_repository_contracts
python3 -B /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$TARGET_REPO/.agents/skills/engineering-specs"
python3 -B scripts/check.py
python3 -B engineering-execution-plan/scripts/epctl.py --repo . validate
```

Create an isolated target repository, bootstrap the Codex profile, drive Hook
events through JSON fixtures, and retain concise logs under this EP's
`artifacts/` directory.

## Validation and Acceptance

- [x] From EngineeringSpecifications, run `python3 -B scripts/check.py`;
  expect Proposal, bilingual docs, links, schema, digests, and existing tests
  to pass without a Catalog change. Evidence:
  `artifacts/engineering-specifications-check.txt`.
- [x] From RepoFoundry, run `python3 -B -m unittest
  tests.test_spec_router tests.test_foundryctl tests.test_repository_contracts`;
  expect candidate, activation, Hook, Bootstrap, non-overwrite, and packaging
  tests to pass. Evidence: `artifacts/focused-tests.txt`.
- [x] Validate the generated target Skill with `quick_validate.py`; expect a
  valid `engineering-specs` package with matching UI metadata. Evidence:
  `artifacts/generated-skill-validation.txt`.
- [x] Run an isolated end-to-end scenario; expect an unactivated edit to be
  denied, activation to return local paths and requirements, the first edit to
  receive injected content and retry, an uncovered path to be denied, and a
  complete handoff to pass. Evidence: `artifacts/router-e2e.txt`.
- [x] From RepoFoundry, run `python3 -B scripts/check.py`; expect every
  repository contract and test to pass. Evidence: `artifacts/repo-check.txt`.
- [x] From RepoFoundry, run `python3 -B
  engineering-execution-plan/scripts/epctl.py --repo . validate`; expect no
  EP errors. Evidence: `artifacts/epctl-validate.txt`.
- [ ] In a detached clean worktree at the implementation commit, rerun
  `python3 -B scripts/check.py`; expect exit 0 and no generated diff. Evidence:
  `artifacts/exact-revision-check.txt`.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Bootstrap remains preview-first and obtains the existing Harness lock before
writing. Missing Router files can be created repeatedly. Matching files are
preserved. A conflicting Skill path, symlink, or custom `.codex/hooks.json`
without the required groups stops all Bootstrap writes; the user merges Hooks
manually and reruns the same preview.

Runtime activation writes only turn-scoped state outside the working tree.
Repeated activation replaces the current turn's receipt atomically and may
extend its planned paths. A failed digest or malformed state makes no project
change. Deleting runtime state merely requires the Agent to activate again.

Rollback removes the generated Router Skill and the exact RepoFoundry Hook
groups after review, then restores the former AGENTS route. Normative managed
copies, manifest selection, and lock remain valid. Temporary worktrees and
runtime state are removed only after exact-revision validation.

## Progress

- [x] (2026-08-03T06:15:08Z) Created EP-009 with explicit not-required gates.
- [x] (2026-08-03T06:30:00Z) Filled the self-contained plan and recorded the
  approved ESP-0010 consumer activation contract before implementation.
- [x] (2026-08-03T07:05:00Z) Implemented one generated Router Skill, four
  Codex Hook groups, strict Bootstrap/validation ownership, turn-scoped
  receipts, candidate/activation/dependency routing, full local content
  injection, and changed-path/handoff auditing.
- [x] (2026-08-03T07:17:07Z) Added bilingual public documentation, Skill and
  Hook trust boundaries, eval coverage, generated-package validation, and 42
  focused tests; both repositories' canonical checks pass.
- [x] (2026-08-03T07:17:07Z) Forward-tested the generated Skill in an isolated
  Go repository, fixed the discovered manual-fallback gap with `begin` and
  `audit --message`, and retained its evidence.
- [ ] Commit exact revisions, rerun the RepoFoundry canonical check in a clean
  worktree, archive EP-009, push, and create stacked pull requests.

## Surprises & Discoveries

- (2026-08-03) Forward testing showed that an instruction-only fallback was
  not operational: `activate` correctly failed closed when no Hook had created
  a turn baseline. Resolution: add an explicit idempotent `begin` command and
  inline `audit --message`; keep implicit activation forbidden.
- (2026-08-03) A small Go naming task injected 44,032 bytes because the selected
  Go Spec depends on both Core Specs. This remains below the 128 KiB hard cap
  and guarantees complete context. Requirement-section injection is a future
  optimization that needs evidence and a separate contract.

## Decision Log

- (2026-08-03) Use one generated Router Skill, not one Skill per Specification.
  This keeps the Skill metadata set bounded and Specifications Agent-neutral.
- (2026-08-03) Require trusted project Hooks for Codex mechanical enforcement,
  while documenting AGENTS/Skill-only fallback for untrusted or disabled Hook
  environments. Official Codex trust behavior makes an unconditional claim
  inaccurate.
- (2026-08-03) Keep task activation state outside the Git working tree. The
  task handoff remains the evidence index; conformance still depends on the
  underlying tests and immutable revision.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The implementation establishes a reviewable activation receipt between
project-level installation and code mutation. One bounded Skill serves every
current and future Catalog category, while normative content remains
Agent-neutral. The first-write retry proves that locked local content reached
developer context before mutation; Stop auditing catches Bash paths that cannot
be fully predicted before execution.

The enforcement claim is deliberately scoped. In a trusted Codex project with
the exact reviewed Hooks enabled, Bash and `apply_patch` writes are mechanically
gated and all Git-visible deltas are audited at Stop. Other Agent hosts can
implement the same receipt contract, but RepoFoundry cannot guarantee that an
untrusted project, disabled Hook, or unrelated runtime invokes Codex Hooks.

### Knowledge promotion candidates

- Consider Requirement-level context extraction only after real task evidence
  defines how to preserve rationale, enforcement, and Verification closure.

## Interfaces and Dependencies

The generated runtime uses Python 3.10+ standard library and Git only. It must
not import RepoFoundry from its installation directory or access the network.

Stable user commands:

```text
spec_router.py candidates --path PATH ...
spec_router.py begin --session-id ID --turn-id ID [--prompt TEXT]
spec_router.py activate (--spec ID ... | --none --reason TEXT) --path PATH ...
spec_router.py status
spec_router.py audit [--message TEXT | --message-file PATH]
spec_router.py hook
```

Hook stdin follows current Codex JSON events. The script consumes
`session_id`, `turn_id`, `cwd`, `hook_event_name`, `tool_name`, `tool_input`,
`stop_hook_active`, and `last_assistant_message` when present. Hook stdout uses
`hookSpecificOutput.additionalContext`, `permissionDecision: deny`, or
`decision: block` only where the official event supports them.

Target repository inputs are `docs/.engineering/specs.json`,
`docs/.engineering/specs.lock.json`,
`docs/agent-guides/managed/index.md`, locked managed Markdown, and referenced
project Specifications. Every path is repository-relative and symlinks are
rejected.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-009_enforce-spec-task-activation/EXECPLAN.md`
- EngineeringSpecifications Proposal:
  `proposals/0010_task-activation-router.md` in the independent repository.
- EngineeringSpecifications check:
  `artifacts/engineering-specifications-check.txt`.
- Focused RepoFoundry tests: `artifacts/focused-tests.txt`.
- Generated Skill validation: `artifacts/generated-skill-validation.txt`.
- Isolated Router forward test: `artifacts/router-e2e.txt`.
- RepoFoundry canonical check: `artifacts/repo-check.txt`.
- EP validation: `artifacts/epctl-validate.txt`.
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-03T06:15:08Z — Initial plan created.
- 2026-08-03T06:30:00Z — Replaced all required placeholders with the selected
  activation architecture, milestones, commands, evidence, recovery, and
  interfaces before implementation.
- 2026-08-03T07:17:07Z — Updated current facts, validation evidence, forward
  test discoveries, manual fallback, retrospective, and stable interfaces.
