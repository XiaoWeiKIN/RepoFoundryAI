---
schema_version: "1.2"
metadata_schema: "1"
artifact_type: research
id: R-002
title: "Assess RepoFoundry AI as an AI-native project scaffolding product"
status: active
maturity: exploratory
research_type: feasibility
synthesis: SYNTHESIS.md
manifest: RESEARCH_MANIFEST.json
created: 2026-08-02
updated: 2026-08-04
owner: "XiaoWeiKIN"
author: "Codex"
current_round: RR-001
synthesis_revision: "0"
approved_by: ""
approved_at: ""
approval_ref: ""
---

# Assess RepoFoundry AI as an AI-native project scaffolding product

This controller is the bounded entrypoint for a multi-document Research
package. Keep current questions, routes, findings, and next actions here. Put
focused analysis in the declared corpus, raw evidence in `artifacts/`, and the
current decision-ready view in `SYNTHESIS.md`. Decision readiness never grants
permission to conclude or archive the Research.

## Research Metadata

| Field | Value |
|---|---|
| Date | 2026-08-02 |
| Last Updated | 2026-08-04 |
| Research Type | Feasibility |
| Research Owner | XiaoWeiKIN |
| Author | Codex |
| Lifecycle | active |
| Maturity | exploratory |
| Current Round | RR-001 |
| Synthesis Revision | v0 |
| Approval | Pending |

## Purpose and Decision to Enable

评估 RepoFoundry AI 是否值得从当前的 Repository Harness 与工程治理工具包，
扩展为类似 Spring Initializr、但同时内置 Coding Agent 上下文、工程规范、质量门禁
和持续升级能力的 AI 原生项目脚手架产品。本 Research 需要支持后续产品定位、首条
Golden Path、MVP 范围和商业验证投入的决策，但不在本阶段接受架构 ADR 或授权全面
实施。

## Current Snapshot

- Current state: 市场与工程证据支持“有条件 Go”。问题真实、时机成立，现有仓库也
  已具备安全 Bootstrap、版本化 Spec、漂移验证和工程证据生命周期；但当前产品只
  生成 Harness 与文档控制面，尚未形成可运行项目生成、持续升级、公开 Benchmark
  或付费验证。
- Next inquiry: 选择一条技术栈 Golden Path，完成普通脚手架与 RepoFoundry 项目的
  对照 Benchmark；同时访谈 10–15 个目标团队，验证真实使用频率、预算归属和付费
  意愿。
- Open blockers: none.

## Research Rounds

Use one round for one bounded pass over the shared Research purpose. A round
may add or reopen Research Questions and may reference any number of corpus
documents.

| Round | Focus | Status | Author | Started | Evidence and outcome |
|---|---|---|---|---|---|
| RR-001 | Baseline investigation | active | Codex | 2026-08-02 | `rounds/rr-001_baseline.md` |

## Scope and Non-goals

范围包括需求强度、市场时机、竞争与替代方案、当前仓库资产、产品差异化、目标客户、
可能的商业模式、技术落地路线和 Go/No-Go 验证门槛。

本轮不包含完整市场规模预测、法律与商标尽调、具体价格定案、多技术栈模板实现、企业
控制平面设计或真实客户 Benchmark。它也不把 Research 建议视为已接受的产品或架构
决定。

## Research Questions

| ID | Status | Question | Answer or disposition | Evidence |
|---|---|---|---|---|
| RQ-001 | answered | AI 编程是否产生了足够真实且持续的工程质量问题？ | 是。AI 提高局部产出，但会放大既有工程系统的优缺点；开发者对准确性、复杂任务和返工仍有显著顾虑。 | `notes/commercial-and-delivery-feasibility.md` |
| RQ-002 | answered | 现有脚手架、Agent 指令和 Spec 工具是否已经完全覆盖该机会？ | 没有完全覆盖，但基础文件与一次性模板已经商品化；直接竞争正在快速增加。 | `notes/commercial-and-delivery-feasibility.md` |
| RQ-003 | answered | RepoFoundry AI 应以什么产品边界获得可辨识的差异化？ | 前门采用项目脚手架，核心做成可创建、接管、诊断和升级的 Benchmark-verified Golden Path 生命周期。 | `notes/commercial-and-delivery-feasibility.md` |
| RQ-004 | open | 哪类客户会为私有规范、跨仓库治理和持续升级实际付费？ | 初步 ICP 是已规模化采用 Coding Agent 的平台工程、架构和交付团队；仍需客户访谈、真实试点和付费承诺验证。 | `notes/commercial-and-delivery-feasibility.md` |
| RQ-005 | answered | 是否存在可控制风险的最小落地路径和停止条件？ | 有。先完成单一技术栈 Golden Path、三项核心命令、对照 Benchmark 和 3 个设计伙伴，再按量化门槛决定是否扩张。 | `notes/commercial-and-delivery-feasibility.md` |

