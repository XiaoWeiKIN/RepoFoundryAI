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

<!-- REQUIRED: Report measurements with units, sample units and counts, aggregation, effect sizes, uncertainty or dispersion and its definition, validity/correctness checks, and pointers to raw artifacts and generating commands. Retain excluded samples with reasons; do not report only the best run. -->

## Interpretation

<!-- REQUIRED: For each hypothesis/prediction ID, record predicted versus observed results, evidence links, and supported / falsified / inconclusive. Cross-check mechanism claims against measurements, compiler/runtime diagnostics, and version-matched source; qualify gaps or conflicts. Separate interpretation from observations and gate outcome. Do not accept an architecture decision here. -->

## Contradictions and Supersession

<!-- REQUIRED: Preserve falsified hypotheses, conflicting signals, anomalies, invalid experiments, and corrections. State what exposed each issue and link follow-up Scenarios/Runs without rewriting the original hypothesis. Explain supersession while retaining older evidence. Write "None observed" when applicable. -->

## Boundaries and Extrapolation

<!-- REQUIRED: Bind conclusions to tested versions, architecture, workload, and scale. Distinguish specification guarantees from implementation details; state invalidating conditions, environmental differences, missing evidence, and conclusions this Run cannot support. -->

## Handoff

<!-- REQUIRED: Name the intended Research, ExecPlan, CI, capacity, or runbook consumer and the exact claim this evidence may support. -->

## Artifacts

<!-- REQUIRED: List every local artifact with purpose. For external evidence record immutable URI or job ID, digest, retention, and access conditions. Write "No additional artifacts" only when the Result and Scenario snapshot are sufficient. -->
