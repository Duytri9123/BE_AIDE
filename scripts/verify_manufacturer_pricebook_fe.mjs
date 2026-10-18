import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
const actual=JSON.parse(fs.readFileSync('tmp/manufacturer-pricebook-qa.json','utf8'));
const browser=await chromium.launch({headless:true});
const results=[];
try{
 for(const legacy of [false,true]){
  const page=await browser.newPage({viewport:{width:1600,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const actualRows=actual.rows.filter(r=>r.information_kind==='pricebook');
  if(!actualRows.length)throw Error('No actual ABB pricebook rows');
  const device=structuredClone(actual.device);
  device.catalog_references={options:[{brand:'CHINT',model:'NM8',specifications:{'Số cực':'1P'}}]};
  const wrong={...actualRows[0],id:'wrong-maker',brand:'CHINT',sku:'NM8',item_name:'CHINT NM8'};
  let legacyCalled=false;
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url()),path=url.pathname.replace(/^\/api\/v1/,'');
   if(path==='/equipment-library/browser-data')return route.fulfill({json:{...fixture.browser,items:[device],total:1}});
   if(path.endsWith('/catalog-information')){
    if((url.searchParams.get('scope')||'current')!=='current')return route.fulfill({json:{items:[],total:0}});
    if(legacy)return route.fulfill({status:404,json:{detail:'Not Found'}});
    return route.fulfill({json:{items:[...actualRows,wrong],total:actualRows.length+1}});
   }
   if(path==='/device-catalog'){
    if(url.searchParams.get('brand')!=='ABB')throw Error('Legacy price lookup lacks manufacturer constraint');
    legacyCalled=true;return route.fulfill({json:{items:[...actualRows,wrong],total:actualRows.length+1}});
   }
   if(path==='/library-access')return route.fulfill({json:{can_download:false}});
   if(fixture.assets[path])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[path])});
   return route.continue();
  });
  await page.goto('http://127.0.0.1:5197/catalog-qa.html');
  const table=page.locator('.library-prices table').first();await table.locator('tbody tr').first().waitFor();
  const headings=await table.locator('thead th').allTextContents();
  if(JSON.stringify(headings)!==JSON.stringify(actualRows[0].columns))throw Error('Original pricebook columns altered: '+headings);
  const text=await page.locator('[data-product-scope="current"]').innerText();
  if(/CHINT|Thông tin sản phẩm|Căn cứ|Trang tài liệu/i.test(text))throw Error('Wrong manufacturer or synthetic table visible');
  if(!text.includes('ABB'))throw Error('Actual manufacturer pricebook not identified');
  if(!await page.locator('[data-product-scope="other_brands"]').count())throw Error('Missing separate other manufacturer section');
  if(await page.getByRole('heading',{name:'Bảng thông tin thiết bị',exact:true}).count())throw Error('Duplicate information table still visible');
  const cells=await table.locator('tbody tr').first().locator('td').allTextContents();
  if(cells[0]!==actualRows[0].cells[0]||cells[1]!==actualRows[0].sku)throw Error('Original item name or ordering code lost');
  if(legacy!==legacyCalled)throw Error('Incorrect legacy endpoint selection');
  if(errors.length)throw Error(errors.join('\n'));
  results.push({legacy_endpoint:legacy,original_columns:headings,rows:await page.locator('.library-prices tbody tr').count(),other_manufacturers_in_pricebook:false,separate_other_manufacturers_section:true,duplicate_information_table:false});
  await table.locator('thead').scrollIntoViewIfNeeded();
  await page.screenshot({path:`outputs/abb-original-pricebook-${legacy?'legacy':'current'}.png`});
  await page.close();
 }
 fs.writeFileSync('docs/manufacturer-pricebook-fe-check.json',JSON.stringify({results},null,2)+'\n');
 console.log(JSON.stringify({results}));
}finally{await browser.close()}
