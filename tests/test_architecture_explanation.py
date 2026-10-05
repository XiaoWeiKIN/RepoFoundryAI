"""Tests for the source-bound architecture HTML renderer."""
from __future__ import annotations
import copy, hashlib, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/explain_architecture.py"
SPEC=importlib.util.spec_from_file_location("explain_architecture",SCRIPT);assert SPEC and SPEC.loader
ARCH=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ARCH)

def fixture():
    d={"schema":ARCH.SCHEMA,"authority":"none",
       "subject":{"title":"Synthetic editor architecture","summary":"Test-only source-bound architecture."},
       "source":{"repository":"example/test","revision":"abc123","source_set_sha256":"a"*64},
       "components":[
         {"id":"caller","label":"Caller","responsibility":"Owns controlled state.","paths":["src/caller.py"]},
         {"id":"editor","label":"Editor","responsibility":"Owns the editing surface.","paths":["src/editor.py"]}],
       "flows":[{"id":"edit","title":"Edit flow","steps":[
         {"actor":"caller","action":"Provides controlled state."},
         {"actor":"editor","action":"Emits an edit.","condition":"Only after an input event."}]}],
       "invariants":[{"text":"Caller remains the state owner.","refs":["src/caller.py:10"]}],
       "limitations":[{"text":"No browser behavior was measured.","refs":["tests/editor.py"]}],
       "evidence":[{"id":"source-editor","kind":"source","label":"Editor source","locator":"src/editor.py"},
                   {"id":"test-editor","kind":"test","label":"Editor test","locator":"tests/editor.py"}]}
    raw=ARCH.canonical(d);d["sha256"]=ARCH.sha256(raw);return d

class ArchitectureTests(unittest.TestCase):
    def cli(self,*args):
        return subprocess.run([sys.executable,"-B",str(SCRIPT),*args],capture_output=True,text=True,timeout=10)
    def test_validates_source_bound_document_and_digest(self):
        d=fixture();before=copy.deepcopy(d);self.assertIs(ARCH.validate(d),d);self.assertEqual(d,before)
        bad=copy.deepcopy(d);bad["flows"][0]["steps"][0]["actor"]="missing"
        with self.assertRaises(ARCH.ArchitectureError):ARCH.validate(bad)
        bad=copy.deepcopy(d);bad["subject"]["summary"]="edited"
        with self.assertRaisesRegex(ARCH.ArchitectureError,"digest"):ARCH.validate(bad)
    def test_duplicate_json_and_nonfinite_values_are_rejected(self):
        for raw in (b'{"a":1,"a":2}',b'{"x":NaN}'):
            with self.subTest(raw=raw),self.assertRaises(ARCH.ArchitectureError):ARCH.parse(raw)
    def test_html_keeps_untrusted_text_inert_and_offline(self):
        d=fixture();d.pop("sha256");d["subject"]["summary"]='</script><img src=x onerror=alert(1)>'
        d["sha256"]=ARCH.sha256(ARCH.canonical(d))
        page=ARCH.page(d).decode()
        self.assertNotIn("<img src=x",page);self.assertIn("\\u003c/script>",page)
        self.assertIn("connect-src 'none'",page);self.assertNotIn("fetch(",page)
    def test_dry_run_then_apply_preserves_input_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/"architecture.json";out=root/"view";raw=ARCH.canonical(fixture());src.write_bytes(raw)
            dry=self.cli("--input",str(src),"--output",str(out));self.assertEqual(dry.returncode,0,dry.stderr);self.assertFalse(out.exists())
            run=self.cli("--input",str(src),"--output",str(out),"--apply");self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(src.read_bytes(),raw);self.assertTrue((out/"index.html").is_file())
            manifest=json.loads((out/"render-manifest.json").read_text())
            self.assertEqual(manifest["authority"],"none")
            self.assertEqual(manifest["files"]["index.html"],hashlib.sha256((out/"index.html").read_bytes()).hexdigest())
            again=self.cli("--input",str(src),"--output",str(out),"--apply");self.assertEqual(again.returncode,2)
    def test_no_repository_inference_or_markdown_conversion_claim(self):
        text=SCRIPT.read_text()
        self.assertNotIn("subprocess",text);self.assertNotIn("requests",text);self.assertNotIn("urllib",text)
        self.assertIn("source-bound architecture JSON",text)
if __name__=="__main__":unittest.main()
