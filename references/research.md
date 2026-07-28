# Research 与 Synthesis

## 目标

Research 把决策相关的未知转化为可追溯证据。每个包围绕一个功能或决策域，保持一个有界控制文档，并把详细分析和原始输出下沉。

```text
docs/research/active/r-NNN_slug/
├── RESEARCH.md
├── SYNTHESIS.md
├── notes/
└── artifacts/
```

- `RESEARCH.md`：当前问题、路线、状态、发现索引和下一步。
- `notes/`：单一主题、来源或实验的聚焦分析。
- `artifacts/`：完整日志、benchmark、trace、抓包和生成数据。
- `SYNTHESIS.md`：供 ADR 与 ExecPlan 使用的决策级结论。

## 何时创建

复杂功能默认先创建 Research，尤其是：

- 关键行为、约束或现状不清楚。
- 需要比较多个库、协议、架构或迁移方案。
- 需要 prototype、spike、benchmark 或真实系统观察。
- 决策涉及公共契约、安全、可靠性、数据或高逆转成本。

已存在 accepted ADR、权威标准或用户已经给出固定方案时，可以跳过正式 Research。创建 ExecPlan 时必须写明 `research-not-required` 理由。

## 研究问题

每个问题使用 `RQ-NNN`，状态只能是：

- `open`：仍需证据。
- `answered`：已有支持结论和证据。
- `deferred`：不影响当前决策，并已说明转移位置或条件。
- `invalidated`：前提不成立或问题不再相关，并有依据。

结论前不得只靠材料数量判断完成。Research Gate 要求：

1. 没有 `open` 问题。
2. 没有 open blocker。
3. 关键结论具有仓库路径、权威来源或可复现实验。
4. 冲突证据、置信度和局限已明确。
5. 方案可以依据 Decision Drivers 排序。
6. 剩余未知不会改变当前排序，或已转化为 ADR 条件、EP 验收或 blocker。
7. `SYNTHESIS.md` 已完整填写。

## 实验记录

每个实验至少记录：

- Hypothesis：什么观察会支持或反驳主张。
- Method：工作目录、命令、输入和环境。
- Observation：实际结果，避免把推断写成事实。
- Interpretation：结果如何影响选项或下一步。
- Evidence：完整输出路径。
- Promotion or discard：prototype 保留、演进或删除的判定。

网络来源使用稳定链接，并在 Research 中复述决策所需事实。代码行为优先使用源代码、测试和可复现实验。

## Synthesis

Synthesis 负责压缩信息，不复制全部 Research。它必须包含：

- 对研究目的的直接回答。
- 支持结论、置信度与证据。
- 被否定的假设。
- 剩余未知及其处理位置。
- 候选方案和 Decision Drivers。
- 推荐方案、成立条件和风险。
- 需要进入 ADR 与 ExecPlan 的约束。

执行 `archive-research R-NNN --outcome concluded` 后，Synthesis 正文被 SHA-256 封存，Research 包移动到 completed。后续新证据创建新的 Research；如果它改变 accepted ADR，则通过 superseding ADR 处理。

取消 Research 必须记录原因。取消制品可以保留已获得证据，但不能满足 ExecPlan 的 Research Gate。

## 有界性

- 根 `RESEARCH.md` 优先服务当前研究接手。
- 单一主题分析进入 `notes/`。
- 完整输出进入 `artifacts/`。
- `SYNTHESIS.md` 只保留决策所需结论。
- Research 不使用 EP Checkpoint；结论封存后整体归档。
