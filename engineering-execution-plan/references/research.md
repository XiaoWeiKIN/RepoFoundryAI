# Research consumer contract

## Contents

- Ownership boundary
- Legacy Research package
- Manifest-bearing Research package
- Research conversion and provenance gate
- ADR/Design conversion and ExecPlan audit handoff
- Compatibility

## Ownership boundary

`engineering-execution-plan` validates concluded Research only as provenance for
a referenced ADR or Design. Research is not an implementation input and cannot
independently authorize an ExecPlan, milestone, Task, or code change. This skill
does not own evidence acquisition, experiments, multi-document corpus
maintenance, or Synthesis authoring. Use the independent `engineering-research`
skill or any producer that emits the compatible repository file contract.

The consumer never imports another skill, executes its script by path, or
assumes how it is installed.

## Legacy Research package

Existing schema-1 packages may contain:

```text
docs/research/completed/r-NNN_slug/
├── RESEARCH.md
├── SYNTHESIS.md
├── notes/
└── artifacts/
```

A legacy package satisfies the Gate only when:

- controller status is `concluded`;
- every Research Question is answered, deferred, or invalidated;
- no blocker is open;
- required sections contain no REQUIRED marker;
- `SYNTHESIS.md` is `sealed` and its body SHA-256 matches.

Legacy compatibility permits consumption; it is not the preferred format for
new Research.

## Manifest-bearing Research package

A new producer adds `manifest: RESEARCH_MANIFEST.json` to the controller:

```text
docs/research/completed/r-NNN_slug/
├── RESEARCH.md
├── RESEARCH_MANIFEST.json
├── SYNTHESIS.md
├── notes/
└── artifacts/
    └── research-snapshot/
```

The manifest is a UTF-8 JSON object with:

- `schema_version: "1"` or current `"1.1"`;
- current manifests also carry `metadata_schema: "1"`,
  `artifact_type: "research-manifest"`, `R-NNN-MANIFEST`, title,
  author/owner, and created/updated provenance;
- matching `research_id`;
- `status: "sealed"`;
- `mode: "managed"` or `"snapshot"`;
- declared roots and entrypoints;
- document records containing package-relative path, byte count, and SHA-256;
- a canonical `payload_sha256`.

The payload digest is SHA-256 over compact, key-sorted UTF-8 JSON after
replacing `payload_sha256` with an empty string.

For concluded Research, every document must resolve inside the Research
package, cannot traverse or use symlinks, and must match its recorded bytes and
digest. Every entrypoint must also appear in the document inventory.

Detailed producer behavior belongs to
`engineering-research/references/manifest.md` in the distribution repository;
consumers need only the contract above.

## Research conversion and provenance gate

Before `new-adr`, Research validation still proves that a proposed decision is
grounded in concluded evidence. Before a v2.8 `new-ep`:

1. collect Research provenance declared by every referenced ADR and Design;
2. require `research_refs` to match that collected set exactly;
3. locate each package in `docs/research/completed/`;
4. validate controller and sealed Synthesis;
5. validate the manifest when declared;
6. reject cancelled, active, missing, unsealed, unsupported, or tampered
   packages;
7. reject any plan Research reference that has no converting ADR or Design.

When Research is legitimately unnecessary, record a specific Gate reason
based on existing accepted decisions, authoritative standards, fixed user
direction, or local reversible scope. “No research was done” is not a reason.
The frontmatter field remains named `research_gate` for schema-2.8 compatibility;
its meaning is conversion/provenance integrity, not permission to develop from
Research.

## ADR/Design conversion and ExecPlan audit handoff

ADR or Design must perform the semantic translation. Do not force their readers
to load the complete corpus. Restate:

- direct conclusion and confidence boundary;
- evidence that materially changes option ranking;
- rejected hypotheses or negative evidence;
- recommendation preconditions and failure modes;
- remaining unknowns and their blocker or acceptance destination;
- which evidence is audit-only.

The manifest provides auditability; the sealed Synthesis provides bounded
decision/design context. In the ExecPlan, identify which ADR/Design converted
each Research reference. Research findings may be summarized as audit context,
but implementation constraints, milestones, and acceptance criteria must be
attributed to the ADR/Design result rather than to Research itself.

A sealed Engineering Benchmark Run may be one evidence source inside Research.
When a Run can change option ranking or contradicts other sources, Research
must interpret it before ADR or Design conversion. When the route is already
accepted and the Run only verifies the final revision, the ExecPlan may consume
the Benchmark contract directly without creating another Research.

Schema 1.1/1.2 concluded Research additionally carries `owner`, `maturity:
review_ready`, `approved_by`, `approved_at`, and `approval_ref`. Consumers
require these fields so an Agent cannot turn mere decision readiness into a
terminal Research state. Schema 1.2 also implements the shared artifact
metadata contract. Schema 1 remains readable only as a legacy contract.

## Compatibility

`epctl` retains legacy Research creation commands temporarily so existing
automation does not break. New instructions route Research production to
`engineering-research`.

A future contract version must remain explicitly versioned. Unsupported
versions fail closed; they are not silently interpreted as schema 1.
