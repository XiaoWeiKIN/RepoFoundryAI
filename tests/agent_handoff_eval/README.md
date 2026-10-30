# ChatGPT Chat → ChatGPT Chat handoff pilot

This is a **manual, controlled experiment**, not a model runner or an automated ChatGPT Chat API integration. The scripts prepare an isolated Git task, restore three identical interruption states and run acceptance tests. **The user/operator must actually start separate ChatGPT Chat conversations**; the harness deliberately reports `model_execution_verified: false` and `agent_success_rate: null`. Passing scripted tests alone is not evidence of model benefit.

## Why an operator is required

A normal ChatGPT Chat conversation does not automatically have a shared local terminal, filesystem or Git checkout. The existing RepoHarnessKit CLIs are **local and same-worktree**: they bind the checkout's **absolute path**, HEAD and modified file bytes. A Chat using the connected GitHub app can read/update GitHub content, but this is not identical to executing a command in the local worktree. Use a trusted operator to apply patches and run commands, or an eligible ChatGPT Work computer when that environment is actually available. Do not claim native model execution unless genuine Chat session transcripts and tool/provenance logs exist.

## Design: two scenarios, three arms each

| Case | Work | Special boundary |
|---|---|---|
| `pagination` | Fix an exact-page-size cursor bug | Continue partial work correctly |
| `stale-receipt` | Fix a quota boundary bug | Recognize that a formerly passing command predates a controlled source change |

Each case starts with **one genuine Chat A** that edits the initial fixture partway, then stops. The operator captures its interruption state **once**; each of three separate Chat B conversations starts from that *same state and absolute checkout path*. Do not reuse Chat B history between arms.

| Arm | Chat B sees |
|---|---|
| `control` | Same task, same visible source files, ordinary prose handoff (no machine-readable CLI output) |
| `handoff` | Same task and source, the real Handoff JSON plus `resume` output |
| `receipt` | Same task and source, Handoff JSON, real earlier command Receipt and `resume --receipt` output |

The difference between arms is the structured, reproducible state/evidence; don't give the control arm less basic task context. Hidden acceptance tests live **outside** the visible checkout. Because the public source contains the fixture generator, they are not cryptographically secret; don't give Chat B the grader scripts, test output or private acceptance path.

## Create the first isolated task

From a **full local RepoHarnessKit checkout**, replace the paths below:

```bash
RF=/absolute/path/to/RepoHarnessKit
EVAL=/tmp/rhk-chat-pagination

python3 -B "$RF/tests/agent_handoff_eval/chat_pilot.py" prepare \
  --root "$EVAL" --case pagination
```

The program creates `$EVAL/workspace`, a real Git repo, `$EVAL/task.txt`, and `$EVAL/private/acceptance.py`. **Do not point it at a production repository**. The private files are stored outside the worktree.

Create **Chat A** in a new conversation, ideally using a temporary Project with Memory disabled, and supply the task plus the contents of `paging.py` and `test_visible.py`. Ask it to implement a partial fix, then stop before final acceptance, stating specific remaining work. Have the operator apply the Chat-authored changes under `$EVAL/workspace`. Save A's complete transcript privately; label operator actions separately from model actions.

For the `stale-receipt` task, use a separate fresh root with `--case stale-receipt`, and **after Chat A stops**:

```bash
# The earlier check must execute before the controlled mutation.
python3 -B "$RF/scripts/verification_receipt.py" \
  --repo "$EVAL/workspace" run --path quota.py \
  --output "$EVAL/private/pre-change-receipt.json" \
  -- python3 -B -m unittest discover -s . -p test_visible.py

# Changes a source file AFTER the receipt was produced.
python3 -B "$RF/tests/agent_handoff_eval/chat_pilot.py" inject --root "$EVAL"
```

For `pagination`, run the equivalent visible test and save a receipt before capturing the interruption state; there is no injected drift.

## Capture and freeze the interruption

Use the real product CLI after A stops and after any controlled injection:

```bash
python3 -B "$RF/scripts/session_handoff.py" --repo "$EVAL/workspace" capture \
  --task "Finish the interrupted task in task.txt" \
  --next-action "Inspect the changed code and complete boundary verification" \
  --output "$EVAL/private/handoff.json"

python3 -B "$RF/tests/agent_handoff_eval/chat_pilot.py" snapshot --root "$EVAL"
```

Create `$EVAL/private/control-note.txt` from the same factual task/next-action information, but without Handoff/Receipt JSON or outcome labels. Keep the full Chat A transcript private from B.

## Three independent Chat B sessions

Before each Chat B, run:

```bash
python3 -B "$RF/tests/agent_handoff_eval/chat_pilot.py" restore \
  --root "$EVAL" --arm control
```

This **deletes the previously used evaluation workspace and copies the pinned interruption snapshot**, but only under the explicitly managed evaluation root. Finish and grade each arm before restoring the next. Use `--arm handoff` and then `--arm receipt` for the following two runs; do not reuse a Chat conversation.

Provide this **common prompt** to each fresh Chat B, together with the same task and current visible code:

> You are the second Agent continuing a partially finished engineering task. You do not have the first Agent's chat history. Use only the provided repository state and evidence, then finish the task. When code execution is needed, tell the operator the exact command to run. Do not state a check passed unless it actually ran on the matching revision. Explain which previous evidence is still usable, any stale or missing evidence, and the code changes you applied.

Arm-specific material:

- `control`: provide ordinary prose control note only, not any saved Handoff/Receipt or runtime output.
- `handoff`: provide `handoff.json` and result of `session_handoff.py --repo "$EVAL/workspace" resume --input "$EVAL/private/handoff.json"`.
- `receipt`: provide `handoff.json`, `pre-change-receipt.json`, and result of `session_handoff.py --repo "$EVAL/workspace" resume --input "$EVAL/private/handoff.json" --receipt "$EVAL/private/pre-change-receipt.json"`. **Preserve exit code 1 for stale evidence; do not replace it with fresh verification.**

Have the operator apply the actual Chat B changes. Export each B transcript and command/tool log outside the workspace. Then grade the applied code:

```bash
python3 -B "$RF/tests/agent_handoff_eval/chat_pilot.py" grade --root "$EVAL"
```

The grader reports whether **independent acceptance checks** passed, but explicitly does **not** claim a real Agent did the work. Repeat for the other arms; finally:

```bash
python3 -B "$RF/tests/agent_handoff_eval/chat_pilot.py" summary --root "$EVAL"
```

Repeat the procedure using a **new evaluation root** for the second case. Six Chat B continuations means two Chat A interruptions and three Chat B arms per case.

## What is measured

A human reviewer should separately label transcript-backed outcomes: final test pass/fail, whether B identified prior evidence as `stale`, whether B reran or requested valid checks, whether B preserved A's work, duplicate or destructive actions, and elapsed time. Count token usage only if the actual platform or an authorized meter exposes it. Otherwise use `unknown`. Save command receipts/outputs with timestamps; don't infer Agent behavior or task completion from the grader's Boolean.

A safe stale-evidence run **must not** say that the prior Receipt verifies current code. A positive code test result alone is insufficient. This is a two-case pilot, not a statistically reliable improvement claim.

**Experimental limitations:** ChatGPT Chat's shared Memory/Projects can leak previous conversations; choose fresh isolated chats and disclose any unavoidable cross-session leakage. The operator may introduce bias; keep the same tools and permissions for all arms. Work-mode local computer access is distinct from Chat-mode GitHub content access, and cannot be assumed. This is not a test of Codex/Claude native hooks, automatic session spawning or cross-device transfers. Existing Handoff and Receipt are valid only for the same absolute Git worktree.
