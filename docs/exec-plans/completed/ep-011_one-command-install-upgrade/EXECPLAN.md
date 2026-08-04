---
schema_version: "2.5"
id: EP-011
title: "Add one-command RepoFoundry AI install and upgrade"
status: completed
latest_checkpoint:
research_refs: ["R-001"]
research_gate: satisfied
research_gate_reason: ""
adr_refs: ["ADR-001", "ADR-004", "ADR-007", "ADR-008", "ADR-009", "ADR-002", "ADR-005", "ADR-010", "ADR-011", "ADR-012"]
design_refs: ["docs/design-docs/repo-foundry-system.md", "docs/design-docs/repo-foundry-versioning-and-migrations.md", "docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"]
architecture_entrypoint: "docs/design-docs/index.md"
architecture_gate: satisfied
architecture_gate_reason: ""
required_benchmark_scenarios: []
verified_revision: "ab0b6e5bbb5e086f9b38f4de771b02665ba46439"
verification_evidence: ["docs/exec-plans/completed/ep-011_one-command-install-upgrade/artifacts/validation-summary.txt", "python3 -B scripts/check.py (exit 0)", "live:github-release-v0.1.0@2c54bb85a1fb88096eee0ef63ac30bc44d300329"]
archive_sha256: 40b49f1bcf9ce4fda1a3dcc0a7c0d76970c55b509262943b67b2240237a0c866
created: 2026-08-04
updated: 2026-08-04
owner: "RepoFoundry Maintainer"
---

# Add one-command RepoFoundry AI install and upgrade

This ExecPlan is a bounded living document. Keep current truth synchronized. Preserve historical events without rewriting them, and seal older events into immutable history checkpoints when the root working set grows.

## Purpose / Big Picture

RepoFoundry AI currently requires users to clone the repository, choose a
directory, export `REPO_FOUNDRY_HOME`, expose Skill roots to their Agent host,
and repeat those steps manually for upgrades. This is too much ceremony for an
AI-era project scaffold.

After this plan, the same copyable command installs or upgrades the latest
stable RepoFoundry AI distribution:

    curl -fsSL https://raw.githubusercontent.com/XiaoWeiKIN/RepoFoundryAI/main/install.py | python3 -

The installer resolves an immutable GitHub release tag to its commit, safely
downloads and validates the package, installs it as a versioned local release,
atomically switches `current`, exposes a `repofoundry` CLI, and automatically
registers the root package with Codex when that host is present. Repeating the
command at the same release is a no-op. Upgrading the distribution never scans
or silently migrates project repositories; project Harness upgrades remain the
separate preview-first `repofoundry --repo PATH upgrade --to VERSION` flow.

## Current Snapshot

- Latest checkpoint: none.
- Current milestone: Milestone 3 complete — public command and acceptance are
  green.
- Current state: `install.py`, offline and live-release coverage, managed CLI
  and Codex registration, bilingual documentation, evals, and design updates
  are implemented. The canonical repository check passes.
- Next action: commit the verified implementation, archive EP-011 against that
  exact revision, then push the additional commit to PR #19.

## Context and Orientation

`VERSION` is the distribution version. `scripts/foundryctl.py` is the existing
project-facing CLI and already owns Bootstrap, Harness upgrade, Spec lifecycle,
and validation. The new root `install.py` owns only distribution acquisition
and local activation. It must not call Harness Bootstrap or upgrade against any
project.

An **install prefix** is the user-local product directory, defaulting to the
XDG data location plus `repofoundry-ai`. It contains immutable directories
under `releases/`, a relative `current` symlink, and `install.json` provenance.
The generated `repofoundry` executable in the user-local bin directory always
dispatches through `current/scripts/foundryctl.py`. A **host integration** is a
discoverability link outside the package; initially only Codex is detectable,
and all other Agents can use the installed CLI and portable adapter without an
Agent-specific private path.

Remote stable installation uses the GitHub Releases API, resolves the release
tag through Git data to a commit SHA, downloads the archive for that commit,
records its SHA-256, and checks that the package `VERSION` matches the tag.
Tests use `--source PATH` so every filesystem and idempotence contract is
exercised without network access.

## Constraints and References

| Source | Why it matters | When to read |
|---|---|---|
| `docs/design-docs/repo-foundry-system.md` | Product name, root Skill ID, CLI identity, and Agent-neutral package boundary | Before public naming or paths |
| `docs/design-docs/repo-foundry-versioning-and-migrations.md` | Independent distribution/Harness versions and explicit migration rule | Before installer or upgrade behavior |
| `docs/design-docs/agent-neutral-harness-adapters.md` | Host-specific behavior stays outside Core | Before Codex registration |
| `scripts/foundryctl.py` | Installed CLI target; project mutation must remain here | Before launcher integration |
| `scripts/check.py` | Canonical repository acceptance entrypoint | At completion |
| `tests/test_installer.py` | Offline installation, upgrade, safety, and idempotence contracts | During implementation |

