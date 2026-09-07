---
name: repo-foundry-ai
description: 初始化、升级或诊断 RepoFoundry 仓库 Harness，配置 Agent adapter 与 Engineering Specs。普通编码、代码解释和文档写作直接使用项目约定或对应专业 skill。
---

# RepoFoundry AI

管理仓库共享的工程入口、adapter 与规范安装。专业制品由各自的 skill 持有。

## 先确定任务范围

如果目标仓库存在 `.repo-foundry/skills/repo-foundry-ai/SKILL.md`，读取并遵循
该项目版本的工作流。个人入口负责发现，仓库文件持有当前项目契约。
没有 Harness 时，普通实现、解释和局部文档修改沿用仓库约定；仅在用户要求初始化时
执行 bootstrap。不要为了使用专业 skill 自动安装 Harness。

读取已有 Harness 的 `governance.profile`：adaptive 从 Explore 开始，缺失字段的
旧仓库保持 strict / Governed。按风险升级，不能用低模式绕过已有边界：

- Explore：有界可逆的阅读、实验、本地编辑与测试，使用任务相关文件和检查。
- Build：有界生产修改，明确 intent、path、acceptance、compatibility，并激活适用 Spec。
- Governed：公共契约、安全、数据、不可逆操作、可靠性声明、发布或长期决定，按实际
  触发器使用专业制品。复杂度本身不要求创建一整套文档。

## 按操作读取说明

把 `<repo-foundry-ai-dir>` 解析为本 skill 所在目录。CLI 为
`python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo <repo>`；用 `--help` 查询具体参数。
只读取当前操作需要的说明：

| 任务 | 说明 |
|---|---|
| 安装或更新用户级 CLI、注册宿主发现入口 | [installation.md](references/installation.md) |
| 初始化 Harness、选择或追加 adapter | [bootstrap.md](references/bootstrap.md) |
| 升级既有 Harness、处理 seed 与历史兼容 | [upgrades.md](references/upgrades.md) |
| 安装、同步或更新 Engineering Specs | [specifications.md](references/specifications.md) |
| 检查 Harness 或 Spec 完整性 | `validate --harness` 或 `spec validate`；按诊断读取对应说明 |
| 展示专业 skill 的端到端用法 | [Prompt 示例](examples/README.zh-CN.md) |

初始化或升级先预览，检查 create、preserve、register 和 conflict。用户已要求实施且
没有 conflict 时继续 `--apply` 和验证，不重复索取同一授权。已有定制内容必须保留；
有冲突时先准备可审阅的合并方案。升级发行包与迁移项目 Harness 是两个独立操作。

Spec 可选集合由用户选择。预览出现 `selection_decision.status=required` 且当前会话
尚无明确选择时，展示 candidate 的 ID、描述和依赖，再询问完整 `--spec` 集合、
`--required-only` 或 `--keep-selection`。不能从沉默推断选择。

## 路由专业工作

| 用户需要的结果 | Skill |
|---|---|
| 普通 Architecture、Internals、模块设计或实现合同的撰写与评审 | `detailed-design` |
| 预声明 Scenario、执行并封存可复用测量 | `engineering-benchmark` |
| 为决策未知维护 Research、专题证据与 Synthesis | `engineering-research` |
| 创建、评审或修订受治理的 DD-NNN / Design Package | `engineering-design` |
| ADR、ExecPlan、Task、Checkpoint、Bugfix 或 ADR 历史维护 | `engineering-execution-plan` |
| 用户明确要求的工程分享文章 | `engineering-case-study` |

一次请求可按证据流组合这些 skill。先完成已授权的取证、实现、验证与修正；需要
Owner 决定时，提供具体的待批准结果。专业 skill 可以独立安装，跨 skill 依赖版本化
文件契约，不依赖安装路径。ADR lifecycle/storage 变化后及适用的 Governed 交接前，
由 Execution Plan 工作流运行 `adr-maintenance`；其建议不构成修改 ADR 的授权。

## 核心边界

- 不编造项目命令、Owner、架构、SLO、安全控制或验证结果；未知项目事实保留为
  `BOOTSTRAP_TODO`。不自动接受 ADR、批准 Design 或封存 Research。
- 使用确定性 CLI 维护锁、ID、摘要、迁移和制品生命周期；不改写 locked/sealed 历史。
- 规范安装与任务激活分开。项目只用一个共享 Router；Build/Governed 选择精确
  Requirement 并保留已验证原文，恢复上下文时运行 `rehydrate`。
- Core 保持产品中立；adapter 持有宿主发现、事件与信任配置。Hook 生效需要仓库
  信任和精确命令审查；未启用 Hook 时依赖显式 CLI 检查，不声称机械强制。
- RepoFoundry 的有效 Spec enforcement 上限是 Advisory，不声称 finding lifecycle。
- 对受影响行为执行适当验证并报告结果。Explore 使用普通说明；Build/Governed 的
  receipt 与交接由项目 Router 约定，不能用格式化汇报代替实际检查。
