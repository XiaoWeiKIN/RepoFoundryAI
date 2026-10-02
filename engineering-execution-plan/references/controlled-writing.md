# Controlled technical writing

This is RepoFoundry authoring guidance, not a Catalog Specification. It uses
selected clarity principles associated with ASD-STE100 Simplified Technical
English. It does not reproduce that standard or its dictionary, and does not
claim full ASD-STE100 conformance. The official standard is available from
https://www.asd-ste100.org/.

Read the common guidance and the section for the artifact being written. Apply
it to new prose and authorized revisions, not to an entire repository at once.
Artifact contracts, installed Specifications, evidence, and authority boundaries
remain controlling. This guide adds no approval step or lifecycle gate.

## Language and fidelity

Keep the user's requested language; otherwise follow the Skill and repository
language conventions. Use STE-inspired English for English prose. For Chinese
and other languages, use the clarity principles without imposing English
vocabulary, grammar, or word-count rules. Do not translate a document merely to
apply this guide. Keep bilingual versions aligned in meaning and evidence.

Preserve conditions, negation, quantifiers, uncertainty, units, and requirement
strength. Do not replace `MUST` with `SHOULD`, turn a possibility into a fact, or
remove a qualification to shorten a sentence. Keep technical terms, identifiers,
commands, paths, interface names, schema fields, and evidence references exact.
Do not replace distinct operations with one word just because they look similar.

Do not rewrite quoted source text, raw logs, code, or normative source excerpts
for style. Do not change metadata, IDs, required headings, generator markers,
digests, or lifecycle fields. Do not rewrite accepted ADRs, approved snapshots,
sealed Checkpoints, sealed Benchmark bundles, or archived plans in place. Use
the owning workflow's revision or supersession process when a change is needed.

## Common guidance

Use one stable term for each concept. Define an unfamiliar term at first use.
Retain established software terminology, including backpressure, idempotency,
and write-ahead log. A plain synonym is not an improvement if it changes meaning.

Prefer short, complete sentences with one main claim or action. Keep conditions
and exceptions with the claim they limit. Split a sentence when that makes the
logic clearer; do not enforce an arbitrary word limit or produce fragments.
Use connected paragraphs to explain mechanisms and trade-offs, rather than a
sequence of disconnected bullets.

Name the actor when several components or people could perform the action.
Use a direct verb when it is clearer than an abstract noun phrase. Imperatives
can address the operator directly. Passive voice is acceptable when the actor
is irrelevant or unknown; do not invent an actor to avoid it.

Replace an ambiguous reference such as "this", "it", or "the relevant component"
with the actual subject. Put a prerequisite before the action that requires it.
State failure and stop conditions when the source contract supplies them. If a
required detail is unknown, name the gap instead of inventing a command or rule.

Remove filler, idioms, and promotional wording. Support a comparison with its
criterion, evidence, and scope. Words such as "robust" or "significant" are not
banned: a defined statistical term or a supported claim can require them.
Do not invent a measurement to justify an adjective.

Separate observations, interpretations, proposals, decisions, and unknowns.
Keep the evidence and its limits near the claim. Retain negative evidence and
uncertainty. Clear prose must not imply acceptance, approval, completion, or
verification that did not occur.

## ADR

State one concrete decision or proposal, then explain its rationale. Preserve
the ADR's actual status. Identify affected behavior, constraints, alternatives,
and costs. Keep consequences separate from promised outcomes. Preserve stable
constraint IDs and the existing Confirmation and Revisit Triggers sections.
Name the evidence that supports a claimed benefit; do not turn an expected
benefit into a measured result. Writing an ADR does not accept it.

## ExecPlan, Task, and Bugfix

Describe the target, action, prerequisites, expected result, and verification
for each bounded unit of work. Use exact repository commands only when verified.
Keep ordering and failure branches explicit. Distinguish planned work from work
already performed. Separate test execution from acceptance and release authority.
Record actual blockers and recovery information, not "handle as appropriate".

## Checkpoint

State the verified revision, completed work, remaining work, evidence, and
blockers. Keep the current handoff readable without replaying the whole session.
Do not compress away a failure, unresolved condition, or evidence locator.
A stylistic revision does not justify changing sealed history.

## Architecture and Design

Explain the system model before listing files. Name boundaries, ownership,
interfaces, invariants, failure behavior, and material trade-offs. Use paragraphs,
examples, tables, or Mermaid where they explain the mechanism. Distinguish
observed behavior from proposed or approved design. Do not reduce an explanation
to short sentences that no longer establish why the design works.

## Research and Synthesis

Separate observations from interpretations and recommendations. State confidence,
applicability, counterevidence, and remaining unknowns. Explain the reasoning
between evidence and conclusion. Preserve correlation/causation distinctions
and source references. Do not turn review-ready prose into a concluded Research.

## Benchmark Scenario and Result

In a Scenario, state hypotheses, controlled variables, workload, repetitions,
units, thresholds, and failure or stop conditions before measurement. In a
Result, distinguish raw observations from interpretation and report uncertainty.
Do not change a frozen protocol, discard negative results, or rewrite an outcome
for readability. A valid digest does not prove experimental validity.

## Case Study

Use the common guidance with a lighter narrative style. Preserve the central
claim, causal explanation, examples, and trade-offs. Do not force an article into
maintenance instructions. Keep claims traceable and respect publication and
redaction boundaries. A polished article does not become a normative source.

## Examples for ADR and ExecPlan

These examples illustrate wording, not facts about a target repository.

Given an unaccepted proposal to use a read cache, a database that remains the
source of truth, and a specified fallback on cache-read failure:

> Proposed decision: Use a cache for reads. If a cache read fails, read from the
> database. The database remains the source of truth. The latency effect has not
> been measured.

Given an authorized task to run RepoFoundry's repository check, with no release
authorization:

> Run `python3 -B scripts/check.py` from the repository root. If the check fails,
> record the failure and keep the task open. If it passes, record the command,
> exit status, and tested revision. Passing this check does not authorize release.

Do not replace either example with an unsupported claim such as "the system is
now more robust" or omit its status, failure branch, or evidence limitation.

## Review before handoff

Compare the revision with its sources. Check terminology, actors, references,
conditions, uncertainty, requirement strength, evidence, and lifecycle status.
Correct misleading prose within the authorized scope. Report unresolved gaps
without filling them with invented facts. Then run the artifact's existing
validators; writing review is not a substitute for them.

Sentence length and keyword matches can identify review candidates. They cannot
prove clarity, truth, authorization, or ASD-STE100 compliance. Do not label a
heuristic pass as semantic verification or add a blocking style gate.

## Distribution maintenance

The distribution source is `references/controlled-writing.md`. Each professional
Skill contains an identical file at that relative path so it works independently
and offline. These are packaged copies, not separate policy owners. From the
RepoFoundry source checkout, run `python3 scripts/sync_controlled_writing.py` to
check them or add `--apply` to refresh them after editing the source. Repository
tests check both copy integrity and the Skill reading links. Those tests do not
measure an LLM's adherence to the writing guidance.
