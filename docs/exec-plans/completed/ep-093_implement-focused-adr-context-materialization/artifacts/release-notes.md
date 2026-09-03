# RepoFoundry AI v0.8.1

RepoFoundry AI 0.8.1 adds an explicit focused mode for exact ADR task context while
preserving complete history, full current-effect validation, and the 0.8.0 default
capsule contract.

## Highlights

- Adds `decision-capsule --materialization focused`, requiring one or more stable
  `ADR-NNN#C-NNN` references and a non-empty `--focus-reason`.
- Validates the complete current-effect closure before materializing requested rows
  and the complete constraint sets of recursively downstream scoped amendments.
- Emits exact source bytes, materialized and validated source digests, a canonical
  closure SHA-256, validated/materialized/omitted ADR IDs, and unmaterialized
  relation references under an explicit `focused_partial` boundary.
- Fails closed for linked legacy focus boundaries, broad amendments without stable
  row-level scope, and budget overflow. It never summarizes, truncates, raises its
  own budget, changes mode, or mutates ADR lifecycle.
- Keeps the existing complete invocation byte-for-byte compatible, including its
  Markdown, JSON fields, source costs, budget behavior, and capsule SHA-256.

## Compatibility and upgrade

Harness schema `3`, Core `1.5.0`, Codex adapter `2.4.0`, Claude adapter `1.3.0`,
Portable adapter `1.3.0`, governance policy schema `1`, Decision View registry
schema `1`, and activation protocol `2` are unchanged. Focused capsules are
ephemeral, so upgrading persists no new project schema and downgrading to 0.8.0
leaves repository state readable.

```bash
repofoundry --repo . upgrade --to 0.8.1
repofoundry --repo . upgrade --to 0.8.1 --apply
repofoundry --repo . validate
```

Compile a focused task context with the released Engineering Execution Plan tool:

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  decision-capsule --view runtime --constraint ADR-019#C-002 \
  --materialization focused \
  --focus-reason "Implement the selected runtime boundary" --json
```
