(() => {
  const formatter = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' });
  const text = (node, value) => { node.textContent = value; return node; };
  const toast = (message, error = false) => {
    const root = document.querySelector('[data-toast-root]');
    if (!root) return;
    const item = document.createElement('div'); item.className = 'ui-toast' + (error ? ' error' : ''); item.setAttribute('role', error ? 'alert' : 'status');
    const close = text(document.createElement('button'), '×'); close.type = 'button'; close.setAttribute('aria-label', 'Đóng thông báo'); close.onclick = () => item.remove();
    item.append(text(document.createElement('span'), message), close); root.append(item);
    if (!error) setTimeout(() => item.remove(), 6000);
  };
  const updateCart = (count) => document.querySelectorAll('[data-cart-count]').forEach((badge) => { badge.textContent = count; badge.setAttribute('aria-label', count + ' sản phẩm'); });
  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-quick-cart]'); if (!form) return;
    event.preventDefault(); const button = form.querySelector('button'); if (button.disabled) return;
    button.disabled = true; button.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(form.action, { method: 'POST', body: new URLSearchParams(new FormData(form)), headers: { 'X-Requested-With': 'fetch' } });
      if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Phiên đã hết hạn. Tải lại trang và thử lại.');
      const result = await response.json(); if (!response.ok) throw new Error(result.message || result.detail || 'Không thể thêm sản phẩm.');
      updateCart(result.count); toast(result.message);
    } catch (error) { toast(error.message, true); }
    finally { button.disabled = false; button.removeAttribute('aria-busy'); }
  });
  if (document.querySelector('[data-cart-count]')) {
    setInterval(async () => { if (document.hidden) return; try { const response = await fetch('/api/cart-summary'); if (response.ok) updateCart((await response.json()).count); } catch {} }, 15000);
    window.addEventListener('focus', async () => { try { const r = await fetch('/api/cart-summary'); if (r.ok) updateCart((await r.json()).count); } catch {} });
  }

  const search = document.querySelector('[data-autosuggest]'), results = document.querySelector('#search-results');
  let timer, controller;
  const closeSearch = () => { if (results) results.hidden = true; search?.setAttribute('aria-expanded', 'false'); };
  search?.addEventListener('input', () => {
    clearTimeout(timer); controller?.abort(); closeSearch();
    const query = search.value.trim(); if (query.length < 1) return;
    timer = setTimeout(async () => {
      controller = new AbortController(); search.setAttribute('aria-busy', 'true');
      try {
        const response = await fetch('/api/search?q=' + encodeURIComponent(query), { signal: controller.signal });
        if (!response.ok) throw new Error(); const products = await response.json();
        if (search.value.trim() !== query) return;
        results.replaceChildren();
        for (const product of products) {
          const link = document.createElement('a'); link.href = '/products/' + product.id; link.className = 'search-result';
          const image = document.createElement('img'); image.src = product.image; image.alt = ''; image.width = 48; image.height = 48;
          link.append(image, text(document.createElement('strong'), product.name), text(document.createElement('span'), formatter.format(product.price))); results.append(link);
        }
        if (!products.length) results.append(text(document.createElement('p'), 'Không tìm thấy sản phẩm phù hợp.'));
        results.hidden = false; search.setAttribute('aria-expanded', 'true');
      } catch (error) { if (error.name !== 'AbortError') closeSearch(); }
      finally { search.removeAttribute('aria-busy'); }
    }, 220);
  });
  search?.addEventListener('keydown', (event) => { if (event.key === 'ArrowDown' && !results.hidden) { event.preventDefault(); results.querySelector('a')?.focus(); } if (event.key === 'Escape') closeSearch(); });
  results?.addEventListener('keydown', (event) => {
    const links = [...results.querySelectorAll('a')], index = links.indexOf(document.activeElement);
    if (event.key === 'Escape') { closeSearch(); search.focus(); }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); const next = index + (event.key === 'ArrowDown' ? 1 : -1); if (next < 0) search.focus(); else links[Math.min(next, links.length-1)]?.focus(); }
  });
  document.addEventListener('click', (event) => { if (!event.target.closest('.search')) closeSearch(); });
  document.querySelectorAll('.account-dropdown,.mega-menu').forEach((details) => {
    document.addEventListener('click', (event) => { if (!details.contains(event.target)) details.open = false; });
    details.addEventListener('keydown', (event) => { if (event.key === 'Escape') { details.open = false; details.querySelector('summary').focus(); } });
  });

  document.querySelectorAll('[data-carousel]').forEach((carousel) => {
    const slides = [...carousel.querySelectorAll('[data-carousel-slide]')], indicators = [...carousel.querySelectorAll('[data-carousel-index]')]; let selected = 0;
    const show = (index) => { selected = (index + slides.length) % slides.length; slides.forEach((slide, i) => { slide.hidden = i !== selected; }); indicators.forEach((button, i) => button.setAttribute('aria-pressed', String(i === selected))); };
    carousel.querySelector('[data-carousel-prev]')?.addEventListener('click', () => show(selected-1));
    carousel.querySelector('[data-carousel-next]')?.addEventListener('click', () => show(selected+1));
    indicators.forEach((button) => button.addEventListener('click', () => show(Number(button.dataset.carouselIndex))));
    show(0);
  });
  document.querySelectorAll('[data-countdown]').forEach((element) => {
    const end = Date.parse(element.dataset.countdown.replace(' ', 'T') + 'Z');
    const update = () => { const seconds = Math.max(0, Math.floor((end-Date.now())/1000)); const days = Math.floor(seconds/86400); element.querySelector('[data-countdown-value]').textContent = seconds ? (days ? days+' ngày ' : '') + [Math.floor(seconds/3600)%24, Math.floor(seconds/60)%60, seconds%60].map(v => String(v).padStart(2,'0')).join(':') : 'Đã kết thúc'; };
    update(); setInterval(update, 1000);
  });

  const mainImage = document.querySelector('#product-main-image'), zoomDialog = document.querySelector('#image-zoom-dialog');
  document.querySelectorAll('[data-gallery-src]').forEach((button) => button.addEventListener('click', () => {
    mainImage.src = button.dataset.gallerySrc;
    if (zoomDialog) zoomDialog.querySelector('img').src = mainImage.src;
    document.querySelectorAll('[data-gallery-src]').forEach((thumb) => thumb.setAttribute('aria-pressed', String(thumb === button)));
  }));
  document.querySelector('[data-image-zoom]')?.addEventListener('click', () => zoomDialog.showModal());
  document.querySelector('[data-zoom-close]')?.addEventListener('click', () => zoomDialog.close());
  zoomDialog?.addEventListener('close', () => document.querySelector('[data-image-zoom]').focus());
  document.querySelectorAll('[data-quantity-control],.quantity-form').forEach((group) => {
    const input = group.querySelector('input[type=number]'); if (!input) return;
    if (!group.querySelector('[data-quantity-step]')) {
      const wrapper = document.createElement('span'); wrapper.className = 'quantity-stepper'; input.before(wrapper);
      for (const step of [-1, 1]) { const b = text(document.createElement('button'), step < 0 ? '−' : '+'); b.type = 'button'; b.dataset.quantityStep = step; b.setAttribute('aria-label', step < 0 ? 'Giảm số lượng' : 'Tăng số lượng'); wrapper.append(b); }
      wrapper.insertBefore(input, wrapper.lastChild);
    }
    const updateButtons=()=>group.querySelectorAll('[data-quantity-step]').forEach(button=>{button.disabled=input.disabled||(Number(button.dataset.quantityStep)<0?Number(input.value)<=Number(input.min||1):Number(input.value)>=Number(input.max||99));});
    input.addEventListener('input',updateButtons);updateButtons();
    group.querySelectorAll('[data-quantity-step]').forEach((button) => button.addEventListener('click', () => {
      if (input.disabled) return;
      const value = Math.max(Number(input.min || 1), Math.min(Number(input.max || 99), Number(input.value || 1) + Number(button.dataset.quantityStep)));
      input.value = value; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }));
    }));
  });
  document.addEventListener('input', event => {
    const slider = event.target.closest('[data-price-slider]'); if (!slider) return;
    slider.closest('form').querySelector('input[name=max_price]').value = slider.value;
    slider.closest('.field').querySelector('output').value = Number(slider.value).toLocaleString('vi-VN');
  });

  const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
  const sidebarState = (collapsed) => { document.body.classList.toggle('sidebar-collapsed', collapsed); sidebarToggle?.setAttribute('aria-expanded', String(!collapsed)); };
  try { sidebarState(localStorage.getItem('neu-sidebar') === 'collapsed'); } catch {}
  sidebarToggle?.addEventListener('click', () => { const next = !document.body.classList.contains('sidebar-collapsed'); sidebarState(next); try { localStorage.setItem('neu-sidebar', next ? 'collapsed' : 'expanded'); } catch {} });
  document.querySelectorAll('[data-return-open]').forEach((trigger) => {
    const section = trigger.closest('.return-request'), dialog = section.querySelector('dialog'), form = section.querySelector('form'); if (!dialog || !form) return;
    trigger.hidden = false; dialog.querySelector('[data-return-target]').append(form);
    trigger.addEventListener('click', () => dialog.showModal()); dialog.querySelector('[data-return-close]').addEventListener('click', () => dialog.close()); dialog.addEventListener('close', () => trigger.focus());
  });

  document.querySelectorAll('input[type=file]').forEach((input) => {
    const zone = document.createElement('div'); zone.className = 'upload-zone'; input.before(zone); zone.append(input);
    const caption = text(document.createElement('p'), 'Kéo ảnh vào đây hoặc chọn tệp PNG/JPEG (tối đa 2 MB).'); zone.append(caption);
    input.addEventListener('change', () => {
      zone.querySelector('img')?.remove(); const file = input.files[0]; if (!file) return;
      const valid = ['image/png','image/jpeg'].includes(file.type) && file.size <= 2000000;
      input.setCustomValidity(valid ? '' : 'Chỉ chọn PNG/JPEG tối đa 2 MB.'); input.setAttribute('aria-invalid', String(!valid)); caption.textContent = file.name;
      if (valid) { const image = document.createElement('img'); image.alt = 'Ảnh xem trước'; image.src = URL.createObjectURL(file); image.onload = () => URL.revokeObjectURL(image.src); zone.append(image); }
    });
    zone.addEventListener('dragover', (event) => { event.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (event) => { event.preventDefault(); zone.classList.remove('drag-over'); if (event.dataTransfer.files.length) { const transfer = new DataTransfer(); transfer.items.add(event.dataTransfer.files[0]); input.files = transfer.files; input.dispatchEvent(new Event('change')); } });
  });
  window.addEventListener('pageshow',()=>document.querySelectorAll('button[aria-busy=true]').forEach(button=>button.removeAttribute('aria-busy')));
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('invalid', (event) => {
      const input = event.target; input.setAttribute('aria-invalid', 'true'); const id = input.id + '-client-error';
      if (input.id) { let message = document.getElementById(id); if (!message) { message = document.createElement('small'); message.id = id; message.className = 'field-error'; input.closest('.field')?.append(message); } message.textContent = input.validationMessage; input.setAttribute('aria-describedby', id); }
    }, true);
    form.addEventListener('input', (event) => { const input = event.target; if (input.validity?.valid) { input.removeAttribute('aria-invalid'); document.getElementById(input.id + '-client-error')?.remove(); } });
    form.addEventListener('submit', (event) => { if (event.defaultPrevented || form.matches('[data-quick-cart]') || !event.submitter) return; event.submitter.setAttribute('aria-busy', 'true'); });
  });
})();


