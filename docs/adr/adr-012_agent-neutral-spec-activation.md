---
schema_version: "1.1"
id: ADR-012
title: "Separate Engineering Spec activation from Agent runtime adapters"
status: accepted
research_refs: []
depends_on: ["ADR-005"]
amends: ["ADR-010"]
design_refs: ["docs/design-docs/agent-neutral-harness-adapters.md"]
supersedes: []
superseded_by:
decision_maker: "Repository Owner (explicitly accepted ADR-011 and ADR-012 in the current Codex conversation on 2026-08-04)"
decided: "2026-08-04T02:09:16Z"
payload_sha256: 410121e886544b41db4c29b2e757b422fa2c3e1dfcf14e55ff714a2a9e79df86
created: 2026-08-04
updated: 2026-08-04
owner: "RepoFoundry Maintainer"
---

# Separate Engineering Spec activation from Agent runtime adapters

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

ADR-005 keeps normative Engineering Specifications independent of Agent
products, and ADR-010 defines one project-local Router with locked content,
Applicability decisions, dependency closure, explicit `none`, trusted Hooks,
and manual fallback. The implemented resolver and most Router commands are
runtime-neutral, but the integration boundary is not:

- Spec validation requires an `AGENTS.md` route;
- generated Router metadata includes an OpenAI-specific descriptor;
- the Router `hook` command parses Codex event names and tool payloads;
- runtime receipts assume one Agent product; and
- the canonical Router executable is installed inside the Codex-oriented
  generated Skill package.

Copying that Router for every product would create multiple activation engines
over the same Spec lock. Their candidate, activation, digest, injection, and
audit behavior could drift. Engineering Spec semantics need one durable Core,
while product events and response shapes need independent adapters.

## Decision Drivers

- Keep one normative Spec document and one immutable local lock for all Agents.
- Preserve ESP-0010 candidate, Applicability, dependency, explicit-none, and
  five-label handoff semantics across runtimes.
- Make manual and native-Hook flows use the same activation engine.
- Keep all task-time routing offline and digest-verified.
- Prevent receipt collisions when different Agent products work concurrently.
- Keep product event names, tool JSON, Hook output, instruction routes, and
  trust semantics outside the Core.
- Fail closed on malformed adapter input, uncovered paths, unknown protocol
  versions, symlinks, and content drift.
- Preserve the current Codex first-write injection, supported write gate,
  subagent propagation, and Stop audit behavior.
- Avoid one generated Skill per Spec and avoid provider-specific Spec content.

## Research Evidence

No additional persistent Research package is required. The Repository Owner
explicitly requested that the previously selected Agent-neutral adapter model
also apply to Engineering Specifications. ADR acceptance remains a separate
explicit authorization.

The existing implementation provides sufficient evidence:

- ADR-005 fixes independent normative Spec ownership and immutable local
  materialization.
- ADR-010 fixes one Router, local-only activation, trusted-Hook enforcement,
  and manual fallback, and explicitly permits other runtimes to implement the
  protocol through their own adapter.
- `scripts/spec_manager.py` already models Catalog Specs without Agent product
  fields; the coupling is limited to its instruction-route validation.
- `spec_router.py` already exposes `begin`, `candidates`, `activate`, `status`,
  and `audit` independently from Hooks, demonstrating a reusable engine.
- Completed EP-009 provides parity tests for candidate routing, activation,
  dependency closure, write denial, content injection, audit, and manual use.

The remaining questions concern interface extraction and migration rather than
which architecture to choose.

## Considered Options

### Maintain a separate Router implementation for every Agent product

This gives each adapter freedom, but duplicates security-sensitive path,
digest, dependency, receipt, and audit behavior and allows observable Spec
decisions to diverge.

### Keep the Codex Router as canonical and let other products call its manual commands

This reuses code, but retains Codex event names, packaging, instruction paths,
and trust assumptions in the canonical interface.

### Remove native Hooks and use only a portable CLI

This is neutral but discards useful lifecycle context injection and mechanical
gating for products that provide a trusted integration.

### Use one Activation Engine with normalized events and thin product adapters

