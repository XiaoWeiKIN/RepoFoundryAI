---
schema_version: "1.1"
id: ADR-008
title: "Use RepoFoundry AI as the external brand"
status: accepted
research_refs: []
depends_on: []
amends: ["ADR-007"]
design_refs: ["docs/design-docs/repo-foundry-system.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicit RepoFoundry AI approval in current Codex conversation on 2026-07-31)"
decided: "2026-07-30T16:37:51Z"
payload_sha256: a24c374098260286a0025bd6baaed45093d61f53c50df2ec5a90b93cd828b34f
created: 2026-07-30
updated: 2026-07-30
owner: "RepoFoundry Maintainer"
---

# Use RepoFoundry AI as the external brand

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-007 established `RepoFoundry` as the product and distribution identity.
During the implementation, the Repository Owner clarified that public
promotion must make the AI use case immediately visible. `RepoFoundry` describes
the repository-centered boundary accurately, but the base name alone does not
tell a new reader that the system prepares repositories for AI coding agents.

This refinement affects the README title, root Skill display name, marketplace
metadata, diagrams, icon language, and launch copy. It must not rename stable
technical contracts such as the Skill ID, CLI, environment variable, or
manifest owner.

## Decision Drivers

- Communicate the AI and coding-agent use case in the first glance.
- Keep `Repo` visible because the repository is the installation and governance
  boundary.
- Preserve the distinct `RepoFoundry` base identity instead of adopting an
  occupied generic Agent or Harness name.
- Avoid a second technical migration after the ADR-007 contract rename.
- Support a concise English and Chinese launch message.
- Keep the public claim accurate: the system prepares an AI-ready environment
  and does not pretend to be a model or general agent runtime.

## Research Evidence

No additional formal Research package is required. The Repository Owner
explicitly selected `RepoFoundry AI` in the current conversation after reviewing
the naming architecture and public message.

Informal name discovery found multiple active `AgentFoundry` products and an
existing `Harness Foundry` business, making those names poor differentiation
choices. This discovery reduces naming risk but is not legal or trademark
clearance. ADR-007 and `docs/design-docs/repo-foundry-system.md` remain the
authoritative technical inputs.

## Considered Options

### Keep RepoFoundry without an AI suffix

This is concise and repository-centered, but promotional surfaces require a
reader to reach the category line before learning the AI use case.

### Rename the product to AgentFoundry

This makes the Agent association explicit but loses the repository boundary and
collides with multiple active AI products.

### Rename the product to HarnessFoundry

This is technically suggestive, but it narrows expectations toward runtime
agent harness construction, overlaps an existing business, and underrepresents
Inventory, Specs, evidence, and governance.

### Use RepoFoundry AI externally and keep RepoFoundry technical identifiers

This adds the high-signal `AI` term to promotional surfaces while retaining the
distinct repository-centered base name and the ADR-007 migration contract.

## Decision Outcome

Use **RepoFoundry AI** as the external product brand.

Use the following message hierarchy:

- brand: **RepoFoundry AI**;
- category: **The Agent-Native Engineering System**;
- primary claim: **Turn any repository into an AI-ready engineering system.**

After the first full mention, prose may use **RepoFoundry** as the short name.
Retain these technical identities from ADR-007:

- repository/distribution basename: `RepoFoundry`;
- root Skill ID: `repo-foundry`;
- CLI: `scripts/foundryctl.py`;
- example environment variable: `REPO_FOUNDRY_HOME`;
- new Harness and Spec manifest owner: `repo-foundry`;
- brand asset filename prefix: `repofoundry-`.

`AI` is a public brand qualifier, not a new package namespace or runtime claim.

## Consequences

The README, root Skill display name, agent metadata, current design documents,
and icon presentation gain an immediate AI signal. Search snippets and launch
copy can contain `Repo`, `AI`, `Agent-Native`, and `AI-ready` without replacing
the distinct brand with a generic category term.

The public wordmark becomes longer, and the `AI` qualifier may eventually feel
less differentiating as the market matures. The base `RepoFoundry` identity
remains usable if that happens.

No additional CLI, manifest, installed-Skill, or target-repository migration is
introduced. Historical artifacts keep the names that were current when sealed.
The external Git hosting rename remains a separate operation.

## Confirmation

- Both README files begin with `RepoFoundry AI`, the category line, and the
  primary AI-ready claim.
- Root agent metadata displays `RepoFoundry AI`, while `SKILL.md` keeps
  `name: repo-foundry`.
- Current architecture documentation distinguishes external brand from stable
  technical identifiers.
- Repository contract tests enforce the naming hierarchy and brand assets.
- `python3 -B scripts/check.py` passes through the canonical validation path.

## Revisit Triggers

- Legal or trademark review finds a conflict with `RepoFoundry AI`.
- The repository is no longer the primary installation and governance unit.
- The system starts marketing a general agent runtime or model platform.
- Audience research shows that the `AI` qualifier materially harms trust or
  differentiation.

## More Information

- Research references: []
- Prerequisite ADRs: []
- Amended ADRs: ["ADR-007"]
- Design documents: ["docs/design-docs/repo-foundry-system.md"]
- Related ExecPlans:
  `docs/exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md`.

## Revision Notes

- 2026-07-30T16:37:14Z — Proposed ADR created.
- 2026-07-30T16:43:00Z — Filled the external-brand boundary, message
  hierarchy, stable technical identities, and confirmation contract after the
  Repository Owner explicitly approved RepoFoundry AI.
