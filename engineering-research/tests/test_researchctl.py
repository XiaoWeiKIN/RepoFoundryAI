from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "researchctl.py"


def find_epctl() -> Path | None:
    configured = os.environ.get("EXECUTION_PLAN_EPCTL")
    candidates = [
        Path(configured).expanduser() if configured else None,
        SKILL_DIR.parent / "scripts" / "epctl.py",
        SKILL_DIR.parent / "execution-plan" / "scripts" / "epctl.py",
    ]
    return next(
        (candidate for candidate in candidates if candidate and candidate.is_file()),
        None,
    )


EPCTL = find_epctl()


class ResearchctlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *arguments],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def run_epctl(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        if EPCTL is None:
            self.skipTest(
                "execution-plan consumer is not installed; "
                "set EXECUTION_PLAN_EPCTL to run contract tests"
            )
        result = subprocess.run(
            [sys.executable, str(EPCTL), "--repo", str(self.repo), *arguments],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected epctl exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def new_research(
        self,
        slug: str = "sample",
        *extra: str,
    ) -> Path:
        result = self.run_cli(
            "new-research",
            "--slug",
            slug,
            "--title",
            slug.replace("-", " ").title(),
            "--owner",
            "Test Research Owner",
            "--author",
            "Test Researcher",
            *extra,
        )
        return Path(result.stdout.strip())

    @staticmethod
    def replace_section(path: Path, heading: str, body: str) -> None:
        text = path.read_text(encoding="utf-8")
        pattern = rf"(?ms)^## {re.escape(heading)}\s*$.*?(?=^## |\Z)"
        replacement = f"## {heading}\n\n{body.strip()}\n\n"
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count != 1:
            raise AssertionError(f"section not found: {heading}")
        path.write_text(updated, encoding="utf-8")

    @staticmethod
    def complete_placeholders(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"<!--\s*REQUIRED(?:_[A-Z_]+)?\s*:[\s\S]*?-->",
            "Recorded evidence.",
            text,
        )
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def topic_frontmatter(path: Path, schema_version: str) -> str:
        text = path.read_text(encoding="utf-8")
        end = text.find("\n---\n", 4)
        if end < 0:
            raise AssertionError("topic frontmatter not found")
        frontmatter = text[: end + len("\n---\n")]
        frontmatter = re.sub(
            r'(?m)^schema_version:\s*"[^"]+"$',
            f'schema_version: "{schema_version}"',
            frontmatter,
            count=1,
        )
        if schema_version in {"1", "2", "2.1"}:
            frontmatter = re.sub(
                r"(?m)^topic_id:\s*RT-\d{3,}\n",
                "",
                frontmatter,
                count=1,
            )
        return frontmatter

    def complete_topic(self, path: Path) -> None:
        frontmatter = self.topic_frontmatter(path, "2.2")
        match = re.search(r"(?m)^topic_id:\s*(RT-\d{3,})$", frontmatter)
        if not match:
            raise AssertionError("topic_id not found")
        topic_id = match.group(1)
        body = f"""

# {topic_id} · Complete learning topic

## 结论速览

<!-- topic-role: decision-brief -->

> **答案：** The inspected implementation and tests share one stable contract.
>
> **置信度：** High — implementation and tests agree.
>
> **决策影响：** Keep the current contract.
>
> **适用边界：** The inspected implementation is used.

关联研究问题：`RQ-001`。

This topic determines which contract is safe.

**按阅读目标选择路径：**

- Quick decision: read this brief and implications.
- Learn: continue through the model and A-001.
- Full review: inspect the evidence index and sources.

## 先理解实现与测试如何表达同一契约

<!-- topic-role: mental-model -->

The implementation defines behavior and the tests independently exercise it.
Their agreement is the minimum model needed by the analysis.

## 从独立实现与测试推导契约稳定性

<!-- topic-role: analysis -->

The analysis first observes the implementation, then checks whether the tests
encode the same externally visible behavior.

### 实现与测试共同约束当前契约（A-001）

The implementation exposes one contract, while an independently maintained
test suite exercises the same inputs, outputs, and failure boundary. Their
agreement is stronger than either source alone because a mismatch would fail
the suite. The exact observation is registered as E-001. This supports keeping
the contract for the inspected version while leaving external integrations
outside the claim.

## 替代解释没有得到同等支持

<!-- topic-role: alternatives -->

No inspected implementation or test supports a different contract.

## 当前证据支持保留现有契约

<!-- topic-role: implications -->

Keep the current contract and add conformance coverage before expanding its
applicability to external integrations.

## 哪些新证据会改变当前判断

<!-- topic-role: falsifiers -->

| 影响的分析 | 会削弱或推翻当前判断的证据 | 为什么重要 | 如何验证 |
|---|---|---|---|
| A-001 | A supported implementation uses another contract. | The compatibility claim would narrow. | Run conformance tests. |

## 下游交接

<!-- topic-role: handoff -->

Synthesis should retain the current contract. No ADR is ready yet.

## 证据索引

<!-- topic-role: evidence-index -->

| ID | 观察 | 精确来源 | 支持的分析 | 置信度 |
|---|---|---|---|---|
| E-001 | Implementation and tests use the same contract. | S-001 | A-001 | High |

## 来源

<!-- topic-role: sources -->

- S-001 — `src/contract.py` and `tests/test_contract.py` — inspected contract.

## 修订记录

<!-- topic-role: revision-notes -->

- Complete schema 2.2 fixture.
"""
        path.write_text(frontmatter + body.lstrip("\n"), encoding="utf-8")

    @staticmethod
    def convert_topic_to_complete_v1(path: Path) -> None:
        frontmatter = ResearchctlTestCase.topic_frontmatter(path, "1")
        body = """

# Legacy topic

## Executive Takeaway

The legacy contract remains supported with high confidence.

## Question and Decision Relevance

Related Research Questions: `RQ-001`.

This question determines which implementation contract is safe.

## Scope and Non-goals

This topic covers the contract and excludes performance.

## Current Context

The implementation exposes one stable contract.

## Method and Evidence Selection

The implementation and its tests were inspected together.

## Evidence

### E-001 — The implementation and tests agree

**Observation**

Both use the same contract.

**Evidence**

`src/contract.py` and `tests/test_contract.py`.

**Interpretation**

The current option preserves observed behavior.

**Confidence**

High

## Analysis

Independent implementation and test agreement supports the current option.

## Alternatives and Counterevidence

No credible alternative was found in the bounded implementation.

## Findings

| ID | Finding | Confidence | Evidence | Decision impact |
|---|---|---|---|---|
| F-001 | The contract is stable. | High | E-001 | Keep the current option. |

## Uncertainty and Limitations

External integrations were not inspected and would weaken applicability.

## Impact on Synthesis

Keep the current contract as a supported constraint.

## Next Inquiry

No further inquiry is needed before synthesis.

## References and Artifacts

`src/contract.py` and `tests/test_contract.py`.

## Revision Notes

- Legacy schema 1 compatibility fixture.
"""
        path.write_text(frontmatter + body.lstrip("\n"), encoding="utf-8")

    @staticmethod
    def convert_topic_to_complete_v2(path: Path) -> None:
        frontmatter = ResearchctlTestCase.topic_frontmatter(path, "2")
        body = """

# Legacy claim-card topic

## Decision Brief

> **Answer:** The inspected contract is stable.
>
> **Confidence:** High — implementation and tests agree.
>
> **Decision impact:** Keep the current option.
>
> **Applies when:** The inspected implementation is used.

Related Research Questions: `RQ-001`.

This question determines which contract is safe.

## Model at a Glance

The implementation and tests express the same contract.

## Claims and Evidence

### C-001 — The inspected contract is stable

**Evidence**

The implementation and tests use the same contract.

**Reasoning**

Independent agreement supports the current behavior.

**Decision impact**

Keep the current option.

**Confidence**

High — implementation and tests agree.

**Falsifier**

A supported implementation with another contract.

## Options and Trade-offs

No credible alternative was found in the inspected boundary.

## Risks, Unknowns, and Validation

External integrations remain outside the claim.

## Handoff

Synthesis should retain the current contract.

## Sources

- S-001 — `src/contract.py` and `tests/test_contract.py`.

## Revision Notes

- Complete legacy schema 2 fixture.
"""
        path.write_text(frontmatter + body.lstrip("\n"), encoding="utf-8")

    def prepare_for_conclusion(self, research: Path) -> None:
        synthesis = research.parent / "SYNTHESIS.md"
        self.complete_placeholders(research)
        self.complete_placeholders(synthesis)
        self.replace_section(
            research,
            "Research Questions",
            "\n".join(
                (
                    "| ID | Status | Question | Answer or disposition | Evidence |",
                    "|---|---|---|---|---|",
                    "| RQ-001 | answered | Which contract works? | "
                    "The manifest contract works. | `notes/result.md` |",
                )
            ),
        )
        self.run_cli("mark-review-ready", "R-001")

    def conclude_research(self, research_id: str = "R-001") -> Path:
        result = self.run_cli(
            "conclude-research",
            research_id,
            "--approved-by",
            "Test Research Owner",
            "--approval-ref",
            "test:explicit-owner-approval",
        )
        return Path(result.stdout.strip())

    def test_init_and_managed_manifest_are_idempotent(self) -> None:
        first = json.loads(self.run_cli("init").stdout)
        self.assertIn("docs/RESEARCH.md", first["created"])
        second = json.loads(self.run_cli("init").stdout)
        self.assertEqual(second["created"], [])

        research = self.new_research("managed")
        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["mode"], "managed")
        self.assertEqual(
            [item for item in manifest["documents"] if item["role"] == "round"],
            [manifest["documents"][0]],
        )
        self.assertEqual(manifest["roots"][0]["base"], "package")
        self.assertEqual(manifest["roots"][0]["path"], "notes")

    def test_managed_sync_and_drift_detection(self) -> None:
        research = self.new_research("managed-drift")
        notes = research.parent / "notes"
        (notes / "one.md").write_text("# One\n", encoding="utf-8")
        synced = json.loads(self.run_cli("sync-research", "R-001").stdout)
        self.assertEqual(synced["documents"], 2)
        self.run_cli("validate")

        (notes / "two.md").write_text("# Two\n", encoding="utf-8")
        drift = self.run_cli("validate", expected=1)
        self.assertIn("manifest drift", drift.stderr)

        self.run_cli("sync-research", "R-001")
        self.run_cli("validate")

    def test_new_topic_creates_auditable_round_evidence(self) -> None:
        research = self.new_research("structured-topic")

        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "http-auth-boundary",
                "--title",
                "HTTP authentication boundary",
                "--question",
                "RQ-001",
                "--author",
                "Security Researcher",
            ).stdout.strip()
        )

        self.assertEqual(topic.parent, research.parent / "notes")
        topic_text = topic.read_text(encoding="utf-8")
        self.assertIn('schema_version: "2.2"', topic_text)
        self.assertIn("doc_type: research-topic", topic_text)
        self.assertIn("parent_id: R-001", topic_text)
        self.assertIn("topic_id: RT-001", topic_text)
        self.assertIn("round_id: RR-001", topic_text)
        self.assertIn(
            "# RT-001 · HTTP authentication boundary",
            topic_text,
        )
        self.assertIn("`RQ-001`", topic_text)
        topic_headings = re.findall(r"(?m)^## (.+)$", topic_text)
        self.assertEqual(topic_headings[0], "结论速览")
        self.assertEqual(
            re.findall(
                r"<!--\s*topic-role:\s*([a-z0-9-]+)\s*-->",
                topic_text,
            ),
            [
                "decision-brief",
                "mental-model",
                "analysis",
                "alternatives",
                "implications",
                "falsifiers",
                "handoff",
                "evidence-index",
                "sources",
                "revision-notes",
            ],
        )
        self.assertIn("（A-001）", topic_text)
        self.assertNotIn("\n## Claims and Evidence\n", topic_text)
        self.assertLess(
            topic_text.index("topic-role: analysis"),
            topic_text.index("topic-role: implications"),
        )
        self.assertLess(
            topic_text.index("topic-role: handoff"),
            topic_text.index("topic-role: evidence-index"),
        )

        round_text = (
            research.parent / "rounds" / "rr-001_baseline.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "**RT-001** — [HTTP authentication boundary]"
            "(../notes/http-auth-boundary.md)",
            round_text,
        )

        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        topic_record = next(
            item
            for item in manifest["documents"]
            if item["path"] == "notes/http-auth-boundary.md"
        )
        self.assertEqual(topic_record["role"], "topic")
        self.assertEqual(topic_record["topic_id"], "RT-001")
        self.run_cli("validate")

        round_file = research.parent / "rounds" / "rr-001_baseline.md"
        round_file.write_text(
            round_text.replace(
                "**RT-001** — [HTTP authentication boundary]"
                "(../notes/http-auth-boundary.md)",
                "HTTP authentication boundary",
            ),
            encoding="utf-8",
        )
        missing_route = self.run_cli("validate", expected=1)
        self.assertIn(
            "RR-001 Evidence Added must link "
            "../notes/http-auth-boundary.md",
            missing_route.stderr,
        )

    def test_topic_ids_are_monotonic_and_unique_within_research(self) -> None:
        research = self.new_research("topic-identities")
        first = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "first-topic",
                "--title",
                "First topic",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        second = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "second-topic",
                "--title",
                "Second topic",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.assertIn(
            "topic_id: RT-001",
            first.read_text(encoding="utf-8"),
        )
        second_text = second.read_text(encoding="utf-8")
        self.assertIn("topic_id: RT-002", second_text)
        self.assertIn("# RT-002 · Second topic", second_text)

        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        topic_records = sorted(
            (
                item["topic_id"],
                item["path"],
            )
            for item in manifest["documents"]
            if item["role"] == "topic"
        )
        self.assertEqual(
            topic_records,
            [
                ("RT-001", "notes/first-topic.md"),
                ("RT-002", "notes/second-topic.md"),
            ],
        )
        self.run_cli("validate")

        second.write_text(
            second_text.replace("RT-002", "RT-001"),
            encoding="utf-8",
        )
        self.run_cli("sync-research", "R-001")
        duplicate = self.run_cli("validate", expected=1)
        self.assertIn("duplicate topic_id RT-001", duplicate.stderr)

    def test_new_topic_continues_after_ids_in_linked_corpus(self) -> None:
        linked_root = self.repo / "existing"
        linked_root.mkdir()
        (linked_root / "topic.md").write_text(
            "\n".join(
                (
                    "---",
                    'schema_version: "2.2"',
                    "doc_type: research-topic",
                    "parent_id: R-001",
                    "topic_id: RT-007",
                    "round_id: RR-001",
                    'title: "Existing topic"',
                    'author: "Researcher"',
                    "created: 2026-07-30",
                    "updated: 2026-07-30",
                    "---",
                    "",
                    "# RT-007 · Existing topic",
                    "",
                )
            ),
            encoding="utf-8",
        )
        self.new_research(
            "linked-topic-identities",
            "--corpus-root",
            "existing",
            "--entrypoint",
            "existing/topic.md",
        )

        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "managed-topic",
                "--title",
                "Managed topic",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.assertIn(
            "topic_id: RT-008",
            topic.read_text(encoding="utf-8"),
        )

    def test_topic_quality_blocks_review_ready_until_complete(self) -> None:
        research = self.new_research("topic-quality")
        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "cache-contract",
                "--title",
                "Cache contract",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        synthesis = research.parent / "SYNTHESIS.md"
        self.complete_placeholders(research)
        self.complete_placeholders(synthesis)
        self.replace_section(
            research,
            "Research Questions",
            "\n".join(
                (
                    "| ID | Status | Question | Answer or disposition | Evidence |",
                    "|---|---|---|---|---|",
                    "| RQ-001 | answered | Which contract works? | "
                    "The stable contract works. | `notes/cache-contract.md` |",
                )
            ),
        )

        denied = self.run_cli("mark-review-ready", "R-001", expected=2)
        self.assertIn("structured topic quality", denied.stderr)
        self.assertIn("required topic placeholders remain", denied.stderr)

        self.complete_topic(topic)
        topic.write_text(
            topic.read_text(encoding="utf-8").replace(
                "> **置信度：** High",
                "> **置信度：** Certain",
                1,
            ),
            encoding="utf-8",
        )
        uncalibrated_brief = self.run_cli(
            "mark-review-ready",
            "R-001",
            expected=2,
        )
        self.assertIn(
            "decision brief confidence must start with",
            uncalibrated_brief.stderr,
        )

        self.complete_topic(topic)
        self.replace_section(
            topic,
            "从独立实现与测试推导契约稳定性",
            "\n".join(
                (
                    "<!-- topic-role: analysis -->",
                    "",
                    "### 契约稳定（A-001）",
                    "",
                    "E-001.",
                )
            ),
        )
        shallow_analysis = self.run_cli(
            "mark-review-ready",
            "R-001",
            expected=2,
        )
        self.assertIn(
            "A-001 needs explanatory analysis",
            shallow_analysis.stderr,
        )

        self.complete_topic(topic)
        topic.write_text(
            topic.read_text(encoding="utf-8").replace(
                "registered as E-001",
                "registered in the evidence index",
                1,
            ),
            encoding="utf-8",
        )
        missing_evidence_link = self.run_cli(
            "mark-review-ready",
            "R-001",
            expected=2,
        )
        self.assertIn(
            "A-001 must cite at least one E-NNN",
            missing_evidence_link.stderr,
        )

        self.complete_topic(topic)
        review_ready = Path(
            self.run_cli("mark-review-ready", "R-001").stdout.strip()
        )
        self.assertEqual(review_ready.name, "SYNTHESIS.md")
        self.assertEqual(list((research.parent / "snapshots").iterdir()), [])
        snapshot = Path(
            self.run_cli(
                "mark-review-ready",
                "R-001",
                "--snapshot",
            ).stdout.strip()
        )
        self.assertEqual(snapshot.name, "synthesis-v001.md")
        self.run_cli("validate")

        completed = self.conclude_research()
        sealed_manifest = json.loads(
            (completed.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        sealed_topic = next(
            item
            for item in sealed_manifest["documents"]
            if item["path"] == "notes/cache-contract.md"
        )
        self.assertEqual(sealed_topic["role"], "topic")
        self.assertEqual(sealed_topic["topic_id"], "RT-001")
        self.assertTrue(
            (completed.parent / "notes" / "cache-contract.md").is_file()
        )
        self.run_cli("validate")

    def test_learning_topic_rejects_unknown_evidence_reference(self) -> None:
        self.new_research("unknown-topic-evidence")
        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "unknown-evidence",
                "--title",
                "Unknown evidence",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.complete_topic(topic)
        topic.write_text(
            topic.read_text(encoding="utf-8").replace(
                "registered as E-001",
                "registered as E-999",
                1,
            ),
            encoding="utf-8",
        )
        self.run_cli("sync-research", "R-001")

        denied = self.run_cli("validate", expected=1)
        self.assertIn(
            "A-001 cites unknown evidence E-999",
            denied.stderr,
        )

    def test_learning_topic_role_order_is_independent_of_titles(self) -> None:
        self.new_research("topic-role-order")
        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "role-order",
                "--title",
                "Role order",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.complete_topic(topic)
        text = topic.read_text(encoding="utf-8")
        text = text.replace(
            "topic-role: alternatives",
            "topic-role: temporary-role",
            1,
        )
        text = text.replace(
            "topic-role: implications",
            "topic-role: alternatives",
            1,
        )
        text = text.replace(
            "topic-role: temporary-role",
            "topic-role: implications",
            1,
        )
        topic.write_text(text, encoding="utf-8")
        self.run_cli("sync-research", "R-001")

        denied = self.run_cli("validate", expected=1)
        self.assertIn(
            "required topic roles are out of order",
            denied.stderr,
        )

    def test_complete_legacy_schema_1_topic_remains_reviewable(self) -> None:
        research = self.new_research("legacy-topic")
        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "legacy-contract",
                "--title",
                "Legacy contract",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.convert_topic_to_complete_v1(topic)

        synthesis = research.parent / "SYNTHESIS.md"
        self.complete_placeholders(research)
        self.complete_placeholders(synthesis)
        self.replace_section(
            research,
            "Research Questions",
            "\n".join(
                (
                    "| ID | Status | Question | Answer or disposition | Evidence |",
                    "|---|---|---|---|---|",
                    "| RQ-001 | answered | Which contract works? | "
                    "The legacy contract works. | "
                    "`notes/legacy-contract.md` |",
                )
            ),
        )

        review_ready = Path(
            self.run_cli("mark-review-ready", "R-001").stdout.strip()
        )
        self.assertEqual(review_ready.name, "SYNTHESIS.md")
        self.assertIn(
            'schema_version: "1"',
            topic.read_text(encoding="utf-8"),
        )
        self.run_cli("validate")

    def test_complete_legacy_schema_2_topic_remains_reviewable(self) -> None:
        research = self.new_research("legacy-claim-topic")
        topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "legacy-claim-contract",
                "--title",
                "Legacy claim contract",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.convert_topic_to_complete_v2(topic)

        synthesis = research.parent / "SYNTHESIS.md"
        self.complete_placeholders(research)
        self.complete_placeholders(synthesis)
        self.replace_section(
            research,
            "Research Questions",
            "\n".join(
                (
                    "| ID | Status | Question | Answer or disposition | Evidence |",
                    "|---|---|---|---|---|",
                    "| RQ-001 | answered | Which contract works? | "
                    "The claim-card contract works. | "
                    "`notes/legacy-claim-contract.md` |",
                )
            ),
        )

        review_ready = Path(
            self.run_cli("mark-review-ready", "R-001").stdout.strip()
        )
        self.assertEqual(review_ready.name, "SYNTHESIS.md")
        self.assertIn(
            'schema_version: "2"',
            topic.read_text(encoding="utf-8"),
        )
        self.run_cli("validate")

    def test_new_topic_rejects_unknown_question_without_mutation(self) -> None:
        research = self.new_research("unknown-topic-question")

        denied = self.run_cli(
            "new-topic",
            "R-001",
            "--slug",
            "invalid-question",
            "--title",
            "Invalid question",
            "--question",
            "RQ-999",
            expected=2,
        )

        self.assertIn("unknown Research Questions: RQ-999", denied.stderr)
        self.assertEqual(list((research.parent / "notes").iterdir()), [])
        round_text = (
            research.parent / "rounds" / "rr-001_baseline.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("invalid-question.md", round_text)

    def test_review_ready_never_concludes_without_explicit_approval(self) -> None:
        research = self.new_research("approval-gate")
        self.prepare_for_conclusion(research)

        controller = research.read_text(encoding="utf-8")
        synthesis = (research.parent / "SYNTHESIS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("status: active", controller)
        self.assertIn("maturity: review_ready", controller)
        self.assertIn("status: review_ready", synthesis)
        self.assertEqual(
            list((research.parent / "snapshots").iterdir()),
            [],
        )

        denied = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "concluded",
            expected=2,
        )
        self.assertIn("--approved-by", denied.stderr)
        self.assertTrue(research.is_file())
        self.assertEqual(
            list(
                (self.repo / "docs" / "research" / "completed").glob(
                    "r-001_*"
                )
            ),
            [],
        )

        completed = self.conclude_research()
        completed_text = completed.read_text(encoding="utf-8")
        self.assertIn("status: concluded", completed_text)
        self.assertTrue(
            (
                completed.parent / "snapshots" / "synthesis-v001.md"
            ).is_file()
        )
        self.assertIn('approved_by: "Test Research Owner"', completed_text)
        self.assertIn(
            'approval_ref: "test:explicit-owner-approval"', completed_text
        )

    def test_review_ready_reopens_as_another_round(self) -> None:
        research = self.new_research("iterative")
        self.prepare_for_conclusion(research)
        self.run_cli("mark-review-ready", "R-001", "--snapshot")
        first_snapshot = research.parent / "snapshots" / "synthesis-v001.md"
        first_snapshot_text = first_snapshot.read_text(encoding="utf-8")

        second_round = Path(
            self.run_cli(
                "new-round",
                "R-001",
                "--slug",
                "http-security",
                "--title",
                "HTTP security deep dive",
                "--author",
                "Security Reviewer",
            ).stdout.strip()
        )
        controller = research.read_text(encoding="utf-8")
        synthesis = (research.parent / "SYNTHESIS.md").read_text(
            encoding="utf-8"
        )
        first_round = research.parent / "rounds" / "rr-001_baseline.md"

        self.assertTrue(second_round.is_file())
        self.assertIn("current_round: RR-002", controller)
        self.assertIn("maturity: evidence_building", controller)
        self.assertIn("| RR-002 | HTTP security deep dive | active |", controller)
        self.assertIn("status: draft", synthesis)
        self.assertIn("status: completed", first_round.read_text(encoding="utf-8"))
        self.assertEqual(
            first_snapshot.read_text(encoding="utf-8"),
            first_snapshot_text,
        )
        self.run_cli("validate")

        second_review = Path(
            self.run_cli("mark-review-ready", "R-001").stdout.strip()
        )
        self.assertEqual(second_review.name, "SYNTHESIS.md")
        controller = research.read_text(encoding="utf-8")
        self.assertIn("maturity: review_ready", controller)
        self.assertIn('synthesis_revision: "2"', controller)
        self.assertIn("| RR-002 | HTTP security deep dive | completed |", controller)
        self.assertFalse(
            (research.parent / "snapshots" / "synthesis-v002.md").exists()
        )
        deduplicated = Path(
            self.run_cli(
                "mark-review-ready",
                "R-001",
                "--snapshot",
            ).stdout.strip()
        )
        self.assertEqual(deduplicated, first_snapshot)
        self.assertEqual(
            [path.name for path in (research.parent / "snapshots").iterdir()],
            ["synthesis-v001.md"],
        )
        self.run_cli("validate")

    def test_sparse_snapshot_revision_gaps_are_valid(self) -> None:
        research = self.new_research("sparse-snapshots")
        self.prepare_for_conclusion(research)
        self.run_cli(
            "new-round",
            "R-001",
            "--slug",
            "changed-conclusion",
            "--title",
            "Re-evaluate the conclusion",
        )
        synthesis = research.parent / "SYNTHESIS.md"
        self.replace_section(
            synthesis,
            "Executive Conclusion",
            "The second review has a materially different conclusion.",
        )

        snapshot = Path(
            self.run_cli(
                "mark-review-ready",
                "R-001",
                "--snapshot",
            ).stdout.strip()
        )

        self.assertEqual(snapshot.name, "synthesis-v002.md")
        self.assertFalse(
            (research.parent / "snapshots" / "synthesis-v001.md").exists()
        )
        self.assertTrue(snapshot.is_file())
        self.run_cli("validate")

    def test_review_snapshot_tampering_survives_manifest_refresh_detection(
        self,
    ) -> None:
        research = self.new_research("review-snapshot")
        self.prepare_for_conclusion(research)
        self.run_cli("mark-review-ready", "R-001", "--snapshot")
        snapshot = research.parent / "snapshots" / "synthesis-v001.md"
        snapshot.write_text(
            snapshot.read_text(encoding="utf-8").replace(
                "## Executive Conclusion",
                "Tampered review content.\n\n## Executive Conclusion",
            ),
            encoding="utf-8",
        )

        self.run_cli("sync-research", "R-001")
        result = self.run_cli("validate", expected=1)

        self.assertIn("review_ready Synthesis payload changed", result.stderr)

    def test_unassigned_owner_blocks_conclusion(self) -> None:
        research = self.new_research("unowned", "--owner", "")
        self.prepare_for_conclusion(research)

        denied = self.run_cli(
            "conclude-research",
            "R-001",
            "--approved-by",
            "Someone",
            "--approval-ref",
            "test:no-owner",
            expected=2,
        )

        self.assertIn("assigned owner", denied.stderr)
        self.assertTrue(research.is_file())

    def test_controller_contract_paths_cannot_traverse(self) -> None:
        research = self.new_research("unsafe-controller")
        text = research.read_text(encoding="utf-8")
        research.write_text(
            text.replace(
                "manifest: RESEARCH_MANIFEST.json",
                "manifest: ../../escape.json",
            ),
            encoding="utf-8",
        )

        validated = self.run_cli("validate", expected=1)
        archived = self.run_cli(
            "archive-research",
            "R-001",
            "--outcome",
            "cancelled",
            "--reason",
            "Unsafe fixture.",
            "--approved-by",
            "Test Research Owner",
            "--approval-ref",
            "test:explicit-owner-approval",
            expected=2,
        )

        self.assertIn("manifest must be RESEARCH_MANIFEST.json", validated.stderr)
        self.assertIn("manifest must be RESEARCH_MANIFEST.json", archived.stderr)

    def test_linked_corpus_keeps_entrypoint_and_source_in_place(self) -> None:
        corpus = self.repo / "existing" / "research"
        corpus.mkdir(parents=True)
        index = corpus / "index.md"
        topic = corpus / "topic.md"
        index.write_text("# Index\n\n[Topic](./topic.md)\n", encoding="utf-8")
        topic.write_text("# Topic\n", encoding="utf-8")

        research = self.new_research(
            "linked",
            "--corpus-root",
            str(corpus),
            "--entrypoint",
            "existing/research/index.md",
        )
        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["mode"], "linked")
        self.assertEqual(len(manifest["documents"]), 3)
        entrypoints = [
            item for item in manifest["documents"] if item["role"] == "entrypoint"
        ]
        self.assertEqual(entrypoints[0]["path"], "existing/research/index.md")
        self.assertTrue(index.exists())
        self.run_cli("validate")

        # Simulate a schema 1.1 linked package created before package-local
        # notes became a default manifest root.
        manifest["roots"] = [
            root
            for root in manifest["roots"]
            if not (
                root.get("base") == "package"
                and root.get("path") == "notes"
            )
        ]
        (research.parent / "RESEARCH_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        self.run_cli("validate")

        structured_topic = Path(
            self.run_cli(
                "new-topic",
                "R-001",
                "--slug",
                "linked-corpus-gap",
                "--title",
                "Linked corpus gap",
                "--question",
                "RQ-001",
            ).stdout.strip()
        )
        self.assertEqual(structured_topic.parent, research.parent / "notes")
        refreshed = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        topic_record = next(
            item
            for item in refreshed["documents"]
            if item["path"] == "notes/linked-corpus-gap.md"
        )
        self.assertEqual(topic_record["base"], "package")
        self.assertEqual(topic_record["role"], "topic")
        self.assertEqual(topic_record["topic_id"], "RT-001")
        self.assertTrue(
            any(
                root.get("base") == "package"
                and root.get("path") == "notes"
                for root in refreshed["roots"]
            )
        )
        self.run_cli("validate")

    def test_linked_corpus_supports_multiple_roots_and_entrypoints(self) -> None:
        first = self.repo / "research" / "request"
        second = self.repo / "research" / "storage"
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        (first / "index.md").write_text("# Request\n", encoding="utf-8")
        (first / "contract.md").write_text("# Contract\n", encoding="utf-8")
        (second / "index.md").write_text("# Storage\n", encoding="utf-8")

        research = self.new_research(
            "multi-root",
            "--corpus-root",
            "research/request",
            "--corpus-root",
            "research/storage",
            "--entrypoint",
            "research/request/index.md",
            "--entrypoint",
            "research/storage/index.md",
        )
        manifest = json.loads(
            (research.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(len(manifest["roots"]), 5)
        self.assertEqual(len(manifest["entrypoints"]), 2)
        self.assertEqual(len(manifest["documents"]), 4)
        self.assertEqual(
            sum(item["role"] == "entrypoint" for item in manifest["documents"]),
            2,
        )
        self.run_cli("validate")

    def test_missing_markdown_and_input_document_references_are_errors(self) -> None:
        corpus = self.repo / "corpus"
        corpus.mkdir()
        (corpus / "index.md").write_text(
            "---\n"
            "inputDocuments:\n"
            "  - corpus/missing-input.md\n"
            "---\n\n"
            "# Index\n\n[Missing](./missing-link.md)\n",
            encoding="utf-8",
        )
        self.new_research(
            "broken",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )

        result = self.run_cli("validate", expected=1)

        self.assertIn("missing Markdown target", result.stderr)
        self.assertIn("missing inputDocuments target", result.stderr)

    def test_absolute_input_document_is_a_portability_warning(self) -> None:
        corpus = self.repo / "corpus"
        corpus.mkdir()
        source = self.repo / "source.md"
        source.write_text("# Source\n", encoding="utf-8")
        (corpus / "index.md").write_text(
            "---\n"
            "inputDocuments:\n"
            f"  - {source}\n"
            "---\n\n# Index\n",
            encoding="utf-8",
        )
        self.new_research(
            "portable",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )

        result = self.run_cli("validate")

        self.assertIn("not portable", result.stderr)
        self.assertIn('"warnings": 3', result.stdout)

    def test_linked_conclusion_snapshots_and_detects_tampering(self) -> None:
        corpus = self.repo / "corpus"
        corpus.mkdir()
        source = corpus / "index.md"
        source.write_text("# Stable evidence\n", encoding="utf-8")
        research = self.new_research(
            "snapshot",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )
        self.prepare_for_conclusion(research)

        completed = self.conclude_research()
        manifest_path = completed.parent / "RESEARCH_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        snapshotted_source = next(
            item for item in manifest["documents"] if item.get("source_path")
        )
        snapshot = completed.parent / snapshotted_source["path"]

        self.assertEqual(manifest["status"], "sealed")
        self.assertEqual(manifest["mode"], "snapshot")
        self.assertRegex(manifest["payload_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(snapshot.is_file())
        self.assertTrue(source.is_file())
        self.run_cli("validate")

        snapshot.write_text("# Tampered\n", encoding="utf-8")
        tampered = self.run_cli("validate", expected=1)
        self.assertIn("sealed document digest changed", tampered.stderr)

    def test_sealed_snapshot_replaced_by_symlink_is_rejected_by_both_tools(
        self,
    ) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unsupported")
        corpus = self.repo / "corpus"
        corpus.mkdir()
        source = corpus / "index.md"
        source.write_text("# Stable evidence\n", encoding="utf-8")
        research = self.new_research(
            "snapshot-symlink",
            "--corpus-root",
            "corpus",
            "--entrypoint",
            "corpus/index.md",
        )
        self.prepare_for_conclusion(research)
        completed = self.conclude_research()
        manifest = json.loads(
            (completed.parent / "RESEARCH_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        snapshotted_source = next(
            item for item in manifest["documents"] if item.get("source_path")
        )
        snapshot = completed.parent / snapshotted_source["path"]
        replacement = self.repo / "replacement.md"
        replacement.write_bytes(snapshot.read_bytes())
        snapshot.unlink()
        os.symlink(replacement, snapshot)

        producer = self.run_cli("validate", expected=1)
        consumer = self.run_epctl("validate", expected=1)

        self.assertIn("symbolic link", producer.stderr)
        self.assertIn("symbolic link", consumer.stderr)

    def test_managed_conclusion_seals_in_place(self) -> None:
        research = self.new_research("managed-conclusion")
        note = research.parent / "notes" / "result.md"
        note.write_text("# Result\n", encoding="utf-8")
        self.run_cli("sync-research", "R-001")
        self.prepare_for_conclusion(research)

        completed = self.conclude_research()
        manifest = json.loads(
            (completed.parent / "RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["mode"], "managed")
        self.assertEqual(manifest["status"], "sealed")
        self.assertTrue((completed.parent / "notes" / "result.md").is_file())
        self.run_cli("validate")

    def test_outside_repository_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            result = self.run_cli(
                "new-research",
                "--slug",
                "outside",
                "--title",
                "Outside",
                "--corpus-root",
                outside,
                expected=2,
            )
            self.assertIn("escapes repository", result.stderr)

        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unsupported")
        corpus = self.repo / "corpus"
        corpus.mkdir()
        target = self.repo / "target.md"
        target.write_text("# Target\n", encoding="utf-8")
        os.symlink(target, corpus / "linked.md")
        result = self.run_cli(
            "new-research",
            "--slug",
            "symlink",
            "--title",
            "Symlink",
            "--corpus-root",
            "corpus",
            expected=2,
        )
        self.assertIn("symbolic link", result.stderr)

    def test_cancelled_research_requires_reason(self) -> None:
        research = self.new_research("cancelled")
        missing = self.run_cli("cancel-research", "R-001", expected=2)
        self.assertIn("--reason", missing.stderr)

        completed = Path(
            self.run_cli(
                "cancel-research",
                "R-001",
                "--reason",
                "The premise was withdrawn.",
                "--approved-by",
                "Test Research Owner",
                "--approval-ref",
                "test:explicit-owner-approval",
            ).stdout.strip()
        )
        self.assertTrue(completed.is_file())
        self.assertFalse(research.exists())
        self.run_cli("validate")

    def test_epctl_consumes_researchctl_conclusion(self) -> None:
        research = self.new_research("contract")
        note = research.parent / "notes" / "result.md"
        note.write_text("# Result\n", encoding="utf-8")
        self.run_cli("sync-research", "R-001")
        self.prepare_for_conclusion(research)
        completed = self.conclude_research()

        adr = Path(
            self.run_epctl(
                "new-adr",
                "--slug",
                "contract-choice",
                "--title",
                "Contract choice",
                "--research",
                "R-001",
            ).stdout.strip()
        )
        self.complete_placeholders(adr)
        self.run_epctl(
            "decide-adr",
            "ADR-001",
            "--outcome",
            "accepted",
            "--decision-maker",
            "Test Decision Owner",
        )
        plan = Path(
            self.run_epctl(
                "new-ep",
                "--slug",
                "implement-contract",
                "--title",
                "Implement contract",
                "--research",
                "R-001",
                "--adr",
                "ADR-001",
            ).stdout.strip()
        )

        self.assertTrue(adr.is_file())
        self.assertTrue(plan.is_file())

        manifest_path = completed.parent / "RESEARCH_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["documents"][0]["bytes"] += 1
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tampered = self.run_epctl("validate", expected=1)
        self.assertIn("sealed Research manifest payload changed", tampered.stderr)

    def test_epctl_rejects_unsealed_manifest_for_concluded_research(self) -> None:
        research = self.new_research("unsealed-contract")
        note = research.parent / "notes" / "result.md"
        note.write_text("# Result\n", encoding="utf-8")
        self.run_cli("sync-research", "R-001")
        self.prepare_for_conclusion(research)
        completed = self.conclude_research()
        manifest_path = completed.parent / "RESEARCH_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "active"
        manifest["payload_sha256"] = ""
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        rejected = self.run_epctl(
            "new-adr",
            "--slug",
            "unsealed-choice",
            "--title",
            "Unsealed choice",
            "--research",
            "R-001",
            expected=2,
        )

        self.assertIn("must be valid and concluded", rejected.stderr)

    def test_researchctl_accepts_legacy_package_without_manifest(self) -> None:
        legacy = self.run_epctl(
            "new-research",
            "--slug",
            "legacy",
            "--title",
            "Legacy research",
        )

        self.assertTrue(Path(legacy.stdout.strip()).is_file())
        validated = self.run_cli("validate")
        self.assertNotIn("Missing Research manifest", validated.stderr)


if __name__ == "__main__":
    unittest.main()
