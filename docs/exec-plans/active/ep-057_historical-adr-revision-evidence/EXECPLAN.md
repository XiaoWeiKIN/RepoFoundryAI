---
schema_version: "2.7"
metadata_schema: "1"
artifact_type: exec-plan
id: EP-057
title: "Support historical ADR revision evidence"
status: active
latest_checkpoint:
research_refs: []
research_gate: not_required
research_gate_reason: "Datafox EP-051 and EP-052 provide a reproduced compatibility failure, and the recovered ADR-018 Git blob proves the exact historical payload revision; no unresolved fact can change the implementation route."
adr_refs: []
adr_constraint_refs: []
adr_evidence: []
design_refs: ["docs/design-docs/repo-foundry-versioning-and-migrations.md", "docs/design-docs/engineering-workflow-packaging.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_decision_gate: not_required
architecture_decision_gate_reason: "The existing Engineering Execution Plan contract already requires completed and cancelled EPs to retain their original ADR digests, and the repository-owned immutable revision resolver restores that accepted behavior without selecting a new architecture boundary."
architecture_compliance: applicable
architecture_compliance_reason: ""
required_benchmark_scenarios: []
verified_revision:
verification_evidence: []
archive_sha256:
created: 2026-08-06
updated: 2026-08-06
author: "Codex"
owner: "RepoFoundry Maintainer"
---

# Support historical ADR revision evidence

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry users must be able to validate a completed or cancelled ExecPlan
against the exact ADR payload revision it recorded, even when the current ADR
file now contains another byte revision with the same decision semantics. The
observable result is that a repository can import a valid historical ADR
document into repository-owned evidence, clone or export the repository without
Git history, and still make `epctl validate` accept both the historical plan and
newer plans without rewriting either sealed plan.

Datafox provides the concrete compatibility case. EP-051 records ADR-018 digest
`57f3a0be...`, EP-052 records `fba4f02c...`, and the recovered historical blob
differs from the current ADR only by its payload line and one trailing ASCII
space. Today `epctl` compares every historical reference only with the current
ADR file, so one of the two sealed plans must fail. This plan removes that false
choice while keeping active-plan validation fail-closed on the current accepted
ADR.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 complete; implementation, release verification
  and the Datafox compatibility loop are closed.
- Current state: The immutable revision store, registration CLI and historical
  resolver are implemented and documented. A 0.3.1 distribution composed on
  the actual installed 0.3.0 baseline is active locally, and Datafox EP-053 is
  archived with repository validation at zero errors.
- Next action: Commit the source change on an up-to-date distribution branch,
  record its verified revision, and archive EP-057. Do not relabel this older
  0.2.0 development branch as 0.3.1 or regress its newer Core/adapters.

## Context and Orientation

`adr_evidence` is an ExecPlan v2.6/v2.7 entry of the form
`ADR-NNN@sha256:<payload>`. The digest seals the decided ADR payload, not the
ExecPlan file itself. Active EPs intentionally resolve this reference against
the current accepted ADR. Completed and cancelled EPs are historical artifacts
and must preserve the digest they recorded at completion.

`engineering-execution-plan/scripts/epctl.py` currently discovers only current
ADRs through `adr_files()`. `validate_plan()` loads those current files into
`adr_data_by_id` and directly compares every `adr_evidence` digest with the
current `payload_sha256`. The `historical=True` flag relaxes ADR lifecycle status
but does not resolve a prior payload revision. The result contradicts the
documented historical contract.

The new repository-owned store is
`docs/.epctl/adr-revisions/ADR-NNN/sha256-<payload>.md`. Each file contains one
immutable strict decided ADR document. `register-adr-revision` previews an
import from a repository-relative file or an exact Git blob and writes only
with `--apply`. Normal validation reads only repository files and never requires
Git. The optional Git source adapter exists solely at explicit import time.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `engineering-execution-plan/scripts/epctl.py` | Canonical ADR/EP lifecycle and validation implementation | Before every implementation change |
| `engineering-execution-plan/tests/test_epctl.py` | Focused file-contract, security and compatibility tests | While implementing and before handoff |
| `engineering-execution-plan/references/adr.md` | Current ADR seal and historical EP evidence contract | Before changing resolver semantics |
| `engineering-execution-plan/references/integrity.md` | Historical artifacts are sealed rather than rewritten | Before migration and recovery work |
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Preview-first, fail-closed and portable migration rules | Before adding the import command |
| `docs/design-docs/engineering-workflow-packaging.md` | `epctl` owns ADR and ExecPlan state independently of Harness adapters | Before choosing the storage boundary |
| `scripts/check.py` | Repository-wide canonical verification entrypoint | Before completion |

## Research and Architecture Inputs

- Research gate: `not_required`.
- Research references: [].
- Architecture decision gate: `not_required`.
- Architecture compliance: `applicable`.
- ADR references: [].
- ADR constraint references: [].
- ADR evidence: [].
- Design document references: ["docs/design-docs/repo-foundry-versioning-and-migrations.md", "docs/design-docs/engineering-workflow-packaging.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

Research is not required because the Datafox recovery artifact already contains
the decisive evidence: both plan digests, the exact 8,328-byte historical blob,
and the one-byte payload difference. Local reproduction confirms that the only
remaining Datafox validation error is EP-051's mismatch against the current
ADR-018 digest. There is no factual uncertainty that can change the route.

No new architecture decision is required. The existing EP contract already
states that completed and cancelled plans preserve their original ADR digest,
and historical artifacts must not be rewritten. The implementation restores
that contract with the repository-owned resolver already selected by the user.

Architecture compliance remains applicable. The revision store belongs to
`.epctl` state rather than the Harness manifest; importing is preview-first and
conflict-free; normal validation remains product-neutral, offline and
Git-independent; active EPs never fall back to historical evidence. Historical
source bytes must be strict decided ADRs whose ID, recorded digest and computed
digest all agree. A digest can resolve to only one immutable stored document.

## Architecture Compliance Matrix

| ADR constraint or architecture input | Implementation or preservation | Verification |
|---|---|---|
| docs/design-docs/repo-foundry-versioning-and-migrations.md | Add a preview-first explicit import, immutable target paths, conflict detection and offline post-import validation; bump the distribution version without changing Harness schema/Core/adapter versions. | Focused preview/apply/idempotence/conflict tests plus installer and repository canonical checks. |
| docs/design-docs/engineering-workflow-packaging.md | Keep revision evidence and resolution inside independently installable `engineering-execution-plan`; do not move it into `foundryctl`, Harness state or an Agent adapter. | Standalone `test_epctl.py`, copied-package contract tests and `scripts/check.py`. |

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

First, add a narrow revision-store abstraction to `epctl.py`: deterministic
paths, safe discovery, strict document validation, current-or-historical
resolution and explicit import source readers. Add the preview-first CLI only
after the resolver invariants are shared by registration and validation.

Second, change historical v2.6/v2.7 plan validation to resolve each declared
`adr_evidence` digest before deriving research dependencies, design references,
constraint rows and dependency closure. Active plans continue using current
accepted ADR files exclusively. Validate all registered revisions globally so
unused tampered evidence cannot remain silently in the repository.

Third, add fixtures for the exact one-trailing-space failure and for security
boundaries: missing revision, tampered payload, wrong ADR ID, duplicate target,
symlink source, invalid Git object, no-Git validation, active-plan rejection and
historical constraint resolution. Update Skill/reference/design documentation,
the distribution version and user-facing command examples.

Finally, compose and install the updated local distribution on the actual
installed 0.3.0 release baseline, use the new command in Datafox to import blob
`e3fa598bb8999b81c5ed777c74c517239cd565e0`,
run Datafox validation, and only then remove EP-053's compatibility blocker and
attempt its normal archive command. EP-051, EP-052 and current ADR-018 remain
byte-for-byte unchanged.

## Milestones

### Milestone 1: Store and resolve immutable historical ADR payloads

`epctl.py` exposes one deterministic registry and a current-or-historical
resolver. `register-adr-revision` produces a JSON preview by default and writes
only with `--apply`. A historical completed EP passes only when its exact digest
resolves to a valid stored ADR; missing or modified evidence fails closed.

### Milestone 2: Prove and document the portable contract

Focused tests cover registration, idempotence, tampering, path safety,
historical semantic inputs and active-plan isolation. Skill and reference docs
show the storage layout and recovery workflow. `VERSION` advances to the next
distribution release while Harness component versions remain unchanged.

### Milestone 3: Close the Datafox compatibility loop

The locally installed RepoFoundry distribution imports the recovered ADR-018
blob into Datafox repository state. Datafox `epctl validate` no longer reports
the EP-051 digest error, and EP-053 proceeds through its unmodified completion
and archival checks. Any unrelated Datafox warnings or user changes are
preserved and reported separately.

## Concrete Steps

From `/Users/wangxiaowei1/x-otel/EngineeringPlan`:

    python3 -B -m unittest engineering-execution-plan.tests.test_epctl
    python3 -B scripts/check.py

Expected: the focused suite and canonical check exit zero. The check may retain
the pre-existing EP-006 ready-to-archive warning but reports zero errors.

After implementation, preview and apply the downstream import from
`/Users/wangxiaowei1/x-otel/datafox`:

    epctl --repo . register-adr-revision ADR-018 \
      --from-git-blob e3fa598bb8999b81c5ed777c74c517239cd565e0
    epctl --repo . register-adr-revision ADR-018 \
      --from-git-blob e3fa598bb8999b81c5ed777c74c517239cd565e0 --apply
    epctl --repo . validate

Expected: preview reports one create action without changing files; apply
creates the digest-addressed revision; validate reports zero errors and does
not require Git after the revision has been stored.

## Validation and Acceptance

- [x] From the RepoFoundry root, run the focused `test_epctl.py` suite; expect
  all historical revision, active isolation, tamper, idempotence and source
  safety cases to pass. Evidence: EP-057 `artifacts/focused-tests.txt`.
- [x] From the composed 0.3.1 RepoFoundry release root, run `python3 -B scripts/check.py`; expect exit
  zero with no repository contract error. Evidence: EP-057
  `artifacts/repository-check.txt`.
- [x] From a temporary repository without `.git`, validate a copied historical
  revision registry; expect the completed EP to pass, proving normal validation
  is Git-independent. Evidence: focused test transcript.
- [x] From the Datafox root, preview then apply registration of blob
  `e3fa598bb8999b81c5ed777c74c517239cd565e0`; expect the target digest to be
  `57f3a0be4e202cd1a530666378a6bd61d83feec2b9b484bfb21b2abf2e681220`
  and no edits to EP-051, EP-052 or ADR-018. Evidence: Datafox Git diff and
  registration transcript.
- [x] From the Datafox root, run the updated `epctl validate`; expect zero
  errors, then run EP-053's normal archive flow if all of its own gates remain
  satisfied. Evidence: Datafox EP-053 artifact or concise transcript.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Preview performs no repository write. Apply uses the existing repository lock,
revalidates the source, creates parent directories only inside
`docs/.epctl/adr-revisions`, and writes atomically. Reapplying identical bytes
is an idempotent preserve; an existing target with different bytes is a hard
conflict and is never replaced.

The file source must be a repository-relative regular non-symlink path. The Git
source accepts only a full hexadecimal object ID, verifies that it is a blob,
and bounds the payload before UTF-8 parsing. Git is never called by `validate`.

Rollback of an uncommitted registration consists only of removing the newly
created revision file and now-empty ADR directory; no sealed plan or current ADR
is touched. If downstream validation still fails, leave EP-053 blocked and keep
the imported evidence for inspection rather than moving the error by rewriting
digests.

## Progress

- [x] (2026-08-06T12:03:19Z) Plan created with reproduced Datafox evidence and
  a fixed repository-owned compatibility route.
- [x] (2026-08-06) Implemented the revision registry, import command and historical resolver.
- [x] (2026-08-06) Added focused fixtures and documentation; the composed 0.3.1 release passed
  the complete canonical repository check.
- [x] (2026-08-06) Installed 0.3.1 locally, migrated Datafox evidence, archived EP-053 and
  completed Router/Harness validation.

## Surprises & Discoveries

- 2026-08-06 — RepoFoundry `0.2.0`, `0.2.1` and the locally installed `0.3.0`
  all compute ADR-018's current digest as `fba4f02c...`; the `57f3a0be...`
  value is not an algorithm-version artifact. It is reproduced by the recovered
  blob containing one trailing ASCII space. Therefore algorithm negotiation is
  unnecessary; payload-revision resolution is the correct boundary.
- 2026-08-06 — The active development branch is still based on distribution
  0.2.0, while the installed source of truth is 0.3.0 with Core 1.2.0 and Codex
  adapter 2.2.0. Installing this branch as 0.3.1 would silently regress those
  planes, so the local 0.3.1 release was composed on the verified 0.3.0 source
  and only the five matching execution-plan files were overlaid.
- 2026-08-06 — One canonical-check run in the older development checkout hit
  the wrapper's 180-second timeout during its final suite. The same suite then
  passed 96/96 directly in 286.496 seconds, while the actual 0.3.1 release
  completed its full canonical check, including 101/101 release tests, in the
  normal timeout. This is recorded as environmental I/O variance, not hidden.

## Decision Log

- 2026-08-06 — Use digest-addressed repository files rather than Git history as
  the normal validation source. Git is an optional explicit import adapter only.
  This keeps exported repositories verifiable and preserves product neutrality.
- 2026-08-06 — Do not create a new ADR. The change restores the already stated
  completed-EP evidence contract, and the user fixed the storage/resolution
  route before implementation. Record local format choices in this plan.
- 2026-08-06 — Advance the installed distribution to 0.3.1 without changing
  Harness schema 3, Core 1.2.0, Codex adapter 2.2.0 or activation protocol 2.
  Preserve the old 0.3.0 immutable release for rollback and leave the stale
  development checkout's VERSION untouched until its upstream baseline is reconciled.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

The implementation closes the historical-evidence gap without modifying the
`ADR-NNN@sha256:<payload>` schema. Completed/cancelled plans resolve current
evidence first and then a validated immutable revision; active plans remain
current-only. Registry discovery rejects malformed paths, symlinks, digest/ID
mismatches and conflicting content, while normal validation never invokes Git.

The Datafox proof preserved EP-051, EP-052 and current ADR-018 byte-for-byte,
added only the recovered `57f3...` revision, reduced epctl validation to zero
errors, and allowed EP-053 to archive with its existing BR-019/BR-020 evidence.
The locally active 0.3.1 package is based on the true 0.3.0 release, retains
0.3.0 for rollback, and upgrades both Codex and Claude host registrations.

The remaining repository activity is release-integration bookkeeping: this
older development branch needs rebasing/merging onto the current distribution
line before its source commit can become the archived EP's verified revision.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

The implementation remains Python standard-library only. It introduces:

- `adr_revision_root(repo)` and deterministic revision path helpers;
- a strict registered-revision validator shared by import and global validate;
- `resolve_adr_evidence(repo, adr_id, digest)` returning the selected path,
  text and parsed metadata;
- `register_adr_revision(...)` returning a structured preview/apply result;
- CLI `register-adr-revision ADR-NNN (--from-file PATH | --from-git-blob OID)
  [--apply]`.

The resolver consumes the existing `ADR-NNN@sha256:<64-hex>` syntax, so sealed
ExecPlans require no schema migration. The optional registry is EP-owned state,
not a Harness manifest component. No third-party package, network service,
Agent adapter or Git dependency is added to normal validation.

## Artifacts and Notes

- Plan: `docs/exec-plans/active/ep-057_historical-adr-revision-evidence/EXECPLAN.md`
- Focused test evidence: `docs/exec-plans/active/ep-057_historical-adr-revision-evidence/artifacts/focused-tests.txt`
- Repository/release check evidence: `docs/exec-plans/active/ep-057_historical-adr-revision-evidence/artifacts/repository-check.txt`
- Datafox compatibility evidence: `docs/exec-plans/active/ep-057_historical-adr-revision-evidence/artifacts/datafox-compatibility.txt`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-06T12:03:19Z — Initial plan created.
- 2026-08-06 — Recorded the completed implementation, 0.3.1 release composition,
  local installation, Datafox migration/EP-053 archive, Router audit and final
  verification results.
