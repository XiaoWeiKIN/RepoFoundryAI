---
schema_version: "2.2"
doc_type: research-topic
parent_id: {{PARENT_ID}}
topic_id: {{TOPIC_ID}}
round_id: {{ROUND_ID}}
title: "{{TITLE}}"
author: "{{AUTHOR}}"
created: {{DATE}}
updated: {{DATE}}
---

# {{TOPIC_ID}} · {{TITLE}}

<!-- Authoring note: Write for two reading speeds. Let a decision-maker stop
after the brief and implications; let a learner follow the mental model and
continuous analysis; let a reviewer continue into the evidence index and
sources. Keep raw logs, captures, benchmark output, and generated dumps in
../artifacts/. Delete this note before review. -->

## 结论速览

<!-- topic-role: decision-brief -->

> **答案：** <!-- REQUIRED_TOPIC_ANSWER: Give the direct answer in two or three short sentences. Do not restate the question. -->
>
> **置信度：** <!-- REQUIRED_TOPIC_CONFIDENCE: Start with High, Medium, or Low, then name the main reason. -->
>
> **决策影响：** <!-- REQUIRED_TOPIC_IMPACT: State what a decision-maker should do, avoid, measure, or defer. -->
>
> **适用边界：** <!-- REQUIRED_TOPIC_BOUNDARY: State the versions, conditions, and exclusions under which the answer holds. -->

关联研究问题：

{{QUESTION_LIST}}

<!-- REQUIRED_TOPIC_RELEVANCE: In one short paragraph, explain why this topic changes or constrains the parent decision. -->

**按阅读目标选择路径：**

<!-- REQUIRED_TOPIC_READING_PATHS: Give a quick-decision path, a learning path through the important analysis sections, and a full-review path through evidence and sources. Keep this to three bullets. -->

## <!-- REQUIRED_TOPIC_MODEL_TITLE: Replace this with a reader-facing title that says which mental model must be understood. -->

<!-- topic-role: mental-model -->

<!-- REQUIRED_TOPIC_MODEL: Define only the concepts needed by the analysis. Prefer one diagram, protocol timeline, invariant list, worked example, or compact comparison table. End by telling the reader what the analysis will derive from this model. -->

## <!-- REQUIRED_TOPIC_ANALYSIS_TITLE: Replace this with a title that states the reasoning journey, not the generic word "Analysis". -->

<!-- topic-role: analysis -->

<!-- REQUIRED_TOPIC_ANALYSIS_INTRO: Give the reader a short route through the analysis and explain how the subsections build on one another. -->

### <!-- REQUIRED_TOPIC_ANALYSIS_SECTION_TITLE: Write a complete explanatory claim; put the audit ID at the end. -->（A-001）

<!-- REQUIRED_TOPIC_ANALYSIS_BODY: Develop the reasoning in connected prose. Explain the mechanism, cite E-NNN evidence inline, work through an example or counterexample when useful, and show how the evidence changes understanding. Do not replace this narrative with a claim card or a conclusion-only list. -->

## <!-- REQUIRED_TOPIC_ALTERNATIVES_TITLE: Replace this with a title that tells readers which plausible explanations or alternatives are being tested. -->

<!-- topic-role: alternatives -->

| 解释或方案 | 为什么看似合理 | 反证 | 当前判断 |
|---|---|---|---|

<!-- REQUIRED_TOPIC_ALTERNATIVES: Compare only credible alternatives or misconceptions. Preserve negative evidence and explain why each option survives, loses, or remains conditional. -->

## <!-- REQUIRED_TOPIC_IMPLICATIONS_TITLE: Replace this with a title that says how the analysis changes the decision or architecture. -->

<!-- topic-role: implications -->

<!-- REQUIRED_TOPIC_IMPLICATIONS: Derive concrete consequences from the analysis. Use prose for causal reasoning and a table only when several decision areas share the same fields. State the recommended option and its boundary. -->

## 哪些新证据会改变当前判断

<!-- topic-role: falsifiers -->

| 影响的分析 | 会削弱或推翻当前判断的证据 | 为什么重要 | 如何验证 |
|---|---|---|---|
| A-001 | | | |

<!-- REQUIRED_TOPIC_FALSIFIERS: Add analysis-linked falsifiers, boundary changes, unresolved risks, and exact validation actions. Focus on evidence that would change a judgment, not a generic risk inventory. -->

## 下游交接

<!-- topic-role: handoff -->

| 去向 | 状态 | 具体变化或约束 |
|---|---|---|
| Synthesis | pending | |
| ADR / ExecPlan | pending | |
| Prototype / monitoring | pending | |

<!-- REQUIRED_TOPIC_HANDOFF: State what Synthesis should add, change, downgrade, or leave unchanged. Record implementation and monitoring consequences only when supported. Replace pending with integrated, unchanged, not-ready, required, or an exact revision reference as work progresses. -->

## 证据索引

<!-- topic-role: evidence-index -->

<!-- Ordinary readers may stop at Handoff. This section is the compact audit
surface for reviewers; it must not repeat the analysis narrative. -->

| ID | 观察 | 精确来源 | 支持的分析 | 置信度 |
|---|---|---|---|---|
| E-001 | | S-001 | A-001 | |

<!-- REQUIRED_TOPIC_EVIDENCE_INDEX: Add one row per distinct observation. Each row must cite exact S-NNN sources or auditable paths, map to existing A-NNN analysis sections, and use High, Medium, or Low confidence. Every E-NNN referenced in analysis must exist here. -->

## 来源

<!-- topic-role: sources -->

- S-001 — <!-- REQUIRED_TOPIC_SOURCES: Replace this with an exact code path, line or symbol anchor, authoritative document, experiment command, or artifact path, plus its relevance. Add more S-NNN entries as needed and prefer stable locators. -->

## 修订记录

<!-- topic-role: revision-notes -->

- {{TIMESTAMP}} — {{TOPIC_ID}} created for {{ROUND_ID}}.
