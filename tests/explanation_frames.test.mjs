// Optional developer check; does not add Node as a core Python dependency.
import test from 'node:test';
import assert from 'node:assert/strict';
import {atFrame, nodeLayout} from '../assets/explain/frame-model.mjs';
const ir={schema:'repofoundry.explanation/v1',timeline:{duration_frames:360},
  scenes:[{id:'a',from_frame:0,duration_frames:180,statement_ids:['s']},{id:'b',from_frame:180,duration_frames:180,statement_ids:['s']}],
  statements:[{id:'s',text:'Explicit frame-model test fixture'}],graph:{nodes:[{id:'A',role:'direct'},{id:'B',role:'context_dependency'}]}};
test('seeking is deterministic in either direction',()=>{
  const a=atFrame(ir,210), layout=nodeLayout(ir,210);
  for(const n of [350,0,180,20,210])atFrame(ir,n);
  assert.deepEqual(atFrame(ir,210),a);
  assert.deepEqual(nodeLayout(ir,210),layout);
});
test('frame boundaries and finite input',()=>{
  assert.equal(atFrame(ir,179).index,0); assert.equal(atFrame(ir,180).index,1);
  assert.equal(atFrame(ir,-99).frame,0); assert.equal(atFrame(ir,900).frame,359);
  for(const n of [NaN,Infinity,-Infinity])assert.throws(()=>atFrame(ir,n));
});
test('missing scene and invalid schema fail',()=>{
  assert.throws(()=>atFrame({...ir,schema:'v2'},0));
  assert.throws(()=>atFrame({...ir,scenes:[]},0));
});

import {atPresentedFrame} from '../assets/explain/frame-model.mjs';
const source={...ir,sha256:'fixture-ir',source:{sha256:'fixture-source'}};
const reading={schema:'repofoundry.presentation/v1',language:'zh-CN',authority:'none',
  ir_sha256:source.sha256,source_sha256:source.source.sha256,
  scenes:{a:'01 / 计划文件',b:'02 / 候选规范'},statements:{s:'中文阅读文本'}};
test('localized frames are deterministic and do not mutate source facts',()=>{
  const before=structuredClone(source), a=atPresentedFrame(source,reading,210);
  for(const frame of [0,359,179,180])atPresentedFrame(source,reading,frame);
  assert.deepEqual(atPresentedFrame(source,reading,210),a);
  assert.equal(a.scene.title,'02 / 候选规范');
  assert.equal(a.statements[0].text,'中文阅读文本');
  assert.equal(a.frame,atFrame(source,210).frame);
  assert.deepEqual(source,before);
});
test('mismatched source, unsupported locale, and missing labels fail',()=>{
  for(const invalid of [{...reading,ir_sha256:'wrong'}, {...reading,source_sha256:'wrong'},
    {...reading,authority:'approved'}, {...reading,language:'fr'}, {...reading,scenes:{}},
    {...reading,statements:{}}])assert.throws(()=>atPresentedFrame(source,invalid,0));
});

