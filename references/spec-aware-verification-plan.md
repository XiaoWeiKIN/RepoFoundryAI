# Spec-aware Verification Plan v1 (shadow mode)

A **read-only, advisory** planning layer between [Engineering Spec routing](specifications.md), a Git change and [Revision-bound Verification Receipts](verification-receipt.md). It does **not** reduce required CI, run commands, activate Requirements, grant approval, or assert that the work is verified.

## Run

From a Git checkout with RepoHarnessKit Specs installed:

~~~bash
python3 -B <RepoHarnessKit>/scripts/verification_plan.py --repo . --base main
~~~

For a change against the current commit, omit --base (defaults to HEAD). Use repeated --path for Git-ignored or explicitly relevant inputs that a normal diff cannot discover:

~~~bash
python3 -B <RepoHarnessKit>/scripts/verification_plan.py --repo . --base HEAD \
  --path config/ignored-but-relevant.toml
~~~

The command prints deterministic JSON to stdout; it never writes into the repository. Re-running against unchanged Git state and Spec content generates identical JSON.

## Source of truth and scope

1. Resolve --base to a concrete commit, record current HEAD, branch, staged index SHA-256 and Git porcelain SHA-256.
2. Union differences against base, staged changes, unstaged changes and visible untracked files. Keep both sides of renames, canonicalize repository-relative paths and take SHA-256 snapshots of changed and explicitly observed files.
3. **Reuse installed Spec Router** to validate the manifest, lock, managed Spec bytes, requirement index, applicability globs, Spec dependencies and source-range digests. When an indexed Requirement has a published Verification row, preserve the exact Markdown row and byte range with digest.
4. Present **candidate** Specs and Requirements with applicability requiring Agent review. An applicability glob is not proof that a natural-language activation condition is satisfied. A published verification minimum is a source-backed recommendation, **not** a runnable command or proof of execution.
5. Propose change-type review categories. For CI, build, generator, Spec, dependency and unknown inputs, set requires_full_suite_review=true. Any missing, invalid or unmatched Spec coverage also triggers a full-suite review recommendation.
6. Recheck the Git and source snapshot. If it changed during planning, abort rather than emit a mixed-time result.

Output always has mode=shadow, executed_checks=[] and verification_outcome=not_executed, with an advisory-only authority declaration. It is **not** a replacement for existing required GitHub Actions jobs.

## Results and failure semantics

| Exit | Status | Meaning |
|---|---|---|
| 0 | advisory | Source-backed recommendation; **not** a passing validation result |
| 1 | incomplete | Missing or invalid Spec routing state; full-suite review recommended |
| 2 | no plan | Invalid Git ref/path or failed observation; error on stderr |

An advisory plan may still contain evidence gaps, notably REQUIREMENT_ACTIVATION_NOT_ATTESTED, NO_SPEC_PATH_CANDIDATE, or WHOLE_SPEC_REQUIRES_MANUAL_REVIEW. Such gaps require review before asserting sufficient test coverage.

Every suggested check has execution=not_executed and command=null. V1 deliberately does not invent runnable commands without a trusted repository-owned mapping.

## How it connects to Receipt

An Agent or human reviews the plan and activates relevant Requirements via the existing Spec workflow. Then run actual checks through verification_receipt.py run. Recheck those Receipt files against current code via verification_receipt.py check. Keep three separate facts:

- **Plan**: which checks/reviews the change suggests, and why; no checks executed.
- **Spec activation**: which Requirements were actually activated under the installed Router protocol.
- **Receipt**: which exact commands ran, against which revision, and whether evidence is still current.

V1 does not mark plan items satisfied: it has no trustworthy general mapping from natural-language Verification descriptions to arbitrary command argv. A valid Receipt for one command does not prove every applicable Requirement.

## Known limitations

- Git-ignored and external dependencies are not automatically observed. Pass known ignored inputs as --path, and treat external dependencies as unknown.
- Glob-based Spec candidates do not establish Requirement-level applicability or test coverage completeness.
- Git submodules, generator inputs, build graph dependencies, and custom languages may be under-observed: use full-suite review.
- This snapshot is not an authenticated attestation; an actor can modify code after planning.
- Python 3.10+, Git and the full RepoHarnessKit distribution are required.
