import re

from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse


class TabSessionMiddleware(SessionMiddleware):
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await super().__call__(scope, receive, send)
        headers = dict(scope.get('headers', []))
        browser = b'sec-fetch-mode' in headers
        tab_request = headers.get(b'x-neu-tab', b'') == b'1'
        asset = scope['path'].startswith(('/static/', '/media/'))
        protected = (scope['path'].startswith('/admin') and scope['path'] != '/admin/login') or scope['path'].startswith(('/account', '/checkout', '/orders', '/payments', '/contracts'))
        if browser and protected and not asset and headers.get(b'sec-fetch-dest') == b'document' and scope['method'] == 'GET':
            shell = HTMLResponse('<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NEU SHOP</title><script src="/static/tab-session.js" defer></script></head><body><p>Đang mở NEU SHOP…</p><noscript>Bật JavaScript để sử dụng phiên đăng nhập riêng cho từng tab.</noscript></body></html>', headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; base-uri 'self'; frame-ancestors 'none'"})
            return await shell(scope, receive, send)
        if browser or tab_request:
            # Browser sessions travel only in a per-tab header, never the shared cookie.
            token = headers.get(b'x-neu-tab-session', b'')
            cookies = [part.strip() for part in headers.get(b'cookie', b'').split(b';') if part.strip() and not part.strip().startswith(self.session_cookie.encode()+b'=')]
            if token and token != b'null':
                cookies.append(self.session_cookie.encode()+b'='+token)
            scope = {**scope, 'headers':[(key,value) for key,value in scope['headers'] if key.lower()!=b'cookie'] + [(b'cookie', b'; '.join(cookies))]}

            initial_document = browser and not tab_request and headers.get(b'sec-fetch-dest') == b'document'
            html_response = False

            async def send_tab(message):
                nonlocal html_response
                if message['type']=='http.response.start':
                    clean=[]
                    for key,value in message.get('headers',[]):
                        if key.lower()==b'set-cookie' and value.startswith(self.session_cookie.encode()+b'='):
                            clean.append((b'x-neu-tab-session',value.split(b';',1)[0].split(b'=',1)[1]))
                        else:
                            clean.append((key,value))
                    html_response = initial_document and any(key.lower()==b'content-type' and b'text/html' in value for key,value in clean)
                    if html_response:
                        clean = [(key,value) for key,value in clean if key.lower()!=b'content-length']
                    location=next((value for key,value in clean if key.lower()==b'location'),None)
                    if tab_request and message['status'] in (301,302,303,307,308) and location:
                        clean=[(key,value) for key,value in clean if key.lower()!=b'location']
                        clean.append((b'x-neu-redirect',location))
                        clean.append((b'x-neu-redirect-status',str(message['status']).encode()))
                        message['status']=200
                    message['headers']=clean
                if message['type']=='http.response.body' and html_response:
                    message['body'] = re.sub(rb'<script\b(?![^>]*src="/static/tab-session.js")[^>]*>.*?</script>', b'', message.get('body',b''), flags=re.S)
                await send(message)
            return await super().__call__(scope, receive, send_tab)
        return await super().__call__(scope, receive, send)
