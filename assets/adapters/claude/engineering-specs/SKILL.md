---
name: engineering-specs
description: "Activate and audit this repository's locked Engineering Specifications through the canonical RepoFoundry engine."
---

# Engineering Specifications

Use the canonical repository-local Router. This Claude adapter provides native
Skill discovery, but Specification activation and enforcement are explicit CLI
steps; it does not claim lifecycle Hook enforcement.

From the repository root, choose stable session and turn identifiers and run:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py --repo . \
  begin --adapter-id claude --session-id <session> --turn-id <turn> \
  --prompt <task-summary>
python3 .repo-foundry/engineering-specs/spec_router.py --repo . \
  candidates --path <initial-scoped-path>
```

The `begin` result reports adaptive/strict profile and Explore/Build/Governed
mode. Adaptive Explore permits bounded reversible local work without a receipt.
Promote before bounded production or governed-risk work:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py --repo . \
  classify --adapter-id claude --session-id <session> --turn-id <turn> \
  --mode <build|governed> --reason <risk-reason>
```

Build and Governed record one decision for every applicable path scope:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py --repo . \
  activate --adapter-id claude --session-id <session> --turn-id <turn> \
  --path <path> --spec <spec-id> --reason <reason>
```

Repeat `--spec` when multiple candidates apply. If none applies, use `--none`
with a reason. Never infer explicit-none from an empty candidate list.

Before Build/Governed completion, audit the receipt and handoff:

```bash
python3 .repo-foundry/engineering-specs/spec_router.py --repo . \
  audit --adapter-id claude --session-id <session> --turn-id <turn> \
  --message-file <handoff-file>
```

Explore reports outcome, verification, and unresolved risk in ordinary prose.
Build/Governed responses contain `Activated specifications:`,
`Activated requirements:`, `Verification:`, `Exceptions:`, and
`Compatibility or migration:`. Report a missing Router as an exception rather
than claiming that no Specification applies. Never use Explore to bypass
authority, destructive/external action, security, data, or integrity boundaries.
