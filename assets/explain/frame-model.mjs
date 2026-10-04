/** Pure presentation model: identical frames do not depend on playback history. */
export function atFrame(ir, frame) {
  if (ir.schema !== 'repofoundry.explanation/v1' || !Number.isFinite(frame)) {
    throw new Error('Unsupported IR or frame');
  }
  const end = ir.timeline.duration_frames;
  if (!Number.isInteger(end) || end < 1 || end > 108000) throw new Error('Invalid timeline');
  const f = Math.min(end - 1, Math.max(0, Math.floor(frame)));
  const index = ir.scenes.findIndex(s => f >= s.from_frame && f < s.from_frame + s.duration_frames);
  if (index < 0) throw new Error('Frame is not covered by a scene');
  const scene = ir.scenes[index];
  const statements = scene.statement_ids.map(id => ir.statements.find(s => s.id === id));
  if (statements.some(s => !s)) throw new Error('Missing scene statement');
  return {frame: f, index, scene, statements,
    progress: (f - scene.from_frame) / scene.duration_frames,
    overall: (f + 1) / end};
}

export function nodeLayout(ir, frame) {
  const view = atFrame(ir, frame);
  // Positions depend only on stable source order. No random/physics integration.
  const nodes = ir.graph.nodes;
  return nodes.map((node, i) => ({...node, x: 0.1 + (i % 4) * 0.24,
    y: 0.18 + Math.floor(i / 4) * 0.15,
    selected: node.role === 'direct', visible: view.index >= 3}));
}

/** A source-bound reading projection; exact IR fields and timings remain intact. */
export function atPresentedFrame(ir, reading, frame) {
  if (reading.schema !== 'repofoundry.presentation/v1' ||
      !['en', 'zh-CN'].includes(reading.language) || reading.authority !== 'none' ||
      !ir.sha256 || reading.ir_sha256 !== ir.sha256 ||
      !ir.source?.sha256 || reading.source_sha256 !== ir.source.sha256) {
    throw new Error('Presentation does not match the source IR');
  }
  const view = atFrame(ir, frame);
  const title = reading.scenes?.[view.scene.id];
  if (typeof title !== 'string' || !title) throw new Error('Missing localized scene');
  const statements = view.statements.map(s => {
    const text = reading.statements?.[s.id];
    if (typeof text !== 'string' || !text) throw new Error('Missing localized statement');
    return {...s, text};
  });
  return {...view, scene: {...view.scene, title}, statements};
}

/** Source-only geometry for a mechanism explanation, NOT a Router execution trace.
 * Python validates the v1 IR before export. These checks also refuse malformed
 * graphs if a bundle is edited. No glob matching, applicability inference, or
 * authority transition is performed in the renderer.
 */
