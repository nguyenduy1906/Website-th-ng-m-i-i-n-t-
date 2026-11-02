import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const root = resolve('.'), phase = process.argv.includes('--after') ? 'after' : 'before';
mkdirSync(join(root, 'test-results'), { recursive: true });
const output = mkdtempSync(join(root, `test-results/redesign-${phase}-`));
const database = join(output, 'shop.db'), port = 8022, base = `http://127.0.0.1:${port}`;
const copied = spawnSync('python', ['-c', "import sqlite3,sys;a=sqlite3.connect(sys.argv[1]);b=sqlite3.connect(sys.argv[2]);a.backup(b);print(b.execute(\"SELECT id FROM products WHERE active=1 AND category='laptop' LIMIT 1\").fetchone()[0]);b.close();a.close()", join(root, 'data/shop.db'), database], { encoding: 'utf8', windowsHide: true });
assert.equal(copied.status, 0, copied.stderr);
const product = Number(copied.stdout.trim());
const server = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], { cwd: root, env: { ...process.env, NEU_DB_PATH: database, NEU_SESSION_SECRET: 'redesign-audit-only' }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
let logs = '', browser;
server.stdout.on('data', chunk => { logs += chunk; writeFileSync(join(output,'server.log'),logs); }); server.stderr.on('data', chunk => { logs += chunk; writeFileSync(join(output,'server.log'),logs); });
const results = [], javascript = [], focusSamples = [], railSamples = [], pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const analyze = () => {
  const rgba = color => (color.match(/[\d.]+/g) || [255,255,255,1]).map(Number);
  const blend = (front, back) => { const alpha = front.length < 4 ? 1 : front[3]; return front.slice(0,3).map((value,index) => alpha*value+(1-alpha)*back[index]); };
  const background = element => { const chain = []; for (let node=element; node; node=node.parentElement) chain.unshift(getComputedStyle(node)); let color=[255,255,255]; for(const style of chain)color=blend(rgba(style.backgroundColor),color);return color; };
  const luminance = color => color.map(value=>{value/=255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;}).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
  const unique = new Map(), walker = document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const node=walker.currentNode, element=node.parentElement, value=node.textContent.trim();
    if(!value||!element||element.closest('script,style,[aria-hidden="true"],.sr-only')||!element.getClientRects().length)continue;
    const style=getComputedStyle(element);if(style.visibility==='hidden'||Number(style.opacity)===0)continue;
    const bg=background(element),fg=blend(rgba(style.color),bg),ratio=(Math.max(luminance(fg),luminance(bg))+.05)/(Math.min(luminance(fg),luminance(bg))+.05);
    const size=parseFloat(style.fontSize),large=size>=24||(size>=18.66&&Number(style.fontWeight)>=700),threshold=large?3:4.5;
    const key=[style.color,bg.join(),size,element.closest('.admin-rail')?'rail':element.closest('.site-header')?'header':'body'].join('|');
    if(!unique.has(key))unique.set(key,{text:value.slice(0,85),fg:style.color,bg:bg.map(Math.round),size,ratio:Number(ratio.toFixed(2)),threshold,region:key.split('|').at(-1)});
  }
  const controls=[...document.querySelectorAll('button,input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]),select,summary')].filter(element=>element.getClientRects().length&&getComputedStyle(element).visibility!=='hidden').map(element=>{const box=element.getBoundingClientRect();return{label:(element.getAttribute('aria-label')||element.textContent||element.name||element.id).trim().slice(0,70),width:Math.round(box.width),height:Math.round(box.height),disabled:element.disabled};});
  const fontFaces=[...document.fonts].filter(face=>face.family.replaceAll('"','').includes('Be Vietnam Pro')&&face.status==='loaded').map(face=>({family:face.family,weight:face.weight}));
  const fontResources=performance.getEntriesByType('resource').filter(entry=>entry.name.includes('.woff2')).map(entry=>new URL(entry.name).pathname);
  const radiusFailures=[...document.querySelectorAll('body *')].filter(element=>element instanceof HTMLElement&&element.getClientRects().length).flatMap(element=>{
    const corners=['borderTopLeftRadius','borderTopRightRadius','borderBottomRightRadius','borderBottomLeftRadius'];
    return [null,'::before','::after'].flatMap(pseudo=>{
      const style=getComputedStyle(element,pseudo);
      if(pseudo&&(['none','normal'].includes(style.content)||style.display==='none'))return[];
      return corners.filter(corner=>{const value=parseFloat(style[corner]);return value>0&&Math.abs(value-5)>.1;}).map(corner=>({element:element.tagName.toLowerCase()+'.'+element.className+(pseudo||''),corner,value:style[corner]}));
    });
  });
  return {overflow:document.documentElement.scrollWidth>innerWidth+1,contrasts:[...unique.values()],contrastFailures:[...unique.values()].filter(item=>item.ratio<item.threshold),smallControls:controls.filter(item=>!item.disabled&&(item.width<44||item.height<44)),radiusFailures,font:getComputedStyle(document.body).fontFamily,fontFaces,fontResources};
};
try {
  let ready=false;for(let i=0;i<100;i++){try{if((await fetch(base+'/api/health')).ok){ready=true;break;}}catch{}await pause(100);}assert(ready,logs);
  browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const customerContext=await browser.createBrowserContext(),adminContext=await browser.createBrowserContext();
  const customer=await customerContext.newPage(),admin=await adminContext.newPage();
  console.log('Audit browser ready: '+output);
  for(const page of [customer,admin])page.on('pageerror',error=>javascript.push(error.message));
  await customer.goto(base+`/products/${product}`,{waitUntil:'load'});
  await customer.evaluate(async()=>{
    const form=document.querySelector('.buy-form');
    await fetch('/cart/add',{method:'POST',body:new URLSearchParams(new FormData(form))});
  });
  console.log('Guest cart fixture ready');
  await admin.goto(base+'/admin/login',{waitUntil:'load'});await admin.type('#email','admin@neushop.local');await admin.type('#password','Admin@12345');
  await Promise.all([admin.waitForNavigation({waitUntil:'load'}),admin.click('.auth-form form button')]);
  console.log('Admin authenticated');
  for(const width of [375,1440])for(const [page,name,path] of [[customer,'home','/'],[customer,'catalog','/products'],[customer,'product',`/products/${product}`],[customer,'cart','/cart'],[customer,'login','/login'],[admin,'dashboard','/admin'],[admin,'admin-products','/admin/products']]){
    await page.bringToFront();
    await page.setViewport({width,height:1000});const response=await page.goto(base+path,{waitUntil:'networkidle0'});assert.equal(response.status(),200);
    await page.evaluate(async()=>{await document.fonts.ready;await Promise.race([Promise.all([...document.images].map(image=>{image.loading='eager';return image.decode().catch(()=>{});})),new Promise(resolve=>setTimeout(resolve,3000))]);});
    await page.screenshot({path:join(output,`${name}-${width}.png`),fullPage:true});
    console.log(`${name}@${width} captured`);
    results.push({name,width,...await page.evaluate(analyze)});
    writeFileSync(join(output,'audit.json'),JSON.stringify({phase,results,javascript},null,2));
  }
  await customer.bringToFront();await customer.setViewport({width:375,height:1000});await customer.goto(base+'/products',{waitUntil:'load'});
  await customer.click('[data-filter-open]');
  results.push({name:'filter-dialog',width:375,...await customer.evaluate(analyze)});
  await customer.screenshot({path:join(output,'filter-dialog-375.png'),fullPage:true});
  await customer.keyboard.press('Escape');
  assert(await customer.$eval('[data-filter-open]',element=>element===document.activeElement),'Dialog returns focus');
  await customer.setViewport({width:1440,height:1000});
  await customer.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);
  await customer.goto(base+'/',{waitUntil:'networkidle0'});
  const railId=await customer.evaluate(()=>{
    const section=[...document.querySelectorAll('.products-section')].find(section=>{
      const button=section.querySelector('[data-rail-next]');return button&&!button.hidden&&!button.disabled;
    });return section?.querySelector('.product-rail,.brand-strip')?.id;
  });
  assert(railId,'Homepage must expose operable rail controls when products overflow');
  await customer.click(`[data-rail-next][aria-controls="${railId}"]`);
  await customer.waitForFunction(id=>document.getElementById(id).scrollLeft>10,{},railId);
  railSamples.push(await customer.$eval('#'+railId,rail=>({id:rail.id,direction:'next',scrollLeft:rail.scrollLeft})));
  await customer.click(`[data-rail-prev][aria-controls="${railId}"]`);
  await customer.waitForFunction(id=>document.getElementById(id).scrollLeft<=2,{},railId);
  railSamples.push(await customer.$eval('#'+railId,rail=>({id:rail.id,direction:'previous',scrollLeft:rail.scrollLeft})));
  await customer.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'no-preference'}]);
  for(const [page,path,name]of[[customer,'/','home'],[admin,'/admin','dashboard']]){
    await page.bringToFront();await page.goto(base+path,{waitUntil:'load'});
    for(let index=0;index<6;index++){
      await page.keyboard.press('Tab');
      const focus=await page.evaluate(()=>{
        const element=document.activeElement,box=element.getBoundingClientRect(),style=getComputedStyle(element);
        const x=Math.max(0,Math.min(innerWidth-1,box.left+box.width/2)),y=Math.max(0,Math.min(innerHeight-1,box.top+box.height/2));
        const top=document.elementFromPoint(x,y);
        return {name:element.getAttribute('aria-label')||element.textContent.trim().slice(0,60)||element.id,visible:box.width>0&&box.height>0&&box.bottom>0&&box.top<innerHeight&&!!top&&(top===element||element.contains(top)),outline:parseFloat(style.outlineWidth),outlineColor:style.outlineColor};
      });
      focusSamples.push({page:name,...focus});
      assert(focus.visible,`${name} keyboard focus must stay visible: ${focus.name}`);
      assert(focus.outline>=2,`${name} keyboard focus requires visible outline: ${focus.name}`);
    }
  }
  for(const [page,path,name]of[[customer,'/products','catalog'],[admin,'/admin','dashboard']]){
    await page.bringToFront();
    await page.setViewport({width:1440,height:1000});await page.goto(base+path,{waitUntil:'load'});
    await page.evaluate(()=>document.documentElement.style.zoom='200%');
    const metrics=await page.evaluate(analyze);results.push({name:name+'-200-percent-css-zoom',width:1440,...metrics});
    await page.screenshot({path:join(output,`${name}-zoom200.png`),fullPage:true});
    await page.evaluate(()=>document.documentElement.style.zoom='');
  }
  writeFileSync(join(output,'audit.json'),JSON.stringify({phase,results,focusSamples,railSamples,javascript},null,2));
  const smallControls=[...new Map(results.flatMap(row=>row.smallControls.map(item=>[`${row.name}|${row.width}|${item.label}|${item.width}|${item.height}`,{page:row.name,viewport:row.width,...item}]))).values()];
  const overflow=results.filter(row=>row.overflow).map(row=>row.name+'@'+row.width);
  const contrastFailures=results.flatMap(row=>row.contrastFailures.map(item=>({page:row.name,viewport:row.width,...item})));
  const radiusFailures=results.flatMap(row=>row.radiusFailures.map(item=>({page:row.name,viewport:row.width,...item})));
  console.log(JSON.stringify({phase,output,pages:results.length,keyboard:focusSamples.length,rails:railSamples.length,overflow,contrastFailures,smallControls,radiusFailures,javascript},null,2));
  if(phase==='after'){
    assert.deepEqual(overflow,[],'Redesigned pages must not overflow horizontally');
    assert.deepEqual(contrastFailures,[],'Rendered text must meet the configured contrast threshold');
    assert.deepEqual(smallControls,[],'Visible controls must meet the project 44px target');
    assert.deepEqual(radiusFailures,[],'Rounded UI corners must use the requested 5px radius');
    assert.deepEqual(javascript,[],'No JavaScript errors');
    assert(results.every(result=>result.fontFaces.length>0),'Every audited page loads the local Be Vietnam Pro font');
    assert(results.every(result=>result.fontResources.length>0&&result.fontResources.every(path=>path.startsWith('/static/fonts/'))),'Fonts load from local assets');
  }
}finally{if(browser)await browser.close();server.kill();writeFileSync(join(output,'server.log'),logs);}
