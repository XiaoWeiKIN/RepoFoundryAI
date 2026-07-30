---
schema_version: "1.1"
id: ADR-005
title: "Store engineering specifications in a separate repository"
status: accepted
research_refs: []
depends_on: ["ADR-002"]
amends: []
design_refs: ["docs/design-docs/engineering-spec-management.md"]
supersedes: []
superseded_by:
decision_maker: "User (explicit direction in current Codex task on 2026-07-30)"
decided: "2026-07-30T14:58:44Z"
payload_sha256: 4df850ebff7b23b00663ffdd9142ed03633e5c93f6cd61b4e6af3fa38d3f1d69
created: 2026-07-30
updated: 2026-07-30
owner: "EngineeringWorkflow Maintainer"
---

# Store engineering specifications in a separate repository

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

EngineeringWorkflow currently bundles both the mechanism that selects and
materializes Engineering Specs and the normative Spec content itself under
`engineering-specs/`. That combines two lifecycles:

- Workflow code changes when fetching, parsing, locking, routing, or Bootstrap
  behavior changes.
- Specification content changes when an engineering rule is clarified,
  expanded, versioned, reviewed, or released.

The bundled layout makes Workflow releases the only distribution channel for
Spec changes and makes independently governed specifications impossible. It
also encourages the consumer to treat local package content as authoritative
rather than recording which external specification revision it implements.

Repository ownership, the project manifest and lock schema, network and
credential behavior, and update semantics are durable interfaces. Separating
them therefore requires an explicit architecture decision.

## Decision Drivers

- Give reusable engineering specifications an independent review, versioning,
  release, and contribution lifecycle.
- Keep EngineeringWorkflow focused on discovery, dependency resolution,
  fetching, locking, materialization, routing, and validation.
- Let project manifests select one Git repository and ref while lock files
  record an immutable resolved commit.
- Preserve repository-local copies so Codex does not depend on network access
  during implementation or review.
- Keep `spec validate` fully offline and mechanically detect content drift.
- Support public, private, self-hosted, tag, branch, and local test sources
  through standard Git transport without embedding provider credentials.
- Parse remote Catalog and Markdown paths as untrusted boundary data.
- Avoid a second bundled fallback that can silently diverge from the
  specification repository.
- Keep preview-first, non-destructive Bootstrap behavior.

## Research Evidence

No new persistent Research package is required. The Decision Owner fixed the
desired boundary in the current conversation: Specs must not be built into
EngineeringWorkflow and should live in a separate repository modeled on the
OpenTelemetry specification repository, with Workflow dynamically fetching
them.

The referenced model provides relevant precedent:

- OpenTelemetry keeps cross-language requirements in a dedicated
  `opentelemetry-specification` repository, with normative Markdown below
  `specification/`.
- Implementations identify which version of that specification they implement.
- Specification sources, change process, versioning, and implementation code
  have distinct ownership and release histories.

Repository evidence confirms that the boundary is implementable:

- `scripts/spec_manager.py` already parses a Catalog, resolves dependencies,
  records SHA-256 digests, and materializes exact local files.
- `docs/.engineering/specs.json` and `specs.lock.json` already separate
  repository policy from generated resolution.
- The new
  `https://github.com/XiaoWeiKIN/EngineeringSpecifications` repository owns
  `catalog.json`, normative Markdown, schema, tests, and its canonical check.

The remaining unknowns are implementation details covered by tests: Git ref
resolution, locked sync versus update semantics, authentication failure, and
malicious remote paths.

## Considered Options

### Option A — Keep the bundled Catalog

This is offline and simple, but couples every Spec update to a Workflow
release and leaves governance in the wrong repository.

### Option B — Keep bundled defaults and optionally use an external Catalog

This eases migration but creates two possible sources of truth. A project can
silently fall back to stale bundled guidance when remote resolution fails.

### Option C — Require a separate Git-backed specification repository

EngineeringWorkflow ships no normative Spec content. It resolves an explicit
Git URL and ref, reads content directly from an ephemeral Git object store,
records the immutable commit and digests, and installs exact local copies.

### Option D — Read raw HTTP URLs for individual specifications

This avoids Git tooling but loses repository-level atomicity, revision
identity, dependency validation, and a coherent contribution history.

## Decision Outcome

Adopt Option C.

