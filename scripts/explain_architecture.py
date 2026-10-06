#!/usr/bin/env python3
"""Render bounded source-bound architecture JSON as an offline HTML reading view."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "repofoundry.architecture-explanation/v1"
MAX_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 128


class ArchitectureError(ValueError):
    pass


def canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ArchitectureError("Input must be finite UTF-8 JSON.") from exc


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def string(value: object, name: str, maximum: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ArchitectureError(f"{name} must be a bounded nonempty string.")
    return value


def array(value: object, name: str, maximum: int = MAX_ITEMS) -> list:
    if not isinstance(value, list) or len(value) > maximum:
        raise ArchitectureError(f"{name} must be a bounded array.")
    return value


def hex_digest(value: object, name: str, length: int) -> str:
    value = string(value, name, length)
    if len(value) != length or re.search("[^0-9a-f]", value):
        raise ArchitectureError(f"{name} must be {length} lowercase hexadecimal characters.")
    return value


def source_files(source: dict) -> list[dict]:
    files = array(source.get("files"), "source.files", 256)
    normalized = []
    paths = []
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise ArchitectureError(f"source.files[{index}] must be an object.")
        path = string(item.get("path"), f"source.files[{index}].path", 512)
        algorithm = string(item.get("digest_algorithm"), "source digest algorithm", 32)
        if algorithm == "sha256":
            digest = hex_digest(item.get("digest"), "source digest", 64)
        elif algorithm == "git-blob-sha1":
            digest = hex_digest(item.get("digest"), "source digest", 40)
        else:
            raise ArchitectureError(f"Unsupported source digest algorithm: {algorithm}")
        normalized.append({"path": path, "digest_algorithm": algorithm, "digest": digest})
        paths.append(path)
    if not files:
        raise ArchitectureError("source.files must contain at least one inspected source.")
    if len(paths) != len(set(paths)):
        raise ArchitectureError("source file paths must be unique.")
    return normalized


def read_regular(path: Path) -> bytes:
    if path.is_symlink():
        raise ArchitectureError("Input must not be a symlink.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ArchitectureError(f"Cannot read input: {path}") from exc
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ArchitectureError("Input must be a regular file.")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ArchitectureError("Input exceeds 2 MiB.")
    return raw


def parse(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ArchitectureError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ArchitectureError(f"Nonfinite number: {value}")
            ),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ArchitectureError(f"Invalid architecture JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ArchitectureError("Input must be an object.")
    canonical(value)
    return value


def validate(document: dict) -> dict:
    if document.get("schema") != SCHEMA or document.get("authority") != "none":
        raise ArchitectureError("Unsupported schema or authority.")
    if document.get("language") not in {"en", "zh-CN"}:
        raise ArchitectureError("language must be en or zh-CN.")

    subject = document.get("subject")
    source = document.get("source")
    if not isinstance(subject, dict) or not isinstance(source, dict):
        raise ArchitectureError("subject/source must be objects.")
    string(subject.get("title"), "subject.title", 256)
    string(subject.get("summary"), "subject.summary")
    string(source.get("repository"), "source.repository", 256)
    string(source.get("revision"), "source.revision", 128)
    files = source_files(source)
    expected_source_set = sha256(canonical(files))
    if hex_digest(source.get("source_set_sha256"), "source_set_sha256", 64) != expected_source_set:
        raise ArchitectureError("source_set_sha256 disagrees with source.files.")

    component_ids = []
    for index, component in enumerate(array(document.get("components"), "components")):
        if not isinstance(component, dict):
            raise ArchitectureError("Component must be an object.")
        component_ids.append(string(component.get("id"), f"component {index} id", 128))
        string(component.get("label"), "component label", 128)
        string(component.get("responsibility"), "component responsibility")
        for path in array(component.get("paths"), "component paths", 32):
            if string(path, "component path", 512) not in {item["path"] for item in files}:
                raise ArchitectureError(f"Component path is not in source.files: {path}")
    if len(component_ids) != len(set(component_ids)):
        raise ArchitectureError("Duplicate component ID.")
    known_components = set(component_ids)

    flow_ids = []
    for flow in array(document.get("flows"), "flows"):
        if not isinstance(flow, dict):
            raise ArchitectureError("Flow must be an object.")
        flow_ids.append(string(flow.get("id"), "flow id", 128))
        string(flow.get("title"), "flow title", 256)
        steps = array(flow.get("steps"), "flow steps", 64)
        if not steps:
            raise ArchitectureError("Flow needs at least one step.")
        for step in steps:
            if not isinstance(step, dict):
                raise ArchitectureError("Flow step must be an object.")
            actor = string(step.get("actor"), "flow actor", 128)
            if actor not in known_components:
                raise ArchitectureError(f"Unknown flow actor: {actor}")
            string(step.get("action"), "flow action")
            if step.get("condition") is not None:
                string(step["condition"], "flow condition")
    if len(flow_ids) != len(set(flow_ids)):
        raise ArchitectureError("Duplicate flow ID.")

    for field in ("invariants", "limitations"):
        for item in array(document.get(field), field):
            if not isinstance(item, dict):
                raise ArchitectureError(f"{field} item must be an object.")
            string(item.get("text"), field + " text")
            for ref in array(item.get("refs"), field + " refs", 32):
                string(ref, field + " ref", 512)

    evidence_ids = []
    source_paths = {item["path"] for item in files}
    for item in array(document.get("evidence"), "evidence"):
        if not isinstance(item, dict):
            raise ArchitectureError("Evidence must be an object.")
        evidence_ids.append(string(item.get("id"), "evidence id", 128))
        string(item.get("label"), "evidence label", 256)
        locator = string(item.get("locator"), "evidence locator", 512)
        if locator not in source_paths:
            raise ArchitectureError(f"Evidence locator is not in source.files: {locator}")
        if string(item.get("kind"), "evidence kind", 32) not in {
            "source",
            "test",
            "document",
            "measurement",
        }:
            raise ArchitectureError("Unsupported evidence kind.")
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ArchitectureError("Duplicate evidence ID.")

    if "sha256" in document:
        expected = document["sha256"]
        hex_digest(expected, "sha256", 64)
        copy = dict(document)
        copy.pop("sha256")
        if sha256(canonical(copy)) != expected:
            raise ArchitectureError("Document digest mismatch.")
    return document


def safe_json(value: object) -> str:
    return (
        canonical(value)
        .decode("utf-8")
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


SCRIPT = """const d=JSON.parse(document.getElementById('data').textContent),$=x=>document.getElementById(x),el=(t,s,c)=>{const n=document.createElement(t);n.textContent=s;if(c)n.className=c;return n};
$('title').textContent=d.subject.title;$('summary').textContent=d.subject.summary;$('source').textContent=JSON.stringify(d.source,null,2);$('digest').textContent='document sha256: '+(d.sha256||'not supplied');
const sec=[['model','System model',()=>{const x=el('div','');d.components.forEach(c=>{const n=el('div','', 'card');n.append(el('b',c.label),el('p',c.responsibility),el('code',c.paths.join(' · ')));x.append(n)});return x}],...d.flows.map(f=>['flow:'+f.id,f.title,()=>{const x=el('div','');f.steps.forEach(s=>{const n=el('div','', 'step');n.append(el('b',s.actor),el('span',' — '+s.action));if(s.condition)n.append(el('div','Condition: '+s.condition,'condition'));x.append(n)});return x}]),['invariants','Invariants',()=>{const x=el('div','');d.invariants.forEach(i=>{const n=el('div','', 'card');n.append(el('p',i.text),el('code',i.refs.join(' · ')));x.append(n)});return x}],['evidence','Evidence',()=>{const x=el('div','');d.evidence.forEach(e=>{const n=el('div','', 'card');n.append(el('b',e.label),el('p',e.kind),el('code',e.locator));x.append(n)});return x}]];
function show(i){$('view').replaceChildren(sec[i][2]());[...$('nav').children].forEach((b,j)=>b.setAttribute('aria-current',j===i?'true':'false'))}sec.forEach((s,i)=>{const b=el('button',s[1]);b.onclick=()=>show(i);$('nav').append(b)});d.limitations.forEach(i=>$('limits').append(el('p',i.text+' '+i.refs.join(' · '),'limit')));show(0);"""


def html_page(document: dict) -> bytes:
    validate(document)
    title = html.escape(document["subject"]["title"], quote=True)
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode("utf-8")).digest()).decode("ascii")
    csp = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; "
        "img-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-" + script_hash + "'"
    )
    template = """<!doctype html><html lang="@@LANG@@"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="@@CSP@@"><title>@@TITLE@@</title><style>
