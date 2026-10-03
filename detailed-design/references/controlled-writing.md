# Controlled technical writing

This is RepoFoundry authoring guidance, not a Catalog Specification. It combines
selected Google developer-documentation principles with STE-inspired clarity.
It does not reproduce ASD-STE100 or its dictionary, claim full ASD-STE100
conformance, or imply endorsement by Google or ASD.

Read the common guidance and the section for the artifact being written. Apply
it to new prose and authorized revisions, not to an entire repository at once.
Artifact contracts, installed Specifications, evidence, and authority boundaries
remain controlling. Project-specific writing conventions take precedence over
these editorial defaults. This guide adds no approval step or lifecycle gate.

The sources at the end explain the editorial background. This local guide is
self-contained: do not fetch external guides for each writing task or treat a
later upstream edit as an automatic change to the project's contract.

## Language and fidelity

Keep the user's requested language; otherwise follow the Skill and repository
language conventions. Use STE-inspired English for English prose. For Chinese
and other languages, use the clarity principles without imposing English
vocabulary, grammar, capitalization, or word-count rules. Do not translate a
document merely to apply this guide. Keep bilingual versions aligned in meaning
and evidence.

Preserve conditions, negation, quantifiers, uncertainty, units, and requirement
strength. Preserve the defined meanings of `MUST`, `SHOULD`, and `MAY`; do not
replace them as a style edit. Clarify ambiguous advice in ordinary prose only
when the source establishes whether it is required, recommended, or optional.
Otherwise report the ambiguity. Keep technical terms, identifiers, commands,
paths, interface names, schema fields, and evidence references exact. Do not
replace distinct operations with one word just because they look similar.

Use present tense for established behavior, not to turn a proposed feature into
current behavior. Distinguish historical, proposed, approved, implemented, and
verified states. A public product guide need not describe unreleased features;
a design proposal must still describe its intended behavior as a proposal.

Do not rewrite quoted source text, raw logs, code, or normative source excerpts
for style. Do not change metadata, IDs, required headings, generator markers,
digests, or lifecycle fields. Do not rewrite accepted ADRs, approved snapshots,
sealed Checkpoints, sealed Benchmark bundles, or archived plans in place. Use
the owning workflow's revision or supersession process when a change is needed.

## Reader and document structure

Before drafting, identify the reader's task, existing knowledge, and what they
need to understand, decide, or do next. Use the request and project context;
ask only when missing information would change the result. Keep this planning
lightweight. It does not require a separate brief or an Audience section.

Open with the answer, system model, or actionable result the reader needs, and
its material limits. Define scope and relevant exclusions without filling a
universal outline. Introduce concepts before implementation details. Give one
representative flow or example, then link to deeper explanations as needed.
Do not substitute a directory inventory for a system explanation.

Give each paragraph one main point, then explain its mechanism, evidence, or
consequence. Preserve useful transitions and causal links. Use lists for steps
or parallel items and tables for repeated comparable fields, not as a way to
split every explanation into fragments. A shorter document is not necessarily
a clearer one. Omit empty headings and unrelated template sections.

Keep one owner for a normative fact and link to it from other documents. When
an authorized code change affects maintained documentation, update the relevant
current explanation with that change. Historical design records remain history,
not proof of current implementation. Report drift; do not rewrite sealed history
or expand a local edit into a repository-wide cleanup.

## Common guidance

Use one stable term for each concept. Define an unfamiliar term at first use.
Retain established software terminology, including backpressure, idempotency,
and write-ahead log. A plain synonym is not an improvement if it changes meaning.

Prefer short, complete sentences with one main claim or action. Keep conditions
and exceptions with the claim they limit. Split a sentence when that makes the
logic clearer; do not enforce an arbitrary word limit or produce fragments.
Use connected paragraphs to explain mechanisms and trade-offs, rather than a
sequence of disconnected bullets. Use a direct, respectful tone; avoid both
bureaucratic phrasing and forced informality. Address the reader as "you" in
instructions when helpful, without changing the actor in a system description.

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

## Procedures and examples

Before an action, state the necessary environment, working directory, inputs,
permissions, and prerequisites. Use numbered steps when order matters, normally
one action per step. Put a condition before the action it controls, and describe
the expected result after the action. Label optional steps and failure branches.
Choose the procedure supported by project evidence; do not invent a preferred
method or recovery command merely to make the instructions look complete.

