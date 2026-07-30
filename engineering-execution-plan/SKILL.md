---
name: engineering-execution-plan
description: |
  消费已完成的工程 Research/Synthesis 与 sealed Benchmark evidence，创建和维护仓库内的 ADR、ExecPlan、Task、Checkpoint、Bugfix 与技术债务，并支持多个预声明 Benchmark Scenario 共同作为一个 EP 的完成门禁。适用于用户提到 engineering-execution-plan、旧称 execution-plan、EP、ExecPlan、执行计划、ADR、架构决策、多个压测驱动开发、拆 task、压缩计划、记录或归档 bugfix、查状态、登记技术债务及文档—代码 CI 契约。初始化 Codex Agent-first 项目、创建 AGENTS.md/ARCHITECTURE.md 或验证项目 Harness 时使用 engineering-workflow；需要新的可复现测量时使用 engineering-benchmark；需要资料搜集、跨来源解释、多文档 Research corpus 或 Synthesis 时使用 engineering-research。本 skill 只依赖版本化文件契约，不依赖其他 Skill 的安装路径。ADR 的接受或拒绝必须有用户或 Decision Owner 的明确授权。普通编码、一次性局部修复、代码解释和测试编写不会自动创建持久制品。
---

# Engineering Execution Plan

把复杂工程工作组织成可追溯、可恢复、可机械验证的仓库制品。默认工作流是：

项目级 Harness 初始化属于 `engineering-workflow`；本 skill 的 `init` 只创建
ADR、ExecPlan、Bugfix 等执行治理制品。

```mermaid
flowchart LR
    F["功能目标"] --> Q{"存在决策相关未知？"}
    F --> B["engineering-benchmark<br/>可选：预声明 Scenario + sealed Run"]
    B -->|"路线未知或证据矛盾"| R
    B -->|"最终 revision 验收"| G["Benchmark Gate Set<br/>0..N 个预声明 Scenario"]
    Q -->|"是"| R["engineering-research 或兼容生产者<br/>问题、证据、多文档 corpus"]
    R --> S["Sealed Manifest + Synthesis<br/>版本化文件契约"]
    Q -->|"否，写明理由"| RG["Research Gate<br/>not_required"]
    S --> A{"存在架构级选择？"}
    A -->|"是"| P["Proposed ADR"]
    P --> H["用户 / Decision Owner<br/>明确接受或拒绝"]
    H --> D["Accepted ADR 集合<br/>依赖 / 修订关系"]
    A -->|"否，写明理由"| AG["Architecture Gate<br/>not_required"]
    D --> I["Architecture Input Set<br/>ADRs + Design Docs + 入口"]
    I --> EP["ExecPlan v2.5<br/>自包含计划 + 完成证明"]
    G --> EP
    RG --> A
    AG --> EP
```

Engineering Research 负责减少未知并输出 sealed Manifest/Synthesis；本 skill
从该文件契约开始，负责 ADR、ExecPlan 和实施生命周期。生产者可以是
`engineering-research`、BMAD、其他 Deep Research 工具或人工流程，只要制品满足
契约。引用提供审计链；下游制品仍需复述执行所需的结论和约束。

Engineering Benchmark 负责可复现测量。会改变路线的 Benchmark 先由 Research
解释；已决定路线的 final-revision Benchmark 可以直接进入 EP 验收。一个 EP
可以预声明多个 `BS-NNN`，每个 Scenario 代表一个独立的开发门禁，不合并成总分。
完成时，每个 Scenario 必须恰好由一个同 revision 的 passed sealed Run 覆盖。EP
用 `benchmark:BR-NNN@sha256:<payload>` 引用证据并按文件契约验真，不调用
Benchmark Skill。

## 制品路由

| 情况 | 制品 |
|---|---|
| 小型、上下文明确、一次会话可完成 | 线程内轻量计划 |
| 用户明确要求记录的局部既有行为缺陷 | Bugfix |
| 需要可复现测量、性能/容量对比或回归证据 | 切换到 `engineering-benchmark` |
| 关键事实不清、需要比较方案或实验 | 切换到 `engineering-research` |
| 存在影响长期边界且逆转成本较高的选择 | ADR |
| 跨模块、多里程碑、需跨会话恢复或已有决策待实施 | ExecPlan |

