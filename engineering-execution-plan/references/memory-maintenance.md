# Evidence-bound Guided Memory Maintenance (P2, preview only)

## Purpose and boundaries

`memory_maintenance.py` combines the existing **P0** `memory_review.py` assessment
with the existing **epctl** ADR maintenance and impact compilers into one
deterministic, **read-only action queue**. This is not a second EP/ADR/Spec
lifecycle engine, scheduled janitor, or Agent runtime hook. Normal Explore and
Build work does **not** call it. No new Research, ADR, ExecPlan, or per-task
memory files are required.

**Age is not obsolescence.** An old accepted/current ADR stays authoritative
until the existing authorized decision lifecycle changes its effect.
`review_due` and consolidation candidates do not constitute approval.

## Command

From the installed Engineering Execution Plan distribution:

~~~bash
python3 engineering-execution-plan/scripts/memory_maintenance.py \
  --repo . --as-of 2026-10-29T00:00:00Z --json

# Optional P0 policy and digest-checked observations
python3 engineering-execution-plan/scripts/memory_maintenance.py \
  --repo . --as-of 2026-10-29T00:00:00Z \
  --policy .repo-foundry/local/memory-policy.json \
  --observations .repo-foundry/local/memory-observations.json --json
~~~

Paths and time above are illustrative. The caller supplies any policy and
observations. The command does not create them, fetch network data, scan Git
history, or infer that unobserved progress is inactivity. There is **no implicit
30/90/180-day expiry policy**.

## Report contract

| Field | Interpretation |
|---|---|
| `read_only`, `input_integrity`, `authority_changed` | Explicit preview and integrity boundaries |
| `review_report_sha256`, `source_snapshot_sha256`, `report_sha256` | Source/policy binding and replay identity |
| `actions[].action_id`, `kind`, `type` | Deterministic action identity |
| `actions[].reason_codes`, `source` | Trace to validated P0 signals and source |
| `actions[].impact` | Declared consumers/dependencies; exact epctl ADR impact when available |
| `actions[].preview_command` | Existing non-mutating command to inspect next |
| `actions[].authorization_before_mutation` | Explicit owner/effect gate |
| `actions[].mutation_route_after_approval` | Existing command family, not executable approval |
| `coverage`, `current_code_verified` | No invented code consumers or current-HEAD validation |

P2 computes a P0 report, verifies the governed source snapshot, then calls
**epctl.status_rows**, **epctl.evaluate_adr_maintenance** and, for current
ADR amendment candidates, **epctl.adr_consolidation_plan**. It never implements
its own ADR effect resolver or rewrite engine. The source snapshot is rechecked
after action generation.

## Action boundaries

- **EP review**: a concrete P0 trigger proposes continuation/replanning and
  plan-owner review, not automatic cancellation. EPs above workset thresholds
  get an optional `epctl auto-checkpoint EP-NNN` **preview command**. The
  original CLI remains responsible for checking safe completed history. P2
  intentionally does **not execute** checkpoint previews because that CLI
  takes a repository lock even during dry-run.
- **ADR review/consolidation**: an accepted/current ADR retains its authority.
  An amendment edge justifies *investigation*, not semantic equivalence.
  The existing resolver provides the exact closure, active-plan impact,
  proposed-ADR overlap and source digests. A new atomic ADR, acceptance,
  retirement or supersession still needs a Decision Owner and original gates.
- **Terminal ADR packing**: reuse only `adr-maintenance` terminal eligibility
  and its preview command. Actor, reason, review and separate `--apply`
  authorization are required. Never silently pack old history.
- **Spec / Requirement versions**: an externally supplied version comparison
  can trigger review, not a lock update. Use existing Spec validation and
  explicit selection.

Missing/corrupt/changed evidence or an unresolvable ADR preview causes a
nonzero exit and an `incomplete` JSON envelope with **no actions**.
That result does not mean "nothing needs maintenance". No source file, seal,
index, lock, status, Git history or user config is modified.

## Owner workflow

1. Run the preview with explicit evaluation time and review reason codes.
2. Execute the proposed read-only `preview_command` separately and inspect
   unknown code/test consumers. Never infer "no consumers" without coverage.
3. Request the real artifact or Decision Owner's reason and authorization.
4. Apply only through existing epctl / foundryctl lifecycle operations, then
   validate the resulting state and source revisions.
5. Preserve immutable history and restore evidence links as necessary.

This command is not a sign-off receipt. It adds no scheduled job, Issue bot,
background service or default Agent workflow step.

## Tests

~~~bash
python3 -B -m unittest discover \
  -s engineering-execution-plan/tests \
  -p test_memory_maintenance.py -v
python3 -B scripts/check.py
~~~

Tests include age and hold boundaries, evidence-backed idle EP, current ADR
protection, consolidation impact, historical files, terminal pack preview,
Spec lock signals, deterministic sorting, source drift and no repository writes.

P1's [real EP replay](../../tests/test_memory_cooling_evaluation.py) showed
that compressed configured background can still be bigger than Off. P2 does
not auto-inject additional background context.
