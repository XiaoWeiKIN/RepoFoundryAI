# Controlled technical writing

This is RepoFoundry authoring guidance, not a Catalog Specification. It combines
selected Google developer-documentation practices for readers, organization,
procedures, and accessibility with STE-inspired precision. It does not reproduce
ASD-STE100 or its dictionary, claim full ASD-STE100 conformance, or imply Google
endorsement. Source references and RF-specific adaptations are identified below.

Read the shared guidance through documentation maintenance, then the section for
the artifact being written. Apply it to new prose and authorized revisions, not
to an entire repository at once. This guide adds no approval step or lifecycle gate.

## Editorial basis and precedence

Technical facts, artifact contracts, installed Specifications, evidence, and
authority boundaries remain controlling. Follow project-specific writing and
language conventions before this guide's editorial defaults. Within those
boundaries, use Google-informed organization and natural prose together with
STE-inspired terminology and unambiguous actions. Style never overrides meaning.
Do not create a separate Google-writing policy, mandatory document fields, or
an extra Skill. A useful exception should be consistent and preserve meaning.

## Language and fidelity

Keep the user's requested language; otherwise follow the Skill and repository
language conventions. Use STE-inspired English for English prose. For Chinese
and other languages, use the clarity principles without imposing English
vocabulary, grammar, or word-count rules. Do not translate a document merely to
apply this guide. Keep bilingual versions aligned in meaning and evidence.
English sentence case and word-count advice do not become Chinese writing rules.

Preserve conditions, negation, quantifiers, uncertainty, units, and requirement
strength. Do not replace `MUST` with `SHOULD`, turn a possibility into a fact, or
remove a qualification to shorten a sentence. Keep technical terms, identifiers,
commands, paths, interface names, schema fields, and evidence references exact.
Do not replace distinct operations with one word just because they look similar.

In ordinary guidance, make requirements, recommendations, options, and predicted
results distinguishable. Do not replace normative `MUST`, `SHOULD`, or `MAY` to
follow an editorial preference against "should". Prefer present tense for verified
current behavior, but keep proposed behavior, future actions, and historical
observations in their actual state. Changing tense does not implement a proposal.

Do not rewrite quoted source text, raw logs, code, or normative source excerpts
for style. Do not change metadata, IDs, required headings, generator markers,
digests, or lifecycle fields. Do not rewrite accepted ADRs, approved snapshots,
sealed Checkpoints, sealed Benchmark bundles, or archived plans in place. Use
the owning workflow's revision or supersession process when a change is needed.

## Common guidance

Use one stable term for each concept. Define an unfamiliar term at first use.
Retain established software terminology, including backpressure, idempotency,
and write-ahead log. A plain synonym is not an improvement if it changes meaning.

Prefer short, complete sentences with one main claim or action. Keep conditions
and exceptions with the claim they limit. Split a sentence when that makes the
logic clearer; do not enforce an arbitrary word limit or produce fragments.
Use connected paragraphs to explain mechanisms and trade-offs, rather than a
sequence of disconnected bullets.

Name the actor when several components or people could perform the action.
Use a direct verb when it is clearer than an abstract noun phrase. Imperatives
can address the operator directly. Passive voice is acceptable when the actor
is irrelevant or unknown; do not invent an actor to avoid it.

Replace an ambiguous reference such as "this", "it", or "the relevant component"
with the actual subject. Put a prerequisite before the action that requires it.
State failure and stop conditions when the source contract supplies them. If a
required detail is unknown, name the gap instead of inventing a command or rule.

Remove filler, idioms, and promotional wording. Support a comparison with its
criterion, evidence, and scope. Words such as "robust" or "significant" are not
banned: a defined statistical term or a supported claim can require them.
Do not invent a measurement to justify an adjective.

Separate observations, interpretations, proposals, decisions, and unknowns.
Keep the evidence and its limits near the claim. Retain negative evidence and
uncertainty. Clear prose must not imply acceptance, approval, completion, or
verification that did not occur.

## Reader and structure

Identify the reader's task, relevant prior knowledge, and what they need to learn
or decide. Use context already available; ask only about gaps that change the
result. Do not require an audience form or a new section in every artifact.
Open with the answer or system model the reader needs, plus material limits.
Introduce unfamiliar concepts before their internals and keep deep detail after
the main explanation or behind a meaningful link.

