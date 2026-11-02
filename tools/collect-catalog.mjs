import fs from 'node:fs/promises';
import vm from 'node:vm';

const root = new URL('../data/catalog-source/', import.meta.url);
await fs.mkdir(root, { recursive: true });
const pages = [
  ['laptop', 'laptop.html'], ['phone', 'mobile.html'],
  ['audio', 'thiet-bi-am-thanh/tai-nghe/tai-nghe-bluetooth.html'],
  ['audio', 'thiet-bi-am-thanh/tai-nghe/headphones.html'],
  ['accessory', 'phu-kien/chuot-ban-phim-may-tinh.html'],
  ['accessory', 'phu-kien/pin-du-phong.html'],
  ['accessory', 'phu-kien/sac-dien-thoai.html'],
  ['accessory', 'phu-kien/sac-dien-thoai/cap-chuyen-doi-dau-chuyen-doi-macbook.html'],
  ...['asus', 'acer', 'lenovo', 'hp', 'dell', 'msi', 'macbook'].map(brand => ['laptop', `laptop/${brand}.html`]),
  ...['apple', 'samsung', 'xiaomi', 'oppo', 'vivo', 'realme'].map(brand => ['phone', `mobile/${brand}.html`]),
];
const products = new Map();
const failures = [];
for (const [category, path] of pages) {
  const url = `https://cellphones.com.vn/${path}`;
  const cache = new URL(path.replaceAll('/', '_'), root);
  try {
    let html;
    try { html = await fs.readFile(cache, 'utf8'); }
    catch {
      const response = await fetch(url, { signal: AbortSignal.timeout(60000) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      html = await response.text();
      await fs.writeFile(cache, html);
      await new Promise(resolve => setTimeout(resolve, 1200));
    }
    const script = html.match(/<script>\s*(window\.__NUXT__=[\s\S]*?)<\/script>/)?.[1];
    if (!script) throw new Error('No embedded catalogue');
    const context = vm.createContext({ window: {} }, { codeGeneration: { strings: false, wasm: false } });
    vm.runInContext(script, context, { timeout: 5000 });
    const walk = value => {
      if (!value || typeof value !== 'object') return;
      const g = value.general, f = value.filterable;
      if (g?.product_id && g.attributes && f?.price && g.url_path) {
        const a = g.attributes;
        const cats = (g.categories || []).map(c => c.name.toLowerCase()).join(' ');
        const title = g.name.toLowerCase();
        let type = /^(laptop |macbook )/.test(title) || a.laptop_cpu ? 'laptop'
          : /^(tai nghe|loa |micro|mic )/.test(title) ? 'audio'
          : /^(chuột|bàn phím|cáp|sạc|pin |hub |bộ |đế |usb |ổ cứng|thẻ nhớ|giá đỡ)/.test(title) ? 'accessory'
          : /điện thoại/.test(cats) && !/phụ kiện/.test(cats) ? 'phone' : '';
        if (type === category && !products.has(g.product_id) && (a.ads_base_image || a.image)) {
          products.set(g.product_id, { source_id: String(g.product_id), name: g.name,
            category: type, brand: g.manufacturer || a.manufacturer || a.phone_accessory_brands || '',
            source_url: `https://cellphones.com.vn/${g.url_path}`,
            listing_url: url, collected_at: new Date().toISOString(),
            price: Math.round(f.special_price > 0 ? f.special_price : f.price),
            image_url: `https://cdn2.cellphones.com.vn/x/media/catalog/product${a.image || a.ads_base_image}`,
            attributes: a });
        }
      }
      for (const child of Object.values(value)) walk(child);
    };
    walk(context.window.__NUXT__);
    console.log(`${path}: ${products.size} unique products`);
  } catch (error) { failures.push({ url, error: error.message }); console.log(`${path}: ${error.message}`); }
}
await fs.writeFile(new URL('../catalog-candidates.json', root), JSON.stringify({ products: [...products.values()], failures }, null, 2));
console.log(`Collected ${products.size} products. Failed pages: ${failures.length}`);