import {mechanismModel,mechanismFrame} from '../assets/explain/frame-model.mjs';
// Explicit synthetic graph; no bundled normative Spec corpus.
function fixture(dependencies={A:['B','C'],B:['D'],C:['D'],D:[]},selected=['A'],whole=[]) {
  const resolved=Object.entries(dependencies).map(([id,deps])=>({id,spec_id:'sample/spec',
    source:selected.includes(id)?'direct':'context_dependency',context_dependencies:deps}));
  const snapshot={kind:'read-only-preview',authority:'none',receipt_created:false,
    paths:['docs/说明.md'],specs:[{id:'sample/spec',applies_to:['**/*.md']}],direct:selected,
    whole_specs:whole,resolved,edges:resolved.flatMap(r=>r.context_dependencies.map(to=>({from:r.id,to}))),
    capsule:selected.length||whole.length?{bytes:7,budget_bytes:100,sha256:'fixture',text:'Example'}:null};
  return {schema:'repofoundry.explanation/v1',authority:'none',source:{snapshot},
    timeline:{duration_frames:1080},scenes:['paths','candidates','selection','closure','capsule','authority'].map((id,i)=>
      ({id,from_frame:i*180,duration_frames:180,statement_ids:[id]}))};
}
test('mechanism uses captured candidates without manufacturing per-path matches',()=>{
  const m=mechanismModel(fixture());
  assert.deepEqual(m.paths,[{id:'docs/说明.md',ref:'/paths/0'}]);
  assert.deepEqual(m.candidates,[{id:'sample/spec',ref:'/specs/0',scopes:['**/*.md']}]);
  assert(!('matches' in m));
  assert.equal(m.direct[0].id,'A');
  assert.equal(m.nodes.filter(n=>n.direct).length,1);
});
test('a shared dependency has one node and all source edges',()=>{
  const src=fixture(),m=mechanismModel(src);
  assert.equal(m.nodes.filter(n=>n.id==='D').length,1);
  assert.deepEqual(m.edges,src.source.snapshot.edges);
  assert.equal(m.nodes.find(n=>n.id==='D').rank,2);
  for(const edge of m.edges)assert(m.nodes.find(n=>n.id===edge.to).rank>m.nodes.find(n=>n.id===edge.from).rank);
});
test('topological reading layers honor long and short paths to the same dependency',()=>{
  const m=mechanismModel(fixture({A:['B','D'],B:['C'],C:['D'],D:[]}));
  assert.equal(m.nodes.find(n=>n.id==='D').rank,3);
  assert.equal(m.readable,true);
});
test('all six phases have closed-form motion and settle without source mutation',()=>{
  const src=fixture(),before=structuredClone(src),m=mechanismModel(src),original=structuredClone(m);
  for(let i=0;i<6;i++){
    const start=mechanismFrame(m,i*180+12), end=mechanismFrame(m,i*180+135);
    assert.equal(start.stage,i);assert.notDeepEqual(start,end);
    for(const f of [1079,0,540,720])mechanismFrame(m,f);
    assert.deepEqual(mechanismFrame(m,i*180+12),start);
  }
  assert.deepEqual(src,before);assert.deepEqual(m,original);
  assert.equal(mechanismFrame(m,539).edges.every(e=>e.progress===0),true);
  assert.equal(mechanismFrame(m,710).edges.every(e=>e.progress===1),true);
  assert.equal(mechanismFrame(m,899).assembly,1);
});
test('empty, whole-Spec and mixed choices stay distinct and grant no authority',()=>{
  for(const [src,cap,whole] of [[fixture({},[],[]),false,0],
    [fixture({},[],['legacy/spec']),true,1],[fixture(undefined,['A'],['legacy/spec']),true,1]]){
    const m=mechanismModel(src);assert.equal(Boolean(m.capsule),cap);assert.equal(m.whole.length,whole);
    assert.equal(m.authority,'none');assert.equal(m.receipt_created,false);
    assert.equal(mechanismFrame(m,1079).boundary,1);
  }
});
test('capsule budget is captured data, not an animated count or estimated byte sum',()=>{
  const m=mechanismModel(fixture());
  for(const frame of [720,770,899,1079])mechanismFrame(m,frame);
  assert.deepEqual(m.capsule,{bytes:7,budget:100,sha256:'fixture',ref:'/capsule'});
});
test('large or wide graphs fall back explicitly without dropping source nodes',()=>{
  const chain=Object.fromEntries(Array.from({length:20},(_,i)=>['R'+i,i===19?[]:['R'+(i+1)]]));
  const m=mechanismModel(fixture(chain,['R0']));
  assert.equal(m.readable,false);assert.equal(m.nodes.length,20);assert.equal(m.edges.length,19);
  const wide='中文'.repeat(12),w=mechanismModel(fixture({[wide]:[]},[wide]));
  assert.equal(w.readable,false);assert.equal(w.nodes[0].id,wide);
});
test('mechanism rejects cycles, unselected nodes, changed edges and false authority',()=>{
  const invalid=[];
  invalid.push(fixture({A:['B'],B:['A']}));
  invalid.push(fixture({A:[],Z:[]}));
  const edges=fixture();edges.source.snapshot.edges.pop();invalid.push(edges);
  const granted=fixture();granted.source.snapshot.receipt_created=true;invalid.push(granted);
  const missing=fixture();missing.source.snapshot.resolved.pop();invalid.push(missing);
  const budget=fixture();budget.source.snapshot.capsule.bytes=101;invalid.push(budget);
  const storyboard=fixture();storyboard.scenes.reverse();invalid.push(storyboard);
  for(const bad of invalid)assert.throws(()=>mechanismModel(bad));
});
test('mechanism frame boundaries reject nonfinite frames',()=>{
  const m=mechanismModel(fixture());
  assert.equal(mechanismFrame(m,-3).frame,0);assert.equal(mechanismFrame(m,9000).frame,1079);
  for(const f of [NaN,Infinity,-Infinity])assert.throws(()=>mechanismFrame(m,f));
});

test('selection motion starts at its captured owning Spec, never an unrelated candidate',()=>{
  const src=fixture();src.source.snapshot.specs.unshift({id:'other/spec',applies_to:['**/*']});
  const m=mechanismModel(src), start=mechanismFrame(m,360), end=mechanismFrame(m,490);
  assert.equal(start.direct[0].y,185);
  assert.equal(end.direct[0].y,100);
  assert.deepEqual(end.candidates.map(c=>c.selected),[false,true]);
  assert.deepEqual(mechanismFrame(m,300).candidates.map(c=>c.selected),[false,false]);
});

