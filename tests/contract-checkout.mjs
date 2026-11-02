import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const root = resolve('.');
mkdirSync('test-results', { recursive: true });
const output = mkdtempSync(join(root, 'test-results/contract-checkout-'));
const base = 'http://127.0.0.1:8047';
const seed = spawnSync('python', ['-m', 'app.db', '--seed-demo'], {
  cwd: root, env: { ...process.env, NEU_DB_PATH: join(output, 'shop.db') }, encoding: 'utf8', windowsHide: true,
});
assert.equal(seed.status, 0, seed.stderr);
const server = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8047'], {
  cwd: root, env: { ...process.env, NEU_DB_PATH: join(output, 'shop.db'), NEU_SESSION_SECRET: 'contract-checkout-test-only' },
  windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
});
let logs = '', browser;
server.stdout.on('data', data => { logs += data; });
server.stderr.on('data', data => { logs += data; });
const errors = [], layouts = [];
async function go(page, path) {
  await page.bringToFront();
  await page.goto(base + path, { waitUntil: 'load' });
  await page.waitForSelector('html[data-tab-ready="true"] main');
  await page.waitForNetworkIdle();
}
async function post(page, path, values = {}, expected = 200) {
  const result = await page.evaluate(async ({ path, values }) => {
    const csrf = document.querySelector('[name=csrf]').value;
    const response = await fetch(path, { method: 'POST', body: new URLSearchParams({ csrf, ...values }) });
    return { status: response.status, url: response.url, text: await response.text() };
  }, { path, values });
  assert.equal(result.status, expected, path + ': ' + result.text.slice(0, 160));
  if (expected === 200) await go(page, new URL(result.url).pathname);
  return result;
}
async function layout(page, name) {
  for (const width of [375, 1440]) {
    await page.setViewport({ width, height: 1000 });
    await page.evaluate(() => document.fonts.ready);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), name + ' overflow');
    await page.screenshot({ path: join(output, `${name}-${width}.png`), fullPage: true });
    layouts.push({ name, width });
  }
}
try {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(logs);
    try { if ((await fetch(base + '/api/health')).ok) break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
    if (attempt === 99) throw new Error('Test server unavailable: ' + logs);
  }
  browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const customer = await browser.newPage(), admin = await browser.newPage();
  const invalidRequests = [];
  customer.on('request', request => { if (request.url().includes('RadioNodeList')) invalidRequests.push(request.url()); });
  for (const page of [customer, admin]) page.on('pageerror', error => errors.push(error.message));
  await go(customer, '/login');
  await post(customer, '/login', { email: 'demo.lan@example.test', password: 'Demo@12345' });
  await go(admin, '/admin/login');
  await post(admin, '/login', { email: 'admin@neushop.local', password: 'Admin@12345', portal: 'admin' });
  for (const method of ['cod', 'qr']) {
    await go(customer, '/products/8');
    const variant = await customer.$eval('[name=variant_id]', element => element.value);
    await post(customer, '/cart/add', { variant_id: variant, quantity: 1 });
    await go(customer, '/checkout');
    assert((await customer.$eval('[data-submit]', element => element.textContent)).includes('Tiếp tục xem hợp đồng'));
    for (const [selector, value] of [['#recipient', 'Khách kiểm thử'], ['#phone', '0912345678'], ['#address', '12 Đường Kiểm Thử, Hà Nội']]) {
      await customer.click(selector, { clickCount: 3 });
      await customer.keyboard.down('Control');
      await customer.keyboard.press('A');
      await customer.keyboard.up('Control');
      await customer.type(selector, value);
    }
    await customer.click(`[name=payment_method][value="${method}"]`);
    await layout(customer, method + '-checkout');
    await customer.waitForSelector('[data-submit]:not([disabled])');
    const checkoutRequest = customer.waitForRequest(request => new URL(request.url()).pathname === '/checkout' && request.method() === 'POST');
    await customer.click('[data-submit]');
    await checkoutRequest;
    await customer.waitForFunction(() => location.pathname.startsWith('/contracts/') && document.querySelector('.contract-layout'));
    await customer.evaluate(async () => { await window.__neuPageRefreshPromise; });
    const contractPath = new URL(customer.url()).pathname;
    assert(contractPath.startsWith('/contracts/'));
    const orderPath = await customer.$eval('.contract-layout a[href*="/orders/"]', element => element.getAttribute('href'));
    await layout(customer, method + '-contract-pending');
    await go(admin, '/admin' + orderPath);
    if (method === 'cod') {
      assert(await admin.$('form[action$="/status"] button[disabled]'));
      await post(admin, '/admin' + orderPath + '/status', { status: 'Đang chuẩn bị' }, 409);
    }
    await post(customer, contractPath + '/otp');
    const code = await customer.$eval('#contract-demo-otp', element => element.textContent.trim());
    await customer.type('#contract-code', code);
    await customer.$eval('[name=consent]', element => element.scrollIntoView({ block: 'center' }));
    await customer.click('[name=consent]');
    assert(await customer.$eval('[name=consent]', element => element.checked), 'Contract consent selected');
    assert(await customer.$eval(`form[action="${contractPath}/sign"]`, form => form.checkValidity()), 'Contract fields valid');
    await customer.$eval(`form[action="${contractPath}/sign"] button`, element => element.scrollIntoView({ block: 'center' }));
    const signRequest = customer.waitForRequest(request => new URL(request.url()).pathname === contractPath + '/sign' && request.method() === 'POST');
    await customer.click(`form[action="${contractPath}/sign"] button`);
    await signRequest;
    await customer.waitForFunction(() => document.querySelector('.contract-layout .badge')?.textContent.includes('Đã xác nhận OTP'));
    await layout(customer, method + '-contract-confirmed');
    if (method === 'qr') {
      const paymentPath = await customer.$eval('a[href^="/payments/"]', element => element.getAttribute('href'));
      await go(customer, paymentPath);
      await layout(customer, 'qr-payment');
      await post(customer, paymentPath + '/simulate', { result: 'success' });
    }
    await go(admin, '/admin' + orderPath);
    await post(admin, '/admin' + orderPath + '/status', { status: 'Đang chuẩn bị' });
    assert((await admin.content()).includes('Đang chuẩn bị'));
    await go(admin, '/admin' + contractPath);
    assert(await admin.$(`a[href="/admin${contractPath}/download"]`));
    assert(await admin.$(`a[href="/admin${contractPath}/print"]`));
    console.log('PASS ' + method + ': checkout → contract OTP → payment/COD → admin approval');
  }
  for (const path of ['/', '/products', '/cart', '/checkout', '/account/profile', '/login']) {
    await go(admin, path);
    assert.equal(new URL(admin.url()).pathname, '/admin', path);
    assert(await admin.$('.admin-main'));
    assert.equal(await admin.$('.site-header'), null);
  }
  const publicLinks = await admin.$$eval('a[href]', links => links.map(link => link.getAttribute('href')).filter(href => href.startsWith('/') && !href.startsWith('/admin')));
  assert.deepEqual(publicLinks, []);
  await admin.click('.account-dropdown summary');
  await admin.click('form[action="/logout"] button');
  await admin.waitForFunction(() => location.pathname === '/admin/login' && document.querySelector('.admin-login'));
  assert.equal(await admin.$('a[href="/"]'), null);
  assert.deepEqual(invalidRequests, []);
  console.log('PASS admin: public URLs return to admin; logout stays on admin login');
  assert.deepEqual(errors, []);
  writeFileSync(join(output, 'report.json'), JSON.stringify({ layouts, errors }, null, 2));
  console.log(JSON.stringify({ output, layouts: layouts.length, javascriptErrors: errors.length }));
} finally {
  if (browser) await browser.close();
  server.kill();
  writeFileSync(join(output, 'server.log'), logs);
}