Give each paragraph a clear point, then connect its evidence and consequences.
Use transitions that explain cause, contrast, or sequence, not decorative filler.
Write naturally and respectfully; do not describe a task as "easy" or "obvious".
Use lists for steps or parallel choices, not to replace a connected explanation.

Use descriptive headings in a logical hierarchy. For new English headings,
prefer sentence case, action phrases for tasks, and noun phrases for concepts.
Keep required headings and existing anchors stable; check inbound links before
an authorized rename. Use code formatting for identifiers, paths, commands, and
literal output; use bold for named UI controls. Link text should name its target
or purpose, not say "click here". Avoid unnecessary formatting for emphasis.

## Procedures and examples

Before a procedure, state the relevant environment, prerequisites, and authority
needed. Use numbered steps for ordered multi-step work, usually one main action
per step. Put conditions and the action's location before the dependent action.
Introduce a command by its purpose, explain every placeholder, and describe the
expected result after the action. Mark optional steps and failure or stop branches
explicitly. Keep preview, apply, verification, and release distinct.

Keep code examples small enough to inspect. Identify pseudocode, omitted setup,
and illustrative output; label measured output with its actual source. Verify
commands against available tools and interfaces, but do not execute destructive
or external actions merely to validate prose. Report untested examples instead
of claiming success. Never invent flags, output values, or a recovery procedure.

## Accessible explanations

Provide an equivalent text explanation for a diagram, image, or animation.
Describe its relevant relationships or conclusion, not merely "architecture
image". Use appropriate alt text for informative images and empty alt text for
pure decoration. Keep code and output as selectable text, not screenshots alone.
Do not communicate status only through color, position, shape, or sound.

For requested interactive views, use semantic controls with clear labels and
keyboard access. Keep focus and reading order meaningful, and offer a static text
or table route to the same facts. For audio or video, provide captions, a transcript,
or a description that conveys the content. Avoid flashing or unnecessary motion;
provide playback controls when animation is used. Check the rendered reading path
when tools permit, and report which accessibility checks were not performed.
These are authoring and review expectations, not a claim of accessibility certification.

Do not generate HTML or video just to satisfy this guide. When a derived view is
requested, keep its source revision, assumptions, and limits visible. It does not
become a second fact owner. Source changes require rechecking or regeneration;
a polished view is not proof of actual behavior or approval.

## Rewrite scope and fidelity review

Choose the requested operation before editing. Polishing changes expression,
not the factual model, headings, anchors or evidence. Rebuilding may change that
model only from inspected sources and within the requested scope; identify factual
corrections separately. Review-only work returns findings, not edits. Apply these
rules to technical passages in mixed documents without flattening the surrounding
narrative. Do not expand a prose request into project migration or artifact approval.

Treat meaning preservation as a constraint, not a percentage score. Sentence
length, active voice and list use are editorial defaults. An exception can preserve
a causal explanation or an unknown actor; report material exceptions, not a quota
of rules satisfied. Use ordered instructions for an operator's procedure, but do
not turn a description of automatic software events into commands for the reader.

Before rewriting, locate existing terminology in project glossaries, writing
conventions, entry instructions and the affected source. Use those names. If no
term owner exists, keep a small working vocabulary for this document; define only
unfamiliar concepts. Do not create a repository glossary, rename code or revise
historical terms without authorization. A linter match never overrides a term.

After rewriting, compare the original and revision using these review prompts.
These are author checks, not new Spec Requirement IDs or lifecycle gates:

| Prompt | Compare before and after |
|---|---|
| Fidelity: branches | Preconditions, only-if clauses, empty inputs, failure paths and exceptions remain attached to their claims. |
| Fidelity: actors | The same component or person owns the action; caller-controlled state is not described as internally owned. |
| Fidelity: strength | Negation, quantities, units, uncertainty and normative keywords retain their force. |
| Fidelity: status | Proposal, authorization, implementation and verification remain distinct; historical observations keep their scope. |
| Fidelity: protected bytes | Code, quotations, logs, IDs, links, required headings and sealed sources remain exact. |

