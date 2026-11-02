import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import puppeteer from 'puppeteer-core';

const root = resolve('.');
const outputRoot = join(root, 'test-results');
mkdirSync(outputRoot, { recursive: true });
const output = mkdtempSync(join(outputRoot, 'browser-'));
const port = 8017;
const base = `http://127.0.0.1:${port}`;
const server = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: root,
  env: { ...process.env, NEU_DB_PATH: join(output, 'shop.db'), NEU_SESSION_SECRET: 'isolated-browser-test-secret' },
  stdio: ['ignore', 'pipe', 'pipe'],
  windowsHide: true,
});
let logs = '';
server.stdout.on('data', (data) => { logs += data; });
server.stderr.on('data', (data) => { logs += data; });
let browser;
const failures = [];
const pages = [];

try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(logs);
    try {
      const health = await fetch(`${base}/api/health`);
      if (health.ok) { ready = true; break; }
    } catch {}
    await new Promise((done) => setTimeout(done, 100));
  }
  assert(ready, `Test server did not start: ${logs}`);
  const seeded = spawnSync('python', ['-m','app.db','--seed-demo'], {cwd:root,env:{...process.env,NEU_DB_PATH:join(output,'shop.db')},encoding:'utf8',windowsHide:true});
  assert.equal(seeded.status,0,seeded.stderr);
  const chrome = [process.env.CHROME_PATH, 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find((path) => path && existsSync(path));
  assert(chrome, 'Chrome or Edge is required for browser checks.');
  browser = await puppeteer.launch({ executablePath: chrome, headless: true });
  const page = await browser.newPage();
  page.on('pageerror', (error) => failures.push(`JavaScript: ${error.message}`));
  const go = async (path) => {
    const response = await page.goto(base + path, { waitUntil: 'load' });
    assert(response.ok(), `${path}: ${response.status()}`);
  };
  const submit = async (selector) => {
    const elements = await page.$$(selector);
    let target;
    for (const element of elements) if (await element.evaluate(el=>!el.closest('details:not([open])')) && await element.boundingBox()) { target=element;break; }
    if (!target && selector.includes('/logout')) { await page.click('.account-dropdown summary'); for (const element of await page.$$(selector)) if (await element.evaluate(el=>!el.closest('details:not([open])')) && await element.boundingBox()) { target=element;break; } }
    assert(target,'Visible submit control: '+selector);
    await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), target.click()]);
  };
  const inspect = async (name, path) => {
    for (const width of [320, 375, 768, 1280]) {
      await page.setViewport({ width, height: 900 });
      await go(path);
      await page.evaluate(async () => {
        await Promise.all([...document.images].map((image) => {
          image.loading = 'eager';
          return image.decode().catch(() => {});
        }));
      });
      const result = await page.evaluate(() => {
        const visible = (element) => element.getClientRects().length > 0;
        return {
          overflow: document.documentElement.scrollWidth > innerWidth,
          images: [...document.images].filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.src),
          nestedControls: document.querySelectorAll('a button, button a, button button').length,
          labels: [...document.querySelectorAll('input:not([type="hidden"]), select, textarea')].filter(visible).filter((element) => !element.labels?.length && !element.getAttribute('aria-label')).map((element) => element.name),
        };
      });
      if (result.overflow || result.images.length || result.nestedControls || result.labels.length) failures.push(`${name}@${width}: ${JSON.stringify(result)}`);
      if (width === 375 || width === 1280) await page.screenshot({ path: join(output, `${name}-${width}.png`), fullPage: true });
      pages.push(`${name}@${width}`);
    }
  };
  await inspect('home', '/');
  await inspect('catalog', '/products');
  await inspect('product', '/products/1');
  await inspect('login', '/login');
  await inspect('register', '/register');
  await inspect('cart-empty', '/cart');
  await inspect('offers', '/offers');
  await inspect('news', '/news');
  await inspect('article', '/news/1');
  await inspect('policies', '/policies');
  await inspect('forgot', '/forgot-password');
  await inspect('admin-login', '/admin/login');

  await page.setViewport({ width: 1280, height: 900 });
  await go('/');
  await page.click('[data-carousel-index="1"]');
  assert.equal(await page.$eval('[data-carousel-index="1"]',e=>e.getAttribute('aria-pressed')),'true');
  await page.click('[data-carousel-index="0"]');
  await page.evaluate(() => localStorage.setItem('neu-language','en'));
  await go('/');
  assert.equal(await page.evaluate(() => document.documentElement.lang), 'vi');
  assert.equal((await page.$$('[data-language-toggle],a[href="/compare"],form[action="/compare"]')).length, 0);
  await page.click('.mega-menu summary');
  assert(await page.$eval('.mega-menu',e=>e.open));
  await page.keyboard.press('Escape');
  assert.equal(await page.$eval('.mega-menu',e=>e.open),false);
  await page.click('.product-card [data-quick-cart] button');
  await page.waitForFunction(()=>Number(document.querySelector('[data-cart-count]').textContent)>0);
  assert(await page.$('.ui-toast'));
  await go('/cart');
  await submit('button[name="remove"]');
  await page.setViewport({ width: 375, height: 900 });
  await go('/');
  await page.click('[data-menu-open]');
  assert(await page.$eval('#category-dialog', (dialog) => dialog.open), 'Category dialog opens');
  await page.keyboard.press('Escape');
  assert(await page.$eval('[data-menu-open]', (button) => button === document.activeElement), 'Dialog returns keyboard focus');
  await go('/products');
  await page.click('[data-filter-open]');
  assert(await page.$eval('#filter-dialog', (dialog) => dialog.open), 'Mobile filter drawer opens');
  await page.select('#mobile-category', 'phone');
  await page.waitForFunction(() => new URL(location.href).searchParams.get('category') === 'phone' && !document.querySelector('[data-catalog-results]').hasAttribute('aria-busy'));
  assert(page.url().includes('category=phone'), 'Mobile filter applies category');
  assert(await page.$eval('#filter-dialog button.full', button => button.hidden), 'Live filter needs no confirmation button');
  await page.keyboard.press('Escape');

  await page.setViewport({ width: 1280, height: 900 });
  await go('/products');
  await page.type('#desktop-search', 'NEU');
  await page.waitForFunction(() => new URL(location.href).searchParams.get('q') === 'NEU' && !document.querySelector('[data-catalog-results]').hasAttribute('aria-busy'));
  assert(await page.$eval('#desktop-search', input => input === document.activeElement && input.value === 'NEU'), 'Live search preserves typing focus');
  await page.select('#sort', 'price_asc');
  await page.waitForFunction(() => new URL(location.href).searchParams.get('sort') === 'price_asc' && !document.querySelector('[data-catalog-results]').hasAttribute('aria-busy'));
  const sortedPrices = await page.$$eval('.catalog-grid [data-vnd]', prices => prices.map(element => Number(element.dataset.vnd)));
  assert.deepEqual(sortedPrices, [...sortedPrices].sort((a,b) => a-b), 'Sort updates results immediately');

  await go('/register');
  await page.type('#name', 'Khách hàng Demo');
  await page.type('#email', 'browser@example.com');
  await page.type('#password', 'Password123');
  await page.type('#confirm', 'Password123');
  await submit('.auth-form form button');
  assert(page.url().endsWith('/verify'), 'Registration requires OTP');
  const otp = await page.$eval('#demo-otp', (element) => element.textContent);
  await inspect('verify', '/verify');
  await page.type('#code', otp);
  await submit('.narrow-form form button');
  assert(page.url().endsWith('/account'), 'OTP creates authenticated account');
  await go('/products/1');
  const alternateVariant = await page.$$eval('#variant option', options => options.find(option => !option.selected)?.value);
  if (alternateVariant) {
    await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), page.select('#variant', alternateVariant)]);
    assert.equal(await page.$eval('#variant', select => select.value), alternateVariant, 'Variant updates on selection');
  }
  const initialQuantity=await page.$eval('#quantity',e=>Number(e.value));
  await page.click('[data-quantity-step="1"]');
  assert.equal(await page.$eval('#quantity',e=>Number(e.value)),initialQuantity+1);
  await page.click('[data-quantity-step="-1"]');
  const thumbnails=await page.$$('[data-gallery-src]');
  if(thumbnails.length>1)await thumbnails[1].click();
  await page.click('[data-image-zoom]');
  assert(await page.$eval('#image-zoom-dialog',e=>e.open));
  await page.keyboard.press('Escape');
  await submit('.buy-actions button.secondary');
  await inspect('cart', '/cart');
  await inspect('checkout', '/checkout');
  await page.type('#recipient', 'Khách hàng Demo');
  await page.type('#phone', '0912345678');
  await page.type('#address', '12 Đường Demo, Hà Nội');
  await page.select('#shipping_method', 'express');
  await page.waitForFunction(() => document.querySelector('.order-summary dl').textContent.includes('50.000') && !document.querySelector('[data-submit]').disabled);
  assert.equal(await page.$eval('#recipient', input => input.value), 'Khách hàng Demo', 'Live shipping preview preserves recipient');
  await page.type('#voucher', 'NEU100');
  await page.waitForFunction(() => document.querySelector('.order-summary dl').textContent.includes('100.000') && !document.querySelector('[data-submit]').disabled);
  assert(await page.$eval('button[value="preview"]', button => button.hidden), 'Checkout preview needs no confirmation button');
  await submit('[data-submit]');
  const orderPath = new URL(page.url()).pathname;
  assert(orderPath.startsWith('/orders/'), 'Order is created through browser');
  await inspect('order', orderPath);
  await inspect('account', '/account');
  for (const section of ['profile','addresses','security','orders','notifications','support']) await inspect('account-' + section, '/account/' + section);
  await go('/account/addresses');
  await page.type('#recipient','Khách hàng Demo');
  await page.type('#phone','0912345678');
  await page.type('#address','12 Đường Demo, Hà Nội');
  await submit('form[action="/account/addresses"] .button');
  await inspect('address-saved','/account/addresses');
  await go('/account');
  await submit('form[action="/logout"] button');
  await go('/login');
  await page.type('#email', 'admin@neushop.local');
  await page.type('#password', 'Admin@12345');
  await submit('.auth-form form button');
  await inspect('admin', '/admin');
  assert.equal(await page.$$eval('.revenue-chart rect',nodes=>nodes.length),14);
  assert((await page.$$eval('.donut-segment',nodes=>nodes.length))>0);
  await page.click('[data-sidebar-toggle]');
  assert(await page.$eval('body',e=>e.classList.contains('sidebar-collapsed')));
  await page.click('[data-sidebar-toggle]');
  await inspect('admin-products', '/admin/products');
  await inspect('admin-product-form', '/admin/products/new');
  await inspect('admin-orders', '/admin/orders');
  await inspect('admin-order-detail', '/admin' + orderPath);
  for (const section of ['catalog','inventory','returns','vouchers','users','reports','support','content','logs']) await inspect('admin-' + section, '/admin/' + section);
  await inspect('admin-product-edit', '/admin/products/1/edit');
  await page.type('#matrix-colors','Đen, Trắng');
  await page.type('#matrix-storage','256GB, 512GB');
  await page.click('[data-generate-variants]');
  assert.equal(await page.$$eval('[data-variant-rows] tr',rows=>rows.length),4);
  await go('/admin' + orderPath);
  for (const status of ['Đang chuẩn bị','Đang giao','Hoàn tất']) {
    await page.select('#status',status);
    await submit('form[action$="/status"] .button');
  }
  await submit('form[action="/logout"] button');
  await go('/login');
  await page.type('#email','browser@example.com');
  await page.type('#password','Password123');
  await submit('.auth-form form button');
  await inspect('completed-order',orderPath);
  await go('/products/1');
  await page.click('#reviews details summary');
  await page.type('#content','Sản phẩm phù hợp nhu cầu học tập trong demo.');
  await submit('form[action$="/reviews"] .button');
  await inspect('product-reviewed','/products/1');
  await go(orderPath);
  await page.click('[data-return-open]');
  await page.type('form[action$="/return"] textarea','Yêu cầu trả hàng kiểm thử giao diện demo');
  await submit('form[action$="/return"] .button');
  await inspect('order-return-request',orderPath);
  await go('/account');

  await page.setJavaScriptEnabled(false);
  await go('/products');
  assert(await page.$('.product-card'), 'Catalogue works without JavaScript');
  await go('/products/1');
  await submit('.buy-actions button.secondary');
  assert(page.url().endsWith('/cart'), 'Cart form works without JavaScript');
  await page.setJavaScriptEnabled(true);
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await go('/');
  assert.equal(await page.$eval('.button', (element) => getComputedStyle(element).transitionDuration), '0s');

  writeFileSync(join(output, 'report.json'), JSON.stringify({ pages, failures, checks: ['live-filter','live-sort','live-search-focus','immediate-variant','live-checkout-preview','registration-otp','purchase','admin','order-fulfillment','verified-review','return-request','saved-address','vietnamese-interface','dialog-keyboard','no-javascript','reduced-motion'] }, null, 2));
  assert.deepEqual(failures, []);
  console.log(`PASS: ${pages.length} page/viewport checks plus OTP, purchase, fulfillment, verified review, return request, admin, keyboard dialog, no-JS and reduced-motion. Screenshots: ${output}`);
} finally {
  if (browser) await browser.close();
  server.kill();
  if (server.exitCode === null) await once(server, 'exit');
  writeFileSync(join(output, 'server.log'), logs);
}
