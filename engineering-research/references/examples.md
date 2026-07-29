# Examples

## End-to-end worked example

The distribution repository contains
`examples/cache-topology/README.md` and a four-document corpus. It demonstrates
one linked Research with an `index.md` entrypoint, three answered Research
Questions, a bounded Synthesis, a sealed snapshot, an explicitly authorized
ADR, and a gated ExecPlan.

The expected Research conclusion selects a five-second process-local L1 plus a
30-second Redis L2. It preserves the faster-but-invalid L1-only result as
negative evidence and sends Redis outage and invalidation backlog tests to the
ExecPlan. Use this example when a user needs to see the contents of each
handoff, not only the CLI sequence.

## Managed research

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug cache-selection --title "Research cache selection" \
  --owner "Cache Platform Owner" --author "Codex" \
  --research-type technical
```

Write focused documents under the generated `notes/` directory, then refresh:

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . sync-research R-001
```

## Adopt an existing corpus

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug spans-aggregate \
  --title "Research spans aggregate" \
  --owner "Observability Owner" \
  --author "Codex" \
  --corpus-root _bmad-output/planning-artifacts/research/spans-aggregate \
  --entrypoint _bmad-output/planning-artifacts/research/spans-aggregate/index.md
```

The source directory remains unchanged while active. Fix missing local
references, fill the controller and Synthesis, then create a review checkpoint:

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . sync-research R-001
python3 <skill-dir>/scripts/researchctl.py --repo . validate
python3 <skill-dir>/scripts/researchctl.py --repo . mark-review-ready R-001
```

If review asks for deeper HTTP security analysis, continue the same Research:

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . new-round R-001 \
  --slug http-security \
  --title "Deep dive into HTTP transport security" \
  --author "Security Reviewer"
```

Only after the Research Owner explicitly authorizes conclusion:

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . conclude-research R-001 \
  --approved-by "Observability Owner" \
  --approval-ref "review:OBS-123"
```

The completed package contains the linked corpus snapshot, Round history and
review-ready Synthesis revisions; the original corpus still exists at its
original path.

## Multiple roots and entrypoints

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug storage-contract \
  --title "Research storage contract" \
  --owner "Storage Owner" \
  --author "Codex" \
  --corpus-root docs/current-storage \
  --corpus-root experiments/storage \
  --entrypoint docs/current-storage/index.md \
  --entrypoint experiments/storage/results.md
```

Use one Research only when the roots share the same decision purpose and
conclusion. Otherwise create two Research IDs and let the downstream decision
reference both sealed Syntheses.

## Multiple rounds in one Research

Keep one ID when a first version is followed by focused discussion, source
verification, a new experiment, or a challenge to one finding. Each
`new-round` creates a small controller under `rounds/`; detailed work continues
in any number of corpus documents. `SYNTHESIS.md` accumulates the latest view,
while `snapshots/synthesis-vNNN.md` preserves each review checkpoint.

Do not run `conclude-research` merely because the first review snapshot is
decision-ready.

## Process a Deep Research report

Keep the original report as one corpus document, create focused notes only for
decision-relevant analysis, and use Synthesis for the bounded handoff. Do not
discard the original or treat the generated report's claims as verified
without checking its cited sources.
