"""Source-backed, isolated replay of memory cooling across actual Core events.

Run: python3 -B -m tests.test_memory_cooling_evaluation --json
The source checkout is read-only; only a temporary bootstrapped target is used.
This tests router context, not agent answer quality or token use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import time
import unittest
from pathlib import Path

from tests.test_spec_router import SpecRouterTestCase

ROOT = Path(__file__).resolve().parents[1]
REAL_EPS = {
    "EP-006": "docs/exec-plans/active/ep-006_migrate-to-repo-foundry/EXECPLAN.md",
    "EP-058": "docs/exec-plans/active/ep-058_implement-engineering-design-skill/EXECPLAN.md",
    "EP-094": "docs/exec-plans/active/ep-094_recover-born-invalid-checkpoint-seals/EXECPLAN.md",
}
BACKGROUND = ["EP-006", "EP-058"]
STAMP = "2026-10-29T00:00:00Z"
CAPSULE_MARKER = "Exact activation capsule rehydrated for this context epoch:\n\n"


def evaluate(*, repetitions=2):
    """Run representative tasks through a real installed Core with real EP bytes."""
    if type(repetitions) is not int or not 1 <= repetitions <= 8:
        raise ValueError("repetitions must be 1..8")
    fixture = SpecRouterTestCase(methodName="runTest")
    fixture.setUp()
    repo = fixture.repo
    config = repo / ".repo-foundry/memory-context.json"
    try:
        files = []
        for relative in REAL_EPS.values():
            original = ROOT / relative
            if not original.is_file() or original.is_symlink():
                raise AssertionError("Real EP source unavailable: " + relative)
            copied = repo / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, copied)
            files.append(copied)
        files.extend((repo / "docs/.engineering/specs.lock.json", repo / "service/main.go"))
        checksums = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

        def set_mode(mode, invalid_report=False):
            if config.exists():
                config.unlink()
            if mode != "off":
                data = {"schema_version": 1, "mode": mode, "background_ep": BACKGROUND}
                if invalid_report:
                    data["review_report"] = ".repo-foundry/no-review.json"
                config.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

        def event(kind, session, prompt=""):
            response = json.loads(fixture.run_core("event", stdin={
                "protocol_version": 2, "adapter_id": "codex",
                "session_id": session, "turn_id": "eval-turn",
                "event": kind, "prompt": prompt, "memory_as_of": STAMP,
            }).stdout)
            if response["decision"] != "allow":
                raise AssertionError("Core rejected a valid replay")
            plan = response["context_plan"]
            if plan["used_bytes"] > plan["budget_bytes"]:
                raise AssertionError("Non-normative budget exceeded")
            return response

        def measure(mode, kind, session, prompt=""):
            set_mode(mode)
            timings, values = [], []
            # Resume and subagent events deliberately advance the context epoch.
            count = repetitions if kind == "session_start" else 1
            for _ in range(count):
                start = time.perf_counter_ns()
                response = event(kind, session, prompt)
                timings.append((time.perf_counter_ns() - start) / 1_000_000)
                values.append(response)
            if any(v["context"] != values[0]["context"] for v in values[1:]):
                raise AssertionError("Non-deterministic same-source session replay")
            response = values[0]
            memory = response["context_plan"].get("memory", {})
            row = {
                "context_bytes": len(response["context"].encode("utf-8")),
                "routing_bytes": response["context_plan"]["used_bytes"],
                "median_cli_ms": round(statistics.median(timings), 3),
                "timed_events": count,
                "status": memory.get("status", "not_configured"),
                "configured_saved_bytes": memory.get("saved_bytes", 0),
            }
            return response, row

        report = {}
        def compare(name, prompt):
            values, rows = {}, {}
            for mode in ("off", "shadow", "opt-in"):
                values[mode], rows[mode] = measure(
                    mode, "session_start", "eval-" + name, prompt,
                )
            original = values["off"]["context"]
            if not all(values[m]["context"].startswith(original) for m in ("shadow", "opt-in")):
                raise AssertionError("Protected original Core context was changed")
            if rows["shadow"]["context_bytes"] <= rows["off"]["context_bytes"]:
                raise AssertionError("Configured background was not loaded")
            if rows["opt-in"]["context_bytes"] > rows["shadow"]["context_bytes"]:
                raise AssertionError("Cooling increased configured context")
            if rows["opt-in"]["configured_saved_bytes"] <= 0:
                raise AssertionError("No configured-background savings")
            for mode in rows:
                rows[mode]["delta_vs_off_bytes"] = (
                    rows[mode]["context_bytes"] - rows["off"]["context_bytes"]
                )
            report[name] = {"modes": rows}
            return values

        bugfix = compare("bounded_bugfix", "Fix a small local bug in service/main.go")
        if "Current Snapshot for EP-006" not in bugfix["shadow"]["context"]:
            raise AssertionError("Real background EP missing from Shadow")
        if "Current Snapshot for EP-006" in bugfix["opt-in"]["context"]:
            raise AssertionError("Background text was not cooled")
        if "[ContextRef:memory-" not in bugfix["opt-in"]["context"]:
            raise AssertionError("No recoverable pointer in Opt-in")
        if bugfix["off"]["context_plan"].get("memory"):
            raise AssertionError("Unconfigured baseline unexpectedly used memory optimization")

        direct = compare("direct_plan", "Continue EP-094 and assess its next action")
        if not all("Current Snapshot for EP-094" in x["context"] for x in direct.values()):
            raise AssertionError("Explicit current EP omitted")

        compare("public_interface", "Change public service/main.go API with compatibility checks")
        session = "eval-public_interface"
        set_mode("off")
        denied = json.loads(fixture.run_core("event", stdin={
            "protocol_version": 2, "event": "before_mutation",
            "adapter_id": "codex", "session_id": session, "turn_id": "eval-turn",
            "tool": {"category": "file_write", "name": "patch",
                     "paths": ["service/main.go"], "input": {}},
        }).stdout)
        if denied["decision"] != "deny":
            raise AssertionError("Unactivated Governed write was not blocked")
        fixture.run_router("activate", "--session-id", session, "--turn-id", "eval-turn",
                           "--path", "service/main.go", "--spec", "languages/go")
        capsules = {}
        for mode in ("off", "shadow", "opt-in"):
            response, row = measure(mode, "context_resume", session)
            if CAPSULE_MARKER not in response["context"]:
                raise AssertionError("Activation capsule missing")
            capsules[mode] = response["context"].split(CAPSULE_MARKER, 1)[1]
            report["public_interface"].setdefault("activated_resume", {})[mode] = row
        if len(set(capsules.values())) != 1:
            raise AssertionError("Normative capsule differs across modes")
        report["public_interface"]["gate_denied_before_activation"] = True
        report["public_interface"]["capsule_identical_across_modes"] = True

        session = "eval-subagent"
        set_mode("off")
        event("session_start", session, "Fix bounded documentation")
        subagent_rows = {}
        for mode in ("off", "shadow", "opt-in"):
            response, row = measure(
                mode, "subagent_start", session, "Inspect EP-006 and EP-058 history",
            )
            subagent_rows[mode] = row
            if mode == "opt-in":
                if not all(f"Current Snapshot for {eid}" in response["context"] for eid in BACKGROUND):
                    raise AssertionError("New explicit subagent EP omitted")
                if any(x["tier"] != "direct" for x in response["context_plan"]["memory"]["selection"]):
                    raise AssertionError("Subagent EP treated as background")
                if "[ContextRef:memory-" in response["context"]:
                    raise AssertionError("Explicit subagent EP cooled")
        set_mode("opt-in")
        resumed = event("context_resume", session)
        if not all(f"Current Snapshot for {eid}" in resumed["context"] for eid in BACKGROUND):
            raise AssertionError("Explicit subagent EP not retained on Resume")
        report["subagent_handoff"] = {"modes": subagent_rows, "resume_preserved": True}

        session = "eval-fallback"
        set_mode("off")
        original = event("session_start", session, "Fix a small issue")
        set_mode("opt-in", invalid_report=True)
        fallback = event("session_start", session, "Fix a small issue")
        if original["context"] != fallback["context"]:
            raise AssertionError("Invalid optional report modified baseline")
        if fallback["context_plan"]["memory"]["status"] != "baseline_fallback":
            raise AssertionError("Invalid report did not trigger fallback")
        report["invalid_report"] = {"same_as_off": True, "reason":
                                    fallback["context_plan"]["memory"]["reason"]}

        if any(hashlib.sha256((repo / p).read_bytes()).hexdigest() != digest
               for p, digest in checksums.items()):
            raise AssertionError("One of the original EP/Spec/source files was mutated")
        return {
            "schema_version": 1,
            "scope": "temporary_installed_harness_real_repository_ep_snapshots",
            "ep_sources": sorted(REAL_EPS),
            "fixed_time": STAMP,
            "repetitions": repetitions,
            "source_bytes_unchanged": True,
            "scenarios": report,
            "limitations": [
                "CLI wall time is not a service latency SLA",
                "No model quality or token counts measured",
                "Savings are relative to configured shadow background, not necessarily off",
                "No automatic EP aging, ADR retirement, or Spec authority changes",
            ],
        }
    finally:
        fixture.tearDown()


class MemoryCoolingEffectivenessTest(unittest.TestCase):
    def test_isolated_real_ep_replay(self):
        output = evaluate(repetitions=1)
        self.assertTrue(output["source_bytes_unchanged"])
        self.assertTrue(output["scenarios"]["public_interface"]["capsule_identical_across_modes"])
        print("MEMORY_COOLING_EVALUATION " + json.dumps(output, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repetitions", type=int, default=3)
    arguments = parser.parse_args()
    if arguments.json:
        print(json.dumps(evaluate(repetitions=arguments.repetitions),
                         sort_keys=True, ensure_ascii=False, indent=2))
    else:
        print("Use --json for isolated cooling metrics.")
