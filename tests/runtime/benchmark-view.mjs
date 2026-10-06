/** Exercise progressive Benchmark explanations in a real browser. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {chromium} from 'playwright';

const work=process.cwd();
const server=http.createServer(async(req,res)=>{
  try{
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).slice(1)||'index.html';
    const file=path.resolve(work,'generated',relative);
    if(!file.startsWith(path.resolve(work,'generated')+path.sep))throw new Error('outside root');
    const data=await fs.readFile(file);
    res.setHeader('Content-Type',file.endsWith('.html')?'text/html; charset=utf-8':'application/json; charset=utf-8');
    res.setHeader('Cache-Control','no-store');res.end(data);
  }catch{res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true});
const results=[];
try{
  for(const language of ['en','zh-CN']){
    const root=path.join(work,'generated',`benchmark-${language}`);
    const data=JSON.parse(await fs.readFile(path.join(root,'benchmark-explanation.json'),'utf8'));
    for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
      const context=await browser.newContext({viewport,reducedMotion:'reduce'});
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
      await page.goto(`${origin}/benchmark-${language}/index.html`,{waitUntil:'networkidle'});
      assert.equal(await page.locator('html').getAttribute('lang'),language);
      assert.equal(await page.locator('h1').textContent(),data.subject.title);
      const buttons=page.locator('#nav button');
      assert.equal(await buttons.count(),5);

      await buttons.nth(0).click();
      assert((await page.locator('#view').textContent()).includes(data.subject.question));
      assert((await page.locator('#view').textContent()).includes(data.claims.find(c=>c.kind==='hypothesis').text));

      await buttons.nth(1).focus();await page.keyboard.press('Enter');
      const measured=await page.locator('#view').textContent();
      assert(measured.includes(data.metrics[0].baseline.uncertainty));
      assert(measured.includes(data.metrics[0].candidate.uncertainty));
      assert(measured.includes(data.claims.find(c=>c.kind==='observation').text));
      assert(measured.includes(data.claims.find(c=>c.kind==='derived').text));

      await buttons.nth(2).click();
      const chain=await page.locator('#view').textContent();
      for(const kind of ['measurement','diagnostic','source'])assert(chain.includes(kind),kind);

      await buttons.nth(3).click();
      const mechanism=await page.locator('#view').textContent();
      assert(mechanism.includes(data.mechanism_steps[0].baseline));
      assert(mechanism.includes(data.mechanism_steps[0].candidate));
      assert(mechanism.includes(data.claims.find(c=>c.kind==='mechanism').text));
      assert(mechanism.includes(data.claims.find(c=>c.kind==='hypothesis').text));

      await buttons.nth(4).click();
      assert((await page.locator('#view').textContent()).includes(data.limitations[0]));
      assert((await page.locator('#view').textContent()).includes(data.source.manifest_payload_sha256));

      await page.locator('#play').click();
      const playLabel=await page.locator('#play').textContent();
      assert(language==='zh-CN'?playLabel==='暂停':playLabel==='Pause');
      await page.locator('#play').click();

      const transition=await page.locator('.bar').first().evaluate(n=>getComputedStyle(n).transitionDuration);
      assert.equal(transition,'0s');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
      const csp=await page.evaluate(()=>window.__csp);assert.deepEqual(csp,[]);
      results.push({language,viewport,page_errors:errors,external_requests:external,csp_violations:csp});
      await context.close();
    }
  }
}finally{
  await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
console.log(JSON.stringify({success:true,tests:results}));
