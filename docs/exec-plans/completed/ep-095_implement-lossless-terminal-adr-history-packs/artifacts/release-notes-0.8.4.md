# RepoFoundry AI 0.8.4

RepoFoundry AI 0.8.4 adds explicit, lossless physical compaction for strict terminal
ADR history while preserving the logical decision corpus and every original byte.

## Highlights

- Adds `pack-historical-adrs` preview/apply for explicitly selected live strict ADRs
  whose status is `rejected`, `retired`, or `superseded`.
- Stores exact source bytes, original paths, document and payload digests, identity,
  status, actor, and reason in one canonical self-addressed JSON History Pack.
- Resolves live, legacy, and packed ADRs through one offline logical source model for
  validation, relations, current-effect projection, evidence, indexes, capsules,
  status, and health.
- Validates the complete candidate corpus before deletion, repeats preflight under
  the repository lock, validates again after materialization, and restores exact
  source/pack/index bytes after any failure.
- Adds exact all-or-nothing `unpack-adr-history-pack`; existing destinations are
  conflicts and the pack is removed only after restored live sources validate.
- Reports logical/effective ADRs separately from live files, pack count, packed entry
  count, physical source count, and net physical reduction.
- Enforces canonical JSON/Base64, content/filename digests, path confinement,
  symlink/case collision rejection, and bounded entry/pack resource limits.

## Compatibility and upgrade

Harness schema `3`, Core `1.5.0`, Codex adapter `2.4.0`, Claude adapter `1.3.0`,
Portable adapter `1.3.0`, governance policy schema `1`, and activation protocol `2`
are unchanged. Installing the distribution or upgrading a Harness creates no pack
and modifies no ADR.

After a pack is applied, downgrading to a pack-unaware RepoFoundry release is not
supported until every pack has been successfully unpacked and `adr-health` reports
zero `history_packs` and `packed_entries`. Packed ADRs must likewise be unpacked
before any lifecycle mutation.

```bash
repofoundry --repo . upgrade --to 0.8.4
repofoundry --repo . upgrade --to 0.8.4 --apply
```

Use the bundled Engineering Execution Plan controller for storage compaction:

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  pack-historical-adrs ADR-051 ADR-052 \
  --packed-by Wangxiaowei1 --reason "Superseded by ADR-055" --json
```

Pre-release verification passed all canonical repository checks, including 77 EP
tests and 119 RepoFoundry/installer/Harness/Spec contract tests.