Use a counterexample when a sentence loses a condition. In a constructed list
navigator, an empty enabled list returns no selection. An absent current item makes
Down choose the first enabled item. Otherwise Down advances with wraparound.
Rewriting this as "Down selects the first item" is incorrect even though it is
shorter. Compare all three branches; do not declare semantic equivalence from a
keyword check. This example is illustrative, not a report about a target project.

## Chinese precision in practice

中文说明先给读者当前需要的结论，再解释条件和原因。拆句时保留条件的作用范围；
不用短句代替完整推理。主语改变时写出组件或人的名称，避免让读者猜谁负责动作。

先沿用项目术语，再消除同一段中的无意混称。“建议面板”可以是项目名词，不因其中
含有“建议”就改名。“统计显著性”也不等于空泛的程度词。代码名和测试名保持原样；
不为中英文空格、标点或措辞改写代码、命令、原始输出和引文。

以下是构造的措辞例子，不声明任何项目行为或测试结果：

| 问题 | 改写方向 |
|---|---|
| 对缓存进行检查 | 缓存模块检查缓存条目。仅在来源确实指定该主体时这样写。 |
| 客户端调用重试器，它保留计数 | 如果重试器是主体，写“客户端调用重试器。重试器保留计数”。 |
| 校验失败后仍在某些情况下继续 | 保留来源给出的失败分支和具体条件；缺失时报告，不猜测条件。 |
| 恢复选区、重挂节点和通知调用方挤在一句 | 按实际事件顺序拆句；每句保留主体，不重新排序有依赖的动作。 |

新写的中文要求在项目没有约定时，可用“应／不应”表达要求，“宜／不宜”表达推荐，
“可／不必”表达许可或不作要求。已有契约的 MUST/SHOULD/MAY 及项目固定译名优先；
不通过替换情态词增强或减弱原意。“能／不能”描述能力时，不改成授权或禁止。

技术说明优先使用主动、完整的句子。包装动词、长定语、指代和句长都是复核入口，
不是要求作者删除全部命中词。给操作人员的步骤把前提放在动作之前，结果单独说明；
机制文档保留连贯段落，Case Study 保留叙事，不强制每三项就拆成列表。

## Optional mechanical writing check

The full RF checkout includes `scripts/check_writing.py`. It reads only explicitly
named UTF-8 text/Markdown files and prints review candidates with source SHA-256
and line locations. It does not edit files, recurse through a project, call a model,
fetch a policy or prove factual correctness. Independently installed professional
Skills do not require this script: use this guide manually and report the tool as
unavailable rather than installing another package solely for style.

From the full RF checkout, replace `PATH` with the authored file to inspect:

```bash
python3 -B scripts/check_writing.py PATH --lang zh --json
python3 -B scripts/check_writing.py PATH --lang zh --line-range 12:35 --json
```

The second command checks an explicitly selected inclusive line range of one file;
it does not discover Git changes. Read the surrounding conditions during semantic
review. Repeat `--line-range` for additional ranges. Omit `--lang` for per-line
Chinese/English detection, or use `--lang en` for English. Mixed-language detection
is a heuristic; it does not translate text or validate other languages.

Use `--length-hints` only when useful. Its 40/50 Chinese-unit and 20/25 English-word
triggers distinguish step-like and descriptive line fragments. They are review
hints, not sentence limits or a compliance score. Protected spans are omitted and
soft-wrapped sentences are not reconstructed, so these counts are not linguistic
measurements. Project conventions and meaning take precedence.

The scanner conservatively skips code fences, inline code, quotations, metadata,
link targets and HTML blocks. It is not a complete Markdown parser and may omit
prose. Findings return exit status 0; unreadable files, invalid ranges, invalid
UTF-8 and files larger than 1 MiB return 2. Tool errors must not be reported as a
clean scan. No `--fix`, recursive scan or blocking style mode is provided.

Keep checker unit tests in repository CI, not stylistic findings as a merge gate.
Review matches in context, then perform the separate fidelity and reader-task
reviews. A successful process or zero candidates is not semantic verification,
accessibility certification, model adherence or ASD-STE100 conformance.

## Separate document and author handoff

