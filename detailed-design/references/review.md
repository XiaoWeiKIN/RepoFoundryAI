# Detailed design review

Review engineering risk before prose quality. Group repeated symptoms under one root finding.
Use this review after drafting or revising, not only in review mode. For common
editorial rules, use the local [controlled-writing guide](controlled-writing.md).

## Finding format

```text
Finding
Severity: blocker / high / medium / low
Claim or location
Why the design is incomplete or inconsistent
Concrete failure mode
Recommended design change
Verification needed
```

Tie severity to a concrete engineering or reader-task impact. Do not label an
optional stylistic preference as a blocker. For a reading issue, name the task
that fails and the smallest useful correction; do not invent a technical failure.

## Review lenses

- Mental model: no coherent end-to-end explanation, or the document is only a directory/type inventory.
- Fact ownership: a normative fact has multiple owners, no owner, or is delegated without a stable reference.
- Boundaries: parser/analyzer/planner/runtime, logical/physical, product/core, or transport/domain responsibilities overlap.
- State and lifetime: mutable aliases, multiple writers, invalidation, cleanup, retry, cancellation or recovery are undefined.
- Illegal states: nil/empty/zero, mutually exclusive fields, defaults or open containers have ambiguous semantics.
- Evolution: compatibility surface, activation gate, versioning, mixed-version behavior or exhaustive consumers are missing.
- Verification: a strong claim has only examples, no negative case, no failure injection or no measurable workload.
- Freshness: code links do not support the prose, target/current behavior is mixed, or no owner can detect drift.

For architecture documentation, also check that a contributor can follow a real request/data/state flow and then reach the relevant implementation without first reverse-engineering the repository.

## Walk through the reader's task

After the engineering review, follow one representative reading path rather
than merely counting headings or measuring sentence length:

1. Read the opening as the intended reader. Can they identify the question,
   scope, prerequisites, and current or proposed system model without first
   learning the repository layout?
2. Follow one request, datum, or resource. Can they explain each transition,
   its owner, and at least one failure or invalidating condition? Check that
   shortening prose has not removed the causal explanation.
3. Where the document supplies instructions, trace the prerequisites, working
   directory, placeholders, actions, expected results, and stop conditions.
   Compare with the actual interface. Do not execute mutating examples merely
   to complete a document review.
4. Follow evidence links and source locators. Do they support the claims at the
   stated revision? Compare only against an identified baseline. Keep measured,
   inferred, simulated, proposed, and unknown behavior distinct.
5. Read without the diagram, color, animation, or audio. Are the essential facts
   still available? For generated views, check the applicable keyboard, labels,
   text alternatives, captions or transcript, and rendering behavior from the
   common guide. Do not claim checks that were unavailable.

A polished summary or diagram does not compensate for missing conditions or
unsupported claims. These questions guide the review; they are not mandatory
sections in the document or a new acceptance gate.

## Report and revise within scope

For review-only requests, return findings without rewriting files. For authorized
revisions, make the smallest correction, then compare meaning and evidence before
and after. Preserve defined `MUST` / `SHOULD` / `MAY` strength, technical terms,
contract headings, and lifecycle state. Do not alter accepted or sealed history
for style; use the owning workflow when a governed revision is necessary.

Separate editorial inspection, source checks, executed commands, and rendered
accessibility tests in the handoff. Report what remains unverified. A documented
command or a parseable Mermaid block is not proof of successful execution or an
accessible rendered document. Keep the existing artifact validators in use.
