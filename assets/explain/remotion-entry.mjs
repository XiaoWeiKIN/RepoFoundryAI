// Optional Remotion backend. Diagram motion explains a snapshot, not execution.
import React from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame} from 'remotion';
import ir from './explanation.json';
import reading from './presentation.json';
import {atPresentedFrame, mechanismModel, mechanismFrame} from './frame-model.mjs';

const h=React.createElement, ui=reading.labels, model=mechanismModel(ir);
const C={bg:'#0b141b',panel:'#13242f',line:'#465d6b',ink:'#edf3ed',muted:'#b8c8ca',
  direct:'#b6f289',dependency:'#83c6f3',limit:'#fed194'};
const mono='ui-monospace, "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", monospace';
const mix=(a,b,t)=>a+(b-a)*t;

// Wrap only the visible label. No ellipses, source mutation, or raw HTML.
function wrap(text,units=44) {
  const out=[];
  for (const line of String(text).split('\n')) {
    let part='',width=0;
    for (const c of line) {
      const size=c.codePointAt(0)>255?2:1;
      if (width+size>units) {out.push(part);part='';width=0;}
      part+=c;width+=size;
    }
    out.push(part);
  }
  return out;
}
function text(value,x,y,{size=22,color=C.ink,units=70,family=reading.font_family,anchor='start'}={}) {
  return h('text',{x,y,fill:color,fontSize:size,fontFamily:family,textAnchor:anchor},
    wrap(value,units).map((line,i)=>h('tspan',{key:i,x,dy:i?size*1.35:0},line)));
}
function card(id,label,x,y,{width=330,height=92,opacity=1,color=C.direct,ref='',size=19}={}) {
  return h('g',{key:id,opacity,transform:`translate(${x} ${y})`,'data-node':id},
    h('rect',{width,height,rx:12,fill:C.panel,stroke:color,strokeWidth:2}),
    h('path',{d:`M 0 16 L 0 ${height-16}`,stroke:color,strokeWidth:5}),
    text(label,18,30,{size,units:Math.floor((width-36)/(size*0.63)),family:mono}),
    ref?text(ref,18,height-12,{size:14,color:C.muted,units:52,family:mono}):null);
}
function line(x1,y1,x2,y2,progress=1,color=C.line) {
  return h('path',{d:`M ${x1} ${y1} C ${mix(x1,x2,.45)} ${y1} ${mix(x1,x2,.55)} ${y2} ${x2} ${y2}`,
    fill:'none',stroke:color,strokeWidth:3,pathLength:1,strokeDasharray:1,
    strokeDashoffset:1-progress,markerEnd:progress>.98?'url(#mechanism-arrow)':undefined});
}
function collection(items,label,x,width=500,opacity=1) {
  const full=items.length<=4&&items.every(n=>wrap(n.id,44).length<=2);
  if (!full) return h('g',{opacity},
    card(label,`${label}\n${items.length}`,x,100,{width,height:150,color:C.dependency}),
    text(ui.snapshot,x,300,{size:24,units:38,color:C.muted}));
  return h('g',null,items.map((n,i)=>card(`${label}:${i}`,n.id,n.x??x,n.y??80+i*105,
    {width,opacity:(n.opacity??1)*opacity,color:n.selected?C.direct:C.dependency,ref:n.scopes?.length&&n.scopes.join(', ').length<=20?
      `${n.ref} · ${n.scopes.join(', ')}`:n.ref,size:18})));
}
function graph(frame,opacity=1) {
  if (!model.readable) return h('g',{opacity},
    text(reading.statements.closure,110,170,{size:36,units:75}),
    text(ui.large_graph,110,290,{size:27,units:85,color:C.limit}));
  if (!model.nodes.length) return h('g',{opacity},
    text(ui.empty_graph,100,100,{size:28,units:90,color:C.limit}),
    text(`/whole_specs: ${model.whole.length}`,100,300,{size:36,family:mono}),
    text(ui.snapshot,100,390,{size:25,color:C.muted}));
  const positions=new Map(frame.graph.map(n=>[n.id,n]));
  return h('g',{opacity},
    frame.edges.map((e,i)=>{
      const a=positions.get(e.from),b=positions.get(e.to);
      const skip=b.rank-a.rank>1, rail=485+(i%3)*14;
      return h('g',{key:i,'data-edge':`${e.from}>${e.to}`},skip?
        h('path',{d:`M ${a.x+330} ${a.y+46} H ${a.x+365} V ${rail} H ${b.x-26} V ${b.y+46} H ${b.x-10}`,
          fill:'none',stroke:C.dependency,strokeWidth:3,pathLength:1,strokeDasharray:1,
          strokeDashoffset:1-e.progress,markerEnd:e.progress>.98?'url(#mechanism-arrow)':undefined}):
        line(a.x+330,a.y+46,b.x-10,b.y+46,e.progress,C.dependency));
    }),
    frame.graph.map(n=>h('g',{key:n.id},
      card(n.id,n.id,n.x,n.y,{opacity:n.opacity,color:n.direct?C.direct:C.dependency,ref:n.ref}),
      h('g',{opacity:n.opacity},text(n.direct?ui.direct:ui.dependency,n.x+14,n.y-14,
        {size:20,color:n.direct?C.direct:C.dependency,units:38})))));
}
function capsule(x,y,opacity=1,compact=false) {
  const c=model.capsule, width=compact?740:630;
  return h('g',{opacity,transform:`translate(${x} ${y})`},
    h('rect',{width,height:430,rx:18,fill:C.panel,stroke:C.direct,strokeWidth:3}),
    text(reading.scenes.capsule,28,47,{size:28,units:40}),
    c?h('g',null,
      text(`${c.bytes} / ${c.budget} bytes`,28,105,{size:29,color:C.direct,family:mono}),
      h('rect',{x:28,y:132,width:width-56,height:12,rx:6,fill:C.line}),
      h('rect',{x:28,y:132,width:(width-56)*c.bytes/c.budget,height:12,rx:6,fill:C.direct}),
      // The bar always represents the actual captured byte budget, never animation progress.
      text(ui.snapshot,28,194,{size:24,color:C.muted,units:42}),
      text('explanation.json\n/source/snapshot/capsule/text',28,245,
        {size:18,color:C.dependency,units:44,family:mono}),
      text('SHA-256',28,332,{size:17,color:C.muted,family:mono}),
      text(c.sha256,28,361,{size:17,units:52,family:mono}),
      text(c.ref,28,410,{size:16,color:C.muted,family:mono})):
      text(reading.statements.capsule,28,135,{size:25,units:40,color:C.limit}));
}
function board(frame) {
  const s=frame.stage;
  let content;
  if (s===0) {
    content=h('g',null,collection(frame.paths,'/paths',60),
      h('g',{transform:`translate(${mix(1050,990,frame.move)} 180)`},
        h('path',{d:'M 0 0 H 240 V 180 H 0 Z M 40 50 H 190 M 40 85 H 190 M 40 120 H 140',
          fill:'none',stroke:C.dependency,strokeWidth:4}),
        text(String(model.paths.length),340,110,{size:110,color:C.direct,family:mono})),
      text('/paths',990,435,{size:24,color:C.muted,family:mono}));
  } else if (s===1 || s===2) {
    // A bus denotes the aggregate captured match result. It does NOT assert
    // which particular path matched a particular Spec, or rerun glob matching.
    content=h('g',null,
      collection(frame.paths,'/paths',60,500,s===2?.25:1),
      line(560,255,575,255,s===1?frame.move:1,C.dependency),
      h('g',{opacity:s===2?.25:1},
        h('rect',{x:580,y:215,width:106,height:80,rx:9,fill:C.panel,stroke:C.dependency,strokeWidth:2}),
        text('applies_to',633,260,{size:14,family:mono,anchor:'middle'})),
      line(689,255,699,255,s===1?frame.move:1,C.dependency),
      collection(frame.candidates,'/specs',700,500),
      s===1?text(reading.statements.candidates,1290,175,{size:30,units:24,color:C.dependency}):
        h('g',null,
          text(ui.direct,1290,64,{size:23,color:C.direct,units:34}),
          frame.direct.length<=3&&frame.direct.every(n=>wrap(n.id,28).length<=1)?
            frame.direct.map(n=>card(n.id,n.id,n.x,n.y,{opacity:n.opacity,color:C.direct,ref:n.ref,size:17})):
            collection(model.direct,'/direct',1290,350),
          model.whole.length?text(`/whole_specs: ${model.whole.length}`,1290,490,
            {size:20,color:C.limit,family:mono,units:34}):null),
      s===2?h('g',{opacity:frame.move},
        h('path',{d:'M 1222 140 V 380',stroke:C.limit,strokeWidth:4,strokeDasharray:'9 9'}),
        text('≠',1218,440,{size:46,color:C.limit,anchor:'middle'})):null);
  } else if (s===3) {
    content=graph(frame);
  } else if (s===4) {
    content=h('g',null,
      graph(frame,1-frame.assembly),
      model.readable&&model.nodes.length?model.nodes.map((n,i)=>{
        const x=60+Math.floor(i/6)*360,y=50+(i%6)*74;
        return card(n.id,n.id,mix(n.x,x,frame.assembly),mix(n.y,y,frame.assembly),
          {height:62,color:n.direct?C.direct:C.dependency,size:17,opacity:frame.assembly});
      }):text(reading.statements.closure,60,170,{size:26,units:40,color:C.dependency}),
      model.whole.length?text(`/whole_specs: ${model.whole.length}`,60,520,{size:20,color:C.limit,family:mono}):null,
      line(785,245,1050,245,frame.assembly,C.direct),
      capsule(1080,40,frame.assembly));
  } else {
    content=h('g',null,capsule(60,40,1,true),
      line(820,255,965,255,frame.boundary,C.limit),
      h('g',{opacity:.35+.65*frame.boundary},
        h('path',{d:'M 985 90 V 435 M 1010 90 V 435',stroke:C.limit,strokeWidth:6}),
        h('circle',{cx:997,cy:255,r:40,fill:C.bg,stroke:C.limit,strokeWidth:4}),
        h('path',{d:'M 973 230 L 1021 280',stroke:C.limit,strokeWidth:5}),
        text('authority: none',1090,190,{size:34,color:C.limit,family:mono,units:36}),
        text('receipt_created: false',1090,255,{size:29,color:C.limit,family:mono,units:38}),
        text(reading.statements.authority,1090,330,{size:25,color:C.muted,units:41})));
  }
  return h('svg',{viewBox:'0 0 1760 540',width:1760,height:540,role:'img',
    'aria-label':reading.scenes[model.scenes[s].id],
    'data-mechanism-board':true,'data-stage':s,
    style:{position:'absolute',left:80,top:245,overflow:'hidden'}},
    h('title',null,reading.statements[model.scenes[s].id]),
    h('defs',null,h('marker',{id:'mechanism-arrow',viewBox:'0 0 10 10',refX:9,refY:5,
      markerWidth:5,markerHeight:5,orient:'auto-start-reverse'},
      h('path',{d:'M 0 0 L 10 5 L 0 10',fill:'none',stroke:C.muted,strokeWidth:2}))),
    content);
}
function Explainer() {
  const frame=useCurrentFrame(), view=atPresentedFrame(ir,reading,frame), state=mechanismFrame(model,frame);
  const note=state.stage<3?reading.statements.applicability:
    state.stage===3?ui.graph_note:state.stage===4?ui.hash_note:reading.statements.freshness;
  return h(AbsoluteFill,{lang:reading.language,style:{background:C.bg,color:C.ink,fontFamily:reading.font_family}},
    h('div',{style:{position:'absolute',left:80,top:35,fontSize:21,letterSpacing:2,color:C.muted}},ui.brand),
    h('div',{style:{position:'absolute',right:80,top:35,fontSize:21,color:C.limit}},ui.badge),
    h('div',{style:{position:'absolute',left:80,top:102,fontSize:reading.language==='zh-CN'?46:44,lineHeight:1.35}},view.scene.title),
    h('div',{style:{position:'absolute',left:80,top:188,display:'flex',gap:12}},
      model.scenes.map((s,i)=>h('div',{key:s.id,style:{width:283,height:5,
        background:i===state.stage?C.direct:i<state.stage?C.dependency:C.line}}))),
    board(state),
    h('div',{'data-mechanism-caption':true,style:{position:'absolute',left:80,top:803,width:1760,
      fontSize:28,lineHeight:1.5}},view.statements.map(s=>s.text).join(' ')),
    h('div',{style:{position:'absolute',left:80,top:887,width:1760,fontSize:20,lineHeight:1.5,color:C.limit}},note),
    h('div',{style:{position:'absolute',left:80,top:957,fontSize:17,color:C.muted,fontFamily:mono}},
      view.statements.flatMap(s=>s.refs).join(' · ')+' | SHA-256 '+ir.sha256),
    h('div',{style:{position:'absolute',left:80,top:994,width:1760,fontSize:17,color:C.muted}},ui.timeline),
    h('div',{style:{position:'absolute',left:80,bottom:24,width:1760,height:4,background:C.line}},
      h('div',{style:{height:4,width:1760*view.overall,background:C.direct}})));
}
function Root() {
  return h(Composition,{id:'RFExplanation',component:Explainer,width:1920,height:1080,
    fps:ir.timeline.fps,durationInFrames:ir.timeline.duration_frames});
}
registerRoot(Root);
