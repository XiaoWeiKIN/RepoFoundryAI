# Examples

## End-to-end worked example

The distribution repository contains
`examples/cache-topology/README.md` and a four-document corpus. It demonstrates
one linked Research with an `index.md` entrypoint, three answered Research
Questions, a bounded Synthesis, a sealed snapshot, an explicitly authorized
ADR that converts the Research, and an ExecPlan that consumes the ADR while
retaining Research only as audit provenance.

The expected Research conclusion selects a five-second process-local L1 plus a
30-second Redis L2. It preserves the faster-but-invalid L1-only result as
negative evidence and proposes Redis outage and invalidation backlog checks for
ADR/Design conversion. The Research does not send development work directly to
the ExecPlan. The example is written as a Codex conversation: users express intent,
constraints, and authority through prompts; this Skill invokes `researchctl`
internally and reports the resulting artifacts.

## Managed research

```text
Use $engineering-research to investigate cache selection in this repository.
The Research Owner is Cache Platform Owner and the author is Codex.
Create a managed technical Research, identify the decision-relevant questions,
and stop after reporting the new Research ID, document paths, and validation
status. Do not conclude it.
```

Create decision-relevant deep dives as structured topics:

```text
Continue R-001 with $engineering-research.
Create a structured topic for RQ-001 titled "Cache eviction semantics".
Build a mental model, show the analysis instead of only conclusions, preserve
counterevidence, and link every material claim to auditable evidence.
```

When the Skill creates a topic, it allocates a stable Research-scoped
`RT-NNN`, links the document from the current Round, and refreshes the
manifest. The resulting schema 2.3 document is learning-first and carries the
common artifact metadata: a brief for
quick decisions, a mental model and continuous `A-NNN` analysis for learning,
then an `E-NNN` evidence index and `S-NNN` sources for review. Use a full
cross-topic reference such as
`R-001/RT-001/A-002`; ordinary notes may still be written under `notes/`.
The Skill refreshes the manifest after topic creation and after any manual
corpus membership change.

## Adopt an existing corpus

```text
Use $engineering-research to take over the existing multi-document corpus at
_bmad-output/planning-artifacts/research/spans-aggregate/.
Use index.md as the entrypoint, keep every source document in place, assign
Observability Owner as Research Owner, and create one linked Research only if
the documents share a single decision purpose. Report broken links or scope
conflicts before changing the corpus.
```

The source directory remains unchanged while active. Fix missing local
references, fill the controller and Synthesis, then ask for a review boundary:

```text
Continue R-001 with $engineering-research. Answer or explicitly dispose every
Research Question, update the Synthesis with recommendation, counterevidence,
uncertainty, and decision impact, refresh the manifest, and validate the whole
package. If it is ready, mark it review-ready but do not conclude it.
```

The default transition content-addresses the current Synthesis without copying
another file. For a formal review, downstream handoff, or material decision
milestone, explicitly ask the Skill to preserve a full Synthesis snapshot.

If review asks for deeper HTTP security analysis, continue the same Research:

```text
The R-001 review found an unresolved HTTP transport security boundary.
Use $engineering-research to open a new Round under the same Research ID,
create the necessary structured topics, and revise the Synthesis after
investigation. Do not append new evidence to the completed Round.
```

Create any new structured topic only after the Skill opens the new Round, so
the topic is attributed to the correct inquiry.

Only after the Research Owner explicitly authorizes conclusion:

```text
I am the Observability Owner. R-001 is sufficient for the current decision.
Use $engineering-research to conclude and archive it, and record this message
as the explicit Owner approval.
```

The completed package contains the linked corpus snapshot, Round history,
selected Synthesis milestones, and a sealed final Synthesis; the original
corpus still exists at its original path.

## Multiple roots and entrypoints

```text
Use $engineering-research to study the storage contract.
Inspect docs/current-storage/ and experiments/storage/, using index.md and
results.md as candidate entrypoints. Keep one Research only if both roots serve
the same decision and can share one Synthesis; otherwise create two Research
packages and explain the split.
```

Use one Research only when the roots share the same decision purpose and
conclusion. Otherwise create two Research IDs and let the downstream decision
reference both sealed Syntheses.

## Multiple rounds in one Research

Keep one ID when a first version is followed by focused discussion, source
verification, a new experiment, or a challenge to one finding. Each new Round
has a small controller under `rounds/`; detailed work continues in any number
of corpus documents. `SYNTHESIS.md` accumulates the latest view, while
`snapshots/synthesis-vNNN.md` preserves only selected full milestones. Snapshot
revisions may have gaps. Identical Synthesis bodies reuse the earlier snapshot,
and conclusion ensures the latest unique review body is preserved.

Do not ask the Skill to conclude merely because the first review revision is
decision-ready.

## Process a Deep Research report

Keep the original report as one corpus document, create focused notes only for
decision-relevant analysis, and use Synthesis for the bounded handoff. Do not
discard the original or treat the generated report's claims as verified
without checking its cited sources.
