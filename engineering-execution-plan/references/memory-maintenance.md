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

## Deduplicated ADR review packets

The original per-ADR actions and source digests remain in `actions[]` for
backwards compatibility. An additional `review_packets[]` contains **one
review entry per identical, source-bound resolver impact**. Identity covers
the resolved ADR closure, amendment edges, active-plan consumers, proposed
overlap, digests and the resolver recommendation. Same closure with changed
source bytes or different consumer impact is **not** merged. Every packet
records all member ADR IDs, their source paths/digests, one primary preview
command, and an explicit Decision Owner gate.

`actions[].review_packet_id` links members to their packet; only the primary
sets `review_packet_primary=true`. Human output prints each packet once,
instead of presenting multiple copies of the same impact review. The summary
reports `adr_consolidation_packets` and `adr_consolidation_deduplicated`.

**Review packet identity is not semantic equivalence.** Each decision's exact
constraints and original effect remain distinct; grouping does not authorize
a consolidated ADR, acceptance, retirement or supersession.

## Optional release / CI milestone evidence

Supply `--milestones <repository-relative-json>` only for an explicit
maintenance audit. **No automatic Git or network access is added.** The
input declares which active EP's authored *Current Snapshot → Next action*
should be compared to an exported Release or successful CI run. Both the
declared source SHA-256 and the parsed source metadata must match, or the
whole run fails closed.

~~~bash
python3 -B engineering-execution-plan/scripts/memory_maintenance.py \
  --repo . --as-of 2026-10-29T00:00:00Z \
  --milestones .repo-foundry/local/milestones.json --json
~~~

For example, an explicitly saved GitHub Release API response for v0.8.3
might be stored at `.repo-foundry/local/release-v0.8.3.json`, with fields
`tag_name`, `published_at`, `draft: false`, `prerelease: false` and its
`html_url`. The caller must verify provenance separately. The companion
declaration would look like:

~~~json
{
  "schema_version": 1,
  "records": [{
    "artifact_id": "EP-094",
    "event": "release_published",
    "version": "0.8.3",
    "at": "2026-09-03T08:50:04Z",
    "source": {
      "path": ".repo-foundry/local/release-v0.8.3.json",
      "sha256": "REPLACE_WITH_ACTUAL_LOWERCASE_64_HEX_SHA256",
      "revision": "release:v0.8.3"
    }
  }]
}
~~~

The source is **not created or downloaded** by the CLI. The release tag,
publication timestamp, non-draft/non-prerelease status, URL shape and
version in the EP's authored next action must all agree. The last property
requires an explicit publication verb (for example `publish` or `发布`)
in the Next action. Evidence of a published release can suggest that
*this exact next action* needs review; it is **not** evidence that related
deployment, external migration or owner approval steps were completed.

For a CI export, use `event: "ci_succeeded"` with `match_text` matching
the authored next action and the run's `name`, source revision
`git:<full-40-hex-head_sha>` and a source JSON with matching
`head_sha`, `conclusion: "success"` and `completed_at`. This is evidence
for a review prompt, **not** current HEAD validation or EP acceptance.

The resulting action type is `review_milestone_evidence`. It keeps the
P0 assessment unchanged, sets `completion_inferred=false` and
`progress_observation_created=false`, and requires the Plan Owner to
review or update the authored Snapshot using existing lifecycle workflow.
`milestone_evidence.external_authenticity` explicitly states
`not_verified_offline`: matching locally supplied bytes and metadata does
not authenticate an external service's claim.

For audit integrity, both `source_snapshot_sha256` (existing P0) and
`milestone_source_snapshot_sha256` (optional evidence inputs) are recorded.
The evidence source, policy and derived actions are checked against the
repository's source snapshot before success. Absence of the optional
milestone file causes no probing, no auto-discovery and no change to
default maintenance routing.

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
