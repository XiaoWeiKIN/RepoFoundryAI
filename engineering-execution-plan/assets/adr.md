---
schema_version: "1.4"
metadata_schema: "1"
artifact_type: adr
id: {{ID}}
title: "{{TITLE}}"
status: proposed
research_refs: {{RESEARCH_REFS}}
depends_on: {{DEPENDS_ON}}
amends: {{AMENDS}}
amends_constraints: {{AMENDS_CONSTRAINTS}}
design_refs: {{DESIGN_REFS}}
supersedes: []
superseded_by:
decision_maker:
decided:
decision_outcome:
effect_changed_by:
effect_changed:
effect_reason:
payload_sha256:
created: {{DATE}}
updated: {{DATE}}
author: "{{AUTHOR}}"
owner: "{{OWNER}}"
---

# {{TITLE}}

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies and decision-input metadata are sealed;
later changes require an amending or superseding ADR.

## Context and Problem Statement

<!-- REQUIRED: Define the architectural problem, affected boundaries, and why a durable decision is required. -->

## Decision Drivers

<!-- REQUIRED: List the functional, quality, risk, compatibility, operational, and reversibility criteria that determine the choice. -->

## Research Evidence

<!-- REQUIRED: Summarize decision-relevant Research conclusions and link their sealed Synthesis files. Do not require readers to reconstruct the decision from raw notes. -->

## Considered Options

<!-- REQUIRED: List credible options, including the status quo when it is viable. -->

## Decision Outcome

<!-- REQUIRED: State the selected or rejected outcome and why it best satisfies the decision drivers. Remove this marker before deciding the ADR. -->

## Decision Statement

<!-- REQUIRED: State the normative decision in one concise sentence that can be accepted, rejected, amended, or superseded as a whole. -->

## Normative Constraints

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| C-001 | must | REPLACE_WITH_SCOPE | REPLACE_WITH_CONSTRAINT | REPLACE_WITH_CONFIRMATION |

<!-- REQUIRED: Replace the example with every durable constraint created by this decision. Keep IDs stable. Strength must be must, must_not, should, or may. The ADR body is normative; linked Design Docs may explain it but cannot silently add or override constraints. -->

## Consequences

<!-- REQUIRED: Record positive, negative, neutral, migration, operational, and future-development consequences. -->

## Confirmation

<!-- REQUIRED: State how implementation and continued compliance will be verified, preferably with tests, lint, schema checks, or observable behavior. -->

## Revisit Triggers

<!-- REQUIRED: Define evidence or environmental changes that would justify a superseding ADR. -->

## More Information

- Research references: {{RESEARCH_REFS}}
- Prerequisite ADRs: {{DEPENDS_ON}}
- Amended ADRs: {{AMENDS}}
- Amended constraints: {{AMENDS_CONSTRAINTS}}
- Design documents: {{DESIGN_REFS}}
- Related ExecPlans: none yet.

## Revision Notes

- {{TIMESTAMP}} — Proposed ADR created.
