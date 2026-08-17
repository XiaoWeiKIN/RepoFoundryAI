---
schema_version: "1.1"
metadata_schema: "1"
artifact_type: design-doc
id: {{DESIGN_ID}}
doc_type: design
layout: {{LAYOUT}}
title: {{TITLE_JSON}}
status: draft
working_revision: "1"
published_revision: "0"
research_refs: {{RESEARCH_REFS}}
research_not_required_reason: {{RESEARCH_NOT_REQUIRED_REASON_JSON}}
adr_refs: {{ADR_REFS}}
design_dependencies: {{DESIGN_DEPENDENCIES}}
decision_not_required_reason: ""
approved_by: ""
approved_at: ""
approval_ref: ""
superseded_by: ""
terminal_reason: ""
revision_reason: ""
author: {{AUTHOR_JSON}}
owner: {{OWNER_JSON}}
created: {{DATE}}
updated: {{DATE}}
---

# {{TITLE}}

This document is the entrypoint for `{{DESIGN_ID}}`. The logical Design and all
managed package members share one review and approval boundary.

## Design Summary

<!-- REQUIRED: State the selected system shape, user-visible outcome, and validity conditions. -->

## Goals and Non-goals

<!-- REQUIRED: State owned outcomes and explicit exclusions. -->

## Research and Decision Inputs

### Supported Findings and Confidence

<!-- REQUIRED: Reproduce decision-relevant findings and confidence; do not provide only links. -->

### Negative Evidence and Rejected Hypotheses

<!-- REQUIRED: Preserve evidence against tempting alternatives or state a reasoned Not applicable. -->

### Remaining Unknowns and Validity Conditions

<!-- REQUIRED: State remaining unknowns, assumptions, destinations, and evidence that would invalidate the design. -->

### ADR Constraints

<!-- REQUIRED: Map current accepted ADR constraints, or explain why no durable decision is required. -->

## System Context and Invariants

<!-- REQUIRED: Define existing boundaries and invariants. Use Mermaid when relationships matter. -->

## Proposed Architecture

<!-- REQUIRED: Define components, responsibilities, ownership, and dependency direction. -->

## Interfaces and Contracts

<!-- REQUIRED: Define APIs, schemas, commands or events, versioning, idempotency, validation, and errors. -->

## Data Model and State Ownership

<!-- REQUIRED: Define identity, lifecycle, persistence, consistency, retention, and sensitive-data boundaries. -->

## Control and Data Flows

<!-- REQUIRED: Define success, concurrency, retry, and partial-failure paths. Use Mermaid when relationships matter. -->

## Failure Semantics and Recovery

<!-- REQUIRED: Define fail-open/closed behavior, timeouts, rollback, reconciliation, and operator actions. -->

## Compatibility, Migration, and Rollout

<!-- REQUIRED: Define coexistence, upgrade, downgrade, cleanup, and irreversible boundaries. -->

## Security, Privacy, and Operations

<!-- REQUIRED: Define trust, authorization, observability, capacity, alerting, and support ownership. -->

## Verification Strategy

<!-- REQUIRED: Define contract, integration, migration, failure, security, and operational evidence. -->

## Alternatives, Open Questions, and Revisit Triggers

<!-- REQUIRED: Record rejected shapes, blockers, follow-up ownership, and evidence that changes this design. -->

## Package Document Map

{{PACKAGE_MAP}}

## Revision Notes

- {{DATE}} — Created working revision 1.
