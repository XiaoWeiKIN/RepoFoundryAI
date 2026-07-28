---
schema_version: "2.1"
id: EP-001
title: "Add research and ADR lifecycle"
status: completed
latest_checkpoint:
created: 2026-07-28
updated: 2026-07-28
owner: ""
---

# Add research and ADR lifecycle

This ExecPlan is a bounded living document. Keep current truth synchronized.
Preserve historical events without rewriting them, and seal older events into
immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

Extend the execution-plan skill so a complex feature can move through a
repository-local, evidence-driven lifecycle:

1. create and conclude a bounded Research package;
2. synthesize its evidence into decision-ready conclusions;
3. create and explicitly decide an ADR when the choice is architecturally
   significant; and
4. create an ExecPlan only after Research and Architecture gates are satisfied
   or explicitly waived with reasons.

A user can observe the result by running `epctl` in an empty repository,
completing this lifecycle, and seeing invalid transitions rejected while legacy
v2.1 ExecPlans continue to validate, checkpoint and archive.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 — Agent workflow, compatibility and release.
- Current state: Research, Synthesis, ADR and v2.2 ExecPlan contracts,
  documentation and UI metadata are implemented. All 30 unit tests and static
  skill validation pass. The isolated fresh-Agent lifecycle also passed with
  `0 errors / 0 warnings` and no product-code changes. Installed and legacy
  skill copies exactly match the verified source. Implementation commit
  `23984ff` is published to `origin/main`, and the post-push tree was clean.
- Next action: Archive EP-001 as completed and publish the lifecycle-only
  archive commit.
- Open blockers: none.

## Context and Orientation

The repository root is the standalone `ExecutionPlan` skill. `SKILL.md` is the
runtime entry point. `assets/` contains Markdown templates copied into target
repositories. `references/` contains detailed rules loaded on demand.
`scripts/epctl.py` performs deterministic repository operations and validation.
`tests/test_epctl.py` is the regression suite; `evals/evals.json` tests Agent
routing and behavior.

The current v2.1 model has first-class ExecPlan, Task, Bugfix, Checkpoint and
technical-debt artifacts. `new-ep` immediately creates an active plan. Research
is currently only an execution activity recorded in
`Surprises & Discoveries`; ADRs are only knowledge-promotion candidates.

Terms:

- **Research package**: one bounded controller document, topic notes, raw
  artifacts and a concise Synthesis for a feature-level decision.
- **Research Gate**: either referenced Research is concluded or a fast-track
  reason explicitly states why formal Research is unnecessary.
- **Architecture Gate**: either referenced ADRs are accepted and current or an
  explicit reason states why no architectural decision is required.
- **ADR**: a stable repository-level record of one architecturally significant
  decision. Proposed ADRs are editable; decided ADR bodies are sealed.
- **Gate**: a mechanically validated prerequisite. Scripts validate structure
  and explicit status; the Agent remains responsible for semantic quality.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `SKILL.md` | Core routing and authorization rules | Before changing workflow |
| `scripts/epctl.py` | Existing IDs, locking, atomic writes and validators | Before implementation |
| `assets/execplan.md` | v2.1 schema that must remain readable | Before adding v2.2 |
| `references/checkpoints.md` | Bounded-root invariants | Before changing checkpoint validation |
| `tests/test_epctl.py` | Mechanical compatibility contract | During every milestone |
| `evals/evals.json` | Agent behavior contract | Before final validation |
| `README.md` | Public installation and usage guide | After CLI stabilizes |

Preserve these invariants:

- Existing v2.0 and v2.1 ExecPlans remain readable; v2.1 checkpoint and archive
  behavior must not regress.
- `EXECPLAN.md` remains self-contained even when it links Research and ADRs.
- Research raw evidence lives in `artifacts/`; `SYNTHESIS.md` is concise and
  decision-ready.
- Accepted or rejected ADR bodies are immutable; supersession changes metadata
  and points to a newer accepted ADR.
- Only explicit user or Decision Owner authorization may accept or reject an
  ADR. The script records the decision; it cannot infer authority.
- Small or already-decided work may use explicit Research/Architecture
  not-required reasons. Silent Gate bypass is invalid.
- Continue to use repository locks, high-water IDs, atomic file replacement,
  recoverable indexes and symlink protection.
