/** Execute real browsers/libraries. No stub p5, simulated OS, or source edits. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {chromium} from 'playwright';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';
import ffprobe from 'ffprobe-static';
const work=process.cwd(), evidence=path.join(work,'evidence');
await fs.mkdir(evidence,{recursive:true});
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const json=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const original=await fs.readFile(path.join(work,'input/explanation.json'));
const ir=JSON.parse(original);
const report={kind:'actual-optional-runtime-evaluation',rf_revision:process.env.GITHUB_SHA,
  os:os.platform(),release:os.release(),arch:os.arch(),node:process.version,
  versions:{},tests:[],font_samples:[],canvas_fonts:[],sources:{ir:ir.sha256,capsule:ir.source.snapshot.capsule.sha256},
  commercial_render:false,production_conformance:false};
for(const p of ['remotion','p5','playwright','react'])report.versions[p]=(await json(path.join(work,'node_modules',p,'package.json'))).version;
const save=()=>fs.writeFile(path.join(evidence,'runtime-results.json'),JSON.stringify(report,null,2));
await save();
async function test(name,fn){
  console.log('START',name);
  try{const data=await fn();report.tests.push({name,ok:true,...data});console.log('PASS',name);}
  catch(e){report.tests.push({name,ok:false,error:e.stack||String(e)});console.error('FAIL',name,e);}
  await save();
}
const server=http.createServer(async(req,res)=>{
  try{
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).slice(1);
    const file=path.resolve(work,'generated',relative);
    if(!file.startsWith(path.resolve(work,'generated')+path.sep))throw new Error('outside root');
    const data=await fs.readFile(file);
    res.setHeader('Content-Type',file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.js')?'text/javascript; charset=utf-8':'application/json; charset=utf-8');
    res.setHeader('Cache-Control','no-store');res.end(data);
  }catch{res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true});
report.browser=browser.version();
async function fonts(page,reading,kind){
  const chars=[...new Set(JSON.stringify(reading).match(/[\u3400-\u9fff]/gu)||[])].sort();
  await page.evaluate(({chars,font})=>{
    const host=document.createElement('div');host.id='font-probe';host.lang='zh-CN';
    for(const [stack,family] of [['primary',font],['mono','ui-monospace, monospace']]){
      for(const [i,c] of chars.entries()){
        const n=document.createElement('span');n.id=`glyph-${stack}-${i}`;
        n.style.fontFamily=family;n.style.fontSize='32px';n.textContent=c;host.append(n);
      }
    }
    document.body.append(host);
  },{chars,font:reading.font_family});
  await page.evaluate(()=>document.fonts.ready);
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('DOM.enable');await cdp.send('CSS.enable');
  const {root}=await cdp.send('DOM.getDocument');
  for(const stack of ['primary','mono'])for(const [i,character] of chars.entries()){
    const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:root.nodeId,selector:`#glyph-${stack}-${i}`});
    const result=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
    report.font_samples.push({kind,stack,character,fonts:result.fonts});
    assert(result.fonts.some(f=>f.glyphCount>0),'No rendered glyph: '+character);
    assert(!result.fonts.some(f=>/lastresort|last resort/i.test(f.familyName)),'Last-resort glyph: '+character);
  }
  await page.locator('#font-probe').evaluate(n=>n.remove());await cdp.detach();
  return chars.length;
}
try{
for(const language of ['zh-CN','en'])for(const kind of ['html','p5'])for(const viewport of [{width:1440,height:1100},{width:390,height:844}]){
  const name=`${kind}-${language}-${viewport.width}`;
  await test(name,async()=>{
    const context=await browser.newContext({viewport,deviceScaleFactor:1});
    const page=await context.newPage(),errors=[],external=[],violations=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/*',route=>{
      if(new URL(route.request().url()).origin!==origin){external.push(route.request().url());return route.abort();}
      return route.continue();
    });
    await page.addInitScript(()=>{
      window.__csp=[];window.__canvas=[];
      document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective));
      const fill=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(text,...rest){
        if(window.__canvas.length<10000)window.__canvas.push({text:String(text),font:this.font});
        return fill.call(this,text,...rest);
      };
    });
    try{
      await page.goto(`${origin}/${language}-${kind}/index.html`,{waitUntil:'networkidle'});
      const reading=await json(path.join(work,'generated',`${language}-${kind}`,'presentation.json'));
      assert.equal(await page.locator('html').getAttribute('lang'),language);
      await page.waitForFunction(()=>document.querySelectorAll('#steps button').length===6);
      assert.equal(await page.locator('#capsule').textContent(),ir.source.snapshot.capsule.text);
      let p5version=null;
      if(kind==='p5'){
        await page.locator('canvas').waitFor();
        p5version=await page.evaluate(()=>window.p5.VERSION||window.p5.prototype.VERSION);
        assert.equal(p5version,report.versions.p5);
      }
      for(let i=0;i<6;i++){
        await page.locator('#steps button').nth(i).focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#scene-title').textContent(),reading.scenes[ir.scenes[i].id]);
        assert.equal(await page.locator('#seek').inputValue(),String(ir.scenes[i].from_frame));
        if(i===3)await page.screenshot({path:path.join(evidence,name+'.png'),fullPage:true});
      }
      const seek=page.locator('#seek');
      await seek.focus();await page.keyboard.press('Home');assert.equal(await seek.inputValue(),'0');
      await page.keyboard.press('End');assert.equal(await seek.inputValue(),'1079');
      await page.keyboard.press('ArrowLeft');assert.equal(await seek.inputValue(),'1078');
      await page.keyboard.press('Home');await page.locator('#play').click();
      await page.waitForFunction(()=>Number(document.querySelector('#seek').value)>1);
      assert.equal(await page.locator('#play').textContent(),reading.labels.pause);
      await page.locator('#play').click();assert.equal(await page.locator('#play').textContent(),reading.labels.play);
      let canvasHash=null;
      if(kind==='p5'){
        const capture=async i=>{
          await page.locator('#steps button').nth(i).click();
          await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
          return hash(await page.locator('canvas').screenshot());
        };
        canvasHash=await capture(3);const other=await capture(5);assert.notEqual(canvasHash,other);
        assert.equal(await capture(3),canvasHash,'Canvas depends on playback history');
        const log=await page.evaluate(()=>window.__canvas);
        if(language==='zh-CN'){
          assert(log.some(x=>/[\u3400-\u9fff]/u.test(x.text)),'No actual Chinese canvas draw');
          report.canvas_fonts.push({name,fonts:[...new Set(log.filter(x=>/[\u3400-\u9fff]/u.test(x.text)).map(x=>x.font))]});
        }
      }
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Viewport overflow');
      assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
      violations.push(...await page.evaluate(()=>window.__csp));assert.deepEqual(violations,[]);
      let glyphs=0;if(language==='zh-CN'&&viewport.width===1440)glyphs=await fonts(page,reading,kind);
      return {p5_version:p5version,canvas_sha256:canvasHash,source_preserved:true,
        chinese_codepoints_probed:glyphs,external_requests:external,page_errors:errors,csp_violations:violations};
    }finally{await context.close();}
  });
}
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
for(const language of ['zh-CN','en'])await test(`remotion-mp4-${language}`,async()=>{
  const directory=path.join(work,'generated',`${language}-remotion`);
  const serveUrl=await bundle({entryPoint:path.join(directory,'index.mjs'),outDir:path.join(work,`bundled-${language}`)});
  // Playwright's executablePath points to full modern Chromium, not the separate
  // old-headless shell. Explicit mode prevents an invalid --headless=old launch.
  const options={serveUrl,browserExecutable:chromium.executablePath(),chromeMode:'chrome-for-testing',logLevel:'error'};
  const composition=await selectComposition({...options,id:'RFExplanation'});
  assert.equal(composition.width,1920);assert.equal(composition.height,1080);
  assert.equal(composition.fps,30);assert.equal(composition.durationInFrames,1080);
  const output=path.join(evidence,`${language}.mp4`);
  let milestone=-1;
  await renderMedia({...options,composition,outputLocation:output,codec:'h264',crf:24,x264Preset:'ultrafast',concurrency:2,
    onProgress:({progress})=>{const next=Math.floor(progress*4);if(next!==milestone){milestone=next;console.log('RENDER',language,next*25+'%');}}});
  const probe=spawnSync(ffprobe.path,['-v','error','-count_frames','-show_streams','-show_format','-of','json',output],{encoding:'utf8',timeout:120000});
  assert.equal(probe.status,0,probe.stderr);
  const metadata=JSON.parse(probe.stdout),video=metadata.streams.find(s=>s.codec_type==='video');
  assert.equal(video.codec_name,'h264');assert.equal(video.width,1920);assert.equal(video.height,1080);
  assert.equal(Number(video.nb_read_frames),1080);assert.equal(Number(metadata.format.duration),36);
  assert.equal(metadata.streams.filter(s=>s.codec_type==='audio').length,0);
  await fs.writeFile(path.join(evidence,`${language}-ffprobe.json`),probe.stdout);
  for(const frame of [0,180,360,540,720,900,1079])await renderStill({...options,composition,frame,
    output:path.join(evidence,`${language}-frame-${frame}.png`)});
  const duplicate=path.join(evidence,`${language}-repeat-540.png`);
  await renderStill({...options,composition,frame:540,output:duplicate});
  assert.equal(hash(await fs.readFile(duplicate)),hash(await fs.readFile(path.join(evidence,`${language}-frame-540.png`))));
  assert.deepEqual(await fs.readFile(path.join(directory,'explanation.json')),original);
  await fs.copyFile(path.join(directory,'presentation.json'),path.join(evidence,`${language}-presentation.json`));
  return {sha256:hash(await fs.readFile(output)),frames:1080,duration:36,width:1920,height:1080,
    codec:'h264',audio:false,repeat_frame_identical:true,chrome_mode:options.chromeMode};
});
assert.deepEqual(await fs.readFile(path.join(work,'input/explanation.json')),original);
await fs.writeFile(path.join(evidence,'source-explanation.json'),original);
await fs.copyFile(path.join(work,'package-lock.json'),path.join(evidence,'package-lock.json'));
report.success=report.tests.length===10&&report.tests.every(t=>t.ok);
await save();console.log(JSON.stringify({success:report.success,tests:report.tests.length,versions:report.versions,platform:report.os}));
if(!report.success)process.exitCode=1;
