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
