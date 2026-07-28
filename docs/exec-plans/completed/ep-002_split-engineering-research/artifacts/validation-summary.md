# EP-002 Validation Summary

Recorded at 2026-07-28T09:13:19Z.

## Package and repository validation

- Source `execution-plan`: `quick_validate.py` reported `Skill is valid!`.
- Source `engineering-research`: `quick_validate.py` reported
  `Skill is valid!`.
- Installed copies at their two independent Skill roots produced the same
  results.
- `researchctl.py --repo . validate` reported
  `{"errors": 0, "warnings": 0}`.
- `epctl.py --repo . validate` reported
  `{"errors": 0, "warnings": 0}` before plan archive.
- `git diff --check` passed.
- README and both active Skill instructions contain no `~/.codex/skills`
  installation contract.

## Regression tests

- Engineering Research: 15 tests passed in the source distribution and 15
  passed from the independently installed Skill root.
- Execution Plan: 30 tests passed in the source distribution and 30 passed
  from the independently installed Skill root.
- Producer-consumer coverage concludes a manifest-bearing Research, accepts
  its ADR under an explicit test Decision Owner, creates a gated ExecPlan, and
  rejects unsealed or tampered manifests.
- Safety coverage rejects outside-repository roots, traversal in controller
  contract paths, corpus symlinks, and sealed snapshot symlink replacement.

## Real-corpus forward test

Source corpus:
`/Users/wangxiaowei1/x-otel/datafox/_bmad-output/planning-artifacts/research/spans-aggregate`

- The source directory contains 11 Markdown documents and 4,868 lines.
- A disposable copy registered with `index.md` as its entrypoint.
- Initial validation identified the exact missing target in
  `03-capability-matrix.md`:
  `_bmad-output/planning-artifacts/research/spans-aggregate/07-api-contract.md`.
- The validator also reported the existing absolute `inputDocuments` paths as
  non-portable warnings.
- After changing only the disposable fixture reference to the existing
  `07-clickhouse-renderer-contract.md`, validation succeeded.
- Conclusion produced a sealed `snapshot` manifest containing all 11
  documents, and `epctl new-adr --research R-001` succeeded.
- The disposable fixture was moved to Trash; the DataFox source corpus was not
  modified.
