#!/usr/bin/env python3
"""One-off evidence audit against pinned *real* apm-control-plane Go source.

Runs the released RepoHarnessKit Handoff/Receipt CLIs in an isolated runner.
No Agent/Chat session is invoked or simulated, and no business repository
push, release, or lifecycle action occurs.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

APM_COMMIT = "a0eae73f2ec10e9a28c00eb48e0a3593a69209f1"
SOURCE = "internal/config/java_sampling.go"
FOCUSED = ["go", "test", "./internal/config", "./internal/policy"]
NEEDLE = (
    "\tif rate == 0 {\n"
    "\t\trate = 0 // Canonicalize negative zero to the same configuration.\n"
    "\t}\n"
)
REGRESSION = "\t// EVAL-ONLY regression: negative zero canonicalization omitted.\n"
REPAIR = (
    "\tif rate == 0 {\n"
    "\t\trate = 0 // EVAL-ONLY repair: preserve canonical configuration bytes.\n"
    "\t}\n"
)


def run(args: list[str], *, cwd: Path | None = None, expected: int = 0) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(args, cwd=cwd, env=environment, text=True,
                            capture_output=True, timeout=180)
    if result.returncode != expected:
        raise RuntimeError(
            f"expected {expected}, got {result.returncode} for {args!r}:\n"
            f"stdout={result.stdout[-2000:]}\nstderr={result.stderr[-2000:]}"
        )
    return result


def json_cmd(args: list[str], *, expected: int = 0) -> dict:
    result = run(args, expected=expected)
    return json.loads(result.stdout)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 4:
        raise ValueError("usage: apm_handoff_audit.py <rhk checkout> <apm checkout> <output dir>")
    harness, repo, evidence = (Path(x).resolve(strict=True) if i < 2 else Path(x).resolve()
                               for i, x in enumerate(sys.argv[1:]))
    evidence.mkdir(parents=True, exist_ok=True)
    source = repo / SOURCE
    if run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip() != APM_COMMIT:
        raise RuntimeError("Unexpected APM revision")
    if run(["git", "-C", str(repo), "status", "--porcelain"]).stdout.strip():
        raise RuntimeError("APM checkout must start clean")
    baseline = source.read_text(encoding="utf-8")
    if baseline.count(NEEDLE) != 1:
        raise RuntimeError("Pinned APM source changed: missing exact canonicalization block")

    receipt_cli = [sys.executable, "-B", str(harness / "scripts/verification_receipt.py"),
                   "--repo", str(repo)]
    handoff_cli = [sys.executable, "-B", str(harness / "scripts/session_handoff.py"),
                   "--repo", str(repo)]
    receipt_before = evidence / "receipt-before.json"
    receipt_after = evidence / "receipt-after.json"
    handoff = evidence / "handoff-after-injection.json"

    # Execute ACTUAL focused Go tests against the real complete project.
    baseline_result = json_cmd(
        receipt_cli + ["run", "--path", SOURCE, "--output", str(receipt_before),
                       "--", *FOCUSED]
    )
    if baseline_result["outcome"] != "passed":
        raise RuntimeError("Focused Go baseline must pass before regression injection")
    baseline_check = json_cmd(receipt_cli + ["check", "--input", str(receipt_before)])
    if baseline_check["outcome"] != "passed":
        raise RuntimeError("Baseline receipt mismatch immediately after generation")

    # Create a real code regression AFTER the successful receipt.
    source.write_text(baseline.replace(NEEDLE, REGRESSION, 1), encoding="utf-8")
    if source.read_text() == baseline:
        raise RuntimeError("Regression injection had no effect")
    stale = json_cmd(receipt_cli + ["check", "--input", str(receipt_before)], expected=1)
    if stale["outcome"] != "stale" or "OBSERVED_BYTES_CHANGED" not in stale["reasons"]:
        raise RuntimeError("Receipt did not detect actual source mutation")

    # Show that the original Go contract catches the fault in the isolated runner.
    broken = run(FOCUSED, cwd=repo, expected=1)
    if "negative zero" not in (broken.stdout + broken.stderr).lower():
        raise RuntimeError("Go regression failed for an unexpected reason")

    capture = json_cmd(handoff_cli + [
        "capture",
        "--task", "Restore deterministic Java sampling -0 handling in the isolated APM source",
        "--next-action", "Inspect java_sampling.go, repair -0 canonicalization, run focused Go checks",
        "--path", SOURCE,
        "--evidence", "Focused Go test before injected regression: passed; old receipt is stale",
        "--output", str(handoff),
    ])
    resume = json_cmd(handoff_cli + [
        "resume", "--input", str(handoff), "--receipt", str(receipt_before)
    ], expected=1)
    if (resume["state"] != "matching_snapshot" or
        resume["verification_receipt"]["outcome"] != "stale" or
        resume["verification"] != "unknown"):
        raise RuntimeError("Handoff/Receipt integration misreported current source")

    # Demonstrate code recovery in the SAME runner without pretending an Agent B ran.
    source.write_text(baseline.replace(NEEDLE, REPAIR, 1), encoding="utf-8")
    after_result = json_cmd(
        receipt_cli + ["run", "--path", SOURCE, "--output", str(receipt_after),
                       "--", *FOCUSED]
    )
    if after_result["outcome"] != "passed":
        raise RuntimeError("Go tests did not pass after scripted repair")
    old_after_repair = json_cmd(
        receipt_cli + ["check", "--input", str(receipt_before)], expected=1
    )
    new_after_repair = json_cmd(receipt_cli + ["check", "--input", str(receipt_after)])
    stale_handoff = json_cmd(handoff_cli + ["resume", "--input", str(handoff)], expected=1)
    if (old_after_repair["outcome"] != "stale" or
        new_after_repair["outcome"] != "passed" or
        stale_handoff["state"] != "stale"):
        raise RuntimeError("Repair/receipt revision checks inconsistent")

    report = {
        "schema_version": 1,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "source_repo": "XiaoWeiKIN/apm-control-plane",
        "pinned_source_commit": APM_COMMIT,
        "product_repo": "XiaoWeiKIN/RepoHarnessKit",
        "scenario": "Java sampling negative-zero canonicalization; controlled, nonproduction regression",
        "initial_source_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
        "injected_source_sha256": hashlib.sha256(
            baseline.replace(NEEDLE, REGRESSION, 1).encode()).hexdigest(),
        "after_repair_source_sha256": digest(source),
        "baseline_go_test": baseline_result["outcome"],
        "regression_go_test_failed_as_expected": broken.returncode == 1,
        "old_receipt_after_mutation": stale["outcome"],
        "old_receipt_reason_codes": stale["reasons"],
        "handoff_at_interruption": resume["state"],
        "receipt_at_interruption": resume["verification_receipt"]["outcome"],
        "repaired_go_test": after_result["outcome"],
        "old_receipt_after_repair": old_after_repair["outcome"],
        "new_receipt_after_repair": new_after_repair["outcome"],
        "handoff_after_repair": stale_handoff["state"],
        "model_executions": 0,
        "independent_chat_sessions": 0,
        "chatgpt_success_rate": None,
        "limitations": [
            "This is a scripted integration audit on a real Go project, NOT a model A/B trial.",
            "Only two focused Go packages tested; external databases and full CI not assessed.",
            "No business repo branch or main commit is written.",
            "The injected source regression is synthetic; the surrounding source and Go tests are real.",
            "Receipt source digests do not establish model behavior or human authority.",
        ],
    }
    output = evidence / "audit-result.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print("APM_REAL_REPO_HANDOFF_AUDIT " + json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("apm-handoff-audit: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