Deliver a readable document and a short author note only where needed. Keep
execution-critical prerequisites, risks and stopping conditions beside the action
in the document; place missing evidence and noncritical editorial questions in the
note. Use placeholders only when a reader cannot complete the task without the
missing value. Never invent a recovery command, measurement or owner to fill one.

Report the actual command, input revision or digest, exit status, candidate counts
and unperformed checks when a checker ran. If it did not run, say so; reading its
source is not execution. Do not claim a count of rules applied without a traceable
basis. Keep factual corrections distinct from wording changes. Preserve unsupported
claims at their original strength during polishing and flag them for the author;
do not knowingly publish a contradicted statement as a verified fact.

For comparative writing evaluations, fix source material, task, model settings and
output budget before generation. Use isolated runs and hide treatment labels from
reviewers when possible. Freeze assertions before scoring and retain failures.
Packaging tests and an eval catalog do not execute an LLM. Same-session reconstructions
are demonstrations, not blind experiments or evidence of a quality improvement.

## Documentation maintenance

When authorized code changes affect documentation, update the current explanation
in the same change when feasible, or identify the remaining gap. Link shared facts
and procedures rather than maintaining independent copies. Use the project's
existing owner and navigation conventions; do not invent a new ownership registry.

Distinguish historical decisions from present behavior. General advice to trim
outdated docs does not authorize deleting or rewriting accepted ADRs, approved
snapshots, sealed evidence, or archived plans. Propose a current explanation or
route revision through the owning workflow. Stay within the requested scope.

## ADR

State one concrete decision or proposal, then explain its rationale. Preserve
the ADR's actual status. Identify affected behavior, constraints, alternatives,
and costs. Keep consequences separate from promised outcomes. Preserve stable
constraint IDs and the existing Confirmation and Revisit Triggers sections.
Name the evidence that supports a claimed benefit; do not turn an expected
benefit into a measured result. Writing an ADR does not accept it.

## ExecPlan, Task, and Bugfix

Describe the target, action, prerequisites, expected result, and verification
for each bounded unit of work. Use exact repository commands only when verified.
Keep ordering and failure branches explicit. Distinguish planned work from work
already performed. Separate test execution from acceptance and release authority.
Record actual blockers and recovery information, not "handle as appropriate".

## Checkpoint

State the verified revision, completed work, remaining work, evidence, and
blockers. Keep the current handoff readable without replaying the whole session.
Do not compress away a failure, unresolved condition, or evidence locator.
A stylistic revision does not justify changing sealed history.

## Architecture and Design

Explain the system model before listing files. Name boundaries, ownership,
interfaces, invariants, failure behavior, and material trade-offs. Use paragraphs,
examples, tables, or Mermaid where they explain the mechanism. Distinguish
observed behavior from proposed or approved design. Do not reduce an explanation
to short sentences that no longer establish why the design works.

## Research and Synthesis

Separate observations from interpretations and recommendations. State confidence,
applicability, counterevidence, and remaining unknowns. Explain the reasoning
between evidence and conclusion. Preserve correlation/causation distinctions
and source references. Do not turn review-ready prose into a concluded Research.

## Benchmark Scenario and Result

In a Scenario, state hypotheses, controlled variables, workload, repetitions,
units, thresholds, and failure or stop conditions before measurement. In a
Result, distinguish raw observations from interpretation and report uncertainty.
Do not change a frozen protocol, discard negative results, or rewrite an outcome
for readability. A valid digest does not prove experimental validity.

## Case Study

Use the common guidance with a lighter narrative style. Preserve the central
claim, causal explanation, examples, and trade-offs. Do not force an article into
maintenance instructions. Keep claims traceable and respect publication and
redaction boundaries. A polished article does not become a normative source.

## Examples for ADR and ExecPlan

These examples illustrate wording, not facts about a target repository.

Given an unaccepted proposal to use a read cache, a database that remains the
source of truth, and a specified fallback on cache-read failure:

> Proposed decision: Use a cache for reads. If a cache read fails, read from the
> database. The database remains the source of truth. The latency effect has not
> been measured.

Given an authorized task to run RepoFoundry's repository check, with no release
authorization:

> Run `python3 -B scripts/check.py` from the repository root. If the check fails,
> record the failure and keep the task open. If it passes, record the command,
> exit status, and tested revision. Passing this check does not authorize release.

