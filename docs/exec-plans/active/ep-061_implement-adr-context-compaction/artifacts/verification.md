# EP-061 verification evidence

Date: 2026-09-01

## Focused behavior

- `python3 -m unittest engineering-execution-plan.tests.test_epctl` — 66 tests passed.
- `python3 -m unittest tests.test_foundryctl` — 52 tests passed.
- `python3 -m unittest tests.test_installer tests.test_repository_contracts` — 31
  tests passed.
- Focused fixtures cover view preview/apply/remove/idempotency/drift, amendment closure,
  retirement review state, strict and whole-document legacy context, constraint
  selection, budget failure/reason gates, multidimensional health, consolidation
  impact, CRLF-preserving exact UTF-8 source bytes, symlink failure closure, invalid
  registries, and additive Harness upgrade.

## Repository integrity

- `python3 -B scripts/check.py` — all integrity checks passed, including 66 EP tests
  and 119 RepoFoundry/Harness/installer/spec tests in the final canonical run after
  exact-byte and path-safety review.
- `epctl validate` — 0 errors; only pre-existing draft/archival warnings plus EP-061's
  active completion placeholder.
- `designctl validate` — 0 errors and one pre-existing legacy draft warning.
- Two consecutive `epctl reindex` runs produced the same working-tree status digest:
  `c31b1b805d5fd8a7aa530e67625568fba9148496f18ddb1d5413bf4ffab92ab6`.

## Remaining release evidence

PR/CI/merge/tag/release, installed 0.8.0 receipts, and DataFox upgrade/View/capsule/hash
evidence will be appended after Milestone 4 completes.
