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

Read each candidate's `Applicability` section. Then record either the applicable
IDs or a justified explicit-none decision before the first write:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py activate \
  --adapter-id portable --session-id <session-id> --turn-id <turn-id> \
  --path <planned-path> [--spec <id> ...]
```

This adapter provides CLI checks and advisory instructions. It does not claim
native lifecycle interception. Re-run activation if planned paths change, run
each activated requirement's verification, then audit the final handoff:

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
