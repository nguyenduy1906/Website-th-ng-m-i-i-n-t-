import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const root = resolve('.');
mkdirSync(join(root, 'test-results'), { recursive: true });
const output = mkdtempSync(join(root, 'test-results/live-filters-'));
const database = join(output, 'shop.db'), port = 8021, base = `http://127.0.0.1:${port}`;
const copy = spawnSync('python', ['-c', "import sqlite3,sys; a=sqlite3.connect(sys.argv[1]);b=sqlite3.connect(sys.argv[2]);a.backup(b);b.execute('UPDATE products SET active=1 WHERE id=1');b.commit();b.close();a.close()", join(root, 'data/shop.db'), database], { encoding: 'utf8', windowsHide: true });
assert.equal(copy.status, 0, copy.stderr);
const countOrders = () => Number(spawnSync('python', ['-c', 'import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute("SELECT count(*) FROM orders").fetchone()[0])', database], { encoding: 'utf8', windowsHide: true }).stdout.trim());
const initialOrderCount = countOrders();
const env = { ...process.env, NEU_DB_PATH: database, NEU_SESSION_SECRET: 'live-filter-isolated-test' };
const server = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], { cwd: root, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
let logs = '', browser;
server.stdout.on('data', chunk => { logs += chunk; }); server.stderr.on('data', chunk => { logs += chunk; });
const passes = [], failures = [], pageErrors = [];
const pause = duration => new Promise(resolve => setTimeout(resolve, duration));
try {
  let ready = false;
  for (let attempt = 0; attempt < 80; attempt++) {
    try { if ((await fetch(base + '/api/health')).ok) { ready = true; break; } } catch {}
    await pause(100);
  }
  assert(ready, logs);
  browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const context = await browser.createBrowserContext(), page = await context.newPage();
  await page.setViewport({ width: 1440, height: 950 });
  page.on('pageerror', error => pageErrors.push(error.message));
  const go = path => page.goto(base + path, { waitUntil: 'networkidle0' });
  const fill = async (selector, value) => {
    await page.$eval(selector, (input, next) => { input.focus(); input.value = next; input.dispatchEvent(new Event('input', { bubbles: true })); }, value);
  };
  const waitQuery = (name, value) => page.waitForFunction((key, expected) => new URL(location.href).searchParams.get(key) === expected && !document.querySelector('[aria-busy="true"]'), { timeout: 8000 }, name, value);
  const check = async (name, task) => {
    try { await task(); passes.push(name); console.log('PASS ' + name); }
    catch (error) { failures.push(name + ': ' + error.message); console.log('FAIL ' + name + ': ' + error.message); await page.screenshot({ path: join(output, name.replaceAll(/[^a-z0-9]+/gi, '-') + '.png'), fullPage: true }); }
  };
  await check('header search works from every public page without losing focus', async () => {
    for (const route of ['/', '/news', '/cart', '/login', '/offers', '/contact', '/about', '/products/1']) {
      await go(route); await page.evaluate(() => { window.searchDocumentMarker = true; });
      await fill('#header-search', 'S'); await waitQuery('q', 'S');
      assert.equal(new URL(page.url()).pathname, '/products', route);
      assert(await page.$('[data-catalog-results]'), route);
      assert.equal(await page.evaluate(() => window.searchDocumentMarker), true, 'No document reload');
      assert.equal(await page.$eval('#header-search', input => input === document.activeElement), true);
      await fill('#header-search', 'Samsung'); await waitQuery('q', 'Samsung');
      await fill('#header-search', ''); await waitQuery('q', '');
      assert((await page.$$('.catalog-grid .product-card')).length > 0);
    }
  });
  await check('composition waits for completed Vietnamese input', async () => {
    await go('/products');
    await page.$eval('#header-search', input => {
      input.focus(); input.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }));
      input.value = 'đ'; input.dispatchEvent(new InputEvent('input', { bubbles: true, isComposing: true }));
    });
    await pause(500); assert.equal(new URL(page.url()).searchParams.has('q'), false);
    await page.$eval('#header-search', input => {
      input.value = 'điện'; input.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
    });
    await waitQuery('q', 'điện');
  });
  await check('news search updates and clears with no reset buttons', async () => {
    await go('/news'); await fill('#news-q', 'zz-no-matching-article'); await waitQuery('q', 'zz-no-matching-article');
    assert.equal((await page.$$('.news-card')).length, 0);
    assert(!(await page.content()).includes('Xóa bộ lọc'));
    await fill('#news-q', ''); await waitQuery('q', '');
    assert.equal(await page.$eval('#news-q', input => input === document.activeElement), true);
  });
  await check('mobile filters initialize after header search from home', async () => {
    await page.setViewport({ width: 375, height: 900 }); await go('/');
    await fill('#header-search', 'zz-no-product'); await waitQuery('q', 'zz-no-product');
    assert(!(await page.content()).includes('Xóa bộ lọc'));
    await page.click('[data-filter-open]');
    assert.equal(await page.$eval('#filter-dialog', node => node.open), true);
    await fill('#mobile-search', ''); await waitQuery('q', '');
    await page.$eval('#mobile-price-slider', slider => { slider.value = '10000000'; slider.dispatchEvent(new Event('input', { bubbles: true })); });
    await waitQuery('max_price', '10000000');
    assert.equal(await page.$eval('#mobile-max', input => input.value), '10000000');
    await page.click('[data-filter-close]');
    await page.setViewport({ width: 1440, height: 950 });
  });
  await check('catalog typing updates results and retains focus', async () => {
    await go('/products'); await fill('#desktop-search', 'Logitech'); await waitQuery('q', 'Logitech');
    assert((await page.$$eval('.catalog-grid h3', nodes => nodes.map(node => node.textContent))).every(name => name.toLowerCase().includes('logitech')));
    assert.equal(await page.$eval('#desktop-search', input => input === document.activeElement), true);
  });
  await check('category selection applies without submit', async () => {
    await fill('#desktop-search', ''); await waitQuery('q', '');
    await page.select('#desktop-category', 'audio'); await waitQuery('category', 'audio');
    assert((await page.$$eval('.catalog-grid .product-copy > .caption', nodes => nodes.map(node => node.firstChild.textContent.trim()))).every(label => label === 'Âm thanh'));
    assert((await page.$$('.catalog-grid .product-card')).length > 0);
  });
  await check('sort applies and preserves category', async () => {
    await page.select('#sort', 'price_asc'); await waitQuery('sort', 'price_asc');
    assert.equal(new URL(page.url()).searchParams.get('category'), 'audio');
    const prices = await page.$$eval('.catalog-grid .price', nodes => nodes.map(node => Number(node.textContent.replace(/\D/g, ''))));
    assert.deepEqual(prices, [...prices].sort((a,b) => a-b));
  });
  await check('brand selection preserves current sort and category', async () => {
    const brand = await page.$$eval('#desktop-brand option', options => options.find(option => option.textContent === 'Sony')?.value);
    assert(brand); await page.select('#desktop-brand', brand); await waitQuery('brand', brand);
    assert.equal(new URL(page.url()).searchParams.get('sort'), 'price_asc');
    assert.equal(new URL(page.url()).searchParams.get('category'), 'audio');
    assert((await page.$$eval('.catalog-grid h3', nodes => nodes.map(node => node.textContent))).every(name => name.toLowerCase().includes('sony')));
  });
  await check('rapid input keeps latest response', async () => {
    await go('/products'); await fill('#desktop-search', 'Samsung'); await pause(350); await fill('#desktop-search', 'Logitech');
    await waitQuery('q', 'Logitech'); await pause(500);
    assert((await page.$$eval('.catalog-grid h3', nodes => nodes.map(node => node.textContent))).every(name => name.toLowerCase().includes('logitech')));
  });
  await check('quick cart after live replacement', async () => {
    const count = Number(await page.$eval('[data-cart-count]', node => node.textContent));
    await page.click('.catalog-grid [data-quick-cart] button');
    await page.waitForFunction(previous => Number(document.querySelector('[data-cart-count]').textContent) === previous + 1, {}, count);
    assert(await page.$('.ui-toast'));
  });
  await check('mobile filter dialog survives live update', async () => {
    await page.setViewport({ width: 375, height: 900 }); await go('/products'); await page.click('[data-filter-open]');
    await page.select('#mobile-category', 'accessory'); await waitQuery('category', 'accessory');
    assert.equal(await page.$eval('#filter-dialog', node => node.open), true);
    await page.click('[data-filter-close]'); assert.equal(await page.$eval('#filter-dialog', node => node.open), false);
    assert.equal(await page.$eval('[data-filter-open]', node => node === document.activeElement), true);
  });
  await check('variant selection navigates immediately', async () => {
    await page.setViewport({ width: 1440, height: 950 }); await go('/products/1');
    const options = await page.$$eval('#variant option', nodes => nodes.map(node => node.value));
    assert(options.length >= 2, 'need seeded multivariant product');
    await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), page.select('#variant', options[1])]);
    assert.equal(new URL(page.url()).searchParams.get('variant'), options[1]);
  });
  await check('checkout shipping and voucher preview without order', async () => {
    await go('/login'); await fill('#email', 'demo.lan@example.test'); await fill('#password', 'Demo@12345');
    await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), page.click('form[action="/login"] button')]);
    await go('/cart');
    await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), page.click('#cart-selection button')]);
    assert.equal(new URL(page.url()).pathname, '/checkout');
    const oldTotal = await page.$eval('.summary-total dd', node => node.textContent);
    await page.select('#shipping_method', 'express');
    await page.waitForFunction(previous => document.querySelector('.summary-total dd').textContent !== previous && !document.querySelector('[data-submit]').disabled, {}, oldTotal);
    await fill('#voucher', 'NEU100');
    await page.waitForFunction(() => document.querySelector('.submit-status').textContent.includes('Đã cập nhật') && !document.querySelector('[data-submit]').disabled);
    assert.equal(new URL(page.url()).pathname, '/checkout');
    assert.equal(await page.$eval('#voucher', input => input.value), 'NEU100');
  });
  const adminContext = await browser.createBrowserContext(), admin = await adminContext.newPage();
  admin.on('pageerror', error => pageErrors.push(error.message)); await admin.setViewport({ width: 1440, height: 950 });
  await check('admin global search updates without submit', async () => {
    await admin.goto(base + '/admin/login', { waitUntil: 'load' });
    await admin.type('#email', 'admin@neushop.local'); await admin.type('#password', 'Admin@12345');
    await Promise.all([admin.waitForNavigation({ waitUntil: 'load' }), admin.click('form button')]);
    await admin.type('#admin-global-search', 'Logitech');
    await admin.waitForFunction(() => location.pathname === '/admin/products' && new URL(location.href).searchParams.get('q') === 'Logitech' && !document.querySelector('[aria-busy="true"]'));
    const names = await admin.$$eval('.table-product strong', nodes => nodes.map(node => node.textContent));
    assert(names.length > 0); assert(names.every(name => name.toLowerCase().includes('logitech')));
  });
  await check('admin inner search retains focus after replacement', async () => {
    await admin.$eval('.admin-search input[name=q]', input => { input.focus(); input.value = 'Sony'; input.dispatchEvent(new Event('input', { bubbles: true })); });
    await admin.waitForFunction(() => new URL(location.href).searchParams.get('q') === 'Sony' && !document.querySelector('[aria-busy="true"]'));
    assert.equal(await admin.$eval('.admin-search input[name=q]', input => input === document.activeElement), true);
  });
  await check('every admin search updates and clears without submit', async () => {
    for (const [route, selector] of [['/admin/products', '#admin-q'], ['/admin/orders', '#orders-q'], ['/admin/users', '#users-q'], ['/admin/contact', '#contact-q']]) {
      await admin.goto(base + route, { waitUntil: 'load' });
      for (const value of ['z', 'zz-no-match', '']) {
        await admin.$eval(selector, (input, value) => { input.focus(); input.value = value; input.setSelectionRange(value.length, value.length); input.dispatchEvent(new Event('input', { bubbles: true })); }, value);
        await admin.waitForFunction(value => new URL(location.href).searchParams.get('q') === value && !document.querySelector('[aria-busy="true"]'), {}, value);
        const focus = await admin.$eval(selector, input => ({ active: input === document.activeElement, caret: input.selectionStart, value: input.value }));
        assert.equal(focus.active, true); assert.equal(focus.value, value); assert.equal(focus.caret, value.length);
      }
    }
  });
  await check('no JavaScript still has submit fallback', async () => {
    const fallback = await browser.newPage(); await fallback.setJavaScriptEnabled(false); await fallback.goto(base + '/products', { waitUntil: 'load' });
    assert.equal(await fallback.$eval('.filter-panel [data-live-submit]', button => button.hidden), false);
    await fallback.close();
  });
  assert.deepEqual(pageErrors, [], 'No JavaScript errors');
  assert.equal(countOrders(), initialOrderCount, 'Search, filter and checkout previews never create orders');
  writeFileSync(join(output, 'results.json'), JSON.stringify({ passes, failures, pageErrors }, null, 2));
  console.log(JSON.stringify({ passed: passes.length, failures, output }, null, 2));
  if (failures.length) process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill(); writeFileSync(join(output, 'server.log'), logs);
}
