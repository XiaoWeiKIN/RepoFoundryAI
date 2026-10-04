// The caller explicitly provides its trusted p5 distribution; no CDN fallback.
if (typeof window.p5 !== 'function') {
  $('visual-note').textContent=ui.p5_missing;
} else {
  const visual=$('visual'), nodes=ir.graph.nodes;
  // Keep CSS pixels readable. Narrow screens scroll the graph instead of
  // shrinking the entire canvas and its text. Layout never depends on history.
  const width=800, columns=4, pitch=192, cardWidth=168;
  const fontSize=16, leading=22, padding=12;
  let ready=false, positions=[], cardHeight=0, height=360, omitted=nodes.length>24;
  const sketch=new window.p5(p=>{
    p.setup=()=>{
      p.createCanvas(width,height);
      p.textFont(reading.font_family);
      p.textSize(fontSize);
      // Measure explicit lines; p5's fixed-height text box could hide an ID.
      const wrap=text=>{
        const lines=[];let line='';
        for(const character of text){
          if(line && p.textWidth(line+character)>cardWidth-padding*2){
            lines.push(line);line='';
          }
          line+=character;
        }
        lines.push(line);return lines;
      };
      if(!omitted){
        positions=nodes.map((node,i)=>({...node,
          x:112+(i%columns)*pitch, row:Math.floor(i/columns),
          lines:wrap(node.id), roleLines:wrap(node.role==='direct'?ui.direct:ui.dependency)}));
        // Do not draw a misleading partial graph for exceptionally long labels.
        omitted=positions.some(n=>n.lines.length>4 || n.roleLines.length>2);
      }
      if(!omitted && positions.length){
        cardHeight=Math.max(...positions.map(n=>n.lines.length+n.roleLines.length))*leading+padding*2;
        positions=positions.map(n=>({...n,y:32+cardHeight/2+n.row*(cardHeight+48)}));
        height=Math.max(height,Math.ceil(nodes.length/columns)*(cardHeight+48)+64);
      }
      p.resizeCanvas(width,height,true);
      p.textFont(reading.font_family);p.textSize(fontSize);p.textLeading(leading);
      p.textAlign(p.LEFT,p.TOP);p.noLoop();ready=true;p.describe(ui.p5_description);
      $('visual-note').textContent=omitted?ui.large_graph:
        nodes.length?ui.graph_note+' '+ui.p5_pan_hint:ui.empty_graph;
      // Reveal a portable reading path once, without overriding a later
      // user decision to close the disclosure or resetting playback on resize.
      let revealed=false;
      const reveal=()=>{
        if(!revealed && visual.clientWidth<width){
          $('relationships').closest('details').open=true;revealed=true;
        }
      };
      reveal();
      if(typeof ResizeObserver==='function')new ResizeObserver(reveal).observe(visual);
    };
    p.draw=()=>{
      p.background('#17242d');
      const view=atFrame(ir,frame);
      p.noStroke();p.fill('#b6f289');p.rect(20,height-20,(width-40)*view.overall,4);
      if(omitted || !nodes.length)return;
      if(view.index<3){p.fill('#b8c8ca');p.text(ui.seek_hint,20,50,width-40);return;}
      const byId=new Map(positions.map(n=>[n.id,n]));
      // Arrows stop at the card boundaries and always follow source edges.
      for(const edge of ir.graph.edges){
        const a=byId.get(edge.from), b=byId.get(edge.to), dx=b.x-a.x, dy=b.y-a.y;
        const inset=Math.min(cardWidth/2/Math.abs(dx),cardHeight/2/Math.abs(dy));
        const ax=a.x+dx*inset, ay=a.y+dy*inset, bx=b.x-dx*inset, by=b.y-dy*inset;
        p.stroke('#b8c8ca');p.strokeWeight(1.5);p.line(ax,ay,bx,by);
        const angle=Math.atan2(dy,dx);
        p.line(bx,by,bx-9*Math.cos(angle-0.4),by-9*Math.sin(angle-0.4));
        p.line(bx,by,bx-9*Math.cos(angle+0.4),by-9*Math.sin(angle+0.4));
      }
      for(const node of positions){
        const left=node.x-cardWidth/2, top=node.y-cardHeight/2;
        p.stroke(node.role==='direct'?'#b6f289':'#b8c8ca');p.fill('#17242d');
        p.rect(left,top,cardWidth,cardHeight,6);
        p.noStroke();p.fill(node.role==='direct'?'#b6f289':'#b8c8ca');
        p.text([...node.lines,...node.roleLines].join('\n'),left+padding,top+padding);
      }
    };
  },visual);
  drawVisual=()=>{if(ready)sketch.redraw();};
}
