---
schema_version: "1"
metadata_schema: "1"
artifact_type: research-synthesis
id: {{ID}}
parent_id: {{PARENT_ID}}
title: "{{TITLE}}"
status: draft
created: {{DATE}}
updated: {{DATE}}
author: "{{AUTHOR}}"
owner: "{{OWNER}}"
payload_sha256:
---

# {{TITLE}}

This Synthesis is the bounded decision interface between Research and ADR or
ExecPlan. Once sealed, changing its body invalidates the recorded SHA-256.

## Executive Conclusion

<!-- REQUIRED: Answer the research purpose directly and state whether the evidence is decision-ready. -->

## Supported Findings

<!-- REQUIRED: List the findings that materially affect the decision, with confidence and evidence paths. -->

| Finding | Confidence | Evidence |
|---|---|---|
| `<supported conclusion>` | `<high, medium, or low>` | `<source or artifact>` |

## Rejected Hypotheses

<!-- REQUIRED: Record disproven or unsupported hypotheses and the evidence that rejected them. Write "None" when applicable. -->

## Remaining Unknowns

<!-- REQUIRED: State every remaining unknown, why it does not block the recommendation, or where it must become a blocker or acceptance item. -->

## Options Comparison

<!-- REQUIRED: Compare viable options against the decision drivers. Preserve material disadvantages and uncertainty. -->

## Recommendation and Preconditions

<!-- REQUIRED: Recommend an option, state why it ranks highest, and list conditions required for the recommendation to remain valid. -->

## Handoff to ADR and ExecPlan

<!-- REQUIRED: State which decision requires an ADR, which constraints must be restated in the ExecPlan, and which evidence is audit-only. -->

## Revision Notes

- {{TIMESTAMP}} — Draft Synthesis created with {{PARENT_ID}}.
