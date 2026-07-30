# TypeScript Implementation

Use TypeScript to make domain and boundary contracts explicit rather than
treating type assertions as validation.

## Types

- Prefer precise domain types, discriminated unions, and exhaustive handling
  over broad objects and optional-field combinations.
- Avoid `any`. Use `unknown` for untrusted values and narrow it through a
  parser, schema, or type guard.
- Do not use `as` to claim that external data satisfies an interface.
- Encode identifiers, units, and incompatible states with branded types or
  constructors when accidental mixing is plausible.
- Keep public return types stable and intentional.

## Boundary data

- Decode JSON or protocol data as `unknown`, then parse it once at the owning
  boundary.
- Have parsers return a typed value or a structured error; do not return the
  original weak shape after validation.
- Make normalization explicit and test raw-value preservation where
  transformation is forbidden.
- Keep transport DTOs separate from domain commands when their compatibility
  and invariants differ.
- Translate domain failures into HTTP, RPC, queue, or UI errors only at the
  corresponding adapter.

## Control flow

- Handle every discriminant and use a `never` assertion for exhaustive
  branches where appropriate.
- Await promises whose completion or failure matters.
- Propagate cancellation with the platform's supported signal.
- Avoid hidden process-wide mutable state and import-time side effects.

## Tests

- Test parsers with valid, missing, malformed, unknown, and cross-field-invalid
  data.
- Assert that invalid input fails before network, storage, or state mutation.
- Test public serialization independently from internal object layout.
- Run formatting, type checking, focused tests, and the repository's canonical
  validation command before completion.
