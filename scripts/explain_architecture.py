#!/usr/bin/env python3
"""Render a bounded source-bound architecture JSON as an offline HTML reading view."""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, stat, sys
from pathlib import Path

SCHEMA="repofoundry.architecture-explanation/v1"
MAX_BYTES=2*1024*1024
class ArchitectureError(ValueError): pass

def canonical(v):
    try:return json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(",",":")).encode()
    except (TypeError,ValueError,UnicodeError,RecursionError) as e:raise ArchitectureError("Input must be finite UTF-8 JSON.") from e
def sha256(v):return hashlib.sha256(v).hexdigest()
def string(v,name,n=2048):
    if not isinstance(v,str) or not v.strip() or len(v)>n:raise ArchitectureError(f"{name} must be a bounded nonempty string.")
    return v
def array(v,name,n=128):
    if not isinstance(v,list) or len(v)>n:raise ArchitectureError(f"{name} must be a bounded array.")
    return v
def digest(v,name):
    v=string(v,name,64)
    if len(v)!=64 or re.search("[^0-9a-f]",v):raise ArchitectureError(f"{name} must be lowercase SHA-256.")
    return v
def read(path):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):raise ArchitectureError("Input must be a regular non-symlink file.")
    raw=path.read_bytes()
    if len(raw)>MAX_BYTES:raise ArchitectureError("Input exceeds 2 MiB.")
    return raw
def parse(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ArchitectureError(f"Duplicate JSON key: {k}")
            out[k]=v
        return out
    try:v=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ArchitectureError(f"Nonfinite number: {x}")))
    except (ValueError,UnicodeError,RecursionError) as e:raise ArchitectureError(f"Invalid architecture JSON: {e}") from e
    if not isinstance(v,dict):raise ArchitectureError("Input must be an object.")
    canonical(v);return v

def validate(d):
    if d.get("schema")!=SCHEMA or d.get("authority")!="none":raise ArchitectureError("Unsupported schema or authority.")
    s=d.get("subject");src=d.get("source")
    if not isinstance(s,dict) or not isinstance(src,dict):raise ArchitectureError("subject/source must be objects.")
    string(s.get("title"),"subject.title",256);string(s.get("summary"),"subject.summary")
    string(src.get("repository"),"source.repository",256);string(src.get("revision"),"source.revision",128);digest(src.get("source_set_sha256"),"source digest")
    ids=[]
    for i,c in enumerate(array(d.get("components"),"components")):
        if not isinstance(c,dict):raise ArchitectureError("Component must be an object.")
        ids.append(string(c.get("id"),f"component {i} id",128));string(c.get("label"),"component label",128);string(c.get("responsibility"),"component responsibility")
        for p in array(c.get("paths"),"component paths",32):string(p,"component path",512)
    if len(ids)!=len(set(ids)):raise ArchitectureError("Duplicate component ID.")
    known=set(ids)
    flowids=[]
    for f in array(d.get("flows"),"flows"):
        if not isinstance(f,dict):raise ArchitectureError("Flow must be an object.")
        flowids.append(string(f.get("id"),"flow id",128));string(f.get("title"),"flow title",256)
        steps=array(f.get("steps"),"flow steps",64)
        if not steps:raise ArchitectureError("Flow needs at least one step.")
        for st in steps:
            if not isinstance(st,dict):raise ArchitectureError("Flow step must be an object.")
            actor=string(st.get("actor"),"flow actor",128)
            if actor not in known:raise ArchitectureError(f"Unknown flow actor: {actor}")
            string(st.get("action"),"flow action")
            if st.get("condition") is not None:string(st["condition"],"flow condition")
    if len(flowids)!=len(set(flowids)):raise ArchitectureError("Duplicate flow ID.")
    for field in ("invariants","limitations"):
        for item in array(d.get(field),field):
            if not isinstance(item,dict):raise ArchitectureError(f"{field} item must be an object.")
            string(item.get("text"),field+" text")
            for ref in array(item.get("refs"),field+" refs",32):string(ref,field+" ref",512)
    evid=[]
    for e in array(d.get("evidence"),"evidence"):
        if not isinstance(e,dict):raise ArchitectureError("Evidence must be an object.")
        evid.append(string(e.get("id"),"evidence id",128));string(e.get("label"),"evidence label",256);string(e.get("locator"),"evidence locator",512)
        if string(e.get("kind"),"evidence kind",32) not in {"source","test","document","measurement"}:raise ArchitectureError("Unsupported evidence kind.")
    if len(evid)!=len(set(evid)):raise ArchitectureError("Duplicate evidence ID.")
    if "sha256" in d:
        expected=d["sha256"];digest(expected,"sha256");copy=dict(d);copy.pop("sha256")
        if sha256(canonical(copy))!=expected:raise ArchitectureError("Document digest mismatch.")
    return d

