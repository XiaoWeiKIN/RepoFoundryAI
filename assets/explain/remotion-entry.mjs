// Optional backend. Regenerate this bundle when the captured source changes.
import React from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame} from 'remotion';
import ir from './explanation.json';
import {atFrame} from './frame-model.mjs';
const h=React.createElement;
const font='system-ui, sans-serif';
function Explainer(){
  const state=atFrame(ir,useCurrentFrame());
  return h(AbsoluteFill,{style:{background:'#0e161d',color:'#edf3ed',fontFamily:font,padding:100,display:'flex',justifyContent:'space-between'}},
    h('div',null,
      h('div',{style:{fontSize:23,letterSpacing:4,color:'#b6f289'}},'REPOFOUNDRY / DERIVED EXPLANATION'),
      h('div',{style:{fontSize:31,marginTop:36,color:'#b8c8ca'}},state.scene.title),
      h('div',{style:{fontSize:24,marginTop:30,color:'#fed194'}},state.statements.map(s=>s.kind.toUpperCase()).join(' · ')),
      h('div',{style:{fontSize:64,lineHeight:1.3,marginTop:25,maxWidth:1600}},state.statements.map(s=>s.text).join(' ')),
      h('div',{style:{fontSize:23,marginTop:25,color:'#b8c8ca'}},'Evidence: '+state.statements.flatMap(s=>s.refs).join(' · '))),
    h('div',null,
      h('div',{style:{fontSize:23,color:'#fed194',marginBottom:16}},'Derived preview. No activation, approval, or execution authority.'),
      h('div',{style:{fontSize:18,fontFamily:'monospace',color:'#b8c8ca',marginBottom:14}},'IR SHA-256 '+ir.sha256),
      h('div',{style:{fontSize:18,color:'#b8c8ca',marginBottom:18}},'Reading order, not observed execution time. Source snapshot is in the companion bundle.'),
      h('div',{style:{height:7,background:'#3a4c53'}},h('div',{style:{height:'100%',background:'#b6f289',width:`${state.overall*100}%`}}))));
}
function Root(){
  return h(Composition,{id:'RFExplanation',component:Explainer,width:1920,height:1080,
    fps:ir.timeline.fps,durationInFrames:ir.timeline.duration_frames});
}
registerRoot(Root);
