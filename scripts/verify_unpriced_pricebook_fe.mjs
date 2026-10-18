import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const feed=JSON.parse(fs.readFileSync('tmp/priority-pricebooks/public-feed.json','utf8'));
const qaRoot='../AIDE/packages/cad-viewer-example/';
fs.writeFileSync(qaRoot+'pricebook-qa.html','<html><head><meta charset="utf-8"></head><body><div id="app"></div><script type="module" src="/src/pricebook-qa.ts"></script></body></html>');
fs.writeFileSync(qaRoot+'src/pricebook-qa.ts',`import {createApp} from 'vue';
import {createPinia} from 'pinia';
import {createRouter,createMemoryHistory} from 'vue-router';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';import './styles/main.css';
import Page from './components/dashboard/DeviceCatalogPage.vue';
createApp(Page).use(createPinia()).use(createRouter({history:createMemoryHistory(),routes:[]})).use(ElementPlus).mount('#app');`);
const browser=await chromium.launch({headless:true});
const results=[];
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/device-catalog?*',route=>{
   const q=new URL(route.request().url()).searchParams,brand=q.get('brand');
   const all=feed.items.filter(r=>!brand||r.brand===brand);
   const selected=[...all.filter(r=>r.price!=null).slice(0,2),...all.filter(r=>r.price==null).slice(0,2)];
   return route.fulfill({json:{...feed,items:selected,total:selected.length}});
 });
 await page.route('**/users/me',route=>route.fulfill({json:{id:1,name:'QA',role:'user'}}));
 await page.goto('http://127.0.0.1:5197/pricebook-qa.html');
 for(const brand of ['LS Electric','CHINT','Mitsubishi Electric','Schneider Electric','Shihlin','ABB']){
   await page.getByLabel('Lọc theo hãng',{exact:true}).selectOption(brand);
   await page.waitForFunction(b=>document.querySelector('.result-heading h2')?.textContent?.includes(b)&&document.querySelectorAll('.pricebook tbody tr').length===4,brand);
   const rows=page.locator('.pricebook tbody tr');
   if(await rows.count()!==4)throw Error('Missing rows: '+brand);
   const text=await page.locator('.pricebook-grid').innerText();
   if(!text.includes('---'))throw Error('Missing price placeholder: '+brand);
   if(/Căn cứ|Trang tài liệu|source_sha256|\{\}/.test(text))throw Error('Private or empty metadata: '+brand);
   for(const table of await page.locator('.pricebook table').all()){
      const headers=await table.locator('th').count();
      for(const row of await table.locator('tbody tr').all())if(await row.locator('td').count()!==headers)throw Error('Misaligned cells: '+brand);
   }
   results.push({brand,priced_rows:2,unpriced_rows:2,missing_price:'---',aligned_columns:true});
 }
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('docs/unpriced-pricebook-fe-check.json',JSON.stringify({results,page_errors:errors},null,2)+'\n');
 await page.screenshot({path:'tmp/priority-pricebooks/pricebook-fe.png',fullPage:true});
 console.log(JSON.stringify({results,page_errors:errors}));
}finally{await browser.close();fs.unlinkSync(qaRoot+'pricebook-qa.html');fs.unlinkSync(qaRoot+'src/pricebook-qa.ts')}
