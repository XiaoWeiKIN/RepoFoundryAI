# Agent Engineering Guide

This repository uses RepoFoundry's product-neutral engineering Harness. Read
`ARCHITECTURE.md` and `docs/index.md` before changing established boundaries.

## Engineering Specifications

Before implementation or code review, create a stable local session and turn
identifier, list the repository-relative paths you may change, and run the
shared activation engine:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py begin \
  --adapter-id portable --session-id <session-id> --turn-id <turn-id> \
  --prompt "<task summary>"
python3 .repo-foundry/engineering-specs/spec_router.py candidates \
  --path <planned-path> [--path <planned-path> ...]
```

Read each candidate's `Applicability` section. Request bounded cards for the
applicable Specs, then record exact direct Requirements with reasons before the
first write:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py requirements \
  --path <planned-path> --spec <applicable-spec-id>
python3 .repo-foundry/engineering-specs/spec_router.py activate \
  --adapter-id portable --session-id <session-id> --turn-id <turn-id> \
  --path <planned-path> --spec <applicable-spec-id> \
  --requirement <ID> --because "<ID>=<task-specific reason>"
```

This adapter provides CLI checks and advisory instructions. It does not claim
native lifecycle interception. Use explicit whole-Spec fallback only with a
reason; a raised capsule budget also requires `--capsule-budget-reason`. Use
`--none --reason` when nothing applies. Run `rehydrate` after a context reset,
re-run activation if planned paths change, run each resolved
Requirement's Verification row, then audit the final handoff:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py audit \
  --adapter-id portable --session-id <session-id> --turn-id <turn-id> \
  --message-file <handoff-file>
```

The handoff must contain all five labels:

```text
Activated specifications: <IDs and versions | none>
Activated requirements: <Requirement IDs | none>
Verification: <commands and observable results>
Exceptions: none | <governed exception>
Compatibility or migration: none | <observable effect and plan>
```