Allowed statuses: `open`, `answered`, `deferred`, `invalidated`.

## Method and Sources

先检查仓库 README、设计文档、CLI、Spec 管理实现、测试规模和公开发行状态，再使用
一手或官方来源验证 AI 工程痛点与替代方案。市场需求优先采用 DORA、Stack Overflow、
OpenAI 和实践者原文；竞品能力优先采用 Spring、Backstage、GitHub、Tessl 与直接竞品
产品页。仓库观察和外部观察分别记录，商业推断不冒充已发生的客户验证。

主要仓库入口包括 `README.zh-CN.md`、`scripts/foundryctl.py`、
`scripts/spec_manager.py`、`engineering-benchmark/` 与 `tests/`。完整来源、主张与
反证条件登记在结构化 Topic 的 Evidence Index 中。

## Experiments and Prototypes

本轮尚未执行产品效果实验。下一阶段应使用 `engineering-benchmark` 建立普通脚手架与
RepoFoundry Golden Path 的稳定 Scenario，对比新仓库进入 Green CI 的时间、Agent
任务首次通过率、人工 Review 返工和质量门禁违规。没有这组证据，不应宣称产品能够
提高工程质量或降低总交付成本。

## Findings

- 问题与时机成立：AI 输出速度增长后，架构上下文、机械验证和持续治理成为新的瓶颈。
- 当前仓库已有可复用的技术内核，但仍是治理工具包，不是可售的项目生成产品。
- 一次性模板、Prompt 或 AGENTS.md 不足以形成护城河；可验证的 Golden Path、升级
  图谱、Benchmark 数据和跨仓库治理更可能产生持续价值。
- 商业化必须从一次性 `create` 延伸到 `adopt`、`doctor`、`upgrade` 和 Fleet 管理。
- 建议以单一技术栈和真实设计伙伴验证，而不是立即构建多语言平台。

## Contradictions and Uncertainty

AI 使用者普遍报告局部效率提升，但团队级协作、交付稳定性和客观生产率证据并不完全
一致；较早的生产率实验也已被研究者声明不能代表当前模型。因此本 Research 只能证明
问题与产品假设值得验证，不能证明 RepoFoundry 已经带来净生产率提升。

竞争者的出现同时是需求信号和商品化风险。公开仓库目前没有 Star、Fork、Release、
安装转化或客户案例，无法从现有公开数据推断市场拉力。目标客户、预算 Owner、付费
方式和可接受部署形态仍是开放问题。

## Decision Drivers and Options

决策驱动包括：用户首次获得价值的时间、Agent 输出质量改善、跨模型可移植性、模板
维护成本、持续使用频率、企业付费意愿、可验证性以及团队当前实现能力。

- Option A：维持当前 Repository Harness 与专业 Skill 工具包。
- Option B：增加一次性 AI 最佳实践项目模板和 Web 下载页。
- Option C：建设单一 Golden Path 起步的 AI 原生 Project Foundry，覆盖
  `create/adopt/doctor/upgrade`，并以 Benchmark 和 Fleet 治理形成长期价值。

## Blockers

| ID | Status | Opened | Resolved | Missing capability | Impact | Unblock or resolution |
|---|---|---|---|---|---|---|

## Progress

- [x] (2026-08-02T07:37:32Z) Research created.
- [x] (2026-08-02) 完成第一轮仓库盘点、外部证据检查、竞争分析与条件式产品建议。
- [ ] 使用客户访谈、真实试点和付费承诺回答 RQ-004。
- [ ] 建立并执行 Golden Path 对照 Benchmark 后更新 Synthesis。

## Outcome

Research is active. A review-ready Synthesis remains active until the Research
Owner explicitly authorizes conclusion. Cancellation also requires explicit
authorization and a reason.

## Artifacts and Notes

- Manifest: `docs/research/active/r-002_ai-native-project-scaffolding-feasibility/RESEARCH_MANIFEST.json`
- Synthesis: `docs/research/active/r-002_ai-native-project-scaffolding-feasibility/SYNTHESIS.md`
- Round controllers belong under `rounds/`; managed analysis belongs under
  `notes/`; sparse, immutable Synthesis milestone snapshots belong under
  `snapshots/`; raw logs, benchmarks, traces and captures belong under
  `artifacts/`.

## Revision Notes

- 2026-08-02T07:37:32Z — Initial Research package created.
