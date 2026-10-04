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
