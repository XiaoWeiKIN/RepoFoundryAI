---
schema_version: "1"
id: ADR-001
title: "Separate engineering research from execution planning"
status: accepted
research_refs: ["R-001"]
supersedes: []
superseded_by:
decision_maker: "User — explicitly confirmed the dual-skill architecture in the current conversation on 2026-07-28"
decided: "2026-07-28T08:42:42Z"
payload_sha256: 9866f72aa09c400b36a9993681a73f7131381a28179a1f0832cd6a89a2ca8fae
created: 2026-07-28
updated: 2026-07-28
owner: "XiaoWeiKIN"
---

# Separate engineering research from execution planning

This ADR records one architecturally significant decision. Proposed ADRs may be
revised. Accepted or rejected ADR bodies are sealed; later changes require a
superseding ADR.

## Context and Problem Statement

ExecutionPlan currently owns evidence gathering, multi-document Research,
Synthesis, ADR governance, implementation planning, task tracking, checkpoint
history, Bugfix, and technical debt. The supplied DataFox corpus demonstrates
that engineering Research is itself a substantial bounded context: it needs
source acquisition, question decomposition, multiple document entrypoints,
manifest and link integrity, experiments, refresh, synthesis, and conclusion
snapshots.

Keeping that growing behavior in one skill makes triggering less precise,
loads research instructions during plan-only work, and couples evidence tools
to the plan lifecycle. Splitting carelessly would create a hard dependency
between skills or bind installation to one Agent. A durable producer-consumer
boundary is therefore required.

## Decision Drivers

1. Research must be useful without an ExecPlan.
2. ExecPlan must accept compatible evidence produced by BMAD, another
   deep-research tool, a human, or the companion skill.
3. Both skills must remain independently installable and Agent/Harness
   independent.
4. The handoff must be a versioned repository file contract, not a runtime
   call to another skill.
5. Existing `execution-plan` installations and v1 Research packages must keep
   working during migration.
6. Research-specific context and tooling must not load for plan-only work.
7. ADR acceptance and implementation planning must retain explicit human
   governance.

## Research Evidence

[R-001 Synthesis](../research/completed/r-001_multi-document-research/SYNTHESIS.md)
concludes that Research is a control record around a versioned document set,
with one bounded Synthesis for downstream consumers. It recommends an explicit
manifest, non-destructive linked adoption during active work, per-document
validation, and a self-contained conclusion snapshot. It also finds that BMAD
research methods, Spec Kit workflow fan-out/fan-in, and OpenSpec artifact
dependencies are complementary rather than replacements for the ADR/ExecPlan
lifecycle.

## Considered Options

1. **Keep one skill:** extend `execution-plan` with the full corpus and
   deep-research lifecycle.
2. **Hard-dependent companion:** add a Research skill that calls scripts or
   assets inside the ExecutionPlan skill.
3. **Independent producer and consumer:** add an `engineering-research` skill
   that owns Research production and exports a versioned file contract;
   `execution-plan` consumes that contract and owns ADR onward.
4. **Split Research, ADR, and planning into three skills:** maximize separation
   immediately.

## Decision Outcome

Adopt option 3.

Add an independently installable `engineering-research` companion skill.
It owns Research Questions, source and experiment work, multi-document corpus
manifests, linked-corpus refresh, integrity checks, Synthesis, conclusion
snapshots, and Research archive.

Keep `execution-plan` responsible for consuming compatible concluded Research,
creating and governing ADRs, and maintaining ExecPlan, Task, Checkpoint,
Bugfix, and technical debt. Its dependency is the versioned Research package
contract, never the presence or filesystem location of the companion skill.

Keep the existing repository root as the `execution-plan` skill during the
compatibility period and add `engineering-research/` as a self-contained
second skill. Retain legacy Research commands in `epctl` temporarily, but
remove them from the primary instructions and treat packages without a
manifest as compatible v1 input.

Do not split ADR into a third skill now. ADR is the human-governed bridge
between evidence and execution, and remains cohesive with plan gating.

## Consequences

Positive:

- Research-only requests trigger a smaller, purpose-specific skill.
- Large corpora no longer inflate the execution-planning instruction surface.
- Any producer can satisfy the Research Gate by emitting the contract.
- Installation remains Agent-independent and neither skill calls the other.
- The supplied `index.md + topic documents` shape becomes first-class.

Negative:

- The repository distributes two skills and README installation has two
  registration targets.
- Some schema-reading logic exists on both producer and consumer sides.
- Legacy `epctl` Research commands overlap temporarily with `researchctl`.
- Contract evolution requires producer-consumer compatibility tests.

Migration:

- Existing v1 Research without a manifest remains valid.
- New Research uses the manifest contract.
- Existing root skill paths remain stable; the new companion lives at
  `engineering-research/`.
- Installed copies are synchronized independently.

## Confirmation

Verification requires:

1. `skill-creator` validation for both skill directories.
2. Unit tests for managed and linked multi-document Research, manifest drift,
   local references, traversal, symlinks, snapshots, and tamper detection.
3. A producer-consumer contract test proving `epctl` accepts a concluded
   Research created by `researchctl`.
4. A forward test against a disposable copy of the supplied
   `spans-aggregate` corpus that detects its missing document reference.
5. Existing `epctl` regression tests remaining green.
6. README examples containing no Agent-specific installation path.

## Revisit Triggers

- A portable standard for inter-skill dependencies becomes available and is
  supported across the target Agent/Harness ecosystem.
- Research and execution planning cannot evolve independently without
  frequent breaking contract changes.
- Binary or extremely large corpora make repository snapshots operationally
  unacceptable.
- ADR governance grows into an independently useful lifecycle with distinct
  triggers and tooling.

## More Information

- Research references: ["R-001"]
- Related ExecPlans: EP-002 (to be created).

## Revision Notes

- 2026-07-28T08:39:22Z — Proposed ADR created.
- 2026-07-28T08:48:00Z — Selected the independent producer-consumer split
  after the user explicitly confirmed the dual-skill architecture.
