# P3-B：真实 ADR 整合候选的约束与影响审查（仅建议）

> **性质：** 一次性、非规范性、只读的 Decision Owner 复核材料。此文件不新增 ADR、改变接受/退役状态、批准 Design、修改 EP，也不建立新的持续维护义务。源正文、当前效力和授权仍以 `epctl` 与原始 ADR 为准。

## 取证范围与方法

| 字段 | 本次依据 |
|---|---|
| 基线代码和工程制品 | `main`：`0134d3f01691b771dad6fa3b20fa18dd8eea3f30` |
| 固定评估时点 | `2026-10-30T00:00:00Z` |
| 复现运行 | [P3-B 只读审计](https://github.com/XiaoWeiKIN/RepoHarnessKit/actions/runs/40988147771)（审计分支提交 `28c903c72d52729fa9e165c5214f89950460cfec`；仅添加临时工作流，不改受管源） |
| 既有 P2 计算摘要 | `53ccca65f3c6f7857d2e6968f7503bbe4f6ddd7b39489b45e5afe4ea5de96192` |
| 本次结果 | **19** 个 accepted/current ADR；**9** 个逐项整合预览 → **6** 个带来源和影响的复核包 |
| 覆盖范围 | epctl 当前效力、`amends`/`depends_on` 闭包、sealed payload 与文档摘要、Active EP 的显式 ADR 引用、Proposed ADR 关系 |
| 未证明事项 | 源码/测试消费者的完整覆盖、原子决策之间语义等价、实施后的净收益、任一 Owner 的正式批准 |

**关键解释：** `active_plan_impact` 表示一个完整解析闭包与 Active EP 的 `adr_refs` 相交；它不意味着 EP 直接引用了该复核包主 ADR，也不意味着对应代码消费者已被完整检查。审计中各复核包的 `proposed_overlap` 均为空；不能因此推断没有未登记的外部消费者。

当前三个 Active EP 的**直接** ADR 引用如下（来自 `epctl.status_rows`）：

| 计划 | 直接 `adr_refs` |
|---|---|
| [EP-006](../exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md) | ADR-001、004、007、008、009 |
| [EP-058](../exec-plans/active/ep-058_implement-engineering-design-skill/EXECPLAN.md) | ADR-001、004、014、016、018、019 |
| [EP-094](../exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/EXECPLAN.md) | 无 |

## 六组初步处置

| 包 / 主 ADR | 责任主题 | 原候选 ADR | 闭包大小 | 原 resolver EP 交集 | 建议 |
|---|---|---|---:|---|---|
| 1 / [ADR-001](../adr/adr-001_split-engineering-research.md) | 研究/编排与品牌链 | [ADR-001](../adr/adr-001_split-engineering-research.md)、[ADR-004](../adr/adr-004_separate-workflow-orchestration-from-execution-planning.md)、[ADR-007](../adr/adr-007_repo-foundry-identity.md)、[ADR-008](../adr/adr-008_repofoundry-ai-brand.md) | 5 | EP-006、EP-058 | **保留，暂不合并** |
| 2 / [ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md) | Codex Bootstrap 与 Agent-neutral Harness | [ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md) | 7 | EP-006、EP-058 | **保留，待代码/适配器消费者审查** |
| 3 / [ADR-010](../adr/adr-010_spec-task-activation-router.md) | Spec 激活 Router 与 Agent-neutral Engine | [ADR-010](../adr/adr-010_spec-task-activation-router.md) | 10 | EP-006、EP-058 | **保留，继续强制激活门禁** |
| 4 / [ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md) | 治理元数据与可逆 ADR 效力 | [ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md) | 2 | EP-058 | **保留源约束，不自动收敛** |
| 5 / [ADR-018](../adr/adr-018_first-class-technical-design-documents.md) | Design 生产与文档拓扑 | [ADR-018](../adr/adr-018_first-class-technical-design-documents.md) | 9 | EP-006、EP-058 | **延期至 DD-011 Owner 审批后再判断** |
| 6 / [ADR-058](../adr/adr-058_lossless-adr-context-compaction.md) | ADR 工作上下文、聚焦检索与 History Pack | [ADR-058](../adr/adr-058_lossless-adr-context-compaction.md) | 5 | EP-058 | **保留三个独立能力，不合并** |

**建议汇总：** **5 组先保留各自现行原子决策；1 组（Design 相关）延期到明确的 Owner 审批后复核。当前没有足够证据支持直接创建替代 ADR，更没有证据授权退役或归档。** 这是工程复核建议，不是 Owner 已做出的决定。重复预览由 9 降到 6，只减少重复**审阅入口**，不证明减少 3 个实际修改或节省了具体工时。

## 分组审查与具体约束

### 复核包 1：[ADR-001](../adr/adr-001_split-engineering-research.md)

**解析闭包：** [ADR-001](../adr/adr-001_split-engineering-research.md)、[ADR-004](../adr/adr-004_separate-workflow-orchestration-from-execution-planning.md)、[ADR-007](../adr/adr-007_repo-foundry-identity.md)、[ADR-008](../adr/adr-008_repofoundry-ai-brand.md)、[ADR-009](../adr/adr-009_align-repofoundry-ai-skill-name.md)。

**修订边：** ADR-004 → ADR-001；ADR-007 → ADR-004；ADR-008 → ADR-007；ADR-009 → ADR-008。

**EP 交集（原 resolver 输出，并非直接依赖认定）：** EP-006 [ADR-001, ADR-004, ADR-007, ADR-008, ADR-009]；EP-058 [ADR-001, ADR-004]。Proposed overlap：0。

源 [ADR-001](../adr/adr-001_split-engineering-research.md) 将 Research 生产者和 EP 消费者分离；[ADR-004](../adr/adr-004_separate-workflow-orchestration-from-execution-planning.md) 决定编排层归属；[ADR-007](../adr/adr-007_repo-foundry-identity.md)、[ADR-008](../adr/adr-008_repofoundry-ai-brand.md) 和 [ADR-009](../adr/adr-009_align-repofoundry-ai-skill-name.md) 逐次调整对外标识与根 Skill 名称。它们构成不同时间和不同边界的已接受决策，并不因共享闭包就语义等价。**EP-006 直接引用 001/004/007/008/009，EP-058 直接引用 001/004。** P3-A 已更新 EP-006 的旧“推送 PR”下一步，但外部仓库命名意图仍需 Owner 裁定。建议：保留五份当前决定；在 EP-006 最终验收前不启动新整合 ADR。

### 复核包 2：[ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md)

**解析闭包：** [ADR-001](../adr/adr-001_split-engineering-research.md)、[ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md)、[ADR-004](../adr/adr-004_separate-workflow-orchestration-from-execution-planning.md)、[ADR-007](../adr/adr-007_repo-foundry-identity.md)、[ADR-008](../adr/adr-008_repofoundry-ai-brand.md)、[ADR-009](../adr/adr-009_align-repofoundry-ai-skill-name.md)、[ADR-011](../adr/adr-011_agent-neutral-harness-adapters.md)。

**修订边：** ADR-004 → ADR-001；ADR-007 → ADR-004；ADR-008 → ADR-007；ADR-009 → ADR-008；ADR-011 → ADR-002。

**EP 交集（原 resolver 输出，并非直接依赖认定）：** EP-006 [ADR-001, ADR-004, ADR-007, ADR-008, ADR-009]；EP-058 [ADR-001, ADR-004]。Proposed overlap：0。

[ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md) 的原始决定是 Codex 文档 Bootstrap 与非破坏性初始化；[ADR-011](../adr/adr-011_agent-neutral-harness-adapters.md) 以 Agent-neutral Core 和声明式 Adapter 修订产品边界。要核查的不同义务包括：**Codex 原生 Hook/短 AGENTS 入口**、**Core 共享文件所有权与版本迁移**、保留定制文件及手动适配路径。当前三个 Active EP **均没有直接把 ADR-002 或 ADR-011 列入 adr_refs**；resolver 出现 EP-006/058，是因为选择闭包还含它们直接引用的 ADR-001/004 等公共祖先。因此这一影响不是“EP-006/058 直接使用 Codex Bootstrap”的证据。建议：暂保留 ADR-002/011；如要整合，先从现有 Codex、Claude、Portable 适配器测试建立明确消费者映射。

### 复核包 3：[ADR-010](../adr/adr-010_spec-task-activation-router.md)

**解析闭包：** [ADR-001](../adr/adr-001_split-engineering-research.md)、[ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md)、[ADR-004](../adr/adr-004_separate-workflow-orchestration-from-execution-planning.md)、[ADR-005](../adr/adr-005_external-engineering-specifications.md)、[ADR-007](../adr/adr-007_repo-foundry-identity.md)、[ADR-008](../adr/adr-008_repofoundry-ai-brand.md)、[ADR-009](../adr/adr-009_align-repofoundry-ai-skill-name.md)、[ADR-010](../adr/adr-010_spec-task-activation-router.md)、[ADR-011](../adr/adr-011_agent-neutral-harness-adapters.md)、[ADR-012](../adr/adr-012_agent-neutral-spec-activation.md)。

**修订边：** ADR-004 → ADR-001；ADR-007 → ADR-004；ADR-008 → ADR-007；ADR-009 → ADR-008；ADR-011 → ADR-002；ADR-012 → ADR-010。

**EP 交集（原 resolver 输出，并非直接依赖认定）：** EP-006 [ADR-001, ADR-004, ADR-007, ADR-008, ADR-009]；EP-058 [ADR-001, ADR-004]。Proposed overlap：0。

[ADR-010](../adr/adr-010_spec-task-activation-router.md) 要求本地锁定 Spec、Applicability、精确需求及受信任 Hook 写入门禁；[ADR-012](../adr/adr-012_agent-neutral-spec-activation.md) 将候选、激活、审计转交 Agent-neutral Engine，并明确 Adapter 仅作事件/输出翻译。[ADR-015](../adr/adr-015_risk-adaptive-agent-governance.md) 当前直接依赖 ADR-012。**两者没有被本次三个 Active EP 直接列入 adr_refs**；resolver 的 EP-006/058 影响仍是公共祖先交集。需要保留的不变量是强制约束的精确性、离线摘要、路径覆盖、写入拒绝、手动降级与 Adapter 能力边界。建议：保留效力，先完成代码/测试消费者审计；不能以“新版中立 Engine 已存在”推断旧约束可退休。

### 复核包 4：[ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md)

**解析闭包：** [ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md)、[ADR-016](../adr/adr-016_reversible-decision-effect.md)。

**修订边：** ADR-016 → ADR-014。

**EP 交集（原 resolver 输出，并非直接依赖认定）：** EP-058 [ADR-014, ADR-016]。Proposed overlap：0。

[ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md) 的 **C-001** 规定治理对象的稳定元数据字段，**C-004** 规定状态与 seal 的验证；[ADR-016](../adr/adr-016_reversible-decision-effect.md) 通过 `amends_constraints` **精确指向 ADR-014#C-001、ADR-014#C-004**，增加独立的 ADR 当前效力生命周期、授权转移和历史不可改写约束。其余 ADR-014 结构性字段与证据契约不能默默丢弃。**EP-058 直接引用 ADR-014、ADR-016。** 这些是相邻但不同的治理责任，而非可互相替换的重复规则。建议：保留原子 ADR 与精确 scoped amendment，后续只有语义和迁移收益得到证明后才向 Decision Owner 提交新整合方案。

### 复核包 5：[ADR-018](../adr/adr-018_first-class-technical-design-documents.md)

**解析闭包：** [ADR-001](../adr/adr-001_split-engineering-research.md)、[ADR-004](../adr/adr-004_separate-workflow-orchestration-from-execution-planning.md)、[ADR-007](../adr/adr-007_repo-foundry-identity.md)、[ADR-008](../adr/adr-008_repofoundry-ai-brand.md)、[ADR-009](../adr/adr-009_align-repofoundry-ai-skill-name.md)、[ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md)、[ADR-016](../adr/adr-016_reversible-decision-effect.md)、[ADR-018](../adr/adr-018_first-class-technical-design-documents.md)、[ADR-019](../adr/adr-019_technical-architecture-design-packages.md)。

**修订边：** ADR-004 → ADR-001；ADR-007 → ADR-004；ADR-008 → ADR-007；ADR-009 → ADR-008；ADR-016 → ADR-014；ADR-019 → ADR-018。

**EP 交集（原 resolver 输出，并非直接依赖认定）：** EP-006 [ADR-001, ADR-004, ADR-007, ADR-008, ADR-009]；EP-058 [ADR-001, ADR-004, ADR-014, ADR-016, ADR-018, ADR-019]。Proposed overlap：0。

[ADR-018](../adr/adr-018_first-class-technical-design-documents.md) 的 **C-006** 是 Design 内容覆盖契约，**C-008** 是 Package 入口/成员约束；[ADR-019](../adr/adr-019_technical-architecture-design-packages.md) 精确修订这两个 C-NNN，改为以读者为中心的技术架构文档和按需关切。ADR-018 的 **C-001/C-003/C-007/C-010/C-011** 等仍控制 Design 生产者所有权、ADR 决策权、批准 revision 和 EP 归档门禁。**EP-058 直接引用 ADR-018/019，且所引用的 DD-011 仍为 Draft；EP-058 当前是 `archive_blocked`。** EP-006 仅通过共享祖先交集出现在该组影响中。建议：在 DD-011 Owner 做出独立批准或拒绝决定且 EP-058 重新验证前，**延期任何语义整合或效力调整**。

### 复核包 6：[ADR-058](../adr/adr-058_lossless-adr-context-compaction.md)

**解析闭包：** [ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md)、[ADR-016](../adr/adr-016_reversible-decision-effect.md)、[ADR-058](../adr/adr-058_lossless-adr-context-compaction.md)、[ADR-059](../adr/adr-059_focused-adr-context-materialization.md)、[ADR-060](../adr/adr-060_lossless-terminal-adr-history-packs.md)。

**修订边：** ADR-016 → ADR-014；ADR-059 → ADR-058；ADR-060 → ADR-058。

**EP 交集（原 resolver 输出，并非直接依赖认定）：** EP-058 [ADR-014, ADR-016]。Proposed overlap：0。

[ADR-058](../adr/adr-058_lossless-adr-context-compaction.md) 的 **C-006** 规定完整任务 Capsule 及选定约束，[ADR-059](../adr/adr-059_focused-adr-context-materialization.md) 仅在这个边界上新增显式的 `focused_partial`（完整模式仍为默认）；[ADR-060](../adr/adr-060_lossless-terminal-adr-history-packs.md) 修订 **ADR-058#C-001/C-008/C-009**，另行允许仅对严格终态 ADR 执行可逆、源字节无损的 History Pack。它没有给出自动退役权限。[ADR-061](../adr/adr-061_workflow-triggered-adr-maintenance.md) 仍以 `depends_on: ["ADR-060"]` 引用该历史打包契约。**EP-058 在本组仅通过共同的 ADR-014/016 依赖相交；没有直接引用 ADR-058/059/060。** 建议：保留独立的检索模式与物理存储决定，不做三合一 ADR；优先保证现有测试对精确原文、预算失败、打包/解包回滚和无默认启用的覆盖。

## 逐条跨文档修订边界（不能以摘要取代）

| 当前修订 ADR | 明确受影响的原始约束 | 不变更的原则 |
|---|---|---|
| [ADR-016](../adr/adr-016_reversible-decision-effect.md) | `ADR-014#C-001`、`ADR-014#C-004` | 元数据真实性与决策效力的独立授权 |
| [ADR-019](../adr/adr-019_technical-architecture-design-packages.md) | `ADR-018#C-006`、`ADR-018#C-008` | DD 生命周期、ADR 决策权与 EP 完成门禁不放宽 |
| [ADR-059](../adr/adr-059_focused-adr-context-materialization.md) | `ADR-058#C-006` | 完整 Capsule 默认行为不被自动切换为部分输出 |
| [ADR-060](../adr/adr-060_lossless-terminal-adr-history-packs.md) | `ADR-058#C-001`、`ADR-058#C-008`、`ADR-058#C-009` | 历史物理打包不得改变 ADR 当前效力或密封字节 |

上述编号来自各被接受 ADR 的原始 `amends_constraints`，是精确约束级引用；不得仅从 `amends` 边推断其他行被覆盖。早期 ADR 的决定主体存在完整文档式表述，不能将未列为结构化 C-NNN 的部分当作不存在。

## 源码一致性示例（完整来源摘要在审计日志）

| 主 ADR 原始文件 | 当前文档 SHA-256 | 已封存 Payload SHA-256 |
|---|---|---|
| [ADR-001](../adr/adr-001_split-engineering-research.md) | `d20c8a27223ce63c62050e5d4223e626cbf63efe132c184d4d8eb229d9c98470` | `9866f72aa09c400b36a9993681a73f7131381a28179a1f0832cd6a89a2ca8fae` |
| [ADR-002](../adr/adr-002_codex-project-documentation-bootstrap.md) | `4a4c9dae98bc9612bec6edc7f5c99fff569eab73be083f8ddf97e5904f80e820` | `a9ced6c6e80b1e246bd8fc7b90e53b7e9e6aff18a590c545f904dbf59ce61ad7` |
| [ADR-010](../adr/adr-010_spec-task-activation-router.md) | `c36c991121585d443737a80ab2b867c73961cf26affab352cbc2048615e3a470` | `b0a68a290d59d1279f40d8f1937b4d5ae8f85bc1766eb890a7151554adef364e` |
| [ADR-014](../adr/adr-014_governed-artifact-metadata-contract.md) | `e75628f5d30bac7688342164407ea3ba8f430c8d2857a793b32ee7bddfe01da4` | `bf56752a919cc0bc807ef703db9cb8e4192a1e1495597b954412db93a915b1e7` |
| [ADR-018](../adr/adr-018_first-class-technical-design-documents.md) | `399d055132c933ec6494dd7ca9a7b62d212c335cba49b80dc2fa2731ecd49dab` | `578dc79ed9f5fecc2d15a4ea550b63cc18e4e1301131476a4aa4439be81e9e6e` |
| [ADR-058](../adr/adr-058_lossless-adr-context-compaction.md) | `2e1564e3943e81816b8283690929be46f8572811f2cfa80e954cec88fb87c6a4` | `7fa638fb69bcd70969a7491fb7567ec0fa3b7ba72f34a0793333901c6bfeca1b` |

上述文件为本次固定 `main` 快照中的原文；审计核对 `epctl` 解析出的所有闭包成员文档 SHA-256 与 resolver `source_digests` 一致。原始审计脚本也要求工作树无变更。任何新的 ADR / EP 修订都会使这里的源快照不再代表最新状态，应重新运行只读检查。

## 建议的 Decision Owner 审阅次序

| 触发条件 | 下一步（仍只读） | 授权边界 |
|---|---|---|
| EP-006 的仓库命名范围已明确且验收完成 | 重新审阅 ADR-001/004/007/008/009 的具体仍适用约束，检查机器标识兼容 | Owner 可记录保留/再审，不隐式退休历史 |
| 需要缩小 Codex 与 Agent-neutral 协议的维护负担 | 为 ADR-002/011 与 ADR-010/012 增加实际代码路径、适配器测试和独立安装边界映射 | 没有代码覆盖前不做语义合并 |
| DD-011 获正式 Design Owner 决定、EP-058 重新验证 | 重放 ADR-014/016、ADR-018/019 的完整约束与受影响 EP | Design 批准不等于 ADR 效力变更；新 ADR 仍需 Decision Owner |
| 评估 ADR 物理存储或检索成本变化 | 对 ADR-058/059/060/061 分别验证完整/聚焦/打包的不可互换性及成本 | History Pack 资格与效果转移仍由原有命令控制 |

参考重放命令（在仓库根目录，均不携带 `--apply`）：

```bash
python3 -B engineering-execution-plan/scripts/memory_maintenance.py \
  --repo . --as-of 2026-10-30T00:00:00Z --json
python3 -B engineering-execution-plan/scripts/epctl.py --repo . \
  adr-consolidation-plan --adr ADR-001 --json
python3 -B engineering-execution-plan/scripts/epctl.py --repo . \
  adr-consolidation-plan --adr ADR-018 --json
python3 -B engineering-execution-plan/scripts/epctl.py --repo . validate
```

**审查结果边界：** 建议是“当前没有可安全执行的语义合并”，而不是“这些 ADR 永远无需维护”。只有新代码/测试消费者证据、明确的语义冗余或可量化的复核收益出现时，才为某一范围生成新的原子 ADR 草案，由 Decision Owner 单独批准后使用既有效果生命周期命令。任何检查都不能修改 sealed 决策正文或自动取消仍活跃的 ExecPlan。
