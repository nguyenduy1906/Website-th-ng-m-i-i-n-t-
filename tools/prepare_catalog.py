import concurrent.futures
import hashlib
import html
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = {
    'cpu': 'CPU', 'laptop_ram': 'RAM', 'o_cung_laptop': 'Ổ cứng',
    'vga': 'Đồ họa', 'display_size': 'Màn hình', 'display_resolution': 'Độ phân giải',
    'laptop_tan_so_quet': 'Tần số quét', 'chipset': 'Chip xử lý',
    'ram': 'RAM', 'memory_internal': 'RAM', 'internal_memory': 'Bộ nhớ trong', 'storage': 'Bộ nhớ trong', 'battery': 'Pin',
    'os_version': 'Hệ điều hành', 'product_weight': 'Khối lượng',
    'dimensions': 'Kích thước', 'bluetooth': 'Bluetooth', 'wlan': 'Wi-Fi',
    'am_thanh_cong_nghe_am_thanh': 'Công nghệ âm thanh',
    'tai_nghe_cong_sac': 'Cổng sạc', 'tai_nghe_thoi_luong_dung_pin': 'Thời lượng pin',
    'tai_nghe_bluetooth': 'Bluetooth', 'tai_nghe_ket_noi': 'Kết nối',
    'tai_nghe_dinh_dang_am_thanh': 'Định dạng âm thanh', 'tai_nghe_loa': 'Màng loa',
    'chuot_ban_phim_ket_noi': 'Kết nối', 'chuot_bp_ket_noi': 'Kết nối',
    'chuot_ban_phim_pin': 'Pin', 'ban_phim_so_phim': 'Số phím',
    'chuot_bp_tuong_thich': 'Tương thích',
}


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', str(value)))).strip()


def prepare(product):
    directory = ROOT / 'app/static/images/catalog'
    directory.mkdir(parents=True, exist_ok=True)
    existing = list(directory.glob(product['source_id'] + '.*'))
    target = existing[0] if existing else directory / (product['source_id'] + '.png')
    for attempt in range(3):
        try:
            if target.exists():
                content = target.read_bytes()
            else:
                request = urllib.request.Request(product['image_url'], headers={'User-Agent': 'NEU-Shop-local-demo/1.0'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    content = response.read(8_000_001)
            extension = '.png' if content.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if content.startswith(b'\xff\xd8\xff') else '.webp' if content[:4] == b'RIFF' and content[8:12] == b'WEBP' else None
            if len(content) > 8_000_000 or not extension:
                raise ValueError('Expected a PNG, JPEG or WebP image')
            target = target.with_suffix(extension)
            target.write_bytes(content)
            attributes = product.pop('attributes')
            product['specs'] = '\n'.join(f'{label}: {clean(attributes[key])}' for key, label in FIELDS.items() if attributes.get(key) and isinstance(attributes[key], (str, int, float)))
            product['summary'] = clean(attributes.get('additional_information') or product['name'])[:500]
            product['media'] = '/static/images/catalog/' + target.name
            product['image_sha256'] = hashlib.sha256(content).hexdigest()
            product['stock'] = 20
            product['storage'] = clean(attributes.get('laptop_ram') or attributes.get('ram') or attributes.get('memory_internal') or '')
            drive = clean(attributes.get('hdd_sdd') or attributes.get('internal_memory') or attributes.get('storage') or '')
            product['storage'] = ' / '.join(filter(None, [product['storage'], drive])) or 'Theo cấu hình công bố'
            product['color'] = 'Theo ảnh sản phẩm'
            return product
        except Exception as error:
            if attempt == 2:
                print(f"Skipped {product['source_id']}: {error}", flush=True)
                return None
            time.sleep(2)


if __name__ == '__main__':
    candidates = json.loads((ROOT / 'data/catalog-candidates.json').read_text(encoding='utf-8'))['products']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        products = [p for p in pool.map(prepare, candidates) if p]
    output = {'source': 'CellphoneS', 'mode': 'local-demo', 'products': products}
    (ROOT / 'docs/catalog-real.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prepared {len(products)} real products with local verified image signatures.', flush=True)
