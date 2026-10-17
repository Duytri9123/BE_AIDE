import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
const device=fixture.browser.items.find(d=>d.product_code==='NXB-63' && d.spec.so_cuc==='2P');
if(!device || device.views.length!==2)throw Error('NXB-63 2P faces were not joined');
const facts={'Số cực':'2P','Căn cứ':'Nhãn đọc trực tiếp từ CAD nguồn','Phạm vi':'Mã/dòng trên bản vẽ','Trang tài liệu':4};
device.catalog_references={options:[{brand:'CHINT',model:'NXB-63',specifications:facts,source_url:'https://www.chintglobal.com/'}]};
device.use='Mã/dòng tra từ block CAD';device.spec={...device.spec,...facts};
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage();
 await page.route('**/*',async route=>{
  const path=new URL(route.request().url()).pathname.replace(/^\/api\/v1/,'');
  if(path==='/equipment-library/browser-data')return route.fulfill({json:{...fixture.browser,items:[device],total:1}});
  if(path.endsWith('/catalog-information')){
   if(new URL(route.request().url()).searchParams.get('scope')!=='current')return route.fulfill({json:{items:[],total:0}});
   return route.fulfill({status:404,json:{detail:'Not Found'}});
  }
  if(path==='/device-catalog')return route.fulfill({json:{total:1,items:[{
   id:'manufacturer-original-row',brand:'CHINT',sku:'NXB-63 2P',item_name:'NXB-63 2P',group:'MCB · NXB-63',
   information_kind:'pricebook',price:null,book_key:'chint-nxb63',columns:['Tên hàng','Thông số','Giá'],
   cells:['NXB-63 2P','Số cực: 2P', ''],edition:'2026'
  }]}});
  if(path==='/library-access')return route.fulfill({json:{can_download:false}});
  if(fixture.assets[path])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[path])});
  return route.continue();
 });
 await page.goto('http://127.0.0.1:5197/catalog-qa.html');
 await page.locator('.library-prices tbody tr').first().waitFor();
 const text=await page.locator('.device-detail').innerText();
 if(/Căn cứ|Phạm vi|Trang tài liệu|block CAD|Không tải được/i.test(text))throw Error('Legacy metadata or endpoint failure is visible');
 if(!text.includes('Số cực: 2P'))throw Error('Product specifications lost');
 if(await page.locator('.view-tabs button').count()!==2)throw Error('Missing complementary views');
 console.log('PASS: older API payload sanitized; 404 retrieves original pricebook rows; NXB-63 2P has both faces.');
}finally{await browser.close()}
