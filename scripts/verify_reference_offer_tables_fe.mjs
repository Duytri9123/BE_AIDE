import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('tmp/customer-catalog-qa/data.json','utf8'));
const offers=JSON.parse(fs.readFileSync('tmp/hager-offer-qa.json','utf8'));
const browser=await chromium.launch({headless:true});
try{
 const results=[];
 for(const variant of ['raw','public']){
  const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url()),path=url.pathname.replace(/^\/api\/v1/,'');
   if(path==='/equipment-library/browser-data')return route.fulfill({json:{...fixture.browser,items:[{...fixture.browser.items[0],display:'MCCB ABB A1 · 1P',brand:'ABB',spec:{so_cuc:'1P'}}],total:1}});
   if(path.endsWith('/catalog-information')){
    const items=url.searchParams.get('scope')==='other_brands'?offers[variant]:[];
    return route.fulfill({json:{items,total:items.length}});
   }
   if(path==='/library-access')return route.fulfill({json:{can_download:false}});
   if(fixture.assets[path])return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(fixture.assets[path])});
   return route.continue();
  });
  await page.goto('http://127.0.0.1:5197/catalog-qa.html');
  const section=page.locator('[data-product-scope="other_brands"]');
  await section.locator('tbody tr').first().waitFor();
  if(await section.locator('.pricebook').count()!==1)throw Error('Offers are still split into separate books');
  if(await section.locator('tbody tr').count()!==4)throw Error('Missing Hager offers');
  const text=await section.innerText();
  for(const value of ['HDA014Z','HDA018Z','HDA023Z','HDA030Z','Số cực: 1P','1.056.990 ₫'])if(!text.includes(value))throw Error('Missing '+value);
  if(/Hager\s*·\s*$/.test(text))throw Error('Empty group heading');
  const links=await section.locator('tbody a').evaluateAll(nodes=>nodes.map(n=>n.href));
  if(JSON.stringify(links)!==JSON.stringify(offers[variant].map(r=>r.source_url)))throw Error('Row document links changed');
  if(errors.length)throw Error(errors.join('\n'));
  results.push({payload:variant,books:1,rows:4,names_specs_prices_visible:true,correct_document_per_row:true});
  await section.scrollIntoViewIfNeeded();
  await page.screenshot({path:`outputs/hager-offer-tables-${variant}.png`});
  await page.close();
 }
 fs.writeFileSync('docs/reference-offer-tables-fe-check.json',JSON.stringify({results},null,2)+'\n');
 console.log(JSON.stringify({results}));
}finally{await browser.close()}
