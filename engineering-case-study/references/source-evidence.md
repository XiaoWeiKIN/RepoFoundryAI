# 来源与证据

## 目录

- 来源职责
- 代码取证
- Claim–Evidence Ledger
- 冲突与缺口
- 版本与历史

## 来源职责

不同来源回答不同问题。不要让一个来源越权替代另一个来源。

| 来源 | 主要回答 | 不能单独证明 |
|---|---|---|
| 当前代码、schema、配置 | 系统在指定 revision 实际如何工作 | 为什么选择这条路线 |
| 测试、CI、benchmark、运行证据 | 哪些行为或结果被观察到 | 未覆盖场景也正确 |
| concluded Research / sealed Synthesis | 当时有哪些证据、未知和推荐条件 | 实现已经完成 |
| active / review-ready Research | 当前研究认识和待批准方向 | Owner 已批准结论 |
| accepted ADR | 哪个架构选择获得授权及其后果 | 当前实现完全符合决定 |
| Design Doc | 接口、数据流、迁移和运维设计 | 代码已经落地 |
| ExecPlan 当前事实 | 实施目标、约束和当前路线 | 所有计划项已经实现 |
| Task、Progress、Checkpoint | 实施过程、转折、发现和停止点 | 当前规范 |
| Outcomes、verified revision、evidence | 已完成计划在什么版本通过了什么验证 | 更晚版本仍保持相同行为 |
| Git history / diff | 代码如何演进、哪些文件一起改变 | commit message 中的解释一定正确 |

Case Study 是上述来源的派生叙事。案例中的关键主张应能回到至少一个事实源；涉及
动机与结果的主张通常需要两类来源共同支撑。

## 代码取证

先读仓库导航和模块入口，再沿真实调用链下钻：

1. 找到用户或上游模块调用的入口。
2. 找到核心模型、接口和状态转换。
3. 找到边界适配器、持久化或外部系统调用。
4. 找到与文章主张直接相关的测试。
5. 核对 README、注释和代码是否一致。
6. 用 Git history 定位关键变化，但回到当前代码验证最终形态。

典型检索：

```bash
rg --files <module> docs
rg -n "<type|function|error|contract>" <module> docs
git log --oneline -- <paths>
git diff <before>..<after> -- <paths>
```

记录源码路径和符号名。行号只适合当前工作树的短期导航；对长期案例，优先链接
稳定文件和记录 `source_revision`。

如果实现位于 dirty working tree：

- 记录基准 commit；
- 查看并描述相关 diff；
- 不把尚未提交的结果写成历史完成事实；
- 不在文章中泄露与主题无关的用户改动。

## Claim–Evidence Ledger

Ledger 是写作前的临时工作表，不一定进入最终文章：

| Claim | 类型 | Evidence | Revision / lifecycle | Confidence | Publication |
|---|---|---|---|---|---|
| Planner 是唯一 backend 选择点 | code + rationale | `planner.go`; ADR-012 | `git:abc`; accepted | high | yes |
| 新链路降低 40% 延迟 | outcome | benchmark artifact | `git:abc` | high | yes |
| 团队维护成本下降 | inference | 无直接测量 | — | low | omit |

类型使用：

- `code`：实现机制；
- `rationale`：选择和权衡；
- `outcome`：测试、性能、可靠性或用户可观察结果；
- `history`：实施过程和转折；
- `inference`：作者基于多份来源作出的解释。

推论可以写，但要用“这意味着”“从这些证据可以推断”等语言标明，并保留适用
条件。不要把推论包装成测量结果。

## 冲突与缺口

遇到来源冲突时按问题类型裁定：

- “当前怎样运行”以指定 revision 的代码、schema 和测试为准。
- “为什么这样决定”以 accepted ADR 和当时 Decision Log 为准。
- “研究当时知道什么”以对应 revision 的 sealed 或明确标态 Synthesis 为准。
- “最终取得什么结果”以 verified revision 和 evidence 为准。

把冲突本身作为有价值的工程转折写入文章，前提是能说明哪个来源更新、哪个来源
仅代表历史。不要静默拼接互相矛盾的描述。

证据不足时选择以下一种：

1. 缩小主张；
2. 标明未知或推论；
3. 运行安全、相关的验证；
4. 请求用户提供缺失的私有结果；
5. 删除该段。

不要为了让故事完整而补造原因、数字、用户反馈或失败经历。

## 版本与历史

文章至少记录一个可恢复的代码版本：

- `git:<full-or-unambiguous-sha>`；
- 其他 VCS revision；
- 无 VCS 时使用稳定 `snapshot:<id>`；
- dirty 工作区使用 `<base-revision>+dirty`，并在正文说明事实边界。

历史案例必须区分：

- 当时成立的行为；
- 当前仍成立的行为；
- 已被替代但仍值得复盘的方法。

文章开头链接当前规范入口；正文的历史命令、API、路径或数据必须明确标注时间和
revision，避免案例成为误导性的第二份规范。