- Use only the Python standard library and support Python 3.10+.

## Plan of Work

First add reusable templates and detailed references. A Research package will
contain `RESEARCH.md`, `SYNTHESIS.md`, optional `notes/`, and `artifacts/`.
ADRs will live at stable paths under `docs/adr/`. Root indexes will project
Research and ADR status.

Then extend `epctl.py` with R and ADR IDs, repository discovery, creation,
validation, transition, index and status operations. Add v2.2 ExecPlan
frontmatter and a required `Research and Architecture Inputs` section. `new-ep`
will require valid references or explicit not-required reasons. Existing plan
schemas will keep their current validation behavior.

Finally update the skill instructions, public README, examples, evals and UI
metadata. Add unit and forward tests that exercise a complete lifecycle,
negative gates, ADR supersession, immutability and legacy compatibility. Sync
the verified skill into the installed Codex location and publish the reviewed
commit to `origin/main`.

## Milestones

### Milestone 1: First-class Research and ADR contracts

Add assets for Research, Synthesis, ADR and their indexes; add lifecycle
references; define stable frontmatter, sections, states, Gate semantics and
directory layout. Extend `epctl init`, ID allocation and discovery without
breaking current artifacts. At the end, template rendering and repository
initialization tests will demonstrate the new paths and IDs.

### Milestone 2: Deterministic lifecycle and Plan gates

Implement Research creation/conclusion/cancellation, ADR creation/decision/
supersession, v2.2 ExecPlan creation, cross-reference validation, immutable
payload verification, aggregate status and index rebuilding. At the end, unit
tests will prove valid transitions succeed and invalid transitions fail without
partial mutation.

### Milestone 3: Agent workflow, compatibility and release

Update `SKILL.md`, references, README, evals and `agents/openai.yaml`. Run the
complete regression suite, quick skill validation and an isolated fresh-Agent
workflow. Verify the installed copy matches the source, archive this EP if all
acceptance criteria pass, then commit and push the implementation.

## Concrete Steps

Run all commands from `/Users/wangxiaowei1/x-otel/ExecutionPlan`.

1. Add templates and references with `apply_patch`. Keep `SKILL.md` below 500
   lines and put detailed Research/ADR rules in one-level references.
2. Extend `scripts/epctl.py` in small patches: constants and discovery first,
   creation and transitions second, validators and status last.
