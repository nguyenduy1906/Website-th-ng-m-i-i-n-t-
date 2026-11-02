(() => {
const currency = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' });
const root = document.documentElement;
root.classList.add('js');
document.querySelectorAll('[data-vnd]').forEach((element) => { element.textContent = currency.format(Number(element.dataset.vnd)); });

function enhanceDialogs() {
  for (const [id, openSelector, closeSelector] of [
    ['category-dialog', '[data-menu-open]', '[data-menu-close]'],
    ['filter-dialog', '[data-filter-open]', '[data-filter-close]'],
  ]) {
    const dialog = document.getElementById(id), trigger = document.querySelector(openSelector);
    if (!dialog || !trigger || dialog.dataset.enhanced) continue;
    dialog.dataset.enhanced = "true";
    trigger.hidden = false;
    trigger.addEventListener('click', () => dialog.showModal());
    dialog.querySelector(closeSelector)?.addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => trigger.focus());
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
  }
}
enhanceDialogs();
document.addEventListener('neu:content-updated', enhanceDialogs);

document.querySelectorAll('img').forEach((image) => image.addEventListener('error', () => {
  if (!image.src.endsWith('/static/images/fallback.svg')) { image.src = '/static/images/fallback.svg'; image.alt = 'Ảnh sản phẩm chưa có'; }
}));
document.querySelectorAll('[data-print]').forEach((button) => button.addEventListener('click', () => window.print()));
document.querySelectorAll('form[data-confirm]').forEach((form) => form.addEventListener('submit', (event) => {
  if (!window.confirm(form.dataset.confirm)) event.preventDefault();
}));

document.querySelectorAll('[data-checkout]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!event.submitter?.matches('[data-submit]')) return;
    const button = form.querySelector('[data-submit]');
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    form.querySelector('[role="status"]').textContent = 'Đang kiểm tra tồn kho và lưu đơn hàng…';
  });
  const previewButton = form.querySelector('button[value="preview"]');
  if (previewButton) previewButton.hidden = true;
  let previewTimer, previewRequest, previewGeneration = 0;
  async function preview() {
    clearTimeout(previewTimer); previewRequest?.abort();
    const generation = ++previewGeneration;
    previewRequest = new AbortController();
    const submit = form.querySelector('[data-submit]'), status = form.querySelector('[role="status"]');
    submit.disabled = true; status.textContent = 'Đang cập nhật ưu đãi và phí vận chuyển…';
    try {
      const data = new URLSearchParams(new FormData(form)); data.set('action', 'preview');
      const response = await fetch(form.getAttribute('action') || location.href, { method: 'POST', body: data, signal: previewRequest.signal });
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      const totals = parsed.querySelector('.order-summary dl');
      if (!totals || !response.ok) throw new Error('Chưa thể cập nhật tổng tiền. Thử lại trước khi đặt hàng.');
      if (generation !== previewGeneration) return;
      form.querySelector('.order-summary dl').replaceWith(totals);
      const voucher = form.querySelector('#voucher');
      const sourceField = parsed.querySelector('#voucher')?.closest('.field');
      const field = voucher?.closest('.field');
      field?.querySelectorAll('.field-error').forEach(error => error.remove());
      sourceField?.querySelectorAll('.field-error').forEach(error => field?.append(error.cloneNode(true)));
      status.textContent = 'Đã cập nhật tổng tiền.'; submit.disabled = false;
    } catch (error) {
      if (error.name !== 'AbortError') { status.textContent = error.message; if (previewButton) previewButton.hidden = false; }
    }
  }
  form.addEventListener('input', event => {
    if (event.target.id !== 'voucher') return;
    clearTimeout(previewTimer); previewRequest?.abort(); previewGeneration++;
    form.querySelector('[data-submit]').disabled = true;
    previewTimer = setTimeout(preview, 400);
  });
  form.addEventListener('change', event => {
    if (event.target.matches('#shipping_method,#address_id,input[name="payment_method"]')) preview();
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('[data-submit]').forEach((button) => { button.disabled = false; button.removeAttribute('aria-busy'); });
});

for (const chat of document.querySelectorAll('[data-chat]')) {
  if (!Number(chat.dataset.chat)) continue;
  let signature = '';
  async function updateChat() {
    if (document.hidden) return;
    try {
      const response = await fetch('/api/support?customer=' + encodeURIComponent(chat.dataset.chat));
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return;
      const messages = await response.json(), next = messages.map((message) => message.id).join(',');
      if (next === signature) return;
      signature = next;
      if (!messages.length) return;
      const nearBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80;
      const nodes = messages.map((message) => {
        const article = document.createElement('article'); article.className = 'message' + (message.admin ? ' from-admin' : '');
        const name = document.createElement('strong'), body = document.createElement('p'), time = document.createElement('small');
        name.textContent = message.name; body.textContent = message.content; time.textContent = message.time; article.append(name, body, time); return article;
      });
      chat.replaceChildren(...nodes);
      if (nearBottom) chat.scrollTop = chat.scrollHeight;
    } catch {}
  }
  updateChat();
  setInterval(updateChat, 5000);
}


for (const watcher of document.querySelectorAll('[data-order-watch]')) {
  setInterval(async () => {
    if (document.hidden) return;
    try {
      const response = await fetch('/api/orders/' + watcher.dataset.orderWatch);
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return;
      const update = await response.json();
      if (update.signature === watcher.dataset.orderSignature) return;
      if (document.activeElement?.matches('input,textarea,select')) {
        watcher.className = 'notice'; watcher.setAttribute('role','status');
        const link = document.createElement('a'); link.href = location.href; link.textContent = 'Đơn hàng vừa có cập nhật. Chọn để tải lại thông tin mới.'; watcher.replaceChildren(link);
      } else location.reload();
    } catch {}
  }, 5000);
}

const stickyNavigation = document.querySelector('.site-header,.admin-topbar');
if (stickyNavigation) {
  const updateNavigationHeight = () => root.style.setProperty('--sticky-header-height', stickyNavigation.getBoundingClientRect().height + 'px');
  updateNavigationHeight();
  if (window.ResizeObserver) new ResizeObserver(updateNavigationHeight).observe(stickyNavigation);
  window.addEventListener('resize', updateNavigationHeight);
}

window.__neuRevenueRadiusObserver?.disconnect();
const revenueChart = document.querySelector('.revenue-chart');
if (revenueChart) {
  const updateBarRadius = () => {
    const matrix = revenueChart.getScreenCTM();
    if (!matrix?.a || !matrix?.d) return;
    for (const bar of revenueChart.querySelectorAll('rect')) {
      bar.setAttribute('rx', 5 / Math.abs(matrix.a));
      bar.setAttribute('ry', 5 / Math.abs(matrix.d));
    }
  };
  updateBarRadius();
  window.__neuRevenueRadiusObserver = new ResizeObserver(updateBarRadius);
  window.__neuRevenueRadiusObserver.observe(revenueChart);
}

})();
