# RepoFoundry AI 0.9.0

RepoFoundry 0.9.0 makes ADR maintenance a built-in workflow capability instead
of a manual reminder.

## Added

- `epctl adr-maintenance` with deterministic human and JSON output.
- A versioned `default-v1` policy over independent ADR health dimensions.
- Three states: `within_target`, `review_due`, and `action_required`.
- Typed preview actions for history packing, current-decision consolidation,
  Decision View repair, context narrowing, plan narrowing, and legacy-contract
  migration.
- `--check` for scheduled CI; it exits 1 only for `action_required` pressure.
- `--explain` to force complete slow-path action analysis.
- A bounded maintenance summary in `status --json` and one non-blocking warning
  in `validate` when review is due.
- Event-driven maintenance checks in the versioned RepoFoundry workflow guidance.

## Authority and compatibility

Maintenance output is non-normative and preview-only. It never accepts, retires,
supersedes, consolidates, packs, unpacks, or deletes an ADR. Existing commands
still require their explicit actor, reason, reviewed preview, and `--apply`
authority. Upgrading installs detection and guidance only; it creates no History
Pack and introduces no repository state or timestamp.

Harness schema remains 3. Core Harness advances to 1.5.2 and the portable adapter
to 1.3.1. Existing repositories remain readable by the same logical ADR resolver.

## Upgrade

```bash
repofoundry --repo /path/to/repository upgrade --to 0.9.0
repofoundry --repo /path/to/repository upgrade --to 0.9.0 --apply
python3 /path/to/engineering-execution-plan/scripts/epctl.py \
  --repo /path/to/repository adr-maintenance --json
```