def safe(v):return canonical(v).decode().replace("<","\\u003c").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
def page(d):
    validate(d);data=safe(d);title=html.escape(d["subject"]["title"],quote=True)
    tpl='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src 'none';connect-src 'none';img-src 'none';style-src 'unsafe-inline';script-src 'unsafe-inline'"><title>@@TITLE@@</title><style>
body{margin:0;background:#0e161d;color:#edf3ed;font:15px/1.65 system-ui}header,main{max-width:1200px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:240px 1fr;gap:20px}.panel{background:#17242d;border:1px solid #3a4c53;border-radius:12px;padding:20px}button{width:100%;text-align:left;padding:9px;margin:4px 0;background:transparent;color:#b8c8ca;border:1px solid transparent;border-radius:6px}button[aria-current=true]{color:#b6f289;border-color:#3a4c53}.card{padding:14px 0;border-bottom:1px solid #3a4c53}.step{border-left:2px solid #b6f289;padding:10px 14px;margin:10px 0}.condition,.limit{color:#fed194}.small,code{font-size:12px;color:#b8c8ca}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style></head>
<body><header><b>RepoFoundry / Architecture view</b><span>Derived view · authority none</span></header><main><h1 id="title"></h1><p id="summary"></p><div class="grid"><nav class="panel" id="nav"></nav><section class="panel" id="view"></section></div><section class="panel" style="margin-top:20px"><h2>Limits</h2><div id="limits"></div><details><summary>Source identity</summary><pre id="source"></pre></details><p class="small" id="digest"></p></section></main>
<script type="application/json" id="data">@@DATA@@</script><script>
const d=JSON.parse(document.getElementById('data').textContent),$=x=>document.getElementById(x),el=(t,s,c)=>{const n=document.createElement(t);n.textContent=s;if(c)n.className=c;return n};
$('title').textContent=d.subject.title;$('summary').textContent=d.subject.summary;$('source').textContent=JSON.stringify(d.source,null,2);$('digest').textContent='document sha256: '+(d.sha256||'not supplied');
const sec=[['model','System model',()=>{const x=el('div','');d.components.forEach(c=>{const n=el('div','', 'card');n.append(el('b',c.label),el('p',c.responsibility),el('code',c.paths.join(' · ')));x.append(n)});return x}],...d.flows.map(f=>['flow:'+f.id,f.title,()=>{const x=el('div','');f.steps.forEach(s=>{const n=el('div','', 'step');n.append(el('b',s.actor),el('span',' — '+s.action));if(s.condition)n.append(el('div','Condition: '+s.condition,'condition'));x.append(n)});return x}]),['invariants','Invariants',()=>{const x=el('div','');d.invariants.forEach(i=>{const n=el('div','', 'card');n.append(el('p',i.text),el('code',i.refs.join(' · ')));x.append(n)});return x}],['evidence','Evidence',()=>{const x=el('div','');d.evidence.forEach(e=>{const n=el('div','', 'card');n.append(el('b',e.label),el('p',e.kind),el('code',e.locator));x.append(n)});return x}]];
function show(i){$('view').replaceChildren(sec[i][2]());[...$('nav').children].forEach((b,j)=>b.setAttribute('aria-current',j===i?'true':'false'))}sec.forEach((s,i)=>{const b=el('button',s[1]);b.onclick=()=>show(i);$('nav').append(b)});d.limitations.forEach(i=>$('limits').append(el('p',i.text+' '+i.refs.join(' · '),'limit')));show(0);
</script></body></html>'''
    return tpl.replace("@@TITLE@@",title).replace("@@DATA@@",data).encode()

def publish(out,files):
    if out.exists() or out.is_symlink():raise ArchitectureError("Output exists; refusing overwrite.")
    out.mkdir(mode=0o700)
    for name,raw in files.items():
        fd=os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:f.write(raw)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",required=True,type=Path);p.add_argument("--output",required=True,type=Path);p.add_argument("--apply",action="store_true");a=p.parse_args(argv)
    try:
        d=validate(parse(read(a.input)));files={"architecture.json":canonical(d)+b"\n","index.html":page(d)}
        manifest={"kind":"derived-architecture-render","authority":"none","schema":SCHEMA,"source_set_sha256":d["source"]["source_set_sha256"],"files":{n:sha256(v) for n,v in sorted(files.items())}}
        files["render-manifest.json"]=canonical(manifest)+b"\n"
        if a.apply:publish(a.output,files)
        print(json.dumps({"mode":"apply" if a.apply else "dry-run","output":str(a.output),"files":sorted(files)},ensure_ascii=False));return 0
    except (OSError,UnicodeError,ArchitectureError) as e:print(json.dumps({"error":str(e)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
