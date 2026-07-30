# Architecture

Status: bootstrap scaffold
Last verified: unknown

<!-- BOOTSTRAP_TODO: Replace this scaffold with verified repository facts. -->

## System Purpose

Describe the user-visible purpose, system boundary, and primary responsibilities.

## Code Map

Describe the stable top-level modules and answer:

- Where does each major capability live?
- Which entrypoints start the system?
- Where are tests, schemas, migrations, and operational tooling?

## Dependency Direction

Record allowed dependency directions between layers or domains. Link durable
choices to `docs/DECISIONS.md`; keep implementation detail in
`docs/design-docs/`.

## Architectural Invariants

List properties that must remain true and identify the test, lint, type, or
review mechanism that confirms each one.

## System Boundaries

Describe external APIs, storage systems, queues, identity providers, and other
trust or ownership boundaries.

## Cross-cutting Concerns

Summarize the canonical locations for security, reliability, observability,
configuration, feature flags, and data governance.

## Known Gaps

List unknown or unverified architecture areas without guessing their behavior.