复杂功能默认先取得 concluded Research，尤其是涉及公共契约、安全、可靠性、
数据、迁移、第三方选型、prototype，或 Benchmark 会改变架构路线时。新的可复现
测量使用 `engineering-benchmark`；跨来源解释和 Synthesis 使用
`engineering-research`。以下情况可直接进入 ExecPlan，但必须记录具体的
Research Gate 跳过理由：

- 当前 accepted ADR 和代码事实已覆盖所需输入。
- 权威标准或用户已经固定实现方向。
- 工作局部、可逆，且没有会改变计划路线的未知。

存在两个以上可信选项，并涉及公共接口、跨系统边界、长期约束、高迁移成本、安全、数据一致性、可靠性或部署拓扑时创建 ADR。局部且易逆转的实现取舍写入 ExecPlan Decision Log，并记录 Architecture Gate 跳过理由。

Bugfix 一旦需要 Research、ADR、任务拆分、公共契约变更或持续推进，升级为 ExecPlan。普通“修 bug”仍是实现请求；用户未要求记录时不创建 Bugfix 台账。

完整判定与状态机见 `references/templates.md`。消费 manifest-bearing Research
前读取 `references/research.md`；起草或决定 ADR 前读取
`references/adr.md`。

## 仓库布局

```text
docs/
├── .epctl/
│   ├── state.json
│   └── config.json          # 可选：注册既有 architecture roots
├── RESEARCH.md
├── DECISIONS.md
├── PLANS.md
├── BUGFIXES.md
├── research/
│   ├── active/r-NNN_slug/
│   │   ├── RESEARCH.md
│   │   ├── SYNTHESIS.md
│   │   ├── notes/
│   │   └── artifacts/
│   └── completed/
├── adr/
│   └── adr-NNN_slug.md
├── design-docs/             # 可选：既有 ADR / Design Doc corpus
├── exec-plans/
│   ├── active/ep-NNN_slug/
│   │   ├── EXECPLAN.md
│   │   ├── tasks/
│   │   ├── history/
│   │   └── artifacts/
│   ├── completed/
│   └── tech-debt-tracker.md
└── bugfixes/
    ├── active/
    └── completed/
```

Research 结论或取消时整体移动到 `research/completed/`。新 ADR 始终写入
`docs/adr/`，路径稳定且不随状态移动。既有 ADR / Design Doc corpus 可以原地注册，
不要求搬迁。四个根索引都是可重建投影；制品文件才是事实源。

## 优先使用确定性脚本

把 `<skill-dir>` 解析为本 skill 所在目录。所有命令在目标仓库根目录运行：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . init
python3 <skill-dir>/scripts/epctl.py --repo . register-architecture-root \
  docs/design-docs

python3 <skill-dir>/scripts/epctl.py --repo . new-adr \
  --slug cache-topology --title "Choose cache topology" --research R-001 \
  --depends-on ADR-004 --design docs/design-docs/cache-topology.md
python3 <skill-dir>/scripts/epctl.py --repo . decide-adr ADR-001 \
  --outcome accepted --decision-maker "<explicit authority>"
python3 <skill-dir>/scripts/epctl.py --repo . supersede-adr ADR-001 \
  --by ADR-002

python3 <skill-dir>/scripts/epctl.py --repo . new-ep \
  --slug implement-cache --title "Implement cache topology" \
  --research R-001 --adr ADR-004 --adr ADR-005 \
  --design docs/design-docs/cache-topology.md \
  --architecture-entrypoint docs/design-docs/index.md \
  --benchmark-scenario BS-003 \
  --benchmark-scenario BS-004

