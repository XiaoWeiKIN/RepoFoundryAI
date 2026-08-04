---
schema_version: "1"
metadata_schema: "1"
artifact_type: research
id: {{ID}}
title: "{{TITLE}}"
status: active
synthesis: SYNTHESIS.md
created: {{DATE}}
updated: {{DATE}}
author: "{{AUTHOR}}"
owner: "{{OWNER}}"
---

# {{TITLE}}

This Research package is a bounded evidence workspace. Keep this controller
concise; put focused analysis in `notes/`, raw outputs in `artifacts/`, and the
decision-ready conclusion in `SYNTHESIS.md`.

## Purpose and Decision to Enable

<!-- REQUIRED: State the feature question, why the decision matters, and what downstream decision this Research must enable. -->

## Current Snapshot

<!-- REQUIRED: State what is known, the exact next inquiry or experiment, and any open blocker. -->

- Current state: `<concise evidence-based state>`.
- Next inquiry: `<exact source, command, experiment, or synthesis action>`.
- Open blockers: none.

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

<!-- REQUIRED: Record supported findings with concise evidence references and confidence. -->

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

Research is active. Its decision-ready outcome will be sealed in
`SYNTHESIS.md`, or cancellation will record why work stopped.

## Artifacts and Notes

- Research: `docs/research/active/{{DIR_NAME}}/RESEARCH.md`
- Synthesis: `docs/research/active/{{DIR_NAME}}/SYNTHESIS.md`
- Focused analysis belongs under `notes/`; raw logs, benchmarks, traces and
  captures belong under `artifacts/`.

## Revision Notes

- {{TIMESTAMP}} — Initial Research package created.
