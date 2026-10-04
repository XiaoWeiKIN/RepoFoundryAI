"""Exercise real, pinned Catalog commits through RF's installed consumer CLIs.

Run explicitly with RF_REAL_SPEC_REPO pointing to an existing local Git clone.
No remote fetch, tag creation, upstream execution, or embedded Spec corpus.
Missing prerequisites fail this integration run rather than produce a green skip.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PINS = json.loads(Path(__file__).with_name("catalog-pins.json").read_text())
TECH = "documentation/technical-documentation"
DERIVED = "documentation/derived-explanations"
DEFAULT_SELECTION = ("languages/go", DERIVED)
INDEX = "docs/agent-guides/managed/requirements.json"
MANIFEST = "docs/.engineering/specs.json"
LOCK = "docs/.engineering/specs.lock.json"
CAPSULE_MARKER = "# Engineering Specification Context Capsule"
TECH_IDS = {"DOC-STATE-001", "DOC-EVIDENCE-001", "DOC-PROC-001", "DOC-TERM-001", "DOC-FRESH-001"}
DERIVED_IDS = {"DOC-DERIVED-AUTH-001", "DOC-DERIVED-PROV-001", "DOC-A11Y-001"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(args: list[str], cwd: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    # Only local Git transport is allowed. The caller supplies the checkout.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_TERMINAL_PROMPT="0",
               GIT_ALLOW_PROTOCOL="file", GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding="utf-8", timeout=120)
    if result.returncode != expected:
        raise AssertionError(f"{args!r}: expected {expected}, got {result.returncode}\n"
                             f"{result.stdout[-4000:]}\n{result.stderr[-4000:]}")
    return result


def git(root: Path, *args: str) -> str:
    return command(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", *args], root).stdout.strip()


def blob(root: Path, revision: str, path: str) -> bytes:
    # Binary read preserves exact Markdown bytes; no newline normalization.
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=root,
                            capture_output=True, check=True, timeout=30)
    return result.stdout


def inventory(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes())
            for p in root.rglob("*") if p.is_file()}


class RealDocumentationCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = os.environ.get("RF_REAL_SPEC_REPO")
        if not source:
            raise RuntimeError("Set RF_REAL_SPEC_REPO to a local clone containing both pinned commits.")
        cls.upstream = Path(source).resolve(strict=True)
        cls.catalogs = {}
        for key in ("baseline", "candidate"):
            pin = PINS[key]
            revision = pin["revision"]
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                raise AssertionError("A full immutable commit is required, not a moving ref")
            if git(cls.upstream, "rev-parse", "--verify", f"{revision}^{{commit}}") != revision:
                raise AssertionError("Pinned commit mismatch")
            raw = blob(cls.upstream, revision, "catalog.json")
            catalog = json.loads(raw)
            if catalog["catalog_id"] != PINS["catalog_id"] or catalog["catalog_version"] != pin["version"]:
                raise AssertionError("Pinned Catalog identity mismatch")
            if catalog["schema_version"] != 1 or len(catalog["specs"]) != 8:
                raise AssertionError("Review changed Catalog shape before updating the pins")
            for spec in catalog["specs"]:
                path = PurePosixPath(spec["path"])
                if path.is_absolute() or ".." in path.parts:
                    raise AssertionError("Unsafe upstream source path")
                if sha256(blob(cls.upstream, revision, spec["path"])) != spec["sha256"]:
                    raise AssertionError(f"Upstream source digest mismatch: {spec['id']}")
            cls.catalogs[key] = catalog
            print(f"PIN_VERIFIED {key} {revision} Catalog {pin['version']} SHA256 {sha256(raw)}", flush=True)
        # Reading the upstream worktree is not how the tests select a version.
        cls.upstream_status = git(cls.upstream, "status", "--porcelain=v1", "--untracked-files=all")
        cls.upstream_head = git(cls.upstream, "rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls) -> None:
        if git(cls.upstream, "rev-parse", "HEAD") != cls.upstream_head:
            raise AssertionError("Integration changed the upstream checkout")
        if git(cls.upstream, "status", "--porcelain=v1", "--untracked-files=all") != cls.upstream_status:
            raise AssertionError("Integration wrote into the upstream worktree")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="rf-real-catalog-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        (self.repo / "README.md").write_text("# Integration fixture\nNot production evidence.\n")
        (self.repo / "main.go").write_text("package main\n")
        (self.repo / "go.mod").write_text("module example.invalid/fixture\n\ngo 1.22\n")
        self.commit("synthetic target project")

    def commit(self, message: str) -> None:
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=RF Integration", "-c", "user.email=rf@example.invalid",
            "commit", "--quiet", "-m", message)

    def cli(self, script: str, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        return command([sys.executable, "-B", str(ROOT / "scripts" / script), *args], self.repo, expected)

    def foundry(self, *args: str, expected: int = 0) -> dict:
        result = self.cli("foundryctl.py", "--repo", str(self.repo), *args, expected=expected)
        return json.loads(result.stdout) if expected == 0 else {"error": result.stderr}

    def bootstrap(self, key: str = "candidate", selection: tuple[str, ...] = DEFAULT_SELECTION,
                  apply: bool = True) -> dict:
        args = ["bootstrap", "--adapter", "codex", "--governance-profile", "strict",
                "--spec-repository", self.upstream.as_uri(), "--spec-ref", PINS[key]["revision"]]
        if selection:
            for identifier in selection:
                args += ["--spec", identifier]
        else:
            args += ["--required-only"]
        return self.foundry(*args, *(["--apply"] if apply else []))

    def index(self) -> dict:
        return json.loads((self.repo / INDEX).read_bytes())

    def router(self, *args: str, expected: int = 0) -> dict:
        path = self.repo / ".agents/skills/engineering-specs/scripts/spec_router.py"
        result = command([sys.executable, "-B", str(path), *args], self.repo, expected)
        return json.loads(result.stdout) if expected == 0 else {"error": result.stderr}

    def preview(self, path: str = "README.md", requirements: tuple[str, ...] = (),
                budget: int = 32768, expected: int = 0) -> dict:
        args = ["--repo", str(self.repo), "--json", "--path", path, "--budget-bytes", str(budget)]
        for identifier in requirements:
            args += ["--requirement", identifier]
        result = self.cli("explain_spec_activation.py", *args, expected=expected)
        return json.loads(result.stdout) if expected == 0 else {"error": result.stderr}

    def assert_sources(self, key: str) -> None:
        by_id = {s["id"]: s for s in self.catalogs[key]["specs"]}
        for installed in self.index()["specs"]:
            expected = by_id[installed["id"]]
            raw = (self.repo / installed["path"]).read_bytes()
            self.assertEqual(raw, blob(self.upstream, PINS[key]["revision"], expected["path"]))
            self.assertEqual(sha256(raw), expected["sha256"])
        source = self.preview()["provenance"]["catalog"]
        self.assertEqual(source["revision"], PINS[key]["revision"])
        self.assertEqual(source["version"], PINS[key]["version"])

    def assert_capsule(self, preview: dict, expected: set[str]) -> None:
        capsule = preview["capsule"]
        raw = capsule["text"].encode("utf-8")
        self.assertEqual(sha256(raw), capsule["sha256"])
        self.assertEqual(len(raw), capsule["bytes"])
        self.assertLessEqual(len(raw), capsule["budget_bytes"])
        self.assertEqual({r["id"] for r in preview["resolved"]}, expected)
        headings = set(re.findall(r"^### ([A-Z][A-Z0-9-]*-\d{3})\s", capsule["text"], re.M))
        self.assertEqual(headings, expected)
        for record in preview["resolved"]:
            source = (self.repo / record["path"]).read_bytes()
            for name in ("block", "verification"):
                span = record[name]
                excerpt = source[span["start_byte"]:span["end_byte"]]
                self.assertEqual(sha256(excerpt), span["sha256"])
                self.assertIn(excerpt, raw)

    def test_bootstrap_preview_writes_nothing_and_explicit_selection_is_exact(self) -> None:
        before = inventory(self.repo)
        self.assertEqual(self.bootstrap(apply=False)["mode"], "dry-run")
        self.assertEqual(inventory(self.repo), before)
        self.bootstrap()
        self.assertEqual({s["id"] for s in self.index()["specs"]},
                         {"core/semantic-naming", "core/data-boundaries", "languages/go", TECH, DERIVED})
        self.assertEqual(self.index()["schema_version"], 2)
        self.assert_sources("candidate")
        self.foundry("spec", "validate")
        self.foundry("validate", "--harness")

    def test_unselected_documentation_is_not_installed_or_auto_activated(self) -> None:
        self.bootstrap(selection=())
        self.assertEqual({s["id"] for s in self.index()["specs"]},
                         {"core/semantic-naming", "core/data-boundaries"})
        self.assertFalse((self.repo / "docs/agent-guides/managed/documentation").exists())
        view = self.preview()
        self.assertIsNone(view["capsule"])
        self.assertFalse(view["receipt_created"])
        self.assertNotIn(TECH, {s["id"] for s in view["specs"]})

    def test_wide_scope_is_only_a_candidate_and_root_md_mdx_route(self) -> None:
        self.bootstrap()
        before = inventory(self.repo)
        for path in ("README.md", "docs/guide.mdx"):
            view = self.preview(path)
            self.assertIn(TECH, {s["id"] for s in view["specs"]})
            self.assertIsNone(view["capsule"])
        view = self.preview("main.go")
        self.assertIn(DERIVED, {s["id"] for s in view["specs"]})
        self.assertNotIn(TECH, {s["id"] for s in view["specs"]})
        self.assertEqual(view["resolved"], [])
        self.assertEqual(view["authority"], "none")
        self.assertEqual(inventory(self.repo), before)

    def test_exact_doc_capsules_cover_state_procedures_and_cross_spec_terms(self) -> None:
        self.bootstrap()
        cases = [("DOC-STATE-001", {"DOC-STATE-001"}),
                 ("DOC-PROC-001", {"DOC-STATE-001", "DOC-EVIDENCE-001", "DOC-PROC-001"}),
                 ("DOC-TERM-001", {"DOC-TERM-001", "SEM-NAME-001", "SEM-SURFACE-001"})]
        before = inventory(self.repo)
        for direct, expected in cases:
            with self.subTest(requirement=direct):
                self.assert_capsule(self.preview(requirements=(direct,)), expected)
        self.assertEqual(inventory(self.repo), before)

    def test_all_eight_documentation_requirements_are_individually_compilable(self) -> None:
        self.bootstrap()
        for direct in sorted(TECH_IDS | DERIVED_IDS):
            with self.subTest(requirement=direct):
                view = self.preview(requirements=(direct,))
                self.assertEqual(view["direct"], [direct])
                self.assert_capsule(view, {r["id"] for r in view["resolved"]})

    def test_real_activation_rehydrates_exact_bytes_and_audits_declared_path(self) -> None:
        self.bootstrap()
        self.commit("installed real Catalog")
        identity = ["--session-id", "doc-integration", "--turn-id", "adr-review"]
        self.router("begin", *identity, "--prompt", "Review proposed documentation state; fixture only")
        result = self.router("activate", *identity, "--path", "README.md", "--spec", TECH,
                             "--requirement", "DOC-STATE-001", "--because",
                             "DOC-STATE-001=preserve proposed versus verified behavior in fixture")
        self.assertEqual(result["decision"], "activated")
        self.assertEqual([r["id"] for r in result["direct_requirements"]], ["DOC-STATE-001"])
        rehydrated = self.router("rehydrate", *identity)["context"]
        capsule = rehydrated[rehydrated.index(CAPSULE_MARKER):].encode("utf-8")
        self.assertEqual(sha256(capsule), result["capsule"]["sha256"])
        self.assertEqual(capsule, self.preview(requirements=("DOC-STATE-001",))["capsule"]["text"].encode())
        (self.repo / "README.md").write_text("# Fixture proposal\nProposed: use a cache.\nVerification: not performed.\n")
        report = (f"Activated specifications: {TECH}@0.1.0\nActivated requirements: DOC-STATE-001\n"
                  "Verification: scripted fixture path audit; no production verification\n"
                  "Exceptions: none\nCompatibility or migration: none")
        self.assertTrue(self.router("audit", *identity, "--message", report)["ok"])

    def test_missing_reason_does_not_create_activation(self) -> None:
        self.bootstrap()
        self.commit("installed real Catalog")
        identity = ["--session-id", "doc-integration", "--turn-id", "missing-reason"]
        self.router("begin", *identity, "--prompt", "Fixture review")
        before = inventory(self.repo)
        error = self.router("activate", *identity, "--path", "README.md", "--spec", TECH,
                            "--requirement", "DOC-STATE-001", expected=2)["error"]
        self.assertIn("REASON", error.upper())
        self.assertEqual(inventory(self.repo), before)

    def test_budget_failure_has_no_partial_output_or_writes(self) -> None:
        self.bootstrap()
        before = inventory(self.repo)
        error = self.preview(requirements=("DOC-PROC-001",), budget=100, expected=2)["error"]
        self.assertIn("ROUTER_CONTEXT_BUDGET_EXCEEDED", error)
        self.assertEqual(inventory(self.repo), before)
        error = self.router("requirements", "--path", "README.md", "--spec", TECH,
                            "--card-budget-bytes", "1", expected=2)["error"]
        self.assertIn("ROUTER_REQUIREMENT_CARDS_TOO_LARGE", error)

    def test_source_drift_fails_then_locked_sync_restores_exact_original(self) -> None:
        self.bootstrap()
        path = self.repo / f"docs/agent-guides/managed/{TECH}.md"
        original = path.read_bytes()
        path.write_bytes(original + b"\nfixture drift\n")
        self.assertIn("DRIFT", self.preview(requirements=("DOC-STATE-001",), expected=2)["error"])
        self.foundry("spec", "sync", "--apply")
        self.assertEqual(path.read_bytes(), original)
        self.assert_sources("candidate")

    def test_index_drift_is_detected_against_real_source(self) -> None:
        self.bootstrap()
        index = self.index()
        spec = next(s for s in index["specs"] if s["id"] == TECH)
        spec["requirements"][0]["activation"] = "Load when forged routing metadata claims applicability."
        (self.repo / INDEX).write_text(json.dumps(index))
        self.assertIn("DRIFT", self.preview(requirements=("DOC-STATE-001",), expected=2)["error"])

    def test_existing_lock_does_not_follow_upstream_head_or_bootstrap_override(self) -> None:
        self.bootstrap("baseline")
        original = (self.repo / LOCK).read_bytes()
        self.foundry("spec", "sync", "--apply")
        self.assertEqual((self.repo / LOCK).read_bytes(), original)
        self.assert_sources("baseline")
        before = inventory(self.repo)
        error = self.foundry("bootstrap", "--adapter", "codex", "--spec-ref",
                             PINS["candidate"]["revision"], "--apply", expected=2)["error"]
        self.assertIn("SPEC_BOOTSTRAP_OVERRIDE_REQUIRES_UPDATE", error)
        self.assertEqual(inventory(self.repo), before)

    def test_explicit_upgrade_preserves_selection_custom_files_and_is_idempotent(self) -> None:
        self.bootstrap("baseline")
        agents = self.repo / "AGENTS.md"
        custom = agents.read_bytes() + b"\nProject-owned writing convention.\n"
        agents.write_bytes(custom)
        before_selection = json.loads((self.repo / MANIFEST).read_bytes())["specs"]
        before = inventory(self.repo)
        args = ["spec", "update", "--spec-ref", PINS["candidate"]["revision"], "--keep-selection"]
        self.foundry(*args)
        self.assertEqual(inventory(self.repo), before)
        self.foundry(*args, "--apply")
        self.assertEqual(json.loads((self.repo / MANIFEST).read_bytes())["specs"], before_selection)
        self.assertEqual(agents.read_bytes(), custom)
        self.assert_sources("candidate")
        after = inventory(self.repo)
        self.foundry(*args, "--apply")
        self.assertEqual(inventory(self.repo), after)
        self.foundry("spec", "validate")

    def test_explicit_documentation_adoption_keeps_requested_go_selection(self) -> None:
        self.bootstrap("baseline", selection=("languages/go",))
        args = ["spec", "update", "--spec-ref", PINS["candidate"]["revision"],
                "--spec", "languages/go", "--spec", DERIVED]
        before = inventory(self.repo)
        self.foundry(*args)
        self.assertEqual(inventory(self.repo), before)
        self.foundry(*args, "--apply")
        self.assertEqual({s["id"] for s in self.index()["specs"]},
                         {"core/semantic-naming", "core/data-boundaries", "languages/go", TECH, DERIVED})
        self.assert_sources("candidate")

    def test_real_catalog_html_export_is_source_bound_and_read_only(self) -> None:
        self.bootstrap()
        requirements = ("DOC-DERIVED-PROV-001", "DOC-A11Y-001")
        view = self.preview("view.html", requirements)
        self.assert_capsule(view, {"DOC-STATE-001", "DOC-EVIDENCE-001", "DOC-FRESH-001",
                                   "DOC-DERIVED-AUTH-001", "DOC-DERIVED-PROV-001", "DOC-A11Y-001"})
        captured = self.base / "captured.json"
        captured.write_text(json.dumps(view, ensure_ascii=False))
        output = self.base / "html"
        args = ["from-preview", "--input", str(captured), "--format", "html", "--output", str(output)]
        before = inventory(self.repo)
        self.cli("explain.py", *args)
        self.assertFalse(output.exists())
        self.cli("explain.py", *args, "--apply")
        ir = json.loads((output / "explanation.json").read_bytes())
        self.assertEqual(ir["source"]["snapshot"], view)
        self.assertEqual(ir["authority"], "none")
        self.assertFalse(ir["source"]["snapshot"]["receipt_created"])
        manifest = json.loads((output / "render-manifest.json").read_bytes())
        self.assertEqual(manifest["ir_sha256"], ir["sha256"])
        for name, digest in manifest["files"].items():
            self.assertEqual(sha256((output / name).read_bytes()), digest)
        self.assertIn("No activation", (output / "README.txt").read_text())
        output_before = inventory(output)
        self.cli("explain.py", *args, "--apply", expected=2)
        self.assertEqual(inventory(output), output_before)
        self.assertEqual(inventory(self.repo), before)
        artifact_dir = os.environ.get("RF_SPEC_ARTIFACT_DIR")
        if artifact_dir:
            target = Path(artifact_dir).resolve()
            target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(output, target / "real-catalog-html")


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    ok = program.result.wasSuccessful() and not program.result.skipped
    result = {"kind": "scripted-consumer-integration", "pins": PINS,
              "rf_revision": git(ROOT, "rev-parse", "HEAD"),
              "tests_run": program.result.testsRun, "skipped": len(program.result.skipped),
              "success": ok, "model_behavior_evaluated": False,
              "release_published": False, "browser_e2e": False}
    target = os.environ.get("RF_SPEC_ARTIFACT_DIR")
    if target:
        path = Path(target)
        path.mkdir(parents=True, exist_ok=True)
        (path / "consumer-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    raise SystemExit(0 if ok else 1)
