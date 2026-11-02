import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import puppeteer from 'puppeteer-core';

const base = process.env.NEU_TEST_URL || 'http://127.0.0.1:8000';
const output = 'test-results/customer-layout';
await mkdir(output, { recursive: true });
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
const reports = [];
try {
  const page = await browser.newPage();
  await page.goto(base + '/products');
  const detail = await page.$eval('.product-card a', link => link.pathname);
  for (const width of [320, 375, 768, 1024, 1280, 1440, 1920, 2560]) {
    await page.setViewport({ width, height: 1000 });
    for (const path of ['/', '/products', '/products?category=laptop', detail]) {
      const response = await page.goto(base + path, { waitUntil: 'networkidle0' });
      assert.equal(response.status(), 200, path);
      const report = await page.evaluate(() => {
        const rect = element => { const b = element.getBoundingClientRect(); return { top: b.top, left: b.left, width: b.width, height: b.height }; };
        return {
          overflow: document.documentElement.scrollWidth > innerWidth + 1,
          groups: [...document.querySelectorAll('.product-grid')].map(grid => ({
            rail: grid.classList.contains('product-rail'),
            cards: [...grid.querySelectorAll('.product-card')].map(card => ({ box: rect(card), price: rect(card.querySelector('.price')), bottom: rect(card.querySelector('.card-bottom')) })),
          })),
        };
      });
      assert(!report.overflow, `Page overflow ${path}/${width}`);
      for (const group of report.groups) {
        const rows = new Map();
        for (const card of group.cards) {
          const top = Math.round(card.box.top);
          if (!rows.has(top)) rows.set(top, []);
          rows.get(top).push(card);
        }
        for (const row of rows.values()) {
          assert(row.every(card => Math.abs(card.box.height - row[0].box.height) <= 1), `Unequal card heights ${path}/${width}`);
          assert(row.every(card => Math.abs(card.price.top - row[0].price.top) <= 1), `Price misalignment ${path}/${width}`);
          assert(row.every(card => Math.abs(card.bottom.top - row[0].bottom.top) <= 1), `Actions misaligned ${path}/${width}`);
        }
        if (!group.rail && group.cards.length === 12) assert.equal(new Set([...rows.values()].map(row => row.length)).size, 1, `Incomplete normal page row ${path}/${width}`);
        if (group.rail) assert(rows.size <= 1, `Showcase unexpectedly wraps ${path}/${width}`);
      }
      reports.push({ width, path, ...report });
      if (['/','/products'].includes(path) && [375,1280,1920].includes(width)) {
        await page.evaluate(async () => { for (const image of document.images) image.loading='eager'; await Promise.all([...document.images].map(image=>image.decode().catch(()=>{}))); });
        await page.screenshot({ path: `${output}/${path==='/'?'home':'catalog'}-${width}.png`, fullPage: true });
      }
    }
  }
  await writeFile(`${output}/report.json`, JSON.stringify(reports, null, 2));
  console.log(`${reports.length} page/viewport checks passed: equal cards, prices/actions aligned, full normal catalogue rows, no overflow.`);
} finally { await browser.close(); }
