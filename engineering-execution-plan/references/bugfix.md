# Bugfix 规范

## 适用边界

Bugfix 是用户明确要求保存的局部缺陷记录。普通修复请求不自动创建记录。

出现以下任一信号时升级为 ExecPlan：

- 公共接口、协议、schema 或兼容约定变化。
- 多模块联动。
- 需要 Task、prototype 或架构决策。
- 缺失能力的建设超过局部修复范围。

## 必需字段

使用 `assets/bugfix.md`：

- `id`：BF-NNN。
- `status`：open / in_progress / blocked / fixed / escalated / cancelled。
- `severity`：用户未提供时保留 `unspecified`，不要凭“用户可见”自行判定 High。
- `area`：模块或子系统。
- `linked_ep`：升级时必填。
- `created` / `updated`：ISO 日期。

正文必须包含：

- Symptom：实际异常。
- Scope：影响范围。
- Reproduction：复现输入、环境与观察。
- Root Cause：未定位时写 `待定位`。
- Fix：未明确时写 `待补`。
- Verification：命令、预期结果和证据。
- Blockers：带 open/resolved 生命周期。
- Notes：追加式处理记录。
- Outcome：归档结论。

## 进展与阻塞

更新 Root Cause、Fix、Verification 等当前事实时同步更新 `updated`。

Notes 使用 UTC 时间戳：

```markdown
### 2026-07-27T12:30:00Z
- 已复现：...
- 已定位：...
- 下一步：...
```

Blocker 表：

```markdown
| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|
```

解除阻塞时把同一行改为 `resolved`，若该阻塞已不再适用则改为 `dismissed`，并补充解决信息、在 Notes 追加事件。阻塞历史不等于当前阻塞。

## 升级与归档

升级：

1. 创建 ExecPlan。
2. 在 Bugfix 填写 `linked_ep`。
3. 状态改为 `escalated`，Outcome 说明升级原因。
4. 归档 Bugfix；复杂推进只写入 ExecPlan。

归档门槛：

- fixed：Verification 全部完成，Outcome 有结果。
- escalated：linked_ep 指向存在的 EP，Outcome 有升级原因。
- cancelled：Outcome 有取消原因。

不要让 escalated Bugfix 长期滞留 active。

使用单次终态命令更新状态、移动文件并重建索引：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . archive-bugfix BF-007 \
  --outcome fixed

python3 <skill-dir>/scripts/epctl.py --repo . archive-bugfix BF-008 \
  --outcome escalated --linked-ep EP-023 \
  --reason "公共 token 契约需要跨模块设计"
```

`fixed` 时必须先填完 Verification 和 Outcome；也可用 `--reason` 写入 Outcome。`escalated` 不要求完成原验证，但 Symptom、Scope、Reproduction、升级原因和有效 `linked_ep` 必须存在。
