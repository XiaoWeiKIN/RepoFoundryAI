# Quality Score

Status: bootstrap scaffold
Last assessed: unknown

<!-- BOOTSTRAP_TODO: Replace unknown ratings with evidence-backed assessments. -->

Use this document to expose quality gaps by domain or architectural layer. A
rating without an evidence path is `unknown`.

## Rating Scale

| Rating | Meaning |
|---|---|
| unknown | Not assessed or evidence is missing |
| red | Material correctness or maintainability risk |
| amber | Known gaps with bounded impact |
| green | Required controls exist and current evidence passes |

## Current Scorecard

| Area | Rating | Evidence | Gap | Owner |
|---|---|---|---|---|
| Build reproducibility | unknown | unknown | Assess setup from a clean environment | unknown |
| Automated tests | unknown | unknown | Identify coverage and critical journeys | unknown |
| Static checks | unknown | unknown | Identify lint, formatting, and type checks | unknown |
| Architecture conformance | unknown | unknown | Map invariants to mechanical checks | unknown |
| Documentation freshness | unknown | unknown | Define ownership and verification cadence | unknown |

## Promotion Rules

- Turn repeated defects into regression tests.
- Turn repeated review feedback into lint, types, or structural tests.
- Put actionable gaps into the technical-debt tracker or an ExecPlan.
- Record the revision and evidence whenever a rating changes.
