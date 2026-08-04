from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.spec_git_fixture import create_git_catalog, git


ROOT = Path(__file__).resolve().parents[1]
FOUNDRYCTL = ROOT / "scripts" / "foundryctl.py"


class SpecRouterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repo = self.base / "target"
        self.repo.mkdir()
        self.catalog, _ = create_git_catalog(self.base)
        git(self.repo, "init", "-b", "main")
        (self.repo / "go.mod").write_text(
            "module example.test/router\n",
            encoding="utf-8",
        )
        source = self.repo / "service" / "main.go"
        source.parent.mkdir()
        source.write_text("package service\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(
            self.repo,
            "-c",
            "user.name=Router Test",
            "-c",
            "user.email=router@example.invalid",
            "commit",
            "-m",
            "initial target",
        )
        self.run_foundry(
            "bootstrap",
            "--profile",
            "codex",
            "--spec-repository",
            self.catalog.resolve().as_uri(),
            "--spec-version",
            "0.1.0",
            "--spec",
            "languages/go",
            "--apply",
        )
        git(self.repo, "add", ".")
        git(
            self.repo,
            "-c",
            "user.name=Router Test",
            "-c",
            "user.email=router@example.invalid",
            "commit",
            "-m",
            "bootstrap harness",
        )
        self.router = (
            self.repo
            / ".agents"
            / "skills"
            / "engineering-specs"
            / "scripts"
            / "spec_router.py"
        )
        self.core_router = (
            self.repo
            / ".repo-foundry"
            / "engineering-specs"
            / "spec_router.py"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_foundry(
        self,
        *arguments: str,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FOUNDRYCTL),
                "--repo",
                str(self.repo),
                *arguments,
            ],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != expected:
            self.fail(
                f"expected {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def run_router(
        self,
        *arguments: str,
        stdin: dict[str, object] | None = None,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-B", str(self.router), *arguments],
            cwd=self.repo,
            input=(json.dumps(stdin) if stdin is not None else None),
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def run_core(
        self,
        *arguments: str,
        stdin: dict[str, object] | None = None,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-B", str(self.core_router), *arguments],
            cwd=self.repo,
            input=(json.dumps(stdin) if stdin is not None else None),
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != expected:
            self.fail(
                f"expected {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def hook(self, event: str, **values: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "cwd": str(self.repo),
            "hook_event_name": event,
            "model": "test-model",
            "permission_mode": "default",
        }
        payload.update(values)
        result = self.run_router("hook", stdin=payload)
        return json.loads(result.stdout) if result.stdout else {}

    def initialize_turn(self) -> dict[str, object]:
        output = self.hook(
            "UserPromptSubmit",
            prompt="Rename the public Go service API",
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("$engineering-specs", context)
        self.assertIn("Session ID: `session-1`", context)
        self.assertIn("languages/go", context)
        return output

    def activate_go(self, *paths: str) -> dict[str, object]:
        arguments = [
            "activate",
            "--session-id",
            "session-1",
            "--turn-id",
            "turn-1",
        ]
        for path in paths:
            arguments.extend(("--path", path))
        arguments.extend(("--spec", "languages/go"))
        return json.loads(self.run_router(*arguments).stdout)

    def test_bootstrap_generates_one_valid_router_skill_and_hooks(self) -> None:
        self.assertTrue(self.router.is_file())
        self.assertTrue(self.core_router.is_file())
        self.assertTrue(
            (self.repo / ".agents/skills/engineering-specs/SKILL.md").is_file()
        )
        hooks = json.loads(
            (self.repo / ".codex/hooks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(hooks["hooks"]),
            {"UserPromptSubmit", "SubagentStart", "PreToolUse", "Stop"},
        )
        agents = (self.repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("$engineering-specs", agents)
        self.run_foundry("spec", "validate")
        self.run_foundry("validate", "--harness")

    def test_codex_and_portable_share_results_but_isolate_receipts(self) -> None:
        self.initialize_turn()
        codex_candidates = json.loads(
            self.run_router(
                "candidates",
                "--path",
                "service/main.go",
            ).stdout
        )
        codex_activation = self.activate_go("service/main.go")

        portable_start = {
            "protocol_version": 1,
            "event": "session_start",
            "adapter_id": "portable",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "prompt": "Rename the public Go service API",
        }
        started = json.loads(
            self.run_core("event", stdin=portable_start).stdout
        )
        self.assertEqual(started["decision"], "allow")
        self.assertIn("Adapter ID: `portable`", started["context"])
        portable_candidates = json.loads(
            self.run_core(
                "candidates",
                "--path",
                "service/main.go",
            ).stdout
        )
        portable_activation = json.loads(
            self.run_core(
                "activate",
                "--adapter-id",
                "portable",
                "--session-id",
                "session-1",
                "--turn-id",
                "turn-1",
                "--path",
                "service/main.go",
                "--spec",
                "languages/go",
            ).stdout
        )

        self.assertEqual(
            [item["id"] for item in portable_candidates["candidates"]],
            [item["id"] for item in codex_candidates["candidates"]],
        )
        self.assertEqual(
            portable_activation["activated_specs"],
            codex_activation["activated_specs"],
        )
        mutation = {
            "protocol_version": 1,
            "event": "before_mutation",
            "adapter_id": "portable",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool": {
                "category": "file_write",
                "name": "portable-write",
                "paths": ["service/main.go"],
                "input": {},
            },
        }
        first_write = json.loads(
            self.run_core("event", stdin=mutation).stdout
        )
        self.assertEqual(first_write["decision"], "deny")
        self.assertIn("BEGIN languages/go", first_write["context"])
        second_write = json.loads(
            self.run_core("event", stdin=mutation).stdout
        )
        self.assertEqual(second_write, {"decision": "allow"})
        codex_status = json.loads(
            self.run_router(
                "status",
                "--session-id",
                "session-1",
                "--turn-id",
                "turn-1",
            ).stdout
        )
        portable_status = json.loads(
            self.run_core(
                "status",
                "--adapter-id",
                "portable",
                "--session-id",
                "session-1",
                "--turn-id",
                "turn-1",
            ).stdout
        )
        self.assertEqual(codex_status["adapter_id"], "codex")
        self.assertEqual(portable_status["adapter_id"], "portable")

    def test_normalized_protocol_fails_closed_on_future_version(self) -> None:
        result = self.run_core(
            "event",
            stdin={
                "protocol_version": 2,
                "event": "session_start",
                "adapter_id": "portable",
                "session_id": "session-1",
                "turn_id": "turn-1",
            },
            expected=2,
        )

        self.assertIn("ROUTER_PROTOCOL_UNSUPPORTED", result.stderr)

    def test_subagent_receives_the_same_turn_routing_contract(self) -> None:
        self.initialize_turn()
        output = self.hook(
            "SubagentStart",
            agent_id="agent-1",
            agent_type="worker",
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("$engineering-specs", context)
        self.assertIn("Session ID: `session-1`", context)
        self.assertIn("Turn ID: `turn-1`", context)
        self.assertIn("languages/go", context)

    def test_candidates_activation_injection_and_stop_handoff(self) -> None:
        self.initialize_turn()
        candidates = json.loads(
            self.run_router(
                "candidates",
                "--path",
                "service/main.go",
            ).stdout
        )
        self.assertEqual(
            [item["id"] for item in candidates["candidates"]],
            ["core/semantic-naming", "languages/go"],
        )

        activation = self.activate_go("service/main.go")
        self.assertEqual(
            [item["id"] for item in activation["activated_specs"]],
            ["core/semantic-naming", "languages/go"],
        )

        patch = "*** Begin Patch\n*** Update File: service/main.go\n@@\n-package service\n+package service\n*** End Patch"
        first = self.hook(
            "PreToolUse",
            tool_name="apply_patch",
            tool_use_id="tool-1",
            tool_input={"command": patch},
        )
        specific = first["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "deny")
        self.assertIn(
            "BEGIN languages/go",
            specific["additionalContext"],
        )

        second = self.hook(
            "PreToolUse",
            tool_name="apply_patch",
            tool_use_id="tool-2",
            tool_input={"command": patch},
        )
        self.assertEqual(second, {})

        (self.repo / "service/main.go").write_text(
            "package service\n\nfunc PublicAPI() {}\n",
            encoding="utf-8",
        )
        incomplete = self.hook(
            "Stop",
            stop_hook_active=False,
            last_assistant_message="done",
        )
        self.assertEqual(incomplete["decision"], "block")
        self.assertIn("ROUTER_HANDOFF_INCOMPLETE", incomplete["reason"])

        complete = self.hook(
            "Stop",
            stop_hook_active=True,
            last_assistant_message=(
                "Activated specifications: core/semantic-naming@0.1.0, "
                "languages/go@0.1.0\n"
                "Activated requirements: none\n"
                "Verification: go test ./... passed\n"
                "Exceptions: none\n"
                "Compatibility or migration: none"
            ),
        )
        self.assertEqual(complete, {})

    def test_uncovered_path_is_denied_until_activation_expands(self) -> None:
        self.initialize_turn()
        self.activate_go("service/main.go")
        patch = "*** Begin Patch\n*** Add File: service/other.go\n+package service\n*** End Patch"
        output = self.hook(
            "PreToolUse",
            tool_name="apply_patch",
            tool_use_id="tool-3",
            tool_input={"command": patch},
        )
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "deny")
        self.assertIn("service/other.go", specific["permissionDecisionReason"])

    def test_explicit_none_requires_reason_and_still_unlocks_declared_path(self) -> None:
        self.initialize_turn()
        missing_reason = self.run_router(
            "activate",
            "--session-id",
            "session-1",
            "--turn-id",
            "turn-1",
            "--path",
            "README.md",
            "--none",
            expected=2,
        )
        self.assertIn("ROUTER_NONE_REASON_REQUIRED", missing_reason.stderr)

        activation = json.loads(
            self.run_router(
                "activate",
                "--session-id",
                "session-1",
                "--turn-id",
                "turn-1",
                "--path",
                "README.md",
                "--none",
                "--reason",
                "Editorial wording does not change an engineering contract",
            ).stdout
        )
        self.assertEqual(activation["decision"], "none")
        self.assertEqual(activation["activated_specs"], [])

    def test_unbounded_scope_and_mutating_inspection_commands_are_denied(self) -> None:
        self.initialize_turn()
        broad = self.run_router(
            "candidates",
            "--path",
            "**/*",
            expected=2,
        )
        self.assertIn("ROUTER_PLANNED_PATH_TOO_BROAD", broad.stderr)

        safe = self.hook(
            "PreToolUse",
            tool_name="Bash",
            tool_use_id="tool-safe",
            tool_input={"command": "git status --short"},
        )
        self.assertEqual(safe, {})

        mutating = self.hook(
            "PreToolUse",
            tool_name="Bash",
            tool_use_id="tool-mutating",
            tool_input={"command": "git branch bypass"},
        )
        self.assertEqual(
            mutating["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

    def test_manual_begin_activation_and_handoff_audit_work_without_hooks(self) -> None:
        begin = json.loads(
            self.run_router(
                "begin",
                "--session-id",
                "manual-session",
                "--turn-id",
                "manual-turn",
                "--prompt",
                "Review the Go handler name",
            ).stdout
        )
        self.assertTrue(begin["initialized"])
        activation = json.loads(
            self.run_router(
                "activate",
                "--session-id",
                "manual-session",
                "--turn-id",
                "manual-turn",
                "--path",
                "service/main.go",
                "--spec",
                "languages/go",
            ).stdout
        )
        self.assertEqual(activation["decision"], "activated")

        (self.repo / "service/main.go").write_text(
            "package service\n\nfunc ManualReview() {}\n",
            encoding="utf-8",
        )
        handoff = (
            "Activated specifications: languages/go@0.1.0\n"
            "Activated requirements: none\n"
            "Verification: focused review passed\n"
            "Exceptions: none\n"
            "Compatibility or migration: none"
        )
        audit = json.loads(
            self.run_router(
                "audit",
                "--session-id",
                "manual-session",
                "--turn-id",
                "manual-turn",
                "--message",
                handoff,
            ).stdout
        )
        self.assertTrue(audit["ok"])

    def test_custom_hooks_are_preserved_and_report_manual_merge(self) -> None:
        custom = self.repo / ".codex/hooks.json"
        original = '{"hooks":{"Stop":[]},"description":"custom"}\n'
        custom.write_text(original, encoding="utf-8")

        preview = json.loads(
            self.run_foundry(
                "bootstrap",
                "--profile",
                "codex",
                expected=0,
            ).stdout
        )
        conflicts = [
            item
            for item in preview["actions"]
            if item["action"] == "conflict"
            and item["path"] == ".codex/hooks.json"
        ]
        self.assertEqual(len(conflicts), 1)
        self.assertIn("preserve existing Hooks", conflicts[0]["reason"])
        self.assertEqual(custom.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
