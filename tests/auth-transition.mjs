import puppeteer from 'puppeteer-core';
import assert from 'node:assert/strict';
const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [375,768,1280]){
  await page.setViewport({width,height:800});await page.goto('http://127.0.0.1:8000/login',{waitUntil:'networkidle0'});await page.waitForSelector('.auth-login');
  await page.evaluate(()=>{window.savedAuth=document.querySelector('.auth-layout');window.savedImage=document.querySelector('.auth-campus img');window.savedHeader=document.querySelector('.site-header');document.querySelector('#email').value='retained@example.com';scrollTo(0,120);});
  const before=await page.evaluate(()=>({scroll:scrollY,height:document.querySelector('.auth-layout').getBoundingClientRect().height}));let documents=0;page.on('request',r=>{if(r.isNavigationRequest()&&r.frame()===page.mainFrame())documents++;});
  for(const mode of ['register','login']){
   await page.evaluate(mode=>document.querySelector(`.auth-switch a[href="/${mode}"]`).click(),mode);await page.waitForSelector('.auth-'+mode);await page.waitForFunction(()=>!document.querySelector('.auth-intro').getAnimations().length);
   const result=await page.evaluate(()=>({same:window.savedAuth===document.querySelector('.auth-layout')&&window.savedImage===document.querySelector('.auth-campus img')&&window.savedHeader===document.querySelector('.site-header'),scroll:scrollY,height:document.querySelector('.auth-layout').getBoundingClientRect().height,email:document.querySelector('#email').value}));
   assert(result.same);assert.equal(result.email,'retained@example.com');assert(Math.abs(result.scroll-before.scroll)<2);if(width>=768)assert(Math.abs(result.height-before.height)<2,`${width}: ${result.height} vs ${before.height}`);
  }
  assert.equal(documents,0);
 }
 assert.deepEqual(errors,[]);console.log('Login/register: persistent image, shell and header, preserved email/scroll, stable desktop height, no document reload at 375/768/1280px.');
}finally{await browser.close();}
