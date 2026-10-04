"""Export actual RF bundles in an isolated evaluation directory, never in RF."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(os.environ["RF_RUNTIME_WORK"]).resolve()
source = WORK / "input" / "explanation.json"
raw = source.read_bytes()
original = json.loads(raw)
expected = original["sha256"]
runtime = WORK / "node_modules/p5/lib/p5.min.js"
if not runtime.is_file():
    raise SystemExit("The actual pinned p5 distribution is required")
for language in ("zh-CN", "en"):
    for kind in ("html", "p5", "remotion"):
        destination = WORK / "generated" / f"{language}-{kind}"
        destination.parent.mkdir(exist_ok=True)
        args = [sys.executable, "-B", str(ROOT / "scripts/explain.py"), "render",
                "--input", str(source), "--lang", language, "--format", kind,
                "--output", str(destination), "--apply"]
        if kind == "p5":
            args += ["--p5-js", str(runtime)]
        subprocess.run(args, check=True, timeout=60)
        if (destination / "explanation.json").read_bytes() != raw:
            raise AssertionError("Export changed the canonical IR bytes")
        manifest = json.loads((destination / "render-manifest.json").read_bytes())
        for path, digest in manifest["files"].items():
            assert hashlib.sha256((destination / path).read_bytes()).hexdigest() == digest
assert source.read_bytes() == raw
print(json.dumps({"source_ir_sha256": expected,
                  "p5_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
                  "source_preserved": True, "bundles": 6}))
