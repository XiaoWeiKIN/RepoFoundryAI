#!/usr/bin/env python3
"""Render a sealed Benchmark Run as a progressive, source-bound explanation view."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import benchctl

SCHEMA = "repofoundry.benchmark-explanation/v1"
MAX_BYTES = 2 * 1024 * 1024
CLAIM_KINDS = {"observation", "derived", "hypothesis", "mechanism"}
EVIDENCE_KINDS = {"measurement", "diagnostic", "source", "scenario", "result"}


class ExplanationError(ValueError):
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
        raise ExplanationError("Explanation input must be finite UTF-8 JSON.") from exc


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def string(value: object, name: str, maximum: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ExplanationError(f"{name} must be a bounded nonempty string.")
    return value


def array(value: object, name: str, maximum: int = 128) -> list:
    if not isinstance(value, list) or len(value) > maximum:
        raise ExplanationError(f"{name} must be a bounded array.")
    return value


def hex_sha(value: object, name: str) -> str:
    value = string(value, name, 64)
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ExplanationError(f"{name} must be a lowercase SHA-256.")
    return value


def read_regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ExplanationError(f"Expected a regular non-symlink input: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ExplanationError("Explanation input exceeds 2 MiB.")
    return raw


def parse(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ExplanationError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ExplanationError(f"Nonfinite number: {token}")
            ),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ExplanationError(f"Invalid explanation JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExplanationError("Explanation input must be an object.")
    canonical(value)
    return value


def sealed_run(repo: Path, run_id: str):
    run = benchctl.find_record(repo.resolve(), "BR", run_id)
    if run.metadata.get("status") != "sealed":
        raise ExplanationError(f"{run.identifier} must be sealed before it can be explained.")
    errors = benchctl.verify_manifest(run)
    if errors:
        raise ExplanationError("\n".join(errors))
    manifest_path = run.path.parent / "EVIDENCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ExplanationError("Evidence Manifest must be an object.")
    return run, manifest


def validate(document: dict, run, manifest: dict) -> dict:
    if document.get("schema") != SCHEMA or document.get("authority") != "none":
        raise ExplanationError("Unsupported schema or authority.")
    if document.get("language") not in {"en", "zh-CN"}:
        raise ExplanationError("language must be en or zh-CN.")

    source = document.get("source")
    subject = document.get("subject")
    if not isinstance(source, dict) or not isinstance(subject, dict):
        raise ExplanationError("source and subject must be objects.")

    expected_source = {
        "run_id": run.identifier,
        "suite_id": run.metadata.get("suite_id"),
        "scenario_id": run.metadata.get("scenario_id"),
        "outcome": run.metadata.get("outcome"),
        "subject_revision": run.metadata.get("subject_revision"),
        "harness_revision": run.metadata.get("harness_revision"),
        "manifest_payload_sha256": manifest.get("payload_sha256"),
    }
    for field, expected in expected_source.items():
        if source.get(field) != expected:
            raise ExplanationError(
                f"source.{field} must match the sealed Run: expected {expected!r}."
            )
    hex_sha(source.get("manifest_payload_sha256"), "manifest_payload_sha256")
    string(subject.get("title"), "subject.title", 256)
    string(subject.get("question"), "subject.question", 1024)
    string(subject.get("summary"), "subject.summary", 2048)

    manifest_paths = {
        item["path"] for item in manifest.get("files", []) if isinstance(item, dict)
    }
    evidence_by_id = {}
    for index, item in enumerate(array(document.get("evidence"), "evidence", 256)):
        if not isinstance(item, dict):
            raise ExplanationError(f"evidence[{index}] must be an object.")
        identifier = string(item.get("id"), "evidence id", 128)
        if identifier in evidence_by_id:
            raise ExplanationError(f"Duplicate evidence ID: {identifier}")
        kind = string(item.get("kind"), "evidence kind", 32)
        if kind not in EVIDENCE_KINDS:
            raise ExplanationError(f"Unsupported evidence kind: {kind}")
        path = string(item.get("path"), "evidence path", 512)
        if path not in manifest_paths:
            raise ExplanationError(f"Evidence path is not sealed by the Manifest: {path}")
        string(item.get("label"), "evidence label", 256)
        evidence_by_id[identifier] = item

    claims_by_id = {}
    for index, claim in enumerate(array(document.get("claims"), "claims", 256)):
        if not isinstance(claim, dict):
            raise ExplanationError(f"claims[{index}] must be an object.")
        identifier = string(claim.get("id"), "claim id", 128)
        if identifier in claims_by_id:
            raise ExplanationError(f"Duplicate claim ID: {identifier}")
        kind = string(claim.get("kind"), "claim kind", 32)
        if kind not in CLAIM_KINDS:
            raise ExplanationError(f"Unsupported claim kind: {kind}")
        string(claim.get("text"), "claim text", 2048)
        refs = array(claim.get("evidence_ids"), "claim evidence_ids", 32)
        if not refs or any(ref not in evidence_by_id for ref in refs):
            raise ExplanationError(f"{identifier} must reference known evidence.")
        evidence_kinds = {evidence_by_id[ref]["kind"] for ref in refs}
        if kind == "observation" and "measurement" not in evidence_kinds:
            raise ExplanationError(f"{identifier}: observation needs measurement evidence.")
        if kind == "derived":
            if "measurement" not in evidence_kinds:
                raise ExplanationError(f"{identifier}: derived claim needs measurement evidence.")
            string(claim.get("derivation"), f"{identifier}.derivation", 1024)
        if kind == "mechanism":
            missing = {"measurement", "diagnostic", "source"} - evidence_kinds
            if missing:
                raise ExplanationError(
                    f"{identifier}: mechanism interpretation needs measurement, "
                    f"diagnostic, and source evidence; missing {sorted(missing)}."
                )
        claims_by_id[identifier] = claim

    metrics = array(document.get("metrics"), "metrics", 32)
    metric_ids = set()
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            raise ExplanationError(f"metrics[{index}] must be an object.")
        identifier = string(metric.get("id"), "metric id", 128)
        if identifier in metric_ids:
            raise ExplanationError(f"Duplicate metric ID: {identifier}")
        metric_ids.add(identifier)
        string(metric.get("title"), "metric title", 256)
        string(metric.get("unit"), "metric unit", 64)
        for side in ("baseline", "candidate"):
            point = metric.get(side)
            if not isinstance(point, dict):
                raise ExplanationError(f"{identifier}.{side} must be an object.")
            string(point.get("label"), f"{identifier}.{side}.label", 128)
            value = point.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ExplanationError(f"{identifier}.{side}.value must be finite.")
            samples = point.get("samples")
            if type(samples) is not int or samples < 1:
                raise ExplanationError(f"{identifier}.{side}.samples must be a positive integer.")
            string(point.get("uncertainty"), f"{identifier}.{side}.uncertainty", 256)
            ref = string(point.get("evidence_id"), f"{identifier}.{side}.evidence_id", 128)
            if ref not in evidence_by_id or evidence_by_id[ref]["kind"] != "measurement":
                raise ExplanationError(f"{identifier}.{side} must reference measurement evidence.")

    steps = array(document.get("mechanism_steps"), "mechanism_steps", 32)
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ExplanationError(f"mechanism_steps[{index}] must be an object.")
        string(step.get("label"), "mechanism step label", 128)
        string(step.get("baseline"), "mechanism baseline", 512)
        string(step.get("candidate"), "mechanism candidate", 512)
        claim_id = step.get("claim_id")
        if claim_id is not None:
            claim_id = string(claim_id, "mechanism claim_id", 128)
            if claim_id not in claims_by_id or claims_by_id[claim_id]["kind"] not in {
                "hypothesis",
                "mechanism",
            }:
                raise ExplanationError(
                    "mechanism step claim_id must reference a hypothesis or mechanism claim."
                )

    limitations = array(document.get("limitations"), "limitations", 64)
    if not limitations:
        raise ExplanationError("At least one limitation is required.")
    for limitation in limitations:
        string(limitation, "limitation", 1024)

    if "sha256" in document:
        expected = hex_sha(document["sha256"], "sha256")
        projection = dict(document)
        projection.pop("sha256")
        if sha256(canonical(projection)) != expected:
            raise ExplanationError("Document digest mismatch.")
    return document


def safe_json(value: object) -> str:
    return (
        canonical(value)
        .decode("utf-8")
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


SCRIPT = r"""const d=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),el=(tag,text,cls)=>{const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n};
const zh=d.language==='zh-CN',ui=zh?{question:'问题与预测',measurement:'实测差异',diagnostic:'诊断证据',mechanism:'机制解释',limits:'边界与未证明',play:'播放',pause:'暂停',observed:'观察',derived:'推导',hypothesis:'假说',mechanismClaim:'机制解释',samples:'样本'}:{question:'Question & predictions',measurement:'Measured difference',diagnostic:'Diagnostic evidence',mechanism:'Mechanism explanation',limits:'Limits & not established',play:'Play',pause:'Pause',observed:'Observation',derived:'Derived',hypothesis:'Hypothesis',mechanismClaim:'Mechanism interpretation',samples:'samples'};
const evidence=Object.fromEntries(d.evidence.map(x=>[x.id,x])),claimsByKind=k=>d.claims.filter(x=>x.kind===k);
const claimCard=c=>{const n=el('div','', 'claim '+c.kind);n.append(el('div',({observation:ui.observed,derived:ui.derived,hypothesis:ui.hypothesis,mechanism:ui.mechanismClaim})[c.kind],'kind'),el('p',c.text));if(c.derivation)n.append(el('code',c.derivation));const refs=el('div','', 'refs');c.evidence_ids.forEach(id=>refs.append(el('span',evidence[id].label+' · '+evidence[id].path,'ref')));n.append(refs);return n};
const metricView=()=>{const x=el('div','');d.metrics.forEach(m=>{const card=el('div','', 'metric');card.append(el('h3',m.title));const max=Math.max(Math.abs(m.baseline.value),Math.abs(m.candidate.value),1);for(const key of ['baseline','candidate']){const p=m[key],row=el('div','', 'metricrow'),head=el('div',p.label+' — '+p.value+' '+m.unit+' · '+p.samples+' '+ui.samples+' · '+p.uncertainty,'small'),track=el('div','', 'bartrack'),bar=el('div','', 'bar');bar.style.width=(Math.abs(p.value)/max*100)+'%';track.append(bar);row.append(head,track);card.append(row)}x.append(card)});claimsByKind('observation').concat(claimsByKind('derived')).forEach(c=>x.append(claimCard(c)));return x};
const diagnosticView=()=>{const x=el('div','', 'chain');for(const k of ['measurement','diagnostic','source']){const col=el('section','', 'chaincol');col.append(el('h3',k));d.evidence.filter(e=>e.kind===k).forEach(e=>{const n=el('div','', 'evidence');n.append(el('b',e.label),el('code',e.path));col.append(n)});x.append(col)}return x};
const mechanismView=()=>{const x=el('div','');const tracks=el('div','', 'tracks'),base=el('div','', 'track'),cand=el('div','', 'track');base.append(el('h3','Baseline'));cand.append(el('h3','Candidate'));d.mechanism_steps.forEach(s=>{base.append(el('div',s.label+' — '+s.baseline,'node'));cand.append(el('div',s.label+' — '+s.candidate,'node'))});tracks.append(base,cand);x.append(tracks);claimsByKind('mechanism').concat(claimsByKind('hypothesis')).forEach(c=>x.append(claimCard(c)));return x};
const scenes=[
 {title:ui.question,render:()=>{const x=el('div','');x.append(el('h2',d.subject.question),el('p',d.subject.summary));claimsByKind('hypothesis').forEach(c=>x.append(claimCard(c)));return x}},
 {title:ui.measurement,render:metricView},
 {title:ui.diagnostic,render:diagnosticView},
 {title:ui.mechanism,render:mechanismView},
 {title:ui.limits,render:()=>{const x=el('div','');d.limitations.forEach(v=>x.append(el('p',v,'limit')));x.append(el('code',d.source.run_id+' @ '+d.source.manifest_payload_sha256));return x}}
];
let index=0,timer=null;function show(i){index=Math.max(0,Math.min(scenes.length-1,i));$('view').replaceChildren(scenes[index].render());$('scene-title').textContent=scenes[index].title;[...$('nav').children].forEach((b,j)=>b.setAttribute('aria-current',j===index?'true':'false'));$('progress').value=index;$('progress-label').textContent=(index+1)+' / '+scenes.length}
function stop(){$('play').textContent=ui.play;if(timer!==null)clearInterval(timer);timer=null}
scenes.forEach((s,i)=>{const b=el('button',s.title);b.onclick=()=>{stop();show(i)};$('nav').append(b)});$('progress').max=scenes.length-1;$('progress').oninput=()=>{stop();show(Number($('progress').value))};$('play').textContent=ui.play;$('play').onclick=()=>{if(timer!==null){stop();return}$('play').textContent=ui.pause;timer=setInterval(()=>{if(index>=scenes.length-1){stop();return}show(index+1)},2800)};$('title').textContent=d.subject.title;$('source').textContent=JSON.stringify(d.source,null,2);show(0);"""


def html_page(document: dict) -> bytes:
    labels = (
        {
            "badge": "Benchmark 派生解释 · 无决策授权",
            "nav": "解释步骤",
            "source": "封存来源",
            "note": "动画用于解释证据，不改变 sealed outcome，也不证明未被证据支持的因果关系。",
        }
        if document["language"] == "zh-CN"
        else {
            "badge": "Derived Benchmark explanation · no decision authority",
            "nav": "Explanation steps",
            "source": "Sealed source",
            "note": "Animation explains evidence; it does not change the sealed outcome or establish unsupported causality.",
        }
    )
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    csp = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; "
        "img-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-" + script_hash + "'"
    )
    template = """<!doctype html><html lang="@@LANG@@"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="@@CSP@@"><title>@@TITLE@@</title><style>
