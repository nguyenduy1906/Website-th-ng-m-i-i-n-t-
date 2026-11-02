import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import puppeteer from 'puppeteer-core';

const fixture = JSON.parse(await fs.readFile('docs/catalog-real.json', 'utf8'));
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
const output = 'test-results/real-catalog';
await fs.mkdir(output, { recursive: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8000/products', { waitUntil: 'networkidle0' });
  const failed = await page.evaluate(async products => {
    const errors = [];
    for (let offset = 0; offset < products.length; offset += 8) {
      await Promise.all(products.slice(offset, offset + 8).map(async product => {
        const image = new Image(); image.src = product.media;
        try { await image.decode(); if (image.naturalWidth < 50) errors.push(product.source_id); }
        catch { errors.push(product.source_id); }
      }));
    }
    return errors;
  }, fixture.products);
  assert.deepEqual(failed, [], 'All imported images must decode');
  const detail = await page.$eval('.product-card a', link => link.href);
  for (const width of [320, 768, 1440]) {
    await page.setViewport({ width, height: 1000 });
    for (const [label, url] of [['catalog','http://127.0.0.1:8000/products'],['product', detail]]) {
      const response = await page.goto(url, { waitUntil: 'networkidle0' });
      assert.equal(response.status(), 200);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Overflow ${label}/${width}`);
      if (label === 'product') assert(await page.$('a[href^="https://cellphones.com.vn/"]'), 'Source attribution visible');
      await page.screenshot({ path: `${output}/${label}-${width}.png`, fullPage: true });
    }
  }
  assert.deepEqual(errors, []);
  console.log(`${fixture.products.length} local images decoded; catalogue/detail passed at 320, 768, 1440px; no JavaScript errors.`);
} finally { await browser.close(); }
