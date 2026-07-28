# 使用示例

## 初始化

```bash
python3 <skill-dir>/scripts/epctl.py --repo . init
```

只补缺失目录、`docs/PLANS.md`、`docs/BUGFIXES.md` 和技术债务登记册。

## 创建复杂 ExecPlan

用户：“统一网关、BFF、SDK 的 token 刷新契约，并兼容旧字段。”

```bash
python3 <skill-dir>/scripts/epctl.py --repo . new-ep \
  --slug unify-token-refresh \
  --title "Unify token refresh contract"
```

随后研究仓库并填写 `EXECPLAN.md`。至少写一个独立可验证里程碑、明确契约变化、兼容路径、回滚方法和端到端验证。

## 普通修复不自动建记录

用户：“修复 cursor 等于 page_size 时不生成 next cursor 的问题。”

直接复现、修复和验证。用户没有要求保存 bugfix 记录，因此不创建 `docs/bugfixes/`。

## 明确记录 Bugfix

用户：“先帮我记个 bugfix，不要建 EP。”

```bash
python3 <skill-dir>/scripts/epctl.py --repo . new-bugfix \
  --slug cursor-boundary \
  --title "Fix cursor generation at page-size boundary" \
  --area spans-api
```

填写 Reproduction 和 Verification；根因未知时保留 `待定位`。

## 拆 Task

```bash
python3 <skill-dir>/scripts/epctl.py --repo . new-task EP-001 \
  --slug add-gateway-contract \
  --title "Add gateway refresh contract"
```

Task 使用稳定父 ID。把里程碑和总体进度继续维护在根 `EXECPLAN.md`。

## 处理技术未知

发现第三方库行为不明确时：

1. 建立可丢弃的 prototype/spike。
2. 运行最小验证。
3. 在 Surprises & Discoveries 记录观察与证据。
4. 更新 Plan of Work 和 Decision Log。

只有缺权限、外部输入、人类判断或高风险不可逆操作时建立 open blocker。

## 压缩增长中的 ExecPlan

Milestone 1 已完成，根文档积累了大量进度、发现和已解决 blocker。先把完整测试输出保存到 `artifacts/milestone-1-validation.txt`，再预览 checkpoint：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . checkpoint EP-001 \
  --slug milestone-one \
  --title "Milestone 1 complete" \
  --current-milestone "Milestone 2: adapter integration" \
  --summary "契约层已完成；适配层尚未实现。" \
  --next-action "编辑 src/adapter.ts 并运行 npm test。" \
  --dry-run
```

检查预览中的归档数量与路径后，去掉 `--dry-run`。脚本保留所有 `[ ]` Progress 和 open blocker，把旧事件原文写入 sealed checkpoint，并刷新根 Current Snapshot。

不要为了缩短文档删除历史、验收或开放问题。checkpoint 后应让一个无历史会话的 Agent 只读根 `EXECPLAN.md`，确认可以直接执行下一动作。

## 严格归档

```bash
python3 <skill-dir>/scripts/epctl.py --repo . validate
python3 <skill-dir>/scripts/epctl.py --repo . archive-ep EP-001 \
  --outcome completed
```

脚本拒绝归档以下计划：

- 验收仍有未勾选项。
- Task 仍为 todo/in_progress/blocked。
- 存在 open blocker。
- Outcomes & Retrospective 仍有必填占位符。

不完整工作保留 active/blocked，或明确取消：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . archive-ep EP-001 \
  --outcome cancelled --reason "产品方向已改变"
```

## 修复派生索引

如果制品存在但索引缺行，或索引仍指向已移动路径：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . validate --fix-index
```

该操作只重建 `PLANS.md` / `BUGFIXES.md` 的托管区，不改 ExecPlan、Bugfix 或托管区外的人工内容。