## Research and Architecture Inputs

- Research gate: `satisfied`.
- Research references: ["R-001"].
- Architecture gate: `satisfied`.
- ADR references: ["ADR-001", "ADR-004", "ADR-007", "ADR-008", "ADR-009", "ADR-002", "ADR-005", "ADR-010", "ADR-011", "ADR-012"].
- Design document references: ["docs/design-docs/repo-foundry-system.md", "docs/design-docs/repo-foundry-versioning-and-migrations.md", "docs/design-docs/engineering-workflow-packaging.md", "docs/design-docs/codex-project-bootstrap.md", "docs/design-docs/engineering-spec-management.md", "docs/design-docs/agent-neutral-harness-adapters.md"].
- Architecture entrypoint: `docs/design-docs/index.md`.

R-001 is present only through the historical ADR dependency closure: durable
control records point to independently versioned content, and downstream
consumers use explicit, verifiable interfaces. No new Research is required.
The user fixed the observable outcome—one command for first install and
upgrade—and the repository plus GitHub release contract provide all facts
needed for deterministic local tests.

ADR-007 through ADR-009 fix the RepoFoundry AI brand, `repo-foundry-ai` Skill
ID, and `repofoundry` distribution vocabulary. ADR-011 and ADR-012 require an
Agent-neutral Core and keep product integration behind adapters; therefore the
canonical package lives outside Agent-private directories, while Codex
registration is a replaceable host integration. ADR-002, ADR-005, and ADR-010
remain dependency-closure inputs because installed files must preserve the
current Bootstrap and Engineering Spec behavior. ADR-001 and ADR-004 keep the
professional Skills independently discoverable and prohibit moving their
lifecycle logic into the installer.

The existing design already separates RepoFoundry distribution upgrades from
project Harness migrations. This implementation must preserve that boundary:
installing a newer tool may make a project migration available, but cannot
apply it. The installer uses Python 3.10+ standard library only, rejects unsafe
archive members and source symlinks, validates staged content before switching
the active release, preserves pre-existing host registrations in a recoverable
backup, records source provenance, and makes remote/network failure
non-destructive. No performance Benchmark is relevant.

## Benchmark Gate Set

- Required Scenario IDs: [].

| Scenario | Development decision or milestone gated | Completion contract |
|---|---|---|
| — | No Benchmark Scenario gate declared for this EP. | — |

This set is declared before implementation. Do not replace one Scenario with
another after observing results; change the plan and record the reason first.

## Plan of Work

First add a standalone root `install.py`. Its pure helpers validate semantic
versions, resolve release tags and commits, download with bounded size, safely
extract archives, calculate deterministic package digests, validate required
RepoFoundry entrypoints, and construct a plan. Its apply path installs content
under a commit-addressed release directory, atomically switches the `current`
symlink and `install.json`, writes a managed `repofoundry` launcher, and handles
Codex discovery through `auto`, `codex`, or `none` host selection. Existing
non-managed host content is moved to a reported backup before linking.

Then add offline `tests/test_installer.py` fixtures for install, no-op repeat,
version upgrade, existing Codex Skill backup, launcher execution, invalid
package state, and archive traversal/symlink rejection. Add installer
portability and public-command assertions to repository contracts if useful.

Finally replace manual-clone-first README guidance with the one-line stable
command, document `--version`, `--host`, custom prefix/bin locations, the
download-and-inspect alternative, and the explicit distinction between tool
upgrade and project Harness upgrade. Extend the versioning design without
changing Core, adapter, protocol, or Harness schema versions, run focused and
canonical checks, and archive this plan against the verified commit.

## Milestones

### Milestone 1: Safe, deterministic distribution installation

`install.py --source REPOSITORY --prefix PREFIX --bin-dir BIN --host codex
--codex-home CODEX_HOME --json` installs the current checkout without network
access. The JSON reports `installed`, exact version, content digest, active
home, launcher, host links, backups, and `project_harnesses_modified: false`.
The launcher reports the same distribution version. Repeating the command
reports `unchanged` and creates no second release.

### Milestone 2: Upgrade, recovery, and remote release contract

Installing a second valid source version reports `upgraded`, keeps the earlier
immutable release, and atomically switches `current`. Unsafe archives,
symlinks, version mismatches, corrupt existing release directories, download
failures, or staged validation failures leave the previous active release and
host links unchanged. Remote resolution accepts only exact `vMAJOR.MINOR.PATCH`
release tags and records commit plus archive SHA-256.

