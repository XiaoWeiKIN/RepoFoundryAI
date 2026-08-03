# RepoFoundry AI

[简体中文](README.zh-CN.md) | English

<p align="center">
  <img src="./assets/brand/repofoundry-icon.svg" alt="RepoFoundry AI icon" width="128">
</p>

<p align="center"><strong>The Agent-Native Engineering System</strong></p>

<p align="center">Turn any repository into an AI-ready engineering system.</p>

**RepoFoundry AI** turns an ordinary software repository into an environment
that humans and coding agents can navigate, govern, and verify together. It
installs durable engineering context close to the code: short agent
entrypoints, architecture maps, composable specifications, evidence contracts,
decisions, execution plans, and one deterministic validation path.

The repository remains the source of truth. RepoFoundry does not depend on one
model, agent, editor, or Git hosting provider.

## One system, four layers

```mermaid
flowchart LR
    F["RepoFoundry AI<br/>Agent-Native Engineering System"]
    F --> I["Inventory<br/>discover facts and gaps"]
    I --> S["Scaffold<br/>install missing entrypoints"]
    S --> H["Repository Harness<br/>navigate, constrain, validate"]
    H --> C["Capability Skills"]
    C --> B["Benchmark"]
    C --> R["Research"]
    C --> E["Decision and Execution"]
    C --> W["Case Study"]
```

- **Inventory** inspects the repository before proposing change.
- **Scaffold** performs guarded, preview-first Bootstrap.
- **Repository Harness** is the persistent environment left in the target
  repository.
- **Capability Skills** create specialized evidence and governance artifacts.

`Workflow` describes how an individual capability runs. RepoFoundry is the
system that makes those workflows composable and verifiable.

## Five Skills share file contracts

| Skill | Responsibility | Durable output |
|---|---|---|
| [`repo-foundry-ai`](./SKILL.md) | Inspect, Bootstrap, synchronize Specs, validate the Harness, and route work | `AGENTS.md`, architecture and docs maps, Harness and Spec manifests |
| [`engineering-benchmark`](./engineering-benchmark/SKILL.md) | Predeclare and execute reproducible measurement | Suite, Scenario, Run, Result, sealed Evidence Manifest |
| [`engineering-research`](./engineering-research/SKILL.md) | Investigate unknowns and synthesize multi-document evidence | Research controller, corpus Manifest, Rounds, topics, sealed Synthesis |
| [`engineering-execution-plan`](./engineering-execution-plan/SKILL.md) | Govern decisions and implementation | ADR, ExecPlan, Task, Checkpoint, Bugfix, technical debt |
| [`engineering-case-study`](./engineering-case-study/SKILL.md) | Turn verified code and process evidence into a shareable narrative | Chinese, English, or bilingual engineering case study |

The four professional Skills remain independently installable. They communicate
through versioned repository files rather than private runtime imports.

## Evidence moves forward without losing authority

```mermaid
flowchart LR
    U["Engineering request"] --> Q{"What is missing?"}
    Q -->|"measurement"| B["Benchmark<br/>sealed Run"]
    Q -->|"understanding"| R["Research<br/>sealed Synthesis"]
    B -->|"route-changing evidence"| R
    B -->|"final-revision gate"| E
    R --> A["Proposed ADR"]
    A --> O["Decision Owner<br/>explicit authorization"]
    O --> E["ExecPlan<br/>implementation + acceptance"]
    E --> C["Checkpoint<br/>bounded history"]
    R -. "explicit sharing request" .-> S["Case Study"]
    E -. "explicit sharing request" .-> S
```

Agents may collect evidence and draft decisions. Research conclusion and ADR
acceptance remain explicit human authority boundaries.

## What appears in a target repository

RepoFoundry creates only the paths owned by a selected capability. A fully used
target may contain:

