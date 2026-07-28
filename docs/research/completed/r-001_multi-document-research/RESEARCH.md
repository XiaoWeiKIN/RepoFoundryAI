---
schema_version: "1"
id: R-001
title: "Model multi-document Research workspaces"
status: concluded
synthesis: SYNTHESIS.md
created: 2026-07-28
updated: 2026-07-28
owner: "XiaoWeiKIN"
---

# Model multi-document Research workspaces

This Research package is a bounded evidence workspace. Keep this controller
concise; put focused analysis in `notes/`, raw outputs in `artifacts/`, and the
decision-ready conclusion in `SYNTHESIS.md`.

## Purpose and Decision to Enable

Determine how ExecutionPlan should represent, validate, conclude, and archive a
Research that consists of multiple documents, including a pre-existing corpus
outside the canonical `docs/research/` tree. The result must enable a durable
architecture decision without turning every downstream plan into a reader of
the complete corpus.

## Current Snapshot

- Current state: the supplied 11-document corpus and three relevant tool
  families support a control-record plus document-manifest model.
- Next inquiry: convert the recommendation into a proposed ADR and verify its
  compatibility requirements against the current `epctl` tests.
- Open blockers: none.

## Scope and Non-goals

Covers Research identity, document discovery, existing-corpus adoption,
entrypoints, integrity validation, conclusion snapshots, Synthesis boundaries,
and backward compatibility.

Does not choose a general knowledge-base product, replace external
deep-research engines, prescribe the internal outline of every topic document,
or make architecture decisions from the supplied DataFox content.

## Research Questions

| ID | Status | Question | Answer or disposition | Evidence |
|---|---|---|---|---|
| RQ-001 | answered | Is Research a file or a collection? | A Research is an identity and lifecycle around a document set; its controller is not the payload. | `notes/real-world-corpus.md` |
| RQ-002 | answered | How can an existing corpus be adopted without relocation? | Keep a canonical control record that links a repository-relative corpus through an explicit manifest. | `notes/real-world-corpus.md` |
| RQ-003 | answered | How should a multi-document conclusion remain auditable? | Seal one bounded Synthesis plus a per-document digest manifest; snapshot linked documents at conclusion. | `notes/real-world-corpus.md` |
| RQ-004 | answered | When should one directory become multiple Research identities? | Split when topics have independent decision purposes, owners, conclusion timing, or downstream reuse; otherwise retain multiple documents under one identity. | `notes/real-world-corpus.md` |
| RQ-005 | answered | Which external tool patterns are reusable? | Use BMAD-style research packs, Spec Kit fan-out/fan-in, and OpenSpec-style artifact dependencies without coupling the skill to any host. | `notes/tool-landscape.md` |

Allowed statuses: `open`, `answered`, `deferred`, `invalidated`.

## Method and Sources

Inspected the supplied DataFox corpus's file inventory, headings, frontmatter,
reading route, and local references. Inspected the current `epctl` creation,
validation, hashing, and archive implementation. Compared only primary
documentation or source repositories for BMAD Method, GitHub Spec Kit,
OpenSpec, GPT Researcher, LangChain Open Deep Research, and STORM.

Claims about the current tool are checked against `scripts/epctl.py`, its
assets, and tests. Corpus observations are recorded in
`notes/real-world-corpus.md`; external tool findings are recorded in
`notes/tool-landscape.md`.

## Experiments and Prototypes

### Corpus inventory and reference check

- Hypothesis: the supplied corpus is a cohesive multi-document Research with
  an existing entrypoint and machine-detectable integrity problems.
- Method: enumerate Markdown files, count lines/bytes, inspect headings and
  `inputDocuments`, and resolve referenced repository paths.
- Observation: 11 documents, 4,868 lines, 211,187 bytes, one natural
  `index.md` entrypoint, and one missing local document reference.
- Interpretation: a manifest must model document membership and entrypoints,
  and validation must check local references.
