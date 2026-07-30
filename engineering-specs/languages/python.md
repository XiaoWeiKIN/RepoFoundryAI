# Python Implementation

Use explicit Python types and boundary parsers while keeping runtime behavior
clear and testable.

## APIs and types

- Add type annotations to public functions and important internal boundaries.
- Use dataclasses, enums, protocols, and focused value objects when they make
  domain contracts clearer.
- Avoid unstructured dictionaries beyond decoding and integration boundaries.
- Distinguish identifiers, units, and states with types or constructors when
  mixing them would be unsafe.
- Keep imports free of unexpected I/O and mutable process-wide side effects.

## Errors

- Raise or return domain-specific failures with useful context.
- Catch exceptions only when adding context, translating at a boundary, or
  performing a defined recovery.
- Preserve the original cause with exception chaining.
- Do not use assertions for validating external input or production
  preconditions.

## Boundary data

- Treat decoded JSON, environment variables, CLI arguments, and storage rows as
  untrusted shapes.
- Parse them into typed domain values before core logic or side effects.
- Keep normalization explicit and owned by the boundary that defines the input
  semantics.
- Reject unknown enum values and invalid cross-field combinations at the
  boundary.
- Preserve raw passwords, signatures, tokens, and protocol fields unless their
  protocol requires transformation.

## Resources and concurrency

- Use context managers for files, locks, transactions, and other resources.
- Make coroutine cancellation and task ownership explicit.
- Avoid blocking operations inside async code unless they are isolated through
  the supported executor or worker mechanism.

## Tests

- Parameterize tests for boundary value families.
- Cover valid, missing, malformed, unknown, and cross-field-invalid inputs.
- Assert that rejected input does not trigger downstream side effects.
- Run formatting, static typing when configured, focused tests, and the
  repository's canonical validation command before completion.
