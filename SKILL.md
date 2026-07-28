---
name: execution-plan
description: |
  创建和维护仓库内的工程执行制品：为复杂、长时或需要跨会话恢复的工作建立自包含 ExecPlan；按用户明确要求记录局部 bugfix；维护进度、发现、决策、阻塞、Task、归档状态和技术债务。用户提到 EP、ExecPlan、执行计划、建 EP、拆 task、记录/归档 bugfix、查计划状态或登记技术债务时使用。复杂跨模块实现即使未点名 EP，也可使用。普通编码、一次性修 bug、代码解释和测试编写不会自动创建持久记录。
---

# Execution Plan

把计划当作可执行、可恢复、可验证的仓库制品。人类给出目标和判断，Agent 负责研究、维护计划、执行和验证。

## 制品路由

| 工作 | 制品 | 是否入库 |
|---|---|---|
| 小型、上下文明确、一次会话可完成 | 线程内轻量计划 | 默认否 |
| 用户明确要求记录的局部既有行为缺陷 | Bugfix | 是 |
| 跨模块、公共契约、显著未知、需要多里程碑或跨会话恢复 | ExecPlan | 是 |

- 不因出现“修 bug”“阻塞”“归档”等普通词自动建记录；先判断用户是否要求管理工程制品。
- Bugfix 一旦需要任务拆分、架构决策、公共契约变更或持续推进，升级为 ExecPlan。
- 新 ExecPlan 统一使用目录模式，不按验收条目数量选择模板：

```text
docs/exec-plans/active/ep-NNN_slug/
├── EXECPLAN.md
├── tasks/                 # 仅在独立追踪或并行推进有价值时创建
├── history/               # sealed checkpoint；按需创建
└── artifacts/             # 完整日志、trace、截图等；按需创建
```

`EXECPLAN.md` 始终是自包含、有界的当前事实源。Task 和 checkpoint 都不能成为恢复工作所必需的唯一上下文。

详细路由与状态机见 `references/templates.md`。

## 仓库布局

```text
docs/
├── .epctl/
│   ├── lock
│   └── state.json
├── PLANS.md
├── BUGFIXES.md
├── exec-plans/
│   ├── active/
│   ├── completed/
│   └── tech-debt-tracker.md
└── bugfixes/
    ├── active/
    └── completed/
```

旧仓库若使用 `docs/tech-debt-tracker.md`，继续读取该路径；不要静默移动历史文件。

## 优先使用确定性脚本

解析 `<skill-dir>` 为本 skill 所在目录。所有命令在目标仓库根目录运行：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . init
python3 <skill-dir>/scripts/epctl.py --repo . new-ep --slug unify-token-refresh --title "Unify token refresh"
python3 <skill-dir>/scripts/epctl.py --repo . new-task EP-001 --slug add-gateway-contract --title "Add gateway refresh contract"
python3 <skill-dir>/scripts/epctl.py --repo . new-bugfix --slug cursor-boundary --title "Fix cursor boundary"
python3 <skill-dir>/scripts/epctl.py --repo . new-debt --description "Trace coverage gap"
python3 <skill-dir>/scripts/epctl.py --repo . checkpoint EP-001 \
  --slug milestone-one --title "Milestone 1 complete" \
  --current-milestone "Milestone 2" \
  --summary "<current state>" --next-action "<exact next action>" \
  --dry-run
