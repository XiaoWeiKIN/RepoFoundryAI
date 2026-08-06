---
schema_version: "1"
metadata_schema: "1"
artifact_type: design-doc
id: DD-005
doc_type: design
title: Engineering Spec resolution and project materialization
status: current
adr_refs: ["ADR-002", "ADR-004", "ADR-005", "ADR-010", "ADR-012"]
author: "Codex"
owner: "RepoFoundry Maintainer"
created: 2026-07-31
updated: 2026-08-06
---

# Engineering Spec Resolution and Project Materialization

> Current adapter boundary: ADR-012 and
> [Agent-neutral Harness and Engineering Spec adapters](agent-neutral-harness-adapters.md)
> move candidate, activation, dependency, digest, receipt, and audit semantics
> into the shared Core. Codex-specific routes and Hooks described below are the
> Codex adapter, not a requirement of Spec content or `spec_manager.py`.

## Purpose

Extend the RepoFoundry AI Harness with versioned, composable engineering
Specs fetched from an independently governed Git repository. Bootstrap installs
required common guidance plus optional guidance explicitly selected by the
repository owner. Deterministic repository evidence recommends optional IDs;
it does not authorize installation. RepoFoundry generates one project-local
`$engineering-specs` Router Skill that reads repository-local copies through a
bounded `AGENTS.md` route. Trusted Codex Hooks make the turn decision, local
content injection, write gate, and completion audit mechanical without
depending on remote content at task time.

This design implements the ownership accepted by ADR-002, ADR-004, and ADR-005:
`repo-foundry-ai` owns project Bootstrap and Spec consumption,
`EngineeringSpecifications` owns Catalog and normative content, while
`engineering-execution-plan` remains Agent-neutral and owns only ADR, ExecPlan,
Task, Checkpoint, Bugfix, and technical-debt artifacts.

ADR-010 owns the task-time adapter boundary: one project-local Router Skill,
one short `AGENTS.md` route, digest-verified local content, trusted project Hook
guardrails for supported lifecycle paths, and an explicit manual fallback. The
Hooks are not a universal sandbox or an organization-managed policy boundary.

The release-source refinement follows approved EngineeringSpecifications
ESP-0008: production consumers select immutable `vX.Y.Z` Catalog tags, while
explicit branch refs remain development sources.

The selection refinement follows approved EngineeringSpecifications ESP-0009:
required entries remain automatic, detection is advisory, optional direct IDs
are user-selected, and dependency closure remains automatic.

The task-activation refinement follows approved EngineeringSpecifications
ESP-0010: one generated Router Skill evaluates file candidates plus task
Applicability, while AGENTS and trusted project Hooks require a turn-scoped
activation decision before implementation or review.

```mermaid
flowchart LR
    G["EngineeringSpecifications<br/>Git URL + ref"] --> F["Ephemeral bare fetch"]
    F --> C["Catalog + exact content"]
    C --> R["foundryctl Spec Resolver"]
    D["Repository evidence"] --> Q["Recommended optional IDs"]
    Q --> R
    P["Explicit project selection"] --> R
    R --> L["Pinned commit + content lock"]
    R --> M["Repository-local managed Specs"]
    L --> I["Managed routing index"]
    M --> I
    X["Project-owned Specs"] --> I
    I --> A["$engineering-specs Router"]
    H["AGENTS.md + trusted Hooks"] --> A
    A --> T["Task-specific Agent context"]
```

## Goals

- Always select a common semantic-naming Spec for implementation repositories.
- Recommend language Specs from deterministic repository evidence.
- Let the repository owner explicitly select the complete optional direct set.
- Support polyglot repositories without loading every language guide.
- Materialize exact Spec content inside the target repository.
- Record the immutable Git commit, versions, and SHA-256 digests in a lock file.
- Give reusable Specs an independent contribution and release lifecycle.
- Support public, private, self-hosted, branch, tag, and local Git sources
  through standard Git transport.
- Keep project-specific guidance repository-owned and independently editable.
- Preserve Bootstrap dry-run, whole-plan preflight, idempotence, and
  non-destructive behavior.
- Validate configuration, catalog content, local copies, project references,
  the generated Router package, Hook groups, and the Codex routing entry
  mechanically.

## Non-goals

