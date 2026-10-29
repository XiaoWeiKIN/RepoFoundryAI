# 可选运行时记忆降温（P1-B）

Core 1.6.0 将 P1-A 的确定性选择接到现有 `session_start`、`subagent_start` 和 `context_resume`。它只处理用户显式配置的背景 EP 导航，不修改 EP、ADR、Spec lock、Checkpoint 或任务状态。不配置时维持原有注入行为，不为普通任务创建新制品。

## 启用与撤回

先按现有 Harness 升级流程预览并安装 Core 1.6.0。新版本将 `memory_runtime.py` 和 `memory_retrieval.py` 记录为版本化 Core 文件；旧 Core 1.5.6 不因缺少这两个文件而验证失败。Bootstrap 和 upgrade 不创建、不覆盖下面的用户配置，也不会默认开启降温。

在目标仓库显式创建 `.repo-foundry/memory-context.json`，例如：

```json
{
  "schema_version": 1,
  "mode": "shadow",
  "background_ep": ["EP-023"]
}
```

`EP-023` 是示例，必须替换为确实希望提供的可选背景计划。最多配置 8 个 active/blocked EP。**这不是要求新增 EP，也不是全库自动发现。** 普通任务不需要配置此文件。

| mode | 行为 |
|---|---|
| `off` 或没有配置 | 原有上下文，不读取背景 EP 或报告 |
| `shadow` | 在原有上下文剩余预算中提供已配置的背景 Snapshot；只计算指针方案，不应用 |
| `opt-in` | 应用有界且不比对应基线更长的背景来源指针方案 |

把 mode 改为 `off` 或删除此可选配置，下一次事件恢复原有上下文，不需要修改治理制品。不存在自动提升到 opt-in 的步骤。

## 保留范围

运行时先生成原有路由基线，再从剩余预算提供背景内容。**基线中的每个字节均保留**，包括必要治理说明、命令、当前 EP Snapshot、ADR 导航和规范索引。因此，背景内容不能挤掉原有内容。8 KiB 仍是非规范性路由预算；精确 Requirement Capsule 在其后按原契约加载，不受本功能截断或降温。

任务显式引用的 EP 不再当作背景候选。Core 保留至多 32 个显式 EP 引用用于防止误降温；超过范围则放弃优化。Subagent 的显式引用会保留到后续 Resume。多 EP 任务仍沿用既有“不猜测当前计划”的行为；这里的保护不会声称已经完整解析多计划范围。

背景 EP 的 ADR 引用不会自动成为当前任务的 ADR 适用性依据，也不会被用于减少原有 ADR 导航。ADR 的当前效力、依赖闭包及 scoped amendments 仍由既有 resolver 负责。`review_due` 不等于过期，未知活动时间不等于闲置。

## 可选的 P0 提示

可在配置中添加现有报告的仓库相对路径：

```json
{
  "schema_version": 1,
  "mode": "opt-in",
  "background_ep": ["EP-023"],
  "review_report": ".repo-foundry/local/memory-review.json",
  "max_report_age_seconds": 86400
}
```

运行时不生成报告、不运行 `memory_review.py`，也不扫描整个工程语料。仅检查现有报告的 schema、自摘要、时间和相关源字节。没有配置报告时，选择只依赖显式背景关系；配置了报告但它缺失、过期、未来时间、损坏或不匹配时，返回原有 Core 基线。报告仅提供注释，不能授权取消计划、退役 ADR 或修改锁。

配置限制 16 KiB，报告限制 1 MiB，每个背景 EP 沿用 Core 源大小上限。符号链接、路径越界、重复 ID、未知配置字段和读取期间源变化均触发回退；不通过静默修复让数据看起来有效。回退原因保存在诊断中。

## 宿主与诊断

Codex 在已有受信任 Hook 路径中调用共享 Core，因此 `UserPromptSubmit` / `SubagentStart` 的 `additionalContext` 会使用选定模式。Claude 和 Portable 通过现有规范化 `event` / `rehydrate` CLI 获取相同选择结果；**这不新增 Claude 原生 Hook，也不将 advisory 集成宣称为 native enforcement**。

例如，在已有 turn 上检查返回的 `context_plan.memory`：

```bash
python3 .repo-foundry/engineering-specs/spec_router.py rehydrate \
  --adapter-id portable --session-id example-session --turn-id example-turn
```

Session/turn 必须实际存在。`context_plan.memory` 包含模式、回退原因、来源摘要、被保护基线的摘要、选择结果以及以下字节计量：

- `original_core_bytes`：没有背景内容的既有路由上下文。
- `configured_baseline_bytes`：为用户配置的背景信息分配剩余预算后的基线。
- `proposed_bytes` / `effective_bytes`：建议方案和实际注入的非规范上下文。
- `saved_bytes`：相对 configured baseline 的差额；Shadow 为 0。

这些字段不包含宿主引导前缀或精确激活 Capsule，不能当作模型整个 Context Window 的计量。**配置背景后，即使 opt-in 比 shadow 更短，也未必比完全关闭背景更短。** 不为制造节省量而自动加载无关历史。

时间默认在事件内采集一次 UTC；规范化事件可提供带时区的 `memory_as_of` 用于重放。相同源、配置和时间输入产生相同选择；时间字段不构成工程批准。

## 错误边界与非目标

无剩余预算、可选模块/输入不可用、报告失效或背景文件变化时，回退原有有效 Core 基线。有效基线已存在时，优化失败不阻断普通任务；原基线的必需内容超预算、Spec 摘要漂移、写入激活缺失等原有错误仍按原契约失败，不能被这个回退吞掉。

配置和背景文件仅只读访问。原有 Router 自己的 session/turn 状态写入仍存在，不应将整个 Hook 宣称为无写入。源前后摘要比较是尽力一致性检查，不是对恶意并发文件修改者的隔离。

P1-B 首版不推断代码到 ADR 的语义关联、不自动退休旧需求、不安装后台进程、不修改 Issue、不生成语义摘要。P1-A 的 `memory_context.py` 继续提供按需 Shadow Preview；P0 的全库复核继续独立。正式生效或废弃仍属于后续授权维护流程。
