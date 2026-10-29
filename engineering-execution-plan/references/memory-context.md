# 任务相关的工程记忆检索（P1-A）

P1-A 提供只读 Shadow Preview：按明确任务范围读取 EP Snapshot、当前 ADR 导航、
历史入口和路径匹配的 Spec 候选，并对照现有 Session Context Budget 计算降温建议。
**实际 effective context 始终等于 baseline。** 本版不修改默认 SessionStart Hook，
不执行降温、归档、取消、退役或自动 Checkpoint，也不为普通任务增加必填制品。

## 运行范围

使用完整 RepoHarnessKit 发行包中的 `engineering-execution-plan`。此命令按需运行，
不是每次 Agent 启动都执行的全量 Memory Review。它导入发行包的 Core budgeter 和
EP/ADR resolver，不执行目标仓库里的 Python 脚本。独立安装 Skill 而缺少发行包
Core 时明确报错 `VALIDATOR_UNAVAILABLE`，不能声称取得了已验证的上下文。

将 `<skill-dir>` 替换为本 Skill 目录，`<repo>` 替换为目标仓库；ID、View、路径和
时间必须对应实际任务。以下 ID 仅为示例：

```bash
python3 -B <skill-dir>/scripts/memory_context.py --repo <repo> \
  --as-of 2026-10-29T00:00:00Z --ep EP-023 --json

# 同时指定当前 ADR、已存在的领域 View 或具体计划修改路径
python3 -B <skill-dir>/scripts/memory_context.py --repo <repo> \
  --as-of 2026-10-29T00:00:00Z --adr ADR-012 --view cache \
  --path src/cache/redis.py --json

# 明确请求历史：仍标注非当前，不恢复其效力
python3 -B <skill-dir>/scripts/memory_context.py --repo <repo> \
  --as-of 2026-10-29T00:00:00Z --adr ADR-007 --history --json
```

`--ep`、`--adr`、`--view`、`--path` 可重复；总计最多 32 个选择器。不猜测多个 EP
中哪个“当前”，不从标题相似度推断 ADR 适用性。无选择器时上下文为空，不因仓库
里存在历史而全部加载。路径必须具体、位于仓库内，不支持宽泛 glob 或路径越界。

`--background-ep EP-NNN` 仅用于比较调用方已经持有的可选旧上下文。它不自动扫描
旧计划，也不会把该 EP 的 ADR 依赖扩展成当前任务要求。同一 ID 同时由 `--ep`
指定时，显式任务引用优先。可用以下命令比较，但有效输出仍不改变：

```bash
python3 -B <skill-dir>/scripts/memory_context.py --repo <repo> \
  --as-of 2026-10-29T00:00:00Z --ep EP-023 \
  --background-ep EP-006 --json
```

## 选择契约

| 类别 | 依据 | Shadow 建议 |
|---|---|---|
| `required` | 调用方原本的 mandatory section | 原文保留，不允许降温 |
| `direct` | 显式 EP/ADR 查询 | 优先保留；历史查询标明非当前 |
| `related` | 当前 EP、View 的 ADR closure 或 Spec 路径声明 | 保留导航，不宣称已激活规范 |
| `background` | 调用方显式声明的可选背景 | 比较将正文替换为来源指针的效果 |
| `unknown` | 无法确定相关性 | 保留原行为，不把未知解释为无关 |

`review_due` 只是复核提醒，不能覆盖 `current_effect`；`insufficient_evidence`
不是“长期闲置”。本版没有访问次数加权、隐含年龄淘汰、LLM 语义判断或热度分数。

当前 ADR 的传递依赖及 scoped amendments 仍由 `epctl.resolve_decision_context`
解析，输出 `resolved_constraint_refs` 供比较。这里仅展示导航，不复制或裁剪规范性
约束。真正的 Requirement Capsule、Decision Capsule、预算失败语义和 mutation gate
保持原路径。Spec `applies_to` 的路径命中只是候选，后续仍须选择适用 Requirements。

当前实现没有可靠的代码路径到 ADR 映射；`coverage.code_to_adr` 明确为 `unknown`。
历史 Pack 通过已有 logical resolver 定位，不能把不存在的原文件链接冒充可读来源。

## 可选的 P0 报告

可以传入调用方已经生成的 `memory-review` JSON，不自动重新运行 P0：

```bash
python3 -B <skill-dir>/scripts/memory_context.py --repo <repo> \
  --as-of 2026-10-29T00:00:00Z --ep EP-023 \
  --review-report reports/memory-review.json --max-report-age-seconds 86400 --json
```

报告版本、自身摘要、评估时间以及所选对象的当前来源字节必须匹配。默认报告新鲜度
窗口为 86,400 秒，调用方可显式修改；它是**优化提示的新鲜度**，不是 EP/ADR 的
失效时间。超时、来自未来、损坏、缺失、版本不支持或来源变化的提示被忽略。

提示只增加标准化评估标签，不建立候选身份、依赖关系、授权或当前效力。来源摘要
匹配不证明报告真实；声明的代码/测试消费者未在检索层重新证明。输出将这一边界标为
`SOURCE_SCOPED_ANNOTATIONS_ONLY` 和 `authority_verified: false`。

可选报告不可用不会阻塞有效的显式查询。反之，真正的 EP/ADR seal、Spec lock 或
当前依赖闭包校验失败，仍退出 `2`，不允许用“忽略提示”绕过源数据错误。

## 输出与保证

JSON schema 为 `1`，包含 `baseline`、`proposal`、`effective_context`、逐对象
`selection`、原因码、来源摘要、coverage、报告摘要及真实 UTF-8 字节数差值。
`scope: supplemental_artifact_context_only` 表示这些数字只覆盖本次补充查询，
**不是整个 Agent context window，也不是完整 SessionStart token 预算**。

默认预算 8 KiB，可用 `--budget-bytes` 调整。复用现有 budgeter，正文放不下时保留
来源指针；mandatory 内容放不下则明确失败。不能为了展示节省而截断规范原文。
`byte_delta` 可以为零或正数；本版不承诺每个任务都减少上下文。

比较期间不更新源制品、EP/ADR 状态、Spec lock、Runtime、使用次数或复核时间。
退出码 `0` 仅表示预览完成，既不是验收通过，也不是生命周期变更授权。源不合法或
读取期间发生变化时退出 `2`，不输出部分成功 selection。检查为尽力的一致性复核，
不是恶意并发场景的文件系统隔离；需要强隔离时使用调用方准备的只读快照。

## 后续 P1-B

完成真实任务 Shadow 对照后，再单独评审 opt-in cooling 和 Adapter 接入。本 PR
不自动安装新 Hook、不改变已安装仓库的默认行为。Agent-neutral 纯选择器位于
`assets/core/engineering-specs/memory_retrieval.py`，不依赖专业 Skill；本 Skill 的
显式 CLI 只是提供经过现有解析器验证的候选。不直接修改 Core 安装契约或版本号。
