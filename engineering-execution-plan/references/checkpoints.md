# Checkpoint 与有界工作集

## 核心模型

`EXECPLAN.md` 是当前工作集，不是无限增长的审计日志。它必须让无历史会话的 Agent 直接继续，但不需要内联所有旧事件。

```text
ep-NNN_slug/
├── EXECPLAN.md
├── tasks/
├── history/
│   ├── cp-001_milestone-one.md
│   └── cp-002_milestone-two.md
└── artifacts/
    ├── validation-001.txt
    └── trace-001.json
```

- `EXECPLAN.md`：当前目的、系统事实、当前里程碑、下一动作、未完成验收、开放 blocker 和当前接口。
- `history/`：已经封存的不可变事件原文。checkpoint 形成单向链。
- `artifacts/`：完整日志、trace、截图、视频和生成物。根文档只保留结论与路径。

“只追加”是逻辑不变量：历史事件一旦记录不能被改写。它们可以从根文件无损搬到 sealed checkpoint，不能被删除或只留下无法追溯的摘要。

## 何时建立 Checkpoint

出现以下任一情况时建立：

- 一个可独立验证的里程碑完成。
- 准备跨会话交接或长时间暂停。
- 根文档超过约 800 行或 64 KiB。
- 活跃历史事件超过 50 条。
- 大量已解决 blocker、发现和决策开始遮蔽当前下一步。

这些是默认警戒线，不是完成条件。`validate` 超过警戒线只给 warning。

## Checkpoint 前置条件

执行前：

1. 把仍然有效的发现和决策吸收到 Context、Constraints、Plan、Interfaces 和 Validation。
2. 更新 `Current Snapshot` 的当前状态与准确下一动作。
3. 把完整验证输出写入 `artifacts/`，根文档只保留短结论和路径。
4. 确认每条 Progress 使用 `[x]` / `[ ]` 表达完成状态。
5. 确认 blocker 使用 `open` / `resolved` / `dismissed`。
6. 删除所有 `<!-- REQUIRED... -->` 占位符并运行 `validate`。
7. 取得当前 repository/workspace revision；Git 可使用 `git:<sha>`，其他
   VCS 或构建系统使用稳定的 `snapshot:<id>`。

语义摘要由 Agent 编写，脚本不自动推断关键决策。

## 命令

先预览：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . checkpoint EP-023 \
  --slug milestone-one \
  --title "Milestone 1 complete" \
  --current-milestone "Milestone 2: adapter integration" \
  --summary "契约层已完成；适配层仍待实现。" \
  --next-action "编辑 src/adapter.ts 并运行 npm test。" \
  --revision "git:<current-commit>" \
  --dry-run
```

确认预览后去掉 `--dry-run`。命令会：

- 封存已勾选 Progress。
- 封存 Surprises & Discoveries 与 Decision Log，并将根 section 重置为 checkpoint 后的新事件区。
- 只封存 `resolved` / `dismissed` blocker，保留 `open` blocker。
- 封存 Revision Notes。
- 更新 `Current Snapshot`、`latest_checkpoint` 和索引更新时间。
- 记录 `repository_revision`，说明历史对应的代码或工作区版本。
- 为 checkpoint payload 写入 SHA-256；后续编辑会使 `validate` 失败。

## 永远留在根文档的内容

- 当前 Purpose、Context、Constraints、Plan 和接口。
- 当前 `Current Snapshot` 与下一动作。
- 所有未完成 Validation and Acceptance。
- 所有未勾选 Progress。
- 所有 open blocker。
- 当前 Recovery 方法。

checkpoint 不能成为恢复工作的必读前置。只有调查历史原因或审计旧证据时才读取 `history/`。

## 迁移与恢复

旧 v2.0 ExecPlan 没有 `schema_version: "2.1"`、`latest_checkpoint` 或 `Current Snapshot`。不要静默压缩它：

1. 在 front matter 增加 `schema_version: "2.1"` 和空的 `latest_checkpoint:`。
2. 增加 `## Current Snapshot`，写当前里程碑、当前状态和下一动作。
3. 运行 `validate`，再建立第一个 checkpoint。

`checkpoint` 使用仓库锁、编号高水位和原子文件替换。普通失败会回滚根文档和索引；若进程在索引更新前崩溃，制品仍是事实源，运行 `validate --fix-index` 恢复投影。