### Milestone 3: Public one-command experience

English and Chinese README files lead with the same install-or-upgrade command,
explain that stable GitHub releases are selected, and show how to inspect the
installer before execution. The versioning design and root Skill distinguish
distribution update from repository Harness migration. Focused tests and the
canonical repository check pass.

## Concrete Steps

Run from the isolated implementation worktree:

    cd /private/tmp/repofoundry-agent-adapters.omlsdZ/foundry

Exercise the installer entirely from local source:

    python3 -B install.py --source . --prefix /tmp/repofoundry-prefix \
      --bin-dir /tmp/repofoundry-bin --host none --json
    /tmp/repofoundry-bin/repofoundry --version

Expected: JSON action `installed`, version `0.2.0`, no project Harness writes,
then `RepoFoundry AI 0.2.0`. Run focused tests and governance validation:

    python3 -B -m unittest tests.test_installer tests.test_repository_contracts
    python3 -B engineering-execution-plan/scripts/epctl.py --repo . validate

Expected: tests report `OK`; epctl reports zero errors and warnings. Run the
complete repository gate before commit:

    python3 -B scripts/check.py

Expected: all integrity checks pass. Do not exercise the production one-line
command against a mutable branch in tests; remote release behavior is covered
with mocked HTTP responses and local archives.

## Validation and Acceptance

- [x] From a temporary home, install local source with `--host codex`; expect
  one versioned release, `current`, a working `repofoundry` launcher, a Codex
  discovery link, provenance metadata, and no project Harness path. Evidence:
  `tests/test_installer.py`.
- [x] Repeat the identical install; expect action `unchanged`, the same release
  and links, and no backup or duplicate content. Evidence:
  `tests/test_installer.py`.
- [x] Install fixtures with two versions; expect action `upgraded`, both
  immutable releases retained, and launcher output from the new current
  release. Evidence: `tests/test_installer.py`.
- [x] Start with an unmanaged Codex Skill directory; expect its exact bytes in
  a reported backup before the managed discovery link is created. Evidence:
  `tests/test_installer.py`.
- [x] Attempt path-traversing archives, source symlinks, version mismatches, and
  staged validation failures; expect nonzero exits and no active-release
  change. Evidence: `tests/test_installer.py`.
- [x] Validate mocked GitHub release/tag resolution; expect only exact SemVer
  tags, a peeled commit SHA, bounded archive download, and recorded SHA-256.
  Evidence: `tests/test_installer.py`.
- [x] Run `python3 -B -m unittest tests.test_installer
  tests.test_repository_contracts`; expect `OK`. Evidence: Progress transcript.
- [x] Run root and Codex Router Skill validation; expect both valid. Evidence:
  Progress transcript.
- [x] Run `python3 -B engineering-execution-plan/scripts/epctl.py --repo .
  validate`; expect 0 errors and 0 warnings. Evidence: Progress transcript.
- [x] Run `python3 -B scripts/check.py`; expect exit 0 and all integrity checks
  passed. Evidence: Progress transcript and archived verification evidence.

### Required Benchmark Scenario Gates

- No required Benchmark Scenario gates.

Completion writes `verified_revision` and `verification_evidence` through
`archive-ep`. Archival also seals the complete document with `archive_sha256`;
do not pre-fill these fields while the plan is active.

## Idempotence and Recovery

Every release directory is content-addressed by version and immutable source
identity. The installer fully acquires, extracts, rejects links, validates, and
renames a staged package before changing `current`. The active symlink,
launcher, install metadata, and host links are written through sibling
temporary paths and atomic replacement where supported. A failure before
activation leaves all existing state untouched; a failure while activating
restores captured links/files and removes only new temporary paths.

An identical rerun validates and reuses the installed release. An existing
release directory with unexpected content is a conflict, not overwrite
authority. Existing unmanaged host registrations and launchers are moved to a
timestamped backup within the install prefix and reported to the user. Old
versioned releases are retained for manual rollback by repointing `current`;
automatic pruning and uninstall are outside this plan.

The installer never locates project repositories. After a distribution
upgrade, each repository remains on its recorded Harness schema/Core/adapters
until the user separately previews and applies `repofoundry upgrade` there.

## Progress

- [x] (2026-08-04T03:15:46Z) Created EP-011 with the dependency-closed accepted
  architecture and no Benchmark gates.
- [x] (2026-08-04T03:22:00Z) Filled the public command, security, provenance,
  idempotence, host-integration, recovery, and observable acceptance contract
  before implementation.
- [x] (2026-08-04T03:30:00Z) Implemented Milestone 1 with a POSIX install lock,
  source and archive validation, content-addressed releases, atomic activation,
  a managed `repofoundry` launcher, recoverable Codex registration, and JSON
  provenance output.
