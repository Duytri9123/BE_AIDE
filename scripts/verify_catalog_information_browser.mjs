import {chromium} from '../../AIDE/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const browser=await chromium.launch({headless:true});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(new URL('../data/CatalogTB/index.html',import.meta.url).href,{waitUntil:'networkidle'});
 await page.getByRole('button',{name:/^ABB\s*\d+ hồ sơ$/}).click();
 await page.getByRole('button',{name:/MCCB ABB A1.*1P/}).first().click();
 const heading=page.getByRole('heading',{name:'Danh mục mã và thông số từ bảng giá / catalog'});
 await heading.scrollIntoViewIfNeeded();
 await page.screenshot({path:'outputs/catalog-restored-information-browser.png'});
 const rows=await page.locator('table').allTextContents();
 const hasOrderCode=rows.some(t=>t.includes('1SDA066485R1'));
 if(!hasOrderCode)throw Error('Original ABB A1 ordering code is missing from the rendered table');
 await page.getByRole('button',{name:/AX12/}).first().click();
 const visualHeading=page.getByRole('heading',{name:'Đối chiếu theo hình ảnh CAD'});
 await visualHeading.scrollIntoViewIfNeeded();
 await page.screenshot({path:'outputs/catalog-visual-comparison-browser.png'});
 const comparisonImage=page.locator('img[alt*="AX25"]').first();
 await comparisonImage.waitFor({state:'visible'});
 const imageLoaded=await comparisonImage.evaluate(img=>img.complete&&img.naturalWidth>0);
 if(!imageLoaded)throw Error('Visual comparison preview did not load');
 if(errors.length)throw Error(errors.join('\n'));
 const result={original_order_code_visible:hasOrderCode,visual_comparison_image_loaded:imageLoaded,page_errors:errors,screenshot:'outputs/catalog-restored-information-browser.png'};
 fs.writeFileSync('docs/catalog-information-browser-check.json',JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result));
}finally{await browser.close();}
