# Research manifest contract

## Contents

- Role and compatibility
- Schema
- Path resolution
- Discovery and refresh
- Reference diagnostics
- Sealing and snapshots
- Consumer requirements

## Role and compatibility

`RESEARCH_MANIFEST.json` makes a Research document set explicit. Controller
schema 1 packages without a manifest are legacy-compatible inputs, but new
Engineering Research packages always contain one.

The JSON file is UTF-8, formatted deterministically, and uses only standard
JSON types.

## Schema

Top-level fields:

| Field | Meaning |
|---|---|
| `schema_version` | Contract version string; current producer writes `"1.1"`; `"1"` remains compatible |
| `metadata_schema` | Shared metadata contract, currently `"1"` |
| `artifact_type`, `id`, `title` | `research-manifest`, `R-NNN-MANIFEST`, and a portable name |
| `research_id` | Parent `R-NNN` |
| `status` | `active` or `sealed` |
| `author`, `owner`, `created`, `updated` | Authorship, accountability, and portable time provenance inherited from the Research |
| `mode` | `managed`, `linked`, or `snapshot` |
| `roots` | Declared discovery roots |
| `entrypoints` | Normalized entrypoint paths |
| `documents` | Deterministic document inventory |
| `payload_sha256` | Empty while active; canonical manifest digest when sealed |

An active root contains:

```json
{
  "base": "package",
  "path": "notes",
  "include": ["**/*.md"]
}
```

`base` is `package` for managed content or `repo` for linked content. Paths
always use `/` and contain no `.` or `..` components.

Schema 1.1 Research declares package roots for `notes/`, `rounds/`, and
`snapshots/` in addition to any linked repository roots. This lets linked
Research retain package-local analysis without modifying the adopted corpus. A
root may set a default `role`, such as `round` or `snapshot`. Entrypoint role
still takes precedence. A Markdown document declaring
`doc_type: research-topic` receives `role: topic`.
Schema 2.2 Topic records also contain their stable `topic_id`:

```json
{
  "base": "package",
  "path": "notes/http-security.md",
  "role": "topic",
  "topic_id": "RT-004",
  "bytes": 1200,
  "sha256": "..."
}
```

Within one manifest, `topic_id` values are unique. The ID remains unchanged if
the document path or title changes. Schema 2.1 and earlier Topic records may
omit it for backward compatibility.

Synthesis snapshot membership is intentionally sparse. A package at
`synthesis_revision: "7"` may contain only `synthesis-v002.md` and
`synthesis-v007.md`. Validation requires each filename to match its embedded
revision and forbids revisions newer than the controller; it does not require
a contiguous `1..N` set. Repeated body digests are reported and the CLI reuses
an existing full snapshot rather than creating another copy.

An active document contains:

```json
{
  "base": "repo",
  "path": "_research/topic/index.md",
  "role": "entrypoint",
  "bytes": 1200,
  "sha256": "..."
}
```

A snapshotted document additionally retains `source_path` for provenance while
`base` becomes `package` and `path` points under
`artifacts/research-snapshot/`.

## Path resolution

- `repo` paths resolve from the target repository root.
- `package` paths resolve from the directory containing `RESEARCH.md`.
- CLI input may be absolute only if the resolved target remains inside the
  repository.
- Persisted paths are relative POSIX paths.
- Reject traversal, symlinked components, symlinked files, directories outside
  the repository, duplicate documents, and files outside declared roots.

## Discovery and refresh

`sync-research` expands each root's include patterns, sorts paths
lexicographically, computes byte size and SHA-256, assigns entrypoint and
structured topic roles, and atomically replaces the active manifest.

Validation rescans active roots. A changed membership set, size, or digest is
manifest drift. Refresh is explicit so users can review new or removed
documents.

Default discovery is `**/*.md`. Repeat `--include` to use a different declared
set. Raw artifacts are not implicitly members.

## Reference diagnostics

For each Markdown document other than an immutable Synthesis snapshot:

- validate relative Markdown links and repository-relative local links;
- ignore URL, mail, fragment-only, and data links;
- strip query and fragment suffixes before local resolution;
- inspect flat `inputDocuments` frontmatter lists;
- report missing repository paths as errors;
- report absolute workstation paths as portability warnings, even when they
  currently exist.

References outside the manifest may be valid source evidence; they need not be
added automatically. The check proves the target exists, not that its claim is
correct.

## Sealing and snapshots

Managed conclusion hashes documents in place. Linked conclusion may contain
both repository and package roots: repository documents are copied into a
temporary directory below `artifacts/research-snapshot/`, while package-local
Round and Synthesis snapshot documents remain in place. Only after all copies
and hashes validate does the command replace the final snapshot.

Before conclusion seals the package, the current unique review-ready Synthesis
body is preserved as a full milestone under `snapshots/`; an identical earlier
snapshot is reused. This milestone snapshot is distinct from the linked-corpus
copy under `artifacts/research-snapshot/`.

The sealed manifest:

- uses `status: sealed`;
- uses `mode: snapshot` for formerly linked content;
- resolves every auditable document from the package;
- retains original repository paths as `source_path`;
- records every byte count and SHA-256;
- stores `payload_sha256`, calculated from canonical JSON with
  `payload_sha256` treated as an empty string.

Changing a sealed document, inventory field, root, entrypoint, or digest causes
validation failure.

## Consumer requirements

A consumer such as `engineering-execution-plan`:

1. locates concluded Research through its controller;
2. validates the sealed Synthesis body digest;
3. when `manifest` is present, requires a sealed supported manifest;
4. validates manifest identity, canonical payload digest, document existence,
   and per-document digests;
5. may accept legacy concluded packages without a manifest;
6. never assumes the producer skill is installed.
