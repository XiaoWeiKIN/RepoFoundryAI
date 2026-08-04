# 使用示例

以下示例都从用户在 Codex 中输入的 Prompt 开始。用户负责表达目标、约束和授权；
`engineering-research` 与 `engineering-execution-plan` 负责调用各自脚本、维护
状态并验证制品。CLI 是 Agent 的确定性执行机制，不是端到端使用入口。

## Prompt 驱动的端到端样例

发行仓库中的 `examples/cache-topology/README.md` 从四篇 linked corpus 文档
开始，展示完整的 R-001、sealed Synthesis/Manifest、明确授权的 ADR-001 和
gated EP-001。需要理解“用户怎么提问、Skill 如何交接、每份制品实际写什么”
时先读该例。

## 初始化

```text
使用 $engineering-execution-plan 检查当前仓库是否已经具备 Research、ADR、
ExecPlan、Bugfix 和技术债务控制面。缺失时安全初始化，只补缺失内容；
不要覆盖现有文档。完成后报告创建、保留和冲突项。
```

只补缺失目录、四个派生索引和技术债务登记册，不覆盖人工内容。

## 完整功能生命周期

```text
先使用 $engineering-research 充分研究网关、BFF 和 SDK 当前的 token 刷新契约，
比较兼容方案并形成决策就绪的 Synthesis。Research Owner 是
API Platform Owner。不要提前创建 ADR 或开发计划，也不要 conclude。
```

填写 `RESEARCH.md`，把聚焦分析写到 `notes/`，把完整命令输出写到
`artifacts/`。所有 `RQ-NNN` 已回答或明确处置、Synthesis 决策就绪后：

```text
继续使用 $engineering-research 完成 R-001 的分析和证据核对。
如果已经决策就绪，生成 review-ready revision；保留 counterevidence、
兼容约束和未决风险，不要 conclude。
```

若 Owner 要求继续深入，Skill 在同一个 R-001 下开启新 Round。只有 Owner 明确
授权结束后，用户才发出：

```text
我以 API Platform Owner 身份确认 R-001 已满足本次决策需要。
请使用 $engineering-research 结束并归档 R-001，并记录本条授权。
```

公共契约具有架构意义，创建 proposed ADR：

```text
使用 $engineering-execution-plan 消费已 concluded 的 R-001，
创建“Choose token refresh contract” ADR。比较可行选项、写清兼容义务、
后果和确认方式。ADR 必须停在 proposed，等待 Decision Owner。
```

Agent 写全 ADR 后停在 proposed。用户或 Decision Owner 明确接受该 ADR 时：

```text
我代表 API Architecture Council 接受 ADR-001。
请使用 $engineering-execution-plan 记录决定和 Decision Owner，
然后核对依赖与 supersession 关系。
```

最后创建 gated ExecPlan：

```text
使用 $engineering-execution-plan，基于 R-001 和已接受的 ADR-001，
创建“Implement token refresh contract” ExecPlan。
复述兼容约束、迁移义务、负面后果和仍需验证的未知；把每个
ADR-001#C-NNN 映射到实现位置与验证方式，并填写里程碑、Concrete Steps、验收、
恢复方法和准确下一步。先评审计划，不要开始实现。
```

## 多份输入

先用 Prompt 明确全部输入：

```text
使用 $engineering-execution-plan 创建“Migrate storage”计划。
Research 输入是 R-003、R-007；ADR 输入是 ADR-004、ADR-009；
Design Docs 是 docs/design-docs/storage-schema.md 和
docs/design-docs/storage-migration.md，架构入口是 docs/design-docs/index.md。
先注册并验证 Design Doc 根目录，再检查 ADR 依赖闭包；缺少输入时停止。
```

ADR 引用的每份 Research 和 Design Doc 都必须出现在 ExecPlan 中。若 ADR-009
`depends_on: ["ADR-004"]`，不能只传 `--adr ADR-009`；依赖闭包必须显式完整。
完整案例见 `examples/architecture-input-set/README.md`。

## Fast track

用户要求实现一个局部、可逆的 adapter 清理。现有 accepted ADR 已规定边界，没有
新的架构选择，但已有架构仍然适用：

```text
使用 $engineering-execution-plan 为 adapter boundary 清理创建一个 ExecPlan。
现有 ADR-004 和 contract tests 已完整定义行为，因此 Research Gate 可标记
not_required；改动不产生独立持久选择，因此 Architecture Decision Gate 可标记
not_required，但 ADR-004 仍是 applicable architecture input。引用 ADR-004，保留
Architecture Compliance applicable，并把其 constraints 映射到 contract tests。
```