- [x] (2026-08-04T03:34:00Z) Implemented Milestone 2 coverage for initial
  install, idempotent repeat, upgrade/downgrade protection, existing Skill
  backup, activation rollback, recursive target rejection, archive traversal,
  symlink rejection, and peeled Git tag resolution.
- [x] (2026-08-04T03:36:00Z) Exercised the live GitHub path against stable
  `v0.1.0`: it resolved commit
  `2c54bb85a1fb88096eee0ef63ac30bc44d300329`, recorded archive SHA-256
  `f2288b57063ae17725506a8acb8bf9b72571061efcd9974097d66daf76b78cc4`,
  installed successfully, and returned `unchanged` on repeat.
- [x] (2026-08-04T03:38:19Z) Completed Milestone 3 and acceptance. Focused
  RepoFoundry tests passed 84 cases; both Skill packages validated; `epctl`
  reported 0 errors and 0 warnings; the canonical check passed Research 29,
  Benchmark 8, Execution Plan 37, and RepoFoundry/repository 84 tests. See
  `artifacts/validation-summary.txt`.

## Surprises & Discoveries

- The local macOS Python installation did not have a usable CA chain for
  `urllib`, while the already-required outer `curl` command validated GitHub
  TLS correctly. The installer now prefers `curl` transport without exposing
  tokens in process arguments and retains certificate-validating `urllib` as a
  fallback; it never disables TLS verification.
- The existing `v0.1.0` GitHub Release has no custom assets. Resolving its tag
  to a commit and downloading the commit-addressed GitHub archive proved the
  installer does not require a separately maintained release artifact.

## Decision Log

- 2026-08-04 — Use a Python standard-library installer as the one-line entry
  point because Python 3.10+ is already a RepoFoundry prerequisite and it
  allows the archive and filesystem safety contract to be tested across macOS
  and Linux without adding a package-manager dependency.
- 2026-08-04 — Default to the latest stable GitHub release, install centrally,
  and auto-register only detected hosts. Keep project Harness migration a
  separate explicit command.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Outcomes & Retrospective

RepoFoundry AI now has one copyable command for first install and upgrade. The
result is versioned, provenance-bearing, idempotent, recoverable, and
Agent-neutral: central package activation and CLI work without an Agent host,
while Codex discovery is an optional integration. A live GitHub release test
proved the public transport and tag-peeling path rather than relying only on
mocks.

The installer deliberately stops at tool distribution. It reports
`project_harnesses_modified: false` and cannot silently upgrade repository
Harness state. This preserves RepoFoundry's preview-first project migration
contract and makes the convenience command safe to repeat globally.

Windows host installation, release pruning, uninstall, and native Agent hosts
other than Codex remain future work. The portable CLI is available everywhere
this release supports installation; a future host adapter can be added without
changing the Core distribution layout.

### Knowledge promotion candidates

- None.

## Interfaces and Dependencies

Runtime requirements are macOS or Linux and Python 3.10+. Remote mode uses
`curl` when available, with a certificate-validating standard-library fallback,
to call GitHub HTTPS APIs for latest-release metadata, Git ref/tag resolution,
and commit-addressed archive download. `GITHUB_TOKEN` or `GH_TOKEN` may be used by
the HTTP client but is never written to output or metadata. Local `--source`
mode has no network dependency.

Public installer interface:

    install.py [--version latest|MAJOR.MINOR.PATCH] [--prefix PATH]
               [--bin-dir PATH] [--host auto|codex|none]
               [--codex-home PATH] [--source PATH] [--json]

`--source` is an explicit development/testing source and derives the version
from its `VERSION` file. The result JSON schema version is `1` and contains the
action, active version and source provenance, active package home, CLI path,
host integration records, backup paths, and a constant false
`project_harnesses_modified` field. The installed launcher forwards all
arguments to `current/scripts/foundryctl.py`.

## Artifacts and Notes

- Plan: `docs/exec-plans/completed/ep-011_one-command-install-upgrade/EXECPLAN.md`
- Validation summary: `docs/exec-plans/completed/ep-011_one-command-install-upgrade/artifacts/validation-summary.txt`
- Full logs, traces, screenshots and generated evidence belong under `artifacts/`; keep only concise observations and paths here.

## Revision Notes

- 2026-08-04T03:15:46Z — Initial plan created.
- 2026-08-04T03:22:00Z — Defined a stable-release, content-addressed,
  Agent-neutral install/update contract and explicit project-migration boundary.
- 2026-08-04T03:38:19Z — Recorded implemented installation, recovery, live
  Release evidence, supported-platform boundary, and completed acceptance.