python3 <skill-dir>/scripts/epctl.py --repo . validate
python3 <skill-dir>/scripts/epctl.py --repo . validate --fix-index
python3 <skill-dir>/scripts/epctl.py --repo . reindex
python3 <skill-dir>/scripts/epctl.py --repo . status
python3 <skill-dir>/scripts/epctl.py --repo . archive-ep EP-001 --outcome completed
python3 <skill-dir>/scripts/epctl.py --repo . archive-bugfix BF-001 --outcome fixed
```

- 先运行 `init`；该命令只补缺失目录和索引，不覆盖已有内容。
- 用脚本分配 ID、复制 assets、更新索引、校验和归档。不要手工猜测下一个编号。
- active/completed 中的制品是事实源；`PLANS.md` / `BUGFIXES.md` 是可重建投影。发现缺项或陈旧行时运行 `reindex`，不要据索引推断制品不存在。
- `.epctl/state.json` 只保存编号高水位：允许故障造成跳号，不允许复用或覆盖旧 ID。
- 脚本不可用时，按 `assets/` 中的同名模板执行，并扫描索引与 active/completed 文件系统后取最大 ID +1。
- 不要求目标仓库使用 Git；普通文件移动后由 Git 自行识别 rename。

## 创建 ExecPlan

1. 先读仓库入口、相关代码和测试，确认现状。只在产品意图、权限、不可逆取舍或外部输入确实缺失时询问用户。
2. 运行 `new-ep` 创建目录和 `EXECPLAN.md`。
3. 完整填写模板；不得留下 `<!-- REQUIRED... -->` 标记。
4. 保证计划可以让无历史会话的 Agent 从当前工作树继续：
   - 解释目的、用户可观察结果和术语。
   - 在 Current Snapshot 写明当前里程碑、当前状态和准确下一动作。
   - 写明完整仓库相对路径、模块关系、接口与依赖。
   - 提供可修订的 `Plan of Work` 与独立可验证的里程碑。
   - 写清工作目录、精确命令、预期输出和证据位置。
   - 记录幂等性、失败重试、回滚和清理方法。
5. 上下文地图用于导航；同时在计划内复述执行所需的关键事实。不要只写“见某文档”。
6. 不预测耗时。进度时间戳只记录事实。

完整要求与模板字段见 `references/template.md`。

## 维护 Living Document

把内容分成两类：

- **当前事实**：Purpose、Current Snapshot、Context、Plan、Milestones、Validation、Recovery、Interfaces。发现新事实或改变路线时同步修订和精简。
- **历史记录**：Progress、Surprises & Discoveries、Decision Log、Blockers、Revision Notes。在当前 checkpoint 区间只追加；纠错时新增更正记录。

每个停止点都更新 Progress。每次改动当前事实时，在 Revision Notes 记录时间、作者、变化和原因。

“只追加”是逻辑历史不变量，不要求旧事件永远留在根文件。里程碑完成、交接前，或根文档超过约 800 行 / 64 KiB / 50 个活跃历史事件时建立 checkpoint：

1. 先把仍有效的发现和决策吸收到当前事实。
2. 把完整 transcript、trace 和截图移到 `artifacts/`，根文档只保留结论和路径。
3. 用 `checkpoint ... --dry-run` 预览，再去掉 `--dry-run` 封存历史。
4. 保证未完成 Progress、未完成验收和 open blocker 仍在根文档。
5. 只读根 `EXECPLAN.md` 做一次接手验证。

checkpoint 细则、迁移和恢复见 `references/checkpoints.md`。

## 拆分 Task

- 仅在 Task 能明确指定修改目标、独立验证、有限上下文推进时拆分。
- 使用 `new-task` 分配 EP 内唯一 ID。
- `parent_id` 使用稳定的 `EP-NNN`，不要写 `active/` 物理路径。
- 开始 Task 前检查 `depends_on` 均为 `done` 或 `cancelled`。
- 保持根 `EXECPLAN.md` 的进度、里程碑和关键决策同步，确保只读根计划仍可恢复。

## 处理未知与阻塞

先在授权范围内检索、运行小实验或建立 prototype/spike，并把证据写入 Surprises & Discoveries。

只在以下情况建立硬阻塞：

- 缺少权限、凭据或外部系统状态。
- 需要人类产品判断或不可逆决策。
- 缺失能力的建设明显超出当前范围。
- 继续执行会产生安全、数据或兼容性风险。

Blocker 使用 `open` / `resolved` / `dismissed` 状态。解除后保留原行，补充解决时间和结果；实体状态从 `blocked` 恢复为 `active` / `in_progress`。不要因历史上出现过 blocker 就持续报告阻塞。

## Bugfix

- 只在用户明确要求记录/跟踪局部缺陷时创建。
- 至少记录 Symptom、Scope、Root Cause、Fix、Verification 和证据。
- `blocked` 可恢复到 `in_progress`。
- 升级时创建 ExecPlan，填写 `linked_ep`，将 bugfix 设为 `escalated` 并归档；之后只在 ExecPlan 推进复杂工作。

详细字段见 `references/bugfix.md`。

## 严格完成与归档

完成 ExecPlan 前：

1. 运行真实验证，补充可观察结果和证据。
2. 确认 Validation 全部勾选。
3. 确认 Task 全部 `done` / `cancelled`。
4. 确认没有 `open` blocker。
5. 填写 Outcomes & Retrospective，说明结果、遗留项和经验。
6. 运行 `validate`，再运行 `archive-ep EP-NNN --outcome completed`。

验收未完成时保持 active/blocked，或明确改为 cancelled；不能把不完整计划标为 completed。

取消时先把 Task 改为 `done` / `cancelled`，再执行：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . archive-ep EP-NNN \
  --outcome cancelled --reason "<why work stopped>"
```

归档时只记录知识提升候选：

- 工程规范候选 → `docs/standards/` 或机械 lint/test。
- 架构决策候选 → draft ADR。
- `AGENTS.md` 只维护短入口和链接。

不要在“归档 EP”的隐含授权下自动追加 `AGENTS.md` 规则或直接生成 accepted ADR。

Bugfix 只有在：

- `fixed` 且 Verification 全部完成；
- `escalated` 且 `linked_ep` 已填写；或
- `cancelled`

时才能归档。

```bash
python3 <skill-dir>/scripts/epctl.py --repo . archive-bugfix BF-NNN \
  --outcome escalated --linked-ep EP-NNN --reason "<why this needs an EP>"
```

## 查看状态与技术债务

- 用 `status` 汇总验收、Task、未解决 blocker、checkpoint、根文档大小和最后活动时间。
- 用 `validate` 检查 ID、路径、状态、必需 section、依赖和索引完整性。
- 技术债务是反馈入口，不是垃圾桶。定期扫描 tracker，将可独立解决的条目转为小型修复或 ExecPlan，并关闭已解决条目。

## 参考

- 制品路由、状态机、兼容策略 → `references/templates.md`
- ExecPlan 自包含要求、必需 section、Living Document 规则 → `references/template.md`
- Bugfix 字段与升级/归档 → `references/bugfix.md`
- 有界根文档、checkpoint、压缩与恢复 → `references/checkpoints.md`
- 典型命令和场景 → `references/examples.md`
