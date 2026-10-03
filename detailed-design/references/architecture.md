# Architecture documentation method

Use this reference for system architecture, internals, contributor architecture, and subsystem-overview documents.

## Start from the reader

Choose the primary reader before choosing sections:

| Reader | Needs first |
|---|---|
| library or platform user | capabilities, stable abstractions, extension points |
| contributor | end-to-end flow, boundaries, code map, safe change points |
| maintainer | ownership, invariants, failure behavior, evolution pressure |
| reviewer | selected shape, alternatives, risks, verification |

If audiences need incompatible detail, keep one overview and link focused deep dives. Do not interleave beginner orientation with implementation minutiae.

For the chosen reader, identify what they already know and the question they
must answer after reading. For a contributor, that might be where to add a
behavior without violating an invariant; for a reviewer, which failure makes
an option unacceptable. Explain unfamiliar project concepts before using them.
This is planning for the existing document, not a new brief or required section.
Use the local [controlled-writing guide](controlled-writing.md) for common
organization, procedures, formatting, and accessibility rules.

## Scale to a documentation set only when needed

One focused Markdown document is the default. When a topic has genuinely
independent reader routes or separately maintained deep dives, use this
Technical Architecture Docs vocabulary selectively:

```text
README.md
how-it-works/
core-concepts/
subsystems/
extension-points/
deep-dives/
contributor-guide/
```

`README.md` owns the overview and reading routes. A directory exists only when
it contains a useful document. Do not create top-level `contracts/`, `data/`,
`operations/`, `migration/`, or `verification/` buckets to mirror a review
checklist; cover those topics inside the architecture document they materially
affect.

## Choose a narrative spine

Prefer one dominant spine:

- request/query lifecycle;
- data flow and transformation stages;
- control-plane lifecycle;
- state/resource lifecycle;
- subsystem composition.

For a query engine, a useful spine may be:

```text
input -> parse -> analyze -> logical plan -> optimize -> physical plan -> execute -> result
```

For each stage state its input, output, owner, facts established, facts deliberately deferred, and failure boundary.

## Build progressive disclosure

A strong architecture document usually moves through:

1. purpose, audience, goals and non-goals;
2. one-page system model;
3. representative end-to-end flows;
4. core abstractions and responsibility boundaries;
5. state, data, runtime or deployment model where material;
6. extension and integration points;
7. failure, resource, security or compatibility constraints that shape the architecture;
8. code map and links to focused deep dives;
9. freshness owner or observable guards when drift is likely.

This is an ordering heuristic, not a required outline. Remove sections that do not help the selected reader.

On revision, explain the material change against a known source version before
repeating stable background. If no comparison is available, state the current
model. A summary must retain the conditions that make that model valid.

Choose representations by the question: diagrams for relationships, tables
for comparable alternatives, and optional interactive views for parameter or
failure exploration. Apply the common guide's text-alternative and interaction
checks. State a demonstration's assumptions and source version; simulation does
not prove implementation behavior. Recheck derived views when their sources
change, keeping the document's existing fact owners authoritative.

## Explain abstractions through behavior

For each core abstraction, answer:

- Why does it exist?
- What does it own and explicitly not own?
- What enters and leaves it?
- Which invariant does it establish or preserve?
- How does it compose or extend?
- Which concrete type, module, test, or API proves the description?

Do not lead with a package tree. A code map is useful only after the reader understands the concepts it maps.

A representative example needs an input, the relevant state or ownership
transition, and an observable result. Add the failure branch that limits the
explanation. Mark hypothetical inputs, pseudocode, and unexecuted examples;
they cannot establish performance or reliability claims. Link maintained current
behavior to implementation evidence, and use historical decisions only for the
rationale they actually record.

## Architecture review questions

- Can a reader redraw the system after the overview?
- Can they trace a real request, datum, state transition, or resource through it?
- Are logical, physical, transport, runtime, and product concerns separated?
- Are extension points distinguished from internal implementation seams?
- Are examples clearly examples rather than normative owners?
- Do source links support the claim, and is likely drift visible?

Before handoff, use [the design review](review.md) to test this reading path,
including what remains understandable without the chosen visual presentation.
