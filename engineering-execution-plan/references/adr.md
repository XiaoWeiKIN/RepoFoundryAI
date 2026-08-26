# ADR、Architecture Decision Gate 与 Compliance

## 目标

ADR 保存一个长期有效、具有架构意义的决定。它解释问题、决策驱动因素、可信选项、选择理由、后果和确认方式。

ADR 位于稳定路径：

```text
docs/adr/adr-NNN_slug.md
```

路径不随状态移动。`docs/DECISIONS.md` 是可重建索引。

新 ADR 只写入 `docs/adr/`。仓库已有其他架构目录时原地注册：

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  register-architecture-root docs/design-docs
```

配置保存在 `docs/.epctl/config.json`。注册目录必须位于仓库 `docs/` 下；
绝对路径、路径穿越和 symlink escape 会被拒绝。

## 何时需要 ADR

当存在两个以上可信选项，并至少满足一项时创建 ADR：

- 影响公共 API、事件、schema、配置或兼容协议。
- 跨模块、服务或团队边界。
- 形成长期技术约束。
- 迁移或逆转成本较高。
- 涉及安全、数据一致性、可靠性或部署拓扑。

局部实现细节、执行顺序和容易逆转的策略写入 ExecPlan Decision Log。没有需要独立
决定的架构级选择时，ExecPlan 必须写明 `architecture_decision_gate: not_required`
的具体理由；这不等于现有架构不适用，Architecture Compliance 仍需单独判断。

## 必需内容

- Context and Problem Statement
- Decision Drivers
- Research Evidence
- Considered Options
- Decision Outcome
- Decision Statement
- Normative Constraints
- Consequences
- Confirmation
- Revisit Triggers
- More Information
- Revision Notes

Research Evidence 应复述 sealed Synthesis 的决策级结论并提供路径。ADR 读者不需要重建全部 Research。

## 状态

```mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> accepted
    proposed --> rejected
    accepted --> under_review
    under_review --> accepted
    accepted --> retired
    under_review --> retired
    accepted --> superseded
    under_review --> superseded
```

- `proposed`：可由 Agent 起草和修订。
- `accepted`：明确 Decision Owner 批准，成为当前架构约束。
- `rejected`：明确 Decision Owner 拒绝，保留原因。
- `under_review`：历史决定仍为 accepted，但暂停作为新工作的当前约束。
- `retired`：明确撤销当前效力且没有 replacement；不暗示代码已自动回滚。
- `superseded`：被新的 accepted、current ADR 替代。

## 当前效力投影与索引升级

`docs/DECISIONS.md` 默认回答“哪些决定现在约束新工作”，而不是把所有曾经决定过的
ADR 平铺在一张表里。`epctl reindex` 从 ADR 文档和关系图派生五个受管区域：

```mermaid
flowchart LR
    A["ADR corpus"] --> P["Proposed<br/>尚未决定"]
    A --> E["Effective<br/>递归 current 的 accepted ADR"]
    A --> R["Review Required<br/>under_review 或传递 non-current"]
    A --> H["Historical<br/>rejected / retired / superseded"]
    E --> M["Current constraint amendments<br/>ADR-NNN#C-NNN → amendment ADR"]
```

- `Effective` 是新 ExecPlan 的默认入口。accepted ADR 只有在自身及
  `depends_on` / `amends` 传递闭包都 current 时才进入该表。
- current ADR 若被一份或多份 current ADR 局部修订，显示派生 effect
  `partially amended`；这不是新的 lifecycle status，两份 ADR 仍为 accepted。
- `Current constraint amendments` 精确列出当前生效的
  `ADR-NNN#C-NNN → amendment ADR` 映射；旧 schema 的非结构化修订仍通过
  `amended by` / `amends` 关系导航。
- `Review Required` 保留显式 review 与传递失效原因，避免下游 ADR 继续被误当作
  current；`Historical` 保留完整可审计路径，不删除 ADR。