(() => {
  for (const builder of document.querySelectorAll('[data-variant-builder]')) {
    builder.hidden = false;
    const form = builder.querySelector('[data-matrix-form]'), tbody = builder.querySelector('[data-variant-rows]'), status = builder.querySelector('[data-matrix-status]');
    builder.querySelector('[data-generate-variants]').addEventListener('click', () => {
      const values = (id) => [...new Set(builder.querySelector(id).value.split(',').map(v=>v.trim()).filter(Boolean))];
      const colors = values('#matrix-colors'), storage = values('#matrix-storage');
      if (!colors.length || !storage.length || colors.length*storage.length>20) { status.textContent = 'Nhập màu và cấu hình; tối đa 20 tổ hợp.'; return; }
      tbody.replaceChildren(); let index = 0;
      for (const color of colors) for (const capacity of storage) {
        const tr = document.createElement('tr');
        const defaults = {color,storage:capacity,sku:'NEU-'+form.dataset.productId+'-B'+Date.now().toString(36).toUpperCase()+'-'+(++index),price:'',stock:'0'};
        for (const key of ['color','storage','sku','price','stock']) {
          const td = document.createElement('td'), input = document.createElement('input'); input.dataset.matrixField = key; input.value = defaults[key]; input.required = true; input.setAttribute('aria-label',key+' dòng '+index);
          if (['price','stock'].includes(key)) { input.type='number'; input.min=key==='price'?'1000':'0';input.max=key==='price'?'1000000000':'100000'; } else input.maxLength=key==='sku'?50:60;
          td.append(input);tr.append(td);
        }
        tbody.append(tr);
      }
      status.textContent = index+' biến thể. Nhập giá, tồn đầu và kiểm tra SKU trước khi lưu.';
      builder.querySelector('[data-save-matrix]').disabled=false;
    });
    form.addEventListener('submit', () => {
      const rows=[...tbody.querySelectorAll('tr')].map(tr=>Object.fromEntries([...tr.querySelectorAll('input')].map(input=>[input.dataset.matrixField,input.value])));
      form.querySelector('[name=variants]').value=JSON.stringify(rows);
    });
  }
})();