```text
target-repository/
├── AGENTS.md
├── ARCHITECTURE.md
├── .agents/skills/engineering-specs/ # one project-local task Router Skill
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── scripts/spec_router.py
├── .codex/
│   └── hooks.json                     # reviewed project activation guards
├── scripts/
│   └── bench/                         # project-owned benchmark executables
├── benchmarks/
│   ├── BENCHMARKS.md
│   └── suites/b-NNN_slug/
│       ├── BENCHMARK.md
│       ├── scenarios/bs-NNN_slug.md
│       └── runs/br-NNN_slug/
│           ├── SCENARIO.md
│           ├── RESULT.md
│           ├── EVIDENCE_MANIFEST.json
│           └── artifacts/
└── docs/
    ├── .engineering/
    │   ├── harness.json
    │   ├── specs.json
    │   └── specs.lock.json
    ├── agent-guides/managed/
    ├── design-docs/
    ├── research/{active,completed}/
    ├── adr/
    ├── exec-plans/{active,completed}/
    ├── bugfixes/{active,completed}/
    └── case-studies/
```

Benchmark Scenarios reference project-owned executables under
`scripts/bench/`; RepoFoundry AI records their evidence without owning the
project's measurement implementation.

Bootstrap never invents repository facts. Unknown commands, owners,
architecture, SLOs, and security controls remain explicit `BOOTSTRAP_TODO`
markers for maintainers to resolve.

## Install the distribution

RepoFoundry AI requires Python 3.10+ and Git. Its governance CLIs use only the
Python standard library.

The external repository rename is a separate hosting operation. Until the
canonical hosting URL is confirmed, clone from the repository URL supplied by
its owner:

```bash
git clone <repo-url> /absolute/path/to/RepoFoundry
export REPO_FOUNDRY_HOME=/absolute/path/to/RepoFoundry
```

Register the root and any professional Skills your agent host should discover:

```text
/absolute/path/to/RepoFoundry
/absolute/path/to/RepoFoundry/engineering-benchmark
/absolute/path/to/RepoFoundry/engineering-research
/absolute/path/to/RepoFoundry/engineering-execution-plan
/absolute/path/to/RepoFoundry/engineering-case-study
```

RepoFoundry does not require installation inside an agent-specific private
directory. Directory scanning, symbolic links, or host configuration all work
when they preserve these package roots.

## Start with a Prompt

Bootstrap a repository:

```text
Use $repo-foundry-ai to inspect this repository, preview the Codex Harness
Bootstrap, and report create, preserve, and conflict actions. Apply only after
the preview is conflict-free, then validate the Harness and local Specs.
```

Route specialized work:

```text
Use $engineering-benchmark to define a reproducible capacity Scenario before
running the measurement.

Use $engineering-research to investigate the cache topology, preserve
counterevidence, and stop at review-ready Synthesis.

Use $engineering-execution-plan to consume the concluded Research, draft the
ADR, and wait for Decision Owner authorization before accepting it.

Use $engineering-case-study with the verified code, Research, ADR, and ExecPlan
to write a bilingual module-design article.
```

The [cache-topology example](./examples/cache-topology/README.md) shows the full
Prompt-driven handoff from an existing corpus to Research, an authorized ADR,
and a gated ExecPlan.

## Prompt-driven examples

The bilingual [Prompt example catalog](./examples/README.md) and
[Chinese catalog](./examples/README.zh-CN.md) cover all five Skills as
standalone entrypoints and as evidence handoffs:

| Situation | First Skill |
|---|---|
| Initialize a repository or route an ambiguous request | `$repo-foundry-ai` |
| Produce reproducible measurements | `$engineering-benchmark` |
| Investigate unknowns or adopt an existing corpus | `$engineering-research` |
| Record a decision or drive delivery | `$engineering-execution-plan` |
| Write a shareable engineering narrative | `$engineering-case-study` |

Users provide intent, context, stopping boundaries, and explicit authority.
Skills invoke deterministic control scripts internally and report the resulting
IDs, artifacts, and validation results.

## Deterministic CLI surfaces

Skills invoke these CLIs for state changes and validation. Humans can use them
directly for automation or diagnosis:

```bash
FOUNDRYCTL="$REPO_FOUNDRY_HOME/scripts/foundryctl.py"
BENCHCTL="$REPO_FOUNDRY_HOME/engineering-benchmark/scripts/benchctl.py"
RESEARCHCTL="$REPO_FOUNDRY_HOME/engineering-research/scripts/researchctl.py"
EPCTL="$REPO_FOUNDRY_HOME/engineering-execution-plan/scripts/epctl.py"

python3 "$FOUNDRYCTL" --version
python3 "$FOUNDRYCTL" --repo . bootstrap --profile codex
python3 "$FOUNDRYCTL" --repo . \
  bootstrap --profile codex --spec languages/go --apply
python3 "$FOUNDRYCTL" --repo . validate --harness
python3 "$FOUNDRYCTL" --repo . upgrade --to 0.1.0
python3 "$FOUNDRYCTL" --repo . upgrade --to 0.1.0 --apply

python3 "$FOUNDRYCTL" --repo . spec plan
python3 "$FOUNDRYCTL" --repo . spec sync --apply
python3 "$FOUNDRYCTL" --repo . \
  spec update --spec-version 1.2.0 --spec languages/go --apply
python3 "$FOUNDRYCTL" --repo . spec validate

python3 "$BENCHCTL" --repo . validate
python3 "$RESEARCHCTL" --repo . validate
python3 "$EPCTL" --repo . validate
python3 "$EPCTL" --repo . status
```

Bootstrap, Harness upgrades, and Spec writes are preview-first. Bootstrap
creates missing paths and preserves repository-owned files. An agent
instruction file registered by the Codex profile must stay at or below 100
physical lines.

RepoFoundry `0.1.0` introduces Harness schema `2` and Codex profile `1.0.0`.
Those versions evolve independently from the Engineering Specs Catalog.
Schema `1` stays readable but is changed only by an explicit
`upgrade --to 0.1.0 --apply`. A versioned seed is replaced only when its bytes
still match the recorded installed SHA-256; customized or provenance-unknown
files are preserved, and post-write validation failure rolls the migration
back. See the [versioning and migration design](./docs/design-docs/repo-foundry-versioning-and-migrations.md).