- Evidence: `notes/real-world-corpus.md`.
- Promotion or discard: use the corpus shape as a forward-test fixture; do not
  copy its proprietary contents into this repository.

### Current implementation audit

- Hypothesis: the current package layout supports multiple notes but does not
  make their membership or integrity first-class.
- Method: inspect `new_research`, `validate_research`,
  `validate_synthesis`, and `archive_research`.
- Observation: the tool creates `notes/` and `artifacts/`, but validation
  checks only `RESEARCH.md` and `SYNTHESIS.md`; only Synthesis is hashed.
- Interpretation: add a manifest without removing the bounded Synthesis
  interface.
- Evidence: `scripts/epctl.py`.
- Promotion or discard: preserve current v1 packages through compatibility
  handling.

## Findings

1. High confidence: multi-document Research is already structurally anticipated
   by `notes/`, but document membership is implicit.
2. High confidence: existing corpora need linked adoption; mandatory relocation
   would duplicate content and break established reading routes.
3. High confidence: downstream consumers need one Synthesis even when upstream
   evidence is a graph.
4. High confidence: per-document hashes and local-link checks are necessary to
   make a concluded corpus auditable.
5. Medium confidence: snapshotting linked Markdown documents on conclusion is
   the best agent-independent default. Very large or external binary evidence
   may later require a content-addressed or Git-pinned extension.

## Contradictions and Uncertainty

Explicit manifests add maintenance overhead, while pure discovery is easier
during active research. The recommended compromise is deterministic manifest
refresh during active work and sealing only at conclusion.

Copying linked documents on conclusion duplicates data. The first version
should scope automatic snapshots to declared research documents and leave raw
binary artifacts under existing evidence rules. Git-object pinning is not a
universal replacement because ExecutionPlan does not require Git.

The supplied corpus includes absolute local source paths. The validator should
report portability warnings rather than reject active research solely because
an external source was used.

## Decision Drivers and Options

Decision drivers, in order:

1. adopt existing multi-document corpora without destructive relocation;
2. preserve a bounded downstream interface;
3. mechanically detect missing, added, or changed documents;
4. keep concluded evidence auditable without requiring Git;
5. preserve current repositories and commands;
6. keep the skill independent of a particular Agent or Harness.

Options:

- **Canonical-only package:** require all documents under `notes/`. Simple but
  invasive for existing corpora.
- **Live linked corpus:** keep documents in place and hash them. Non-invasive,
  but later source edits invalidate historical conclusions.
- **Linked-active, snapshotted-conclusion:** link existing documents while
  active, then copy and seal the declared document set at conclusion.
- **In-place registry:** store lifecycle metadata beside arbitrary corpora.
  Flexible, but replaces the current filesystem state model with a central
  registry and substantially increases migration risk.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Progress

- [x] (2026-07-28T08:13:12Z) Research created.
- [x] (2026-07-28T08:20:00Z) Inspected the supplied multi-document corpus and
  recorded its topology and integrity findings.
- [x] (2026-07-28T08:24:00Z) Compared BMAD, Spec Kit, OpenSpec, and
  deep-research engines.
- [x] (2026-07-28T08:28:00Z) Audited current creation, validation, hashing, and
  archive behavior and completed Synthesis.

## Outcome

- 2026-07-28 — Concluded with sealed `SYNTHESIS.md`; downstream decisions must cite its evidence.

## Artifacts and Notes

- Research: `docs/research/completed/r-001_multi-document-research/RESEARCH.md`
- Synthesis: `docs/research/completed/r-001_multi-document-research/SYNTHESIS.md`
- Focused analysis belongs under `notes/`; raw logs, benchmarks, traces and
  captures belong under `artifacts/`.
- Corpus observation: `notes/real-world-corpus.md`
- Tool comparison: `notes/tool-landscape.md`

## Revision Notes

- 2026-07-28T08:13:12Z — Initial Research package created.
- 2026-07-28T08:28:00Z — Completed the corpus, integrity, compatibility, and
  tool-pattern analysis; prepared decision-ready Synthesis.
