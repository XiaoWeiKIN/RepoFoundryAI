# RepoFoundry AI v0.7.0

RepoFoundry AI 0.7.0 improves how teams make decisions with Coding Agents and
how repositories keep those decisions usable over time.

## Highlights

- Adds collaborative calibration to Engineering Benchmark, Research, Design,
  and Execution Plan workflows while preserving deterministic lifecycle and
  evidence controls.
- Adds effective ADR projections for active/proposed, current/effective,
  amendment, review, and historical views.
- Derives partially amended and current-effect state from the ADR graph, making
  retired decisions discoverable without treating them as current guidance.
- Upgrades legacy two-table decision indexes deterministically while preserving
  repository-owned notes.
- Extends `epctl status` JSON and human output with decision effect, currentness,
  projection, and amendment information.

## Compatibility

This release keeps Harness schema `3`, Core `1.5.0`, Codex adapter `2.4.0`,
Claude adapter `1.3.0`, Portable adapter `1.3.0`, governance policy schema `1`,
and activation protocol `2`. Existing artifacts remain readable. Repository
metadata changes only through an explicit preview/apply upgrade.

```bash
repofoundry --repo . upgrade --to 0.7.0
repofoundry --repo . upgrade --to 0.7.0 --apply
repofoundry --repo . validate
```
