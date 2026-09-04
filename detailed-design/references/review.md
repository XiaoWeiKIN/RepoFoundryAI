# Detailed design review

Review engineering risk before prose quality. Group repeated symptoms under one root finding.

## Finding format

```text
Finding
Severity: blocker / high / medium / low
Claim or location
Why the design is incomplete or inconsistent
Concrete failure mode
Recommended design change
Verification needed
```

## Review lenses

- Mental model: no coherent end-to-end explanation, or the document is only a directory/type inventory.
- Fact ownership: a normative fact has multiple owners, no owner, or is delegated without a stable reference.
- Boundaries: parser/analyzer/planner/runtime, logical/physical, product/core, or transport/domain responsibilities overlap.
- State and lifetime: mutable aliases, multiple writers, invalidation, cleanup, retry, cancellation or recovery are undefined.
- Illegal states: nil/empty/zero, mutually exclusive fields, defaults or open containers have ambiguous semantics.
- Evolution: compatibility surface, activation gate, versioning, mixed-version behavior or exhaustive consumers are missing.
- Verification: a strong claim has only examples, no negative case, no failure injection or no measurable workload.
- Freshness: code links do not support the prose, target/current behavior is mixed, or no owner can detect drift.

For architecture documentation, also check that a contributor can follow a real request/data/state flow and then reach the relevant implementation without first reverse-engineering the repository.