import fs from 'node:fs';
import vm from 'node:vm';
const p5Source=fs.readFileSync(new URL('../assets/explain/p5-visual.mjs',import.meta.url),'utf8');
function p5Unit(count=5,{width=320,longLabel=false,runtime=true}={}){
  // Unit-only drawing recorder. Real p5 coverage lives in tests/runtime/run.mjs.
  const nodes=Array.from({length:count},(_,i)=>({id:longLabel&&i===0?'长'.repeat(100):`DOC-STATE-${i}`,role:i?'context_dependency':'direct'}));
  const source={graph:{nodes,edges:nodes.slice(1).map(n=>({from:nodes[0].id,to:n.id}))}};
  const disclosure={open:false}, visual={clientWidth:width};
  const elements={visual,'visual-note':{textContent:''},relationships:{closest:()=>disclosure}};
  const recorded={text:[],lines:[],canvas:null,description:null,observer:null};
  const p={LEFT:'left',TOP:'top',
    textFont:()=>{},textSize:size=>{recorded.size=size;},textLeading:()=>{},textAlign:()=>{},
    textWidth:text=>[...text].length*8,createCanvas:(w,h)=>{recorded.canvas={width:w,height:h};},
    resizeCanvas:(w,h,noRedraw)=>{assert.equal(noRedraw,true);recorded.canvas={width:w,height:h};},
    noLoop:()=>{},describe:text=>{recorded.description=text;},background:()=>{},
    noStroke:()=>{},stroke:()=>{},strokeWeight:()=>{},fill:()=>{},rect:()=>{},
    line:(...args)=>recorded.lines.push(args),
    text:(text,x,y)=>recorded.text.push({text,x,y,size:recorded.size})};
  function P5(sketch){sketch(p);p.setup();this.redraw=()=>{recorded.text=[];recorded.lines=[];p.draw();};}
  const context={window:{p5:runtime?P5:undefined},ir:source,frame:540,drawVisual:()=>{},
    $:id=>elements[id],reading:{font_family:'fixture-font'},
    ui:{direct:'直接选择',dependency:'上下文依赖',p5_missing:'missing',large_graph:'large',
      graph_note:'graph',p5_pan_hint:'pan',empty_graph:'empty',p5_description:'description',seek_hint:'seek'},
    ResizeObserver:class{constructor(fn){recorded.observer=fn;}observe(){ }},
    atFrame:(_,frame)=>({index:Math.floor(frame/180),overall:(frame+1)/1080})};
  const before=structuredClone(source);vm.runInNewContext(p5Source,context);context.drawVisual();
  return {context,source,before,recorded,disclosure,visual,elements};
}
test('p5 canvas is not CSS-scaled below readable font size',()=>{
  const css=fs.readFileSync(new URL('../assets/explain/story.html.template',import.meta.url),'utf8');
  assert.match(css,/\.visual canvas\{max-width:none;display:block\}/);
  const {recorded}=p5Unit();assert.equal(recorded.canvas.width,800);
  assert(recorded.text.length>0);assert(recorded.text.every(t=>t.size===16));
});
test('p5 wraps full IDs and separates rows for 24 nodes',()=>{
  const {source,recorded}=p5Unit(24);
  assert.equal(recorded.text.length,24);
  recorded.text.forEach((item,i)=>{
    assert.equal(item.text.split('\n').slice(0,-1).join(''),source.graph.nodes[i].id);
    assert(item.x>=0&&item.x+144<=800);
    assert(item.y+item.text.split('\n').length*22<recorded.canvas.height-20);
  });
  assert(recorded.text[4].y>recorded.text[0].y+recorded.text[0].text.split('\n').length*22);
  assert.equal(recorded.lines.length,source.graph.edges.length*3);
  assert(recorded.lines.every(line=>line.every(Number.isFinite)));
});
test('p5 reveals the text alternative once on narrow layout or later resize',()=>{
  const a=p5Unit();assert.equal(a.disclosure.open,true);
  a.disclosure.open=false;a.recorded.observer();assert.equal(a.disclosure.open,false);
  const b=p5Unit(5,{width:900});assert.equal(b.disclosure.open,false);
  b.visual.clientWidth=320;b.recorded.observer();assert.equal(b.disclosure.open,true);
});
test('p5 long labels and oversized graphs use an explicit complete-source fallback',()=>{
  for(const a of [p5Unit(25),p5Unit(5,{longLabel:true})]){
    assert.equal(a.elements['visual-note'].textContent,'large');
    assert.equal(a.recorded.text.length,0);assert.deepEqual(a.source,a.before);
    assert.equal(a.disclosure.open,true);
  }
});
test('p5 reverse seeking preserves exact source and drawing positions',()=>{
  const a=p5Unit(),first={text:structuredClone(a.recorded.text),lines:structuredClone(a.recorded.lines)};
  a.context.frame=900;a.context.drawVisual();a.context.frame=540;a.context.drawVisual();
  assert.deepEqual(a.recorded.text,first.text);assert.deepEqual(a.recorded.lines,first.lines);
  assert.deepEqual(a.source,a.before);
});
test('p5 empty and unavailable-runtime states remain explicit',()=>{
  const empty=p5Unit(0);assert.equal(empty.elements['visual-note'].textContent,'empty');
  const missing=p5Unit(2,{runtime:false});assert.equal(missing.elements['visual-note'].textContent,'missing');
  assert.equal(missing.recorded.canvas,null);
});
