---
schema_version: "1.1"
id: ADR-007
title: "Adopt RepoFoundry as the product identity"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-004"]
design_refs: ["docs/design-docs/repo-foundry-system.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicit RepoFoundry approval in current Codex conversation on 2026-07-31)"
decided: "2026-07-30T16:18:55Z"
payload_sha256: 462e012b2dc1934c6ddf274bccc93c62265fb37b76cfa328606b520fd3f65078
created: 2026-07-30
updated: 2026-07-30
owner: "RepoFoundry Maintainer"
---

# Adopt RepoFoundry as the product identity

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

The distribution is presented as `EngineeringWorkflow`, while its current
boundary is broader than one workflow. The root package bootstraps and validates
a persistent Repository Harness, resolves Engineering Specs, and routes work to
four independently installable capability Skills. The target repository keeps
that environment across agent sessions.

The former name now hides the product boundary. It also appears in public and
persistent contracts: the root Skill ID, CLI path, installation examples,
manifest owner, test names, and Git repository presentation. Changing those
surfaces without one durable decision would create multiple identities and an
unclear migration path.

## Decision Drivers

- Describe a repository-centered system designed for humans and coding agents.
- Distinguish the overall system from its Inventory, Scaffold, Harness, and
  professional workflow layers.
- Give the project a short, memorable identity that can carry an original mark.
- Maintain one current Skill and CLI entrypoint.
- Preserve sealed historical records and readability of existing target
  manifests.
- Keep Benchmark, Research, Execution Plan, and Case Study independently
  installable under their existing domain names.

## Research Evidence

No formal Research package is required. The Repository Owner fixed the product
direction in the current conversation after comparing `EngineeringWorkflow`,
`Engineering Inventory`, and agent-native system terminology. Current repository
facts are visible in `README.md`, `SKILL.md`, and
`docs/design-docs/engineering-workflow-packaging.md`.

ADR-004 remains valid for the separation between the root aggregation package
and professional Skills. This ADR amends its product identity and public naming
without collapsing those boundaries.

## Considered Options

### Keep EngineeringWorkflow

This avoids migration but continues to present one internal mechanism as the
whole product.

### Adopt Engineering Inventory

This gives repository discovery a clear name. `Inventory` describes a passive
catalog and does not cover bootstrap, validation, evidence governance, or
continued operation.

### Use Agent-Native Engineering System as the product name

This phrase accurately describes the category. It is deliberately descriptive
and does not provide a distinctive repository identity.

### Use RepoFoundry with Agent-Native Engineering System as its category

`RepoFoundry` identifies the repository as the unit being transformed and
`Foundry` conveys an active, durable engineering environment. The category line
explains the product without overloading the brand name.

## Decision Outcome

Adopt **RepoFoundry** as the product and distribution identity, with
**Agent-Native Engineering System** as its category.

Apply the following public contract:

- root Skill ID: `repo-foundry`;
- root CLI: `scripts/foundryctl.py`;
- installation variable in examples: `REPO_FOUNDRY_HOME`;
- owner written to new Harness and Spec manifests: `repo-foundry`;
- persistent target state directory: `docs/.engineering/`;
- professional Skill IDs: unchanged.

Use Inventory, Scaffold, Repository Harness, and Workflows as architectural
layers under RepoFoundry. The complete contract and brand model live in
`docs/design-docs/repo-foundry-system.md`.

## Consequences

RepoFoundry gains a product identity that matches the implemented boundary.
README navigation can start with the system outcome, then explain its layers and
capability Skills. The icon can express a stable repository mold around an
engineered core.

The root Skill name, CLI path, and example environment variable change. Users
must update local Skill registration and scripts. The release does not carry
parallel root packages or CLIs, so documentation must provide an explicit
mapping.

New manifests use `repo-foundry`. Validators recognize
`engineering-workflow` as a legacy owner so existing target repositories remain
readable without rewriting their managed state.

Accepted ADRs, completed ExecPlans, and sealed validation artifacts keep their
historical names. Current source, tests, examples, and mutable design documents
adopt RepoFoundry. The external Git repository rename remains a separate hosting
operation and must not be claimed complete by local documentation.

## Confirmation

- `python3 -B scripts/check.py` passes through the canonical repository entrypoint.
- Root Skill metadata and evals use `repo-foundry`.
- `foundryctl` bootstrap and Spec tests prove new manifests use
  `repo-foundry`.
- Compatibility tests prove legacy `engineering-workflow` manifests remain
  readable.
- Repository contract tests reject the former identity on current public
  surfaces while excluding sealed history.
- `assets/brand/` contains a valid SVG master and square raster icon.

## Revisit Triggers

- The product begins running agents directly and becomes an execution runtime.
- The repository ceases to be the primary unit of installation and governance.
- Independent capability Skills move to a separate distribution model.
- A legal or ecosystem collision prevents continued use of RepoFoundry.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-004"]
- Design documents: ["docs/design-docs/repo-foundry-system.md"]
- Related ExecPlans: pending implementation plan.

## Revision Notes

- 2026-07-30T16:17:57Z — Proposed ADR created.
- 2026-07-30T16:24:00Z — Filled the decision, migration, compatibility, and
  confirmation contract after the Repository Owner explicitly approved
  RepoFoundry and requested the complete migration in the current conversation.
