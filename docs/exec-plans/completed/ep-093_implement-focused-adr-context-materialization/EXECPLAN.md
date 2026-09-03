---
schema_version: "2.8"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-093
title: "Implement focused ADR context materialization"
status: completed
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "Accepted ADR-059, approved DD-012 revision 2, and reproducible DataFox corpus measurements fully determine the implementation route; no unresolved factual question can change the selected architecture."
adr_refs: ["ADR-014", "ADR-016", "ADR-058", "ADR-059"]
adr_constraint_refs: ["ADR-014#C-001", "ADR-014#C-002", "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006", "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004", "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008", "ADR-058#C-001", "ADR-058#C-002", "ADR-058#C-003", "ADR-058#C-004", "ADR-058#C-005", "ADR-058#C-006", "ADR-058#C-007", "ADR-058#C-008", "ADR-058#C-009", "ADR-059#C-001", "ADR-059#C-002", "ADR-059#C-003", "ADR-059#C-004", "ADR-059#C-005", "ADR-059#C-006", "ADR-059#C-007", "ADR-059#C-008", "ADR-059#C-009", "ADR-059#C-010"]
adr_evidence: ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7", "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb", "ADR-058@sha256:7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b", "ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc"]
design_refs: ["docs/design-docs/artifact-metadata-contract.md", "docs/design-docs/reversible-adr-effect.md", "docs/design-docs/dd-012_lossless-adr-context-compaction.md"]
design_evidence: ["DD-012@rev:2@sha256:a15abeda142891ecd63f218a629532725a85d1c492d0a662b700bf7abe5e6fab"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: satisfied
architecture_decision_gate_reason: ""
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision: "git:6d0529f42e8cd9f5ee040eadfd6749f5ca475bc1"
verification_evidence: ["local: python3 -B scripts/check.py; 69 EP tests and 119 RepoFoundry/Harness/installer/spec tests passed", "github-pr: https://github.com/XiaoWeiKIN/RepoFoundryAI/pull/39", "github-ci: https://github.com/XiaoWeiKIN/RepoFoundryAI/actions/runs/33721414909", "github-release: https://github.com/XiaoWeiKIN/RepoFoundryAI/releases/tag/v0.8.1", "install: package sha256 ce7804d287fe29211484e4f3689a7aa002e09595b2fc7c3b6e99c36006c10295; archive sha256 a292f1ddc16313371469b321795dbe220975ae1c6888dc70b3510ab59dd9362b", "datafox: producer 0.8.1; four focused capsules validate 29 ADRs in 3828-8509 bytes; 51-source manifest sha256 77574e40438c808a855b7064aa527f875fc3f542883bd1a3ceead7eb33f59ed5; Decision Views 0 errors/0 warnings"]
archive_sha256: 1238efa9d741e94167e17cbfddb5b9e24b4fd741961e7797fe48094450768259
created: 2026-09-03
updated: 2026-09-03
author: "Codex"
owner: "Wangxiaowei1"
---

# Implement focused ADR context materialization

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry users can explicitly compile a small, exact ADR task context without
pretending that the omitted architecture disappeared. After this plan,
`decision-capsule --materialization focused --constraint ... --focus-reason ...`
will validate the same complete current-effect closure as the existing command,
then materialize only requested constraint owners and recursively downstream scoped
amenders. The existing invocation remains byte-for-byte compatible.

The capability ships as RepoFoundry 0.8.1, is installed into the local Codex host,
and is applied to DataFox. Success is observable when four OQL focuses validate the
same 29 ADRs but materialize one or two ADRs into capsules below 32 KiB, while no
DataFox ADR lifecycle or source byte changes.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: all implementation and rollout milestones are complete.
- Current state: RepoFoundry 0.8.1 is merged, released, installed into Codex, and
  applied to DataFox. Four released focused capsules stay below 32 KiB while
  validating the same 29-ADR closure; DataFox ADR bytes are unchanged.
- Next action: run final repository validation and archive EP-093 against the
  verified release revision.
- Open questions: none that can change the approved route.

## Context and Orientation

The current resolver in `engineering-execution-plan/scripts/epctl.py` builds a full
current-effect context through `resolve_decision_context()`. The compiler then calls
`expanded_decision_constraint_refs()`, whose reverse traversal of every
`amends_constraints` target expands one DataFox OQL row to 20 ADR owners. Finally,
`compile_decision_capsule()` emits every resolved Decision Statement.

Revision 2 keeps that resolver as the validation boundary. A new focused selection
policy operates on its in-memory result and traverses only selected row -> current
scoped amender rows. It does not follow an included amender back to unrelated old
targets. The CLI remains read-only; focus data is ephemeral JSON/Markdown.

Primary code and contract surfaces are:

- `engineering-execution-plan/scripts/epctl.py` — resolver, compiler, CLI parser;
- `engineering-execution-plan/tests/test_epctl.py` — exact-byte and graph fixtures;
- `tests/test_foundryctl.py`, `tests/test_installer.py`, and
  `tests/test_repository_contracts.py` — distribution and compatibility coverage;
- `VERSION`, root READMEs and Skill references — 0.8.1 public surface;
- `/Users/wangxiaowei1/x-otel/datafox` — real mixed strict/legacy integration corpus.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/adr/adr-059_focused-adr-context-materialization.md` | Accepted focused-mode authority and C-001–C-010 | Before code or test changes |
| `docs/design-docs/dd-012_lossless-adr-context-compaction.md` | Approved algorithm, output, failures and rollout | Before implementation and review |
| `docs/adr/adr-058_lossless-adr-context-compaction.md` | Revision 1 exact/complete compatibility baseline | Before changing compiler output |
| `engineering-execution-plan/scripts/epctl.py` | Canonical implementation owner | During Milestone 1 |
| `engineering-execution-plan/tests/test_epctl.py` | Executable public CLI contract | During Milestones 1–2 |
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Release/install/upgrade compatibility | Before Milestone 3 |

Task invariants are: complete mode remains the default and byte-stable; focus is
explicit and partial; the full closure is validated before filtering; materialized
bytes remain exact; ambiguity and overflow fail without output; no command mutates
ADR lifecycle; no persistent schema migration is introduced.

## Research and Architecture Inputs

- Research gate: `not_required` because the accepted decision, approved design and
  reproducible DataFox measurements fully determine the route. Remaining work is
  implementation verification, not fact discovery.
- Architecture decision gate: `satisfied` by accepted ADR-059, which amends only
  ADR-058 C-006 and preserves the revision 1 authority boundary.
- Architecture compliance: `applicable`. ADR-014 controls governed metadata and
  seals; ADR-016 controls immutable decisions/current effect; ADR-058 controls
  lossless context; ADR-059 authorizes explicit focused materialization.
- ADR references: ["ADR-014", "ADR-016", "ADR-058", "ADR-059"].
- ADR constraint references: ["ADR-014#C-001", "ADR-014#C-002",
  "ADR-014#C-003", "ADR-014#C-004", "ADR-014#C-005", "ADR-014#C-006",
  "ADR-016#C-001", "ADR-016#C-002", "ADR-016#C-003", "ADR-016#C-004",
  "ADR-016#C-005", "ADR-016#C-006", "ADR-016#C-007", "ADR-016#C-008",
  "ADR-058#C-001", "ADR-058#C-002", "ADR-058#C-003", "ADR-058#C-004",
  "ADR-058#C-005", "ADR-058#C-006", "ADR-058#C-007", "ADR-058#C-008",
  "ADR-058#C-009", "ADR-059#C-001", "ADR-059#C-002", "ADR-059#C-003",
  "ADR-059#C-004", "ADR-059#C-005", "ADR-059#C-006", "ADR-059#C-007",
  "ADR-059#C-008", "ADR-059#C-009", "ADR-059#C-010"].
- ADR evidence:
  ["ADR-014@sha256:bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7",
  "ADR-016@sha256:448a34be4804a9e60e7ce2e6e78158d7c45d462326b99d456fe533a1513590fb",
  "ADR-058@sha256:7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b",
  "ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc"].
- Design references: ["docs/design-docs/artifact-metadata-contract.md",
  "docs/design-docs/reversible-adr-effect.md",
  "docs/design-docs/dd-012_lossless-adr-context-compaction.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.
- Approved design evidence is
  `DD-012@rev:2@sha256:a15abeda142891ecd63f218a629532725a85d1c492d0a662b700bf7abe5e6fab`.
- The implementation may add a focused output object but must not change the default
  complete Markdown, JSON fields, source costs, budget result, or capsule digest.
- The focused manifest records all validated source digests and a canonical closure
  SHA-256; only materialized source bodies count toward the capsule body budget.
- Whole-document focus and broad current amendments without stable constraint scope
  fail closed. This limitation is accepted and does not block release.
- No Benchmark Scenario is required: exact bytes, graph traversal, compatibility and
  failure behavior are deterministic functional contracts covered by fixtures and
  real-corpus integration, not environment-sensitive performance measurements.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| ADR-014#C-001 | Preserve metadata on ADR, Design and EP; focused output has explicit schema fields. | metadata validators and JSON golden test |
| ADR-014#C-002 | Represent the validated closure as a digest-bound manifest rather than unbound evidence. | canonical-manifest tamper test |
| ADR-014#C-003 | Keep approval and decision actors only in lifecycle artifacts; never infer them from author/owner. | approval seals plus lifecycle regression tests |
| ADR-014#C-004 | Validate all sealed ADR metadata before focus materialization. | drift and missing-field fixtures |
| ADR-014#C-005 | Leave sealed legacy schemas unchanged; reject unsafe legacy focus. | legacy compatibility and focus-failure tests |
| ADR-014#C-006 | Use repository paths and source digests as provenance; add no decorative headers. | repository contract checks |
| ADR-016#C-001 | Focus reads decided payloads and never changes decision outcome or body. | before/after ADR digest equality |
| ADR-016#C-002 | Add no effect transition path to capsule compilation. | mutation-call audit tests |
| ADR-016#C-003 | Reuse currentness resolution so under-review chains cannot enter focus. | non-current graph fixtures |
| ADR-016#C-004 | Retired constraints remain excluded by complete resolver validation. | retired-seed/amender rejection tests |
| ADR-016#C-005 | Superseded decisions remain historical and cannot satisfy focused current input. | superseded graph fixture |
| ADR-016#C-006 | Preserve active-plan review reporting; focused output cannot clear plan blockers. | EP regression tests |
| ADR-016#C-007 | Resolve only recursively current accepted ADRs and scoped amendments. | full/focused closure parity tests |
| ADR-016#C-008 | Do not rewrite schemas 1–1.3 or their payload digests. | legacy repository suite |
| ADR-058#C-001 | Mark every capsule non-normative and keep ADR sources immutable. | output header and source digest audit |
| ADR-058#C-002 | Run the complete dependency/amendment resolver before either materializer. | validated-closure parity fixtures |
| ADR-058#C-003 | Copy strict source sections/rows exactly; complete legacy fallback stays unchanged. | CRLF, Unicode, substring and legacy tests |
| ADR-058#C-004 | Preserve budget reasons and fail without summary, truncation or adaptive omission. | boundary and overflow diagnostics |
| ADR-058#C-005 | Do not change Decision View registry, projections or mutation flow. | view regression and reindex tests |
| ADR-058#C-006 | Extend the ephemeral capsule with an explicit focused materialization contract. | CLI/JSON/Markdown golden tests |
| ADR-058#C-007 | Preserve independent health metrics and no lifecycle mutation. | health regression tests |
| ADR-058#C-008 | Leave consolidation preview-only and separate from focus. | before/after corpus digest test |
| ADR-058#C-009 | Ship through 0.8.1 and preserve upgrade/downgrade readability. | installer and DataFox upgrade tests |
| ADR-059#C-001 | Validate the same full current-effect closure before focused filtering. | complete/focused validated source equality |
| ADR-059#C-002 | Keep default complete output byte-for-byte compatible with 0.8.0. | frozen 0.8.0 golden fixture |
| ADR-059#C-003 | Require constraints and focus reason; declare `focused_partial`; never auto-fallback. | argument and overflow tests |
| ADR-059#C-004 | Traverse requested row -> downstream scoped amenders and include each amender's full row set without reverse-target expansion. | branching graph fixture |
| ADR-059#C-005 | Emit exact participating bytes, full validated source metadata and deterministic closure SHA-256. | exact-byte and canonical-digest tests |
| ADR-059#C-006 | Report validated/materialized/omitted ADRs and unmaterialized relations with hydration guidance. | human/JSON golden tests |
| ADR-059#C-007 | Fail focused output for legacy requested boundaries and ambiguous broad amendments. | legacy and unscoped-amendment fixtures |
| ADR-059#C-008 | Never truncate, summarize, omit selected sources, raise budget or change mode. | overflow and no-mutation audit |
| ADR-059#C-009 | Keep focus non-normative and unable to mutate or prove complete compliance. | warning contract and lifecycle audit |
| ADR-059#C-010 | Release additively with no persisted schema migration and safe 0.8.0 downgrade. | install/upgrade/downgrade/DataFox integration |

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate; deterministic contract and corpus tests apply. | — |

## Plan of Work

First, isolate materialization policy from the existing complete resolver. Add a
focused directional selector, canonical validated-closure manifest, explicit output
partition and ambiguity checks. Thread `materialization` and `focus_reason` through
the compiler and CLI while leaving the default call path untouched.

Second, encode the contract in unit/integration fixtures. Freeze current complete
output before implementation, test recursive downstream amendments and reverse
non-expansion, exact bytes, closure digest drift, partial warnings, legacy/broad
ambiguity, budgets and zero repository mutation. Run the full repository suite.

Third, update distribution documentation and version to 0.8.1, verify installer and
Harness upgrade compatibility, commit the final verified tree, merge through the
repository review path, tag and publish the release, then install the immutable
release into the local Codex host.

Finally, preview/apply the DataFox Harness producer upgrade, run focused OQL capsules
for four representative constraints, compare validated/materialized partitions and
bytes, validate the DataFox Harness, and prove that no ADR lifecycle or source bytes
changed.

## Milestones

### Milestone 1: Focused compiler behavior exists

`epctl.py` accepts explicit focused materialization, performs full validation plus
directional selection, emits the closure/omission contract, and fails on ambiguity.
Targeted `test_epctl.py` tests pass while existing complete output remains unchanged.

### Milestone 2: Repository and distribution contracts pass

All RepoFoundry tests pass, documentation describes complete/focused semantics,
`VERSION` is 0.8.1, and installer/upgrade/downgrade tests prove no persisted schema
migration or project-content overwrite.

### Milestone 3: RepoFoundry 0.8.1 is published and installed

The verified change is merged, tagged `v0.8.1`, published as a GitHub Release, and
installed locally. `repofoundry --version` reports 0.8.1 and the active Codex Skill
resolves to the immutable 0.8.1 installation.

### Milestone 4: DataFox integration proves bounded focus

DataFox upgrades from producer 0.8.0 to 0.8.1 without conflicts. Four OQL focused
capsules validate 29 ADRs, materialize one or two ADRs, stay below 32 KiB, and leave
all ADR lifecycle/source bytes unchanged. Harness and view validation pass subject
only to already documented unrelated warnings/errors.

## Concrete Steps

1. In `/Users/wangxiaowei1/x-otel/EngineeringPlan-scoped-adr-context`, edit
   `engineering-execution-plan/scripts/epctl.py` and
   `engineering-execution-plan/tests/test_epctl.py` with `apply_patch`.
2. Run
   `python3 -m unittest discover -s engineering-execution-plan/tests -p 'test_epctl.py' -v`;
   expect all execution-plan tests to pass.
3. Update versioned public surfaces and run `python3 -B scripts/check.py`; expect
   `all integrity checks passed`.
4. Commit the verified tree, publish via the repository's normal PR/release workflow,
   and install the released source with `install.py --version 0.8.1 --host codex`.
5. In `/Users/wangxiaowei1/x-otel/datafox`, run the released upgrade preview, inspect
   conflicts, apply only if clear, then validate the Harness.
6. Run focused capsules for `ADR-049#C-001`, `C-003`, `C-009`, and `C-010` + `C-011`;
   record full validated count, materialized IDs, bytes and SHA-256.
7. Update this living document, execute final verification on the committed revision,
   and archive EP-093 with repository and release evidence.

## Validation and Acceptance

- [x] From the RepoFoundry worktree, run the targeted `test_epctl.py` suite; expect
  all tests to pass, including focused traversal, exact bytes, compatibility,
  ambiguity and budgets.
- [x] Run `python3 -B scripts/check.py`; expect every suite and repository validator
  to pass with no errors.
- [x] Run `git diff --check`; expect no whitespace errors.
- [x] Run `repofoundry --version`; expect `0.8.1` from the released immutable install.
- [x] Preview and apply the DataFox 0.8.1 Harness upgrade; expect no conflict and
  `producer_version: 0.8.1` while Harness schema remains compatible.
- [x] Run four DataFox focused OQL capsules; expect 29 validated ADRs, one or two
  materialized ADRs, each context below 32,768 bytes, and deterministic digests.
- [x] Compare DataFox ADR source/lifecycle digest manifests before and after; expect
  exact equality and no additional retirement/supersession.
- [x] Run DataFox RepoFoundry Harness and Decision View validation; expect no new
  error attributable to the 0.8.1 upgrade.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`; do not
pre-fill these fields while the plan is active.

## Idempotence and Recovery

Focused capsule compilation is read-only and deterministic; retry recomputes the
closure from repository bytes. Complete mode remains the recovery path for an
ambiguous focus. No overflow may mutate arguments or output a partial body.

The implementation stays in the isolated worktree and never resets the user's dirty
RepoFoundry or DataFox trees. Test failures are fixed forward. Release creation is
performed only after the target commit is verified; an existing tag/release is
inspected rather than overwritten. The installer atomically switches versions and
retains 0.8.0 for rollback. DataFox upgrade is preview-first and its CLI rolls back
managed changes on validation failure; unrelated dirty files are preserved.

No cleanup deletes Decision Views or ADR sources. Downgrade to 0.8.0 merely removes
access to the ephemeral focused flag and leaves all repository state readable.

## Progress

- [x] (2026-09-03T04:37:04Z) Wangxiaowei1 approved DD-012 revision 2 and accepted
  ADR-059; immutable evidence and decision seal were generated.
- [x] (2026-09-03T04:37:46Z) EP-093 created with complete ADR/Design closure.
- [x] (2026-09-03T05:01:19Z) Implemented focused materialization, froze the 0.8.0
  complete-mode contract, documented 0.8.1, and passed `scripts/check.py` with 69
  Execution Plan tests and 119 distribution/Harness/installer/spec tests.
- [x] (2026-09-03T05:01:19Z) Ran the new compiler read-only against DataFox before
  release: all four focuses validated the same 29 ADRs and materialized one or two
  ADRs in 3,822–8,503 bytes.
- [x] (2026-09-03T06:08:51Z) Merged PR #39 at release revision `6d0529f`, observed
  passing Python 3.10, Python 3.14 and aggregate CI gates, and published v0.8.1.
- [x] (2026-09-03) Installed the immutable GitHub Release into Codex;
  `repofoundry --version` reports 0.8.1 and the active package SHA-256 is
  `ce7804d287fe29211484e4f3689a7aa002e09595b2fc7c3b6e99c36006c10295`.
- [x] (2026-09-03T06:15:04Z) Upgraded DataFox from producer 0.8.0 to 0.8.1 with
  only `docs/.engineering/harness.json` changed, replayed all four focuses, and
  completed the project Engineering Specifications audit.

## Surprises & Discoveries

- The existing constraint selector is not merely retaining too many Decision
  Statements: reverse traversal of an amender's full target list expands one OQL row
  to 20 constraint-owning ADRs. Directional selection is therefore required before
  source materialization.
- The final auditable header and omission manifest add roughly two KiB over the
  design probe, but the largest representative DataFox focus is still only 8,503
  bytes, well below the 32,768-byte default budget.

## Decision Log

- 2026-09-03, Codex: use one EP for implementation, release and DataFox integration
  because the user-visible completion boundary is a released tool proven against the
  target corpus; a code-only merge would not satisfy the approved rollout.
- 2026-09-03, Codex: use deterministic test/integration evidence rather than an
  Engineering Benchmark Scenario because byte identity and closure membership are
  pure functions of fixed repository bytes.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry 0.8.1 now separates complete current-effect validation from explicit
focused materialization. The default complete output remains frozen to the 0.8.0
contract. Focused output is exact, partial, digest-bound and fail-closed; it adds no
persistent schema or ADR lifecycle authority.

The production-scale DataFox result confirms that file count was not the right
compression target. Its OQL View still validates all 29 current ADRs, while the four
representative tasks materialize only ADR-049 alone or ADR-049 with one downstream
amender. Final capsules are 3,828–8,509 bytes instead of the 112,668-byte selected
complete context. All seven Decision Views validate with zero errors and warnings.

DataFox's complete `epctl validate` still reports six unrelated pre-existing errors:
one changed EP-091 checkpoint seal and five EP-092 blocker/status errors. The 0.8.1
upgrade introduced none of them; Harness validation has zero errors, and the
51-source ADR byte manifest stayed exactly
`77574e40438c808a855b7064aa527f875fc3f542883bd1a3ceead7eb33f59ed5` before and
after migration.

### Knowledge promotion candidates

- If focused hydration proves useful across repositories, add a concise progressive
  ADR-context example to the public RepoFoundry documentation after this EP.

## Interfaces and Dependencies

- `compile_decision_capsule(context, constraint_values, *, budget_bytes,
  budget_reason, materialization="complete", focus_reason="")` remains callable by
  existing code without behavior changes.
- A focused selector consumes only the validated `resolve_decision_context()` result
  and returns selected refs, materialized ADR IDs and unmaterialized relations.
- The canonical closure manifest uses Python standard-library JSON and SHA-256; no
  new runtime dependency is allowed.
- CLI flags are `--materialization {complete,focused}` and `--focus-reason TEXT`.
- Focused JSON keeps the existing envelope and adds focused-only fields/object;
  complete JSON and Markdown remain unchanged.
- RepoFoundry 0.8.1 remains compatible with Harness schema 3 and Decision View
  registry schema 1.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-093_implement-focused-adr-context-materialization/EXECPLAN.md`
- Approved design: `DD-012@rev:2@sha256:a15abeda142891ecd63f218a629532725a85d1c492d0a662b700bf7abe5e6fab`
- Accepted decision: `ADR-059@sha256:9feddb44011fafc361b77f59ced5242fa6c53f3c90612179a2fb8db50288adbc`
- Release notes: `artifacts/release-notes.md`.
- Pull request: `https://github.com/XiaoWeiKIN/RepoFoundryAI/pull/39`.
- CI: `https://github.com/XiaoWeiKIN/RepoFoundryAI/actions/runs/33721414909`.
- Release: `https://github.com/XiaoWeiKIN/RepoFoundryAI/releases/tag/v0.8.1`, tag
  and target commit `6d0529f42e8cd9f5ee040eadfd6749f5ca475bc1`.
- Install: GitHub Release archive SHA-256
  `a292f1ddc16313371469b321795dbe220975ae1c6888dc70b3510ab59dd9362b`;
  package SHA-256
  `ce7804d287fe29211484e4f3689a7aa002e09595b2fc7c3b6e99c36006c10295`.
- Released DataFox capsules: C-001 = 3,828 bytes / SHA-256 `9faaa66f33940d18` /
  ADR-049; C-003 = 8,319 / `e0fbc17493b945e5` / ADR-049 + ADR-057; C-009 =
  8,509 / `35fca63121c3f820` / ADR-049 + ADR-056; C-010 + C-011 = 8,194 /
  `9a10004dc5f97933` / ADR-049 + ADR-050. All validate 29 ADRs with closure SHA-256
  `79fd2f7c1ddde7140d51bd9c83fe4a9a3fc1763937d20796432d7aa03fe8dc87`.
- DataFox project Spec audit: one covered changed path,
  `docs/.engineering/harness.json`; zero errors, zero uncovered paths, and all five
  Governed handoff labels present.

## Revision Notes

- 2026-09-03T04:37:46Z — Initial plan created.
- 2026-09-03 — Filled the self-contained implementation, compatibility, release and
  DataFox integration contract before production code changes.
- 2026-09-03T05:01:19Z — Completed compiler/docs/test implementation and recorded
  the passing repository suite plus bounded DataFox pre-release measurements.
- 2026-09-03T06:15:04Z — Recorded the merged release, immutable installation,
  DataFox migration, focused capsule measurements, ADR byte equality and explicit
  pre-existing validation exceptions; all acceptance items are satisfied.
