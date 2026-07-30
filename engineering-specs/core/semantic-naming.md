# Semantic Naming

Use names to expose observable behavior and preserve domain meaning across
code, schemas, storage, protocols, metrics, and documentation.

## Semantic verbs

- Use `Parse` when converting untrusted text or tokens into a semantic value
  while rejecting invalid representations.
- Use `Decode` or `Unmarshal` when recovering structure from an encoding or
  wire format. Decoding alone does not prove domain validity.
- Use `Validate` when checking constraints without changing the input or
  returning a stronger representation.
- Use `Normalize` for explicit, potentially lossy equivalence conversion.
- Use `Canonicalize` when selecting one stable representation from equivalent
  valid forms.
- Use `Convert`, `Map`, or `To...` for explicit representation changes that do
  not imply parsing or validation.
- Use `Load`, `Fetch`, `Read`, and `List` consistently with their I/O and
  cardinality behavior.

Do not name a function `Parse...` if it only returns a Boolean. Do not name a
mutating function `Validate...` unless mutation is part of the documented
contract.

## Boundaries

- Decode external data into a transport shape, then parse or convert it into
  domain-safe values before core logic or side effects.
- Keep raw protocol, authentication, signature, password, and token fields
  unchanged unless their owning protocol explicitly defines normalization.
- Return actionable boundary errors that identify the field and violated
  contract without leaking secrets.
- Preserve the result of successful parsing in a type or constructor result so
  downstream code does not repeat the same checks.
- Keep wire names, domain names, and storage names independently explicit when
  their compatibility requirements differ.

## Types and units

- Encode units and semantic distinctions in names or types: bytes versus bits,
  duration versus timestamp, identifier versus display name.
- Give enums and status values stable external spellings and explicit parsing.
- Prefer safe zero values. When no safe zero value exists, require a
  constructor or parser that can fail.
- Avoid Boolean parameters whose meaning is unclear at the call site; prefer a
  named option or semantic type.

## Review

Verify that public names describe behavior, mappings are explicit and tested,
and new terminology does not create a synonym for an existing domain concept.
When a naming rule represents a mechanical invariant, enforce it with a schema,
lint rule, structural test, or contract test.
