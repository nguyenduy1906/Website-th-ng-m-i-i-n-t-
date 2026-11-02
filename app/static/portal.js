(() => {
  document.querySelectorAll('.editor-toolbar,[data-map-load],[data-copy-url],[data-share-url],[data-contract-print]').forEach(element=>{element.hidden=false;});
  const status = (target,message) => { const region=target.closest('.share-tools,.portal-actions')?.querySelector('[role=status]');if(region)region.textContent=message; };
  async function copy(value) {
    if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(value);return;}
    const input=document.createElement('textarea');input.value=value;document.body.append(input);input.select();
    const success=document.execCommand('copy');input.remove();if(!success)throw new Error('Trình duyệt không hỗ trợ sao chép tự động.');
  }
  document.addEventListener('click',async event=>{
    const share=event.target.closest('[data-share-url],[data-copy-url]');
    if(share){try{const url=share.dataset.shareUrl||location.href;if(share.dataset.shareUrl&&navigator.share){await navigator.share({title:share.dataset.shareTitle,url});status(share,'Đã mở bảng chia sẻ.');}else{await copy(url);status(share,'Đã sao chép liên kết.');if(share.matches('[data-copy-url]'))share.textContent='Đã sao chép đường dẫn';}}catch(error){if(error.name!=='AbortError')status(share,error.message);}return;}
    const map=event.target.closest('[data-map-load]');
    if(map){const frame=document.createElement('iframe');frame.src=map.dataset.mapSrc;frame.title='Vị trí cửa hàng trên Google Maps';frame.className='store-map';frame.loading='lazy';frame.referrerPolicy='no-referrer';map.closest('section').querySelector('[data-map-target]').replaceChildren(frame);map.disabled=true;map.textContent='Đã hiển thị bản đồ';return;}
    if(event.target.closest('[data-contract-print]')){window.print();return;}
    const action=event.target.closest('[data-editor-insert],[data-editor-preview]');
    if(!action)return;
    const editor=action.closest('[data-text-editor]'),input=editor?.querySelector('textarea');if(!input)return;
    if(action.hasAttribute('data-editor-insert')){const before=input.value.slice(0,input.selectionStart),after=input.value.slice(input.selectionEnd);input.value=before+(before&&!before.endsWith('\n')?'\n':'')+action.dataset.editorInsert+'\n'+after;input.focus();input.dispatchEvent(new Event('input',{bubbles:true}));return;}
    const output=editor.querySelector('[data-editor-output]');action.disabled=true;
    try{const csrf=input.closest('form').querySelector('[name=csrf]').value;const response=await fetch('/admin/content/preview',{method:'POST',body:new URLSearchParams({csrf,content:input.value})});if(!response.ok)throw new Error('Không thể xem trước nội dung.');const data=await response.json();output.innerHTML=data.html;output.hidden=false;}catch(error){output.textContent=error.message;output.hidden=false;}finally{action.disabled=false;}
  });
  const parent=document.querySelector('#category'),child=document.querySelector('#subcategory');
  const sync=()=>{if(!parent||!child)return;for(const option of child.options){const valid=!option.value||option.dataset.parent===parent.value;option.hidden=!valid;option.disabled=!valid;if(option.selected&&!valid)child.value='';}};
  parent?.addEventListener('change',sync);sync();
  if(document.querySelector('.site-footer'))setInterval(async()=>{if(document.hidden)return;const csrf=document.querySelector('[name=csrf]')?.value;if(!csrf)return;try{await fetch('/api/visits/heartbeat',{method:'POST',body:new URLSearchParams({csrf}),keepalive:true});}catch{}},60000);
  if(document.querySelector('[data-stat-views]')){
    const stats=async()=>{if(document.hidden)return;try{const response=await fetch('/api/visits/stats');if(!response.ok)return;const values=await response.json();for(const [key,label]of[['views','Lượt xem'],['visitors','Phiên khách'],['online','Đang truy cập']]){const item=document.querySelector('[data-stat-'+key+']');if(item)item.textContent=label+': '+values[key];}}catch{}};
    stats();setInterval(stats,60000);
  }
})();
