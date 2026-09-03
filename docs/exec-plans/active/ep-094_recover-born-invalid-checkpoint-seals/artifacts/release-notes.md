# RepoFoundry AI 0.8.2

RepoFoundry AI 0.8.2 adds a fail-closed recovery path for schema-1.2
checkpoints whose payload seal was already invalid in the Git commit that
introduced their exact repository path.

- `register-checkpoint-recovery` is preview-first and requires a full ancestor
  commit, explicit attesting actor, and reason.
- Registration proves that every parent lacks the path and that the commit blob
  equals the current raw checkpoint bytes.
- Apply stores a content-addressed, self-digested repository receipt; it never
  edits the checkpoint.
- Normal validation is Git-independent and suppresses only the exact registered
  payload mismatch. Receipt drift, checkpoint drift, later corruption, or any
  additional structural error fails closed.
- Harness schema 3, Core 1.5.0, Codex adapter 2.4.0, Claude/Portable adapters
  1.3.0, governance schema 1, activation protocol 2, and the Spec Catalog
  selection contract are unchanged.
