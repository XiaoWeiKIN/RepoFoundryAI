---
schema_version: "1"
id: {{CHECKPOINT_ID}}
parent_id: {{PARENT_ID}}
title: "{{TITLE}}"
status: sealed
previous_checkpoint: {{PREVIOUS_CHECKPOINT}}
created: {{DATE}}
created_at: {{TIMESTAMP}}
payload_sha256: {{PAYLOAD_SHA256}}
---

# {{CHECKPOINT_ID}} — {{TITLE}}

This checkpoint is immutable history. Do not edit it after sealing. The active handoff state remains in the parent `EXECPLAN.md`.

## Handoff Summary

{{SUMMARY}}

## Next Action At Checkpoint

{{NEXT_ACTION}}

## Archived Progress

{{ARCHIVED_PROGRESS}}

## Archived Surprises & Discoveries

{{ARCHIVED_DISCOVERIES}}

## Archived Decision Log

{{ARCHIVED_DECISIONS}}

## Archived Resolved Blockers

{{ARCHIVED_BLOCKERS}}

## Archived Revision Notes

{{ARCHIVED_REVISIONS}}
