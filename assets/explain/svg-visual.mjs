// Dependency-free renderer using the same pure layout as the optional p5 view.
const svgNS='http://www.w3.org/2000/svg';
const shape=(tag,attrs,text)=>{const n=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
drawVisual=state=>{
  $('visual').replaceChildren();
  if(state.index<3){$('visual-note').textContent=ui.seek_hint;return;}
  if(!ir.graph.nodes.length){$('visual-note').textContent=ui.empty_graph;return;}
  if(ir.graph.nodes.length>24||ir.graph.nodes.some(n=>n.id.length>36)){$('visual-note').textContent=ui.large_graph;return;}
  $('visual-note').textContent=ui.graph_note;
  const svg=shape('svg',{viewBox:'0 0 800 340',width:'100%',role:'img','aria-label':ui.graph});
  svg.append(shape('title',{},ui.graph_title));
  const defs=shape('defs',{}),marker=shape('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto'});
  marker.append(shape('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#b8c8ca'}));defs.append(marker);svg.append(defs);
  const nodes=nodeLayout(ir,frame),positions=new Map(nodes.map(n=>[n.id,{x:n.x*760+20,y:n.y*280+15}]));
  // Connect rectangle boundaries, not detached points above the labels.
  const port=(a,b)=>{const dx=b.x-a.x,dy=b.y-a.y;const t=Math.min(dx?75/Math.abs(dx):Infinity,dy?22.5/Math.abs(dy):Infinity);return {x:a.x+dx*t,y:a.y+dy*t};};
  for(const e of ir.graph.edges){const pa=positions.get(e.from),pb=positions.get(e.to),a={x:pa.x+10,y:pa.y+22.5},b={x:pb.x+10,y:pb.y+22.5},start=port(a,b),end=port(b,a);svg.append(shape('line',{x1:start.x,y1:start.y,x2:end.x,y2:end.y,stroke:'#b8c8ca','marker-end':'url(#arrow)'}));}
  for(const n of nodes){const {x,y}=positions.get(n.id);svg.append(shape('rect',{x:x-65,y,width:150,height:45,rx:7,fill:n.selected?'#233a2f':'#17242d',stroke:n.selected?'#b6f289':'#70858c'}));svg.append(shape('text',{x:x-57,y:y+18,fill:'#edf3ed','font-size':Math.min(12,210/n.id.length),'font-family':'monospace'},n.id));svg.append(shape('text',{x:x-57,y:y+34,fill:'#b8c8ca','font-size':10},n.selected?ui.direct:ui.dependency));}
  $('visual').append(svg);
};
