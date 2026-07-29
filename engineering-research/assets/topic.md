---
schema_version: "1"
doc_type: research-topic
parent_id: {{PARENT_ID}}
round_id: {{ROUND_ID}}
title: "{{TITLE}}"
author: "{{AUTHOR}}"
created: {{DATE}}
updated: {{DATE}}
---

# {{TITLE}}

This document is one auditable argument unit inside {{PARENT_ID}}. Keep it
focused on the declared Research Questions. Put raw logs, captures, benchmark
output, and large generated material in `../artifacts/`; let `SYNTHESIS.md`
combine findings across topics.

## Executive Takeaway

<!-- REQUIRED_TOPIC_TAKEAWAY: State the current answer, confidence, conditions, and effect on the parent Research in three to five sentences. -->

## Question and Decision Relevance

Related Research Questions:

{{QUESTION_LIST}}

<!-- REQUIRED_TOPIC_QUESTION: Explain why these questions materially affect the downstream decision. -->

## Scope and Non-goals

<!-- REQUIRED_TOPIC_SCOPE: State what this topic covers and explicitly excludes. -->

## Current Context

<!-- REQUIRED_TOPIC_CONTEXT: Provide only the system behavior, terminology, interfaces, or constraints needed to understand this topic. -->

## Method and Evidence Selection

<!-- REQUIRED_TOPIC_METHOD: Explain which sources, code paths, tests, or experiments were selected, why they are suitable, their freshness, and material exclusions. -->

## Evidence

<!-- REQUIRED_TOPIC_EVIDENCE: Add at least one E-NNN level-three evidence record. Every record must contain separate bold Observation, Evidence, Interpretation, and Confidence labels. -->

## Analysis

<!-- REQUIRED_TOPIC_ANALYSIS: Connect the evidence into reasoning. Identify assumptions, contradictions, and the effect on option ranking without repeating the evidence records. -->

## Alternatives and Counterevidence

| Alternative or explanation | Supporting evidence | Counterevidence | Current assessment |
|---|---|---|---|

<!-- REQUIRED_TOPIC_ALTERNATIVES: Compare credible alternatives fairly. Preserve negative and contradictory evidence. Write "None" with a reason only when no credible alternative exists. -->

## Findings

| ID | Finding | Confidence | Evidence | Decision impact |
|---|---|---|---|---|

<!-- REQUIRED_TOPIC_FINDINGS: Add at least one F-NNN row. Confidence must be high, medium, or low; Evidence must reference E-NNN records or auditable paths. -->

## Uncertainty and Limitations

<!-- REQUIRED_TOPIC_UNCERTAINTY: State remaining unknowns, evidence limitations, applicability boundaries, and observations that would overturn the findings. -->

## Impact on Synthesis

<!-- REQUIRED_TOPIC_SYNTHESIS: State exactly what the accumulated Synthesis should add, change, downgrade, or leave unchanged. -->

## Next Inquiry

<!-- REQUIRED_TOPIC_NEXT: Name the next exact source, experiment, Owner question, or review action. If none is needed, state why the topic is ready for synthesis. -->

## References and Artifacts

<!-- REQUIRED_TOPIC_REFERENCES: List repository paths, stable authoritative sources, and artifact paths. Write "None required" only with a reason. -->

## Revision Notes

- {{TIMESTAMP}} — Topic document created for {{ROUND_ID}}.
