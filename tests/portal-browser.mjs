import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const root=resolve('.');mkdirSync('test-results',{recursive:true});
const output=mkdtempSync(join(root,'test-results/portal-browser-'));
const database=join(output,'shop.db'),port=8023,base=`http://127.0.0.1:${port}`;
const backup=spawnSync('python',['-c',`import sqlite3,sys,json;a=sqlite3.connect(sys.argv[1]);b=sqlite3.connect(sys.argv[2]);a.backup(b);r=b.execute("SELECT p.id,v.id FROM products p JOIN variants v ON v.product_id=p.id WHERE p.active=1 AND v.active=1 AND v.stock>0 ORDER BY p.id LIMIT 1").fetchone();print(json.dumps({'product':r[0],'variant':r[1]}));b.close();a.close()`,join(root,'data/shop.db'),database],{encoding:'utf8',windowsHide:true});
assert.equal(backup.status,0,backup.stderr);const fixture=JSON.parse(backup.stdout);
const server=spawn('python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(port)],{cwd:root,env:{...process.env,NEU_DB_PATH:database,NEU_SESSION_SECRET:'portal-browser-test-only'},windowsHide:true,stdio:['ignore','pipe','pipe']});
let logs='',browser;server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
const errors=[],checks=[],report=[];
const record=name=>{checks.push(name);console.log('PASS '+name);};
const go=async(page,path)=>{await page.bringToFront();const response=await page.goto(base+path,{waitUntil:'networkidle0'});assert.equal(response.status(),200,path);};
async function post(page,path,values){
  const result=await page.evaluate(async({path,values})=>{const csrf=document.querySelector('[name=csrf]')?.value;const response=await fetch(path,{method:'POST',body:new URLSearchParams({csrf,...values})});return{status:response.status,url:response.url,text:await response.text()};},{path,values});
  assert.equal(result.status,200,path+': '+result.text.slice(0,100));await go(page,new URL(result.url).pathname+new URL(result.url).search);return result;
}
async function submit(page,selector){await page.bringToFront();await Promise.all([page.waitForNavigation({waitUntil:'networkidle0'}),page.$eval(selector,form=>form.requestSubmit())]);}
try{
  for(let i=0;i<100;i++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(resolve=>setTimeout(resolve,100));if(i===99)throw new Error(logs);}
  browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const guest=await(await browser.createBrowserContext()).newPage(),admin=await(await browser.createBrowserContext()).newPage(),customer=await(await browser.createBrowserContext()).newPage();
  for(const page of[guest,admin,customer])page.on('pageerror',error=>errors.push(error.message));
  await go(guest,'/contact');await guest.type('#name','Khách kiểm thử giao diện');await guest.type('#email','portal-ui@example.test');await guest.type('#content','Tôi cần hỗ trợ chọn thiết bị phục vụ học tập.');
  await submit(guest,'form[action="/contact"]');const receipt=new URL(guest.url()).pathname;assert(receipt.startsWith('/contact/requests/'));record('public contact receipt');
  await go(admin,'/admin/login');await post(admin,'/login',{email:'admin@neushop.local',password:'Admin@12345',portal:'admin'});
  const messageId=await guest.$eval('h1',element=>element.textContent.match(/#(\d+)/)[1]);
  await post(admin,`/admin/contact/${messageId}`,{status:'replied',response:'Bạn có thể xem danh mục laptop và so sánh cấu hình trước khi chọn.'});
  await go(guest,receipt);assert((await guest.content()).includes('so sánh cấu hình'));record('admin reply appears on private receipt');
  await go(admin,'/admin/settings');await post(admin,'/admin/settings',{shop_name:'NEU SHOP',tagline:'Công nghệ cho mỗi ngày',hotline:'0912345678',email:'demo@example.test',address:'Địa chỉ minh họa kiểm thử',map_query:'Hà Nội',facebook:'https://www.facebook.com/example',show_statistics:'1'});
  await go(guest,'/contact');assert(await guest.$('[data-map-load]'));assert((await guest.content()).includes('tel:0912345678'));record('configured contact details and map control');
  await go(admin,'/admin/content');const editor=await admin.$('textarea[name=content]');await editor.click();await editor.type('## Hướng dẫn kiểm thử\nNội dung **định dạng** an toàn trong bài viết.');
  await admin.click('[data-editor-preview]');await admin.waitForFunction(()=>document.querySelector('[data-editor-output]').textContent.includes('định dạng'));
  assert(await admin.$('[data-editor-output] strong'));record('formatted article preview');
  await admin.type('#new-title','Cẩm nang thiết bị cho học tập');await admin.type('#new-summary','Hướng dẫn đọc thông số và chọn thiết bị phù hợp với nhu cầu.');
  const image=readdirSync(join(root,'app/static/images/catalog')).find(name=>name.endsWith('.png')&&statSync(join(root,'app/static/images/catalog',name)).size<1900000);
  assert(image);await(await admin.$('#new-image')).uploadFile(join(root,'app/static/images/catalog',image));
  await submit(admin,'form[action="/admin/content"]');
  await go(guest,'/news');await guest.type('#news-q','Cẩm nang thiết bị');await guest.waitForFunction(()=>location.search.includes('q=')&&document.querySelectorAll('.news-card').length===1);record('live topic/news search');
  const articlePath=await guest.$eval('.news-card h2 a',a=>new URL(a.href).pathname);await go(guest,articlePath);assert(await guest.$('.page-cover'));assert(await guest.$('.rich-content strong'));assert.equal((await guest.$$('.share-tools,[data-share-url],[data-copy-url]')).length,0);record('article image formatting without share controls');
  await go(customer,'/login');await post(customer,'/login',{email:'demo.lan@example.test',password:'Demo@12345'});
  await go(customer,`/products/${fixture.product}`);await post(customer,'/cart/add',{variant_id:fixture.variant,quantity:1});await go(customer,'/checkout');
  const key=await customer.$eval('[name=checkout_key]',element=>element.value);
  await post(customer,'/checkout',{checkout_key:key,recipient:'Khách demo',phone:'0912345678',address:'12 Đường Kiểm Thử, Hà Nội',shipping_method:'standard',payment_method:'cod',action:'place'});
  const contractPath=new URL(customer.url()).pathname;assert(contractPath.startsWith('/contracts/'));
  const orderId=await customer.$eval('.contract-layout a[href*="/orders/"]',element=>element.getAttribute('href').split('/').pop());
  await go(admin,`/admin/orders/${orderId}`);assert(await admin.$('form[action$="/status"] button[disabled]'));
  await customer.setViewport({width:375,height:1000});await customer.screenshot({path:join(output,'contract-before-confirmation-375.png'),fullPage:true});record('checkout opens contract before admin approval');
  await post(customer,contractPath+'/otp',{});const code=await customer.$eval('#contract-demo-otp',element=>element.textContent.trim());
  await customer.type('#contract-code',code);await customer.click('[name=consent]');await submit(customer,`form[action="${contractPath}/sign"]`);
  assert((await customer.content()).includes('Đã xác nhận OTP'));assert.equal(await customer.$('#contract-demo-otp'),null);record('contract read consent OTP confirmation');
  const download=await customer.evaluate(async path=>{const response=await fetch(path+'/download');return{status:response.status,disposition:response.headers.get('content-disposition'),body:await response.text()};},contractPath);
  assert.equal(download.status,200);assert(download.disposition.includes('.html'));assert(download.body.includes('Mã đối chiếu SHA-256'));record('private contract export');
  await go(customer,contractPath+'/print');await customer.emulateMediaType('print');assert(await customer.$eval('.print-controls',element=>getComputedStyle(element).display==='none'));await customer.emulateMediaType(null);record('print/PDF layout');
  const paths=[[guest,'about','/about'],[guest,'services','/services'],[guest,'contact','/contact'],[guest,'receipt',receipt],[guest,'news','/news'],[guest,'article',articlePath],[customer,'contracts','/account/contracts'],[customer,'contract',contractPath],[admin,'settings','/admin/settings'],[admin,'inbox',`/admin/contact/${messageId}`],[admin,'analytics','/admin/analytics'],[admin,'contracts-admin','/admin/contracts'],[admin,'contract-admin','/admin'+contractPath],[admin,'catalog','/admin/catalog'],[admin,'content','/admin/content'],[admin,'archive','/admin/archive']];
  for(const width of[320,375,768,1440])for(const[page,name,path]of paths){
    await page.setViewport({width,height:1000});await go(page,path);await page.evaluate(()=>document.fonts.ready);
    const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,radii:[...document.querySelectorAll('*')].filter(element=>element instanceof HTMLElement&&element.getClientRects().length).flatMap(element=>{const style=getComputedStyle(element);return['borderTopLeftRadius','borderTopRightRadius','borderBottomLeftRadius','borderBottomRightRadius'].map(key=>style[key]);}).filter(value=>value!=='0px'&&value!=='5px')}));
    assert(!metrics.overflow,`${name}@${width} horizontal overflow`);assert.deepEqual(metrics.radii,[],`${name}@${width} radius`);
    report.push({name,width,...metrics});
    if([375,1440].includes(width)&&['contact','article','contract','inbox','settings'].includes(name))await page.screenshot({path:join(output,`${name}-${width}.png`),fullPage:true});
  }
  record(`${report.length} new page/viewport layouts`);
  await go(admin,'/admin'+contractPath);await post(admin,'/admin'+contractPath+'/void',{reason:'Hủy hiệu lực theo yêu cầu kiểm thử.'});await go(customer,contractPath);assert((await customer.content()).includes('Đã hủy hiệu lực'));record('admin void retains contract history');
  assert.deepEqual(errors,[],'No JavaScript errors');
  writeFileSync(join(output,'report.json'),JSON.stringify({checks,views:report,javascript:errors},null,2));console.log(JSON.stringify({checks:checks.length,views:report.length,output}));
}finally{if(browser)await browser.close();server.kill();writeFileSync(join(output,'server.log'),logs);}
