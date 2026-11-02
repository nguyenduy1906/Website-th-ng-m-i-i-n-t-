import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const source = readFileSync(resolve(root, 'data/erd.mmd'), 'utf8');
const escape = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const width = 350, rowHeight = 27, titleHeight = 32, columnHeight = 24;
const positions = {
  CUSTOMER: [1550, 45], CATEGORY: [80, 450], BRAND: [500, 450], PRODUCT: [920, 430],
  PRODUCT_VARIANT: [1340, 480], CART: [1760, 480], REVIEW: [2180, 430], ORDERS: [2600, 430],
  CART_ITEM: [1760, 860], ORDER_ITEM: [2180, 870], PAYMENT: [3020, 860], NOTIFICATION: [2600, 900],
  FINANCE_PARTNER: [80, 1200], INSTALLMENT_PLAN: [530, 1170],
  INSTALLMENT_CONTRACT: [1080, 1110], INSTALLMENT_SCHEDULE: [1640, 1230],
};
const tables = [...source.matchAll(/^\s{2}([A-Z_]+) \{\n([\s\S]*?)^\s{2}\}/gm)].map((match) => {
  const fields = match[2].trim().split('\n').map((line) => {
    const [type, name, key = ''] = line.trim().split(/\s+/);
    return { type, name, key };
  });
  if (!positions[match[1]]) throw new Error(`Missing position: ${match[1]}`);
  const [x, y] = positions[match[1]];
  return { name: match[1], fields, x, y, w: width, h: titleHeight + columnHeight + fields.length * rowHeight };
});
const byName = Object.fromEntries(tables.map((table) => [table.name, table]));
const foreignFields = {
  'CUSTOMER:CART': 'customer_id', 'CUSTOMER:ORDERS': 'customer_id',
  'CUSTOMER:REVIEW': 'customer_id', 'CUSTOMER:NOTIFICATION': 'customer_id',
  'CART:CART_ITEM': 'cart_id', 'CATEGORY:PRODUCT': 'category_id', 'BRAND:PRODUCT': 'brand_id',
  'PRODUCT:PRODUCT_VARIANT': 'product_id', 'PRODUCT:REVIEW': 'product_id',
  'PRODUCT_VARIANT:CART_ITEM': 'variant_id', 'PRODUCT_VARIANT:ORDER_ITEM': 'variant_id',
  'ORDERS:ORDER_ITEM': 'order_id', 'ORDERS:INSTALLMENT_CONTRACT': 'order_id', 'ORDERS:PAYMENT': 'order_id',
  'FINANCE_PARTNER:INSTALLMENT_PLAN': 'partner_id', 'INSTALLMENT_PLAN:INSTALLMENT_CONTRACT': 'plan_id',
  'INSTALLMENT_CONTRACT:INSTALLMENT_SCHEDULE': 'contract_id',
  'INSTALLMENT_SCHEDULE:PAYMENT': 'schedule_id', 'INSTALLMENT_SCHEDULE:NOTIFICATION': 'schedule_id',
};
const edges = [...source.matchAll(/^\s{2}([A-Z_]+) (\S+) ([A-Z_]+) : (\w+)/gm)].map((match) => {
  const [, from, cardinality, to, label] = match;
  const fk = foreignFields[`${from}:${to}`];
  if (!fk) throw new Error(`Missing field mapping for ${from}:${to}`);
  return { from, to, cardinality, label, fk };
});
const bounds = { w: 3460, h: 1660 };
const rowY = (table, field) => {
  const index = table.fields.findIndex((item) => item.name === field);
  if (index < 0) throw new Error(`Unknown field ${table.name}.${field}`);
  return table.y + titleHeight + columnHeight + index * rowHeight + rowHeight / 2;
};
const inside = (x, y) => tables.some((t) => x > t.x - 14 && x < t.x + t.w + 14 && y > t.y - 14 && y < t.y + t.h + 14);
const clear = (a, b) => !tables.some((t) => {
  const left = t.x - 14, right = t.x + t.w + 14, top = t.y - 14, bottom = t.y + t.h + 14;
  if (a.x === b.x) return a.x > left && a.x < right && Math.max(a.y, b.y) > top && Math.min(a.y, b.y) < bottom;
  return a.y > top && a.y < bottom && Math.max(a.x, b.x) > left && Math.min(a.x, b.x) < right;
});