The engine owns all Spec semantics and receipts. Adapters translate product
events, tool inputs, context, decisions, and configuration without copying the
engine or normative content.

## Decision Outcome

Adopt one Agent-neutral Engineering Spec Activation Engine with normalized
lifecycle events and thin Agent runtime adapters.

The engine owns candidates, Applicability receipts, dependency closure,
explicit-none reasons, local digest verification, path coverage, content
selection, and completion audit. It exposes manual `begin`, `candidates`,
`activate`, `status`, and `audit` operations plus a normalized event interface.

Adapters own product event and tool-input translation, context and decision
output translation, instruction discovery, Hook configuration, and trust
guidance. The Codex adapter maps its four current lifecycle events to the
normalized protocol without changing observable behavior. The portable adapter
uses the manual operations and claims no automatic write interception.

The canonical engine is installed once under `.repo-foundry/`. Adapter Skills
and instruction files are thin entrypoints. Receipts are keyed by repository,
adapter, session, and turn. `scripts/spec_manager.py` validates only the shared
Spec state; adapter validators own `AGENTS.md`, Skill metadata, Hook groups, and
other product files.

The exact event envelope, target layout, version planes, compatibility, and
migration steps are specified in
`docs/design-docs/agent-neutral-harness-adapters.md`.

## Consequences

### Positive

- Every Agent receives the same candidate, activation, dependency, digest, and
  audit semantics over one lock.
- Adding an Agent product does not fork Engineering Specifications or their
  activation rules.
- Native Hooks and portable CLI workflows become two enforcement modes over
  the same engine rather than separate implementations.
- Product-specific event parsing is isolated and can be versioned and tested
  independently.

### Negative

- The current standalone Router script must be split into Core and adapter
  boundaries without weakening its fail-closed behavior.
- Event normalization adds an internal protocol and compatibility obligation.
- Thin adapter entrypoints and the canonical engine add generated-file and
  migration records.

### Migration and operations

- Existing selected Specs, lock bytes, managed Markdown, and Catalog release
  remain unchanged.
- A provenance-proven unmodified generated Router can migrate automatically;
  a customized or unknown Router requires manual reconciliation.
- Runtime receipts include adapter identity and old receipts are intentionally
  not migrated because they are ephemeral turn state.
- Products without lifecycle events retain explicit activation and audit but
  cannot claim a native write gate.

## Confirmation

- A shared fixture produces identical candidates, direct activation IDs,
  dependency closure, injected requirement text, and audit result through the
  Codex and portable paths.
- Existing EP-009 Codex Hook behavior remains covered as a parity suite.
- Core tests use normalized events and contain no product event names or
  product configuration paths.
- Adapter tests cover malformed payloads, unsupported tools, context output,
  denial output, subagent propagation, and completion audit translation.
- Core Spec validation passes without `AGENTS.md`, `.codex/hooks.json`, or an
  OpenAI descriptor; selected adapter validation checks only its own files.
- Migration tests prove canonical-engine creation, wrapper replacement,
  customized-file preservation, idempotence, and rollback.
- Task-time routing remains offline and rejects lock, digest, path, symlink,
  protocol, and receipt corruption.
- `python3 -B scripts/check.py` remains green.

## Revisit Triggers

- EngineeringSpecifications changes ESP-0010 activation semantics in a way that
  cannot be represented by the normalized protocol.
- Product runtimes cannot provide stable opaque session and turn correlation.
- The shared engine prevents an adapter from implementing a necessary native
  safety boundary without provider-specific Spec semantics.
- Real activation evidence shows materially different applicable Spec results
  are required for different Agent products.
- A standardized cross-product lifecycle event and instruction protocol makes
  translation adapters unnecessary.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-005"]
- Amended ADRs: ["ADR-010"]
- Design documents: ["docs/design-docs/agent-neutral-harness-adapters.md"]
- Related ExecPlans: none yet.

## Revision Notes

- 2026-08-04T02:02:40Z — Proposed ADR created.
- 2026-08-04T02:08:00Z — Defined the shared Activation Engine, normalized event,
  adapter ownership, migration, parity, and fail-closed confirmation proposal.