body{margin:0;background:#0e161d;color:#edf3ed;font:15px/1.65 system-ui}header,main{max-width:1200px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:240px minmax(0,1fr);gap:20px}.panel{background:#17242d;border:1px solid #3a4c53;border-radius:12px;padding:20px;min-width:0}button{width:100%;text-align:left;padding:9px;margin:4px 0;background:transparent;color:#b8c8ca;border:1px solid transparent;border-radius:6px;cursor:pointer}button[aria-current=true]{color:#b6f289;border-color:#3a4c53}.card{padding:14px 0;border-bottom:1px solid #3a4c53}.step{border-left:2px solid #b6f289;padding:10px 14px;margin:10px 0}.condition,.limit{color:#fed194}.small,code{font-size:12px;color:#b8c8ca;overflow-wrap:anywhere}button:focus-visible,summary:focus-visible{outline:2px solid #b6f289;outline-offset:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style></head>
<body><header><b>RepoFoundry / Architecture view</b><span>Derived view · authority none</span></header><main><h1 id="title"></h1><p id="summary"></p><div class="grid"><nav class="panel" id="nav" aria-label="Architecture sections"></nav><section class="panel" id="view"></section></div><section class="panel" style="margin-top:20px"><h2>Limits</h2><div id="limits"></div><details><summary>Source identity</summary><pre id="source"></pre></details><p class="small" id="digest"></p></section></main>
<script type="application/json" id="data">@@DATA@@</script><script>@@SCRIPT@@</script></body></html>"""
    return (
        template.replace("@@LANG@@", document["language"])
        .replace("@@CSP@@", html.escape(csp, quote=True))
        .replace("@@TITLE@@", title)
        .replace("@@DATA@@", safe_json(document))
        .replace("@@SCRIPT@@", SCRIPT)
        .encode("utf-8")
    )


def publish(output: Path, files: dict[str, bytes]) -> None:
    if output.exists() or output.is_symlink():
        raise ArchitectureError("Output exists; refusing overwrite.")
    output.mkdir(mode=0o700)
    for name, raw in files.items():
        descriptor = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        document = validate(parse(read_regular(args.input)))
        files = {
            "architecture.json": canonical(document) + b"\n",
            "index.html": html_page(document),
        }
        manifest = {
            "kind": "derived-architecture-render",
            "authority": "none",
            "schema": SCHEMA,
            "source_set_sha256": document["source"]["source_set_sha256"],
            "files": {name: sha256(raw) for name, raw in sorted(files.items())},
        }
        files["render-manifest.json"] = canonical(manifest) + b"\n"
        if args.apply:
            publish(args.output, files)
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "dry-run",
                    "output": str(args.output),
                    "files": sorted(files),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, UnicodeError, ArchitectureError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
