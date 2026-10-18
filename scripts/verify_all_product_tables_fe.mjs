// Exercise the real Vue component with customer API payloads and actual CAD SVGs.
// This isolated UI test never changes authentication or a user's browser session.
import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
fixture.browser.items=JSON.parse(fs.readFileSync('tmp/all-product-tables/devices.json','utf8'));
const part=Number(process.env.QA_PART||0),parts=Number(process.env.QA_PARTS||1);
const size=Math.ceil(fixture.browser.items.length/parts);
fixture.browser.items=fixture.browser.items.slice(part*size,(part+1)*size);
fixture.browser.total=fixture.browser.items.length;
const browser=await chromium.launch({headless:true});
const errors=[],failures=[];let checked=0,views=0,tables=0,rows=0;
try{
 let batchDevices=fixture.browser.items.slice(0,12);
 const page=await browser.newPage({viewport:{width:1600,height:1000}});
 page.setDefaultTimeout(7000);
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());const pathname=url.pathname.replace(/^\/api\/v1/,'');
  if(pathname==='/equipment-library/browser-data'){
   const skip=Number(url.searchParams.get('skip')||0),limit=Number(url.searchParams.get('limit')||12);
   let items=batchDevices;const q=url.searchParams.get('q'),brand=url.searchParams.get('brand'),category=url.searchParams.get('category');
   if(q)items=items.filter(i=>[i.display,i.product_code,i.brand].join(' ').toLowerCase().includes(q.toLowerCase()));
   if(brand)items=items.filter(i=>i.brand===brand);if(category)items=items.filter(i=>i.category===category);
   return route.fulfill({json:{...fixture.browser,brands:[...new Set(fixture.browser.items.map(d=>d.brand).filter(Boolean))],total:items.length,items:items.slice(skip,skip+limit)}});
  }
  if(pathname==='/library-access')return route.fulfill({json:{can_download:false}});
  const information=pathname.match(/^\/equipment-library\/([^/]+)\/catalog-information$/);
  if(information){const sections=JSON.parse(fs.readFileSync(`tmp/all-product-tables/${information[1]}.json`,'utf8'));const rows=sections[url.searchParams.get('scope')||'current']||[];const skip=Number(url.searchParams.get('skip')||0);return route.fulfill({json:{items:rows.slice(skip,skip+100),total:rows.length}})}
  if(fixture.assets[pathname])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[pathname])});
  if(pathname.startsWith('/equipment-library/'))return route.fulfill({status:404,body:'Missing audited asset'});
  return route.continue();
 });
 await page.goto('http://127.0.0.1:5197/catalog-qa.html');
 await page.locator('[data-device-id]').first().waitFor();
 for(let batch=0;batch<fixture.browser.items.length;batch+=12){
  batchDevices=fixture.browser.items.slice(batch,batch+12);
  if(batch)await page.reload();
  await page.locator('[data-device-id]').first().waitFor();
 for(const device of batchDevices){
  try{
   await page.locator(`[data-device-id="${device.id}"]`).click();
   await page.waitForFunction(id=>document.querySelector(`[data-device-id="${id}"]`)?.classList.contains('active'),device.id);
   const detail=page.locator('.device-detail');
   await page.waitForFunction(()=>!document.querySelector('.library-prices [role="status"]'));
   for(const section of await detail.locator('[data-product-scope]').all()){
    while(await section.getByRole('button',{name:'Xem thêm mã và thông số',exact:true}).count()){
     await section.getByRole('button',{name:'Xem thêm mã và thông số',exact:true}).click();
     await page.waitForFunction(()=>!Array.from(document.querySelectorAll('.library-prices button')).some(b=>b.textContent==='Đang tải…'));
    }
   }
   const text=await detail.innerText();
   if(/Xem tài liệu nhà cung cấp|Cần đối chiếu|Xác nhận cấu hình và kích thước lắp đặt|\{\}|so_cuc:|dong_chinh_dinh:|kha_nang_cat:/.test(text))throw Error('Redundant or raw technical text visible');
   if(/Căn cứ:|Trang tài liệu:|Thông tin CAD nguồn|bóc tách|thong_tin_|CatalogTB|checksum|SOURCE[-_]|SRC_/i.test(text))throw Error('Internal metadata visible');
   if(!await detail.locator('h2').count())throw Error('Missing device heading');
   const expected=JSON.parse(fs.readFileSync(`tmp/all-product-tables/${device.id}.json`,'utf8')).current||[];
   if(expected.some(r=>!['device','catalog_reference'].includes(r.information_kind)) && !await detail.locator('.library-prices tbody tr').count())throw Error('Missing information table rows');
   for(let n=0;n<device.views.length;n++){
    await detail.locator('.view-tabs button').nth(n).click();
    await page.waitForFunction(()=>{const img=document.querySelector('.preview-frame img');return img&&img.complete&&img.naturalWidth>0});views++;
   }
   tables+=await detail.locator('.library-prices table').count();
   rows+=await detail.locator('.library-prices tbody tr').count();
   checked++;
  }catch(e){failures.push({device:device.id,error:e.message.slice(0,500)});console.log('FAIL',device.id,e.message.slice(0,180))}
  if(checked<5)console.log('Checked',device.id,checked);
  if((checked+failures.length)%25===0)console.log(`FE checked ${checked+failures.length}/${fixture.browser.items.length}`);
 }
 }
 await page.locator('[data-device-id]').first().click();
 await page.locator('.library-prices').first().scrollIntoViewIfNeeded();
 await page.screenshot({path:`outputs/customer-fe-catalog-part-${part}.png`});
 const result={devices_expected:fixture.browser.items.length,devices_checked:checked,views_checked:views,tables_checked:tables,rows_rendered:rows,failures,page_errors:errors,
  environment:'All devices, every CAD view, three scopes and all table pages in actual Vue UI; isolated production selectors/serializers with saved authoritative inventory and actual assets, not a logged-in deployment session.'};
 fs.writeFileSync(`docs/all-product-tables-fe-part-${part}.json`,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 if(failures.length||errors.length)process.exitCode=1;
}finally{await browser.close()}
