# Examples

## Managed research

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug cache-selection --title "Research cache selection"
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
  --corpus-root _bmad-output/planning-artifacts/research/spans-aggregate \
  --entrypoint _bmad-output/planning-artifacts/research/spans-aggregate/index.md
```

The source directory remains unchanged while active. Fix missing local
references, fill the controller and Synthesis, then conclude:

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . sync-research R-001
python3 <skill-dir>/scripts/researchctl.py --repo . validate
python3 <skill-dir>/scripts/researchctl.py --repo . archive-research R-001 \
  --outcome concluded
```

The completed package contains a snapshot; the original corpus still exists at
its original path.

## Multiple roots and entrypoints

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug storage-contract \
  --title "Research storage contract" \
  --corpus-root docs/current-storage \
  --corpus-root experiments/storage \
  --entrypoint docs/current-storage/index.md \
  --entrypoint experiments/storage/results.md
```

Use one Research only when the roots share the same decision purpose and
conclusion. Otherwise create two Research IDs and let the downstream decision
reference both sealed Syntheses.

## Process a Deep Research report

Keep the original report as one corpus document, create focused notes only for
decision-relevant analysis, and use Synthesis for the bounded handoff. Do not
discard the original or treat the generated report's claims as verified
without checking its cited sources.
