"""Check actual browser-assigned CJK glyphs against installed fonts' cmap tables.

Inspect font bytes locally; never copy or upload font files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from fontTools.ttLib import TTCollection, TTFont

work = Path(os.environ["RF_RUNTIME_WORK"])
report_path = work / "evidence/runtime-results.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
assignments: dict[str, set[int]] = {}
for sample in report["font_samples"]:
    for font in sample["fonts"]:
        if font["glyphCount"]:
            key = font.get("postScriptName") or font["familyName"]
            assignments.setdefault(key, set()).add(ord(sample["character"]))
if not assignments:
    raise SystemExit("No actual browser font assignments were captured")
roots = ([Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"] if sys.platform == "win32" else
         [Path("/System/Library/Fonts"), Path("/Library/Fonts")] if sys.platform == "darwin" else
         [Path("/usr/share/fonts"), Path("/usr/local/share/fonts")])
covered = {key: set() for key in assignments}
matched = []
for root in roots:
    if not root.exists():
        continue
    for file in sorted(root.rglob("*")):
        if file.suffix.lower() not in (".ttf", ".otf", ".ttc", ".otc"):
            continue
        collection = None
        fonts = []
        try:
            if file.suffix.lower() in (".ttc", ".otc"):
                collection = TTCollection(file, lazy=True)
                fonts = collection.fonts
            else:
                fonts = [TTFont(file, lazy=True)]
            for face, font in enumerate(fonts):
                names = {font["name"].getDebugName(i) for i in (1, 4, 6, 16)}
                for key in assignments.keys() & names:
                    cmap = font.getBestCmap() or {}
                    present = {c for c in assignments[key] if cmap.get(c) not in (None, ".notdef", ".null")}
                    covered[key] |= present
                    matched.append({"font": key, "file": file.name, "face": face,
                                    "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                                    "tested_glyphs": len(assignments[key]), "covered_glyphs": len(present)})
        except Exception as exc:
            print(f"Font inspection warning {file.name}: {exc}", file=sys.stderr)
        finally:
            if collection:
                collection.close()
            else:
                for font in fonts:
                    font.close()
missing = {key: [f"U+{c:04X}" for c in sorted(chars - covered[key])]
           for key, chars in assignments.items() if chars - covered[key]}
result = {"kind": "installed-font-cmap-evidence", "platform": sys.platform,
          "chinese_codepoints": len(set().union(*assignments.values())),
          "fonts": matched, "missing": missing, "success": not missing,
          "scope": "The actual localized UI characters; not all CJK Unicode or all user machines",
          "font_files_redistributed": False}
(work / "evidence/font-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
if missing:
    raise SystemExit(1)
