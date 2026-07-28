---
name: engineering-research
description: |
  创建、接管和维护仓库内的工程 Research 与 Synthesis，包括研究问题、源码/文档/网络来源、实验与 prototype、多文档 corpus、入口索引、manifest、引用完整性、linked corpus 快照和结论封存。适用于用户要求先调研一个功能或技术方案、比较选项、分析现有多篇研究文档、处理 BMAD/Deep Research 产物、生成决策级总结，或提到 Research、技术调研、证据、Synthesis、research corpus、research manifest。普通代码解释、方向已固定的局部实现或纯 ExecPlan 维护不触发本 skill。
---

# Engineering Research

把决策相关未知转化为可审计的多文档证据包，并输出一个有界、可供
ADR 或实施计划消费的 sealed Synthesis。

```mermaid
flowchart LR
    Q["Research Questions"] --> C["多文档 Corpus<br/>来源、专题、实验"]
    C --> M["Manifest<br/>成员、入口、引用、摘要"]
    M --> S["Synthesis<br/>决策级结论"]
    S --> D["ADR / ExecPlan / 其他消费者"]
```

Research 是“身份与生命周期 + 文档集合 + Synthesis”，不是某个固定文件名。
控制包中的 `RESEARCH.md` 只维护目的、问题、当前路线、发现索引和下一步。

## 判断边界

以下情况使用一个 Research ID 和多篇文档：

- 文档服务于同一个决策目的；
- Research Questions 需要一起排序选项；
- 文档共享结论时间和下游 Synthesis；
- `index.md`、专题分析、能力矩阵、实验报告只是同一证据图的不同入口。

以下情况拆成多个 Research ID：

- 决策目的、Owner、结束时间或下游消费者独立；
- 一个主题可以 concluded，另一个仍需长期等待；
- 一个结论可以被多个无关 ADR 或计划单独复用。

执行 Research 前读取 `references/research.md`。注册 existing corpus、修改
manifest 或处理归档完整性前再读取 `references/manifest.md`。

## 仓库制品

```text
docs/research/
├── active/r-NNN_slug/
│   ├── RESEARCH.md
│   ├── RESEARCH_MANIFEST.json
│   ├── SYNTHESIS.md
│   ├── notes/
│   └── artifacts/
└── completed/
```

- **managed corpus**：研究文档位于控制包内，通常写入 `notes/`。
- **linked corpus**：研究文档已存在于仓库其他位置；active 阶段只登记，不移动。
- linked Research concluded 时，把声明的文档复制到
  `artifacts/research-snapshot/`，再封存 manifest 和 Synthesis。
- 原始二进制、日志、trace、benchmark 数据仍走 `artifacts/`，不会因文档
  manifest 自动复制。

## 优先使用 researchctl

把 `<skill-dir>` 解析为本 skill 所在目录。命令都在目标代码仓库根目录运行：

```bash
python3 <skill-dir>/scripts/researchctl.py --repo . init

python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug cache-topology --title "Research cache topology"

python3 <skill-dir>/scripts/researchctl.py --repo . new-research \
  --slug spans-aggregate --title "Research spans aggregate" \
  --corpus-root _bmad-output/planning-artifacts/research/spans-aggregate \
  --entrypoint _bmad-output/planning-artifacts/research/spans-aggregate/index.md

python3 <skill-dir>/scripts/researchctl.py --repo . sync-research R-001
python3 <skill-dir>/scripts/researchctl.py --repo . validate
python3 <skill-dir>/scripts/researchctl.py --repo . status
python3 <skill-dir>/scripts/researchctl.py --repo . archive-research R-001 \
  --outcome concluded
```

`new-research` 可以重复提供 `--corpus-root`、`--entrypoint` 和 `--include`。
绝对输入路径只有在解析后仍位于目标仓库内才接受；manifest 永远保存仓库相对路径。

## 工作流程

1. 先检查仓库代码、测试、已有文档和权威外部来源。
2. 创建 Research，写清 Purpose、Scope、Decision Drivers 和所有 `RQ-NNN`。
3. managed 研究把专题分析写到 `notes/`；existing corpus 用 linked 模式登记。
4. 每个关键主张保留可定位来源或可复现实验。区分 Observation 与
   Interpretation。
5. 每次新增、删除、移动研究文档后运行 `sync-research`。
6. 修复 manifest drift、缺失本地引用和不可解释的冲突；绝对来源路径至少记录
   可移植替代或 provenance。
7. 在 `SYNTHESIS.md` 直接回答研究目的，比较选项，保留负面证据、置信边界、
   剩余未知、推荐条件和下游约束。
8. 确认没有 open Research Question、open blocker 或 REQUIRED 标记，再 concluded。

Research 取消时必须写明原因。Cancelled Research 保留已获得的证据，但不能满足
下游 Research Gate。

## 有界性与变更

- 根控制页只服务当前接手，不复制全部专题内容。
- Synthesis 只保存决策所需结论，不成为第二份全文。
- concluded 的 snapshot、manifest 和 Synthesis 不可编辑；新证据创建新
  Research。
- 如果新证据改变已接受架构方向，由下游治理工具创建 superseding ADR。
- 外部 Deep Research、BMAD 或人工文档都是 corpus 输入，不改变文件契约。

## 下游契约

本 skill 不接受 ADR，也不创建 ExecPlan。它只输出：

- concluded Research 控制记录；
- sealed `RESEARCH_MANIFEST.json`；
- sealed `SYNTHESIS.md`；
- 可选的 snapshot、notes 和 artifacts。

消费者必须依赖该文件契约，而不是本 skill 的安装路径。完整字段、摘要算法、
引用诊断和兼容规则见 `references/manifest.md`；典型场景见
`references/examples.md`。
