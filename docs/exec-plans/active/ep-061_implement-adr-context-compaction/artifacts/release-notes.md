# RepoFoundry AI v0.8.0

RepoFoundry AI 0.8.0 keeps complete ADR history while giving humans and Coding
Agents smaller, exact, task-relevant decision context.

## Highlights

- Adds independent `adr-health` dimensions for corpus size, contract mix, graph
  coupling, constraints, amendments, active-plan load, View coverage, and context
  cost—without an opaque aggregate score.
- Adds preview/apply Decision Views with stable repository-owned configuration and
  deterministic generated navigation.
- Adds `decision-capsule` for exact, digest-verifiable Decision Statements and
  selected constraint rows under a 32 KiB default budget. Legacy ADRs remain
  whole-document-only; overflow fails instead of summarizing or truncating.
- Adds preview-only `adr-consolidation-plan` impact analysis for amendment chains,
  active ExecPlans, proposed overlap, and legacy boundaries. It has no lifecycle
  mutation authority.
- Rebuilds or marks Views `review_required` as ADR current effect changes, while
  preserving source ADR bytes and explicit Decision Owner authority.

## Compatibility and upgrade

Harness schema `3`, Core `1.5.0`, Codex adapter `2.4.0`, Claude adapter `1.3.0`,
Portable adapter `1.3.0`, governance policy schema `1`, and activation protocol
`2` are unchanged. The migration is additive: explicit upgrade creates an empty
Decision View registry, index, and projection directory without creating a view or
editing an ADR. Customized repository files remain preserved.

```bash
repofoundry --repo . upgrade --to 0.8.0
repofoundry --repo . upgrade --to 0.8.0 --apply
repofoundry --repo . validate
```

After the upgrade, use the released `engineering-execution-plan/scripts/epctl.py`
to inspect health, define views, and compile task capsules.
