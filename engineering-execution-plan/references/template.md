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
8. **输入已决且约束可执行**：Research 与 Architecture Decision Gate 有可验证
   引用或具体 not-required 理由；Architecture Compliance 独立判断，适用的 ADR
   constraints 已映射到实现和验证。
9. **测量门禁已预声明**：需要 Benchmark 验收时，完整 Scenario 集合在实现前
   声明，并映射到具体开发决定或里程碑。

目标与步骤承担不同职责：目标定义成功，步骤提供当前可执行路线。步骤可以随发现修订，不能用模糊清单替代研究。

## 必需 section

| Section | 内容 |
|---|---|
| Purpose / Big Picture | 用户价值、完成后的可观察行为 |
| Current Snapshot | 最新 checkpoint、当前里程碑、当前状态、准确下一动作和开放问题 |
| Context and Orientation | 术语、现状、模块关系、完整仓库相对路径 |
| Constraints and References | 当前任务所需约束摘要与权威入口 |
| Research and Architecture Inputs | Gate、关键证据、ADR 后果、执行约束、剩余未知和跳过理由 |
| Architecture Compliance Matrix | 每项 ADR constraint 或 legacy input 对应的实现/保持位置与验证方式 |
| Benchmark Gate Set | 预声明 Scenario、它驱动的开发决定或里程碑、完成契约 |
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

使用 `assets/execplan.md` 作为唯一新建模板。新计划使用
`schema_version: "2.8"`；v2.0–v2.7 只做兼容读取，不因普通编辑静默迁移。
v2.8 同时实现 `metadata_schema: "1"`，要求 `artifact_type: exec-plan`、稳定
ID、title/status、author/owner 与 created/updated。

## Research 与 Architecture Inputs

该 section 是上游证据和执行计划之间的稳定接口，至少写明：

- 每份 concluded Research 支持的结论、置信边界和 sealed Synthesis 路径。
- Architecture Decision Gate 为何由 accepted ADR 满足，或为何本次不需要独立决定。
- Architecture Compliance 为何 applicable/not_applicable；“不需要新决定”不能用来
  跳过既有架构。
- 每份 accepted ADR 的 Decision Statement、负面后果、迁移义务和 Confirmation。
- schema 1.2+ 的 `ADR-NNN#C-NNN` constraints，以及 sealed
  `ADR-NNN@sha256:<payload>` evidence。
- ADR 的 `depends_on` / `amends` 传递闭包，以及各关系为何属于本次实施输入。
- 每份 Design revision 提供的接口、数据流、迁移或运维细节；多文档集合优先给出
  `architecture_entrypoint`。schema 1.1 Design 使用
  `DD-NNN@rev:N@sha256:<manifest-digest>` evidence 固定精确 approved revision。
- 哪些事实是审计信息，哪些约束必须进入实现和验收。
- 剩余未知为何不改变路线，或它们对应的实验、blocker、里程碑和验收项。
- Gate/Compliance 为 `not_required` / `not_applicable` 时各自的具体依据。

引用不能替代正文。接手 Agent 不应先打开 Research/ADR 才知道要改什么。

`Architecture Compliance Matrix` 必须逐条回答：约束在哪里实现或由本次改动保持，
哪个 test/lint/schema check/observable evidence 证明它。结构化 ADR 的每项 constraint
恰好出现一次；legacy ADR 没有 constraint ID 时按 ADR 级别映射。Design Doc 是解释
输入，不得覆盖 ADR。

## 当前事实与历史记录

必须持续修订：

- Purpose、Context、Constraints
- Research and Architecture Inputs
- Benchmark Gate Set
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

根计划以 500 行、48 KiB、30 个活跃历史事件为整理目标，以 800 行、64 KiB、50
个事件为强警戒线。超过 5 个里程碑或 10 个未完成 Task 时复核完成边界；超过 8 个
里程碑或 15 个未完成 Task 时拆分可独立验证的 successor EP。数量是保守路由信号，
不能替代对发布、回滚和验收边界的语义判断。

