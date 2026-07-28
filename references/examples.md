# 使用示例

以下命令都在目标仓库根目录运行。`<execution-plan-dir>` 是本 skill 目录；
Research 的生产命令来自独立注册的 `<engineering-research-dir>`。两个目录之间
没有固定相对路径。

## 可运行的端到端样例

发行仓库中的 `examples/cache-topology/README.md` 从四篇 linked corpus 文档
开始，展示完整的 R-001、sealed Synthesis/Manifest、明确授权的 ADR-001 和
gated EP-001。需要理解“每份制品实际写什么”时先读该例；以下章节继续作为命令
与边界速查。

## 初始化

```bash
python3 <engineering-research-dir>/scripts/researchctl.py --repo . init
python3 <execution-plan-dir>/scripts/epctl.py --repo . init
```

只补缺失目录、四个派生索引和技术债务登记册，不覆盖人工内容。

## 完整功能生命周期

用户：“先充分研究网关、BFF、SDK 当前的 token 刷新契约，比较兼容方案，形成架构决定，再给开发计划。”

创建 Research：

```bash
python3 <engineering-research-dir>/scripts/researchctl.py --repo . new-research \
  --slug token-refresh-contract \
  --title "Research token refresh contract"
```

填写 `RESEARCH.md`，把聚焦分析写到 `notes/`，把完整命令输出写到
`artifacts/`。所有 `RQ-NNN` 已回答或明确处置、Synthesis 决策就绪后：

```bash
python3 <engineering-research-dir>/scripts/researchctl.py --repo . archive-research R-001 \
  --outcome concluded
```

公共契约具有架构意义，创建 proposed ADR：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . new-adr \
  --slug token-refresh-contract \
  --title "Choose token refresh contract" \
  --research R-001
```

Agent 写全 ADR 后停在 proposed。用户或 Decision Owner 明确接受该 ADR 时：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . decide-adr ADR-001 \
  --outcome accepted \
  --decision-maker "API Architecture Council"
```

最后创建 gated ExecPlan：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . new-ep \
  --slug implement-token-refresh \
  --title "Implement token refresh contract" \
  --research R-001 \
  --adr ADR-001
```

在 `Research and Architecture Inputs` 复述兼容约束、迁移义务、负面后果和仍需验证的未知。随后填写里程碑、Concrete Steps、验收与恢复方法。

## 多份输入

参数通过重复 flag 表示。先注册既有架构文档目录：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . \
  register-architecture-root docs/design-docs

python3 <execution-plan-dir>/scripts/epctl.py --repo . new-ep \
  --slug migrate-storage \
  --title "Migrate storage" \
  --research R-003 --research R-007 \
  --adr ADR-004 --adr ADR-009 \
  --design docs/design-docs/storage-schema.md \
  --design docs/design-docs/storage-migration.md \
  --architecture-entrypoint docs/design-docs/index.md
```

ADR 引用的每份 Research 和 Design Doc 都必须出现在 ExecPlan 中。若 ADR-009
`depends_on: ["ADR-004"]`，不能只传 `--adr ADR-009`；依赖闭包必须显式完整。
完整案例见 `examples/architecture-input-set/README.md`。

## Fast track

用户要求实现一个局部、可逆的 adapter 清理。现有 accepted ADR 已规定边界，没有新的架构选择：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . new-ep \
  --slug clean-adapter \
  --title "Clean adapter boundary" \
  --research-not-required-reason \
  "ADR-004 and current contract tests fully define the behavior." \
  --architecture-not-required-reason \
  "The change stays behind the accepted boundary and adds no durable choice."
```

理由必须可核查。“任务很小”“用户说直接做”不足以说明为何 Gate 不需要。

## ADR 替代

新证据推翻 ADR-004 的成立条件：

1. 创建并 conclude 新 Research。
2. 创建引用新 Research 的 proposed ADR-009。
3. 获得明确授权并接受 ADR-009。
4. 建立替代链：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . supersede-adr ADR-004 \
  --by ADR-009
```

引用 ADR-004 的 active ExecPlan 随后必须更新；superseded ADR 不能继续满足 Architecture Gate。

## 普通修复不自动建记录

用户：“修复 cursor 等于 page_size 时不生成 next cursor 的问题。”

直接复现、修复和验证。用户没有要求保存 Bugfix 记录，不创建持久制品。

## 明确记录并升级 Bugfix

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . new-bugfix \
  --slug cursor-boundary \
  --title "Fix cursor generation at page-size boundary" \
  --area spans-api
```

如果调查发现需要改变多个客户端的公共契约，先完成所需 Research/ADR，再创建 ExecPlan。随后：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . archive-bugfix BF-001 \
  --outcome escalated \
  --linked-ep EP-001 \
  --reason "The fix changes a shared cursor contract."
```

## 拆 Task

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . new-task EP-001 \
  --slug add-gateway-contract \
  --title "Add gateway refresh contract"
```

Task 使用稳定父 ID。根 `EXECPLAN.md` 继续保存总体上下文、里程碑、接口和验收。

## 压缩增长中的 ExecPlan

先把有效结论吸收到当前事实，把完整输出保存到 `artifacts/`，再预览：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . checkpoint EP-001 \
  --slug milestone-one \
  --title "Milestone 1 complete" \
  --current-milestone "Milestone 2: adapter integration" \
  --summary "契约层已完成；适配层尚未实现。" \
  --next-action "编辑 src/adapter.ts 并运行 npm test。" \
  --revision "git:<current-commit>" \
  --dry-run
```

确认后去掉 `--dry-run`。未完成 Progress/Validation 和 open blocker 留在根计划；旧事件原文进入 sealed Checkpoint。

## 严格归档

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . validate
python3 <execution-plan-dir>/scripts/epctl.py --repo . archive-ep EP-001 \
  --outcome completed \
  --verified-revision "git:<verified-commit>" \
  --evidence "ci:<pipeline-or-job-url>"
```

未完成验收、非终态 Task、open blocker、未填写复盘或缺少 revision/evidence
都会阻止 v2.3+ completed。明确停止时可以：

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . archive-ep EP-001 \
  --outcome cancelled --reason "产品方向已改变"
```

## 修复派生索引

```bash
python3 <execution-plan-dir>/scripts/epctl.py --repo . validate --fix-index
```

该操作重建 `RESEARCH.md`、`DECISIONS.md`、`PLANS.md` 和 `BUGFIXES.md`
托管区，不修改事实制品或托管区外人工内容。
