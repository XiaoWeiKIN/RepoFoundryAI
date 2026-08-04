---
schema_version: "1.1"
id: ADR-011
title: "Separate the RepoFoundry core from Agent product adapters"
status: accepted
research_refs: []
depends_on: ["ADR-004"]
amends: ["ADR-002"]
design_refs: ["docs/design-docs/agent-neutral-harness-adapters.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicitly accepted ADR-011 and ADR-012 in the current Codex conversation on 2026-08-04)"
decided: "2026-08-04T02:09:16Z"
payload_sha256: 82b6ab8dc9cec0a0c9f8951198de43cc5bbd17510913d5a061b91d363231a6df
created: 2026-08-04
updated: 2026-08-04
owner: "RepoFoundry Maintainer"
---

# Separate the RepoFoundry core from Agent product adapters

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

RepoFoundry AI `0.1.0` presents an Agent-native product but encodes one Codex
profile as the only Harness implementation. The CLI accepts only `codex`, the
manifest stores one `profile`, generated files combine repository-neutral
documents with Codex instruction and Hook paths, and profile migrations treat
all template behavior as one version plane.

Adding Claude Code, Cursor, Copilot, or future coding agents by extending that
monolith would make the Core depend on every product's instruction discovery,
trust model, lifecycle events, tool payloads, and configuration ownership. It
would also prevent two products from safely sharing one repository Harness.

RepoFoundry needs a durable boundary between its repository engineering
contract and first-class product integrations. The decision changes the public
CLI, persistent Harness schema, generated-file ownership, version planes, and
migration contract, so it cannot remain an implementation detail.

## Decision Drivers

- Make the repository, rather than an Agent product, the source of truth.
- Let multiple Agent products coexist over one Harness and Spec lock.
- Preserve product-native capabilities instead of collapsing to the least
  common denominator.
- Describe enforcement honestly as native, CLI, or advisory.
- Preserve the preview-first, non-overwriting, provenance-based migration
  policy accepted by the current Harness.
- Keep `v0.1.0` Codex behavior compatible through an explicit migration and a
  temporary CLI alias.
- Version the Core, each adapter, the Harness schema, and the Spec Catalog
  independently.
- Fail closed on unknown future schemas, adapters, capabilities, templates, or
  migration records.
- Keep Engineering Execution Plan and the professional Skills independently
  installable and Agent-neutral.

## Research Evidence

No persistent Research package is required. The Repository Owner selected the
Core-plus-adapters direction after reviewing the implemented Codex-only
boundary and asked for implementation. ADR acceptance remains a separate
explicit authorization.

Repository evidence is sufficient to bound the decision:

- ADR-002 already defines `AGENTS.md` as an optional Codex adapter over
  universal architecture and EP artifacts, and names multiple non-Codex
  profiles as a revisit trigger.
- ADR-004 keeps execution governance independent from the root aggregation
  and Harness layer.
- `scripts/foundryctl.py` has a single `CODEX_HARNESS_PROFILE`, one profile
  choice, and Codex-prefixed template and validation state.
- Harness schema `2` and the `0.1.0` migration implementation already provide
  the required provenance, preview, idempotence, and rollback primitives.
- The accompanying design document specifies the proposed component, schema,
  CLI, compatibility, and migration contracts.

The remaining unknowns are mechanical implementation details covered by
schema, parity, migration, and rollback tests; they do not change the selected
boundary.

## Considered Options

### Keep the Codex-only profile

This minimizes immediate code, but contradicts the product's Agent-neutral
positioning and makes every additional product a later breaking redesign.

### Add more product profiles to the existing monolith

This can add `claude-code` quickly, but one profile field cannot represent
coexistence, Core validation remains coupled to product files, and every
product change expands shared branching and migration logic.

### Use only lowest-common-denominator Markdown and CLI behavior

This is portable, but discards native Skills, context injection, lifecycle
events, subagent propagation, and write gates even when a runtime safely
provides them.

### Separate an Agent-neutral Core from capability-declaring adapters

The Core owns repository contracts and adapters own product translation.
Adapters can coexist, version independently, and provide native features
without changing shared engineering state.

## Decision Outcome

Adopt an Agent-neutral RepoFoundry Core with independently versioned Agent
adapters.

Harness schema `3` will replace the singular profile with explicit Core and
adapter records. Adapter descriptors declare capabilities and generated-file
ownership. The first implementation ships `codex` and `portable`: Codex
preserves the current native integration, while portable exposes the shared
CLI and documentation contract without product configuration or claims of
automatic interception.

Bootstrap accepts repeatable `--adapter` values and preflights one atomic Core
plus adapter plan. For one compatibility release, `--profile codex` maps to
`--adapter codex`, and the omitted-option behavior retains Codex with a
deprecation warning. Adapter removal is excluded until deletion and customized
configuration ownership receive a separate decision.

Schemas `1` and `2` remain readable. Only explicit
`upgrade --to 0.2.0 --apply` adopts schema `3`, and only provenance-proven
unmodified generated files are replaced. The detailed file, version,
capability, CLI, and migration contracts live in
`docs/design-docs/agent-neutral-harness-adapters.md`.

## Consequences

### Positive

- RepoFoundry can support additional Agent products without moving normative
  repository or Spec state into those products.
- Teams can use multiple Agent products against one repository without
  duplicating Specs or Harness manifests.
- Native integrations remain available and their enforcement boundary becomes
  explicit and testable.
- Core and adapter migrations have independent version and ownership records.

### Negative

- Manifest, validation, template packaging, and migration code become more
  structured and require adapter contract tests.
- A compatibility period must support both `--profile codex` and the new
  adapter CLI without ambiguous combinations.
- Every adapter must maintain product-specific payload and trust semantics as
  those products evolve.

### Migration and operations

- Existing Codex projects require an explicit schema `2` to `3` migration but
  keep the same selected Specs and repository-owned document bytes.
- Customized generated files continue to require manual reconciliation.
- Adapter capability output becomes part of user-visible validation and must
  never overstate enforcement.
- Historical ADRs, ExecPlans, and manifests remain auditable under the names
  and schemas that were current when they were produced.

## Confirmation

- Contract tests prove Core Bootstrap does not create or require `.codex`
  configuration or `AGENTS.md`.
- Codex parity tests preserve the `v0.1.0` file set, line budget, trusted Hook
  behavior, and conflict semantics.
- Coexistence tests install Codex and portable adapters over one Core manifest
  and one Spec lock.
- Schema migration tests cover preview, apply, customized seed preservation,
  idempotence, future-version rejection, and validation rollback.
- Repository contracts reject product identifiers in Core descriptors and
  duplicate generated-path ownership across adapters.
- CLI tests cover explicit adapters, the compatibility alias, invalid
  combinations, and structured capability output.
- `python3 -B scripts/check.py` remains the canonical repository gate.

## Revisit Triggers

- Two products require incompatible meanings for a supposedly Core-owned
  repository contract.
- Real use shows that simultaneous adapters cannot safely share generated
  files or runtime receipts.
- A broadly adopted, provider-neutral Agent instruction and lifecycle standard
  makes most adapters redundant.
- Adapter capability declarations cannot accurately model a product's trust or
  enforcement boundary.
- Safe adapter removal becomes a common requirement and needs a versioned
  deletion and reconciliation contract.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-004"]
- Amended ADRs: ["ADR-002"]
- Design documents: ["docs/design-docs/agent-neutral-harness-adapters.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-08-04T02:02:40Z — Proposed ADR created.
- 2026-08-04T02:08:00Z — Defined the Agent-neutral Core, capability-declaring
  adapter, schema `3`, compatibility, migration, and confirmation proposal.