export function mechanismModel(ir) {
  const s=ir.source?.snapshot;
  if (ir.schema!=='repofoundry.explanation/v1' || ir.authority!=='none' ||
      s?.kind!=='read-only-preview' || s.authority!=='none' || s.receipt_created!==false) {
    throw new Error('Mechanism requires an authority-free captured preview');
  }
  for (const k of ['paths','specs','direct','whole_specs','resolved','edges']) {
    if (!Array.isArray(s[k]) || s[k].length>1024) throw new Error('Invalid mechanism source array');
  }
  const keys=['paths','candidates','selection','closure','capsule','authority'];
  if (ir.scenes.length!==6 || ir.scenes.some((v,i)=>v.id!==keys[i])) {
    throw new Error('Unsupported mechanism storyboard');
  }
  const ids=s.resolved.map(r=>r.id), byId=new Map(s.resolved.map(r=>[r.id,r]));
  if (byId.size!==ids.length || new Set(s.direct).size!==s.direct.length ||
      s.direct.some(id=>!byId.has(id))) throw new Error('Invalid mechanism selection');
  const direct=new Set(s.direct), edges=[], parents=new Map(ids.map(id=>[id,0]));
  for (const r of s.resolved) {
    if (typeof r.id!=='string' || !r.id ||
        r.source!==(direct.has(r.id)?'direct':'context_dependency') ||
        !Array.isArray(r.context_dependencies) ||
        new Set(r.context_dependencies).size!==r.context_dependencies.length) {
      throw new Error('Invalid mechanism Requirement');
    }
    for (const to of r.context_dependencies) {
      if (!byId.has(to)) throw new Error('Unresolved mechanism dependency');
      edges.push({from:r.id,to}); parents.set(to,parents.get(to)+1);
    }
  }
  const edgeKeys=list=>list.map(e=>JSON.stringify([e.from,e.to])).sort();
  if (JSON.stringify(edgeKeys(edges))!==JSON.stringify(edgeKeys(s.edges))) {
    throw new Error('Mechanism edges disagree with source');
  }
  const reachable=new Set(), stack=[...s.direct];
  while (stack.length) {
    const id=stack.pop(); if (reachable.has(id)) continue;
    reachable.add(id); stack.push(...byId.get(id).context_dependencies);
  }
  if (reachable.size!==ids.length) throw new Error('Unselected mechanism nodes');
  // Longest-path layering preserves arrow direction even in a diamond DAG.
  // Rank and reveal order are reading aids, never measured causality or timings.
  const rank=new Map(ids.map(id=>[id,0])), queue=ids.filter(id=>parents.get(id)===0);
  for (let i=0;i<queue.length;i++) {
    const id=queue[i];
    for (const to of byId.get(id).context_dependencies) {
      rank.set(to,Math.max(rank.get(to),rank.get(id)+1));
      parents.set(to,parents.get(to)-1); if (!parents.get(to)) queue.push(to);
    }
  }
  if (queue.length!==ids.length) throw new Error('Mechanism dependency cycle');
  const levels=Math.max(0,...rank.values()), rows=new Map();
  for (const id of ids) {const k=rank.get(id);rows.set(k,[...(rows.get(k)||[]),id]);}
  const nodes=s.resolved.map((r,i)=>({id:r.id,role:r.source,spec_id:r.spec_id,
    ref:`/resolved/${i}`,rank:rank.get(r.id),
    x:60+rank.get(r.id)*430,y:100+rows.get(rank.get(r.id)).indexOf(r.id)*138,
    direct:direct.has(r.id)}));
  const readable=nodes.length<=12 && levels<=3 && [...rows.values()].every(r=>r.length<=3) &&
    nodes.every(n=>[...n.id].reduce((w,c)=>w+(c.codePointAt(0)>255?2:1),0)<=32);
  const items=(values,key)=>values.map((v,i)=>({id:v,ref:`/${key}/${i}`}));
  const paths=items(s.paths,'paths');
  const candidates=s.specs.map((v,i)=>({id:v.id,ref:`/specs/${i}`,
    scopes:Array.isArray(v.applies_to)?v.applies_to.filter(p=>typeof p==='string'):[]}));
  if ([...paths,...candidates].some(v=>typeof v.id!=='string' || !v.id)) {
    throw new Error('Invalid mechanism label');
  }
  const capsule=s.capsule;
  if (Boolean(capsule)!==Boolean(s.direct.length+s.whole_specs.length) || (capsule &&
      (!Number.isInteger(capsule.bytes) || !Number.isInteger(capsule.budget_bytes) ||
       capsule.bytes<0 || capsule.budget_bytes<1 || capsule.bytes>capsule.budget_bytes ||
       typeof capsule.text!=='string'))) throw new Error('Invalid mechanism capsule');
  return {paths,candidates,nodes,edges:edges.map(e=>({...e})),readable,
    direct:items(s.direct,'direct'),whole:items(s.whole_specs,'whole_specs'),
    capsule:capsule?{bytes:capsule.bytes,budget:capsule.budget_bytes,sha256:capsule.sha256,
      ref:'/capsule'}:null,
    scenes:ir.scenes.map(v=>({id:v.id,from_frame:v.from_frame,duration_frames:v.duration_frames})),
    duration:ir.timeline.duration_frames,authority:'none',receipt_created:false};
}

/** Closed-form animation: evaluating frame B never depends on evaluating A. */
export function mechanismFrame(model, frame) {
  if (!Number.isFinite(frame)) throw new Error('Invalid mechanism frame');
  const f=Math.max(0,Math.min(model.duration-1,Math.floor(frame)));
  const stage=model.scenes.findIndex(s=>f>=s.from_frame && f<s.from_frame+s.duration_frames);
  if (stage<0) throw new Error('Mechanism frame outside storyboard');
  const scene=model.scenes[stage], local=f-scene.from_frame;
  const t=local/Math.max(1,scene.duration_frames-1);
  const ease=x=>{const k=Math.max(0,Math.min(1,x));return k*k*(3-2*k);};
  const reveal=(delay=0)=>ease((t-delay)/0.32);
  const move=reveal();
  return {frame:f,stage,t,move,
    paths:model.paths.map((p,i)=>({...p,x:60-(stage===0?80*(1-reveal(i*0.035)):0),
      y:80+i*105,opacity:stage===0?0.25+0.75*reveal(i*0.035):stage<2?1:0.25})),
    candidates:model.candidates.map((p,i)=>({...p,x:700+(stage===1?80*(1-reveal(0.08+i*0.04)):0),
      y:80+i*105,opacity:stage<1?0:stage===1?reveal(0.08+i*0.04):1,
      selected:stage>=2&&model.nodes.some(n=>n.direct&&n.spec_id===p.id)})),
    direct:model.direct.map((n,i)=>{
      const owner=model.candidates.findIndex(c=>c.id===model.nodes.find(r=>r.id===n.id).spec_id);
      const originX=owner<0?1290:700, originY=owner<0?100+i*138:80+owner*105;
      const progress=stage===2?reveal(i*0.04):1;
      return {...n,x:originX+(1290-originX)*progress,y:originY+(100+i*138-originY)*progress,
        opacity:stage<2?0:stage===2?progress:1};
    }),
    graph:model.nodes.map(n=>({...n,x:stage===3&&n.direct?1290+(n.x-1290)*move:n.x,
      y:stage===3&&n.direct?(100+model.direct.findIndex(d=>d.id===n.id)*138)*(1-move)+n.y*move:n.y,
      opacity:stage<3?0:stage===3?(n.direct?1:reveal(0.10+n.rank*0.09)):1})),
    edges:model.edges.map(e=>({...e,progress:stage<3?0:stage===3?
      reveal(0.09+model.nodes.find(n=>n.id===e.to).rank*0.09):1})),
    assembly:stage<4?0:stage===4?reveal(0.12):1,
    boundary:stage<5?0:stage===5?reveal(0.1):1};
}
