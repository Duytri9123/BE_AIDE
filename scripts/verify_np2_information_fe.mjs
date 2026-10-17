import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
const information=JSON.parse(fs.readFileSync('tmp/np2-review/customer-information.json','utf8'));
const device=fixture.browser.items.find(d=>d.brand==='CHINT' && d.product_code==='NP2');
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url()),path=url.pathname.replace(/^\/api\/v1/,'');
  if(path==='/equipment-library/browser-data')return route.fulfill({json:{...fixture.browser,items:[device],total:1}});
  if(path.endsWith('/catalog-information')){
    if(url.searchParams.get('scope')!=='current')return route.fulfill({json:{items:[],total:0}});
   const skip=Number(url.searchParams.get('skip')||0);
   return route.fulfill({json:{items:information.slice(skip,skip+100),total:information.length}});
  }
  if(path==='/library-access')return route.fulfill({json:{can_download:false}});
  if(fixture.assets[path])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[path])});
  return route.continue();
 });
 await page.goto('http://127.0.0.1:5197/catalog-qa.html');
 const rows=page.locator('.library-prices tbody tr');await rows.first().waitFor();
 while(await rows.count()<information.length){
  const count=await rows.count();await page.getByRole('button',{name:'Xem thêm mã và thông số',exact:true}).click();
  await page.waitForFunction(n=>document.querySelectorAll('.library-prices tbody tr').length>n,count);
 }
  const text=await page.locator('[data-product-scope="current"]').innerText();
 if(/Căn cứ|Trang tài liệu|bóc tách|CatalogTB|SOURCE[-_]|SRC_/i.test(text))throw Error('Private metadata visible');
 for(const sku of ['NP2-BA35','NP2-BW4462','NP2-BE101'])if(!text.includes(sku))throw Error('Missing '+sku);
 if(errors.length)throw Error(errors.join('\n'));
 const result={rows_checked:await rows.count(),manufacturer_np2_codes:new Set(information.filter(r=>r.sku.startsWith('NP2-')).map(r=>r.sku)).size,page_errors:errors};
 console.log(JSON.stringify(result));
 fs.writeFileSync('docs/np2-information-fe-check.json',JSON.stringify(result,null,2)+'\n');
}finally{await browser.close()}
