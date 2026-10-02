from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/explain_spec_activation.py"
spec = importlib.util.spec_from_file_location("explain_spec_activation_tested", SCRIPT)
assert spec is not None and spec.loader is not None
explain = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = explain
spec.loader.exec_module(explain)


def inventory(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class RequestValidationTests(unittest.TestCase):
    def test_invalid_request_shapes_fail_before_source_reads(self) -> None:
        router = types.SimpleNamespace(_normalize_planned_path=lambda root, path: path)
        bad = [None, [], {}, {"paths": ["src/*.go"]}, {"paths": ["a"] * 9},
               {"paths": [False]}, {"paths": ["x" * 513]}, {"paths": ["a"], "apply": True},
               {"paths": ["a"], "requirements": "GO-NAME-001"},
               {"paths": ["a"], "budget_bytes": True}, {"paths": ["a"], "budget_bytes": 32769}]
        with mock.patch.object(explain, "metadata_digests") as reads:
            for request in bad:
                with self.subTest(request=request), self.assertRaises(explain.ExplainError):
                    explain.build_preview(Path("/unused"), router, request)
            reads.assert_not_called()

    def test_string_list_preserves_order_and_deduplicates(self) -> None:
        self.assertEqual(explain.string_list(["B", "A", "B"], "ids", 4), ("B", "A"))

    def test_page_has_no_remote_assets_or_dynamic_html_insertion(self) -> None:
        page, csp = explain.page_bytes()
        self.assertIn(b"AbortController", page)
        self.assertIn(b"own!==sequence", page)
        self.assertIn(b"textContent", page)
        for unsafe in (b"innerHTML", b"<script src=", b"eval(", b"new Function(", b"localStorage"):
            self.assertNotIn(unsafe, page)
        self.assertIn("script-src 'sha256-", csp)
        self.assertIn("connect-src 'self'", csp)


class TransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.router = types.SimpleNamespace(RouterError=RuntimeError)
        self.server = explain.PreviewServer(Path(self.temp.name), self.router)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def request(self, method="POST", path="/api/preview", *, headers=None, body=b"{}"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        values = {"Origin": self.server.origin, "X-Explain-Token": self.server.token,
                  "Content-Type": "application/json"}
        values.update(headers or {})
        try:
            connection.request(method, path, body=body, headers=values)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_transport_valid_preview_and_no_store_headers(self) -> None:
        with mock.patch.object(explain, "build_preview", return_value={"receipt_created": False}) as build:
            status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["receipt_created"])
        build.assert_called_once()
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_transport_rejects_cross_origin_host_and_capability(self) -> None:
        for headers in ({"Origin": "https://attacker.invalid"}, {"Origin": "null"},
                        {"Host": "attacker.invalid"}, {"X-Explain-Token": ""},
                        {"X-Explain-Token": "not-the-token"}, {"X-Explain-Token": "\u00e9"}):
            with self.subTest(headers=headers), mock.patch.object(explain, "build_preview") as build:
                self.assertEqual(self.request(headers=headers)[0], 403)
                build.assert_not_called()

    def test_transport_serves_only_bundled_page(self) -> None:
        self.assertEqual(self.request("GET", "/")[0], 200)
        for path in ("/docs/.engineering/specs.lock.json", "/../../etc/passwd", "/api/preview"):
            self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("GET", "/", headers={"Host": "evil.invalid"})[0], 403)

    def test_transport_rejects_bad_bodies_without_compiling(self) -> None:
        for headers, body in (({"Content-Type": "text/plain"}, b"{}"),
                              ({"Content-Length": "-1"}, b""),
                              ({"Content-Length": "40000"}, b""),
                              ({"Transfer-Encoding": "chunked"}, b""),
                              ({}, b"not json"), ({}, b"\xff")):
            with self.subTest(headers=headers, body=body), mock.patch.object(explain, "build_preview") as build:
                self.assertEqual(self.request(headers=headers, body=body)[0], 400)
                build.assert_not_called()

    def test_transport_keeps_source_text_in_json_not_executable_html(self) -> None:
        payload = {"text": '</script><img src=x onerror="alert(1)">' }
        with mock.patch.object(explain, "build_preview", return_value=payload):
            status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(json.loads(body), payload)

    def test_transport_returns_compiler_errors_without_a_partial_capsule(self) -> None:
        with mock.patch.object(explain, "build_preview", side_effect=RuntimeError("ROUTER_CONTEXT_BUDGET_EXCEEDED")):
            status, _, body = self.request()
        self.assertEqual(status, 400)
        self.assertEqual(set(json.loads(body)), {"error"})


