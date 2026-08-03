# Repository Guidance

<!-- BOOTSTRAP_TODO: Replace unknowns with verified repository facts. -->

## Start Here

- Read `README.md` for the project purpose and supported workflows.
- Read `ARCHITECTURE.md` before changing module boundaries.
- Use `docs/index.md` as the documentation map.
- Before implementation or review, invoke `$engineering-specs`; use `docs/agent-guides/managed/index.md` only as its locked routing source.
- Keep this file at or below 100 physical lines, including blank lines and comments.

## Knowledge Map

- Architecture and invariants: `ARCHITECTURE.md`
- Documentation index: `docs/index.md`
- Research: `docs/RESEARCH.md`
- Architecture decisions: `docs/DECISIONS.md`
- Execution plans: `docs/PLANS.md`
- Persistent bugfix records: `docs/BUGFIXES.md`
- Quality status: `docs/QUALITY_SCORE.md`
- Reliability constraints: `docs/RELIABILITY.md`
- Security constraints: `docs/SECURITY.md`

## Work Routing

- Use a thread-local plan for small, reversible work.
- Use Research when decision-relevant facts or evidence remain unknown.
- Draft an ADR for durable choices; never accept or reject it without explicit authority.
- Use an ExecPlan for cross-module, multi-milestone, or resumable implementation.
- Record a Bugfix only when persistent defect tracking is explicitly requested.
- Convert repeated review feedback into tests, lint rules, types, or documented invariants.

## Working Agreement

- Preserve existing user changes and sources of truth.
- Prefer repository-relative, versioned evidence over hidden conversational context.
- Do not invent project commands, architecture facts, owners, SLOs, or security controls.
- Keep detailed rules in their canonical documents and link them from this map.

## Verification

<!-- BOOTSTRAP_TODO: List the exact build, test, lint, and Harness validation commands. -->

- Run the repository's documented checks for every changed area.
- Validate observable behavior, not only file creation or compilation.
- Record verification evidence in the active ExecPlan when one exists.
