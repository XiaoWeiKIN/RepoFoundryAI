---
schema_version: "2"
doc_type: research-topic
parent_id: {{PARENT_ID}}
round_id: {{ROUND_ID}}
title: "{{TITLE}}"
author: "{{AUTHOR}}"
created: {{DATE}}
updated: {{DATE}}
---

# {{TITLE}}

<!-- Authoring note: This topic is one decision-relevant argument inside
{{PARENT_ID}}. Let readers understand the answer from the first section and
inspect reasoning by claim. Keep raw logs, captures, benchmark output, and
large generated material in ../artifacts/. Delete this note before review. -->

## Decision Brief

> **Answer:** <!-- REQUIRED_TOPIC_ANSWER: Give the direct answer in one or two sentences. Do not restate the question. -->
>
> **Confidence:** <!-- REQUIRED_TOPIC_CONFIDENCE: State high, medium, or low and name the main reason. -->
>
> **Decision impact:** <!-- REQUIRED_TOPIC_IMPACT: State what a decision-maker should do, avoid, or defer because of this answer. -->
>
> **Applies when:** <!-- REQUIRED_TOPIC_BOUNDARY: State the conditions and boundaries under which the answer holds. -->

Related Research Questions:

{{QUESTION_LIST}}

<!-- REQUIRED_TOPIC_RELEVANCE: In one short paragraph, explain why this topic changes or constrains the parent decision. -->

## Model at a Glance

<!-- REQUIRED_TOPIC_MODEL: Give the smallest useful mental model. Prefer one diagram, protocol timeline, invariant list, or compact comparison table over a long background narrative. Define only terms needed by later claims. -->

## Claims and Evidence

<!-- REQUIRED_TOPIC_CLAIMS: Organize the argument as C-NNN claim blocks. Make each level-three heading a complete, decision-relevant claim. Add more blocks only when they advance a distinct claim. -->

### C-001 — <!-- REQUIRED_TOPIC_CLAIM_TITLE: Write a complete, decision-relevant claim, not a category label. -->

**Evidence**

<!-- REQUIRED_TOPIC_CLAIM_EVIDENCE: State the observed facts and cite exact repository locations, authoritative sources, experiments, or artifact paths. Use S-NNN source IDs when helpful. -->

**Reasoning**

<!-- REQUIRED_TOPIC_CLAIM_REASONING: Explain why the evidence supports this claim, including assumptions or contradictions. Do not repeat the evidence. -->

**Decision impact**

<!-- REQUIRED_TOPIC_CLAIM_IMPACT: State how this claim changes an option, constraint, implementation choice, or priority. -->

**Confidence**

<!-- REQUIRED_TOPIC_CLAIM_CONFIDENCE: State high, medium, or low and briefly justify the rating. -->

**Falsifier**

<!-- REQUIRED_TOPIC_CLAIM_FALSIFIER: Name the observation, test result, or boundary change that would overturn or materially weaken this claim. -->

## Options and Trade-offs

| Option or explanation | Evidence for | Evidence against | When it wins | Current assessment |
|---|---|---|---|---|

<!-- REQUIRED_TOPIC_OPTIONS: Compare only credible alternatives. Preserve negative and contradictory evidence. If there is no real choice, say so in one sentence and explain why. -->

## Risks, Unknowns, and Validation

| Risk or unknown | Why it matters | How to resolve or monitor | Trigger / owner |
|---|---|---|---|

<!-- REQUIRED_TOPIC_RISKS: Record material limitations, unanswered questions, validation experiments, and monitoring triggers. Do not create a generic risk list. -->

## Handoff

| Destination | Status | Exact change or constraint |
|---|---|---|
| Synthesis | pending | |
| ADR / ExecPlan | pending | |
| Prototype / monitoring | pending | |

<!-- REQUIRED_TOPIC_HANDOFF: State what Synthesis should add, change, downgrade, or leave unchanged. Record implementation or monitoring consequences only when the evidence supports them. Replace pending with integrated, unchanged, not-ready, or an exact revision reference as work progresses. -->

## Sources

<!-- REQUIRED_TOPIC_SOURCES: Register exact code paths, line or symbol anchors, authoritative documents, experiment commands, and artifact paths. Prefer stable locators such as "- S-001 — source — exact locator and relevance". Write "None required" only with a reason. -->

## Revision Notes

- {{TIMESTAMP}} — Topic document created for {{ROUND_ID}}.
