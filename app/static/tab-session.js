(() => {
 const nativeFetch=window.__neuNativeFetch||(window.__neuNativeFetch=window.fetch.bind(window));
 const key='neu-tab-session';
 const stored=()=>{try{return sessionStorage.getItem(key)||'';}catch{return '';}};
 const save=value=>{try{if(value==='null')sessionStorage.removeItem(key);else sessionStorage.setItem(key,value);}catch{}};
 async function tabFetch(input,options={}) {
  let request=new Request(input instanceof Request?input:new URL(input,location.href),options);
  if(new URL(request.url).origin!==location.origin)return nativeFetch(request);
  for(let i=0;i<10;i++){
   const before=stored();const headers=new Headers(request.headers);headers.set('X-NEU-Tab','1');headers.set('X-NEU-Tab-Session',before);
   const response=await nativeFetch(new Request(request,{headers}));
   const session=response.headers.get('X-NEU-Tab-Session');if(session!==null&&stored()===before)save(session);
   const redirect=response.headers.get('X-NEU-Redirect');if(!redirect)return response;
   const next=new URL(redirect,request.url);if(next.origin!==location.origin)throw new Error('Unexpected redirect');
   const status=response.headers.get('X-NEU-Redirect-Status');
   if(status==='307'||status==='308')throw new Error('Unsupported method redirect');
   request=new Request(next,{method:'GET',credentials:'same-origin'});
  }
  throw new Error('Too many redirects');
 }
 window.fetch=tabFetch;
 const intervals=window.__neuPageIntervals||(window.__neuPageIntervals=new Set());
 const timeouts=window.__neuPageTimeouts||(window.__neuPageTimeouts=new Set());
 if(!window.__neuNativeTimeout){window.__neuNativeTimeout=window.setTimeout.bind(window);window.setTimeout=(callback,delay,...args)=>{const id=window.__neuNativeTimeout(()=>{timeouts.delete(id);callback(...args);},delay);timeouts.add(id);return id;};}
 if(!window.__neuNativeInterval){window.__neuNativeInterval=window.setInterval.bind(window);window.setInterval=(callback,delay,...args)=>{const id=window.__neuNativeInterval(callback,delay,...args);intervals.add(id);return id;};}
 function showPage(html,url,push=false){
  window.__neuPageController?.abort();
  for(const id of intervals)clearInterval(id);intervals.clear();
  for(const id of timeouts)clearTimeout(id);timeouts.clear();
  channelOwner?.close();
  if(push&&url!==location.href)history.pushState(null,'',url);else history.replaceState(null,'',url);
  window.__neuTabHydrated=true;document.open();document.write(html);document.close();
 }
 let channelOwner;
 function beginPageListeners(){
  window.__neuPageController=new AbortController();
  if(window.__neuNativeListener)return;
  window.__neuNativeListener=EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener=function(type,listener,options){
   const script=document.currentScript?.getAttribute('src')||'';
   const persistent=script.endsWith('/chatbot.js')||script.endsWith('/tab-session.js');
   const controller=window.__neuPageController;
   if(controller&&!persistent){
    options=typeof options==='boolean'?{capture:options}:{...(options||{})};
    if(!options.signal)options.signal=controller.signal;
   }
   return window.__neuNativeListener.call(this,type,listener,options);
  };
 }
 async function refreshPageScripts(){
  window.__neuPageController?.abort();
  for(const id of intervals)clearInterval(id);intervals.clear();
  for(const id of timeouts)clearTimeout(id);timeouts.clear();
  document.querySelectorAll('dialog[data-enhanced]').forEach(n=>delete n.dataset.enhanced);
  document.querySelectorAll('[data-neu-page-script],[data-neu-live-announcement]').forEach(n=>n.remove());
  beginPageListeners();
  for(const path of ['/static/portal.js','/static/app.js','/static/ui.js']){
   await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=path;script.dataset.neuPageScript='true';script.onload=resolve;script.onerror=reject;document.head.append(script);});
  }
 }
 async function navigate(url,push=true){
  const generation=(window.__neuNavigationGeneration||0)+1;window.__neuNavigationGeneration=generation;
  const previousScroll=push?0:(history.state?.scroll||0);
  const response=await tabFetch(url);
  if(generation!==window.__neuNavigationGeneration)return;
  if(!response.headers.get('content-type')?.includes('text/html')){location.assign(url);return;}
  const html=await response.text();if(generation!==window.__neuNavigationGeneration)return;
  await renderContent(html,response.url,push,previousScroll);
 }
 async function renderContent(html,url,push=true,previousScroll=0){
  const generation=window.__neuNavigationGeneration;
  const parsed=new DOMParser().parseFromString(html,'text/html');
  const currentMain=document.querySelector('main[data-live-results]'),nextMain=parsed.querySelector('main[data-live-results]');
  const sameShell=['customer-shell','admin-shell'].some(name=>document.body.classList.contains(name)&&parsed.body.classList.contains(name));
  if(!sameShell||!currentMain||!nextMain){showPage(html,url,push);scrollTo(0,previousScroll);return;}
  if(window.__neuPageRefreshPromise)await window.__neuPageRefreshPromise;
  if(generation!==window.__neuNavigationGeneration)return;
  const rail=document.querySelector('.admin-rail'),railScroll=rail?.scrollTop;
  const oldAccount=document.querySelector('.account-menu'),newAccount=nextMain.querySelector('.account-menu');
  if(oldAccount&&newAccount){
   const active=new Set([...newAccount.querySelectorAll('a[aria-current]')].map(n=>n.getAttribute('href')));
   for(const link of oldAccount.querySelectorAll('a')){if(active.has(link.getAttribute('href')))link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
   newAccount.replaceWith(oldAccount);
  }
  const oldAuth=currentMain.querySelector('[data-auth-mode]'),nextAuth=nextMain.querySelector('[data-auth-mode]');
  const switchAuth=oldAuth&&nextAuth&&['login','register'].includes(oldAuth.dataset.authMode)&&['login','register'].includes(nextAuth.dataset.authMode)&&oldAuth.dataset.authMode!==nextAuth.dataset.authMode;
  const authPositions=switchAuth?[...oldAuth.children].map(el=>({selector:el.classList.contains('auth-intro')?'.auth-intro':'.auth-form',left:el.getBoundingClientRect().left})):[];
  const authScroll=switchAuth?{x:scrollX,y:scrollY}:null;
  if(switchAuth){
   const email=oldAuth.querySelector('input[name=email]')?.value;
   const nextForm=nextAuth.querySelector('.auth-form');
   if(email&&nextForm.querySelector('input[name=email]'))nextForm.querySelector('input[name=email]').value=email;
   oldAuth.className=nextAuth.className;
   oldAuth.dataset.authMode=nextAuth.dataset.authMode;
   oldAuth.querySelector('.auth-form').replaceWith(nextForm);
  }else currentMain.replaceChildren(...nextMain.childNodes);
  if(switchAuth&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
   for(const panel of authPositions){
    const el=currentMain.querySelector(panel.selector);
    if(!el)continue;
    const delta=innerWidth>=768?panel.left-el.getBoundingClientRect().left:0;
    el.animate([{transform:`translateX(${delta}px)`,opacity:panel.selector==='.auth-form'?.4:1},{transform:'translateX(0)',opacity:1}],{duration:420,easing:'cubic-bezier(.22,.61,.36,1)'});
   }
  }
  const actions=document.querySelector('.site-header .header-actions'),nextActions=parsed.querySelector('.site-header .header-actions');
  if(actions&&nextActions){
   const identity=actions.querySelector('.account-dropdown summary')?.textContent||'';
   const nextIdentity=nextActions.querySelector('.account-dropdown summary')?.textContent||'';
   if(identity!==nextIdentity)actions.replaceChildren(...nextActions.childNodes);
  }
  const csrf=parsed.querySelector('[name=csrf]')?.value;
  const adminPerson=document.querySelector('a.admin-person'),nextAdminPerson=parsed.querySelector('a.admin-person');
  if(adminPerson&&nextAdminPerson){
   adminPerson.setAttribute('aria-label',nextAdminPerson.getAttribute('aria-label'));
   const name=adminPerson.querySelector('.admin-user-name'),nextName=nextAdminPerson.querySelector('.admin-user-name');
   if(name&&nextName)name.replaceChildren(...nextName.childNodes);
  }
  if(csrf)document.querySelectorAll('input[name=csrf]').forEach(input=>input.value=csrf);
  const nextCount=parsed.querySelector('[data-cart-count]');
  if(nextCount)document.querySelectorAll('[data-cart-count]').forEach(n=>{n.textContent=nextCount.textContent;n.setAttribute('aria-label',nextCount.getAttribute('aria-label'));});
  document.title=parsed.title;
  if(push&&url!==location.href)history.pushState(null,'',url);else history.replaceState(null,'',url);
  document.querySelectorAll('.admin-rail nav a,.nav-row a').forEach(link=>{
   const source=[...parsed.querySelectorAll('.admin-rail nav a,.nav-row a')].find(n=>n.getAttribute('href')===link.getAttribute('href'));
   if(source?.hasAttribute('aria-current'))link.setAttribute('aria-current',source.getAttribute('aria-current'));else link.removeAttribute('aria-current');
   link.querySelector('.admin-nav-dot')?.remove();
   const dot=source?.querySelector('.admin-nav-dot');if(dot)link.append(dot.cloneNode(true));
  });
  for(const input of document.querySelectorAll('.site-header input[name=q],.admin-topbar input[name=q]')){
   const next=parsed.getElementById(input.id);if(next)input.value=next.value;
  }
  if(!switchAuth)await (window.__neuPageRefreshPromise=refreshPageScripts());
  if(rail)rail.scrollTop=railScroll;
  if(authScroll)scrollTo(authScroll.x,authScroll.y);else scrollTo(0,previousScroll);
  document.dispatchEvent(new Event('neu:content-updated'));
 }

 if(!window.__neuTabHydrated){
  document.documentElement.hidden=true;
  window.__neuTabHydrated=true;
  const channel=typeof BroadcastChannel==='function'?new BroadcastChannel('neu-tab-ownership'):null;
  const id=crypto.randomUUID();let duplicate=false;
  if(channel){channel.onmessage=event=>{if(event.data.type==='owned'&&event.data.to===id)duplicate=true;};channel.postMessage({type:'check',id,token:stored()});}
  setTimeout(async()=>{if(duplicate){try{sessionStorage.removeItem(key);sessionStorage.removeItem('neu-chat-history');sessionStorage.removeItem('neu-tab-page');}catch{}}channel?.close();try{const cached=JSON.parse(sessionStorage.getItem('neu-tab-page')||'null');sessionStorage.removeItem('neu-tab-page');if(cached&&cached.url===location.href){showPage(cached.html,cached.url);}else{const response=await tabFetch(location.href);showPage(await response.text(),response.url);}}catch{document.body.textContent='Chưa thể tải trang. Vui lòng tải lại.';}},100);
  return;
 }
 document.documentElement.hidden=false;document.documentElement.dataset.tabReady='true';
 const channel=typeof BroadcastChannel==='function'?new BroadcastChannel('neu-tab-ownership'):null;channelOwner=channel;
 if(channel)channel.onmessage=event=>{if(event.data.type==='check'&&event.data.token&&event.data.token===stored())channel.postMessage({type:'owned',to:event.data.id});};
 window.__neuPageController=undefined;
 document.addEventListener('click',async event=>{
  const link=event.target.closest('a[href]');
  if(event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||!link||link.target==='_blank'||link.hasAttribute('download'))return;
  const url=new URL(link.href,location.href);
  if(url.origin!==location.origin||!['http:','https:'].includes(url.protocol))return;
  if(url.pathname===location.pathname&&url.search===location.search&&url.hash)return;
  event.preventDefault();history.replaceState({...history.state,scroll:scrollY},'',location.href);
  try{await navigate(url.href);}catch{location.assign(url.href);}
 });
 window.addEventListener('popstate',()=>{navigate(location.href,false).catch(()=>location.reload());});
 document.addEventListener('submit',async event=>{
  const form=event.target;
  if(event.defaultPrevented||!(form instanceof HTMLFormElement)||form.matches('[data-live-form],[data-quick-cart],[data-chatbot-form]'))return;
  const method=(event.submitter?.getAttribute('formmethod')||form.getAttribute('method')||'get').toLowerCase();
  const target=event.submitter?.getAttribute('formtarget')||form.getAttribute('target');
  if(method!=='post'||target==='_blank')return;
  const url=new URL(event.submitter?.getAttribute('formaction')||form.getAttribute('action')||location.href,location.href);if(url.origin!==location.origin)return;
  event.preventDefault();
  const enctype=event.submitter?.getAttribute('formenctype')||form.getAttribute('enctype');
  const data=new FormData(form,event.submitter),body=enctype==='multipart/form-data'?data:new URLSearchParams(data);
  try{const response=await tabFetch(url,{method:'POST',body});if(response.headers.get('content-type')?.includes('text/html')){const html=await response.text();await renderContent(html,response.url,true,0);}else location.reload();}
  catch{alert('Chưa thể gửi biểu mẫu. Vui lòng thử lại.');event.submitter?.removeAttribute('disabled');}
 });
 beginPageListeners();
})();
