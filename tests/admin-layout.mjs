import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import puppeteer from 'puppeteer-core';

const browser = await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const output = 'test-results/admin-layout';
await fs.mkdir(output,{recursive:true});
const page = await browser.newPage();
const errors = [];
page.on('pageerror',error=>errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:8000/admin/login',{waitUntil:'networkidle0'});
  await page.type('input[name=email]','admin@neushop.local');
  await page.type('input[name=password]','Admin@12345');
  await Promise.all([page.waitForNavigation({waitUntil:'networkidle0'}),page.click('form button')]);
  const cases = ['','/products','/products/new','/orders','/reports','/catalog','/users','/vouchers','/inventory'];
  const measurements = [];
  for (const width of [320,768,1280]) {
    await page.setViewport({width,height:900});
    for (const route of cases) {
      const response = await page.goto('http://127.0.0.1:8000/admin'+route,{waitUntil:'networkidle0'});
      assert.equal(response.status(),200,route);
      const measurement = await page.evaluate(()=>({
        width:innerWidth,scroll:document.documentElement.scrollWidth,
        filters:[...document.querySelectorAll('.admin-search input:not([type=hidden]),.admin-search select,.admin-search button')].filter(el=>el.getClientRects().length&&el.getBoundingClientRect().height>0).map(el=>({tag:el.tagName,y:el.getBoundingClientRect().y,bottom:el.getBoundingClientRect().bottom,height:el.getBoundingClientRect().height})),
        fieldPairs:[...document.querySelectorAll('.form-two-col')].map(row=>[...row.querySelectorAll(':scope > .field')].map(field=>{let c=field.querySelector('input,select,textarea');c=c?.closest('.upload-zone')||c;return c?{y:c.getBoundingClientRect().y,width:c.getBoundingClientRect().width}:null})).filter(pair=>pair.length===2&&pair.every(Boolean)),
      }));
      measurements.push({route,...measurement});
      assert(measurement.scroll<=width+1,`${route} overflow at ${width}: ${measurement.scroll}`);
      if (route==='/reports' && width>=640 && measurement.filters.length>1) {
        assert(Math.max(...measurement.filters.map(f=>f.bottom))-Math.min(...measurement.filters.map(f=>f.bottom))<2,`Report controls not aligned at ${width}`);
      }
      for (const pair of measurement.fieldPairs) if(width>=640) assert(Math.abs(pair[0].y-pair[1].y)<2,`Paired controls not aligned ${route}/${width}: ${JSON.stringify(pair)}`);
      const filename=(route.replaceAll('/','-')||'dashboard')+'-'+width+'.png';
      if (['','/reports','/products','/products/new','/vouchers'].includes(route)) await page.screenshot({path:output+'/'+filename,fullPage:route!='/products'});
    }
  }
  assert.deepEqual(errors,[]);
  await fs.writeFile(output+'/measurements.json',JSON.stringify(measurements,null,2));
  console.log(`${cases.length*3} admin viewport checks passed: overflow, report filters, paired form controls; no JavaScript errors.`);
} finally {await browser.close();}
