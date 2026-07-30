# Go Implementation

Follow idiomatic Go while preserving repository architecture and boundary
contracts.

## APIs and types

- Accept interfaces where behavior varies; return concrete types unless callers
  need substitution.
- Put `context.Context` first on operations that can block, perform I/O, or be
  cancelled. Do not store a request context in a long-lived struct.
- Keep interfaces small and define them near the consumer.
- Use constructors to establish invariants that exported struct fields cannot
  preserve.
- Use named types for identifiers, units, states, and values that must not be
  mixed accidentally.

## Errors

- Return errors instead of using panic for expected failures.
- Wrap errors with operation context using `%w` when callers need the cause.
- Preserve sentinel and typed-error behavior across layers.
- Translate internal errors into protocol errors only at the owning boundary.
- Do not log and return the same error at every layer; choose the layer that has
  enough context and owns the operational signal.

## Boundary data

- Decode request or storage data into an input shape, then parse it into
  domain-safe values before invoking core logic.
- Keep normalization explicit and owned by the boundary that defines input
  semantics.
- Use `strconv`, `time`, `net/url`, or focused parsers instead of ad hoc
  conversions.
- Reject unknown or malformed external enum values before they enter the
  domain.
- Preserve raw passwords, signatures, tokens, and protocol fields unless the
  protocol explicitly requires transformation.

## Concurrency and resources

- Make goroutine ownership, cancellation, and shutdown observable.
- Do not start background goroutines without a bounded lifetime and error
  strategy.
- Close acquired resources on every path and handle meaningful close errors.
- Protect shared mutable state explicitly; prefer ownership transfer or
  immutable values where practical.

## Tests

- Use table-driven tests when multiple inputs exercise one contract.
- Test malformed, missing, boundary, and unknown values at external boundaries.
- Assert that rejected input does not invoke downstream side effects.
- Run formatting, static checks, focused tests, and the repository's canonical
  validation command before completion.
