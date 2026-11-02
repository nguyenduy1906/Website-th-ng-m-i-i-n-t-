import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / 'app/static/fonts'
CSS_URL = 'https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'


if __name__ == '__main__':
    request = urllib.request.Request(CSS_URL, headers={'User-Agent': USER_AGENT})
    css = urllib.request.urlopen(request, timeout=30).read().decode()
    DIRECTORY.mkdir(exist_ok=True)
    output = ['@charset "UTF-8";', '']
    for subset, block in re.findall(r'/\* ([^*]+) \*/\s*(@font-face\s*\{[^}]+\})', css):
        if subset not in ('vietnamese', 'latin'):
            continue
        url = re.search(r'url\(([^)]+)\)', block).group(1)
        weight = re.search(r'font-weight:\s*(\d+)', block).group(1)
        filename = f'be-vietnam-pro-{subset}-{weight}.woff2'
        response = urllib.request.urlopen(url, timeout=30).read()
        if response[:4] != b'wOF2':
            raise ValueError('Expected WOFF2 font data')
        (DIRECTORY / filename).write_bytes(response)
        output.append(block.replace(url, '/static/fonts/' + filename))
    if len(output) != 10:
        raise ValueError('Expected eight font faces (four weights, two subsets)')
    (DIRECTORY / 'be-vietnam-pro.css').write_text('\n\n'.join(output) + '\n', encoding='utf-8')
    license_url = 'https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/OFL.txt'
    (DIRECTORY / 'OFL-BeVietnamPro.txt').write_bytes(urllib.request.urlopen(license_url, timeout=30).read())
    print(f'Saved {len(output)-2} local font faces with SIL Open Font License.')
