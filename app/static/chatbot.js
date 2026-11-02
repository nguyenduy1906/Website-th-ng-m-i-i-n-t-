const chatDialog = document.getElementById('shop-chatbot');
const chatLaunch = document.querySelector('.chatbot-launch');
let chatDrag, chatSuppressClick = false;
function placeChat(left, top) {
 const size=chatLaunch.getBoundingClientRect();
 chatLaunch.style.left=Math.max(0,Math.min(innerWidth-size.width,left))+'px';
 chatLaunch.style.top=Math.max(0,Math.min(innerHeight-size.height,top))+'px';
 chatLaunch.style.right='auto';chatLaunch.style.bottom='auto';
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
function renderReply(result){const item=bubble('assistant',result.answer);for(const product of result.products||[]){const link=document.createElement('a');link.href=product.url;link.textContent=product.name+' — '+new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(product.price);item.append(link);const specs=document.createElement('p');specs.textContent=product.specs||product.summary||'';item.append(specs);}if(result.url){const a=document.createElement('a');a.href=result.url;a.textContent='Xem chi tiết';item.append(a);}}
for(const message of chatHistory.slice(-40)){if(message.role==='user')bubble('user',message.text);else if(message.result)renderReply(message.result);}
function scrollChat(){const body=chatDialog.querySelector('.chatbot-body');body.scrollTop=body.scrollHeight;}
function closeChat(){chatDialog.hidden=true;chatLaunch.setAttribute('aria-expanded','false');chatLaunch.focus();}
chatLaunch.addEventListener('click',event=>{if(chatSuppressClick&&event.detail){chatSuppressClick=false;return;}chatDialog.hidden=!chatDialog.hidden;chatLaunch.setAttribute('aria-expanded',String(!chatDialog.hidden));if(!chatDialog.hidden){chatInput.focus();scrollChat();}});
chatDialog.querySelector('[data-chatbot-close]').onclick=closeChat;
chatDialog.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();closeChat();}});
chatDialog.querySelector('[data-chatbot-clear]').onclick=()=>{chatGeneration++;chatRequest?.abort();chatHistory=[];saveChat();chatMessages.replaceChildren();chatWelcome.hidden=false;chatForm.querySelector('button').disabled=false;chatInput.value='';chatInput.focus();};
chatDialog.querySelector('[data-chatbot-suggestion]').onclick=()=>{chatInput.value='Laptop dưới 20 triệu';chatForm.requestSubmit();};
chatInput.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();chatForm.requestSubmit();}});
chatForm.addEventListener('submit',async event=>{
 event.preventDefault();const button=chatForm.querySelector('button');const q=chatInput.value.trim();if(!q||button.disabled)return;
 const generation=++chatGeneration;chatRequest=new AbortController();bubble('user',q);chatHistory.push({role:'user',text:q});saveChat();chatInput.value='';button.disabled=true;
 const pending=bubble('assistant','Đang tra cứu dữ liệu cửa hàng…');scrollChat();
 try{const response=await fetch('/api/chatbot',{method:'POST',body:new URLSearchParams({q,csrf:document.querySelector('[name=csrf]').value,history:JSON.stringify(chatHistory.slice(0,-1).slice(-8).map(m=>({role:m.role,text:(m.text||m.result?.answer||'').slice(0,2000)})))}),signal:chatRequest.signal});if(!response.ok)throw new Error();const result=await response.json();if(generation!==chatGeneration)return;pending.remove();renderReply(result);chatDialog.querySelector('[data-ai-status]').textContent=result.provider==='ollama'?'AI local · Ollama':result.provider==='gemini'?'AI · Gemini':'Tra cứu local · AI chưa sẵn sàng';chatHistory.push({role:'assistant',result});saveChat();}
 catch(error){if(error.name!=='AbortError')pending.querySelector('p').textContent='Chưa thể kết nối. Bạn gửi lại câu hỏi sau nhé.';}
 finally{if(generation===chatGeneration){button.disabled=false;if(!chatDialog.hidden)chatInput.focus();scrollChat();}}
});
