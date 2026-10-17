// Exercise the real Vue component with customer API payloads and actual CAD SVGs.
// This isolated UI test never changes authentication or a user's browser session.
import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
const browser=await chromium.launch({headless:true});
const errors=[],failures=[];let checked=0,views=0;
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}});
 page.setDefaultTimeout(7000);
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());const pathname=url.pathname.replace(/^\/api\/v1/,'');
  if(pathname==='/equipment-library/browser-data'){
   const skip=Number(url.searchParams.get('skip')||0),limit=Number(url.searchParams.get('limit')||12);
   let items=fixture.browser.items;const q=url.searchParams.get('q'),brand=url.searchParams.get('brand'),category=url.searchParams.get('category');
   if(q)items=items.filter(i=>[i.display,i.product_code,i.brand].join(' ').toLowerCase().includes(q.toLowerCase()));
   if(brand)items=items.filter(i=>i.brand===brand);if(category)items=items.filter(i=>i.category===category);
   return route.fulfill({json:{...fixture.browser,brands:[...new Set(fixture.browser.items.map(d=>d.brand).filter(Boolean))],total:items.length,items:items.slice(skip,skip+limit)}});
  }
  if(pathname==='/library-access')return route.fulfill({json:{can_download:false}});
  const information=pathname.match(/^\/equipment-library\/([^/]+)\/catalog-information$/);
  if(information){const rows=fixture.information[information[1]]||[];const skip=Number(url.searchParams.get('skip')||0);return route.fulfill({json:{items:rows.slice(skip,skip+100),total:rows.length}})}
  if(fixture.assets[pathname])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[pathname])});
  if(pathname.startsWith('/equipment-library/'))return route.fulfill({status:404,body:'Missing audited asset'});
  return route.continue();
 });
 await page.goto('http://127.0.0.1:5197/catalog-qa.html');
 await page.locator('[data-device-id]').first().waitFor();
 while(await page.locator('[data-device-id]').count()<fixture.browser.items.length){
  const before=await page.locator('[data-device-id]').count();
  await page.getByRole('button',{name:'Tải thêm thiết bị',exact:true}).click();
  await page.waitForFunction(n=>document.querySelectorAll('[data-device-id]').length>n,before);
  if(before%120===0)console.log(`FE loaded ${before}/${fixture.browser.items.length}`);
 }
 console.log('FE pagination complete; checking device details and every view.');
 for(const device of fixture.browser.items){
  try{
   await page.locator(`[data-device-id="${device.id}"]`).click();
   await page.waitForFunction(id=>document.querySelector(`[data-device-id="${id}"]`)?.classList.contains('active'),device.id);
   const detail=page.locator('.device-detail');
   await page.waitForFunction(()=>!document.querySelector('.library-prices [role="status"]'));
   const text=await detail.innerText();
   if(/Căn cứ:|Trang tài liệu:|Thông tin CAD nguồn|bóc tách|thong_tin_|CatalogTB|checksum|SOURCE[-_]|SRC_/i.test(text))throw Error('Internal metadata visible');
   if(!await detail.locator('h2').count())throw Error('Missing device heading');
   const expected=fixture.information[device.id]||[];
   if(expected.length && !await detail.locator('.library-prices tbody tr').count())throw Error('Missing information table rows');
   for(let n=0;n<device.views.length;n++){
    await detail.locator('.view-tabs button').nth(n).click();
    await page.waitForFunction(()=>{const img=document.querySelector('.preview-frame img');return img&&img.complete&&img.naturalWidth>0});views++;
   }
   checked++;
  }catch(e){failures.push({device:device.id,error:e.message.slice(0,500)})}
  if((checked+failures.length)%100===0)console.log(`FE checked ${checked+failures.length}/${fixture.browser.items.length}`);
 }
 await page.locator(`[data-device-id="${fixture.browser.items[0].id}"]`).click();
 await page.locator('.library-prices').scrollIntoViewIfNeeded();
 await page.screenshot({path:'outputs/customer-fe-catalog-final.png'});
 const result={devices_expected:fixture.browser.items.length,devices_checked:checked,views_checked:views,failures,page_errors:errors,
  environment:'Actual Vue EquipmentLibraryPage, isolated API fixtures from production serializers and actual CAD assets; no authenticated user session used.'};
 fs.writeFileSync('docs/all-devices-fe-check.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 if(failures.length||errors.length)process.exitCode=1;
}finally{await browser.close()}
