# Revision-bound Verification Receipt v1

This explicit local CLI binds a **command actually executed** against a Git worktree to the subject revision at execution time. It complements [Session Handoff / Resume](session-handoff.md) without creating a new approval, Task, ADR, EP, Checkpoint, Spec activation, or agent runtime. Requires Python 3.10+, Git and the full distribution containing both scripts.

## Execute a check

At the target repository root:

~~~bash
python3 -B <distribution>/scripts/verification_receipt.py --repo . run \
  --path src/cursor.py \
  --base-ref HEAD \
  --output /tmp/cursor-check.json \
  -- python3 -m unittest tests.test_cursor
~~~

This **executes** the command without a shell, with stdin disabled and stdout/stderr captured into temporary local files. It does not manufacture a result from a proposed command or unverified prose. A command that modifies the source during execution yields outcome `unknown` rather than a false `passed`.

The output path is optional; without it the tool outputs only a compact JSON result on stdout and does not save a receipt. When supplied, it must point to a new private file **outside the observed Git worktree**. Existing files are not overwritten, and the tool never commits the receipt or copies raw test output into it. Receipt file permissions are `0600`. Avoid commands containing passwords: the command argv is stored as evidence.

The receipt contains:

- Exact command argv, exit code, original outcome (`passed`, `failed`, `unknown`), command errors and timestamps.
- SHA-256 and byte counts of stdout/stderr, without storing their potentially sensitive text.
- The absolute checkout root, HEAD, branch, optional resolved base commit, current Git index hash, `git status --porcelain=v1 -z --untracked-files=all` and exact digests for visible changed/untracked and explicitly selected paths.
- Existing `docs/.engineering/harness.json`, `specs.json` and `specs.lock.json` (or their absence) as additional observed paths, not as a claim of successful Spec activation.
- Self-digest for accidental corruption detection. No identity authentication or authorization is implied.

## Recheck without rerunning

~~~bash
python3 -B <distribution>/scripts/verification_receipt.py --repo . check \
  --input /tmp/cursor-check.json
~~~

The check compares the recorded checkout, HEAD, index state, porcelain status, and observed file bytes to the current worktree. It never re-executes the command.

| Outcome | Meaning |
|---|---|
| `passed` | Command exited 0 against a stable observed worktree, and that observed snapshot still matches. **Only that command's check** is supported. |
| `failed` | Command executed with nonzero exit against a stable snapshot; not a passing check. |
| `stale` | Git revision, index, visible worktree or explicitly observed input changed. The previous result does not verify this snapshot. |
| `unknown` | Command was unavailable, timed out or mutated the observed source during execution. No passing result can be asserted. |

Exit `0`: scoped check passed and matches current snapshot; `1`: failed, stale or unknown; `2`: invalid evidence/input or read failure. A green result does not mean the entire task is accepted, all Specs were followed, or a PR can merge.

## Consume from Session Resume

Create a Handoff **after** executing the check, then read both:

~~~bash
python3 -B <distribution>/scripts/session_handoff.py --repo . capture \
  --task "Fix cursor boundary" --next-action "Review and commit" \
  --output /tmp/cursor-handoff.json

python3 -B <distribution>/scripts/session_handoff.py --repo . resume \
  --input /tmp/cursor-handoff.json --receipt /tmp/cursor-check.json
~~~

The optional `verification_receipt` section shows the scoped command result. The Handoff's existing top-level `verification` remains `unknown` for a matching snapshot (or `stale` for a drifted Handoff): one test never automatically becomes whole-task acceptance. Resume exits nonzero for a stale Handoff or a non-passing supplied Receipt. Invalid receipts cause explicit failure.

## Plan before execution (optional)

The [Spec-aware Verification Plan](spec-aware-verification-plan.md) is a read-only shadow-mode advisor. It uses the Git change and validated installed Specs to show candidate verification rows and uncovered inputs **before** commands are run. It does not activate Requirements or claim a test passed; this Receipt remains the only local record of an explicitly executed command. Missing Spec coverage leads to full-suite review, not optimistic skipping.

## Limitations and safety

- This is a local worktree snapshot, not a tamper-proof attestation. A hash proves stored bytes were not accidentally altered; it **cannot authenticate** the writer or prove that a command accurately tests the intended behavior.
- Visibility is bounded to HEAD, the staged index, Git-visible modified/untracked files and explicit input paths; ignored files not listed using `--path`, external dependencies, network services, package registries, environment variable values, and agent context are **unknown**. In particular, a passing Receipt is not a claim of hermetic reproducibility.
- A saved Handoff or Receipt is a private user-controlled artifact, not a canonical repository state. The scripts do not implicitly add project configuration or Hooks.
- The command is explicitly user-requested and can perform arbitrary operations. Run only trusted commands; the tool does **not** sandbox the subprocess. Timeout is configurable between 1 and 900 seconds, but does not guarantee termination of descendants.
- Drift detection takes before/after snapshots, not a transactional or malicious-concurrency-proof filesystem snapshot. Oversized logs and source files fail closed.
- Codex's native write guard and Claude/Portable CLI/advisory semantics remain unchanged. The Receipt does not call an Agent, activate Requirements, manage Spec locks, grant merge authority or replace EP/ADR Design approval.

Tracks Issue #87's separate revision-bound verification stage. Full regression/CI checks validate implementation contracts; actual cross-model task-completion benefit requires separate controlled end-to-end evaluation.
