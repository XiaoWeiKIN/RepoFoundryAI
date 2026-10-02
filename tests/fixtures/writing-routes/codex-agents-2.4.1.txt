# Repository Guidance

<!-- BOOTSTRAP_TODO: Replace unknowns with verified repository facts. -->

## Start Here

- Use `README.md` when project purpose or supported workflows are unclear.
- Read `ARCHITECTURE.md` before changing module boundaries.
- Use `docs/index.md` as the documentation map.
- For changes or formal code review, invoke `$engineering-specs` to inspect governance mode; its locked routing source is `docs/agent-guides/managed/index.md`. Ordinary explanation and navigation need no activation.
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

- Adaptive Harnesses start Explore: bounded reversible inspection, experiments, local edits, and tests need no persistent artifact or Spec receipt.
- Promote to Build for bounded production work; keep a concise intent/path/acceptance contract and activate applicable Specs.
- Promote to Governed for public contracts, security, data, irreversible operations, reliability claims, releases, or durable decisions.
- In Governed, use Research only for decision-relevant unknowns, ADR for durable choices, and ExecPlan for resumable delivery.
- Never accept or reject an ADR without explicit authority.
- Record a Bugfix only when persistent defect tracking is explicitly requested.
- Convert repeated review feedback into tests, lint rules, types, or documented invariants.

## Working Agreement

- Preserve existing user changes and sources of truth.
- Do not use a lower mode to bypass authority, destructive/external-action, security, data-integrity, compatibility, or evidence-integrity boundaries.
- Prefer repository-relative, versioned evidence over hidden conversational context.
- Do not invent project commands, architecture facts, owners, SLOs, or security controls.
- Keep detailed rules in their canonical documents and link them from this map.

## Verification

<!-- BOOTSTRAP_TODO: List the exact build, test, lint, and Harness validation commands. -->

- Run checks relevant to the changed behavior and risk; documentation-only edits need documentation checks.
- Validate observable behavior, not only file creation or compilation.
- Continue authorized local checks and corrections until the requested outcome is verified.
- Record verification evidence in the active ExecPlan when one exists.
