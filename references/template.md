# ExecPlan 规范

## 目录

- 质量门槛
- 必需 section
- 当前事实与历史记录
- 验收证据
- 上下文与长期知识
- Task 规则

## 质量门槛

合格的 ExecPlan 必须：

1. **自包含**：无历史会话的 Agent 只依赖当前工作树和 `EXECPLAN.md` 即可继续。
2. **面向结果**：先说明用户获得什么能力以及如何观察。
3. **可以执行**：写明修改范围、具体路径、里程碑和命令。
4. **可以验证**：每个里程碑与总体结果都有可观察证据。
5. **可以恢复**：危险或可能半途失败的操作有重试、回滚和清理方法。
6. **持续更新**：计划始终反映当前真实路线，同时保留历史轨迹。
7. **保持有界**：根文档优先服务当前接手，旧事件封存到 checkpoint，完整证据外置。

目标与步骤承担不同职责：目标定义成功，步骤提供当前可执行路线。步骤可以随发现修订，不能用模糊清单替代研究。

## 必需 section

| Section | 内容 |
|---|---|
| Purpose / Big Picture | 用户价值、完成后的可观察行为 |
| Current Snapshot | 最新 checkpoint、当前里程碑、当前状态、准确下一动作和开放问题 |
| Context and Orientation | 术语、现状、模块关系、完整仓库相对路径 |
| Constraints and References | 当前任务所需约束摘要与权威入口 |
| Plan of Work | 当前准备怎样修改以及为什么 |
| Milestones | 每阶段新增能力、改动范围、验证命令与预期结果 |
| Concrete Steps | 工作目录、精确命令、关键编辑位置 |
| Validation and Acceptance | 行为、输入、输出、测试和证据 |
| Idempotence and Recovery | 重试、回滚、备份、清理 |
| Progress | 带时间戳的完成/未完成清单 |
| Surprises & Discoveries | 发现、证据及其影响 |
| Decision Log | 决策、理由、备选、日期/作者 |
| Blockers | 有生命周期的能力缺口 |
| Outcomes & Retrospective | 结果、差距、遗留项和经验 |
| Interfaces and Dependencies | 必须存在的接口、类型、服务和依赖 |
| Artifacts and Notes | 关键输出、短 transcript、完整截图/日志/trace 的路径 |
| Revision Notes | 对当前事实的每次修订及原因 |

使用 `assets/execplan.md` 作为唯一新建模板。

## 当前事实与历史记录

必须持续修订：

- Purpose、Context、Constraints
- Current Snapshot
- Plan of Work、Milestones、Concrete Steps
- Validation、Recovery
- Interfaces and Dependencies

在当前 checkpoint 区间只追加：

- Progress
- Surprises & Discoveries
- Decision Log
- Blockers
- Revision Notes

纠正历史时新增一条更正记录。不要删除原始条目。当前计划改变后，必须同步修改受影响的 section，避免日志与路线冲突。

旧事件不必无限留在根文件。建立 checkpoint 时无损搬运到 `history/`，根文件更新 Current Snapshot 并重置已封存的历史 section。开放 blocker、未勾选 Progress 和未完成验收不能移走。详细规则见 `references/checkpoints.md`。

## 验收证据

每条验收至少包含：

- 行为：用户或系统能够做什么。
- 工作目录：从哪里运行。
- 命令或操作：精确到可复制执行。
- 预期：状态码、输出、测试数、指标阈值或可观察 UI。
- 证据：终端摘要、日志、trace、截图、视频或制品路径。

`make test` 通过只能证明测试集合通过。若目标有用户可见行为，还要提供端到端观察。

根文件只保留短 transcript。完整输出写入 EP 的 `artifacts/`，用仓库相对路径引用。

## 上下文与长期知识

上下文地图按“入口优先、必读在前、按需在后”组织。ExecPlan 内仍需解释当前执行依赖的关键事实和术语。

长期规范：

1. 在 Constraints 中写任务相关摘要。
2. 链接到 `docs/standards/`、design doc 或 ADR。
3. 在完成复盘中登记知识提升候选。
4. 经单独确认后更新权威文档，并优先编码为 lint/test。
5. `AGENTS.md` 仅增加短入口，不复制规则全文。

## Task 规则

- 文件名使用动词开头 kebab-case。
- `id` 在父 EP 内唯一；用脚本取最大值 +1。
- `parent_id` 写 `EP-NNN`。
- `depends_on` 只写 Task ID，并检查不存在循环依赖。
- Task 正文至少包含 Context、Change、Constraints、Validation、Blockers。
- 根 ExecPlan 保留里程碑、总体进度和关键决策，不能把它降成只含链接的目录页。
