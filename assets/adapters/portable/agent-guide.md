# Agent Engineering Guide

This repository uses RepoFoundry's product-neutral engineering Harness. Read
`ARCHITECTURE.md` and `docs/index.md` before changing established boundaries.

## Governance and Engineering Specifications

Create a stable local session and turn identifier and run the shared engine:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py begin \
  --adapter-id portable --session-id <session-id> --turn-id <turn-id> \
  --prompt "<task summary>"
python3 .repo-foundry/engineering-specs/spec_router.py candidates \
  --path <planned-path> [--path <planned-path> ...]
```

`begin` reports the repository profile and mode. Adaptive Explore permits
bounded reversible work without a receipt. Promote to Build for bounded
production work or Governed for public contracts, security, data, irreversible
operations, reliability claims, releases, or durable decisions:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py classify \
  --adapter-id portable --session-id <session-id> --turn-id <turn-id> \
  --mode <build|governed> --reason <risk-reason>
```

In Build/Governed, read candidate Applicability and record applicable IDs or a
justified explicit-none decision before the first mutation:

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

Explore may use normal prose for outcome, verification, and unresolved risk.
Build/Governed handoff contains all five labels:

```text
Activated specifications: <IDs and versions | none>
Activated requirements: <Requirement IDs | none>
Verification: <commands and observable results>
Exceptions: none | <governed exception>
Compatibility or migration: none | <observable effect and plan>
```
