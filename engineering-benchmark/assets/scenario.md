---
schema_version: "1.1"
metadata_schema: "1"
artifact_type: benchmark-scenario
id: {{ID_JSON}}
suite_id: {{SUITE_ID_JSON}}
title: {{TITLE_JSON}}
status: "active"
author: {{AUTHOR_JSON}}
owner: {{OWNER_JSON}}
created: {{DATE_JSON}}
updated: {{DATE_JSON}}
---

# {{TITLE}}

## Question and Hypothesis

<!-- REQUIRED: State the exact question, a falsifiable hypothesis, and the observation that would falsify it. -->

## Subject, Control, and Variants

<!-- REQUIRED: Identify the subject, baseline or control, comparison variants, and immutable revision policy. -->

## Variables

<!-- REQUIRED: Separate controlled variables, intentionally changed variables, and measured responses. -->

## Dataset and Traffic Model

<!-- REQUIRED: Define data origin, scale, cardinality, distribution, traffic shape, concurrency, duration, and privacy constraints. -->

## Environment and Isolation

<!-- REQUIRED: Define hardware, OS, runtime, dependencies, topology, resource limits, background-load isolation, clock, and collection tooling. -->

## Procedure and Commands

<!-- REQUIRED: Provide setup, exact executable commands or harness entrypoint, warmup, measurement, repetition, cache-state, teardown, and recovery steps. -->

## Metrics and Correctness Checks

<!-- REQUIRED: Define primary and secondary metrics, units, aggregation, uncertainty, sample exclusions, and correctness or data-integrity checks. -->

## Decision Rule

<!-- REQUIRED: Predeclare how observations map to passed, failed, or inconclusive. Include thresholds, comparison margins, and minimum sample requirements. -->

## Evidence Requirements

<!-- REQUIRED: List required configs, stdout/stderr, raw measurements, traces, profiles, environment capture, and any external immutable evidence. -->

## Safety, Cleanup, and Recovery

<!-- REQUIRED: State stop conditions, blast-radius controls, cleanup commands, rollback, and recovery checks. -->

## Boundaries and Extrapolation

<!-- REQUIRED: State what the Scenario cannot prove and the environments, scales, or workloads to which results may or may not be extrapolated. -->
