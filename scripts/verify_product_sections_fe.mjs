import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
const actual=JSON.parse(fs.readFileSync('tmp/product-sections-qa.json','utf8'));
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url()),path=url.pathname.replace(/^\/api\/v1/,'');
  if(path==='/equipment-library/browser-data')return route.fulfill({json:{...fixture.browser,items:[{...actual.device,visual_candidates:[{comparison_name:'must not render',comparison_preview:'/must-not-load'}]}],total:1}});
  if(path.endsWith('/catalog-information')){
   const scope=url.searchParams.get('scope')||'current';const data=actual[scope];
   const first=data.items[0];
   const bad=first?{...first,id:'wrong-poles',sku:'WRONG-3P',specifications:{'Số cực':'3P'},cells:first.columns.map(()=> 'WRONG-3P')}:null;
   return route.fulfill({json:{...data,items:[...data.items,...(bad?[bad]:[])],total:data.items.length+(bad?1:0)}});
  }
  if(path==='/library-access')return route.fulfill({json:{can_download:false}});
  if(fixture.assets[path])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[path])});
  if(path==='/must-not-load')throw Error('Removed visual comparison still loads');
  return route.continue();
 });
 await page.goto('http://127.0.0.1:5197/catalog-qa.html');
 await page.waitForFunction(()=>document.querySelectorAll('[data-product-scope]').length===3 && !document.querySelector('.library-prices [role="status"]'));
 const text=await page.locator('.device-detail').innerText();
 if(/Đối chiếu theo hình ảnh CAD|must not render|WRONG-3P|Bảng thông tin thiết bị/.test(text))throw Error('Removed content or incorrect pole configuration visible');
 const counts={};
 for(const scope of ['current','same_brand','other_brands']){
  const section=page.locator(`[data-product-scope="${scope}"]`);
  counts[scope]=await section.locator('tbody tr').count();
  if(actual[scope].items.length && !counts[scope])throw Error('Missing '+scope);
 }
 if(errors.length)throw Error(errors.join('\n'));
 const result={device:actual.device.display,sections:counts,wrong_poles_visible:false,visual_comparison_visible:false,page_errors:errors};
 fs.writeFileSync('docs/product-sections-fe-check.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 await page.locator('[data-product-scope="same_brand"]').scrollIntoViewIfNeeded();await page.screenshot({path:'outputs/product-sections-4p.png'});
}finally{await browser.close()}