function route(start, end) {
  const xs = [...new Set([30, bounds.w - 30, start.x, end.x, ...tables.flatMap((t) => [t.x - 32, t.x + t.w + 32])])].sort((a, b) => a - b);
  const ys = [...new Set([20, bounds.h - 20, start.y, end.y, ...tables.flatMap((t) => [t.y - 30, t.y + t.h + 30])])].sort((a, b) => a - b);
  const initial = { x: xs.indexOf(start.x), y: ys.indexOf(start.y), direction: 'h', cost: 0, parent: null };
  const open = [initial], best = new Map();
  while (open.length) {
    open.sort((a, b) => (a.cost + Math.abs(xs[a.x] - end.x) + Math.abs(ys[a.y] - end.y)) - (b.cost + Math.abs(xs[b.x] - end.x) + Math.abs(ys[b.y] - end.y)));
    const node = open.shift();
    if (xs[node.x] === end.x && ys[node.y] === end.y) {
      const points = [];
      for (let current = node; current; current = current.parent) points.unshift({ x: xs[current.x], y: ys[current.y] });
      return { points, cost: node.cost };
    }
    for (const [dx, dy, direction] of [[1, 0, 'h'], [-1, 0, 'h'], [0, 1, 'v'], [0, -1, 'v']]) {
      const x = node.x + dx, y = node.y + dy;
      if (x < 0 || y < 0 || x >= xs.length || y >= ys.length || inside(xs[x], ys[y])) continue;
      const a = { x: xs[node.x], y: ys[node.y] }, b = { x: xs[x], y: ys[y] };
      if (!clear(a, b)) continue;
      const cost = node.cost + Math.abs(b.x - a.x) + Math.abs(b.y - a.y) + (direction !== node.direction ? 55 : 0);
      const id = `${x},${y},${direction}`;
      if (cost >= (best.get(id) ?? Infinity)) continue;
      best.set(id, cost);
      open.push({ x, y, direction, cost, parent: node });
    }
  }
  throw new Error('Could not route relationship outside tables.');
}

function curvedPath(points) {
  const simplified = points.filter((p, i) => i === 0 || i === points.length - 1 || !((points[i - 1].x === p.x && p.x === points[i + 1].x) || (points[i - 1].y === p.y && p.y === points[i + 1].y)));
  let result = `M ${simplified[0].x} ${simplified[0].y}`;
  for (let i = 1; i < simplified.length - 1; i++) {
    const a = simplified[i - 1], b = simplified[i], c = simplified[i + 1];
    const before = Math.hypot(b.x - a.x, b.y - a.y), after = Math.hypot(c.x - b.x, c.y - b.y);
    const radius = Math.min(28, before / 2, after / 2);
    result += ` L ${b.x + (a.x - b.x) * radius / before} ${b.y + (a.y - b.y) * radius / before} Q ${b.x} ${b.y} ${b.x + (c.x - b.x) * radius / after} ${b.y + (c.y - b.y) * radius / after}`;
  }
  const last = simplified.at(-1);
  return `${result} L ${last.x} ${last.y}`;
}

const edgeSvg = edges.map((edge) => {
  const parent = byName[edge.from], child = byName[edge.to];
  const primary = parent.fields.find((field) => field.key.includes('PK')).name;
  const py = rowY(parent, primary), cy = rowY(child, edge.fk), candidates = [];
  for (const pside of [-1, 1]) for (const cside of [-1, 1]) {
    const p = { x: parent.x + (pside === 1 ? width : 0), y: py }, c = { x: child.x + (cside === 1 ? width : 0), y: cy };
    const routed = route({ x: p.x + pside * 32, y: py }, { x: c.x + cside * 32, y: cy });
    candidates.push({ ...routed, points: [p, ...routed.points, c], pside, cside });
  }
  candidates.sort((a, b) => a.cost - b.cost);
  const chosen = candidates[0], p = chosen.points[0], c = chosen.points.at(-1);
  const optional = edge.cardinality.split('--')[1].includes('o'), many = edge.cardinality.includes('{');
  const cardinality = many ? (optional ? '0..n' : '1..n') : '0..1';
  return `<g class="relationship" data-from="${edge.from}" data-to="${edge.to}"><title>${edge.from}.${primary} → ${edge.to}.${edge.fk} (${edge.label}; ${edge.cardinality})</title><path class="connector" d="${curvedPath(chosen.points)}"/><path class="one-mark" d="M ${p.x + chosen.pside * 8} ${p.y - 5} v 10 M ${p.x + chosen.pside * 13} ${p.y - 5} v 10"/>${many ? `<path class="many-mark" d="M ${c.x} ${c.y - 6} L ${c.x + chosen.cside * 12} ${c.y} L ${c.x} ${c.y + 6}"/>` : `<path class="many-mark" d="M ${c.x + chosen.cside * 8} ${c.y - 5} v 10"/>`}<text class="relation-label" x="${c.x + chosen.cside * 19}" y="${c.y - 9}" text-anchor="${chosen.cside === 1 ? 'start' : 'end'}">${cardinality}</text></g>`;
}).join('\n');

