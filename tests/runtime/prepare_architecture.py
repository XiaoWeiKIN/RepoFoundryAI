"""Prepare a synthetic architecture view in the isolated runtime workspace."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
WORK=Path(os.environ["RF_RUNTIME_WORK"]).resolve()
payload={
  "schema":"repofoundry.architecture-explanation/v1",
  "authority":"none",
  "language":"en",
  "subject":{"title":"Synthetic architecture fixture","summary":"Browser-only fixture for the derived architecture reading surface."},
  "source":{"repository":"synthetic/runtime","revision":"fixture",
            "files":[
              {"path":"src/caller.py","digest_algorithm":"sha256","digest":"1"*64},
              {"path":"src/editor.py","digest_algorithm":"sha256","digest":"2"*64},
              {"path":"tests/editor.py","digest_algorithm":"sha256","digest":"3"*64},
              {"path":"tests/runtime/prepare_architecture.py","digest_algorithm":"sha256","digest":"4"*64}],
            "source_set_sha256":""},
  "components":[
    {"id":"caller","label":"Caller","responsibility":"Owns controlled state.","paths":["src/caller.py"]},
    {"id":"editor","label":"Editor","responsibility":"Owns the editing surface.","paths":["src/editor.py"]}
  ],
  "flows":[{"id":"edit","title":"Edit flow","steps":[
    {"actor":"caller","action":"Provides controlled state."},
    {"actor":"editor","action":"Emits an edit.","condition":"Only after an input event."}
  ]}],
  "invariants":[{"text":"Caller remains the state owner.","refs":["src/caller.py:10"]}],
  "limitations":[{"text":"Synthetic browser fixture only; no product behavior is claimed.","refs":["tests/runtime/prepare_architecture.py"]}],
  "evidence":[
    {"id":"source-editor","kind":"source","label":"Editor source","locator":"src/editor.py"},
    {"id":"test-editor","kind":"test","label":"Editor test","locator":"tests/editor.py"}
  ]
}
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
payload["source"]["source_set_sha256"]=hashlib.sha256(canonical(payload["source"]["files"])).hexdigest()
payload["sha256"]=hashlib.sha256(canonical(payload)).hexdigest()
source=WORK/"architecture-input.json"
source.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
destination=WORK/"generated"/"architecture"
destination.parent.mkdir(exist_ok=True)
subprocess.run([sys.executable,"-B",str(ROOT/"scripts/explain_architecture.py"),
                "--input",str(source),"--output",str(destination),"--apply"],
               check=True,timeout=30)
stored=json.loads((destination/"architecture.json").read_text(encoding="utf-8"))
assert stored==payload
manifest=json.loads((destination/"render-manifest.json").read_text(encoding="utf-8"))
for name,digest in manifest["files"].items():
    assert hashlib.sha256((destination/name).read_bytes()).hexdigest()==digest
print(json.dumps({"architecture_sha256":payload["sha256"],"source_preserved":True,
                  "files":sorted(p.name for p in destination.iterdir())}))
