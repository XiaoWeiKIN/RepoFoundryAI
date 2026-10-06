/** Exercise the architecture HTML view in a real browser. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {chromium} from 'playwright';

const work=process.cwd(), root=path.join(work,'generated','architecture');
const payload=JSON.parse(await fs.readFile(path.join(root,'architecture.json'),'utf8'));
const server=http.createServer(async(req,res)=>{
  try{
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).slice(1)||'index.html';
    const file=path.resolve(root,relative);
    if(!file.startsWith(path.resolve(root)+path.sep))throw new Error('outside root');
    const data=await fs.readFile(file);
    res.setHeader('Content-Type',file.endsWith('.html')?'text/html; charset=utf-8':'application/json; charset=utf-8');
    res.setHeader('Cache-Control','no-store');res.end(data);
  }catch{res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const browserInstance=await chromium.launch({headless:true});
const results=[];
try{
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
    const context=await browserInstance.newContext({viewport});
    const page=await context.newPage(),errors=[],external=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/*',route=>{
      if(new URL(route.request().url()).origin!==origin){external.push(route.request().url());return route.abort();}
      return route.continue();
    });
    await page.addInitScript(()=>{
      window.__csp=[];
      document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective));
    });
    await page.goto(origin+'/index.html',{waitUntil:'networkidle'});
    assert.equal(await page.locator('h1').textContent(),payload.subject.title);
    const buttons=page.locator('#nav button');
    assert.equal(await buttons.count(),4);
    assert.equal(await buttons.nth(0).getAttribute('aria-current'),'true');
    assert((await page.locator('#view').textContent()).includes('Owns controlled state.'));

    await buttons.nth(1).focus();await page.keyboard.press('Enter');
    const flowText=await page.locator('#view').textContent();
    assert(flowText.includes('Caller'));assert(flowText.includes('Editor'));
    assert(flowText.includes('Condition: Only after an input event.'));

    await buttons.nth(2).click();
    assert((await page.locator('#view').textContent()).includes('Caller remains the state owner.'));
    await buttons.nth(3).click();
    assert((await page.locator('#view').textContent()).includes('tests/editor.py'));

    assert((await page.locator('#limits').textContent()).includes('Synthetic browser fixture only'));
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    const csp=await page.evaluate(()=>window.__csp);assert.deepEqual(csp,[]);
    results.push({viewport,buttons:await buttons.count(),page_errors:errors,external_requests:external,csp_violations:csp});
    await context.close();
  }
} finally {
  await browserInstance.close();
  await new Promise(resolve=>server.close(resolve));
}
console.log(JSON.stringify({success:true,architecture_sha256:payload.sha256,tests:results}));
