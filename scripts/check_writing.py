#!/usr/bin/env python3
"""Read-only RF prose hints; never a truth, approval, or standards-conformance gate.

Only explicit UTF-8 Markdown/text files are read. No directory traversal, network,
model call, source mutation, or autofix. Findings return 0; input/tool errors return
2. Markdown handling is conservative, not a complete CommonMark parser.
Semantic fidelity remains a separate author review defined by the writing guide.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
from typing import NamedTuple

VERSION = "2"
MAX_BYTES = 1024 * 1024
CJK = r"[\u3400-\u4dbf\u4e00-\u9fff]"
CJK_RE = re.compile(CJK)


class Rule(NamedTuple):
    identifier: str
    pattern: str
    message: str


ZH_RULES = (
    Rule(
        "CW-ZH-ACTION",
        r"(?:进行|实施)(?:校验|验证|检查|迁移|恢复|更新)",
        "Check whether a direct verb is clearer without changing the actor or scope.",
    ),
    Rule(
        "CW-ZH-SCOPE",
        r"适当|若干|较为|基本上|一定程度上",
        "Check whether the source provides a more exact condition or scope.",
    ),
    Rule(
        "CW-ZH-REFERENCE",
        r"(?:该|其)(?:组件|模块|流程|状态|对象)",
        "Check whether the reference has exactly one possible antecedent.",
    ),
)
EN_RULES = (
    Rule(
        "CW-EN-ACTION",
        r"\b(?:perform|conduct) (?:a|an|the) (?:validation|inspection|comparison)\b",
        "Consider a direct verb only if it preserves scope and authority.",
    ),
    Rule(
        "CW-EN-SCOPE",
        r"\b(?:appropriate|various|basically)\b",
        "Check whether the source provides a more exact condition or scope.",
    ),
    Rule(
        "CW-EN-SUBJECT",
        r"\b(?:it is|there is|there are)\b",
        "Check whether naming the actor clarifies the sentence; do not invent one.",
    ),
)


def blank(match: re.Match[str]) -> str:
    return "".join("\n" if c == "\n" else " " for c in match.group())


def protect(text: str) -> str:
    """Mask non-prose while retaining exact character/line positions."""
    # Comments may span lines. Protected content never becomes a review hint.
    text = re.sub(r"<!--.*?(?:-->|\Z)", blank, text, flags=re.S)
    # Exact-length closing backticks; code spans can cross a source line.
    text = re.sub(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", blank, text, flags=re.S)
    text = re.sub(r'https?://[^\s<>]+', blank, text)
    # Keep link labels, not link targets/titles (including nested parentheses).
    chars = list(text)
    i = 0
    while i < len(text) - 1:
        if text[i:i + 2] != "](":
            i += 1
            continue
        start = i + 1
        depth = 1
        i += 2
        while i < len(text) and depth:
            if text[i] == "\\":
                i += 2
                continue
            depth += (text[i] == "(") - (text[i] == ")")
            i += 1
        for pos in range(start, min(i, len(chars))):
            if chars[pos] != "\n":
                chars[pos] = " "
    text = "".join(chars)
    # Quotations are source material, not permission to rewrite the quotation.
    return re.sub(r'“[^”]*”|「[^」]*」|"[^"\n]*"', blank, text)


def prose_lines(text: str) -> list[str]:
    """Preserve line numbering; skip metadata, quotes, code and HTML blocks."""
    result: list[str] = []
    fence: tuple[str, int] | None = None
    frontmatter = False
    html_block = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.lstrip()
        if number == 1 and line == "---":
            frontmatter = True
            result.append("")
            continue
        if frontmatter:
            if line in ("---", "..."):
                frontmatter = False
            result.append("")
            continue
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw)
        if fence:
            if (marker and marker[1][0] == fence[0]
                    and len(marker[1]) >= fence[1] and not marker[2].strip()):
                fence = None
            result.append("")
            continue
        if marker:
            fence = (marker[1][0], len(marker[1]))
            result.append("")
            continue
        if re.match(r"^<[A-Za-z/!]", line):
            html_block = True
        if html_block:
            if not line:
                html_block = False
            result.append("")
            continue
        if (raw.startswith(("    ", "\t")) or line.startswith(">")
                or re.match(r"^\[[^\]]+\]:", line)
                or re.match(r"^\|?[ \t]*:?-{3,}", line)):
            result.append("")
            continue
        result.append(raw)
    return protect("\n".join(result)).split("\n")


def parse_range(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)", value)
    if not match or int(match[1]) > int(match[2]):
        raise argparse.ArgumentTypeError("Use an inclusive positive START:END range")
    return int(match[1]), int(match[2])


def selected(number: int, ranges: list[tuple[int, int]]) -> bool:
    return not ranges or any(start <= number <= end for start, end in ranges)


def review(text: str, lang: str, ranges: list[tuple[int, int]]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for number, line in enumerate(prose_lines(text), 1):
        if not selected(number, ranges):
            continue
        language = ("zh" if CJK_RE.search(line) else "en") if lang == "auto" else lang
        rules = ZH_RULES if language == "zh" else EN_RULES
        for rule in rules:
            for match in re.finditer(rule.pattern, line, re.I):
                findings.append({"line": number, "column": match.start() + 1,
                                 "rule": rule.identifier, "kind": "review",
                                 "match": match.group(), "message": rule.message})
    return sorted(findings, key=lambda x: (x["line"], x["column"], x["rule"]))


def read_source(path: Path) -> bytes:
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Not a regular file: {path}")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"File exceeds {MAX_BYTES} bytes: {path}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--lang", choices=("auto", "en", "zh"), default="auto")
    parser.add_argument("--json", action="store_true", help="Print source-bound JSON")
    parser.add_argument("--line-range", action="append", type=parse_range, default=[],
                        help="Check explicit inclusive lines of one file; repeatable")
    args = parser.parse_args(argv)
    if args.line_range and len(args.files) != 1:
        parser.error("--line-range requires exactly one file")
    documents = []
    try:
        # Complete all reads before printing; an input error is not a clean scan.
        for path in args.files:
            raw = read_source(path)
            text = raw.decode("utf-8")
            if any(end > len(text.splitlines()) for _, end in args.line_range):
                raise ValueError(f"Line range exceeds file length: {path}")
            documents.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                              "line_ranges": args.line_range,
                              "findings": review(text, args.lang, args.line_range)})
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "input_error", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    report = {"schema_version": 1, "tool_version": VERSION, "status": "review_hints_only",
              "language": args.lang, "source_files_modified": False,
              "semantic_verification": "not_performed", "documents": documents,
              "limitations": ["No truth, terminology, authority, accessibility, or standards verdict.",
                              "Markdown masking is conservative and may omit prose.",
                              "A clean scan does not compare source and rewritten meaning."]}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for document in documents:
            print(f"{document['path']} sha256={document['sha256']}")
            for finding in document["findings"]:
                print(f"  {finding['line']}:{finding['column']} {finding['rule']} "
                      f"[{finding['kind']}] {finding['message']}")
        print("Review hints only; no semantic verification. Files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
