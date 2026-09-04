---
name: detailed-design
description: |
  协作撰写、重构和评审面向工程师的架构与详细设计文档：从仓库证据建立 mental model，以真实请求、数据或状态生命周期组织叙事，解释核心抽象、边界、不变量、扩展点和源码映射。适用于 Architecture、Internals、模块设计、实现合同和技术文档评审。普通 API 文档、用户手册、ADR 授权、Research、实施计划，以及 DD-NNN/manifest/revision 治理不使用本 skill。
---

# Detailed Design

把代码、既有设计和工程约束整理成工程师能够阅读、实现和维护的技术文档。
默认产物是一份聚焦的 Markdown 文档；不因主题复杂、章节较多或评审项较多自动创建
目录、文档包、manifest、ID 或生命周期状态。

## 与 Engineering Design 的边界

- `detailed-design` 负责文档内容：mental model、流程、抽象、边界、不变量、源码映射和技术评审。
- `engineering-design` 负责受治理的 Design 制品：`DD-NNN`、manifest、revision、approval 和 snapshot。
- 普通“写架构设计文档”“解释系统内部原理”“优化这篇技术文档”使用本 skill。
- 用户明确要求 Design Package、`DD-NNN`、批准或修订受治理 Design 时，切换到
  `engineering-design`。不要为了显得正式而主动升级。

本 skill 不直接修改受 `engineering-design` 管理的 Design Package；可以生成独立草稿或
评审意见，再由 owning workflow 纳入。

## 选择工作模式

| 目标 | 模式 | 主要回答 |
|---|---|---|
| 建立系统级理解 | `architecture` | 系统为什么这样工作，主流程、核心抽象和边界是什么 |
| 深入一个模块或子系统 | `module` | 职责、状态、算法、并发、失败和资源如何组织 |
| 固化实现级约束 | `contract` | 类型、所有权、不变量、兼容性和验证门禁是什么 |
| 评审已有设计 | `review` | 哪些事实缺 owner、边界矛盾、声明不可验证或已经漂移 |

没有更具体信号时，架构文档请求默认使用 `architecture`。编译器、存储、调度器等复杂
模块可以组合 `module + contract`，但仍优先形成一条清晰叙事，而不是拼接两套模板。

## 工作原则

### 先建立读者的 mental model

优先选择一条能解释系统的叙事主线：请求生命周期、数据流、控制流、状态转换或关键
资源生命周期。不要从仓库目录或类清单开始。代码地图放在概念和流程之后，用来帮助
读者继续探索实现。

### 证据与设计状态分开

读取可用的 ADR/RFC/Spec、当前实现、测试与历史，再写实现事实。明确区分：

- observed：代码或文档直接支持的现状；
- decided：已经授权的设计约束；
- proposed：本文建议但尚未成为现状的方案；
- derived：由其他约束推导出的影响；
- open：尚未解决且会影响设计的问题。

冲突必须显式呈现，不得把 proposal 写成 current behavior。

### 最小充分结构

只保留帮助目标读者理解或实现系统的章节。模板是候选项，不是清单。

- 默认一个文档。
- 不为 architecture、interface、data、operations、migration、verification 分别建文件。
- 只有某个专题具有独立读者、独立维护入口或必须按需加载的大体量内容时才拆文档。
- 确实需要多文档时，使用 Technical Architecture Docs 阅读路径：根 `README.md` 总览，
  按需增加 `how-it-works/`、`core-concepts/`、`subsystems/`、`extension-points/`、
  `deep-dives/`、`contributor-guide/`；目录不是必填清单。
- 一个规范事实只有一个 owner；其他位置链接它，不复制另一份表述。
- 示例用于验证模型，不能反过来成为规范来源。

### 架构文档不是 Codebase Map

架构文档先解释目标、系统形态、端到端流程、核心抽象、责任边界和扩展方式，再连接到
具体 package/type/file。文件树只能作为最后的导航，不能充当系统模型。

## 协作流程

1. 确定读者、使用场景、范围，以及文档描述现状还是目标设计。信息足够时直接推断并
   标明假设，不机械提问。
2. 阅读与结论有关的权威文档、接口、实现和测试，建立证据表与术语表。
3. 选择一条叙事主线，先画出 mental model、关键边界和一到三条代表性流程。
4. 识别核心抽象及其责任、输入输出、所有权和不变量；只在需要约束实现时深入类型或 API。
5. 按模式写作或评审。架构模式先读 [architecture.md](references/architecture.md)，需要
   起草新文档时可从 [architecture template](templates/architecture.md) 选择性取用章节；
   module/contract 模式读 [module-contract.md](references/module-contract.md)；评审模式读
   [review.md](references/review.md)。
6. 检查读者能否回答：请求或数据如何穿过系统、每个阶段拥有什么、失败在哪里收敛、
   如何扩展、到哪里继续读代码。
7. 输出用户要求的 Markdown、文件修改或 findings。未决问题保持未决，不替用户授权决策。

## 写作约束

- 用 Mermaid 表达确实重要的流程、状态、依赖或所有权关系；简单关系用文字。
- 用表格承载重复字段的 inventory、ownership、compatibility 或 verification 映射。
- 代码片段只展示关键接口、数据结构或伪代码，不转录实现。
- 不虚构 SLA、限制、性能数字、owner、兼容承诺或未来路线。
- 当前状态、目标状态和迁移中间态必须能被读者区分。
- 没有内容的章节直接省略，不输出空标题或泛化的 `Not applicable`。

## 完成标准

一份文档完成时，目标读者应当能够建立系统模型、跟随至少一条真实流程、找到核心抽象
及其边界、理解关键失败和演进约束，并从概念跳转到实现证据。无法由证据确认的内容必须
保留为 proposal 或 open question。