3. Extend `tests/test_epctl.py` after each mechanical contract. Run:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
     -s tests -p 'test_*.py' -v
   ```

   Expected: all existing and new tests pass.
4. Validate the skill:

   ```bash
   python3 -B \
     /Users/wangxiaowei1/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
   git diff --check
   jq empty evals/evals.json
   ```

   Expected: all commands exit 0.
5. In a fresh temporary repository, execute Research → Synthesis → accepted ADR
   → gated ExecPlan and run `epctl validate`. A fresh Agent must be able to
   perform the workflow from the revised skill without seeing this plan.
6. Sync the exact verified files to
   `/Users/wangxiaowei1/.codex/skills/execution-plan`, rerun validation there,
   archive EP-001 when complete, and publish the resulting commit.

## Validation and Acceptance

- [x] `epctl init` creates Research and ADR indexes/directories without
  overwriting existing content.
- [x] A Research package cannot conclude while required placeholders, open
  research questions or open blockers remain; a valid package seals its
  Synthesis and moves atomically to completed.
- [x] A decided ADR has a verifiable payload hash; acceptance/rejection records
  a Decision Owner, and supersession requires a newer accepted ADR.
- [x] `new-ep` rejects missing implicit gates, proposed/rejected/superseded ADRs
  and active Research; it accepts concluded Research plus current accepted ADRs
  or explicit not-required reasons.
- [x] A v2.2 ExecPlan restates implementation constraints and validates all
  references while remaining compatible with Checkpoint and strict archive.
- [x] Existing v2.0/v2.1 plans and the previous 22 tests remain supported.
- [x] `status`, `reindex` and `validate --fix-index` cover Research, ADR,
  ExecPlan and Bugfix projections.
- [x] `quick_validate.py`, `git diff --check`, JSON parsing and the complete unit
  suite exit 0.
- [x] An isolated fresh-Agent workflow produces valid Research, Synthesis, ADR
  and ExecPlan artifacts without changing unrelated product files.
- [x] Source and installed skill copies match, and the implementation Git tree
  was clean after publishing.

## Idempotence and Recovery

`init`, `validate`, `status` and `reindex` remain safe to repeat. New creation
commands allocate high-water IDs; failed operations may leave gaps but never
reuse an ID. Multi-file transitions must save original text and indexes, use
atomic replacement, and restore them on ordinary exceptions.

Do not rewrite existing v2.1 artifacts. New v2.2 behavior is selected by schema
and explicit frontmatter. If a new validator causes a regression, retain the
new assets and revert the specific script patch with `apply_patch`; do not use
`git reset --hard`. If index projection is interrupted, run
`python3 scripts/epctl.py --repo . validate --fix-index`.

Forward tests run only in newly allocated temporary repositories. Installed
skill synchronization happens only after source validation; the standalone Git
repository remains the recoverable source of truth.

## Progress

- [x] (2026-07-28T06:25:30Z) Created EP-001 for the approved lifecycle upgrade.
- [x] (2026-07-28T06:25:30Z) Converted the approved analysis into explicit
  contracts, milestones, acceptance criteria and compatibility constraints.
- [x] (2026-07-28T06:50:48Z) Implemented Milestone 1 assets, references,
  Research/ADR indexes, ID allocation and repository initialization.
- [x] (2026-07-28T06:50:48Z) Implemented Milestone 2 transitions, v2.2 Gates,
  sealed payload validation, aggregate status and recoverable index rebuilds.
- [x] (2026-07-28T06:50:48Z) Expanded the regression suite from 22 to 28 tests;
  all pass with Python bytecode writes disabled.
- [x] (2026-07-28T07:01:36Z) Updated `SKILL.md`, README, progressive references,
  17 behavior evals and generated `agents/openai.yaml`; quick validation, JSON
  parsing and whitespace checks pass.
- [x] (2026-07-28T07:01:36Z) Expanded compatibility and four-index recovery
  coverage to 30 passing unit tests.
- [x] (2026-07-28T07:15:45Z) A context-isolated Agent completed Research →
  sealed Synthesis → explicitly accepted ADR → gated ExecPlan in a disposable
  product repository. `epctl validate` returned 0 errors / 0 warnings, the
  baseline behavior assertion passed, and all four product/test hashes were
  unchanged.
- [x] (2026-07-28T07:17:06Z) Synchronized the verified skill files to
  `/Users/wangxiaowei1/.codex/skills/execution-plan` and the legacy
  `x-otel/datafox-skill/execution-plan` mirror. Directory parity, quick
  validation and the installed copy's 30-test suite all pass.
- [x] (2026-07-28T07:17:59Z) Completed Milestone 3 and published implementation
  commit `23984ff` to `origin/main`; local HEAD and `origin/main` matched with a
  clean post-push working tree.

## Surprises & Discoveries

- 2026-07-28T06:25:30Z — The current state store uses an open-ended
  `high_water` map, so adding `R` and `ADR` prefixes does not require a state
  schema migration. Evidence: `scripts/epctl.py:205-229`.
- 2026-07-28T06:25:30Z — Existing frontmatter parsing already accepts flat JSON
  string arrays, which can represent `research_refs` and `adr_refs` without a
  YAML dependency. Evidence: `scripts/epctl.py:372-428`.
- 2026-07-28T06:50:48Z — The existing Checkpoint and strict archive tests
  exercise newly generated v2.2 fast-track plans without special cases, so the
  Gate schema composes with bounded history instead of forking it. Evidence:
  `tests/test_epctl.py`.
- 2026-07-28T07:15:45Z — A fresh Agent kept Research evidence in focused
  notes/artifacts, sealed a concise Synthesis, preserved explicit decision
  authority, and restated the resulting constraints in a 683-line root EP.
  The result stayed below the 800-line checkpoint warning and required no
  upstream artifact to identify its next action.

## Decision Log

- 2026-07-28 — Keep one `$execution-plan` skill as the workflow entry while
  storing Research, ADR and ExecPlan as independent canonical artifacts.
  Rationale: this preserves simple routing and progressive disclosure without
  coupling their lifecycles. Author: Codex; approved by the user.
- 2026-07-28 — Require explicit not-required reasons for fast-track Research or
  Architecture gates. Rationale: small work remains possible while silent
  bypasses become mechanically visible. Author: Codex; approved by the user.
- 2026-07-28 — Allow Agents to author proposed ADRs; require explicit user or
  Decision Owner authorization for accepted/rejected outcomes. Rationale:
  architectural judgment stays at the human control layer. Author: Codex;
  approved by the user.
- 2026-07-28 — Store Synthesis separately from the Research controller and raw
  evidence. Rationale: ADR authors receive a bounded decision input while audit
  trails remain available on demand. Author: Codex; approved by the user.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The skill now supports the complete Research → Synthesis → ADR → ExecPlan
lifecycle:

- complex work defaults to a bounded Research package with explicit questions,
  focused notes, externalized raw evidence and a separately sealed Synthesis;
- Agents may propose ADRs, while accepted/rejected transitions record explicit
  decision authority and seal the decided body;
- v2.2 ExecPlans require valid Research/Architecture Gates and restate upstream
  conclusions and consequences;
- `status`, `reindex`, `validate --fix-index`, high-water IDs and transactional
  rollback cover the new artifacts;
- Checkpoint continues to bound a growing root EP, while v2.0/v2.1 plans remain
  readable and usable.

Evidence includes 30 passing unit tests, 17 behavior evals, two successful
`quick_validate.py` checks on consumer copies, exact directory parity, and a
context-isolated full lifecycle with `0 errors / 0 warnings`. The forward Agent
preserved product hashes and produced a self-contained implementation plan
without reading this EP.

No known functional gap remains in the approved scope. Semantic evidence
quality and actual ADR authority still require Agent judgment; the script
deliberately validates explicit structure and recorded status rather than
pretending it can infer human intent.

### Knowledge promotion candidates

- The reusable lifecycle, Gate and bounded-document rules are already promoted
  into `SKILL.md`, `references/`, templates, tests and evals in this change.
  No additional `AGENTS.md` rule is needed.

## Interfaces and Dependencies

The public CLI will retain existing commands and add:

```text
new-research --slug SLUG --title TITLE [--owner OWNER]
archive-research R-NNN --outcome concluded|cancelled [--reason REASON]
new-adr --slug SLUG --title TITLE [--research R-NNN ...]
decide-adr ADR-NNN --outcome accepted|rejected --decision-maker NAME
supersede-adr ADR-OLD --by ADR-NEW
new-ep ... [--research R-NNN ...] [--adr ADR-NNN ...]
           [--research-not-required-reason TEXT]
           [--architecture-not-required-reason TEXT]