(() => {
  let railNumber = 0;
  document.querySelectorAll('[data-rail-prev]').forEach(previous => {
    const section = previous.closest('.products-section');
    const next = section?.querySelector('[data-rail-next]');
    const rail = section?.querySelector('.product-rail,.brand-strip');
    if (!rail || !next) return;
    if (!rail.id) rail.id = 'product-rail-' + (++railNumber);
    previous.setAttribute('aria-controls', rail.id); next.setAttribute('aria-controls', rail.id);
    const update = () => {
      const overflow = rail.scrollWidth > rail.clientWidth + 2;
      previous.hidden = next.hidden = !overflow;
      previous.disabled = rail.scrollLeft <= 2;
      next.disabled = rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 2;
    };
    const move = direction => {
      const first = rail.querySelector('.product-card,a');
      const step = first ? first.getBoundingClientRect().width + parseFloat(getComputedStyle(rail).columnGap || 16) : rail.clientWidth;
      rail.scrollBy({ left: direction * step, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    };
    previous.addEventListener('click', () => move(-1)); next.addEventListener('click', () => move(1));
    rail.addEventListener('scroll', update, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(update).observe(rail);
    update();
  });
})();

(() => {
  let pending, timer, generation = 0;
  if(window.__neuPageController&&window.__neuNativeListener)window.__neuNativeListener.call(window.__neuPageController.signal,'abort',()=>{clearTimeout(timer);pending?.abort();generation++;},{once:true});
  const announce = document.createElement('p');
  announce.className = 'sr-only'; announce.dataset.neuLiveAnnouncement = 'true'; announce.setAttribute('role', 'status');
  document.body.append(announce);
  const enhance = () => document.querySelectorAll('[data-live-form] [data-live-submit]').forEach(button => { button.hidden = true; });
  enhance();

  function syncControls(url, active) {
    document.querySelectorAll('form[data-live-form] input[name],form[data-live-form] select[name]').forEach(input => {
      if (new URL(input.form.action).pathname !== url.pathname) return;
      if (input === active || ['csrf','page'].includes(input.name)) return;
      const value = url.searchParams.get(input.name);
      if (value !== null) input.value = value;
      else if (!['sort'].includes(input.name)) input.value = '';
    });
  }

  async function update(form) {
    if (!form.checkValidity()) return;
    clearTimeout(timer); pending?.abort();
    const requestGeneration = ++generation;
    const url = new URL(form.action, location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();
    const active = document.activeElement;
    if (form.matches('.variant-selector')) {
      sessionStorage.setItem('neu-live-scroll', String(scrollY));
      location.assign(url); return;
    }
    const catalog = url.pathname === '/products' ? document.querySelector('[data-catalog-results]') : null;
    const publicResults = [...document.querySelectorAll('[data-public-results]')].find(element => element.dataset.publicResults === url.pathname);
    const admin = document.querySelector('.admin-main');
    const main = document.querySelector('main[data-live-results]');
    if (!catalog && !publicResults && !admin && !main) { location.assign(url); return; }
    pending = new AbortController();
    const target = catalog || publicResults || admin || main;
    target.setAttribute('aria-busy', 'true'); announce.textContent = 'Đang cập nhật kết quả…';
    try {
      const response = await fetch(url, { signal: pending.signal, headers: { 'X-Requested-With': 'fetch' } });
      if (!response.ok) throw new Error('Không thể cập nhật kết quả. Vui lòng thử lại.');
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (requestGeneration !== generation) return;
      const next = parsed.querySelector(catalog ? '[data-catalog-results]' : publicResults ? '[data-public-results]' : admin ? '.admin-main' : 'main[data-live-results]');
      if (!next) { location.assign(url); return; }
      const focusId = active?.id, selection = typeof active?.selectionStart === 'number' ? [active.selectionStart, active.selectionEnd] : null;
      target.replaceChildren(...next.childNodes);
      if (catalog || publicResults) {
        const heading = document.querySelector('.page-heading'), nextHeading = parsed.querySelector('.page-heading');
        if (heading && nextHeading) heading.replaceChildren(...nextHeading.childNodes);
      }
      syncControls(url, active);
      if (admin) {
        document.querySelectorAll('.admin-rail nav a').forEach(link => { if (new URL(link.href).pathname === url.pathname) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current'); });
      }
      if (focusId && !active.isConnected && document.activeElement === document.body) {
        const replacement = document.getElementById(focusId); replacement?.focus({ preventScroll: true });
        if (selection && replacement?.setSelectionRange) replacement.setSelectionRange(...selection);
      }
      document.querySelector('.home-nav')?.removeAttribute('aria-current');
      document.title = parsed.title;
      history.replaceState({}, '', url);
      announce.textContent = catalog ? document.querySelector('.page-heading p')?.textContent || 'Đã cập nhật sản phẩm.' : 'Đã cập nhật kết quả.';
      enhance(); document.dispatchEvent(new Event('neu:content-updated'));
    } catch (error) {
      if (error.name !== 'AbortError') { announce.textContent = error.message; form.querySelectorAll('[data-live-submit]').forEach(button => { button.hidden = false; }); }
    } finally { if (requestGeneration === generation) target.removeAttribute('aria-busy'); }
  }

  function scheduleSearch(event) {
    const form = event.target.closest('form[data-live-form]');
    if (!form || !event.target.matches('input:not([type=hidden]),textarea')) return;
    clearTimeout(timer); pending?.abort(); generation++;
    document.querySelector('[data-live-results] [aria-busy="true"],main[aria-busy="true"]')?.removeAttribute('aria-busy');
    if (!event.isComposing) timer = setTimeout(() => update(form), 320);
  }
  document.addEventListener('input', scheduleSearch);
  document.addEventListener('compositionend', scheduleSearch);
  document.addEventListener('change', event => {
    const form = event.target.closest('form[data-live-form]');
    if (!form || !event.target.matches('select,input[type=checkbox],input[type=radio],input[type=date],input[type=range]')) return;
    update(form);
  });
  document.addEventListener('submit', event => {
    if (event.target.matches('form[data-live-form]')) { event.preventDefault(); update(event.target); }
  });
  window.addEventListener('pageshow', () => {
    const previous = sessionStorage.getItem('neu-live-scroll');
    if (previous !== null) { scrollTo(0, Number(previous)); sessionStorage.removeItem('neu-live-scroll'); }
  });
})();
