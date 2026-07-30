# Benchmark evidence in an ExecPlan

## Routing

Benchmark evidence has three different routes:

```mermaid
flowchart LR
    R["sealed Benchmark Run"] -->|"may change route"| Q["Engineering Research"]
    R -->|"accepted route, final revision"| E["ExecPlan acceptance"]
    R -->|"continuous regression"| C["CI / Runbook"]
```

Do not add every Benchmark to Research. Use Research when the evidence must be
combined with other sources, contradicts prior assumptions, or may change the
architecture route. Use direct ExecPlan evidence only after the route and
acceptance rule are fixed.

## Direct evidence reference

A completed ExecPlan may use:

```text
benchmark:BR-014@sha256:<evidence-manifest-payload-sha256>
```

The referenced Run must exist locally below `benchmarks/suites/` and contain
`RESULT.md`, `SCENARIO.md`, `EVIDENCE_MANIFEST.json`, and an `artifacts/`
directory. The consumer does not import or invoke the producer Skill.

For a `benchmark:` reference, `epctl archive-ep` and `epctl validate` require:

- Manifest schema `"1"`, status `sealed`, and the referenced Run ID;
- outcome `passed`;
- reference digest equal to `payload_sha256`;
- a valid canonical Manifest payload digest;
- an exact local inventory of Result, Scenario snapshot, and artifacts;
- matching byte counts and SHA-256 values;
- Result identity, status, outcome, completion, and executor matching Manifest;
- Result `subject_revision` equal to ExecPlan `verified_revision`;
- no symlinked or out-of-bundle evidence.

This proves which revision passed which predeclared protocol. It does not prove
that the Scenario was the right business or architecture criterion; that comes
from the accepted ADR and the ExecPlan's Validation and Acceptance section.

## Archive example

```bash
python3 <skill-dir>/scripts/epctl.py --repo . archive-ep EP-042 \
  --verified-revision "git:<verified-commit>" \
  --evidence \
  "benchmark:BR-014@sha256:<evidence-manifest-payload-sha256>"
```

Generic `ci:` or `artifact:` evidence remains valid and keeps its existing
meaning. Use `benchmark:` only when the versioned local bundle is present and
should be verified mechanically.

## Drift and correction

Any later change to a sealed Result, Scenario snapshot, or artifact invalidates
both Benchmark validation and the completed ExecPlan that cites it.

Never repair a cited bundle in place. Create a new Run, seal it, and use a new
ExecPlan or an explicitly governed follow-up to record the new evidence.
