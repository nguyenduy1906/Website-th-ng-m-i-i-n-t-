import http.cookiejar
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parent.parent


class Browser:
    def __init__(self, base):
        self.base = base
        self.opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.html = ""
        self.url = ""
        self.csrf = None

    def request(self, path, data=None):
        body = urlencode(data, doseq=True).encode() if data is not None else None
        request = Request(self.base + path, data=body)
        try:
            response = self.opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        self.html = response.read().decode()
        self.url = response.url
        code = response.code
        response.close()
        token = re.search(r'name="csrf" value="([^"]+)"', self.html)
        if token:
            self.csrf = token[1]
        return code

    def get(self, path):
        return self.request(path)

    def token(self, name="csrf"):
        if name == "csrf" and self.csrf:
            return self.csrf
        match = re.search(r'name="' + name + r'" value="([^"]+)"', self.html)
        if not match:
            raise AssertionError(f"Missing {name} on {self.url}: {self.html[:200]}")
        return match[1]

    def post(self, path, **data):
        if "csrf" not in data:
            data["csrf"] = self.token()
        return self.request(path, data)


class ShopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_root = ROOT / "test-results"
        test_root.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="neu-tests-", dir=test_root)
        assert Path(cls.temp.name).resolve().is_relative_to(test_root.resolve())
        cls.database = str(Path(cls.temp.name) / "test.db")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        environment = {**os.environ, "NEU_DB_PATH": cls.database, "NEU_SESSION_SECRET": "isolated-integration-test-secret"}
        cls.log = open(Path(cls.temp.name) / "server.log", "w+", encoding="utf-8")
        cls.server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(cls.port)], cwd=ROOT, env=environment, stdout=cls.log, stderr=cls.log)
        for _ in range(100):
            try:
                with urlopen(cls.base + "/api/health", timeout=.5) as response:
                    if response.status == 200:
                        return
            except (URLError, OSError):
                time.sleep(.1)
        cls.server.terminate()
        cls.server.wait(timeout=10)
        cls.log.seek(0)
        log = cls.log.read()
        cls.log.close()
        cls.temp.cleanup()
        raise RuntimeError(log or "Local test server did not start; check loopback permissions.")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)
        cls.log.close()
        cls.temp.cleanup()

    def setUp(self):
        self.browser = Browser(self.base)

    def query(self, sql, params=()):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.row_factory = sqlite3.Row
            return db.execute(sql, params).fetchall()

    def test_admin_low_stock_excludes_archived_products(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            product = db.execute("INSERT INTO products(name,category,price,stock,summary,description,specs,active) VALUES('ARCHIVED_LOW_STOCK_CHECK','laptop',1000,1,'Fixture','Fixture description','RAM: 8GB',0)").lastrowid
            variant = db.execute("INSERT INTO variants(product_id,sku,color,price,stock) VALUES(?,'ARCHIVED-LOW-CHECK','Xám',1000,1)", (product,)).lastrowid
        try:
            self.browser = self.login_admin()
            self.assertEqual(self.browser.get('/admin/inventory?low=1'), 200)
            self.assertNotIn('ARCHIVED_LOW_STOCK_CHECK', self.browser.html)
            expected = self.query('SELECT COUNT(*) AS count FROM variants v JOIN products p ON p.id=v.product_id WHERE v.active=1 AND p.active=1 AND v.stock<=5')[0]['count']
            self.assertEqual(self.browser.get('/admin'), 200)
            count = re.search(r'Biến thể tồn kho thấp.*?<strong>(\d+)</strong>', self.browser.html, re.S)
            self.assertIsNotNone(count)
            self.assertEqual(int(count[1]), expected)
        finally:
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute('DELETE FROM variants WHERE id=?', (variant,))
                db.execute('DELETE FROM products WHERE id=?', (product,))


    def register(self, browser=None, verify=True):
        browser = browser or self.browser
        browser.get('/register')
        email = f'test-{time.time_ns()}@example.com'
        self.assertEqual(browser.post('/register', name='Nguyễn Demo', email=email, password='Password123', confirm='Password123'), 200)
        self.assertTrue(browser.url.endswith('/verify'))
        if verify:
            code = re.search(r'id="demo-otp">(\d{6})', browser.html)[1]
            self.assertEqual(browser.post('/verify', code=code), 200)
            self.assertTrue(browser.url.endswith('/account'))
        return email

    def login_admin(self):
        admin = Browser(self.base)
        admin.get('/admin/login')
        self.assertEqual(admin.post('/login', email='admin@neushop.local', password='Admin@12345', portal='admin'), 200)
        self.assertTrue(admin.url.endswith('/admin'))
        return admin

    def test_admin_personal_profile_and_password(self):
        admin = self.login_admin()
        old = self.query("SELECT * FROM users WHERE email='admin@neushop.local'")[0]
        try:
            self.assertEqual(admin.get('/admin/profile'), 200)
            self.assertIn('href="/admin/profile?edit=true"', admin.html)
            self.assertIn('class="admin-rail-logout"', admin.html)
            self.assertNotIn('Không có giao dịch thực', admin.html)
            self.assertEqual(admin.post('/admin/profile', name='A', phone='abc', gender='invalid'), 400)
            self.assertEqual(admin.post('/admin/profile', name='Quản trị cá nhân', phone='0912345678', birth_date='1995-01-02', gender='Nam', role='customer', email='changed@example.com'), 200)
            updated = self.query('SELECT * FROM users WHERE id=?', (old['id'],))[0]
            self.assertEqual(updated['name'], 'Quản trị cá nhân')
            self.assertEqual(updated['email'], old['email'])
            self.assertEqual(updated['role'], 'admin')
            other = self.login_admin()
            self.assertEqual(admin.post('/admin/profile/password', current_password='wrong', password='NewPassword123', confirm='NewPassword123'), 400)
            self.assertEqual(admin.post('/admin/profile/password', current_password='Admin@12345', password='NewPassword123', confirm='NewPassword123'), 200)
            self.assertTrue(admin.url.endswith('/admin/profile'))
            other.get('/admin/profile')
            self.assertTrue(other.url.endswith('/admin/login'))
            self.assertEqual(admin.post('/logout'), 200)
            self.assertTrue(admin.url.endswith('/admin/login'))
            admin.get('/admin/profile')
            self.assertTrue(admin.url.endswith('/admin/login'))
            customer = Browser(self.base)
            self.register(customer)
            self.assertEqual(customer.get('/admin/profile'), 403)
            self.assertEqual(customer.post('/admin/profile', name='Unauthorized'), 403)
        finally:
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute('UPDATE users SET name=?,phone=?,birth_date=?,gender=?,password=?,auth_rev=? WHERE id=?', (old['name'], old['phone'], old['birth_date'], old['gender'], old['password'], old['auth_rev'], old['id']))

    def test_admin_session_stays_in_admin_portal(self):
        admin = self.login_admin()
        for path in ('/', '/products', '/products/1', '/cart', '/checkout', '/account/profile', '/account/security', '/news', '/login', '/administer'):
            with self.subTest(path=path):
                self.assertEqual(admin.get(path), 200)
                self.assertTrue(admin.url.endswith('/admin'))
                self.assertNotIn('href="/"', admin.html)
                self.assertNotIn('href="/account/', admin.html)
        for path, fields in (('/cart/add', {'variant_id': 2, 'quantity': 1}), ('/checkout', {}), ('/contact', {}), ('/api/chatbot', {'q': 'hi'})):
            with self.subTest(path=path):
                self.assertEqual(admin.post(path, **fields), 403)
        self.assertEqual(admin.get('/api/health'), 200)
        self.assertEqual(admin.post('/logout'), 200)
        self.assertTrue(admin.url.endswith('/admin/login'))
        self.assertRegex(admin.html, r'class="auth-layout(?: |")')

    def test_shared_login_routes_by_account_role(self):
        admin = Browser(self.base)
        self.assertEqual(admin.get('/login'), 200)
        self.assertEqual(admin.post('/login', email='admin@neushop.local', password='wrong'), 400)
        self.assertRegex(admin.html, r'class="auth-layout(?: |")')
        self.assertEqual(admin.post('/login', email='admin@neushop.local', password='Admin@12345'), 200)
        self.assertTrue(admin.url.endswith('/admin'))
        customer = Browser(self.base)
        email = self.register(customer)
        customer.post('/logout')
        self.assertEqual(customer.get('/admin/login'), 200)
        self.assertRegex(customer.html, r'class="auth-layout(?: |")')
        self.assertEqual(customer.post('/login', email=email, password='Password123'), 200)
        self.assertTrue(customer.url.endswith('/account'))
        self.assertEqual(customer.get('/admin/profile'), 403)

    def make_order(self, product_id=2, quantity=1, method='cod', voucher='', shipping='standard'):
        self.register()
        self.browser.get(f'/products/{product_id}')
        variant = self.query('SELECT id FROM variants WHERE product_id=? ORDER BY id LIMIT 1', (product_id,))[0]['id']
        self.assertEqual(self.browser.post('/cart/add', variant_id=variant, quantity=quantity), 200)
        self.browser.get('/checkout')
        key = self.browser.token('checkout_key')
        data = {'csrf':self.browser.token(),'checkout_key':key,'recipient':'Nguyễn Demo','phone':'0912345678','address':'12 Đường Demo, Hà Nội','note':'Đơn kiểm thử','payment_method':method,'shipping_method':shipping,'voucher':voucher}
        self.assertEqual(self.browser.request('/checkout',data),200)
        order = self.query('SELECT * FROM orders WHERE checkout_key=?',(key,))[0]
        return order, data

    def complete(self, order_id, admin=None):
        self.confirm_contract(order_id)
        admin = admin or self.login_admin()
        admin.get(f'/admin/orders/{order_id}')
        for status in ('Đang chuẩn bị','Đang giao','Hoàn tất'):
            self.assertEqual(admin.post(f'/admin/orders/{order_id}/status',status=status),200)
        return admin

    def confirm_contract(self, order_id):
        contract = self.query('SELECT * FROM sales_contracts WHERE order_id=?', (order_id,))[0]
        if contract['status'] == 'signed':
            return
        self.browser.get(f"/contracts/{contract['id']}")
        self.assertEqual(self.browser.post(f"/contracts/{contract['id']}/otp"), 200)
        code = re.search(r'id="contract-demo-otp">(\d{6})', self.browser.html)[1]
        name = json.loads(contract['snapshot'])['buyer']['name']
        self.assertEqual(self.browser.post(f"/contracts/{contract['id']}/sign", signer_name=name, code=code, consent='1'), 200)

    def test_checkout_contract_before_payment_and_admin_approval(self):
        for method in ('cod', 'qr', 'card', 'wallet'):
            with self.subTest(method=method):
                order, data = self.make_order(product_id=8, method=method)
                contract = self.query('SELECT * FROM sales_contracts WHERE order_id=?', (order['id'],))[0]
                self.assertTrue(self.browser.url.endswith(f"/contracts/{contract['id']}"))
                self.assertEqual(contract['status'], 'draft')
                self.assertIn('Hợp đồng mua hàng điện tử', self.browser.html)
                self.assertEqual(self.browser.request('/checkout', data), 200)
                self.assertTrue(self.browser.url.endswith(f"/contracts/{contract['id']}"))
                self.assertEqual(len(self.query('SELECT id FROM sales_contracts WHERE order_id=?', (order['id'],))), 1)
                admin = self.login_admin()
                self.assertEqual(admin.post(f"/admin/orders/{order['id']}/status", status='Đang chuẩn bị'), 409 if method == 'cod' else 400)
                payment = self.query('SELECT * FROM payments WHERE order_id=?', (order['id'],))[0]
                if method != 'cod':
                    self.assertEqual(self.browser.get(f"/payments/{payment['id']}"), 200)
                    self.assertTrue(self.browser.url.endswith(f"/contracts/{contract['id']}"))
                    self.assertEqual(self.browser.post(f"/payments/{payment['id']}/simulate", result='success'), 409)
                    self.assertEqual(self.browser.post(f"/orders/{order['id']}/pay"), 409)
                    self.assertEqual(self.browser.post(f"/orders/{order['id']}/pay", method='cod'), 409)
                    self.assertEqual(self.query('SELECT status FROM payments WHERE id=?', (payment['id'],))[0]['status'], 'Chờ thanh toán')
                self.confirm_contract(order['id'])
                if method != 'cod':
                    self.assertIn('Tiếp tục thanh toán', self.browser.html)
                    self.assertEqual(self.browser.get(f"/payments/{payment['id']}"), 200)
                    self.assertEqual(self.browser.post(f"/payments/{payment['id']}/simulate", result='success'), 200)
                self.assertEqual(admin.post(f"/admin/orders/{order['id']}/status", status='Đang chuẩn bị'), 200)

    def test_contract_void_or_tampering_blocks_payment_and_approval(self):
        for method in ('cod', 'qr'):
            for tamper in (False, True):
                with self.subTest(method=method, tamper=tamper):
                    order, _ = self.make_order(product_id=8, method=method)
                    self.confirm_contract(order['id'])
                    if tamper:
                        self.query("UPDATE sales_contracts SET snapshot=snapshot||' ' WHERE order_id=?", (order['id'],))
                    else:
                        self.query("UPDATE sales_contracts SET status='void' WHERE order_id=?", (order['id'],))
                    admin = self.login_admin()
                    if method == 'cod':
                        self.assertEqual(admin.post(f"/admin/orders/{order['id']}/status", status='Đang chuẩn bị'), 409)
                    else:
                        payment = self.query('SELECT id FROM payments WHERE order_id=?', (order['id'],))[0]
                        self.assertEqual(self.browser.post(f"/payments/{payment['id']}/simulate", result='success'), 409)
                    self.assertEqual(self.browser.post(f"/orders/{order['id']}/cancel"), 200)

    def multipart(self,browser,path,fields,filename,content):
        boundary='----NEUIntegrationTestBoundary'
        body=b''
        fields={'csrf':browser.token(),**fields}
        for name,value in fields.items():
            body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode()+content+f'\r\n--{boundary}--\r\n'.encode()
        req=Request(browser.base+path,data=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
        try:
            response=browser.opener.open(req,timeout=15)
        except HTTPError as error:
            response=error
        browser.html=response.read().decode();browser.url=response.url;code=response.code;response.close()
        token=re.search(r'name="csrf" value="([^"]+)"',browser.html)
        if token:browser.csrf=token[1]
        return code

    def test_public_pages_and_template_separation(self):
        for path in ('/','/products','/products/1','/cart','/offers','/news','/news/1','/policies','/login','/register','/forgot-password','/admin/login','/api/health'):
            with self.subTest(path=path):self.assertEqual(self.browser.get(path),200)
        self.assertEqual(self.browser.get('/compare'),404)
        self.assertEqual(self.browser.post('/compare',product_id=1),404)
        self.assertFalse(list((ROOT/'app/templates').glob('*.html')))
        self.assertTrue((ROOT/'app/templates/customer/base.html').exists())
        self.assertTrue((ROOT/'app/templates/admin/base.html').exists())

    def test_portal_contact_receipt_reply_and_rate_limit(self):
        guest=Browser(self.base)
        self.assertEqual(guest.get('/contact'),200)
        self.assertEqual(guest.post('/contact',name='Khách liên hệ',email='invalid',content=''),400)
        self.assertIn('Khách liên hệ',guest.html)
        payload={'name':'Khách liên hệ','email':'contact@example.test','phone':'0912345678','address':'Địa chỉ thử nghiệm','content':'Tôi cần tư vấn cấu hình máy tính phù hợp.'}
        self.assertEqual(guest.post('/contact',**payload),200)
        receipt_path=guest.url.removeprefix(self.base)
        self.assertTrue(receipt_path.startswith('/contact/requests/'))
        row=self.query('SELECT * FROM contact_requests WHERE receipt=?',(receipt_path.split('/')[-1],))[0]
        self.assertNotIn(row['visitor_key'],guest.html)
        self.assertEqual(guest.post('/contact',**payload),429)
        admin=self.login_admin()
        self.assertEqual(admin.post(f"/admin/contact/{row['id']}",status='replied',response='Bạn có thể so sánh ba cấu hình ngay trên website.'),200)
        self.assertEqual(guest.get(receipt_path),200)
        self.assertIn('so sánh ba cấu hình',guest.html)
        self.assertEqual(guest.get('/contact/requests/not-a-valid-receipt'),404)
        outsider=Browser(self.base);outsider.get('/admin/contact')
        self.assertTrue(outsider.url.endswith('/admin/login'))

    def test_portal_settings_markdown_topics_and_news(self):
        admin=self.login_admin()
        self.assertEqual(admin.post('/admin/settings',shop_name='NEU SHOP',facebook='javascript:alert(1)'),400)
        self.assertEqual(admin.post('/admin/settings',shop_name='NEU SHOP',tagline='Công nghệ demo',email='shop@example.test',hotline='0912345678',address='Địa chỉ kiểm thử',map_query='Hà Nội',facebook='https://www.facebook.com/example',show_statistics='1'),200)
        body='## Sứ mệnh\nThông tin **rõ ràng**, dễ tìm kiếm.\n\n<script>alert(1)</script>\n- Dòng minh họa'
        self.assertEqual(admin.post('/admin/pages/about',title='Giới thiệu NEU SHOP',summary='Giới thiệu website công nghệ demo local.',body=body,active='1'),200)
        self.assertEqual(self.browser.get('/about'),200)
        self.assertIn('<strong>rõ ràng</strong>',self.browser.html)
        self.assertNotIn('<script>alert(1)</script>',self.browser.html)
        self.assertIn('&lt;script&gt;',self.browser.html)
        self.assertEqual(admin.post('/admin/content/preview',content=body),200)
        self.assertNotIn('<script>',json.loads(admin.html)['html'])
        topic='Chủ đề kiểm thử '+str(time.time_ns())
        self.assertEqual(admin.post('/admin/topics',name=topic),200)
        topic_id=self.query('SELECT id FROM article_topics WHERE name=?',(topic,))[0]['id']
        article_ids=[]
        for number in (1,2):
            self.assertEqual(admin.post('/admin/content',title=f'Bài kiểm thử chủ đề {number}',summary='Tóm tắt nội dung bài viết kiểm thử.',content='## Thông tin\nNội dung hướng dẫn chi tiết trong bản demo.',topic_id=topic_id),200)
            article_ids.append(self.query('SELECT MAX(id) AS id FROM articles')[0]['id'])
        self.assertEqual(self.browser.get(f'/news?topic={topic_id}'),200)
        self.assertIn('Bài kiểm thử chủ đề 1',self.browser.html)
        self.assertEqual(self.browser.get(f'/news/{article_ids[0]}'),200)
        self.assertIn(f'/news/{article_ids[1]}',self.browser.html)
        self.assertEqual(admin.post('/admin/topics',id=topic_id,name=topic),200)
        self.assertEqual(self.browser.get(f'/news/{article_ids[0]}'),404)
        self.assertEqual(admin.post(f'/admin/content/articles/{article_ids[0]}/delete'),200)
        self.assertFalse(self.query('SELECT id FROM articles WHERE id=?',(article_ids[0],)))

    def test_portal_two_level_categories_and_archive(self):
        admin=self.login_admin()
        slug='test-child-'+str(time.time_ns())[-10:]
        self.assertEqual(admin.post('/admin/catalog',kind='category',slug=slug,name='Nhóm laptop kiểm thử',parent_slug='laptop'),200)
        self.assertEqual(admin.post('/admin/catalog',kind='category',slug=slug+'-bad',name='Cấp ba không hợp lệ',parent_slug=slug),400)
        original=self.query('SELECT subcategory FROM products WHERE id=1')[0]['subcategory']
        try:
            self.query('UPDATE products SET subcategory=? WHERE id=1',(slug,))
            self.assertEqual(self.browser.get('/products?category='+slug),200)
            self.assertIn('NEU Book Air 14',self.browser.html)
            self.assertEqual(admin.post('/catalog/not-real',kind='category'),403)
            self.assertEqual(admin.post('/admin/catalog/visibility',kind='category',id=slug),200)
            self.assertEqual(self.browser.get('/products/1'),404)
            self.assertEqual(admin.post('/admin/catalog/visibility',kind='category',id=slug),200)
        finally:
            self.query('UPDATE products SET subcategory=? WHERE id=1',(original,))
        self.assertEqual(admin.post(f'/admin/catalog/category/{slug}/delete'),200)
        self.assertEqual(admin.post('/admin/products/8/archive'),200)
        self.assertEqual(self.browser.get('/products/8'),404)
        self.assertEqual(admin.get('/admin/archive'),200)
        self.assertIn('NEU Hub Connect',admin.html)
        self.assertEqual(admin.post('/admin/products/8/restore'),200)
        self.assertEqual(self.browser.get('/products/8'),404)
        self.assertEqual(admin.post('/admin/products/8/visibility'),200)
        self.assertEqual(self.browser.get('/products/8'),200)

    def contract_fixture(self):
        order,_=self.make_order(product_id=8)
        self.assertEqual(self.browser.post(f"/orders/{order['id']}/contract"),200)
        contract=self.query('SELECT * FROM sales_contracts WHERE order_id=?',(order['id'],))[0]
        self.assertEqual(self.browser.post(f"/contracts/{contract['id']}/otp"),200)
        code=re.search(r'id="contract-demo-otp">(\d{6})',self.browser.html)[1]
        return order,contract,code

    def test_portal_contract_sign_snapshot_privacy_and_export(self):
        order,contract,code=self.contract_fixture()
        cid=contract['id']
        self.assertEqual(self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1'),200)
        signed=self.query('SELECT * FROM sales_contracts WHERE id=?',(cid,))[0]
        self.assertEqual(signed['status'],'signed')
        self.assertEqual(signed['snapshot'],contract['snapshot'])
        self.assertEqual(signed['document_hash'],contract['document_hash'])
        self.assertEqual(signed['otp_demo_code'],'')
        self.assertEqual(self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1'),200)
        self.assertEqual(len(self.query("SELECT * FROM contract_events WHERE contract_id=? AND action='signed'",(cid,))),1)
        self.query("UPDATE users SET name='Tên tài khoản đã đổi' WHERE id=?",(order['user_id'],))
        for path in (f'/contracts/{cid}/print',f'/contracts/{cid}/download'):
            self.assertEqual(self.browser.get(path),200)
            self.assertIn('Nguyễn Demo',self.browser.html)
            self.assertNotIn('Tên tài khoản đã đổi',self.browser.html)
        outsider=Browser(self.base);self.register(outsider)
        self.assertEqual(outsider.get(f'/contracts/{cid}'),404)
        self.assertEqual(outsider.get(f'/contracts/{cid}/download'),404)
        self.assertEqual(outsider.post(f'/contracts/{cid}/otp'),404)
        admin=self.login_admin()
        self.assertEqual(admin.get(f'/admin/contracts/{cid}'),200)
        self.assertEqual(admin.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1'),403)
        for suffix in ('download', 'print'):
            self.assertEqual(admin.get(f'/admin/contracts/{cid}/{suffix}'), 200)
            self.assertIn(contract['number'], admin.html)
            self.assertNotIn('href="/contracts/', admin.html)
            self.assertEqual(outsider.get(f'/admin/contracts/{cid}/{suffix}'), 403)

    def test_portal_contract_otp_session_expiry_attempt_limit(self):
        order,contract,code=self.contract_fixture();cid=contract['id']
        email=self.query('SELECT email FROM users WHERE id=?',(order['user_id'],))[0]['email']
        other_session=Browser(self.base);other_session.get('/login');other_session.post('/login',email=email,password='Password123')
        self.assertEqual(other_session.get(f'/contracts/{cid}'),200)
        self.assertNotIn('id="contract-demo-otp"',other_session.html)
        other_session.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1')
        self.assertEqual(self.query('SELECT status FROM sales_contracts WHERE id=?',(cid,))[0]['status'],'draft')
        wrong='000000' if code!='000000' else '999999'
        for _ in range(5):self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=wrong,consent='1')
        self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1')
        self.assertEqual(self.query('SELECT otp_attempts FROM sales_contracts WHERE id=?',(cid,))[0]['otp_attempts'],5)
        self.query('UPDATE sales_contracts SET otp_sent_at=0 WHERE id=?',(cid,))
        self.browser.post(f'/contracts/{cid}/otp')
        new_code=re.search(r'id="contract-demo-otp">(\d{6})',self.browser.html)[1]
        self.query('UPDATE sales_contracts SET otp_expires_at=0 WHERE id=?',(cid,))
        self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=new_code,consent='1')
        self.assertEqual(self.query('SELECT status FROM sales_contracts WHERE id=?',(cid,))[0]['status'],'draft')

    def test_portal_contract_cancel_voids_and_tamper_blocks(self):
        order,contract,code=self.contract_fixture();cid=contract['id']
        self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1')
        self.assertEqual(self.browser.post(f"/orders/{order['id']}/cancel"),200)
        row=self.query('SELECT * FROM sales_contracts WHERE id=?',(cid,))[0]
        self.assertEqual(row['status'],'void')
        self.assertTrue(row['signed_at'])
        self.assertEqual(row['snapshot'],contract['snapshot'])
        self.assertEqual(self.browser.post(f'/contracts/{cid}/sign',signer_name='Nguyễn Demo',code=code,consent='1'),409)
        self.query("UPDATE sales_contracts SET snapshot=snapshot||' ' WHERE id=?",(cid,))
        self.assertEqual(self.browser.get(f'/contracts/{cid}/download'),409)

    def test_portal_visitor_counts_and_heartbeat(self):
        guest=Browser(self.base)
        guest.get('/api/visits/stats');before=json.loads(guest.html)
        guest.get('/about');guest.get('/services')
        guest.get('/api/visits/stats');after=json.loads(guest.html)
        self.assertEqual(after['views'],before['views']+2)
        self.assertEqual(after['visitors'],before['visitors']+1)
        self.assertGreaterEqual(after['online'],1)
        self.assertEqual(guest.post('/api/visits/heartbeat'),200)
        self.assertEqual(guest.post('/api/visits/heartbeat',csrf='invalid'),403)

    def test_every_admin_page_renders(self):
        admin=self.login_admin()
        for path in ('/admin','/admin/products','/admin/products/new','/admin/products/1/edit','/admin/orders','/admin/catalog','/admin/inventory','/admin/vouchers','/admin/users','/admin/returns','/admin/content','/admin/support','/admin/reports','/admin/logs'):
            with self.subTest(path=path):self.assertEqual(admin.get(path),200)

    def test_customer_pages_and_profile_addresses(self):
        self.register()
        for section in ('overview','profile','addresses','security','orders','notifications','support'):
            path='/account' if section=='overview' else '/account/'+section
            with self.subTest(path=path):self.assertEqual(self.browser.get(path),200)
        self.assertEqual(self.browser.post('/account/profile',name='Tên cập nhật',phone='0912345678',birth_date='2000-01-01',gender='Nam'),200)
        self.browser.get('/account/addresses')
        self.assertEqual(self.browser.post('/account/addresses',recipient='Nguyễn Demo',phone='0912345678',address='12 Đường Demo, Hà Nội',is_default=1),200)
        self.assertIn('12 Đường Demo',self.browser.html)
        self.assertIn('Mặc định',self.browser.html)

    def test_registration_otp_and_duplicate(self):
        self.browser.get('/register')
        self.assertEqual(self.browser.post('/register',name='x',email='bad',password='short',confirm='different'),400)
        email=self.register(verify=False)
        self.assertEqual(self.browser.post('/verify',code='invalid'),400)
        code=re.search(r'id="demo-otp">(\d{6})',self.browser.html)[1]
        self.assertEqual(self.browser.post('/verify',code=code),200)
        self.browser.get('/register')
        self.assertEqual(self.browser.post('/register',name='Demo Two',email=email,password='Password123',confirm='Password123'),400)

    def test_otp_five_attempt_limit(self):
        self.register(verify=False)
        code=re.search(r'id="demo-otp">(\d{6})',self.browser.html)[1]
        for _ in range(5):self.assertEqual(self.browser.post('/verify',code='invalid'),400)
        self.assertEqual(self.browser.post('/verify',code=code),400)
        self.assertIn('quá 5 lần',self.browser.html)

    def test_password_reset_and_two_factor(self):
        email=self.register()
        self.browser.get('/account/security')
        self.assertEqual(self.browser.post('/account/security',current_password='Password123',otp_enabled=1),200)
        self.browser.post('/logout')
        self.browser.get('/login')
        self.browser.post('/login',email=email,password='Password123')
        self.assertTrue(self.browser.url.endswith('/verify'))
        code=re.search(r'id="demo-otp">(\d{6})',self.browser.html)[1]
        self.browser.post('/verify',code=code)
        self.browser.get('/forgot-password')
        self.browser.post('/forgot-password',email=email)
        code=re.search(r'id="demo-otp">(\d{6})',self.browser.html)[1]
        self.assertEqual(self.browser.post('/verify',code=code,password='NewPassword456',confirm='NewPassword456'),200)
        self.browser.get('/login')
        self.browser.post('/login',email=email,password='Password123')
        self.assertEqual(self.browser.request('/login',{'csrf':self.browser.token(),'email':email,'password':'Password123'}),400)
        self.assertEqual(self.browser.post('/login',email=email,password='NewPassword456'),200)
        self.assertTrue(self.browser.url.endswith('/verify'))

    def test_search_filter_and_escape(self):
        self.browser.get('/products?q=Book&sort=price_asc')
        self.assertIn('NEU Book Air',self.browser.html)
        self.browser.get('/products?category=phone&max_price=8000000')
        self.assertIn('NEU Phone S1</a>',self.browser.html)
        self.assertNotIn('NEU Phone S1 Plus</a>',self.browser.html)
        self.browser.get('/products?q=nonexistent')
        self.assertIn('Chưa tìm thấy',self.browser.html)
        self.browser.get('/products?'+urlencode({'q':'<script>alert(1)</script>'}))
        self.assertNotIn('<script>alert(1)</script>',self.browser.html)
        self.assertIn('&lt;script&gt;',self.browser.html)
        self.browser.get('/products/1')
        self.browser.get('/api/search?q=Book')
        self.assertGreater(len(json.loads(self.browser.html)),0)

    def test_chatbot_conversation_does_not_match_ai_product_names(self):
        self.browser.get('/')
        for question in ['bạn là ai', 'Bạn là ai?', 'bạn tên gì', 'bạn làm được gì', 'xin chào', 'cảm ơn bạn']:
            with self.subTest(question=question):
                status = self.browser.post('/api/chatbot', q=question, history=json.dumps([{'role':'user','text':'laptop dưới 20 triệu'}]))
                self.assertEqual(status, 200)
                result = json.loads(self.browser.html)
                self.assertEqual(result['products'], [])
                self.assertEqual(result['intent'], 'conversation')
                self.assertNotIn('Thông tin đang có', result['answer'])
        self.browser.get('/')
        self.assertEqual(self.browser.post('/api/chatbot', q='laptop dưới 20 triệu', history='[]'), 200)
        result = json.loads(self.browser.html)
        self.assertTrue(result['products'])
        self.assertTrue(all(product['price'] <= 20000000 for product in result['products']))

    def test_csrf_and_permissions(self):
        self.browser.get('/products/1')
        self.assertEqual(self.browser.request('/cart/add',{'product_id':1,'quantity':1}),403)
        self.assertEqual(self.browser.request('/cart/add',{'csrf':'ký tự','product_id':1}),403)
        self.assertEqual(self.browser.get('/admin'),200)
        self.assertTrue(self.browser.url.endswith('/admin/login'))
        self.register()
        self.assertEqual(self.browser.get('/admin/orders'),403)
        self.assertEqual(self.browser.request('/admin/products/save',{'name':'Hack'}),403)

    def test_cart_variants_and_login_persistence(self):
        email=self.register()
        self.browser.get('/account')
        self.browser.post('/logout')
        variant=self.query('SELECT id FROM variants WHERE product_id=1 ORDER BY id DESC')[0]['id']
        self.browser.get('/products/1')
        self.browser.post('/cart/add',variant_id=variant,quantity=2)
        self.browser.get('/login')
        self.browser.post('/login',email=email,password='Password123')
        self.assertTrue(self.browser.url.endswith('/checkout'))
        self.assertIn('Nâng cấp dung lượng',self.browser.html)
        self.browser.get('/account')
        self.browser.post('/logout')
        self.browser.get('/login');self.browser.post('/login',email=email,password='Password123')
        self.browser.get('/cart')
        self.assertIn('Nâng cấp dung lượng',self.browser.html)
        self.browser.post('/cart/update',variant_id=variant,quantity=1)
        self.assertIn('value="1" min="1"',self.browser.html)
        self.browser.post('/cart/update',variant_id=variant,remove=1)
        self.assertIn('Giỏ hàng đang chờ bạn',self.browser.html)

    def test_checkout_voucher_stock_and_idempotency(self):
        before=self.query('SELECT stock FROM variants WHERE id=2')[0]['stock']
        order,data=self.make_order(voucher='NEU100')
        self.assertEqual(order['discount'],100000)
        self.assertEqual(order['shipping_fee'],30000)
        self.assertEqual(order['total'],order['subtotal']+30000-100000)
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=2')[0]['stock'],before-1)
        self.assertEqual(self.browser.request('/checkout',data),200)
        self.assertEqual(len(self.query('SELECT * FROM orders WHERE checkout_key=?',(data['checkout_key'],))),1)
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=2')[0]['stock'],before-1)

    def test_cart_checkout_only_selected(self):
        self.register();self.browser.get('/products/2')
        self.browser.post('/cart/add',variant_id=2,quantity=1)
        self.browser.post('/cart/add',variant_id=3,quantity=1)
        self.browser.post('/cart/select',items=['2'])
        key=self.browser.token('checkout_key')
        self.browser.post('/checkout',checkout_key=key,recipient='Demo Name',phone='0912345678',address='12 Demo Street, Hà Nội',shipping_method='pickup',payment_method='cod')
        order=self.query('SELECT * FROM orders WHERE checkout_key=?',(key,))[0]
        self.assertEqual(order['shipping_fee'],0)
        self.assertEqual(len(self.query('SELECT * FROM order_items WHERE order_id=?',(order['id'],))),1)
        self.browser.get('/cart')
        self.assertIn('NEU Sound Studio',self.browser.html)

    def test_checkout_validation_preserves_values(self):
        self.register();self.browser.get('/products/2');self.browser.post('/cart/add',variant_id=2,quantity=1);self.browser.get('/checkout')
        self.assertEqual(self.browser.post('/checkout',checkout_key=self.browser.token('checkout_key'),recipient='Tên giữ lại',phone='123',address='abc',voucher='INVALID'),400)
        self.assertIn('value="Tên giữ lại"',self.browser.html)
        self.assertIn('Nhập số điện thoại',self.browser.html)
        self.assertIn('Voucher không hợp lệ',self.browser.html)

    def test_online_failure_retry_success_and_cancel_refund(self):
        order,_=self.make_order(method='qr')
        self.confirm_contract(order['id'])
        self.browser.get(f"/payments/{self.query('SELECT id FROM payments WHERE order_id=?',(order['id'],))[0]['id']}")
        self.assertTrue(self.browser.url.rsplit('/',2)[1]=='payments')
        payment_id=int(self.browser.url.rsplit('/',1)[1])
        self.browser.post(f'/payments/{payment_id}/simulate',result='failed')
        self.assertIn('Thất bại',self.browser.html)
        self.browser.post(f"/orders/{order['id']}/pay")
        new_id=int(self.browser.url.rsplit('/',1)[1]);self.assertNotEqual(new_id,payment_id)
        self.browser.post(f'/payments/{new_id}/simulate',result='success')
        self.assertEqual(self.query('SELECT payment_status FROM orders WHERE id=?',(order['id'],))[0]['payment_status'],'Đã thanh toán')
        self.browser.post(f"/orders/{order['id']}/cancel",reason='Thử hủy đơn đã thanh toán')
        self.assertEqual(self.query("SELECT COUNT(*) AS n FROM payments WHERE order_id=? AND kind='refund'",(order['id'],))[0]['n'],1)
        self.assertEqual(self.browser.post(f'/payments/{new_id}/simulate',result='success'),200)
        self.assertEqual(self.query('SELECT status FROM orders WHERE id=?',(order['id'],))[0]['status'],'Đã hủy')

    def test_expired_payment_releases_stock_once(self):
        before=self.query('SELECT stock FROM variants WHERE id=2')[0]['stock']
        order,_=self.make_order(method='wallet')
        with closing(sqlite3.connect(self.database)) as db,db:db.execute('UPDATE orders SET expires_at=0 WHERE id=?',(order['id'],))
        self.browser.get(f"/orders/{order['id']}")
        self.assertEqual(self.query('SELECT status FROM orders WHERE id=?',(order['id'],))[0]['status'],'Đã hủy')
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=2')[0]['stock'],before)
        self.browser.get('/products')
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=2')[0]['stock'],before)

    def test_order_privacy_and_saved_address_privacy(self):
        order,_=self.make_order()
        stranger=Browser(self.base);self.register(stranger)
        self.assertEqual(stranger.get(f"/orders/{order['id']}"),404)
        self.assertEqual(self.login_admin().get(f"/admin/orders/{order['id']}"),200)
        self.assertEqual(stranger.get('/api/support?customer=1'),403)

    def test_admin_cancel_restocks_once(self):
        order,_=self.make_order(product_id=3)
        stock=self.query('SELECT stock FROM variants WHERE id=3')[0]['stock']
        admin=self.login_admin();admin.get(f"/admin/orders/{order['id']}")
        self.assertEqual(admin.post(f"/admin/orders/{order['id']}/status",status='Đã hủy'),200)
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=3')[0]['stock'],stock+1)
        self.assertEqual(admin.post(f"/admin/orders/{order['id']}/status",status='Đã hủy'),400)
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=3')[0]['stock'],stock+1)

    def test_return_workflow_refund_and_points(self):
        order,_=self.make_order(product_id=4)
        admin=self.complete(order['id'])
        stock=self.query('SELECT stock FROM variants WHERE id=4')[0]['stock']
        self.browser.get(f"/orders/{order['id']}")
        self.assertEqual(self.browser.post(f"/orders/{order['id']}/return",reason='Sản phẩm không phù hợp nhu cầu'),200)
        return_id=self.query('SELECT id FROM return_requests WHERE order_id=?',(order['id'],))[0]['id']
        admin.get('/admin/returns')
        for status in ('Đã duyệt','Đã nhận hàng','Đã hoàn tiền'):
            self.assertEqual(admin.post(f'/admin/returns/{return_id}',status=status,response='Đã kiểm tra theo chính sách demo'),200)
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=4')[0]['stock'],stock+1)
        self.assertEqual(self.query('SELECT payment_status FROM orders WHERE id=?',(order['id'],))[0]['payment_status'],'Đã hoàn tiền')
        self.assertEqual(self.query('SELECT points FROM users WHERE id=?',(order['user_id'],))[0]['points'],0)
        self.assertEqual(admin.post(f'/admin/returns/{return_id}',status='Đã hoàn tiền'),400)

    def test_verified_review_and_question(self):
        order,_=self.make_order(product_id=5)
        self.browser.get('/products/5')
        self.assertEqual(self.browser.post('/products/5/reviews',order_id=order['id'],rating=5,content='Sản phẩm đáp ứng nhu cầu demo'),403)
        self.complete(order['id'])
        self.browser.get('/products/5')
        self.assertEqual(self.browser.post('/products/5/reviews',order_id=order['id'],rating=5,content='Sản phẩm đáp ứng nhu cầu demo'),200)
        self.assertIn('Đã mua hàng',self.browser.html)
        self.assertEqual(self.browser.post('/products/5/reviews',order_id=order['id'],rating=4,content='Thử gửi đánh giá lần hai'),400)
        self.browser.get('/products/5');self.browser.post('/products/5/questions',content='Sản phẩm có kết nối USB-C không?')
        question=self.query('SELECT id FROM questions ORDER BY id DESC LIMIT 1')[0]['id']
        admin=self.login_admin();admin.get('/admin/support');admin.post(f'/admin/questions/{question}',answer='Phiên bản demo có kết nối USB-C.')
        self.browser.get('/products/5');self.assertIn('Phiên bản demo có kết nối USB-C.',self.browser.html)

    def test_support_notifications_and_reconciliation(self):
        order,_=self.make_order(product_id=6)
        self.complete(order['id'])
        self.browser.get('/account/support');self.browser.post('/account/support',content='Tôi cần hỗ trợ đơn hàng')
        admin=self.login_admin();admin.get('/admin/support');admin.post('/admin/support',user_id=order['user_id'],content='NEU SHOP đã tiếp nhận yêu cầu.')
        self.browser.get('/api/support')
        self.assertEqual(len(json.loads(self.browser.html)),2)
        self.browser.get('/account/notifications');self.assertIn('Phản hồi từ NEU SHOP',self.browser.html)
        self.browser.post('/account/notifications/read')
        self.assertEqual(self.query('SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=0',(order['user_id'],))[0]['n'],0)
        payment=self.query("SELECT id FROM payments WHERE order_id=? AND status='Thành công'",(order['id'],))[0]['id']
        admin.get('/admin/reports');self.assertEqual(admin.post(f'/admin/payments/{payment}/reconcile'),200)
        admin.get('/admin/reports?export=1');self.assertIn('Mã giao dịch',admin.html)

    def test_admin_products_variants_inventory_and_catalog(self):
        admin=self.login_admin();admin.get('/admin/products/new')
        self.assertEqual(admin.post('/admin/products/save',name='Bad',category='phone',price=-1,stock=-1),400)
        name=f'Demo Test {time.time_ns()}'
        brand=self.query('SELECT id FROM brands LIMIT 1')[0]['id']
        fields={'name':name,'category':'accessory','brand_id':brand,'price':199000,'stock':3,'summary':'Phụ kiện demo','description':'Mô tả sản phẩm kiểm thử','specs':'Kết nối: USB-C','warranty':'Bảo hành mô phỏng 12 tháng','image':'hub'}
        self.assertEqual(admin.post('/admin/products/save',**fields),200)
        product=self.query('SELECT id FROM products WHERE name=?',(name,))[0]['id']
        self.assertEqual(self.browser.get(f'/products/{product}'),200)
        admin.post(f'/admin/products/{product}/variants',color='Bạc',storage='Bản nâng cấp',price=299000,active=1)
        variant=self.query('SELECT id FROM variants WHERE product_id=? ORDER BY id DESC',(product,))[0]['id']
        admin.get('/admin/inventory');self.assertEqual(admin.post('/admin/inventory',variant_id=variant,quantity=4,reason='Nhập hàng kiểm thử'),200)
        self.assertEqual(self.query('SELECT stock FROM products WHERE id=?',(product,))[0]['stock'],7)
        self.assertEqual(admin.post('/admin/inventory',variant_id=variant,quantity=-99,reason='Thử xuất vượt tồn'),400)
        admin.get('/admin/products');admin.post(f'/admin/products/{product}/visibility')
        self.assertEqual(self.browser.get(f'/products/{product}'),404)
        admin.post(f'/admin/products/{product}/visibility')
        self.assertEqual(self.browser.get(f'/products/{product}'),200)
        admin.get('/admin/catalog');admin.post('/admin/catalog',kind='category',slug='test-category',name='Danh mục kiểm thử')
        self.assertTrue(self.query("SELECT 1 FROM categories WHERE slug='test-category'"))

    def test_upload_and_reject_non_image(self):
        import base64
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        admin=self.login_admin();admin.get('/admin/products/7/edit')
        p=self.query('SELECT * FROM products WHERE id=7')[0]
        fields={name:p[name] for name in ('name','category','brand_id','summary','description','specs','warranty','image')};fields['id']=7
        self.assertEqual(self.multipart(admin,'/admin/products/save',fields,'image.png',png),200)
        media=self.query('SELECT media FROM products WHERE id=7')[0]['media']
        self.assertTrue(media.startswith('/media/'))
        self.assertEqual(self.multipart(admin,'/admin/products/save',fields,'evil.png',b'<script>bad</script>'),400)

    def test_admin_user_role_protection_and_audit(self):
        email=self.register();target=self.query('SELECT id FROM users WHERE email=?',(email,))[0]['id']
        admin=self.login_admin();admin.get('/admin/users')
        self.assertEqual(admin.post('/admin/users/1',role='customer',active=1),400)
        admin.get('/admin/users');self.assertEqual(admin.post(f'/admin/users/{target}',role='customer'),200)
        self.browser.get('/account');self.assertTrue(self.browser.url.endswith('/login'))
        self.assertGreater(len(self.query('SELECT * FROM audit_logs')),0)

    def test_customer_confirm_received_and_no_repeat_points(self):
        order,_=self.make_order(product_id=8)
        self.confirm_contract(order['id'])
        admin=self.login_admin();admin.get(f"/admin/orders/{order['id']}")
        for status in ('Đang chuẩn bị','Đang giao'):admin.post(f"/admin/orders/{order['id']}/status",status=status)
        self.browser.get(f"/orders/{order['id']}")
        self.assertEqual(self.browser.post(f"/orders/{order['id']}/confirm"),200)
        points=self.query('SELECT points FROM users WHERE id=?',(order['user_id'],))[0]['points']
        self.assertGreater(points,0)
        self.assertEqual(self.browser.post(f"/orders/{order['id']}/confirm"),400)
        self.assertEqual(self.query('SELECT points FROM users WHERE id=?',(order['user_id'],))[0]['points'],points)


    def test_migration_preserves_legacy_data_and_is_repeatable(self):
        legacy=Path(self.temp.name)/'legacy.db'
        with closing(sqlite3.connect(legacy)) as db,db:
            db.executescript("""
                CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'customer',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,price INTEGER NOT NULL,stock INTEGER NOT NULL,summary TEXT NOT NULL,description TEXT NOT NULL,specs TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE orders(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,recipient TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,note TEXT NOT NULL,total INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'Chờ xác nhận',checkout_key TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE order_items(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL,product_id INTEGER NOT NULL,name TEXT NOT NULL,price INTEGER NOT NULL,quantity INTEGER NOT NULL);
                INSERT INTO users(id,name,email,password) VALUES(1,'Khách cũ','legacy@example.com','unchanged-hash');
                INSERT INTO products VALUES(1,'Sản phẩm cũ','laptop',100000,3,'Giữ nguyên','Giữ mô tả cũ','RAM: 8GB',1);
                INSERT INTO orders(id,user_id,recipient,phone,address,note,total,status,checkout_key) VALUES(1,1,'Khách cũ','0912345678','12 Demo Street','Ghi chú cũ',100000,'Hoàn tất','legacy-key');
                INSERT INTO order_items VALUES(1,1,1,'Tên tại thời điểm mua',100000,1);
            """)
        subprocess.run([sys.executable,'-c','from app.db import initialize; initialize(); initialize()'],cwd=ROOT,env={**os.environ,'NEU_DB_PATH':str(legacy)},check=True,timeout=20,capture_output=True)
        with closing(sqlite3.connect(legacy)) as db:
            self.assertEqual(db.execute('SELECT password FROM users WHERE id=1').fetchone()[0],'unchanged-hash')
            self.assertEqual(db.execute('SELECT stock FROM variants WHERE product_id=1').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM variants WHERE product_id=1').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT name FROM order_items WHERE id=1').fetchone()[0],'Tên tại thời điểm mua')
            self.assertEqual(db.execute('SELECT payment_status FROM orders WHERE id=1').fetchone()[0],'Đã thanh toán')
        self.assertTrue((legacy.parent/'backups/before-v2.db').exists())

    def test_concurrent_checkout_does_not_oversell(self):
        from concurrent.futures import ThreadPoolExecutor
        with closing(sqlite3.connect(self.database)) as db,db:
            p=db.execute("INSERT INTO products(name,category,brand_id,price,stock,summary,description,specs) VALUES('Last item test','laptop',1,100000,1,'Demo','Fixture for concurrent checkout','RAM: 8GB')").lastrowid
            v=db.execute("INSERT INTO variants(product_id,sku,color,storage,price,stock) VALUES(?,'LAST-ITEM','Xám','Demo',100000,1)",(p,)).lastrowid
        browsers=[Browser(self.base),Browser(self.base)]
        forms=[]
        for browser in browsers:
            self.register(browser);browser.get(f'/products/{p}');browser.post('/cart/add',variant_id=v,quantity=1);browser.get('/checkout')
            forms.append({'csrf':browser.token(),'checkout_key':browser.token('checkout_key'),'recipient':'Demo User','phone':'0912345678','address':'12 Đường Demo, Hà Nội','payment_method':'cod','shipping_method':'standard'})
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(browser.request,'/checkout',data) for browser,data in zip(browsers,forms)]
            results=[future.result() for future in futures]
        self.assertEqual(sorted(results),[200,400])
        self.assertEqual(self.query('SELECT stock FROM variants WHERE id=?',(v,))[0]['stock'],0)
        self.assertEqual(self.query('SELECT COUNT(*) AS n FROM order_items WHERE variant_id=?',(v,))[0]['n'],1)


    def test_linked_demo_fixture_is_idempotent(self):
        fixture_db=Path(self.temp.name)/'ui-fixture.db'
        env={**os.environ,'NEU_DB_PATH':str(fixture_db)}
        command=[sys.executable,'-m','app.db','--seed-demo']
        subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=30,capture_output=True)
        with closing(sqlite3.connect(fixture_db)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],7)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM reviews WHERE is_demo=1').fetchone()[0],4)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM return_requests').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM variants WHERE list_price>price').fetchone()[0],3)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            before='\n'.join(db.iterdump())
        subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=30,capture_output=True)
        with closing(sqlite3.connect(fixture_db)) as db:self.assertEqual('\n'.join(db.iterdump()),before)

    def test_quick_cart_json_and_newsletter(self):
        self.browser.get('/products/3')
        request=Request(self.base+'/cart/add',data=urlencode({'csrf':self.browser.token(),'variant_id':3,'quantity':1}).encode(),headers={'X-Requested-With':'fetch'})
        with self.browser.opener.open(request,timeout=10) as response:
            result=json.loads(response.read().decode());self.assertEqual(response.status,200);self.assertEqual(result['count'],1)
        self.browser.get('/api/cart-summary');self.assertEqual(json.loads(self.browser.html)['count'],1)
        self.browser.get('/');self.assertEqual(self.browser.post('/newsletter',email='invalid'),400)
        self.browser.get('/');self.assertEqual(self.browser.post('/newsletter',email='newsletter@example.test'),200)
        self.assertTrue(self.query("SELECT 1 FROM newsletter_subscriptions WHERE email='newsletter@example.test'"))

    def test_variant_matrix_sale_expiry_and_gallery(self):
        from datetime import datetime,timedelta,timezone
        admin=self.login_admin();admin.get('/admin/products/new')
        name=f'Matrix {time.time_ns()}'
        fields={'name':name,'category':'accessory','brand_id':1,'price':199000,'stock':2,'summary':'Phụ kiện kiểm thử','description':'Mô tả sản phẩm kiểm thử bảng biến thể','specs':'Cổng: USB-C','warranty':'Bảo hành mẫu','image':'hub'}
        self.assertEqual(admin.post('/admin/products/save',**fields),200)
        product=self.query('SELECT id FROM products WHERE name=?',(name,))[0]['id']
        batch=[{'sku':f'MATRIX-{product}-1','color':'Đen','storage':'256GB','price':199000,'stock':3},{'sku':f'MATRIX-{product}-2','color':'Bạc','storage':'512GB','price':299000,'stock':4}]
        self.assertEqual(admin.post(f'/admin/products/{product}/variants/batch',variants=json.dumps(batch)),200)
        self.assertEqual(self.query('SELECT COUNT(*) AS n FROM variants WHERE product_id=?',(product,))[0]['n'],3)
        self.assertEqual(self.query('SELECT stock FROM products WHERE id=?',(product,))[0]['stock'],9)
        self.assertEqual(admin.post(f'/admin/products/{product}/variants/batch',variants=json.dumps(batch)),400)
        variant=self.query('SELECT id FROM variants WHERE product_id=? ORDER BY id LIMIT 1',(product,))[0]['id']
        admin.get(f'/admin/products/{product}/edit')
        end=(datetime.now(timezone(timedelta(hours=7)))+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.assertEqual(admin.post(f'/admin/products/{product}/sale',variant_id=variant,list_price=199000,sale_price=179000,end=end),200)
        self.browser.get(f'/products/{product}');self.assertIn('199.000',self.browser.html);self.assertIn('179.000',self.browser.html)
        with closing(sqlite3.connect(self.database)) as db,db:db.execute("UPDATE variants SET sale_end=datetime('now','-1 minute') WHERE id=?",(variant,))
        self.browser.get(f'/products/{product}')
        row=self.query('SELECT price,list_price FROM variants WHERE id=?',(variant,))[0]
        self.assertEqual(row['price'],199000);self.assertEqual(row['list_price'],0)
        import base64
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        self.assertEqual(self.multipart(admin,f'/admin/products/{product}/gallery',{'alt':'Ảnh kiểm thử'},'sample.png',png),200)
        self.assertTrue(self.query('SELECT * FROM product_images WHERE product_id=?',(product,)))

    def test_admin_reply_on_verified_review(self):
        order,_=self.make_order(product_id=6)
        admin=self.complete(order['id'])
        self.browser.get('/products/6');self.browser.post('/products/6/reviews',order_id=order['id'],rating=5,content='Đánh giá kiểm thử có phản hồi của admin.')
        review=self.query('SELECT id FROM reviews WHERE order_id=?',(order['id'],))[0]['id']
        admin.get('/admin/content')
        self.assertEqual(admin.post(f'/admin/reviews/{review}/reply',reply='Cảm ơn bạn đã chia sẻ trải nghiệm.'),200)
        self.browser.get('/products/6');self.assertIn('Cảm ơn bạn đã chia sẻ trải nghiệm.',self.browser.html)


if __name__ == '__main__':
    unittest.main()
