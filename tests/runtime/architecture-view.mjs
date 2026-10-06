/** Exercise English and Chinese architecture HTML views in a real browser. */
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
    const root=path.join(work,'generated',`architecture-${language}`);
    const payload=JSON.parse(await fs.readFile(path.join(root,'architecture.json'),'utf8'));
    for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
      const context=await browser.newContext({viewport});
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
      await page.goto(`${origin}/architecture-${language}/index.html`,{waitUntil:'networkidle'});
      assert.equal(await page.locator('html').getAttribute('lang'),payload.language);
      assert.equal(await page.locator('h1').textContent(),payload.subject.title);
      const buttons=page.locator('#nav button');
      assert.equal(await buttons.count(),4);
      assert.equal(await buttons.nth(0).getAttribute('aria-current'),'true');
      assert((await page.locator('#view').textContent()).includes(payload.components[0].responsibility));

      await buttons.nth(1).focus();await page.keyboard.press('Enter');
      const flowText=await page.locator('#view').textContent();
      assert(flowText.includes('caller'));assert(flowText.includes('editor'));
      assert(flowText.includes(payload.flows[0].steps[1].condition));

      await buttons.nth(2).click();
      assert((await page.locator('#view').textContent()).includes(payload.invariants[0].text));
      await buttons.nth(3).click();
      assert((await page.locator('#view').textContent()).includes('tests/editor.py'));

      assert((await page.locator('#limits').textContent()).includes(payload.limitations[0].text));
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
      const csp=await page.evaluate(()=>window.__csp);assert.deepEqual(csp,[]);
      const chromeText=await page.locator('body').textContent();
      if(language==='zh-CN'){
        for(const value of ['系统模型','不变量','证据','限制','来源标识'])assert(chromeText.includes(value),value);
      }else{
        for(const value of ['System model','Invariants','Evidence','Limits','Source identity'])assert(chromeText.includes(value),value);
      }
      results.push({language,viewport,buttons:await buttons.count(),page_errors:errors,
        external_requests:external,csp_violations:csp});
      await context.close();
    }
  }
} finally {
  await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
console.log(JSON.stringify({success:true,tests:results}));