旧版只有 `Proposed` / `Decided` 两张表时，`validate` 给出可升级告警。安装新版
RepoFoundry 后运行以下任一命令，只会重建受管索引区域，不修改 ADR 正文或 seal：

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . reindex
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  validate --fix-index
```

`status --json` 同步输出 `decision_outcome`、`projection`、`effect`、`current`、
`amended_by` 和 `review_reasons`；人类可读状态表展示 Decision、Effect、Current 与
Amended by。生命周期与索引使用同一派生模型，重复 reindex 必须 byte-stable。

只有 proposed ADR 可以执行 `decide-adr`。命令要求 `--decision-maker`；skill 还要求本轮对话存在用户或 Decision Owner 的明确授权。脚本记录授权主体，不能推断授权。

accepted 和 rejected schema 1.1/1.2/1.3/1.4 ADR 的正文、Research/ADR/Design 输入、
`decision_maker` 与 `decided` 一起进入 SHA-256。决定后修改这些内容会使
`validate` 失败。schema 1.4 还把不可变 `decision_outcome` 与可变 effect status
分离；`status`、`effect_changed_*`、`effect_reason` 和 replacement 链不进入决定
摘要。旧 schema 的 effect transition 也保持原摘要不变。

## 可执行的规范约束

新 ADR 使用 schema 1.4。`Decision Statement` 用一句话说明被接受或拒绝的完整
决定；`Normative Constraints` 把它拆成下游可引用的稳定约束：

Schema 1.4 还实现 Artifact Metadata Contract：`metadata_schema`、
`artifact_type`、stable `id`、`title`、`status`、`author`、`owner`、`created`、
`updated` 均存在；其中 stable identity、`author`、`owner`、`created` 进入决定
payload，而 `status` / `updated` 属于 effect lifecycle。`author`/`owner` 不能替代
`decision_maker`；决定后修改被封存的 attribution 会触发 digest drift。

| ID | Strength | Scope | Constraint | Confirmation |
|---|---|---|---|---|
| `C-001` | `must` | `gateway → token service` | 刷新请求必须携带 stable subject ID | contract test `refresh_subject_id` |
| `C-002` | `must_not` | `public refresh response` | 不得返回 provider refresh token | schema/lint rule `no_provider_token` |

- ID 在同一 ADR 内稳定，允许 `must`、`must_not`、`should`、`may`。
- EP 使用 `ADR-007#C-001` 形式引用，不复制一个没有身份的散文句子。
- Confirmation 必须落到 test、lint、schema check、CI evidence 或可观察人工验收。
- ADR 正文是规范源；Design Doc 解释结构和流程，不能静默新增或覆盖约束。

## 原子决定与有类型关系

一份 ADR 只回答一个可独立接受、拒绝、修订或替代的问题。一个功能需要多个架构
决定时，保留多份 ADR，并用 schema 1.2+ 的关系字段连接：

| 字段 | 语义 | 对旧 ADR 状态的影响 |
|---|---|---|
| `depends_on` | 当前决定成立所需的 accepted 前置决定 | 无 |
| `amends` | 当前决定缩小、扩展或改写旧决定的局部范围 | 两份都保持 accepted |
| `amends_constraints` | 被局部修改的稳定 `ADR-NNN#C-NNN` 集合 | 每个 `amends` ADR 至少对应一项 |
| `supersedes` | 当前决定完整替代旧决定 | 旧决定变为 superseded |
| `design_refs` | 解释接口、数据流、迁移或运维细节的 Design Docs | 无 |

`depends_on`、`amends`、`supersedes` 必须互斥、不能指向自身；
`depends_on` / `amends` 图必须无环。不要从无类型的 `relates_to` 猜测依赖，
迁移时由架构 Owner 显式补充关系。

```mermaid
flowchart LR
    Q["ADR-011<br/>查询行为"] -->|"depends_on"| B["ADR-010<br/>存储基座"]
    R["ADR-012<br/>路由行为"] -->|"depends_on"| B
    DQ["query-design.md"] -->|"design_refs"| Q
    DR["routing-design.md"] -->|"design_refs"| R
```

创建严格 ADR 的示例：

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . new-adr \
  --slug spans-routing \
  --title "Choose spans routing behavior" \
  --research R-004 \
  --depends-on ADR-010 \
  --amends ADR-008 \
  --amends-constraint ADR-008#C-002 \
  --design docs/design-docs/spans-env-placement-routing.md
