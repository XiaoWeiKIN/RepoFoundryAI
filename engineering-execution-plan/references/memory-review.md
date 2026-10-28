# 工程记忆复核（P0）

Memory Review 读取 EP、ADR、已安装 Spec / Requirement 和显式提供的证据记录，输出需要复核的候选。它不取消计划、不改变 ADR 效力、不更新 Spec lock，也不生成新的必填治理制品。

本版提供同包的独立只读入口 [memory_review.py](../scripts/memory_review.py)，复用 `epctl` 的解析、效力和验证函数。它不修改 `epctl.py` 的生命周期命令，也不依赖 Session Context 或自动 Checkpoint PR 已经合并。此前提议的 `epctl memory-review` 不是本版 CLI；使用下面的实际命令。

## 运行

在安装包中执行，将 `<skill-dir>` 替换为 `engineering-execution-plan` 的目录，将 `<repo>` 替换为目标仓库。目标中的工程制品需要通过现有完整性检查；本命令不会自动执行 `init` 或修复损坏的索引。

```bash
python3 -B <skill-dir>/scripts/memory_review.py --repo <repo> \
  --as-of 2026-10-28T00:00:00Z --json
```

`--as-of` 必填，必须是带时区的 ISO 时间。等价时区会归一到 UTC。同一源快照、策略和评估时刻产生同一排序和报告摘要。命令不读取系统当前时间作为隐含的评估参数。

去掉 `--json` 可得到逐对象摘要。JSON schema version 为 `1`，包括来源摘要、策略版本、评估结果、reason codes、证据引用、消费者、覆盖范围和下一步建议。

退出码 `0` 表示评估完成，不表示所有对象有效，也不表示代码验收通过。存在 `review_due` 不自动阻断普通开发。损坏来源、digest 漂移、不支持的输入或评估期间源发生变化时退出 `2`；JSON 输出明确为 `input_integrity: incomplete`，`items` 为空，不输出部分成功报告。

## 评估与工程效力分开

| 评估结果 | 含义 |
|---|---|
| `retain_active` | 当前效力或明确的记录支持继续保留；不是新的批准 |
| `review_due` | 有可解释的复核触发条件；原生命周期状态不变 |
| `historical` | 来源已经是终态，保留历史 |
| `insufficient_evidence` | 缺少支持时间或使用判断的证据，不推断失效 |

一个 accepted/current ADR 可以同时具有 `assessment: review_due` 和 `current_effect: true`。前者是提醒，后者仍由现有 ADR resolver 决定。年龄、读取次数和引用数量不能撤销约束。

消费者来自当前 ADR 的显式依赖以及 active/blocked EP 的 ADR 引用。报告不声称已分析所有代码、测试、产品或外部消费者；没有查到声明不等于没有使用者。普通循环引用不能产生额外的有效性分数。当前效力解析、引用闭包和 seal 校验仍由现有验证器负责。

ADR 的 `amended_by` 可产生 `preview_adr_consolidation` 建议。这只是结构性候选，不证明语义重复或冲突；后续复用 `adr-consolidation-plan`，接受新决定、退役或替代旧决定仍需明确授权。

## 显式时间策略

缺省策略 `conservative-v1` 不启用按天数触发的复核。依赖已变更、下一动作未知和现有 ADR 效力异常仍会报告。30/90/180 天不是隐藏的自动失效规则。

团队需要时间策略时，提供一个仓库相对 JSON 路径：

```bash
python3 -B <skill-dir>/scripts/memory_review.py --repo <repo> \
  --as-of 2026-10-28T00:00:00Z \
  --policy docs/.engineering/memory-review-policy.json --json
```

策略示例（示例天数必须由项目选择，不由命令自动写入）：

```json
{
  "schema_version": 1,
  "id": "team-review-v1",
  "ep_idle_days": 30,
  "adr_review_days": 180,
  "spec_review_days": 90,
  "version_snapshot_days": 30
}
```

每个天数字段允许 `null`，表示关闭该项。非空值必须是 1–36500 的整数。达到边界时触发复核，不是自动取消或退役。报告记录策略内容和 SHA-256。未知字段、重复 JSON key、错误版本及无效阈值会报错。

## 时间证据不能从维护动作推导