class CanonicalRouterTests(unittest.TestCase):
    """Run against real locked fixture data and the distribution's actual Router."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.spec_git_fixture import create_git_catalog, git, commit_all
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.seed = cls.base / "seed"
        cls.seed.mkdir()
        catalog, _ = create_git_catalog(cls.base)
        git(cls.seed, "init", "-b", "main")
        (cls.seed / "go.mod").write_text("module example.test/explain\n", encoding="utf-8")
        commit_all(cls.seed, "initial fixture")
        subprocess.run([sys.executable, "-B", str(ROOT / "scripts/foundryctl.py"),
                        "--repo", str(cls.seed), "bootstrap", "--adapter", "portable",
                        "--spec-repository", catalog.resolve().as_uri(), "--spec-version", "0.1.0",
                        "--spec", "languages/go", "--spec", "languages/typescript", "--apply"],
                       check=True, capture_output=True, text=True, timeout=90)
        commit_all(cls.seed, "fixture with locked Specs")
        cls.router = explain.load_router()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "target"
        shutil.copytree(self.seed, self.repo)

    def preview(self, **values):
        request = {"paths": ["service/main.go"], "requirements": ["GO-NAME-001"]}
        request.update(values)
        return explain.build_preview(self.repo, self.router, request)

    def test_canonical_capsule_equals_router_and_writes_nothing(self) -> None:
        before = inventory(self.repo)
        result = self.preview()
        state = self.router.load_state(self.repo)
        resolved = self.router.requirement_dependency_closure(state.requirement_index, ("GO-NAME-001",))
        text, mode = self.router.compile_context_capsule(self.repo, state, ("GO-NAME-001",), resolved, (), (), 32768)
        self.assertEqual(result["capsule"]["text"], text)
        self.assertEqual(result["capsule"]["mode"], mode)
        self.assertEqual(result["capsule"]["bytes"], len(text.encode("utf-8")))
        self.assertEqual(result["capsule"]["sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertNotIn("UNRELATED-TEST-SENTINEL", text)
        self.assertEqual(result["edges"], [{"from": "GO-NAME-001", "to": "SEM-NAME-001"}])
        self.assertFalse(result["receipt_created"])
        self.assertEqual(result["authority"], "none")
        self.assertEqual(inventory(self.repo), before)  # Includes .git/index.

    def test_canonical_root_path_and_empty_selection_are_not_activation(self) -> None:
        result = self.preview(paths=["main.go"], requirements=[])
        self.assertIsNone(result["capsule"])
        self.assertIn("languages/go", [s["id"] for s in result["specs"]])
        result = self.preview(paths=["README.md"], requirements=[])
        self.assertEqual([s["id"] for s in result["specs"]], ["core/semantic-naming"])
        self.assertFalse(result["provenance"]["git"]["dirty"])

    def test_canonical_rejects_irrelevant_unknown_and_outside_paths(self) -> None:
        for values in ({"paths": ["README.md"]}, {"requirements": ["NO-SUCH-001"]},
                       {"paths": ["../outside.go"]}, {"paths": ["/outside.go"]}):
            with self.subTest(values=values), self.assertRaises((explain.ExplainError, self.router.RouterError)):
                self.preview(**values)

    def test_canonical_budget_fails_without_truncation(self) -> None:
        with self.assertRaisesRegex(self.router.RouterError, "ROUTER_CONTEXT_BUDGET_EXCEEDED"):
            self.preview(budget_bytes=100)

    def test_canonical_content_drift_is_rejected(self) -> None:
        path = self.repo / "docs/agent-guides/managed/languages/go.md"
        path.write_bytes(path.read_bytes() + b"\nchanged\n")
        with self.assertRaisesRegex(self.router.RouterError, "DRIFT"):
            self.preview()

    def test_canonical_index_drift_is_rejected(self) -> None:
        path = self.repo / self.router.REQUIREMENT_INDEX_PATH
        text = path.read_text(encoding="utf-8")
        original = "Load when changing a shared or public name."
        self.assertIn(original, text)
        # Preserve the Activation shape so this exercises source/index drift,
        # rather than the earlier syntactic validation gate.
        changed = text.replace(original, "Load when changing an unrelated private name.")
        path.write_text(changed, encoding="utf-8")
        with self.assertRaisesRegex(self.router.RouterError, "ROUTER_REQUIREMENT_INDEX_METADATA_DRIFT"):
            self.preview()

    def test_canonical_legacy_whole_spec_and_overlap(self) -> None:
        result = self.preview(paths=["client.ts"], requirements=[], whole_specs=["languages/typescript"])
        state = self.router.load_state(self.repo)
        whole = tuple(e.key for e in self.router.dependency_closure(state, ["languages/typescript"]))
        text, _ = self.router.compile_context_capsule(self.repo, state, (), (), whole, (), 32768)
        self.assertEqual(result["capsule"]["text"], text)
        self.assertIn("core/semantic-naming", result["whole_specs"])
        with self.assertRaisesRegex(explain.ExplainError, "overlap"):
            self.preview(paths=["client.ts", "main.go"], whole_specs=["languages/typescript"])

    def test_canonical_metadata_race_is_rejected(self) -> None:
        before = explain.metadata_digests(self.repo, self.router)
        after = dict(before)
        after[self.router.LOCK_PATH] = "0" * 64
        with mock.patch.object(explain, "metadata_digests", side_effect=[before, after]):
            with self.assertRaisesRegex(explain.ExplainError, "changed during"):
                self.preview()

    def test_canonical_source_symlink_is_rejected(self) -> None:
        path = self.repo / "docs/agent-guides/managed/languages/go.md"
        original = self.repo / "original.md"
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaises(self.router.RouterError):
            self.preview()

    def test_canonical_json_cli_uses_actual_router(self) -> None:
        before = inventory(self.repo)
        output = subprocess.run([sys.executable, "-B", str(SCRIPT), "--repo", str(self.repo),
                                 "--json", "--path", "main.go", "--requirement", "GO-NAME-001"],
                                capture_output=True, text=True, check=True, timeout=30)
        self.assertEqual(json.loads(output.stdout)["capsule"]["sha256"], self.preview(paths=["main.go"])["capsule"]["sha256"])
        self.assertEqual(inventory(self.repo), before)


if __name__ == "__main__":
    unittest.main()