python3 <skill-dir>/scripts/epctl.py --repo . validate
python3 <skill-dir>/scripts/epctl.py --repo . validate --fix-index
python3 <skill-dir>/scripts/epctl.py --repo . reindex
python3 <skill-dir>/scripts/epctl.py --repo . status
```

重复引用时重复写 `--research`、`--adr`、`--design` 或
`--benchmark-scenario`。注册信息写入
`docs/.epctl/config.json`，本地和 CI 因而使用同一组 architecture roots。如果某个
Gate 不需要正式制品：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . new-ep \
  --slug local-cleanup --title "Clean up local adapter" \
  --research-not-required-reason "<specific existing evidence>" \
  --architecture-not-required-reason "<why no durable choice exists>"
```

- 先运行 `init`；它只补缺失目录和索引，不覆盖已有内容。
- 用脚本分配 ADR/EP 等本 skill 拥有的 ID、复制 assets、迁移状态、封存
  payload、重建索引和验证引用。不要手工猜编号。
- `.epctl/state.json` 保存编号高水位。故障可以造成跳号，不能复用旧 ID。
- `validate --fix-index` 只修复派生索引，不改事实制品。
- 脚本不可用时按 `assets/` 模板执行，并扫描文件系统、索引和高水位后取最大 ID +1。
- 不要求目标仓库使用 Git。

## 消费 Research 与 Synthesis

1. 如果仍有会改变路线的未知，先使用 `engineering-research` 或其他兼容流程。
2. 只让 `concluded` Research 满足 Gate；cancelled 或 active Research 都不能。
3. schema 1.1 Research 还必须有 `owner`、`maturity: review_ready` 和完整
   `approved_by/approved_at/approval_ref`；decision-ready 本身不是结束授权。
4. 验证 sealed `SYNTHESIS.md` 正文摘要。
5. 如果控制页声明 `RESEARCH_MANIFEST.json`，还必须验证：
   - schema 与 Research ID；
   - sealed manifest payload；
   - package-relative 文档存在且 bytes/SHA-256 匹配；
   - entrypoint 属于文档集合。
6. 兼容没有 manifest 的既有 v1 Research，但不要把这种兼容当作新制品模板。
7. 在 ADR 与 ExecPlan 中复述关键结论、置信边界、负面证据、成立条件和剩余未知。

本仓库的 `epctl` 暂时保留 legacy Research 创建/归档命令，供既有自动化迁移；
新 Research 不再从本 skill 的主流程创建。

## ADR 与显式决策权

Agent 可以调研、比较并起草 `proposed` ADR。只有当前对话或明确授权来源中出现用户/Decision Owner 对具体 ADR 结果的明确接受或拒绝，才可运行 `decide-adr`。

以下表达不构成决策授权：要求分析、要求起草、同意继续研究、同意实施整个 skill 改造、沉默或推断出的偏好。授权必须能回答“谁决定了哪份 ADR 的哪个结果”。

决定前：

1. 复述 sealed Synthesis 中影响选择的结论和证据路径。
2. 写全 Context、Decision Drivers、可信选项、Outcome、Consequences、Confirmation 和 Revisit Triggers。
3. 把真实授权主体传给 `--decision-maker`。

accepted/rejected schema 1.1 ADR 的正文、Research/ADR/Design 输入和决策授权由
SHA-256 一并封存。方向变化时创建并接受新 ADR，再按语义使用 `amends` 或执行
`supersede-adr ADR-OLD --by ADR-NEW`；不要编辑旧决定。Superseded ADR 不能满足
新 ExecPlan 的 Architecture Gate。

一份 ADR 只记录一个原子决定，不因一个功能需要多个决定而合并成“大 ADR”：

- `depends_on` 表示必须同时成立的 accepted 前置决定。
- `amends` 表示新决定只修订旧决定的一部分；两者仍是当前决定。
- `supersedes` 表示完整替代，旧 ADR 进入 superseded。
- `design_refs` 指向承载接口、数据流、迁移细节的 Design Docs。

关系必须无环且互斥。ExecPlan 的 `adr_refs` 必须包含 `depends_on` / `amends`
传递闭包，不能只引用叶子 ADR。

既有 `docs/design-docs` 等目录先用 `register-architecture-root` 注册。
`doc_type: adr` 或文件名含 `ADR-NNN` 的文档会被发现；缺少 epctl
`decision_maker` / seal 的 accepted 旧 ADR 可兼容满足 Gate，但验证会持续告警，
工具把它视为只读。后续变化应创建严格的新 ADR，不要就地伪造历史授权。

