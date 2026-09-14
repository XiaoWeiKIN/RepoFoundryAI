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

<!-- REQUIRED: Before running benchmarks, state the mechanism question or bounded behavior claim. Give each hypothesis an ID, concrete metric or diagnostic predictions, and an explicit falsifier. Disclose prior exploratory data; hypotheses derived from it require fresh validation runs. -->

## Subject, Control, and Variants

<!-- REQUIRED: Identify the subject, baseline or control, comparison variants, and immutable revision policy. -->

## Variables

<!-- REQUIRED: Separate controlled variables, intentionally changed variables, measured responses, and confounders. Keep work and correctness semantics equivalent and change one causal variable per comparison; for multiple factors predeclare a matrix and interaction analysis or limit claims to the combined effect. -->

## Dataset and Traffic Model

<!-- REQUIRED: Define data origin, scale, cardinality, distribution, traffic shape, concurrency, duration, and privacy constraints. -->

## Environment and Isolation

<!-- REQUIRED: Define hardware, OS, runtime, dependencies, topology, resource limits, background-load isolation, clock, and collection tooling. -->

## Procedure and Commands

<!-- REQUIRED: Provide setup, exact commands or harness entrypoint, validity checks before measurement, warmup, measurement, repetition, sample unit, comparison ordering, cache-state, teardown, and recovery steps. Rule out eliminated work, empty runs, and load-generator or timer artifacts. Default to at least 8 repetitions for microbenchmarks; justify a suitable independent-repeat strategy for long-running experiments. -->

## Metrics and Correctness Checks

<!-- REQUIRED: Define primary and secondary metrics, units, aggregation, effect size, uncertainty or dispersion method, sample exclusions, and correctness checks. Mechanism claims need discriminating diagnostics beyond timing alone; latency and throughput may be primary metrics for bounded capacity/SLO claims. -->

## Decision Rule

<!-- REQUIRED: Predeclare how observations map to passed, failed, or inconclusive. Include thresholds, comparison margins, minimum sample requirements, and stopping conditions. Do not stop only when results become significant or interpret insufficient resolution as equivalence. -->

## Evidence Requirements

<!-- REQUIRED: List required configs, stdout/stderr, all raw samples, diagnostics, environment capture, and external immutable evidence. For mechanism claims plan measurement + compiler/runtime diagnostics + version-matched source evidence; declare unavailable evidence and the resulting limits. Link each reported metric to its generating command and raw artifact. -->

## Safety, Cleanup, and Recovery

<!-- REQUIRED: State stop conditions, blast-radius controls, cleanup commands, rollback, and recovery checks. -->

## Boundaries and Extrapolation

<!-- REQUIRED: State what the Scenario cannot prove and the environments, scales, or workloads to which results may or may not be extrapolated. -->
