# Engineering Research workflow

## Contents

- Purpose and routing
- Research Questions
- Evidence and experiments
- Multi-document organization
- Synthesis
- Conclusion and refresh

## Purpose and routing

Create one Research identity for one decision purpose. A Research may contain
many documents and entrypoints. Split identities when ownership, conclusion
timing, or downstream reuse is independent.

Research reduces uncertainty; it does not silently make a durable architecture
decision. A Synthesis may recommend an option, while acceptance belongs to the
downstream decision authority.

## Research Questions

Use stable `RQ-NNN` rows in `RESEARCH.md`:

- `open`: evidence is still required.
- `answered`: evidence supports an answer.
- `deferred`: the question does not change the present decision and has an
  explicit future destination or trigger.
- `invalidated`: its premise is false or no longer relevant, with evidence.

Concluded Research cannot contain open questions or open blockers. Completion
depends on decision readiness, not document count.

## Evidence and experiments

For each load-bearing claim, retain a repository path, stable authoritative
source, or reproducible experiment.

An experiment records:

- hypothesis and falsifying observation;
- working directory, command, input, and environment;
- raw observation without inference;
- interpretation and effect on option ranking;
- evidence path;
- prototype promotion, retention, or deletion decision.

Prefer source code and tests for implementation behavior. Record source
freshness and confidence for external claims. Preserve contradictory evidence
instead of averaging it away.

## Multi-document organization

Use the corpus documents for focused topics, sources, matrices, experiments,
or interface contracts. Keep an existing `index.md` when it already provides
a useful reading route. Do not rename or flatten documents merely to satisfy a
template.

Keep `RESEARCH.md` small:

- purpose and downstream decision;
- Current Snapshot and exact next inquiry;
- all decision-relevant Research Questions;
- method and source-selection logic;
- concise findings and evidence paths;
- contradictions, uncertainty, drivers, options, blockers, and progress.

Use `sync-research` after membership changes. Resolve missing local references
before conclusion. Absolute source paths are provenance warnings because other
machines cannot reproduce them without an alternate source.

## Synthesis

`SYNTHESIS.md` is the single bounded handoff even when the corpus contains many
documents. It contains:

- direct answer to the Research purpose;
- supported findings with confidence and manifest paths;
- rejected hypotheses;
- remaining unknowns and their destinations;
- option comparison against Decision Drivers;
- recommendation and preconditions;
- durable downstream constraints and audit-only evidence.

Do not copy the corpus into Synthesis. A reader should understand the
recommendation without loading all evidence, while still being able to audit
each claim.

## Conclusion and refresh

Before `archive-research --outcome concluded`:

1. Run `sync-research`.
2. Run `validate`.
3. Answer or dispose every Research Question.
4. Resolve every blocker.
5. Remove all REQUIRED markers from controller and Synthesis.
6. Confirm the recommendation is decision-ready.

The command snapshots linked documents, seals the manifest and Synthesis, and
moves the control package to `completed/`. New evidence that changes the
conclusion creates a new Research identity; never edit a sealed conclusion.

Cancelled Research requires a reason, remains auditable, and cannot satisfy a
downstream Research Gate.