## 验收证据

每条验收至少包含：

- 行为：用户或系统能够做什么。
- 工作目录：从哪里运行。
- 命令或操作：精确到可复制执行。
- 预期：状态码、输出、测试数、指标阈值或可观察 UI。
- 证据：终端摘要、日志、trace、截图、视频或制品路径。

`make test` 通过只能证明测试集合通过。若目标有用户可见行为，还要提供端到端观察。

根文件只保留短 transcript。完整输出写入 EP 的 `artifacts/`，用仓库相对路径引用。
归档 completed 前，把实际运行这些验证的版本写入 `verified_revision`，把 CI
run、日志或仓库制品写入 `verification_evidence`。字段由 `archive-ep` 填写；
active 计划必须保持为空。归档时 CLI 还会写入 `archive_sha256`，封存 frontmatter
和正文；后续变化必须通过新计划或明确的兼容迁移表达。

如果验收来自 Engineering Benchmark，使用
`benchmark:BR-NNN@sha256:<manifest-payload-sha256>`。CLI 会验证 sealed
Manifest、精确文件清单、每个本地文件摘要、`passed` outcome，并要求 Run 的
`subject_revision` 等于 `verified_revision`。v2.5+ 用
`required_benchmark_scenarios` 预声明零个或多个 Scenario；归档时每个必需
Scenario 必须恰好有一个有效 Run，且不能夹带未声明 Scenario 的 Run。多个指标
分别保持独立 gate，不合并成跨环境、跨协议的总分。Benchmark 可能改变架构路线
时应先进入 Research；这里只有路线已固定的 final-revision 验收。

## 上下文与长期知识

上下文地图按“入口优先、必读在前、按需在后”组织。ExecPlan 内仍需解释当前执行依赖的关键事实和术语。

长期规范：

1. 在 Constraints 中写任务相关摘要。
2. 链接到 `docs/standards/`、design doc 或 ADR。
3. 在完成复盘中登记知识提升候选。
4. 经单独确认后更新权威文档，并优先编码为 lint/test。
5. `AGENTS.md` 仅增加短入口，不复制规则全文。

current accepted ADR 的约束属于当前事实。若 ADR 后续 under_review、retired、
superseded，或其依赖闭包 non-current，active ExecPlan 必须重新评估路线并更新引用、
Inputs、Compliance Matrix、Plan 和 Validation。它保持结构有效并显示
`architecture_review_required`，但 completed 归档被阻止；cancelled 可明确终止。
completed/cancelled v2.6–2.8 EP 保留当时的 ADR digest，作为历史证据继续验证。

EP v2.4+ 的 `adr_refs` 必须依赖闭合：每个引用 ADR 的 `depends_on` 和 `amends`
传递目标都要显式出现在数组中。ADR 的 `design_refs` 也必须进入 EP 的
`design_refs`。这样根计划能展示准确输入边界，验证器不需要隐式猜测。

EP v2.6–2.8 还必须包含命中任一所引用 constraint 的 current scoped amendment；
`adr_constraint_refs`、`adr_evidence` 和 Compliance Matrix 均按该输入集精确校验。

EP v2.8 的 `design_refs` 必须包含每个 schema 1.1 Design 的 typed dependency
传递闭包。active 计划可引用未发布工作版本并显示告警，但 completed 计划必须在
`design_evidence` 中精确固定闭包内每个 approved revision；验证器独立校验 snapshot
manifest、entrypoint、reading map、文件 bytes 与 SHA-256。legacy schema 1 Design
必须是 `current` 才能满足完成门禁。

## Task 规则

- 文件名使用动词开头 kebab-case。
- `id` 在父 EP 内唯一；用脚本取最大值 +1。
- `parent_id` 写 `EP-NNN`。
- `depends_on` 只写 Task ID，并检查不存在循环依赖。
- Task 正文至少包含 Context、Change、Constraints、Validation、Blockers。
- 根 ExecPlan 保留里程碑、总体进度和关键决策，不能把它降成只含链接的目录页。
