---
schema_version: "1.1"
id: CP-001
parent_id: EP-012
title: "Project Skill local acceptance"
status: sealed
previous_checkpoint:
repository_revision: "snapshot:project-skill-local-acceptance-20260804"
created: 2026-08-04
created_at: 2026-08-04T06:41:51Z
payload_sha256: 1fd1d46540fd4af30c22f2d26e16b0232d750da444bee6504692af371ebd81c8
---

# CP-001 — Project Skill local acceptance

This checkpoint is immutable history bound to `repository_revision`. Do not edit it after sealing. The active handoff state remains in the parent `EXECPLAN.md`.

## Handoff Summary

Implemented canonical project workflow, Codex and Claude Skill entrypoints, deterministic all-adapter bootstrap, component-version migrations, scoped validation, documentation, and local acceptance.

## Next Action At Checkpoint

Review the final diff, commit, push, create the PR, and verify remote CI before archival.

## Archived Progress

- [x] (2026-08-04T06:15:23Z) EP-012 allocated with the complete accepted ADR
  dependency/amendment closure and required R-001 reference.

- [x] (2026-08-04T06:15:46Z) Every REQUIRED planning section completed before
  implementation; route fixed to existing bootstrap plus deterministic
  all-adapter expansion.

- [x] (2026-08-04T06:41:25Z) Implemented canonical and adapter Skill assets.

- [x] (2026-08-04T06:41:25Z) Implemented descriptors, CLI selection, scoped
  validation, old schema 3 readers, and component migration history.

- [x] (2026-08-04T06:41:25Z) Added executable tests and synchronized user,
  Skill, bootstrap, adapter, and versioning documentation.

## Archived Surprises & Discoveries

- (2026-08-04T06:15:46Z) The source repository itself has no installed
  `.repo-foundry/engineering-specs/spec_router.py`; project-level Engineering
  Spec activation cannot run for this implementation. The distributed Specs
  adapter and repository tests remain the executable fallback contract.
- (2026-08-04T06:15:46Z) PR #21 is already merged, so user-level Claude Skill
  registration is an input rather than part of this feature branch.
- (2026-08-04T06:41:25Z) A schema number alone cannot determine managed-file
  paths after independently versioned components gain new seeds. The reader
  now derives files and instruction budgets from the declared Core/adapter
  versions, allowing Core 1.0.0 and Codex 2.0.0 manifests to reach either
  bootstrap adoption or explicit upgrade safely.

## Archived Decision Log

- (2026-08-04, Codex) Reuse `bootstrap` rather than add a parallel `register`
  command. Registration changes versioned Harness state and therefore needs
  the existing preview, ownership, migration, and rollback contract.
- (2026-08-04, Codex) Add `--all-adapters` as a deterministic expansion of the
  bundled ordered adapter set. Environment auto-detection is unsuitable for
  committed project state because two maintainers could generate different
  manifests from the same revision.
- (2026-08-04, Codex) Generate regular thin Skill files rather than absolute or
  relative symlinks. This preserves clone portability and the existing package
  and managed-file safety model.
- (2026-08-04, Codex) Claude phase 1 installs Skills and uses CLI/advisory Spec
  activation. Native Claude lifecycle Hooks and `CLAUDE.md` are excluded until
  a separately reviewed adapter version can state their trust and enforcement
  guarantees accurately.
- (2026-08-04, Codex) Treat new schema 3 project Skill paths as component
  migrations rather than a schema 4 change. Old component contracts remain
  readable; a previewed adapter bootstrap may create only missing new paths
  and records Core/Codex migration IDs, while explicit upgrade remains the
  route for replacing an older versioned seed.

## Archived Resolved Blockers

- None.

## Archived Revision Notes

- 2026-08-04T06:15:23Z — Initial plan created.
- 2026-08-04T06:15:46Z — Filled the self-contained execution contract from
  accepted ADR-011/012 and the implemented schema 3 boundary; selected
  bootstrap reuse, deterministic all-adapter expansion, regular project-local
  Skill files, and CLI/advisory Claude enforcement for phase 1.
- 2026-08-04T06:41:25Z — Completed local implementation and acceptance: 45
  Harness tests, 11 Router tests, 13 repository contracts, a real all-adapter
  temporary-repository smoke, and the canonical check all pass. Added
  component-version-aware schema 3 compatibility after migration analysis.
