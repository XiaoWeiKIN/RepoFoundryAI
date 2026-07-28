# Tool landscape

## BMAD Method

BMAD Deep Recon provides typed research packs, draft/process/run modes,
parallel evidence gathering, claim verification, and a downstream summary.
It is the closest research methodology to the supplied corpus, but its
standard decision interface remains a report or summary rather than a
mechanically sealed multi-document graph.

Sources:

- <https://docs.bmad-method.org/reference/workflow-map/>
- <https://docs.bmad-method.org/zh-cn/explanation/deep-recon/>

## GitHub Spec Kit

Spec Kit treats a feature as a directory of related artifacts and supports
cross-artifact analysis. Its workflow engine supports fan-out, fan-in, human
gates, and resumable state, which is a useful execution model for researching
multiple questions before synthesis.

Sources:

- <https://github.github.io/spec-kit/>
- <https://github.github.io/spec-kit/reference/workflows.html>

## OpenSpec

OpenSpec schemas define artifact identities and dependencies and can be
customized to flows such as `research -> proposal -> design -> tasks`. Its
status and archive model is the closest reference for a Research manifest and
artifact DAG, although it is not itself a deep-research engine.

Sources:

- <https://openspec.dev/docs/opsx>
- <https://openspec.dev/docs/reference/cli>

## Deep-research engines

GPT Researcher, Open Deep Research, STORM, and hosted deep-research products
are useful evidence collectors. Their primary output is a synthesized report,
so they should integrate as upstream producers rather than own the
Research-to-ADR lifecycle.

Sources:

- <https://github.com/assafelovic/gpt-researcher>
- <https://github.com/langchain-ai/open_deep_research>
- <https://github.com/stanford-oval/storm>
