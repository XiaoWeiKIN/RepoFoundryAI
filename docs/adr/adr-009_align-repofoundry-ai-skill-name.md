---
schema_version: "1.1"
id: ADR-009
title: "Align the root Skill name with RepoFoundry AI"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-008"]
design_refs: ["docs/design-docs/repo-foundry-system.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicit instruction to synchronize the Skill and project names in the current Codex conversation on 2026-08-01)"
decided: "2026-08-01T08:09:54Z"
payload_sha256: c513d4d7f86cdf3071bc9b5932132ac3516199a5b81f7c800edd841f81dad3b1
created: 2026-08-01
updated: 2026-08-01
owner: "RepoFoundry Maintainer"
---

# Align the root Skill name with RepoFoundry AI

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-008 selected **RepoFoundry AI** as the project and display name while
retaining `repo-foundry` as the root Skill ID. The resulting installation and
prompt surface asks users to remember two names for the same entrypoint:
RepoFoundry AI in project navigation and `$repo-foundry` when invoking its
Skill.

The Repository Owner has now explicitly requested that the Skill and project
names be synchronized. This changes a public invocation contract and therefore
requires a durable amendment rather than an edit to the sealed ADR-008 body.

## Decision Drivers

- Make the name visible in Skill lists, documentation, examples, and prompts
  match the project name exactly after normalization.
- Preserve the `AI` signal on both discovery and invocation surfaces.
- Avoid coupling a human-facing Skill rename to persistent target-repository
  schemas and command names.
- Keep the migration explicit for users of the unmerged `$repo-foundry`
  candidate name.
- Retain stable professional `engineering-*` Skill IDs and their independent
  installation boundaries.

## Research Evidence

No additional Research package is required. The choice is a naming constraint
set directly by the Repository Owner in the current Codex conversation on
2026-08-01. Repository inspection confirms that the mismatch is limited to the
root Skill metadata, prompt examples, eval catalog, current design documents,
and tests. The manifest owner, CLI, state directory, and professional Skill IDs
are independent machine contracts and do not need to change.

## Considered Options

### Keep project RepoFoundry AI and Skill `repo-foundry`

This preserves the ADR-008 split but leaves the exact inconsistency the
Repository Owner asked to remove.

### Rename the project back to RepoFoundry

This would align with the existing Skill ID, but it weakens the AI signal that
motivated ADR-008 and conflicts with the selected public brand.

### Rename the root Skill to `repo-foundry-ai`

This makes the normalized Skill ID a direct representation of the project name
while allowing internal contracts to remain stable.

## Decision Outcome

Keep the project and display name **RepoFoundry AI** and rename the root Skill
ID to **`repo-foundry-ai`**.

Current installation, routing, examples, agent metadata, and evals must invoke
`$repo-foundry-ai`. The installed Skill directory should use
`repo-foundry-ai` when a directory name is required.

Do not rename these machine contracts as part of this decision:

- root CLI: `scripts/foundryctl.py`;
- example environment variable: `REPO_FOUNDRY_HOME`;
- new Harness and Spec manifest owner: `repo-foundry`;
- target state directory: `docs/.engineering/`;
- professional Skill IDs: existing `engineering-*` names;
- brand asset filename prefix: `repofoundry-`.

Migration guidance maps both former public entrypoints to the synchronized
Skill: `$engineering-workflow` and the unmerged `$repo-foundry` candidate become
`$repo-foundry-ai`.

## Consequences

Users see one coherent name from project discovery through Skill invocation.
The `AI` qualifier becomes part of the package identifier instead of only a
display label, improving search and promotion consistency.

Prompts and installation paths become slightly longer. Any local installation
made from the pre-merge branch under `repo-foundry` must be re-registered or
renamed to `repo-foundry-ai`. Target repositories do not require manifest or
state migration because owner `repo-foundry` remains valid and intentionally
separate from the Skill package name.

The GitHub repository rename remains an independent hosting operation; this
ADR does not claim it has occurred.

## Confirmation

- Root `SKILL.md` declares `name: repo-foundry-ai` and root
  `agents/openai.yaml` invokes `$repo-foundry-ai`.
- README files, current examples, root evals, and professional routing text use
  `$repo-foundry-ai` for the root Skill.
- Repository contract tests install the root package under
  `repo-foundry-ai` and assert the synchronized identity.
- New target manifests still use owner `repo-foundry`, and legacy
  `engineering-workflow` owners remain readable.
- Skill validation and `python3 -B scripts/check.py` pass.

## Revisit Triggers

- The project drops or changes the RepoFoundry AI brand.
- Skill registries impose a naming constraint incompatible with
  `repo-foundry-ai`.
- A future package system provides a supported display-name alias that removes
  the invocation mismatch without a package rename.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-008"]
- Design documents: ["docs/design-docs/repo-foundry-system.md"]
- Related ExecPlans:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md`.

## Revision Notes

- 2026-08-01T08:09:00Z — Proposed ADR created.
- 2026-08-01T08:16:00Z — Recorded the Repository Owner's instruction to align
  the root Skill ID with the RepoFoundry AI project name while preserving
  machine contracts.
