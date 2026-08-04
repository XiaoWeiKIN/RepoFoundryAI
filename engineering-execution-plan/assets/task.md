---
schema_version: "1"
metadata_schema: "1"
artifact_type: task
id: {{TASK_ID}}
title: "{{TITLE}}"
status: todo
parent_id: {{PARENT_ID}}
author: "{{AUTHOR}}"
owner: "{{OWNER}}"
depends_on: []
blocked_by: []
created: {{DATE}}
updated: {{DATE}}
---

# {{TITLE}}

## Context

<!-- REQUIRED: Explain why this task exists and how it fits the parent ExecPlan. -->

## Change

<!-- REQUIRED: Name the concrete files, functions or modules and the intended result. -->

## Constraints

<!-- REQUIRED: Summarize task-relevant invariants and risks. -->

## Validation

<!-- REQUIRED: Add exact commands, expected outputs and evidence. -->

- [ ] From `<repo-root>`, run `<command>`; expect `<observable result>`.

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Notes

- {{TIMESTAMP}} — Task created.