## 创建 ExecPlan

执行前读取 `references/template.md`。

1. Research Gate 必须引用所有相关 concluded Research，或提供具体 not-required 理由。
2. Architecture Gate 必须引用依赖闭包内所有当前 accepted ADR，或提供具体 not-required 理由。
3. ADR 引用的 Research 和 Design Docs 也必须进入 ExecPlan 的对应引用数组。
4. 多文档架构集可指定一个 `architecture_entrypoint`，供人和 Agent 从索引开始阅读。
5. 对每个需要性能、容量、可靠性或回归验收的独立维度，先完成一个稳定的
   Benchmark Scenario。不要等实现完成、看到结果后才补门禁。
6. 运行 `new-ep` 创建 v2.5 目录和模板；对每个必需 Scenario 重复
   `--benchmark-scenario BS-NNN`。没有 Benchmark 门禁时保留空集合。
7. 在 `Benchmark Gate Set` 中写清每个 Scenario 驱动哪个开发决定或里程碑。
   不同环境、流量模型或判定规则保持为不同 Scenario，不聚合成不可解释的总分。
8. 完整填写所有 REQUIRED section，并在 `Research and Architecture Inputs` 中复述：
   - 支持路线的关键证据与置信边界；
   - accepted ADR 的接口、数据、运维、迁移和负面后果；
   - 仍需在实现中验证的未知；
   - 跳过 Gate 的具体理由。
9. 保证无历史会话的 Agent 只读当前工作树和根 `EXECPLAN.md` 就能继续：
   - 解释目的、术语、用户可观察结果和系统现状；
   - 给出准确仓库相对路径、接口与依赖；
   - 提供独立可验证里程碑、工作目录、命令、预期输出和证据位置；
   - 写明幂等重试、回滚、迁移与清理。

上游引用用于审计，不得替代根计划内的执行上下文。不要预测耗时；时间戳只记录事实。

Benchmark 驱动开发采用闭环而不是自动改代码：Run 为 `failed`、
`inconclusive` 或 `errored` 时，保留 sealed evidence，在 Current Snapshot /
Progress 写明未满足的 Scenario，把修复落到对应 Milestone 或有限 Task，再创建新
Run 重测。只有规则本身确认错误时才先修订计划并创建新 Scenario；不能根据已看到
的结果降低原 Scenario 阈值。

## 维护有界 Living Document

当前事实随路线更新并保持精简：Purpose、Current Snapshot、Context、Inputs、
Benchmark Gate Set、Plan、Milestones、Validation、Recovery、Interfaces。

当前 checkpoint 区间内追加历史：Progress、Surprises & Discoveries、Decision Log、Blockers、Revision Notes。纠错时新增更正记录。每个停止点更新 Progress；修改当前事实时记录 Revision Notes。

里程碑完成、交接前，或根文档超过约 800 行、64 KiB、50 个活跃历史事件时：

1. 把仍有效的发现和决定吸收到当前事实。
2. 把完整输出移到 `artifacts/`。
3. 读取 `references/checkpoints.md`。
4. 读取 `references/integrity.md`，取得当前仓库或工作区 revision。
5. 先运行带 `--revision` 的 `checkpoint ... --dry-run`，确认后再正式封存。
6. 保证未完成 Progress/Validation 和 open blocker 留在根文件。
7. 只读根 `EXECPLAN.md` 做一次恢复检查。

Checkpoint 是 sealed 历史链，不能成为继续工作的必读前置。

## Task、未知与阻塞

- 仅在工作能指定有限修改目标和独立验证时创建 Task。
- Task 使用稳定 `parent_id: EP-NNN`；开始前检查依赖均为 `done` 或 `cancelled`。
- 根 ExecPlan 始终同步总体进度、接口和关键决定。
- 技术未知优先通过 Research、仓库检索或最小实验解决。
- 只有缺权限/凭据/外部状态、人类产品判断、范围外能力，或继续会造成安全、数据、兼容风险时建立 open blocker。
- blocker 解除后补充结果并恢复实体状态，不因历史阻塞持续报告 blocked。

