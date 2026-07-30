# Engineering Case Study Prompt 示例

## 一条完整 Prompt 应给出五个写作输入

Case Study 的输入至少说明读者、分享场景、文章类型、输出语言和中心主张。证据
范围可以由用户指定，也可以让 Skill 从目标模块或 EP 反向发现。

```text
使用 $engineering-case-study，基于当前代码、测试、R-006、ADR-011 和 EP-042，
写一篇简体中文的 spans aggregate planner 模块设计文章。

读者：接手 planner 的后端工程师。
场景：团队技术分享后的长期参考。
中心主张：不可变 capability planning 隔离了 transport、policy 和 backend 变化。
使用 EP-042 的 verified revision，先建立 Claim–Evidence Ledger。
生成 draft，保留未验证边界，不要发布，也不要标记 verified。
```

如果用户没有说明语言，Skill 只询问这一项：

> 这篇分享希望用中文、英文，还是中英双语？

## 模块设计：沿一次真实请求解释机制

```text
使用 $engineering-case-study 写一篇英文 module-design 文章，解释 stateless HTTP
请求如何经过 capability inventory、request-scoped dependencies 和 GitHub API。

读者已经理解 MCP 协议，但不了解当前代码。
从一个真实 tools/call 走完整链路，用一张 Mermaid 图建立心智模型。
每个关键机制链接到对应代码和测试；区分开源实现事实与推断。
保持 draft。
```

预期文章按设计压力和运行机制组织，不按文件列表逐个介绍。

## 最佳实践：从多个真实案例提炼采用边界

```text
使用 $engineering-case-study，根据仓库中三个真实 cache invalidation 事故，
写一篇简体中文 best-practice 文章。

中心主张：失效协议必须同时定义 owner、版本和可观测延迟。
先确认三个案例是否足以支持这个泛化判断；如果只能支持局部经验，就降低主张。
给出失败模式、机制、反例、最小采用步骤和验证信号。不要编造效率数字。
```

最佳实践不能只凭一个成功实现泛化成组织规则。

## 交付案例：只保留真正改变路线的转折

```text
使用 $engineering-case-study，基于 concluded R-006、accepted ADR-011、
completed EP-042、Checkpoint 和最终 Benchmark evidence，写一篇中英双语
delivery-case。

中文和英文分别成文，共享 source_revision、证据集合和中心主张。
只保留改变实施路线的发现与决定，不复刻 Progress 流水账。
两份文章都保持 draft，并互相记录 translation_of。
```

EP 的计划目标只有在验证证据存在时才能写成已实现结果。

## 架构演进：解释为何从 A 走到 B

```text
使用 $engineering-case-study，用简体中文写一篇 architecture-evolution 文章，
解释系统为何从 session-bound workers 演进到 explicit query handles。

画出演进前后的状态归属和故障边界；用 Research、ADR、迁移代码和测试说明
变化触发点、迁移顺序、兼容策略与仍保留的代价。
不要把“新方案更优雅”当作证据。保持 draft。
```

## 没有 Research 或 EP 时仍可写，但要缩小主张

```text
使用 $engineering-case-study，只基于 parser 模块的当前代码、测试和 Git 历史，
写一篇英文 module-design draft。

仓库没有对应 Research、ADR 或 EP。请明确这个证据缺口，只解释可由实现和历史
证明的机制，不推断未记录的设计动机。
```

## 定稿需要一条独立 Prompt

普通生成保持 `draft`。用户评审内容后，再显式要求验证：

```text
继续使用 $engineering-case-study 复核刚才的文章。
逐项检查来源、source_revision、代码片段、链接、术语、脱敏和未验证边界。
只有全部发布检查通过时才标记 verified；不要替我发布到外部平台。
```

“完成 EP”“归档 Research”或“写得不错”都不会自动触发 Case Study，也不会自动
把草稿升级为可发布状态。