Engineering Specs come from the independent
[EngineeringSpecifications](https://github.com/XiaoWeiKIN/EngineeringSpecifications)
Git catalog. `sync` follows the locked commit; `update` explicitly resolves the
selected release again. New repositories default to fixed Catalog version
`1.2.0`, represented as `refs/tags/v1.2.0`; production upgrades name another
version with `spec update --spec-version MAJOR.MINOR.PATCH`. `--spec-ref`
remains an explicit development-source escape hatch. `spec validate` is
offline.

`spec plan` lists every Catalog entry and separates required, recommended,
configured, and dependency-closed selected sets. Detection only recommends
optional IDs. Repeat `--spec ID` during initial Bootstrap or `spec update` to
set the complete optional direct selection; use `--required-only` to select no
optional Specs. Required Specs and transitive dependencies remain automatic.

## Activate Specifications for each task

Installation and task activation are separate. Bootstrap generates exactly one
project-local `$engineering-specs` Router Skill; it does not turn every Spec
into a Skill. Before implementation or code review, the Router:

1. matches planned paths to the locked Catalog scopes;
2. asks the Agent to read candidate descriptions and Applicability;
3. records applicable Spec IDs, including dependencies, or an explicit
   reasoned `none` decision for the current turn;
4. reads only digest-verified local documents; and
5. reports activated requirements, verification, exceptions, and migration
   effects at handoff.

```mermaid
flowchart LR
    P["Prompt + planned paths"] --> R["$engineering-specs Router"]
    L["locked local Specs"] --> R
    R --> A["turn activation receipt"]
    A --> G["trusted Codex Hooks"]
    G --> W["implementation or review"]
    W --> H["changed-path + handoff audit"]
```

The generated Codex Hooks establish a Git baseline on `UserPromptSubmit`, pass
the contract to subagents, deny Bash or `apply_patch` writes before activation,
inject the activated local documents before the first write, and audit changed
paths at `Stop`. Project hooks run only after the repository is trusted and the
exact commands are reviewed through Codex `/hooks`. If hooks are disabled or
unavailable, run the Router's `begin` before any write and finish with
`audit --message` over the five-label handoff. The Skill remains the manual
contract, but there is no mechanical write gate.

## Boundaries keep the system trustworthy

- RepoFoundry AI does not run a general agent runtime or hide orchestration state
  outside the repository.
- The root Skill does not create Benchmark Runs, Research packages, ADRs,
  ExecPlans, or Case Studies.
- Professional Skills do not infer Research Owner or Decision Owner authority.
- Bootstrap does not overwrite repository-owned documentation.
- Normative Engineering Specs stay in their independent repository.
- RepoFoundry generates one task Router, not one Skill per Specification.
- Project Hooks are guardrails inside a trusted Codex project, not a universal
  enforcement guarantee for other agents or disabled hook environments.
- Case Studies are created only after an explicit sharing request.
- GitHub Actions, GitLab CI, Jenkins, and other providers call the same
  repository check instead of duplicating policy.

## Migration from EngineeringWorkflow

RepoFoundry AI replaces the former product identity with one current
entrypoint:

| Former surface | Current surface |
|---|---|
| `$engineering-workflow` | `$repo-foundry-ai` |
| `$repo-foundry` (pre-merge candidate) | `$repo-foundry-ai` |
| `scripts/engineeringctl.py` | `scripts/foundryctl.py` |
| `ENGINEERING_WORKFLOW_HOME` | `REPO_FOUNDRY_HOME` |
| new manifest owner `engineering-workflow` | new manifest owner `repo-foundry` |

Existing target manifests owned by `engineering-workflow` remain readable and
produce a migration warning. New manifests use `repo-foundry`. Accepted ADRs,
completed ExecPlans, and sealed validation artifacts preserve the historical
names that were true when they were recorded.

The local distribution does not claim that its Git hosting repository has
already been renamed. Perform that external operation separately and then
update existing clones with the confirmed remote URL. See
[GitHub repository rename guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).

## Development and validation

Run the only canonical repository check:

```bash
python3 -B scripts/check.py
```

The command validates all five Skill packages and eval catalogs, runs every
governance test suite, checks local Markdown links and independent installation,
and validates repository Research and ExecPlan state. CI adapters only invoke
this command.

## Reference map

RepoFoundry AI:

- [Root Skill](./SKILL.md)
- [Bootstrap contract](./references/bootstrap.md)
- [System identity and packaging](./docs/design-docs/repo-foundry-system.md)
- [Versioning and Harness migrations](./docs/design-docs/repo-foundry-versioning-and-migrations.md)
- [Engineering Spec resolution](./docs/design-docs/engineering-spec-management.md)

Professional capabilities:

- [Benchmark contract](./engineering-benchmark/references/contract.md)
- [Research method](./engineering-research/references/research.md)
- [Research manifest](./engineering-research/references/manifest.md)
- [Execution artifact routing](./engineering-execution-plan/references/templates.md)
- [Architecture Decision Records](./engineering-execution-plan/references/adr.md)
- [ExecPlan specification](./engineering-execution-plan/references/template.md)
- [Benchmark gates for ExecPlans](./engineering-execution-plan/references/benchmark.md)
- [Documentation and code integrity](./engineering-execution-plan/references/integrity.md)
- [Case Study source evidence](./engineering-case-study/references/source-evidence.md)
- [Case Study review](./engineering-case-study/references/review.md)

Decision and implementation:

- [ADR-007 — Adopt RepoFoundry](./docs/adr/adr-007_repo-foundry-identity.md)
- [ADR-008 — Use RepoFoundry AI externally](./docs/adr/adr-008_repofoundry-ai-brand.md)
- [ADR-009 — Align the root Skill name with RepoFoundry AI](./docs/adr/adr-009_align-repofoundry-ai-skill-name.md)
- [EP-006 — Migrate to RepoFoundry AI](./docs/exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md)