Create **EngineeringSpecifications** as the independent source of truth for
Catalog metadata and normative Engineering Spec Markdown.
EngineeringWorkflow removes `engineering-specs/` and retains only the consumer:

- the default source is
  `https://github.com/XiaoWeiKIN/EngineeringSpecifications.git` at `main`;
- projects may override Git URL and ref during initial Bootstrap or by editing
  their manifest and running an explicit update;
- `specs.json` records `{kind: "git", url, ref}` and selected Spec IDs;
- `specs.lock.json` records Catalog identity/version/digest, requested URL/ref,
  and the full resolved 40-character Git commit;
- `spec sync` uses the existing locked commit when a lock exists;
- `spec update` resolves the manifest ref again, refreshes selected content,
  and may add newly detected language Specs without removing selections;
- `spec validate` performs no network or Git operation and verifies only the
  manifest, lock, local managed files, project Specs, index, and AGENTS route.

Remote data is read without checking out a working tree. The resolver creates
an ephemeral bare Git repository, fetches one requested ref or locked commit,
and reads `catalog.json` and selected files with Git plumbing. It uses argument
arrays rather than a shell, disables terminal prompts, applies bounded command
timeouts and file sizes, validates exact JSON shapes and safe relative paths,
and verifies every declared SHA-256.

Git owns authentication discovery through the user's configured credential
helper or SSH agent. EngineeringWorkflow neither accepts nor persists tokens.
There is no bundled fallback.

## Consequences

### Positive

- Specification and consumer releases can evolve independently.
- A project can audit and reproduce the exact remote revision it consumed.
- Spec authors have a focused repository with schema, contribution rules, and
  a canonical validation command.
- Codex still reads local files after sync, so task-time behavior is fast and
  network-independent.
- Standard Git transport works across GitHub, self-hosted servers, tags,
  branches, private repositories, and local test fixtures.

### Negative

- Initial Bootstrap and explicit updates require Git and network or local
  repository access.
- Private sources depend on credentials configured outside
  EngineeringWorkflow.
- A deleted or unreachable historical commit can prevent repair from the
  locked source, although already materialized files remain usable and
  independently validatable.
- Integration tests need isolated Git repositories instead of copying bundled
  fixtures.

### Migration

- Move current Core, Go, Python, and TypeScript content to
  EngineeringSpecifications.
- Delete `engineering-specs/` from EngineeringWorkflow.
- Existing unpublished `{"kind": "bundled"}` and `{"kind": "path"}` manifests
  are intentionally rejected with a migration message; the feature has not
  shipped, so no dual-schema compatibility layer is retained.
- Historical EP-004 remains an accurate record of the earlier implementation.
  This ADR and its follow-up ExecPlan record the correction.

## Confirmation

- EngineeringSpecifications runs `python3 -B scripts/check.py` to validate
  Catalog shape, digests, dependencies, links, and tests.
- EngineeringWorkflow repository contracts fail if `engineering-specs/`
  exists or its packaged Skill requires bundled Spec content.
- Integration tests create temporary Git repositories and prove initial
  Bootstrap, locked sync, ref update, polyglot selection, content drift,
  unreachable refs, path traversal, dependency cycles, and offline validation.
- A real end-to-end preview resolves the public EngineeringSpecifications
  repository and reports its actual commit.
- `python3 -B scripts/check.py` remains the canonical Workflow check.

## Revisit Triggers

- Git transport is unavailable in a supported runtime and a signed archive
  protocol can preserve repository-level identity and verification.
- Catalog size or update frequency makes ephemeral fetch cost unacceptable and
  requires a verified persistent cache.
- Multiple independently governed Catalogs must compose in one project.
- Supply-chain requirements mandate signed tags, commit signatures, SLSA
  provenance, or an allowlisted registry.
- Offline initial Bootstrap becomes a hard product requirement.

## More Information

- Research references: []
- Prerequisite ADRs: ["ADR-002"]
- Amended ADRs: []
- Design documents: ["docs/design-docs/engineering-spec-management.md"]
- Related ExecPlans: EP-005 after acceptance.

## Revision Notes

- 2026-07-30T14:56:00Z — Proposed ADR created.
- 2026-07-30T15:08:00Z — Recorded the user-selected independent repository,
  Git resolution, immutable lock, update, security, and migration contracts.