理由必须可核查。“任务很小”“用户说直接做”不足以说明为何 Decision Gate 不需要，
更不能作为忽略既有 ADR 的理由。

如果模块内 helper 重命名确实不受任何 architecture input 约束，则分别记录
Research Gate not_required、Architecture Decision Gate not_required 和
Architecture Compliance not_applicable 的理由；三个判断不能合并成一句套话。

## ADR 局部修订

旧决定总体仍成立，只调整 ADR-004#C-002：

```text
使用 $engineering-execution-plan 基于 concluded R-009 起草一份 scoped amendment，
amends ADR-004，并精确标记 ADR-004#C-002。写出新的 Decision Statement、C-NNN
constraints 和 Confirmation，保持 proposed，等待 Decision Owner。
```

accepted 后，任何命中 ADR-004#C-002 的 active EP 都必须同时引用 amendment；只
引用 ADR-004 会被判定为漏掉 current scoped amendment。

## ADR 替代

新证据推翻 ADR-004 的成立条件：

1. 创建并 conclude 新 Research。
2. 创建引用新 Research 的 proposed ADR-009。
3. 获得明确授权并接受 ADR-009。
4. 用户要求 Skill 建立替代链：

```text
使用 $engineering-execution-plan 将已接受的 ADR-009 记录为 ADR-004 的替代决定。
更新引用旧决定的 active ExecPlan，并报告无法继续满足 current Architecture
Compliance 的计划。
```

引用 ADR-004 的 active ExecPlan 随后必须更新；superseded ADR 不能继续作为 active
Architecture Compliance input。completed/cancelled EP 保留原 ADR digest，不改写历史。

## 普通修复不自动建记录

用户：“修复 cursor 等于 page_size 时不生成 next cursor 的问题。”

直接复现、修复和验证。用户没有要求保存 Bugfix 记录，不创建持久制品。

## 明确记录并升级 Bugfix

```text
使用 $engineering-execution-plan 为 spans-api 的 cursor page-size boundary
问题创建一条持久 Bugfix 记录，并在修复过程中维护证据与状态。
```

如果调查发现需要改变多个客户端的公共契约，先完成所需 Research/ADR，再创建 ExecPlan。随后：

```text
BF-001 已确认会改变共享 cursor contract。
使用 $engineering-execution-plan 将它升级并归档为 escalated，关联 EP-001，
把共享契约变更记录为升级原因。
```

## 拆 Task

```text
使用 $engineering-execution-plan 在 EP-001 下创建 Task
“Add gateway refresh contract”。Task 只保存局部工作集；
根 EXECPLAN.md 继续保存总体里程碑、接口和验收。
```

Task 使用稳定父 ID。根 `EXECPLAN.md` 继续保存总体上下文、里程碑、接口和验收。

## 压缩增长中的 ExecPlan

先把有效结论吸收到当前事实，把完整输出保存到 `artifacts/`，再请求预览：

```text
使用 $engineering-execution-plan 为 EP-001 预览一个 Milestone 1 Checkpoint。
当前事实：契约层已完成，适配层尚未实现。
当前里程碑：Milestone 2 — adapter integration。
准确下一步：编辑 src/adapter.ts 并运行 npm test。
绑定当前真实 Git revision；先 dry-run，不要直接压缩。
```

确认预览后，用户再明确要求应用 Checkpoint。未完成 Progress/Validation 和
open blocker 留在根计划；旧事件原文进入 sealed Checkpoint。

## 严格归档

```text
使用 $engineering-execution-plan 验证 EP-001。
只有验收全部通过、Task 全部终态、没有 open blocker、复盘已填写时，
才用实际 verified commit 和真实 CI job URL 归档为 completed。
条件不足就保持 active，并准确列出缺口。
```

未完成验收、非终态 Task、open blocker、未填写复盘或缺少 revision/evidence
都会阻止 v2.3+ completed。明确停止时可以：

```text
产品方向已经改变。使用 $engineering-execution-plan 取消 EP-001，
记录取消原因，保留已完成证据和未完成范围，不要伪装成 completed。
```

## 修复派生索引

```text
使用 $engineering-execution-plan 检查派生索引漂移。
先报告差异；确认只是托管区投影过期后，重建 Research、Decision、Plan 和 Bugfix
索引。不要修改事实制品或托管区外人工内容。
```

该操作重建 `RESEARCH.md`、`DECISIONS.md`、`PLANS.md` 和 `BUGFIXES.md`
托管区，不修改事实制品或托管区外人工内容。
