---
schema_version: "1.1"
parent_id: {{PARENT_ID}}
title: "{{TITLE}}"
status: draft
revision: "0"
created: {{DATE}}
updated: {{DATE}}
payload_sha256:
---

# {{TITLE}}

This Synthesis is the bounded, living decision interface between a
multi-document Research corpus and downstream decisions or plans.
`review_ready` revisions are immutable review snapshots but do not conclude
the parent Research. Once sealed, changing the body invalidates the recorded
SHA-256.

## Executive Conclusion

<!-- REQUIRED: Answer the research purpose directly and state whether the evidence is decision-ready. -->

## Supported Findings

<!-- REQUIRED: List the findings that materially affect the decision, with confidence and manifest evidence paths. -->

| Finding | Confidence | Evidence |
|---|---|---|
| `<supported conclusion>` | `<high, medium, or low>` | `<manifest document>` |

## Rejected Hypotheses

<!-- REQUIRED: Record disproven or unsupported hypotheses and the evidence that rejected them. Write "None" when applicable. -->

## Remaining Unknowns

<!-- REQUIRED: State every remaining unknown, why it does not block the recommendation, or where it must become a blocker or acceptance item. -->

## Options Comparison

<!-- REQUIRED: Compare viable options against the decision drivers. Preserve material disadvantages and uncertainty. -->

## Recommendation and Preconditions

<!-- REQUIRED: Recommend an option, state why it ranks highest, and list conditions required for the recommendation to remain valid. -->

## Handoff to ADR and ExecPlan

<!-- REQUIRED: State durable decisions, implementation constraints, remaining validations, and which evidence is audit-only. -->

## Revision Notes

- {{TIMESTAMP}} — Draft Synthesis created with {{PARENT_ID}}.
