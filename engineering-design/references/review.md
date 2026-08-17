# Engineering Design review protocol

## Review-ready gate

Review the package as one system model, not as unrelated Markdown files.
Before `mark-review-ready`, verify every concern below has substantive content
somewhere in the package or a concrete `Not applicable: <reason>` disposition:

1. Design Summary
2. Goals and Non-goals
3. Research and Decision Inputs
4. System Context and Invariants
5. Proposed Architecture
6. Interfaces and Contracts
7. Data Model and State Ownership
8. Control and Data Flows
9. Failure Semantics and Recovery
10. Compatibility, Migration, and Rollout
11. Security, Privacy, and Operations
12. Verification Strategy
13. Alternatives, Open Questions, and Revisit Triggers

Also confirm:

- reproduced Research findings retain confidence limits, negative evidence,
  remaining unknowns, and validity conditions;
- proposed ADRs do not authorize a published durable choice;
- every package member is declared once and manifest bytes match disk;
- interface versioning, idempotency, validation, and error behavior are explicit;
- retry, timeout, partial failure, rollback, reconciliation, and operator action
  are explicit where relevant;
- old/new coexistence, downgrade, cleanup, and irreversible boundaries are clear;
- verification names evidence that an ExecPlan can actually collect;
- typed Design dependencies are current and acyclic.
- material choices explored with the user are either confirmed Design inputs or
  explicit open questions with owner, impact, and revisit trigger; provisional
  preferences are not presented as settled invariants.

## Approval boundary

Approval means one exact revision is coherent and publishable. It does not accept
an ADR, conclude Research, authorize implementation, or approve only selected
members. Specialist reviews may be recorded in prose, but publication remains
atomic. If one member needs its own publication cadence, split it into another
`DD-NNN` before approval.

Never infer approval from “looks good”, `review_ready`, a filled CLI flag, author,
or owner metadata. Run `approve` only after explicit authority for the exact
revision is available and record an auditable `approval_ref`.