## Bugfix 与技术债务

用户明确要求持久记录局部缺陷时使用 Bugfix，并读取 `references/bugfix.md`。至少记录 Symptom、Scope、Root Cause、Fix、Verification 和证据。升级为复杂工作时创建符合 Gate 的 ExecPlan，将 Bugfix 设为 `escalated`、填写 `linked_ep` 并归档，后续只在 EP 推进。

技术债务是反馈入口。用户未提供优先级或目标日期时使用 `unspecified` / `unscheduled`，不要猜测。

## 严格完成与归档

完成 ExecPlan 前：

1. 运行真实验证并记录结果和证据。
2. 勾选全部 Validation。
3. 确认 Task 全部 `done` / `cancelled`。
4. 确认没有 open blocker。
5. 填写 Outcomes & Retrospective。
6. 取得实际通过验证的 repository/workspace revision 和证据引用。
   对 v2.5 `required_benchmark_scenarios` 中的每个 Scenario，取得恰好一个
   passed sealed Run。sealed Benchmark 使用
   `benchmark:BR-NNN@sha256:<manifest-payload-sha256>`；Run 的
   `subject_revision` 必须等于同一个 `verified_revision` 且 outcome 必须是
   `passed`。缺一个、重复覆盖一个、或引用未声明 Scenario 都会阻止归档。
7. 运行 `validate`，再运行：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . archive-ep EP-NNN \
  --outcome completed \
  --verified-revision "<vcs-or-snapshot-revision>" \
  --evidence "benchmark:BR-014@sha256:<payload>" \
  --evidence "benchmark:BR-015@sha256:<payload>"
```

不完整计划保持 active/blocked，或在明确停止时以原因归档为 cancelled。不能靠口头确认、force 或删除验收项伪装完成。

归档只记录知识提升候选。新的架构决定仍需 proposed ADR 和独立明确授权；不要在“归档 EP”的隐含授权下接受 ADR 或修改 `AGENTS.md`。

用户明确要求把模块设计、最佳实践或 EP 过程整理成分享材料时，使用独立的
`engineering-case-study` Skill。EP 完成、归档或出现 knowledge promotion
candidate 本身都不构成生成案例的触发条件。

## 状态与验证

- `status` 汇总 Research 问题、Synthesis、ADR、Benchmark Scenario Gate、验收、
  Task、blocker、Checkpoint 和文档大小。
- `validate` 检查 ID、路径、状态、必需 section、引用、依赖、payload 和索引。
- `reindex` 从事实制品重建 Research、ADR、ExecPlan 和 Bugfix 投影。
- CI 只调用仓库内唯一检查入口；GitHub、GitLab 或其他 CI 平台不得复制校验逻辑。
- accepted ADR 的 Confirmation 应指向测试、lint、schema check 或明确人工验收。
- completed v2.3+ EP 必须保存 `verified_revision` 和至少一个
  `verification_evidence`，归档正文由 `archive_sha256` 封存；Checkpoint 必须
  保存 `repository_revision`。
- `benchmark:` evidence 会验证本地 sealed Manifest、精确文件清单、SHA-256、
  `passed` outcome、Scenario Gate 的一一覆盖和共同 final revision；普通
  `ci:` / `artifact:` 引用保持原语义。

## 参考

- 制品路由、状态机、兼容策略 → `references/templates.md`
- Research/Synthesis 消费契约与 manifest 兼容 → `references/research.md`
- sealed Benchmark 作为 final-revision evidence → `references/benchmark.md`
- ADR 门槛、授权、状态与 supersession → `references/adr.md`
- 多 ADR / Design Doc Architecture Input Set 示例 →
  `examples/architecture-input-set/README.md`
- ExecPlan 自包含要求与 Living Document → `references/template.md`
- Checkpoint、压缩与恢复 → `references/checkpoints.md`
- 文档—代码完整性、CI 适配与合并门禁 → `references/integrity.md`
- Bugfix 字段与升级/归档 → `references/bugfix.md`
- Prompt 示例、典型场景和端到端输出边界 → `references/examples.md`
