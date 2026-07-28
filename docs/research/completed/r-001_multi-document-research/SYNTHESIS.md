---
schema_version: "1"
parent_id: R-001
title: "Model multi-document Research workspaces — Synthesis"
status: sealed
created: 2026-07-28
updated: 2026-07-28
payload_sha256: 05b77767342ea148e88c6ab40554f525f83d44423f42fe776b7a765ddbf2a3eb
---

# Model multi-document Research workspaces — Synthesis

This Synthesis is the bounded decision interface between Research and ADR or
ExecPlan. Once sealed, changing its body invalidates the recorded SHA-256.

## Executive Conclusion

Model Research as a control record around a versioned document set, not as one
Markdown payload. Preserve one bounded `SYNTHESIS.md` as the interface to ADR
and ExecPlan. Add an explicit manifest that can register an existing
repository-relative corpus, refresh its membership during active work, and
seal per-document digests. Linked documents should be snapshotted into the
Research package when the Research concludes so historical conclusions remain
self-contained without requiring Git.

The evidence is sufficient for an architecture decision and implementation
plan.

## Supported Findings

| Finding | Confidence | Evidence |
|---|---|---|
| A real Research can be an indexed graph of many topic documents. | high | `notes/real-world-corpus.md` |
| The current tool does not validate or seal the `notes/` document set. | high | `scripts/epctl.py`; `notes/real-world-corpus.md` |
| A manifest plus one Synthesis separates evidence scale from downstream context size. | high | `notes/real-world-corpus.md`; `notes/tool-landscape.md` |
| Existing corpora need a non-destructive linked mode during active research. | high | `notes/real-world-corpus.md` |
| Linked documents require a conclusion snapshot when Git cannot be assumed. | medium | `notes/real-world-corpus.md` |

## Rejected Hypotheses

- **One `RESEARCH.md` can carry all evidence:** rejected by the supplied
  211-KB corpus and the existing bounded-controller requirement.
- **The filesystem alone is a sufficient manifest:** rejected because the
  supplied corpus already contains a missing dependency and portability
  problems that directory enumeration cannot explain.
- **Hashing Synthesis alone seals the Research:** rejected because a valid hash
  proves only that the summary did not change, not that its cited document set
  remains available.
- **Git can always preserve linked documents:** rejected because ExecutionPlan
  intentionally supports repositories without Git.

## Remaining Unknowns

- A later version may support Git-object or content-addressed snapshots for
  very large corpora. This does not block a Markdown-first implementation.
- Binary evidence needs size and storage policy beyond document manifests. It
  remains governed by `artifacts/` and is not copied automatically.
- Multiple entrypoints may be useful. The manifest should allow a list even if
  the initial CLI commonly receives one.

## Options Comparison

| Option | Existing corpus | Historical integrity | Compatibility | Complexity |
|---|---|---|---|---|
| Canonical-only package | poor | strong | strong | low |
| Live linked corpus | strong | weak | strong | medium |
| Linked-active, snapshotted-conclusion | strong | strong | strong | medium |
| In-place registry | strong | medium | weak | high |

Linked-active, snapshotted-conclusion is the only option that satisfies
non-destructive adoption, agent independence, bounded downstream context, and
Git-independent auditability together.

## Recommendation and Preconditions

Adopt **linked-active, snapshotted-conclusion** with backward compatibility:

1. Keep the canonical Research control package and stable `R-NNN` identity.
2. Add a JSON manifest referenced by `RESEARCH.md`.
3. Support managed documents under the package and linked
   repository-relative corpus roots.
4. Add deterministic manifest refresh and local-link validation.
5. On conclusion, snapshot declared linked documents into the package, record
   per-file SHA-256 values, seal the manifest, then seal Synthesis.
6. Keep old Research packages without manifests readable and valid.
7. Keep raw binary artifacts outside automatic document snapshotting.

The recommendation assumes linked corpus paths remain inside the target
repository during active work and that automatic snapshots are limited to
declared research documents.

## Handoff to ADR and ExecPlan

Create an ADR for the Research identity and conclusion-integrity model. The ADR
must decide whether a control record plus manifest is authoritative, whether
linked documents are snapshotted at conclusion, and how v1 packages remain
compatible.

The ExecPlan must restate:

- the manifest schema and path-resolution rules;
- CLI behavior for creation, linking, refresh, validation, and archive;
- snapshot transaction and rollback behavior;
- link, symlink, traversal, drift, and tamper validation;
- migration and test coverage for v1 packages.

Detailed tool comparisons and the proprietary source corpus inventory are
audit-only and need not be copied into the ExecPlan.

## Revision Notes

- 2026-07-28T08:13:12Z — Draft Synthesis created with R-001.
- 2026-07-28T08:28:00Z — Replaced placeholders with the decision-ready
  multi-document Research recommendation.