本版不从文件 mtime、Markdown 任意日期、`updated`、`last_activity`、索引重建或 Checkpoint 时间推断可信进展。也不把读取或生成报告算作重新确认。Git 历史目前标记为 `not_collected`，因此无 Git、浅克隆和源码包不会被错误地判成长期无活动。

需要按时间评估时，通过可选的 `--observations <repository-relative-path>` 提供已有证据的声明。这是调用方输入，不是每个任务必须维护的第二套状态；调用方可以从已有验收或评审系统导出。命令不会生成或更新该文件。

```json
{
  "schema_version": 1,
  "observations": [
    {
      "kind": "exec-plan",
      "artifact_id": "EP-023",
      "event": "progress",
      "at": "2026-09-20T08:00:00Z",
      "recorded_by": "实际记录人或已有系统标识",
      "reason": "已完成里程碑的现有验证记录",
      "evidence": {
        "path": "docs/exec-plans/active/ep-023_example/artifacts/test-log.txt",
        "sha256": "替换为该文件真实的64位小写SHA-256",
        "revision": "git:<实际运行检查的提交>"
      }
    }
  ]
}
```

示例 ID、路径和摘要不是实际证据，使用前必须替换。`kind` 是 `exec-plan`、`adr`、`spec` 或 `requirement`；`artifact_id` 必须对应本次解析到的对象，Spec 使用其原始 ID（例如 `languages/go`）。

支持的事件：

| 事件 | 必需内容 | 作用 |
|---|---|---|
| `progress` | EP、时间、记录人、理由、digest-bound evidence | EP 最后记录的进展时间 |
| `review` | 时间、记录人、理由、digest-bound evidence | 最后显式复核时间 |
| `pause` / `retain` | 时间、记录人、理由、`next_review_at` | 在指定时间前推迟时间类复核，不改变原状态 |
| `spec_version` | Spec/Requirement、时间、digest-bound evidence、`available_version`、`disposition` | 外部版本审查候选 |

`disposition` 为 `published`、`withdrawn` 或 `superseded`，表示所提供版本快照的声明。版本不同只触发检查，不假设它一定更新或已适用于当前仓库；过了 `version_snapshot_days` 的快照标为陈旧。没有快照时外部版本为 unknown，不访问网络。

Evidence 必须指向仓库内的普通文件，包含 SHA-256 和非空 revision。命令验证字节一致性，**不证明记录人具有决定权，也不证明声明本身为真**。历史 revision 的检查不能代表当前 HEAD 通过，所有报告都明确 `current_code_verified: false`。

未来的 observation 不参与进展计时，报告 `FUTURE_OBSERVATION_IGNORED`。同一对象、事件和时刻的重复声明被拒绝。暂停/保留必须有晚于记录时间的 `next_review_at`；到期后报告复核，期间也不能压制依赖变更、原始输入损坏或其他硬边界。

## 只读与覆盖范围

评估前后比较 `docs/`、`benchmarks/` 和显式输入的文件集合与摘要，拒绝符号链接、越界路径和特殊文件。限制为 20,000 个文件、总计 512 MiB，JSON 输入限制为 2 MiB。输入不适合该范围时明确失败，不截断成成功结果。

这是一致性复核，不是文件系统快照锁或对恶意并发修改者的安全隔离。评估期间保持源稳定；需要强隔离时在调用方准备只读快照。本命令本身不创建 lock、cache、索引或 `__pycache__`，不调用网络或 Git，也不执行目标仓库提供的脚本。

EP/ADR 由本包的 `epctl` 验证。Spec 使用发行包中的共享 Router，检查锁定字节和 Requirement source ranges。独立安装本 Skill 但没有发行包 Spec validator 时，含 Spec 输入的评估明确报告 `VALIDATOR_UNAVAILABLE`，不把未验证的 lock 当作已验证。

## 后续动作与非目标

P0 仅报告；不会自动启动 #88 的上下文降温，也不会调用 #89 的自动压缩。继续使用原有 `checkpoint`、`adr-consolidation-plan`、`transition-adr`、`supersede-adr`、`archive-ep` 或 History Pack 契约处理审阅后的动作。

不实现语义过时分类器、自动遗忘、自动退役、后台调度、Issue 状态同步或新数据库。普通任务不需要运行 Memory Review。后续接入检索层时，冷历史仍可追溯，当前任务适用的强制 ADR / Requirement 不得因降温被省略。