Introduce each command's purpose. Explain placeholders and which values the
reader must supply; distinguish commands from output. Show only relevant output
and identify illustrative output as such. Separate preview, apply, verification,
and release. Documenting a command does not authorize executing it. Check examples
against the stated interface or implementation, and report whether they were
actually run. Never label an unexecuted example as tested.

## Headings, code, and links

Use specific headings that help the reader find a task or concept. Prefer action
headings for tasks and noun phrases for concepts. In English, use sentence case
unless the project requires otherwise; preserve proper names and identifiers.
Keep a logical heading hierarchy without renaming contract-required headings or
breaking existing anchors just to change style.

Use code formatting for identifiers, paths, commands, and literal values. Refer
to UI controls by their actual labels, typically in bold. Use descriptive link
text that identifies the destination, not "click here". Prefer repository-relative
links for local documentation. Pin evidence to an appropriate revision or stable
locator when a changing page would no longer support the claim.

## Accessible explanation surfaces

Choose a diagram only when it explains a relationship or process; prefer Mermaid
for editable technical diagrams. State the conclusion and essential relationships
in prose or a readable list or table as well. Mermaid source alone is not a text
alternative for a reader unfamiliar with its syntax. Provide purposeful alt text
for informative images and empty alt text for purely decorative images. Keep code
and command output as selectable text rather than screenshots.

Do not communicate state solely through color, position, animation, or sound.
For HTML or interactive views, use semantic headings, labeled controls, visible
keyboard focus, and keyboard-accessible actions. Keep the reading order coherent
and provide a static explanation when interaction is unavailable. For video,
provide captions or a transcript and a description of essential visual changes.
Offer pause or reduced-motion behavior where animation is used; avoid flashing.

Keep source revisions, assumptions, uncertainty, and authority limits visible in
all formats. Mark simulation and illustrative timing as such; animation is not
measurement evidence. A view is disposable and is not a second fact owner.
Check the actual rendered output when tools permit. Report unchecked keyboard,
screen-reader, media, or rendering behavior as unverified, not accessible by
assertion. These authoring instructions do not certify existing renderers.

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

Review technical correctness first, then follow the document as its intended
reader. Can the reader find the answer, follow the procedure or mechanism, and
locate its limits and evidence? Compare the revision with its sources. Check
terminology, actors, references, conditions, uncertainty, requirement strength,
and lifecycle status. Check the applicable formatting and accessibility guidance.
Correct misleading prose within the authorized scope; report unresolved gaps
without invented facts. Run the artifact's existing validators and distinguish
editorial review from command execution, rendering tests, and acceptance.

Sentence length and keyword matches can identify review candidates. They cannot
prove clarity, truth, authorization, or ASD-STE100 compliance. Do not label a
heuristic pass as semantic verification or add a blocking style gate.

## Sources and local adaptations

The following public sources inform these editorial defaults. RF's precedence,
lifecycle, source-integrity, and offline-use boundaries are local adaptations;
these sources do not define RF artifact contracts or Google's internal ADR format.
They are optional references, not task-time dependencies.

Google Developer Documentation Style Guide: reference hierarchy and formatting
highlights: https://developers.google.com/style/ and
https://developers.google.com/style/highlights

Google Technical Writing: audience needs and document organization:
https://developers.google.com/tech-writing/one/audience and
https://developers.google.com/tech-writing/one/documents

Google guidance on procedures, voice, and accessibility:
https://developers.google.com/style/procedures,
https://developers.google.com/style/tone, and
https://developers.google.com/style/accessibility

Google guidance on modal wording and tense (adapted to preserve RF requirements
and proposal states): https://developers.google.com/style/prescriptive-documentation
and https://developers.google.com/style/tense

Google repository documentation maintenance:
https://google.github.io/styleguide/docguide/best_practices.html

ASD-STE100 official information: https://www.asd-ste100.org/.
STE permits technical names and technical verbs under its rules; retaining
software terminology is not itself a departure from STE. This guide selects
clarity principles rather than implementing the full standard or its dictionary.

## Distribution maintenance

The distribution source is `references/controlled-writing.md`. Each professional
Skill contains an identical file at that relative path so it works independently
and offline. These are packaged copies, not separate policy owners. From the
RepoFoundry source checkout, run `python3 scripts/sync_controlled_writing.py` to
check them or add `--apply` to refresh them after editing the source. Repository
tests check both copy integrity and the Skill reading links. Those tests do not
measure an LLM's adherence to the writing guidance.
