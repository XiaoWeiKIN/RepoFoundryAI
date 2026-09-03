# RepoFoundry AI 0.8.3

RepoFoundry AI 0.8.3 preserves multi-generation ADR supersession history.
An accepted replacement may itself be superseded later; validation retains each
immediate bidirectional edge, accepts accepted-origin historical states, and
fails closed on a missing backlink or cycle. Current Decision contexts continue
to require an accepted/current terminal ADR.

Harness schema 3, Core 1.5.0, adapter versions, governance policy schema 1 and
activation protocol 2 are unchanged. Existing 0.8.2 checkpoint recovery
receipts remain compatible.

Pre-release verification:

- all 74 `engineering-execution-plan` tests pass, including three-generation
  supersession, terminal review/retirement, and cycle rejection;
- `python3 -B scripts/check.py` passes all repository integrity gates;
- a minimal corpus copied from DataFox ADR-010 and ADR-051 through ADR-055
  applies ADR-051 -> ADR-055 and validates with zero errors.
