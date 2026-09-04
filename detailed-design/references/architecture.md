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

## Explain abstractions through behavior

For each core abstraction, answer:

- Why does it exist?
- What does it own and explicitly not own?
- What enters and leaves it?
- Which invariant does it establish or preserve?
- How does it compose or extend?
- Which concrete type, module, test, or API proves the description?

Do not lead with a package tree. A code map is useful only after the reader understands the concepts it maps.

## Architecture review questions

- Can a reader redraw the system after the overview?
- Can they trace a real request, datum, state transition, or resource through it?
- Are logical, physical, transport, runtime, and product concerns separated?
- Are extension points distinguished from internal implementation seams?
- Are examples clearly examples rather than normative owners?
- Do source links support the claim, and is likely drift visible?