- Bundle normative Engineering Spec content with the RepoFoundry distribution.
- Fetch individual raw HTTP files or silently fall back to packaged content.
- Store, prompt for, or manage Git credentials.
- Check out or execute code from the specification repository.
- Provide persistent catalog caching in version 1.
- Infer frameworks, architecture, owners, build commands, or project facts.
- Rewrite an existing `AGENTS.md` to insert a missing route.
- Overwrite or silently merge an existing `.codex/hooks.json`.
- Create one Skill per Specification or put Codex adapter files in the
  normative Catalog.
- Claim project Hook enforcement before the project and exact Hook definition
  are trusted by Codex.
- Delete untracked, drifted, or repository-owned files during deselection.
- Move project-owned guidance into the central catalog.

When lifecycle Hooks are unavailable, the same Router exposes an explicit
`begin` command that records the pre-write Git baseline for a caller-provided
session and turn. Manual activation remains fail-closed if `begin` was skipped,
and `audit --message` checks both changed-path coverage and the five-label
handoff. This makes fallback operational without pretending it has an automatic
write gate.

## Repository Layout

The independent
[EngineeringSpecifications](https://github.com/XiaoWeiKIN/EngineeringSpecifications)
repository contains:

```text
EngineeringSpecifications/
├── catalog.json
├── schemas/
│   └── catalog.schema.json
├── specification/
│   ├── core/
│   │   ├── data-boundaries.md
│   │   └── semantic-naming.md
│   └── languages/
│       └── go.md
├── scripts/
│   └── check.py
└── tests/
```

The RepoFoundry distribution contains no Catalog or normative Spec Markdown.
It contains only the Router templates and runtime adapter. The target project
receives:

```text
docs/
├── .engineering/
│   ├── harness.json
│   ├── specs.json
│   └── specs.lock.json
└── agent-guides/
    └── managed/
        ├── index.md
        ├── requirements.json
        ├── core/
        │   ├── data-boundaries.md
        │   └── semantic-naming.md
        └── languages/
            └── <selected-language>.md
.agents/
└── skills/
    └── engineering-specs/
        ├── SKILL.md
        ├── agents/openai.yaml
        └── scripts/spec_router.py
.codex/
└── hooks.json
```

`docs/agent-guides/managed/` is tool-owned. Project-specific Specs may live
anywhere inside the repository and are referenced from `specs.json`.

## Catalog Contract

`catalog.json` schema version 1 contains:

- a stable catalog ID;
- a semantic catalog version;
- one current entry for each Spec ID;
- a semantic version and source-relative Markdown path;
- the source file SHA-256;
- required Spec dependencies;
- optional deterministic language-detection markers;
- file scopes and a concise routing description.

Spec IDs use lowercase path segments, for example
`core/semantic-naming` and `languages/go`. Source paths must be relative,
remain within the Git tree, contain no traversal or revision separators, and
match their declared digest. Dependency IDs must exist and form an acyclic
graph.

Language detection may use marker filenames and source extensions. The resolver
ignores generated, dependency, VCS, and Harness-managed directories. Detection
only recommends optional Catalog entries; it neither installs them nor claims
the project uses a particular framework or architecture.

## Project Manifest

`docs/.engineering/specs.json` schema version 1 is repository-owned
configuration:

```json
{
  "version": 1,
  "owner": "repo-foundry",
  "catalog": {
    "kind": "git",
    "url": "https://github.com/XiaoWeiKIN/EngineeringSpecifications.git",
    "ref": "refs/tags/v1.5.0"
  },
  "specs": [
    "core/semantic-naming",
    "core/data-boundaries",
    "languages/go"
  ],
  "project_specs": [
    {
      "path": "docs/agent-guides/handler-pattern.md",
      "applies_to": ["internal/http/**"],
      "description": "Datafox HTTP Handler pattern"
    }
  ]
}
```

The only source kind is `git`. `url` is passed as one argument to Git after
validation; it may be an HTTPS, SSH, `git://`, `file://`, or SCP-style Git URL.
`ref` is a branch, tag, or full commit-like ref accepted by `git fetch` and may
not begin with `-`. Production release refs use the exact canonical form
`refs/tags/vMAJOR.MINOR.PATCH`. The default source is:

```json
{
  "kind": "git",
  "url": "https://github.com/XiaoWeiKIN/EngineeringSpecifications.git",
  "ref": "refs/tags/v1.5.0"
}
```

The default Catalog release is `1.5.0`. The option
`--spec-version MAJOR.MINOR.PATCH` constructs the canonical release ref; the resolver rejects
the source unless its `catalog_version` equals the requested version.
`--spec-ref` remains an explicit development escape hatch for a branch, custom
tag, or commit and does not imply a released Catalog version.

Bootstrap creates this file only when missing. Required Catalog entries always
form the mandatory part of `specs`; repeatable `--spec ID` values form the
complete optional direct part. Detection is returned as a recommendation and
does not mutate `specs`. Once the manifest exists, selection and source are
explicit project policy. `spec sync` reuses the existing locked commit and
selection. `spec update --spec-version ...` replaces the manifest source with
another release tag after preview; `spec update --spec-ref ...` explicitly
selects a development source. When the resolved Catalog changes and contains
optional entries outside the prior dependency-closed selection, an update
without selection arguments is unresolved and cannot apply. Repeatable
`--spec ID` replaces the optional direct set; `--required-only` selects no
optional IDs; `--keep-selection` explicitly retains the prior direct IDs. The
resolver adds dependencies after direct selection.

The dry-run payload includes a `selection_decision` object with `status`,
`reason`, `resolution`, and ordered `candidates`. Each candidate exposes its
ID, version, description, dependencies, recommendation state, prior
configuration state, and resulting selection state. A changed Catalog with
unconfigured optional entries reports `status: required` and
`resolution: unresolved`. Apply fails with
`SPEC_SELECTION_DECISION_REQUIRED` before writing any byte until exactly one
explicit resolution is supplied. This deliberately treats all unconfigured
optional entries as review candidates; repository detection affects only the
`recommended` field and cannot hide a reusable architecture Spec.

```mermaid
flowchart LR
    U["Catalog update preview"] --> C{"Changed Catalog has<br/>unconfigured optional Specs?"}
    C -->|"no"| P["Normal preview/apply contract"]
    C -->|"yes"| D["selection_decision: required"]
    D --> X["Complete --spec set"]
    D --> R["--required-only"]
    D --> K["--keep-selection"]
    D -.->|"no explicit choice"| B["Apply blocked before writes"]
```

Each project Spec path must remain inside the repository and identify a
non-symlink regular Markdown file. Project Spec scopes and descriptions are
rendered into the routing index but their content is never copied or rewritten.

## Lock Contract

`docs/.engineering/specs.lock.json` schema version 1 is generated and contains:

- catalog identity, semantic version, and catalog digest;
- requested Git URL/ref and the resolved 40-character commit;
- each resolved Spec ID and version;
- source and installed repository-relative paths;
- content SHA-256;
- scopes and routing description;
- the selected dependency closure.

The lock is the reproducibility and validation contract. Managed file bytes
must match the recorded digest. A published release tag must never move; the
resolved commit and digests still protect consumers from unexpected movement.
`spec sync` continues to resolve the locked commit. Changing the manifest
source while retaining an old lock requires an explicit update.

## Requirement Index Contract

`docs/agent-guides/managed/requirements.json` is a deterministic, strict JSON
projection of the exact locked and project-owned Spec bytes. It is routing
metadata, not normative content. For each formal Requirement it records:

- the stable Requirement ID, owning Spec, title, bounded Activation card, and
  exact context-dependency IDs;
- the source file digest plus the Requirement block's UTF-8 byte range, byte
  count, and SHA-256;
- mandatory interpretation-frame section ranges and all top-level section
  ranges available for an explicit supporting-section request; and
- the exact matching Verification table row range.

Requirement IDs are globally unique. Every referenced dependency must exist,
remain within the same Spec or a Catalog dependency, and form an acyclic graph.
An indexed formal Requirement block may not exceed 8 KiB and its Activation
card may not exceed 180 Unicode code points. Wildcard dependencies are invalid.
Legacy documents with no formal Requirement blocks are indexed in
`whole-spec` mode; a document cannot mix formal extraction with implicit
whole-document activation.

Index generation reparses only digest-verified local bytes and emits records
in deterministic Spec/source order. Offline validation regenerates the entire
file, compares exact JSON bytes, then verifies every recorded range and hash
against its source. An older project without this derived index remains
readable by the Router in whole-Spec compatibility mode, but `spec validate`
asks the maintainer to run the previewed `spec sync --apply` upgrade.

## Git Resolution

Networked operations create a temporary bare Git repository, set the configured
URL as `origin`, and fetch exactly one manifest ref or locked commit. They
resolve `FETCH_HEAD^{commit}` and read `catalog.json` and selected Markdown with
Git object commands. No working tree is checked out and no repository code,
hooks, filters, or scripts are run.

The resolver:

- uses argument arrays without a shell;
- sets `GIT_TERMINAL_PROMPT=0`;
- applies bounded command timeouts and output sizes;
- rejects URLs or refs that can be interpreted as command options;
- validates remote JSON and paths before addressing Git objects;
- verifies Catalog and file SHA-256 digests;
- deletes the temporary object store after resolution.

Existing Git credential helpers and SSH agents may satisfy authentication.
RepoFoundry never reads, accepts, logs, or persists credentials.

## CLI Contract

All mutating operations are preview-first:

```text
foundryctl spec plan
foundryctl spec sync [--dry-run | --apply]
foundryctl spec update [--spec ID ... | --required-only | --keep-selection] [--dry-run | --apply]
foundryctl spec update --spec-version MAJOR.MINOR.PATCH [--spec ID ... | --required-only | --keep-selection] [--dry-run | --apply]
foundryctl spec validate
```

- `plan` resolves the current manifest, or previews the required-only initial
  manifest when it is absent. It lists all Catalog entries and distinguishes
  required, recommended, configured, and dependency-closed selected sets. With
  a lock, it previews the locked revision.
- `sync` materializes the explicitly selected Spec set from the locked commit;
  without a lock it resolves and creates one from the manifest ref.
- `update --spec-version ...` changes the manifest to a reviewed immutable
  release and refreshes the lock and selected content. `update --spec-ref ...`
  is the explicit development-source equivalent. Repeated `--spec ID` values
  replace the complete optional direct selection; `--required-only` removes
  every optional direct ID; `--keep-selection` explicitly preserves it. A
  changed Catalog that exposes unconfigured optional entries requires one of
  these explicit resolutions before apply.
- `validate` performs no writes and verifies the manifest, lock, managed
  content, project Spec references, and routing index. It performs no network
  or Git operation and owns no adapter instruction route.

`foundryctl bootstrap --adapter codex` includes the same Spec plan;
`--profile codex` remains a deprecated compatibility alias. Bootstrap
accepts optional initial `--spec-repository` and `--spec-version` values.
`--spec-ref` selects an explicit development source instead. Repeated
`--spec ID` values choose optional Specs; omitting them creates a required-only
selection while reporting deterministic recommendations.
Bootstrap apply may create missing files but does not replace an existing
managed file with different bytes. An explicit `spec sync --apply` or
`spec update --apply` may replace files inside the managed namespace after the
preview reports the replacement. An Agent consuming a required selection
decision must present every candidate's ID, description, and dependencies to
the user and wait for an explicit choice. It must not infer
`--keep-selection` from an earlier manifest or from silence.

## Routing

The RepoFoundry `AGENTS.md` template contains one stable instruction:

> Before implementation or review, invoke `$engineering-specs`; use
> `docs/agent-guides/managed/index.md` only as its locked routing source.

The Markdown index maps scope, description, version, and local path. The JSON
Requirement index maps exact extraction ranges without duplicating normative
text. The Router takes planned repository-relative paths, returns conservative
scope candidates, and requires the Agent to apply each candidate's description
and Applicability section. Only applicable Specs enter bounded Requirement-card
discovery. Before work, the Agent records the smallest complete set of direct
Requirement IDs with one task-specific reason per ID, or an explicit no-Spec
reason. Code computes the exact Requirement dependency closure.

```mermaid
flowchart LR
    P["Prompt + planned paths"] --> S["Scope candidates"]
    I["Managed indexes"] --> S
    S --> R["Spec Applicability"]
    R --> C["Bounded Requirement cards"]
    C --> D["Direct IDs + reasons"]
    D --> E["Exact dependency closure"]
    E --> X["Digest-verified capsule"]
    X --> H["PreToolUse<br/>write gate + local injection"]
    H --> W["Implementation or review"]
    W --> A["Stop<br/>path + handoff audit"]
```

Requirement cards have a 16 KiB default response budget. Exact capsules have a
32 KiB default budget and contain, in deterministic source order, a synthetic
identity, each selected Spec's mandatory interpretation frame, resolved
Requirement blocks, matching Verification rows, and any explicitly selected
supporting sections. The engine never summarizes or truncates normative text.
Overflow reports direct/resolved IDs, Requirement and frame costs, then
requires a narrower selection, task partition, or a reviewed larger budget
recorded by `--capsule-budget-reason`. Legacy documents, migrations, and broad
audits may use
whole-Spec mode; it is not the normal path for formal Requirement documents.

`UserPromptSubmit` and `SubagentStart` Hooks inject the Router contract and the
current bounded routing view as developer context. `PreToolUse` allows
read-only discovery and Router commands, but denies mutation until the active
turn has a valid protocol-v2 receipt. It denies the first post-activation
mutation once while injecting the exact capsule, so the Agent must re-evaluate
and retry with the contract in context. `Stop` compares the prompt-time Git
baseline with the current tree and requires coverage plus the five-field Agent
handoff.

Receipts are keyed by repository, adapter, session, and turn under Git metadata
or the platform temporary directory; they never become hidden project policy
or normative evidence. A receipt records applicable and requested Specs,
direct/resolved Requirement IDs and reasons, source ranges, whole-Spec fallback
reason, capsule mode/digest/bytes/budget, and the context epoch. Compaction,
context resume, and subagent startup advance the epoch; `rehydrate` recompiles
and verifies the same capsule before reinjection. Managed content is SHA-256
verified again before every injection. No network access occurs during card,
candidate, activation, rehydration, Hook, status, or audit operations.

Existing `AGENTS.md` and `.codex/hooks.json` files remain byte-preserved. A
missing mandatory route or required Hook group is a Bootstrap conflict, not a
silent edit. Maintainers explicitly merge the short route or Hook group and
rerun validation. Project-local Hooks load only in a trusted project, and
Codex requires trust review for each exact non-managed Hook definition.

## Safety and Ownership

- Catalog, manifest, lock, and installed paths reject traversal and symlinks.
- Remote Git content is parsed as untrusted data and never checked out or
  executed.
- Git failures report the URL/ref and remediation without exposing credential
  material.
- Bootstrap stops before all writes when any Harness or Spec conflict exists.
- Bootstrap never changes an existing manifest, lock, managed Spec, either
  routing index, project Spec, `AGENTS.md`, or Hook configuration.
- Generated Router Skill files must match the RepoFoundry release; drift is an
  error rather than an instruction-injection ambiguity.
- Hook input, activation IDs, planned paths, runtime state, and Markdown are
  parsed as untrusted boundary data. Path traversal and symlinks fail closed.
- Explicit applied Spec commands only write the manifest, lock, routing indexes,
  and files beneath `docs/agent-guides/managed/`.
- Atomic writes and the existing Harness lock protect project state.
- Explicit deselection removes only previously locked managed files whose
  bytes still match their old digest. Drift blocks the complete update before
  writes. Untracked stale files are retained and omitted from the index/lock.
- Validation errors include a stable label, affected path, and remediation.

## Acceptance

- Empty repositories preview without writes and install the required Core Spec
  from the default remote repository when applied.
- Repositories containing Go evidence recommend `languages/go` without
  installing it until the user selects that ID.
- Explicit selections install one or more optional Specs, automatically add
  dependencies, and route the resulting closure by scope.
- `--required-only` previews and removes only unchanged, previously locked
  optional managed copies.
- Repeated Bootstrap and Spec sync operations are byte-idempotent.
- The default absent-manifest plan uses `refs/tags/v1.5.0`, and exact release
  refs whose Catalog version differs fail before writes.
- `spec sync` remains pinned after the tracked branch or tag moves; an explicit
  version/ref update adopts a new source and commit.
- Catalog digest drift, managed-content drift, missing lock entries, traversal,
  dependency cycles, unreachable refs, and missing project Specs fail safely.
- Existing `AGENTS.md` and project documentation remain byte-identical.
- Fresh Bootstrap creates exactly one valid `engineering-specs` Skill and the
  four required Codex Hook groups.
- Candidate routing uses file scopes without equating scope with activation;
  Requirement cards are bounded, direct IDs require reasons, exact dependency
  closure is automatic, and explicit `none` requires a reason.
- Exact capsules contain only required frames, resolved Requirement blocks,
  matching Verification rows, and requested supporting sections; unrelated
  Requirement text is absent and all included ranges retain source hashes.
- Card or capsule overflow fails without truncation; legacy whole-Spec fallback
  is explicit and reasoned, and context rehydration preserves the capsule digest
  while advancing its epoch.
- An unactivated edit, an undeclared target path, digest drift, and incomplete
  completion handoff are rejected in isolated Hook tests.
- A custom Hook file is never overwritten and instead receives a deterministic
  manual-merge conflict.
- The independently installed `repo-foundry-ai` package contains no
  normative Spec files and resolves the public default source.
- EngineeringSpecifications and RepoFoundry each have a canonical
  check, and Workflow integration tests use isolated Git fixture repositories.