```

`amends` 适用于旧决定总体仍成立、只有明确局部被修改的情况。若新旧约束不能同时
成立，必须使用 supersession，不能用 `amends` 回避旧 ADR 失效。schema 1.2/1.3 不允许
只写 `amends: ["ADR-008"]` 而不说明约束；旧 ADR 没有结构化 constraint 时，应新建
可审计的 replacement ADR，而不是猜测旧文档中的局部范围。

## Supersession

架构决定发生变化时：

1. 创建新的 proposed ADR，引用新 Research。
2. 完整说明旧决定为何不再满足 Decision Drivers。
3. 获得明确授权并接受新 ADR。
4. 预览影响，再用同一命令增加 `--apply`：

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  supersede-adr ADR-OLD --by ADR-NEW \
  --decision-maker "<explicit authority>" \
  --reason "<why the old effect must stop>"
```
5. 更新受影响的 active ExecPlan。

新 ADR 必须为 accepted 且递归 current。旧 ADR 变为 superseded 并填写
`superseded_by`；新 ADR 的 `supersedes` 增加旧 ID。受影响的 active ExecPlan 保持
结构有效，但暴露 `architecture_review_required` 并禁止 completed 归档，直到引用、
路线和执行约束同步更新；cancelled 仍可用于明确终止工作。

## Review、reaffirm 与 retirement

发现已落实的 ADR 不合理时，不编辑或删除历史正文。先预览：

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  transition-adr ADR-OLD --to under_review \
  --decision-maker "<explicit authority>" --reason "<new evidence>"
```

确认影响集合后增加 `--apply`。Review 会暂停该 ADR 以及递归依赖/修订它的 ADR 作为
新 Architecture Input；不会回滚代码，也不会改写受影响 EP。调查后可由明确权限以
`--to accepted` reaffirm，或以 `--to retired` 永久撤销效力。`retired` 和
`superseded` 为终态；重用旧方向必须创建新 ADR。

## 既有 ADR 与 Design Doc corpus

注册 root 后，验证器发现两类 ADR：

- 严格 ADR：schema 1 / 1.1 / 1.2 / 1.3 / 1.4，具有稳定 ID、必需 section、显式 Decision Owner
  和决定后 seal。
- linked legacy ADR：`doc_type: adr`，或文件名包含 `ADR-NNN`，并具有可识别
  status。

accepted legacy ADR 可以兼容作为 Architecture Input，但会告警其缺少 epctl
决策权记录和 seal。它是历史事实的只读接入，不代表 Agent 有权补签或改写。
后续方向变化时创建严格的新 ADR；legacy ADR 没有稳定 constraint IDs 时使用
`supersedes`，不要伪造 `amends_constraints`。

Design Doc 是架构输入，不是决策授权。`doc_type: design` 的 `draft` 文档可以在
实施中被引用，但会告警；`obsolete`、`abandoned`、`superseded`、`rejected`
文档不能作为输入。不要 hash 整个持续变化的 design-docs 目录；只引用本 EP
需要的文件，最终完成由代码 revision、CI evidence 与 EP archive seal 证明。

当前 Design Doc 使用 `metadata_schema: "1"`、`artifact_type: design-doc` 和在仓库
内唯一的 `DD-NNN`，并携带 title/status、author/owner、created/updated。注册 corpus
后 `validate` 会检查这些字段和 ID 冲突。缺少该层的既有 Design Doc 继续只读兼容
并告警；当作者本来就在实质修订它时再迁移，不为补 metadata 改写 sealed ADR。

## Decision Gate、Compliance 与 Input Set

EP v2.6+ 把两个过去容易混在一起的问题拆开：

| 问题 | 字段 | 允许状态 |
|---|---|---|
| 本次路线是否需要一个独立架构决定？ | `architecture_decision_gate` | `satisfied` / `not_required` |
| 哪些已有架构约束适用于本次实施？ | `architecture_compliance` | `applicable` / `not_applicable` |

Decision Gate 为 `satisfied` 时必须引用 accepted ADR；为 `not_required` 时必须记录
理由，但仍可引用适用的既有 ADR。Compliance 为 `applicable` 时必须有 ADR、Design
Doc 或架构入口；为 `not_applicable` 时必须无 architecture inputs 并记录理由。
proposed、rejected、under_review、retired 和 superseded ADR 都不能作为新 EP 的
current input。accepted ADR 还要求 `depends_on` / `amends` 的传递闭包全部 current。

Compliance applicable 时，输入集合由以下内容组成：

- `adr_refs`：直接需要的 ADR 以及 `depends_on` / `amends` 传递闭包。
- `design_refs`：EP 直接需要的 Design Docs，以及 ADR 声明的全部 Design Docs。
- `architecture_entrypoint`：可选的架构索引或概览页。
- `adr_constraint_refs`：所有 schema 1.2+ ADR constraints 的精确集合。
- `adr_evidence`：每份 sealed ADR 的 `ADR-NNN@sha256:<payload>` 摘要。

缺少依赖闭包、漏掉命中约束的 current scoped amendment、出现重复 ADR ID、关系
循环、引用不存在或 Design Doc 已废弃时，`new-ep` / `validate` 都失败。
`architecture_entrypoint` 只负责导航，不替代 ADR；Design Docs 可以在“不需要新
决定”的 EP 中作为解释输入，但不能提供 Decision Owner 授权或覆盖 ADR。

```mermaid
flowchart LR
    A["ADR-007#C-001"] --> M["Architecture Compliance Matrix"]
    M --> I["Implementation<br/>src/auth/refresh.ts"]
    M --> V["Verification<br/>contract test + schema lint"]
    S["ADR-007@sha256:..."] -.->|"pins decision payload"| M