:root{--bg:#0b1017;--panel:#141d28;--ink:#eef4f1;--muted:#aebec5;--line:#344555;--accent:#74d7ff;--green:#9cec8f;--amber:#ffd27a;--violet:#c7a7ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}header,main{max-width:1280px;margin:auto;padding:22px}header{display:flex;justify-content:space-between;gap:18px;border-bottom:1px solid var(--line);flex-wrap:wrap}h1{font-size:clamp(28px,4vw,46px);line-height:1.16}.grid{display:grid;grid-template-columns:250px minmax(0,1fr);gap:22px}.panel{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px}nav button{width:100%;text-align:left;margin:0 0 8px;padding:9px;background:transparent;color:var(--muted);border:1px solid transparent;border-radius:7px;cursor:pointer}nav button[aria-current=true]{color:var(--accent);border-color:var(--line);background:#192838}button:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.controls{display:flex;gap:12px;align-items:center;margin-top:18px}.controls button{padding:8px 13px;background:transparent;border:1px solid var(--line);border-radius:7px;color:var(--ink)}.controls input{flex:1}.kind{font:11px ui-monospace,monospace;text-transform:uppercase;color:var(--accent)}.claim,.metric,.evidence,.node{border:1px solid var(--line);border-radius:9px;padding:13px;margin:10px 0}.claim.hypothesis{border-color:var(--violet)}.claim.mechanism{border-color:var(--green)}.refs{display:flex;flex-wrap:wrap;gap:6px}.ref{font:11px ui-monospace,monospace;color:var(--muted);border:1px solid var(--line);padding:3px 6px;border-radius:5px}.metricrow{margin:12px 0}.small{font-size:12px;color:var(--muted)}.bartrack{height:12px;background:#0b1017;border-radius:999px;overflow:hidden}.bar{height:100%;background:var(--accent);transition:width .7s ease}.chain,.tracks{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.tracks{grid-template-columns:1fr 1fr}.chaincol h3{text-transform:capitalize}.node{border-left:3px solid var(--green)}.limit{border-left:2px solid var(--amber);padding:9px 13px;color:var(--amber)}code,pre{font:12px/1.6 ui-monospace,monospace;overflow-wrap:anywhere;white-space:pre-wrap}.note{color:var(--muted);max-width:900px}@media(max-width:800px){.grid,.chain,.tracks{grid-template-columns:1fr}header,main{padding:16px}}@media(prefers-reduced-motion:reduce){.bar{transition:none}}</style></head><body><header><b>RepoFoundry / Benchmark explanation</b><span>@@BADGE@@</span></header><main><h1 id="title"></h1><p class="note">@@NOTE@@</p><div class="grid"><aside class="panel"><nav id="nav" aria-label="@@NAV@@"></nav><div class="controls"><button id="play"></button></div></aside><section class="panel"><h2 id="scene-title"></h2><div id="view"></div><div class="controls"><input id="progress" type="range" min="0" value="0" aria-label="@@NAV@@"><span id="progress-label" class="small"></span></div></section></div><section class="panel" style="margin-top:20px"><details><summary>@@SOURCE@@</summary><pre id="source"></pre></details></section></main><script type="application/json" id="data">@@DATA@@</script><script>@@SCRIPT@@</script></body></html>"""
    return (
        template.replace("@@LANG@@", document["language"])
        .replace("@@CSP@@", html.escape(csp, quote=True))
        .replace("@@TITLE@@", html.escape(document["subject"]["title"], quote=True))
        .replace("@@BADGE@@", html.escape(labels["badge"]))
        .replace("@@NOTE@@", html.escape(labels["note"]))
        .replace("@@NAV@@", html.escape(labels["nav"], quote=True))
        .replace("@@SOURCE@@", html.escape(labels["source"]))
        .replace("@@DATA@@", safe_json(document))
        .replace("@@SCRIPT@@", SCRIPT)
        .encode("utf-8")
    )


def output_files(document: dict) -> dict[str, bytes]:
    files = {
        "benchmark-explanation.json": canonical(document) + b"\n",
        "index.html": html_page(document),
    }
    manifest = {
        "kind": "derived-benchmark-render",
        "authority": "none",
        "schema": SCHEMA,
        "run_id": document["source"]["run_id"],
        "benchmark_manifest_payload_sha256": document["source"][
            "manifest_payload_sha256"
        ],
        "files": {name: sha256(raw) for name, raw in sorted(files.items())},
    }
    files["render-manifest.json"] = canonical(manifest) + b"\n"
    return files


def publish(output: Path, files: dict[str, bytes], sealed_directory: Path) -> None:
    target = output.resolve()
    sealed = sealed_directory.resolve()
    if target == sealed or sealed in target.parents:
        raise ExplanationError("Derived output must stay outside the sealed Run directory.")
    if output.exists() or output.is_symlink():
        raise ExplanationError("Output exists; refusing overwrite.")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ExplanationError("Output parent must be an existing regular directory.")
    output.mkdir(mode=0o700)
    ordered = [name for name in sorted(files) if name != "render-manifest.json"]
    ordered.append("render-manifest.json")
    for name in ordered:
        raw = files[name]
        descriptor = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        run, manifest = sealed_run(args.repo, args.run)
        document = validate(parse(read_regular(args.input)), run, manifest)
        files = output_files(document)
        if args.apply:
            publish(args.output, files, run.path.parent)
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "dry-run",
                    "run": run.identifier,
                    "manifest_payload_sha256": manifest["payload_sha256"],
                    "output": str(args.output),
                    "files": sorted(files),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, UnicodeError, ExplanationError, benchctl.BenchmarkError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
