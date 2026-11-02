(() => {
const chatDialog = document.getElementById('shop-chatbot');
const chatLaunch = document.querySelector('.chatbot-launch');
let chatDrag, chatSuppressClick = false;
function positionChatPanel() {
 if(chatDialog.hidden)return;
 const logo=chatLaunch.getBoundingClientRect(), panel=chatDialog.getBoundingClientRect();
 const viewport=window.visualViewport;
 const leftEdge=viewport?.offsetLeft||0, topEdge=viewport?.offsetTop||0;
 const width=viewport?.width||innerWidth, height=viewport?.height||innerHeight;
 const margin=8,gap=12;
 const rightSide=logo.right+gap, leftSide=logo.left-gap-panel.width;
 let left=logo.left+logo.width/2<leftEdge+width/2?rightSide:leftSide;
 let top=logo.bottom-panel.height;
 if(left<leftEdge+margin||left+panel.width>leftEdge+width-margin){
  left=logo.left;
  top=logo.top-panel.height-gap;
  if(top<topEdge+margin)top=logo.bottom+gap;
 }
 chatDialog.style.left=Math.max(leftEdge+margin,Math.min(leftEdge+width-panel.width-margin,left))+'px';
 chatDialog.style.top=Math.max(topEdge+margin,Math.min(topEdge+height-panel.height-margin,top))+'px';
 chatDialog.style.right='auto';chatDialog.style.bottom='auto';
}
window.visualViewport?.addEventListener('resize',positionChatPanel);
window.visualViewport?.addEventListener('scroll',positionChatPanel);
function placeChat(left, top) {
 const size=chatLaunch.getBoundingClientRect();
 chatLaunch.style.left=Math.max(0,Math.min(innerWidth-size.width,left))+'px';
 chatLaunch.style.top=Math.max(0,Math.min(innerHeight-size.height,top))+'px';
 chatLaunch.style.right='auto';chatLaunch.style.bottom='auto';
 positionChatPanel();
}
chatLaunch.addEventListener('pointerdown', event => {
 if(event.button!==0)return;
 const box=chatLaunch.getBoundingClientRect();
 chatDrag={id:event.pointerId,x:event.clientX,y:event.clientY,left:box.left,top:box.top,moved:false};
 chatSuppressClick=false;chatLaunch.setPointerCapture(event.pointerId);
});
chatLaunch.addEventListener('pointermove', event => {
 if(!chatDrag||event.pointerId!==chatDrag.id)return;
 const dx=event.clientX-chatDrag.x,dy=event.clientY-chatDrag.y;
 if(Math.hypot(dx,dy)>6)chatDrag.moved=true;
 if(chatDrag.moved){chatLaunch.classList.add('is-dragging');placeChat(chatDrag.left+dx,chatDrag.top+dy);}
});
function endChatDrag(){if(!chatDrag)return;chatSuppressClick=chatDrag.moved;chatDrag=null;chatLaunch.classList.remove('is-dragging');}
chatLaunch.addEventListener('pointerup',endChatDrag);
chatLaunch.addEventListener('pointercancel',endChatDrag);
chatLaunch.addEventListener('lostpointercapture',endChatDrag);
window.addEventListener('resize',()=>{const box=chatLaunch.getBoundingClientRect();placeChat(box.left,box.top);});
chatLaunch.addEventListener('keydown',event=>{
 const moves={ArrowLeft:[-16,0],ArrowRight:[16,0],ArrowUp:[0,-16],ArrowDown:[0,16]};
 if(!moves[event.key])return;event.preventDefault();const box=chatLaunch.getBoundingClientRect();placeChat(box.left+moves[event.key][0],box.top+moves[event.key][1]);
});
const chatMessages=chatDialog.querySelector('[data-chatbot-messages]');
const chatInput=document.getElementById('chatbot-question');
const chatForm=chatDialog.querySelector('form');
const chatWelcome=chatDialog.querySelector('[data-chatbot-welcome]');
let chatHistory=[],chatRequest,chatGeneration=0;
try{chatHistory=JSON.parse(sessionStorage.getItem('neu-chat-history')||'[]');if(!Array.isArray(chatHistory))chatHistory=[];}catch{}
function saveChat(){try{sessionStorage.setItem('neu-chat-history',JSON.stringify(chatHistory.slice(-40)));}catch{}}
function bubble(role,value){const item=document.createElement('article');item.className='chat-message '+role;const label=document.createElement('strong');label.textContent=role==='user'?'Bạn':'NEU SHOP';const text=document.createElement('p');text.textContent=value;item.append(label,text);chatMessages.append(item);chatWelcome.hidden=true;return item;}
function renderReply(result, blank=false){
 const item=bubble('assistant',blank?'':result.answer);
 for(const product of result.products||[]){
  const card=document.createElement('section');card.className='chat-product';
  const photoLink=document.createElement('a');photoLink.href=product.url;photoLink.className='chat-product-photo';photoLink.setAttribute('aria-label','Xem '+product.name);
  const image=document.createElement('img');image.src=product.image||'/static/images/fallback.svg';image.alt=product.name;image.width=160;image.height=140;image.loading='lazy';
  image.addEventListener('error',()=>{if(!image.src.endsWith('/static/images/fallback.svg'))image.src='/static/images/fallback.svg';});photoLink.append(image);
  const name=document.createElement('a');name.href=product.url;name.className='chat-product-name';name.textContent=product.name;
  const price=document.createElement('p');price.className='chat-product-price';price.textContent=new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(product.price);
  const variant=document.createElement('p');variant.textContent=product.variant||'';
  const stock=document.createElement('p');stock.textContent=product.stock>0?'Còn '+product.stock+' sản phẩm ở phiên bản này':'Phiên bản này tạm hết hàng';
  const specs=document.createElement('p');specs.className='chat-product-specs';specs.textContent=product.specs||product.summary||'Chưa có thông số';
  const detail=document.createElement('a');detail.href=product.url;detail.className='button secondary chat-product-detail';detail.textContent='Xem chi tiết';
  card.append(photoLink,name,price,variant,stock,specs,detail);item.append(card);
 }
 if(result.url){const a=document.createElement('a');a.href=result.url;a.textContent=result.link_label||'Xem chi tiết';item.append(a);}return item;
}
async function typeReply(result,generation){
 const item=renderReply(result,true),text=item.querySelector('p');
 const characters=Array.from(result.answer||'');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 Array.from(item.children).slice(2).forEach(n=>n.hidden=true);
 for(let i=0;i<characters.length;i+=reduced?characters.length||1:4){
  if(generation!==chatGeneration)return;
  text.textContent=characters.slice(0,i+(reduced?characters.length:4)).join('');scrollChat();
  if(!reduced)await new Promise(resolve=>(window.__neuNativeTimeout||setTimeout)(resolve,12));
 }
 item.querySelectorAll('[hidden]').forEach(n=>n.hidden=false);scrollChat();
}
for(const message of chatHistory.slice(-40)){if(message.role==='user')bubble('user',message.text);else if(message.result)renderReply(message.result);}
function scrollChat(){const body=chatDialog.querySelector('.chatbot-body');body.scrollTop=body.scrollHeight;}
function closeChat(){chatDialog.hidden=true;chatLaunch.setAttribute('aria-expanded','false');chatLaunch.focus();}
chatLaunch.addEventListener('click',event=>{if(chatSuppressClick&&event.detail){chatSuppressClick=false;return;}chatDialog.hidden=!chatDialog.hidden;chatLaunch.setAttribute('aria-expanded',String(!chatDialog.hidden));if(!chatDialog.hidden){positionChatPanel();chatInput.focus();scrollChat();}});
chatDialog.querySelector('[data-chatbot-close]').onclick=closeChat;
chatDialog.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();closeChat();}});
chatDialog.querySelector('[data-chatbot-clear]').onclick=()=>{chatGeneration++;chatRequest?.abort();chatHistory=[];saveChat();chatMessages.replaceChildren();chatWelcome.hidden=false;chatForm.querySelector('button').disabled=false;chatInput.value='';chatInput.focus();scrollChat();};
chatInput.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();chatForm.requestSubmit();}});
chatForm.addEventListener('submit',async event=>{
 event.preventDefault();const button=chatForm.querySelector('button');const q=chatInput.value.trim();if(!q||button.disabled)return;
 const generation=++chatGeneration;chatRequest=new AbortController();bubble('user',q);chatHistory.push({role:'user',text:q});saveChat();chatInput.value='';button.disabled=true;
 const pending=bubble('assistant','Đang suy nghĩ');pending.classList.add('chat-thinking');pending.setAttribute('role','status');pending.setAttribute('aria-label','Đang suy nghĩ');scrollChat();
 try{const response=await fetch('/api/chatbot',{method:'POST',body:new URLSearchParams({q,csrf:document.querySelector('[name=csrf]').value,history:JSON.stringify(chatHistory.slice(0,-1).slice(-8).map(m=>({role:m.role,text:(m.text||m.result?.answer||'').slice(0,2000)})))}),signal:chatRequest.signal});if(!response.ok)throw new Error();const result=await response.json();if(generation!==chatGeneration)return;pending.remove();await typeReply(result,generation);if(generation!==chatGeneration)return;chatHistory.push({role:'assistant',result});saveChat();}
 catch(error){if(error.name!=='AbortError')pending.querySelector('p').textContent='Chưa thể kết nối. Bạn gửi lại câu hỏi sau nhé.';}
 finally{if(generation===chatGeneration){button.disabled=false;if(!chatDialog.hidden)chatInput.focus();scrollChat();}}
});

})();
