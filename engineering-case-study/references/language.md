# 中英文写作

## 语言选择

按以下优先级确定语言：当前请求、既有会话中的明确偏好、目标文档或仓库已声明的
写作语言约定、用户请求的语言。明确的中文、英文、中英双语或 `zh-CN` / `en` /
`bilingual` 选择直接执行，已有授权与偏好不重复确认。

仓库可在现有文档约定中声明默认语言，无需新建配置文件。源码和标识符的语言
不决定文章语言。只有目标读者、发布用途与已有偏好出现影响交付的真实冲突时才
询问；等待答复时继续独立取证。其余情况直接完成草稿，并说明采用的默认值。

## 共享证据，分别成文

中英文版本共享：

- 中心主张；
- Claim–Evidence Ledger；
- `source_revision`；
- Research、ADR、EP、代码和验证证据；
- 对结果与适用边界的判断。

它们不要求共享句子顺序。分别为两类读者选择解释深度、例子、段落节奏和标题。
英文版是同源改写，不是逐句翻译。

双语生成前建立术语表：

| Concept | 中文 | English | 保持原文的标识符 |
|---|---|---|---|
| 示例概念 | 查询计划 | query plan | `MetricQueryPlan` |

- Go/Java/TypeScript 标识符、API 字段、错误码和配置键保持源码拼写。
- 项目自有概念第一次出现时给出中英文对应，后续保持一致。
- 产品名、协议名和已有官方译名不重新创造翻译。
- 中英文版的数字、状态、revision 和证据链接必须一致。

## 中文模式

- 使用自然的简体中文技术表达，句子尽量短。
- 首次出现的必要英文术语可写成“中文（English）”，后续只保留更自然的一种。
- 不把所有代码概念音译；优先解释它在系统中的职责。
- 避免“赋能、抓手、闭环、全方位、显著提升”等无证据表达。

## 英文模式

- Write idiomatic technical English for the intended audience; do not preserve
  Chinese sentence order.
- Lead with the engineering claim and its practical value.
- Prefer concrete subjects and active voice.
- Keep repository identifiers, API names, and code symbols unchanged.
- Avoid filler such as “In today’s rapidly evolving landscape,” “This article
  aims to,” and “In conclusion.”
- Do not overuse artificial contrasts such as “not X, but Y.” State the
  engineering judgment directly.
- Explain organization-specific concepts before using their abbreviations.

## 双语一致性复核

完成两份文章后逐项比较：

1. 中心主张是否等价；
2. 所有数字、版本和生命周期是否一致；
3. 英文版是否遗漏中文中的负面后果或限制；
4. 中文版是否遗漏英文中的条件与推论标记；
5. 两份 `relates_to` 和证据表是否指向同一事实集合；
6. `translation_of` 是否正确互链。

如果某个例子只适合一种语言的读者，可以替换例子，但不能改变工程结论或证据强度。
