---
schema_version: "1.1"
id: {{ID}}
title: "{{TITLE}}"
status: active
maturity: exploratory
research_type: {{RESEARCH_TYPE}}
synthesis: SYNTHESIS.md
manifest: RESEARCH_MANIFEST.json
created: {{DATE}}
updated: {{DATE}}
owner: "{{OWNER}}"
author: "{{AUTHOR}}"
current_round: RR-001
synthesis_revision: "0"
approved_by: ""
approved_at: ""
approval_ref: ""
---

# {{TITLE}}

This controller is the bounded entrypoint for a multi-document Research
package. Keep current questions, routes, findings, and next actions here. Put
focused analysis in the declared corpus, raw evidence in `artifacts/`, and the
current decision-ready view in `SYNTHESIS.md`. Decision readiness never grants
permission to conclude or archive the Research.

## Research Metadata

| Field | Value |
|---|---|
| Date | {{DATE}} |
| Last Updated | {{DATE}} |
| Research Type | {{RESEARCH_TYPE_LABEL}} |
| Research Owner | {{OWNER_LABEL}} |
| Author | {{AUTHOR_LABEL}} |
| Lifecycle | active |
| Maturity | exploratory |
| Current Round | RR-001 |
| Synthesis Revision | v0 |
| Approval | Pending |

## Purpose and Decision to Enable

<!-- REQUIRED: State the feature question, why the decision matters, and what downstream decision this Research must enable. -->

## Current Snapshot

<!-- REQUIRED: State what is known, the exact next inquiry or experiment, and any open blocker. -->

- Current state: `<concise evidence-based state>`.
- Next inquiry: `<exact source, command, experiment, or synthesis action>`.
- Open blockers: none.

## Research Rounds

Use one round for one bounded pass over the shared Research purpose. A round
may add or reopen Research Questions and may reference any number of corpus
documents.

| Round | Focus | Status | Author | Started | Evidence and outcome |
|---|---|---|---|---|---|
| RR-001 | Baseline investigation | active | {{AUTHOR_LABEL}} | {{DATE}} | `rounds/rr-001_baseline.md` |

## Scope and Non-goals

<!-- REQUIRED: Define what this Research covers and what it intentionally excludes. -->

## Research Questions

<!-- REQUIRED: Keep every decision-relevant question in this table. Concluded Research cannot contain open questions. -->

| ID | Status | Question | Answer or disposition | Evidence |
|---|---|---|---|---|
| RQ-001 | open | `<decision-relevant question>` |  |  |

Allowed statuses: `open`, `answered`, `deferred`, `invalidated`.

## Method and Sources

<!-- REQUIRED: Record source-selection logic, repository paths, authoritative documents, and how claims will be checked. -->

## Experiments and Prototypes

<!-- REQUIRED: Record hypotheses, reproducible commands or procedures, observations, and promotion/discard criteria. Write "None required" with a reason when no experiment is needed. -->

## Findings

<!-- REQUIRED: Keep concise supported findings and point to manifest documents. -->

## Contradictions and Uncertainty

<!-- REQUIRED: State conflicting evidence, limitations, confidence boundaries, and unknowns that remain. -->

## Decision Drivers and Options

<!-- REQUIRED: Identify the criteria that will rank viable options and list those options without making the final architectural decision here. -->

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Progress

- [ ] ({{TIMESTAMP}}) Research created; answer or explicitly dispose every
  question before conclusion.

## Outcome

Research is active. A review-ready Synthesis remains active until the Research
Owner explicitly authorizes conclusion. Cancellation also requires explicit
authorization and a reason.

## Artifacts and Notes

- Manifest: `docs/research/active/{{DIR_NAME}}/RESEARCH_MANIFEST.json`
- Synthesis: `docs/research/active/{{DIR_NAME}}/SYNTHESIS.md`
- Round controllers belong under `rounds/`; managed analysis belongs under
  `notes/`; sparse, immutable Synthesis milestone snapshots belong under
  `snapshots/`; raw logs, benchmarks, traces and captures belong under
  `artifacts/`.

## Revision Notes

- {{TIMESTAMP}} — Initial Research package created.
