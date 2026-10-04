#!/usr/bin/env python3
"""Compile a Spec Lab snapshot into disposable, source-bound reading surfaces."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
from explanation_i18n import LANGUAGES, FONT_FAMILY, presentation
from explanation_ir import IRError, MAX_BYTES, canonical, from_preview, parse, sha256, validate

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets/explain"
FORMATS = {
    "json": "Validated Explanation IR and source snapshot; no runtime dependency.",
    "mermaid": "Dependency diagram source plus the same IR; use your Mermaid viewer.",
    "html": "Self-contained offline reading player; no external dependencies.",
    "p5": "Offline reading player with p5 canvas; requires an explicitly supplied trusted --p5-js file.",
    "remotion": "Render-ready source bundle, NOT an MP4. Use an existing local Remotion project; review its license.",
}


def read_regular(path: Path, limit: int) -> bytes:
    """Do not follow a symlink or block on a FIFO passed as an input file."""
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise IRError(f"Expected a regular, non-symlink input file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise IRError("Input is not a regular file.")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise IRError(f"Input exceeds {limit} bytes: {path.name}")
    return raw


def choose_format(requested: str, goal: str) -> tuple[str, str]:
    if requested != "auto":
        if requested not in FORMATS:
            raise IRError("Unknown renderer.")
        return requested, "Explicit renderer selection."
    if goal == "relationships":
        return "mermaid", "Relationship task: dependency diagram with a source companion."
    return "html", "Use the dependency-free reading player. Optional runtimes are never installed or chosen silently."


def safe_json(ir: dict) -> str:
    return canonical(ir).decode("utf-8").replace("<", "\\u003c").replace(
        "\u2028", "\\u2028").replace("\u2029", "\\u2029")


def mermaid(ir: dict, lang: str = "en") -> bytes:
    reading = presentation(ir, lang)
    ui = reading["labels"]
    # Generated identifiers, inert entity-encoded labels; no user directive syntax.
    def label(text: str) -> str:
        return "".join(c if c.isalnum() or c in " -_./" else f"#{ord(c)};" for c in text)
    ids = {n["id"]: f"N{i}" for i, n in enumerate(ir["graph"]["nodes"])}
    lines = [f"%% {ui['boundary']}", f"%% {ui['digest']}: {ir['sha256']}", "flowchart RL"]
    for node in ir["graph"]["nodes"]:
        lines.append(f'    {ids[node["id"]]}["{label(node["id"])} / {label(ui["direct" if node["role"] == "direct" else "dependency"])}"]')
    for edge in ir["graph"]["edges"]:
        lines.append(f'    {ids[edge["from"]]} --> {ids[edge["to"]]}')
    if not ids:
        lines.append(f'    EMPTY["{label(ui["empty_graph"])}"]')
    return ("\n".join(lines) + "\n").encode("utf-8")


def story_html(ir: dict, *, p5: bool = False, lang: str = "en") -> bytes:
    reading = presentation(ir, lang)
    page = (ASSETS / "story.html.template").read_text(encoding="utf-8")
    frame_model = (ASSETS / "frame-model.mjs").read_text(encoding="utf-8")
    visual = (ASSETS / ("p5-visual.mjs" if p5 else "svg-visual.mjs")).read_text(encoding="utf-8")
    page = page.replace("@@FRAME_MODEL@@", frame_model).replace("@@VISUAL@@", visual)
    page = page.replace("@@LANG@@", reading["language"]).replace("@@FONT@@", FONT_FAMILY)
    page = re.sub(r"@@UI_([a-z_]+)@@",
                  lambda m: html.escape(reading["labels"][m[1]], quote=True), page)
    page = page.replace("@@VENDOR@@", '<script src="./p5.js"></script>' if p5 else "")
    # Hash the entire inline module after expansion. Source data is JSON, not code.
    module = page.split('<script type="module">', 1)[1].split("</script>", 1)[0]
    module_hash = base64.b64encode(hashlib.sha256(module.encode("utf-8")).digest()).decode("ascii")
    csp = ("default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; "
           "img-src 'none'; style-src 'unsafe-inline'; "
           f"script-src 'sha256-{module_hash}'" + (" 'self'" if p5 else ""))
    page = page.replace("@@CSP@@", html.escape(csp, quote=True))
    # Replace user JSON last: its strings must never become template directives.
    # One pass: source strings containing template markers stay inert data.
    data = {"IR": ir, "PRESENTATION": reading}
    return re.sub(r"@@(IR|PRESENTATION)@@",
                  lambda m: safe_json(data[m[1]]), page).encode("utf-8")


def render_files(ir: dict, output_format: str, p5_js: Path | None = None,
                 *, lang: str = "en") -> dict[str, bytes]:
    reading = presentation(ir, lang)
    ui = reading["labels"]
    if output_format not in FORMATS:
        raise IRError("Unsupported renderer.")
    if p5_js is not None and output_format != "p5":
        raise IRError("--p5-js is only valid with --format p5.")
    files = {"explanation.json": canonical(ir) + b"\n",
             "presentation.json": canonical(reading) + b"\n"}
    runtime = ui["runtime_none"]
    if output_format == "mermaid":
        files["diagram.mmd"] = mermaid(ir, lang)
    elif output_format in ("html", "p5"):
        if output_format == "p5":
            if p5_js is None:
                raise IRError("p5 is optional: provide --p5-js /path/to/trusted/p5.min.js. No CDN or installer is used.")
            runtime_bytes = read_regular(p5_js, 10 * 1024 * 1024)
            if not runtime_bytes.strip():
                raise IRError("The supplied p5 runtime is empty.")
            runtime_bytes.decode("utf-8")
            files["p5.js"] = runtime_bytes
            runtime = ui["runtime_p5"] + " " + sha256(runtime_bytes)
        files["index.html"] = story_html(ir, p5=output_format == "p5", lang=lang)
    elif output_format == "remotion":
        files["index.mjs"] = (ASSETS / "remotion-entry.mjs").read_bytes()
        files["frame-model.mjs"] = (ASSETS / "frame-model.mjs").read_bytes()
        runtime = ui["runtime_remotion"]
    instructions = ui[output_format + "_help"]
    files["README.txt"] = (
        f"{ui['brand']} / {output_format} / {lang}\n\n{instructions}\n\n"
        + "\n".join(ui[key] for key in (
            "boundary", "source_note", "timeline", "confidential", "hash_note", "do_not_edit"))
        + f"\n{ui['digest']}: {ir['sha256']}\n{ui['runtime']}: {runtime}\n"
    ).encode("utf-8")
    manifest = {"kind": "derived-render-bundle", "authority": "none", "format": output_format, "language": lang,
                "ir_sha256": ir["sha256"], "source_sha256": ir["source"]["sha256"],
                "runtime": runtime, "files": {name: sha256(raw) for name, raw in sorted(files.items())}}
    files["render-manifest.json"] = canonical(manifest) + b"\n"
    return files


def destination(path: Path, protected: tuple[Path, ...]) -> Path:
    absolute = Path(os.path.abspath(path))
    for parent in (absolute, *absolute.parents):
        if parent.is_symlink() or parent.name == ".git":
            raise IRError("Output must not traverse a symlink or Git metadata.")
    if absolute.exists():
        raise IRError("Output already exists. Choose a new disposable directory; overwrite is not supported.")
    if not absolute.parent.is_dir():
        raise IRError("Output parent must already exist.")
    for root in protected:
        if absolute.is_relative_to(root.resolve()):
            raise IRError("Export outside the RF checkout and the target repository.")
    return absolute


def publish(output: Path, files: dict[str, bytes]) -> None:
    """Create a private NEW bundle. Never overwrite or delete an output path.

    Validate the complete render plan before creating anything. Write the
    manifest last; on I/O failure leave an incomplete directory for inspection.
    The caller must choose a new directory for a retry.
    """
    allowed = {"explanation.json", "diagram.mmd", "index.html", "p5.js",
               "index.mjs", "frame-model.mjs", "presentation.json", "README.txt", "render-manifest.json"}
    if (not isinstance(files, dict) or not files or set(files) - allowed
            or "render-manifest.json" not in files
            or any(not isinstance(raw, bytes) for raw in files.values())):
        raise IRError("Invalid renderer file plan. No output was created.")
    # Repeat the non-overwrite/symlink checks even for direct library callers.
    output = destination(output, (ROOT,))
    output.mkdir(mode=0o700, exist_ok=False)
    names = [name for name in files if name != "render-manifest.json"]
    names.append("render-manifest.json")
    for name in names:
        # Exclusive create and owner-only permissions from the first byte.
        # No chmod after opening and no cleanup that could delete another file.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(output / name, flags, 0o600), "wb") as stream:
            stream.write(files[name])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("formats", help="Describe implemented outputs and optional runtimes")
    for command in ("spec", "from-preview", "render"):
        sub = commands.add_parser(command)
        if command == "spec":
            sub.add_argument("--repo", required=True, type=Path)
            sub.add_argument("--path", action="append", required=True)
            sub.add_argument("--requirement", action="append", default=[])
            sub.add_argument("--whole-spec", action="append", default=[])
        else:
            sub.add_argument("--input", required=True, type=Path,
                             help="Captured Spec Lab JSON" if command == "from-preview" else "Validated Explanation IR JSON")
        sub.add_argument("--format", choices=["auto", *FORMATS], default="auto")
        sub.add_argument("--goal", choices=["overview", "relationships", "exploration", "sequence"], default="overview")
        sub.add_argument("--lang", choices=LANGUAGES, default="en",
                         help="Reading language; exact IR/source bytes are never translated (default: en)")
        sub.add_argument("--p5-js", type=Path)
        sub.add_argument("--output", required=True, type=Path)
        sub.add_argument("--apply", action="store_true", help="Create a NEW output bundle; default is read-only preview")
    args = parser.parse_args(argv)
    try:
        if args.command == "formats":
            print(json.dumps(FORMATS, indent=2))
            return 0
        protected = (ROOT, args.repo) if args.command == "spec" else (ROOT,)
        output = destination(args.output, protected)
        selected_format, reason = choose_format(args.format, args.goal)
        if args.command == "spec":
            from explain_spec_activation import build_preview, load_router
            router = load_router()
            root = router.repository_root(str(args.repo))
            ir = from_preview(build_preview(root, router, {"paths": args.path,
                "requirements": args.requirement, "whole_specs": args.whole_spec}))
        else:
            value = parse(read_regular(args.input, MAX_BYTES))
            ir = from_preview(value) if args.command == "from-preview" else validate(value)
        files = render_files(ir, selected_format, args.p5_js, lang=args.lang)
        if args.apply:
            # Recheck after compilation; preview never grants overwrite authority.
            destination(output, protected)
            publish(output, files)
        print(json.dumps({"mode": "apply" if args.apply else "dry-run", "format": selected_format,
            "language": args.lang,
            "reason": reason, "output": str(output), "ir_sha256": ir["sha256"],
            "files": [{"path": name, "bytes": len(raw), "sha256": sha256(raw)} for name, raw in files.items()],
            "authority": "none", "video_rendered": False}, ensure_ascii=False, indent=2))
    except (IRError, OSError, ValueError, RuntimeError, UnicodeError, ImportError) as exc:
        print(f"rf-explain: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