Do not replace either example with an unsupported claim such as "the system is
now more robust" or omit its status, failure branch, or evidence limitation.

## Review before handoff

Compare the revision with its sources. Check terminology, actors, references,
conditions, uncertainty, requirement strength, evidence, and lifecycle status.
Walk the intended reader's task: can they find the answer, follow the reasoning
or procedure, and reach its evidence without relying on images, sound, or color?
Check examples, links, headings, and available keyboard paths. Separate editorial
suggestions from factual errors and record checks that could not be performed.
Correct misleading prose within the authorized scope. Report unresolved gaps
without filling them with invented facts. Then run the artifact's existing
validators; writing review is not a substitute for them.

Sentence length and keyword matches can identify review candidates. They cannot
prove clarity, truth, authorization, or ASD-STE100 compliance. Do not label a
heuristic pass as semantic verification or add a blocking style gate.

## Source references

This is RF's selective paraphrase and adaptation, not a copy of either guide.
The Google sources below inform the editorial defaults. RF adds artifact-state,
authority, exact-source, and immutable-history safeguards; it deliberately does
not impose a fixed sentence length or an English grammar on other languages.
These links are optional maintainer references, not runtime dependencies.
Use the packaged guidance offline; do not fetch the full guides for every task.

| Editorial topic | Official source |
|---|---|
| Reference hierarchy and exceptions | Google Developer Documentation Style Guide: https://developers.google.com/style |
| Reader knowledge and goals | Google Technical Writing, Audience: https://developers.google.com/tech-writing/one/audience |
| Document scope and organization | Google Technical Writing, Documents: https://developers.google.com/tech-writing/one/documents |
| Natural tone and transitions | https://developers.google.com/style/tone |
| Ordered instructions and placeholders | https://developers.google.com/style/procedures |
| Headings and inline formatting | https://developers.google.com/style/headings and https://developers.google.com/style/text-formatting |
| Requirements and tense | https://developers.google.com/style/prescriptive-documentation and https://developers.google.com/style/tense |
| Text alternatives and keyboard access | https://developers.google.com/style/accessibility |
| Current docs and shared fact ownership | Google Documentation Best Practices: https://google.github.io/styleguide/docguide/best_practices.html |
| Controlled-language background | ASD-STE100: https://www.asd-ste100.org/ |

Google Developers prose is licensed under CC BY 4.0 unless otherwise noted:
https://creativecommons.org/licenses/by/4.0/. The adaptations here are identified
above. No Google code samples or ASD-STE100 dictionary entries are reproduced.

### Hai adaptation notice

The sections "Rewrite scope and fidelity review", "Chinese precision in practice"
and "Separate document and author handoff" adapt selected methods from Hai
Simplified Technical by hylarucoder, Copyright (c) 2026 hylarucoder, under
CC BY-NC 4.0: https://creativecommons.org/licenses/by-nc/4.0/ .
Source revision: `a6c7ed23aee5fe9a3d9cb7e162cd8a6c0862ce8c`.
Source and license: https://github.com/hylarucoder/hai-stack/tree/a6c7ed23aee5fe9a3d9cb7e162cd8a6c0862ce8c/skills/hai-simplified-technical
and https://github.com/hylarucoder/hai-stack/blob/a6c7ed23aee5fe9a3d9cb7e162cd8a6c0862ce8c/LICENSE .

RF changes: integrate scope/fidelity review with existing evidence and authority
boundaries; use original bilingual examples; treat length and keyword matches as
non-blocking hints; preserve project terms, independent Skill use and historical
sources. The RF checker is a separate implementation, not a copy of Hai's script.
The adapted material retains the noncommercial restriction and this attribution
in each packaged guide. This notice does not relicense unrelated RF code, endorse
RF on behalf of the upstream author or certify full ASD-STE100 conformance.

## Distribution maintenance

The distribution source is `references/controlled-writing.md`. Each professional
Skill contains an identical file at that relative path so it works independently
and offline. These are packaged copies, not separate policy owners. From the
RepoFoundry source checkout, run `python3 scripts/sync_controlled_writing.py` to
check them or add `--apply` to refresh them after editing the source. Repository
tests check both copy integrity and the Skill reading links. Those tests do not
measure an LLM's adherence to the writing guidance.
