// The caller explicitly provides its trusted p5 distribution; no CDN fallback.
if (typeof window.p5 !== 'function') {
  $('visual-note').textContent=ui.p5_missing;
} else {
  const count=ir.graph.nodes.length;
  $('visual-note').textContent=count>24
    ? ui.large_graph
    : ui.graph_note;
  let ready=false;
  const sketch=new window.p5(p=>{
    p.setup=()=>{p.createCanvas(800,360);p.textFont(reading.font_family);p.noLoop();ready=true;p.describe(ui.p5_description);};
    p.draw=()=>{
      p.background('#17242d');
      const view=atFrame(ir,frame);
      p.noStroke();p.fill('#b6f289');p.rect(20,330,760*view.overall,4);
      if(count>24)return;
      const positions=nodeLayout(ir,frame), byId=new Map(positions.map(n=>[n.id,n]));
      if(view.index<3){p.fill('#b8c8ca');p.textSize(17);p.text(ui.seek_hint,20,50);return;}
      for(const edge of ir.graph.edges){const a=byId.get(edge.from),b=byId.get(edge.to);const ax=a.x*760+20,ay=a.y*280+15,bx=b.x*760+20,by=b.y*280+15;p.stroke('#b8c8ca');p.line(ax,ay,bx,by);const angle=Math.atan2(by-ay,bx-ax);p.line(bx,by,bx-9*Math.cos(angle-0.4),by-9*Math.sin(angle-0.4));p.line(bx,by,bx-9*Math.cos(angle+0.4),by-9*Math.sin(angle+0.4));}
      for(const node of positions){const x=node.x*760+20,y=node.y*280+15;p.noStroke();p.fill(node.selected?'#b6f289':'#b8c8ca');p.circle(x,y,10);p.textSize(11);p.text(node.id+'\n'+(node.selected?ui.direct:ui.dependency),x-48,y+18,130,45);}
    };
  },$('visual'));
  drawVisual=()=>{if(ready)sketch.redraw();};
}
