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