```

`epctl.py` remains a single Python 3.10+ standard-library script. Public artifact
IDs are `R-NNN`, `ADR-NNN`, `EP-NNN`, `TASK-NNN`, `CP-NNN`, `BF-NNN` and
`TD-NNN`. Research and ADR frontmatter use only top-level scalars and flat JSON
string arrays.

Decided ADR and sealed Synthesis integrity uses SHA-256 over Markdown body,
matching the existing Checkpoint approach.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-001_add-research-adr-lifecycle/EXECPLAN.md`
- Full logs, traces, screenshots and generated evidence belong under
  `artifacts/`; keep only concise observations and paths here.
- Approved design sources:
  `https://openai.com/index/harness-engineering/`,
  `https://developers.openai.com/cookbook/articles/codex_exec_plans`, and
  `https://adr.github.io/madr/`.

## Revision Notes

- 2026-07-28T06:25:30Z — Initial plan created.
- 2026-07-28T06:25:30Z — Replaced all required placeholders with the approved
  Research → Synthesis → ADR → ExecPlan implementation contract.
- 2026-07-28T06:50:48Z — Completed Milestones 1 and 2; aligned the public
  `supersede-adr ADR-OLD --by ADR-NEW` contract and advanced the working set to
  documentation and forward validation.
- 2026-07-28T07:15:45Z — Accepted the isolated forward test as evidence for
  semantic Gate propagation and self-containment; advanced to installation
  parity and release.
- 2026-07-28T07:17:06Z — Verified exact parity for all managed skill files in
  both consumer locations and advanced to the two-step implementation/lifecycle
  publication sequence.
- 2026-07-28T07:17:59Z — Published implementation commit `23984ff`, verified
  `HEAD == origin/main` and a clean tree, completed all acceptance criteria and
  prepared EP-001 for strict archive.
