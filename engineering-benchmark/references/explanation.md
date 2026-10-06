# Progressive Benchmark explanations

A sealed Benchmark Run may have a disposable visual explanation generated after
sealing. The explanation helps a reader follow the experimental question,
observed difference, diagnostic evidence, mechanism interpretation, and limits.
It does not modify the Run, change its outcome, accept an architecture decision,
or replace statistical review.

The visual method uses progressive disclosure: introduce one question, then one
evidence layer at a time. This is useful for mechanism explanations because a
reader can see which part is measured, which part is derived, and which part
remains a hypothesis. Animation is a reading aid, not another experiment.

## Scientific boundary

The sealed Scenario, Result, artifacts, and Evidence Manifest remain the facts.
Before rendering, the tool reuses `benchctl` to verify the Run's complete local
Manifest inventory and payload SHA-256. If any sealed file changed, rendering
fails.

Every explanation claim has one of four kinds:

| Kind | Meaning | Minimum evidence |
|---|---|---|
| `observation` | A measured result from this Run | measurement |
| `derived` | Arithmetic or another declared transformation of measurements | measurement + explicit derivation |
| `hypothesis` | A possible explanation that remains unproven | any sealed evidence that motivates it |
| `mechanism` | A bounded mechanism interpretation | measurement + diagnostic + version-matched source |

The renderer checks that those evidence categories are present and that every
referenced path is sealed by the Run Manifest. It cannot determine whether the
author classified an artifact correctly or whether the experiment establishes
causality. A complete three-part evidence chain therefore means "eligible for a
mechanism interpretation in this view", not "causality certified".

Timing data alone cannot be promoted to a mechanism claim. Keep it as an
observation or hypothesis until discriminating diagnostics and matching source
evidence exist.

## Input model

The renderer accepts `repofoundry.benchmark-explanation/v1` JSON. The input is
an authored projection, not a replacement for RESULT.md. It binds to one sealed
Run through:

- Run, Suite, and Scenario IDs;
- sealed outcome;
- subject and harness revisions;
- Evidence Manifest payload SHA-256.

It also contains:

- the reader question and summary;
- predeclared predictions, falsifiers, and supported / falsified / inconclusive status;
- evidence labels and their sealed paths;
- typed claims and evidence references;
- measured baseline/candidate metric summaries with sample counts and uncertainty;
- optional baseline/candidate mechanism steps;
- explicit limitations.

Metric summaries must point to sealed measurement evidence. The view shows
sample counts and the author's uncertainty/dispersion text. It does not recompute
statistics from arbitrary artifact formats and cannot change the official
decision rule or outcome.

## Generate a view

Use the Engineering Benchmark Skill's script from a full Skill installation:

```bash
python3 <engineering-benchmark-dir>/scripts/explain_benchmark.py \
  --repo <target-repository> \
  --run BR-001 \
  --input /path/to/benchmark-explanation.json \
  --output /tmp/br-001-explanation
```

The default is a dry run. Add `--apply` only after inspecting the planned
destination. The output directory must be new and must stay outside the sealed
Run directory.

The bundle contains:

```text
benchmark-explanation.json
index.html
render-manifest.json
```

The HTML is self-contained and offline. It uses a SHA-256 CSP for executable
script, makes no network request, and displays five reading stages:

1. question, predeclared predictions, falsifiers, and prediction status;
2. measured difference;
3. measurement / diagnostic / source evidence chain;
4. baseline/candidate mechanism explanation;
5. limits and the sealed Run identity.

Play/pause only changes reading progression. It does not simulate intermediate
benchmark values, invent unmeasured workload points, interpolate causal effects,
or modify the source data. `prefers-reduced-motion` disables the metric-bar
transition.

## Authoring guidance

Start from the sealed Result and Scenario rather than from the visual story you
want to tell.

- Keep the Run outcome exactly as sealed.
- Copy prediction meaning and falsifiers from the predeclared Scenario; do not reconstruct them from the Result.
- Keep falsified and inconclusive predictions visible.
- Use the same units, sample counts, aggregation, and uncertainty definition as
  the Result.
- Do not convert a percentage difference into a mechanism explanation.
- Put profile, trace, compiler/runtime diagnostics, or actual I/O evidence in
  the sealed Run when a mechanism claim depends on them.
- Put version-matched source evidence in the sealed Run when it is required for
  the interpretation.
- If evidence conflicts, show the conflict as a limitation instead of smoothing
  the animation into one story.
- Keep simulations and hypothetical mechanism diagrams labelled as hypotheses.

A polished animation is not scientific validation. The Scenario protocol,
measurement validity, repeated observations, uncertainty analysis, and sealed
evidence remain controlling.
