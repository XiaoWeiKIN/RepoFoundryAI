# Real-world multi-document corpus

## Observation

The user supplied an existing `spans-aggregate` research directory from the
DataFox repository. It contains an `index.md` entrypoint plus ten focused
Markdown documents:

- request model;
- planner design;
- capability matrix;
- Top-N timeseries semantics;
- response contract;
- ClickHouse renderer contract;
- source/backend boundaries;
- architecture decisions;
- a future configured-span-metrics extension;
- a naming appendix.

The corpus contains 11 Markdown files, 4,868 lines, and 211,187 bytes. The
documents use `inputDocuments` frontmatter and Markdown links to form a
dependency graph. `index.md` already provides a reading route, document map,
current claims, and maintenance constraints.

## Consequences for the model

1. A Research identity cannot be equated with one Markdown payload.
2. An existing entrypoint may be named `index.md`; forcing a rename or move
   would make adoption invasive.
3. Topic documents may be useful independently while still contributing to
   one shared decision boundary.
4. A future topic with an independent activation condition should be allowed
   to become a separate Research identity even when it begins in the same
   directory.
5. Downstream ADRs and ExecPlans need one bounded synthesis, not all 211 KB of
   source material.

## Integrity findings

The corpus also demonstrates why discovery alone is insufficient:

- `03-capability-matrix.md` names
  `spans-aggregate/07-api-contract.md`, which does not exist; the actual
  document is `07-clickhouse-renderer-contract.md`.
- Several `inputDocuments` entries are absolute workstation paths. They can be
  valid evidence during an active run but are not portable repository
  references.

A first-class corpus therefore needs an explicit manifest, link validation,
portability diagnostics, and an immutable conclusion snapshot.