const tableSvg = tables.map((table) => {
  const incoming = new Set(edges.filter((edge) => edge.to === table.name).map((edge) => edge.fk));
  const rows = table.fields.map((field, i) => {
    const y = titleHeight + columnHeight + i * rowHeight;
    const keys = [field.key, incoming.has(field.name) && !field.key.includes('FK') ? 'FK' : ''].filter(Boolean).join(', ');
    return `<g class="field-row"><rect y="${y}" width="${width}" height="${rowHeight}" fill="${i % 2 ? '#f6f4fb' : '#ffffff'}"/><path class="row-line" d="M0 ${y + rowHeight} H${width}"/><text class="key-text" x="9" y="${y + 18}">${escape(keys)}</text><text class="type-text" x="63" y="${y + 18}">${escape(field.type)}</text><text class="field-text ${keys.includes('PK') ? 'primary-field' : ''}" x="153" y="${y + 18}">${escape(field.name)}</text></g>`;
  }).join('');
  return `<g class="entity" id="table-${table.name}" data-table="${table.name}" tabindex="0" role="button" aria-label="Bảng ${table.name}, chọn để tô sáng quan hệ" transform="translate(${table.x} ${table.y})"><title>${table.name}: ${table.fields.length} thuộc tính</title><rect class="table-paper" width="${width}" height="${table.h}"/><rect class="table-heading" width="${width}" height="${titleHeight}"/><text class="table-name" x="${width / 2}" y="22" text-anchor="middle">${table.name}</text><rect class="column-heading" y="${titleHeight}" width="${width}" height="${columnHeight}"/><text class="column-label" x="9" y="49">Key</text><text class="column-label" x="63" y="49">Type</text><text class="column-label" x="153" y="49">Field</text>${rows}<path class="column-line" d="M54 ${titleHeight} V${table.h} M142 ${titleHeight} V${table.h}"/><rect class="table-outline" width="${width}" height="${table.h}"/></g>`;
}).join('\n');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${bounds.w} ${bounds.h}" aria-labelledby="diagram-title"><title id="diagram-title">NEU SHOP — ERD: ${tables.length} bảng, ${edges.length} quan hệ</title><style>
.connector{fill:none;stroke:#c4c2cd;stroke-width:1.5}.one-mark,.many-mark{fill:none;stroke:#9b8eab;stroke-width:1.5}.relation-label{font:11px Arial,sans-serif;fill:#70647d;paint-order:stroke;stroke:white;stroke-width:4px;stroke-linejoin:round}.table-paper{fill:white}.table-heading{fill:#eee4fa}.column-heading{fill:#fffbea}.table-name{font:600 15px Arial,sans-serif;fill:#49345f}.column-label{font:11px Arial,sans-serif;fill:#756281}.key-text{font:600 11px Arial,sans-serif;fill:#78529d}.type-text{font:12px Arial,sans-serif;fill:#6b7280}.field-text{font:13px Arial,sans-serif;fill:#263c58}.primary-field{text-decoration:underline}.row-line,.column-line{fill:none;stroke:#ded4ec;stroke-width:1}.table-outline{fill:none;stroke:#bba5d3;stroke-width:1.4}.entity{cursor:pointer;outline:none}.entity:focus-visible .table-outline,.entity.selected .table-outline{stroke:#7041aa;stroke-width:3}.relationship.active .connector,.relationship.active .one-mark,.relationship.active .many-mark{stroke:#7c49b7;stroke-width:2.5}.relationship.active .relation-label{fill:#7041aa}.entity.related .table-heading,.entity.selected .table-heading{fill:#ddc9f4}
</style><g id="relationships">${edgeSvg}</g><g id="entities">${tableSvg}</g></svg>`;

const html = `<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEU SHOP — Database ERD</title>
<style>
:root{--paper:#fff;--ink:#263c58;--muted:#6b6475;--border:#e5ddee;--primary:#7041aa;--soft:#f5f0fa}
*{box-sizing:border-box}html,body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 Arial,sans-serif}body{height:100dvh;display:flex;flex-direction:column}.toolbar{padding:12px 20px;display:flex;align-items:center;justify-content:space-between;gap:16px;border-bottom:1px solid var(--border);flex-wrap:wrap}.title{font-size:16px;font-weight:600}.subtitle{font-size:12px;color:var(--muted);margin-left:12px}.controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}button{min-height:36px;padding:8px 12px;border:1px solid var(--border);background:var(--paper);border-radius:4px;color:var(--ink);font:13px Arial,sans-serif;cursor:pointer}button:hover{background:var(--soft)}button.primary{background:var(--primary);color:var(--paper);border-color:var(--primary)}:focus-visible{outline:2px solid var(--primary);outline-offset:3px}#zoom-value{min-width:44px;text-align:center;font-size:12px;color:var(--muted)}.viewport{overflow:auto;flex:1;min-height:0;touch-action:pan-x pan-y;cursor:grab}.viewport.dragging{cursor:grabbing;user-select:none}.canvas{width:100%;min-width:700px;margin:auto;transform-origin:top left}.canvas svg{display:block;width:100%;height:auto}.footer{padding:8px 20px;border-top:1px solid var(--border);font-size:11px;color:var(--muted);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.print-title{display:none}
@page{size:A3 landscape;margin:7mm}
@media print{html,body{height:auto;display:block}.toolbar,.footer{display:none}.print-title{display:block;font-size:12pt;font-weight:600;margin-bottom:3mm}.viewport{overflow:visible;display:block;cursor:auto}.canvas{width:100%!important;min-width:0;margin:0}.canvas svg{width:100%;height:260mm;object-fit:contain}.entity{cursor:default}.relationship.active .connector,.relationship.active .one-mark,.relationship.active .many-mark{stroke:#9b8eab;stroke-width:1.5}.entity.related .table-heading,.entity.selected .table-heading{fill:#eee4fa}.entity.selected .table-outline{stroke:#bba5d3;stroke-width:1.4}*{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
@media(max-width:700px){.toolbar{padding:10px 12px}.subtitle{display:block;margin:2px 0 0}.footer{padding:8px 12px}}
</style>
</head>
<body>
<header class="toolbar"><div><span class="title">NEU SHOP — Database ERD</span><span class="subtitle">${tables.length} bảng / ${edges.length} quan hệ</span></div><nav class="controls" aria-label="Điều khiển sơ đồ"><button id="zoom-out" aria-label="Thu nhỏ">−</button><output id="zoom-value" aria-live="polite">Vừa màn hình</output><button id="zoom-in" aria-label="Phóng to">+</button><button id="fit">Vừa màn hình</button><button id="actual">Kích thước gốc</button><button id="print" class="primary">In / Lưu PDF</button></nav></header>
<div class="print-title">NEU SHOP — Sơ đồ cơ sở dữ liệu</div>
<main class="viewport" aria-label="Vùng sơ đồ, có thể cuộn và kéo để xem"><div class="canvas">${svg}</div></main>
<footer class="footer"><span>PK: khóa chính · FK: khóa ngoại · UK: khóa duy nhất · 0..1: không hoặc một · 0..n: không hoặc nhiều · 1..n: một hoặc nhiều</span><span>Chọn bảng để xem quan hệ. Kéo nền để di chuyển. In A3 ngang.</span></footer>
<script>
const canvas=document.querySelector('.canvas'),viewport=document.querySelector('.viewport'),output=document.getElementById('zoom-value');
let zoom=1;
function setZoom(value){zoom=Math.max(0.5,Math.min(6,value));canvas.style.width=(zoom*100)+'%';output.textContent=Math.round(zoom*100)+'%'}
document.getElementById('zoom-in').onclick=()=>setZoom(zoom+.25);
document.getElementById('zoom-out').onclick=()=>setZoom(zoom-.25);
document.getElementById('fit').onclick=()=>{setZoom(1);viewport.scrollTo(0,0);output.textContent='Vừa màn hình'};
document.getElementById('actual').onclick=()=>setZoom(${bounds.w}/viewport.clientWidth);
document.getElementById('print').onclick=()=>window.print();
function selectTable(name){document.querySelectorAll('.entity').forEach(table=>{table.classList.toggle('selected',table.dataset.table===name);table.classList.remove('related')});document.querySelectorAll('.relationship').forEach(edge=>{const active=edge.dataset.from===name||edge.dataset.to===name;edge.classList.toggle('active',active);if(active){document.getElementById('table-'+edge.dataset.from).classList.add('related');document.getElementById('table-'+edge.dataset.to).classList.add('related')}})}
document.querySelectorAll('.entity').forEach(table=>{table.addEventListener('click',()=>selectTable(table.dataset.table));table.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectTable(table.dataset.table)}})});
let drag=null;
viewport.addEventListener('pointerdown',event=>{if(event.target.closest('.entity')||event.button!==0)return;drag={x:event.clientX,y:event.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(event.pointerId);viewport.classList.add('dragging');selectTable(null)});
viewport.addEventListener('pointermove',event=>{if(drag){viewport.scrollLeft=drag.left+drag.x-event.clientX;viewport.scrollTop=drag.top+drag.y-event.clientY}});
function endDrag(){drag=null;viewport.classList.remove('dragging')}
viewport.addEventListener('pointerup',endDrag);viewport.addEventListener('pointercancel',endDrag);
</script>
</body>
</html>`;
writeFileSync(resolve(root, 'data/erd.html'), html, 'utf8');
console.log(`Created data/erd.html: ${tables.length} tables, ${edges.length} field-to-field relationships.`);
