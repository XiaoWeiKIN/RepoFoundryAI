---
schema_version: "1.1"
metadata_schema: "1"
artifact_type: benchmark-result
id: {{ID_JSON}}
suite_id: {{SUITE_ID_JSON}}
scenario_id: {{SCENARIO_ID_JSON}}
title: {{TITLE_JSON}}
status: "draft"
outcome: ""
subject_revision: {{SUBJECT_REVISION_JSON}}
harness_revision: {{HARNESS_REVISION_JSON}}
supersedes: {{SUPERSEDES_JSON}}
manifest: "EVIDENCE_MANIFEST.json"
created: {{TIMESTAMP_JSON}}
updated: {{TIMESTAMP_JSON}}
author: {{AUTHOR_JSON}}
owner: {{OWNER_JSON}}
completed: ""
executed_by: ""
---

# {{TITLE}}

## Summary

<!-- REQUIRED: State what was run, whether execution completed, and the result relative to the predeclared rule. -->

## Revisions and Environment

<!-- REQUIRED: Record resolved subject and harness revisions, build or image digests, configuration, environment identity, and deviations from SCENARIO.md. -->

## Procedure and Commands

<!-- REQUIRED: Record the commands actually executed, timestamps or job IDs, repetition count, warmup, teardown, and any step that differed or failed. -->

## Decision Rule

<!-- REQUIRED: Apply the predeclared Scenario rule without changing it after observing results. Show the calculation and select passed, failed, or inconclusive; use errored only for execution failure. -->

## Raw Observations

<!-- REQUIRED: Report measurements with units, sample counts, uncertainty or dispersion, correctness checks, and pointers to raw artifacts. -->

## Interpretation

<!-- REQUIRED: Separate supported interpretation from raw observations. Do not accept an architecture decision here. -->

## Contradictions and Supersession

<!-- REQUIRED: Record conflicting signals, anomalies, known invalid evidence, and why any superseded Run is replaced while remaining auditable. Write "None observed" when applicable. -->

## Boundaries and Extrapolation

<!-- REQUIRED: State environmental differences, validity limits, missing samples, and conclusions this Run cannot support. -->

## Handoff

<!-- REQUIRED: Name the intended Research, ExecPlan, CI, capacity, or runbook consumer and the exact claim this evidence may support. -->

## Artifacts

<!-- REQUIRED: List every local artifact with purpose. For external evidence record immutable URI or job ID, digest, retention, and access conditions. Write "No additional artifacts" only when the Result and Scenario snapshot are sufficient. -->
