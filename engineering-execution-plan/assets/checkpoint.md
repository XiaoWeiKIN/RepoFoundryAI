---
schema_version: "1.2"
metadata_schema: "1"
artifact_type: checkpoint
id: {{CHECKPOINT_ID}}
parent_id: {{PARENT_ID}}
title: "{{TITLE}}"
status: sealed
previous_checkpoint: {{PREVIOUS_CHECKPOINT}}
repository_revision: "{{REPOSITORY_REVISION}}"
created: {{DATE}}
updated: {{DATE}}
created_at: {{TIMESTAMP}}
author: "{{AUTHOR}}"
owner: "{{OWNER}}"
generated_by: engineering-execution-plan/epctl
payload_sha256: {{PAYLOAD_SHA256}}
---

# {{CHECKPOINT_ID}} — {{TITLE}}

This checkpoint is immutable history bound to `repository_revision`. Do not edit it after sealing. The active handoff state remains in the parent `EXECPLAN.md`.

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
