// Optional backend. Regenerate this bundle when the captured source changes.
import React from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame} from 'remotion';
import ir from './explanation.json';
import {atPresentedFrame} from './frame-model.mjs';
import reading from './presentation.json';
const ui=reading.labels;
const h=React.createElement;
const font=reading.font_family;
function Explainer(){
  const state=atPresentedFrame(ir,reading,useCurrentFrame());
  return h(AbsoluteFill,{lang:reading.language,style:{background:'#0e161d',color:'#edf3ed',fontFamily:font,padding:100,display:'flex',justifyContent:'space-between'}},
    h('div',null,
      h('div',{style:{fontSize:23,letterSpacing:4,color:'#b6f289'}},ui.brand),
      h('div',{style:{fontSize:31,marginTop:36,color:'#b8c8ca'}},state.scene.title),
      h('div',{style:{fontSize:24,marginTop:30,color:'#fed194'}},state.statements.map(s=>ui[s.kind]).join(' · ')),
      h('div',{style:{fontSize:reading.language==='zh-CN'?56:64,lineHeight:1.4,overflowWrap:'anywhere',marginTop:25,maxWidth:1600}},state.statements.map(s=>s.text).join(' ')),
      h('div',{style:{fontSize:23,marginTop:25,color:'#b8c8ca'}},ui.evidence+': '+state.statements.flatMap(s=>s.refs).join(' · '))),
    h('div',null,
      h('div',{style:{fontSize:23,color:'#fed194',marginBottom:16}},ui.boundary),
      h('div',{style:{fontSize:18,fontFamily:'monospace',color:'#b8c8ca',marginBottom:14}},ui.digest+' '+ir.sha256),
      h('div',{style:{fontSize:18,color:'#b8c8ca',marginBottom:18}},ui.timeline),
      h('div',{style:{height:7,background:'#3a4c53'}},h('div',{style:{height:'100%',background:'#b6f289',width:`${state.overall*100}%`}}))));
}
function Root(){
  return h(Composition,{id:'RFExplanation',component:Explainer,width:1920,height:1080,
    fps:ir.timeline.fps,durationInFrames:ir.timeline.duration_frames});
}
registerRoot(Root);