```

active EP 必须跟随 current accepted ADR。若其既有输入后来 non-current，验证输出
review warning 而不是让仓库失效，status 暴露完成 blocker。completed/cancelled EP
保存完成或取消时的 ADR digest；决定后来改变 effect 不会抹掉历史证据，也不要求
改写归档正文。

## 历史 ADR payload revision

如果仓库迁移、格式清理或早期工具行为使同一个 ADR ID 留下多个真实 payload
revision，completed/cancelled EP 继续引用它完成时记录的 digest。不要修改 archived
EP、重新计算 `archive_sha256`，也不要在当前 ADR 与旧 digest 之间来回改写。

先从 repository-relative 文件预览导入：

```bash
python3 <engineering-execution-plan-dir>/scripts/epctl.py --repo . \
  register-adr-revision ADR-018 \
  --from-file evidence/adr-018-historical.md
```

确认 ID、payload digest、document digest、字节数和目标路径后，再重复命令并增加
`--apply`。若旧字节只存在于本地 Git object database，可以显式使用
`--from-git-blob <full-40-or-64-hex-object-id>`；这只是一次性 source adapter，
不会让 `validate` 依赖 Git。

应用后，严格 ADR 文档位于：

```text
docs/.epctl/adr-revisions/ADR-NNN/sha256-<payload>.md
```

该路径按 ADR ID 和 payload digest 唯一寻址。重复导入相同字节是 no-op；相同路径
出现不同字节、文件名与 payload 不一致、source ID 不一致、非 decided ADR、symlink
或篡改都会失败。正常验证流程如下：

```mermaid
flowchart LR
    E["completed/cancelled EP adr_evidence"] --> C{"匹配当前 ADR payload？"}
    C -->|"是"| P["通过当前 ADR 验证"]
    C -->|"否"| H["读取 repository-owned historical revision"]
    H --> V{"ID、状态、payload、文件名和内容均有效？"}
    V -->|"是"| P
    V -->|"否或缺失"| F["fail closed"]
```

历史 resolver 使用选中 revision 的 Research、ADR 关系、Design references 和
constraint rows 验证归档计划。active EP 从不回退到历史 registry；它仍必须匹配
当前 accepted ADR 和 current scoped amendments。

ExecPlan 必须在 `Research and Architecture Inputs` 中复述：

- 选择的架构方向。
- 对模块、接口、数据和部署的约束。
- 负面后果与迁移义务。
- ADR Confirmation 如何进入测试、lint 或验收。

并在 `Architecture Compliance Matrix` 中让每个结构化 constraint 恰好出现一次，
明确它由哪里实现或保持、怎样被验证。引用提供审计链；矩阵把规范变成执行契约。

引用提供审计链；根 ExecPlan 仍需自包含。
