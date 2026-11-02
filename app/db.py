import hashlib
import hmac
import os
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NEU_DB_PATH", str(ROOT / "data" / "shop.db")))
CATEGORIES = {"laptop": "Laptop", "phone": "Điện thoại", "audio": "Âm thanh", "accessory": "Phụ kiện"}
IMAGES = {"": "Theo danh mục", "laptop": "Laptop", "phone": "Điện thoại", "audio": "Tai nghe chụp tai", "earbuds": "Tai nghe không dây", "accessory": "Bàn phím", "hub": "Hub USB-C"}
STATUSES = ("Chờ xác nhận", "Đang chuẩn bị", "Đang giao", "Hoàn tất", "Đã hủy")


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"{salt}${digest}"


def password_matches(password, stored):
    salt, expected = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return hmac.compare_digest(digest, expected)


# ── Schema, migration và dữ liệu nghiệp vụ ──


def _upgrade_schema(db):
    db.execute("CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY)")
    if db.execute("SELECT 1 FROM schema_versions WHERE version=2").fetchone():
        return
    additions = {
        "users": {"phone": "TEXT NOT NULL DEFAULT ''", "birth_date": "TEXT NOT NULL DEFAULT ''", "gender": "TEXT NOT NULL DEFAULT ''", "points": "INTEGER NOT NULL DEFAULT 0", "active": "INTEGER NOT NULL DEFAULT 1", "email_verified": "INTEGER NOT NULL DEFAULT 1", "otp_enabled": "INTEGER NOT NULL DEFAULT 0", "auth_rev": "INTEGER NOT NULL DEFAULT 0"},
        "products": {"brand_id": "INTEGER REFERENCES brands(id)", "warranty": "TEXT NOT NULL DEFAULT 'Bảo hành thử nghiệm 12 tháng'", "featured": "INTEGER NOT NULL DEFAULT 0", "media": "TEXT NOT NULL DEFAULT ''"},
        "orders": {"subtotal": "INTEGER NOT NULL DEFAULT 0", "shipping_fee": "INTEGER NOT NULL DEFAULT 0", "discount": "INTEGER NOT NULL DEFAULT 0", "voucher_id": "INTEGER REFERENCES vouchers(id)", "receive_method": "TEXT NOT NULL DEFAULT 'delivery'", "shipping_method": "TEXT NOT NULL DEFAULT 'standard'", "payment_method": "TEXT NOT NULL DEFAULT 'cod'", "payment_status": "TEXT NOT NULL DEFAULT 'Chưa thanh toán'", "tracking_code": "TEXT NOT NULL DEFAULT ''", "expires_at": "INTEGER", "completed_at": "TEXT", "points_awarded": "INTEGER NOT NULL DEFAULT 0"},
        "order_items": {"variant_id": "INTEGER REFERENCES variants(id)", "variant_label": "TEXT NOT NULL DEFAULT ''", "image": "TEXT NOT NULL DEFAULT ''"},
    }
    db.executescript("""
        CREATE TABLE IF NOT EXISTS brands(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS categories(slug TEXT PRIMARY KEY,name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS variants(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id),sku TEXT NOT NULL UNIQUE,color TEXT NOT NULL,storage TEXT NOT NULL DEFAULT '',price INTEGER NOT NULL CHECK(price>=1000),stock INTEGER NOT NULL CHECK(stock>=0),active INTEGER NOT NULL DEFAULT 1,media TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS account_cart(user_id INTEGER NOT NULL REFERENCES users(id),variant_id INTEGER NOT NULL REFERENCES variants(id),quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 99),selected INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(user_id,variant_id));
        CREATE TABLE IF NOT EXISTS addresses(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),recipient TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,is_default INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS vouchers(id INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,kind TEXT NOT NULL CHECK(kind IN ('fixed','percent')),value INTEGER NOT NULL CHECK(value>0),min_total INTEGER NOT NULL DEFAULT 0,max_discount INTEGER NOT NULL DEFAULT 0,start_date TEXT NOT NULL,end_date TEXT NOT NULL,usage_limit INTEGER NOT NULL CHECK(usage_limit>0),used_count INTEGER NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),method TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>=0),status TEXT NOT NULL DEFAULT 'Chờ thanh toán',reference TEXT NOT NULL UNIQUE,kind TEXT NOT NULL DEFAULT 'payment',reconciled INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,paid_at TEXT);
        CREATE TABLE IF NOT EXISTS return_requests(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),user_id INTEGER NOT NULL REFERENCES users(id),reason TEXT NOT NULL,image TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'Chờ duyệt',response TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),order_id INTEGER NOT NULL REFERENCES orders(id),product_id INTEGER NOT NULL REFERENCES products(id),rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),content TEXT NOT NULL,image TEXT NOT NULL DEFAULT '',visible INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,order_id,product_id));
        CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,content TEXT NOT NULL,url TEXT NOT NULL DEFAULT '/account',is_read INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS inventory_movements(id INTEGER PRIMARY KEY,variant_id INTEGER NOT NULL REFERENCES variants(id),quantity INTEGER NOT NULL,reason TEXT NOT NULL,actor_id INTEGER REFERENCES users(id),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY,actor_id INTEGER REFERENCES users(id),action TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS order_events(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),status TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS otp_challenges(id TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),purpose TEXT NOT NULL,code_hash TEXT NOT NULL,demo_code TEXT NOT NULL,expires_at INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,consumed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),product_id INTEGER NOT NULL REFERENCES products(id),content TEXT NOT NULL,answer TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS support_messages(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),sender_id INTEGER NOT NULL REFERENCES users(id),content TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY,title TEXT NOT NULL,summary TEXT NOT NULL,content TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS variants_product ON variants(product_id);
        CREATE INDEX IF NOT EXISTS notifications_user ON notifications(user_id,is_read);
    """)
    for table, columns in additions.items():
        existing = {column["name"] for column in db.execute(f"PRAGMA table_info({table})")}
        for name, definition in columns.items():
            if name not in existing:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    db.executemany("INSERT OR IGNORE INTO categories(slug,name) VALUES(?,?)", CATEGORIES.items())
    db.execute("INSERT OR IGNORE INTO brands(name) VALUES('NEU')")
    brand = db.execute("SELECT id FROM brands WHERE name='NEU'").fetchone()[0]
    for p in db.execute("SELECT * FROM products").fetchall():
        variant = db.execute("INSERT INTO variants(product_id,sku,color,storage,price,stock) VALUES(?,?,?,?,?,?)", (p["id"], f"NEU-{p['id']:04d}-01", "Xám" if p["category"] in ("laptop", "accessory") else "Xanh", "Tiêu chuẩn", p["price"], p["stock"])).lastrowid
        db.execute("UPDATE products SET brand_id=?,featured=? WHERE id=?", (brand, int(p["id"] <= 4), p["id"]))
        db.execute("UPDATE order_items SET variant_id=?,variant_label='Phiên bản cũ' WHERE product_id=?", (variant, p["id"]))
        db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason) VALUES(?,?,'Tồn đầu khi nâng cấp dữ liệu')", (variant, p["stock"]))
    if not db.execute("SELECT 1 FROM orders").fetchone():
        for p in db.execute("SELECT * FROM products WHERE name IN ('NEU Book Air 14','NEU Phone S1')").fetchall():
            variant_id = db.execute("INSERT INTO variants(product_id,sku,color,storage,price,stock) VALUES(?,?,?,?,?,4)", (p["id"], f"NEU-{p['id']:04d}-02", "Bạc", "Nâng cấp dung lượng", p["price"] + 1000000)).lastrowid
            db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason) VALUES(?,4,'Tồn đầu biến thể mẫu')", (variant_id,))
            db.execute("UPDATE products SET stock=stock+4 WHERE id=?", (p["id"],))
    db.execute("UPDATE orders SET subtotal=total")
    for order in db.execute("SELECT * FROM orders").fetchall():
        db.execute("INSERT INTO order_events(order_id,status,note) VALUES(?,?,'Đơn trước khi nâng cấp')", (order["id"], order["status"]))
        db.execute("INSERT INTO payments(order_id,method,amount,status,reference,paid_at) VALUES(?,'cod',?,?,?,?)", (order["id"], order["total"], "Thành công" if order["status"] == "Hoàn tất" else "Chờ thanh toán", f"LEGACY-{order['id']}", order["created_at"] if order["status"] == "Hoàn tất" else None))
        if order["status"] == "Hoàn tất":
            db.execute("UPDATE orders SET payment_status='Đã thanh toán',completed_at=created_at WHERE id=?", (order["id"],))
    db.execute("INSERT INTO vouchers(code,kind,value,min_total,max_discount,start_date,end_date,usage_limit) VALUES('NEU100','fixed',100000,1000000,0,date('now','+7 hours','-1 day'),date('now','+7 hours','+90 days'),100)")
    db.execute("INSERT INTO vouchers(code,kind,value,min_total,max_discount,start_date,end_date,usage_limit) VALUES('WELCOME5','percent',5,500000,300000,date('now','+7 hours','-1 day'),date('now','+7 hours','+90 days'),100)")
    db.executemany("INSERT INTO articles(title,summary,content) VALUES(?,?,?)", [
        ("Chọn laptop cho góc học tập", "Bắt đầu từ nhu cầu, bộ nhớ và kích thước màn hình.", 'Xác định các phần mềm bạn sử dụng trước khi chọn cấu hình.\n\nƯu tiên dung lượng RAM phù hợp cho đa nhiệm, SSD đủ cho tài liệu và màn hình dễ đọc. So sánh thông số trong trang sản phẩm để lựa chọn.\n\nĐây là bài hướng dẫn mẫu trong bản  NEU SHOP.'),
        ('Mua sắm và đổi trả trong bản ', "Các bước thử đặt hàng, theo dõi và yêu cầu trả hàng.", 'Đăng nhập, chọn biến thể và thêm sản phẩm vào giỏ. Tại bước thanh toán, chọn giao hàng hoặc nhận tại cửa hàng thử nghiệm.\n\nSau khi đơn hoàn tất, bạn có thể đánh giá hoặc yêu cầu trả toàn bộ đơn trong 7 ngày. Admin xét duyệt, xác nhận nhận hàng và hoàn tiền thử nghiệm.\n\nKhông có giao hàng hoặc thu tiền thực tế.'),
    ])
    db.execute("INSERT INTO schema_versions(version) VALUES(2)")


# ── Khởi tạo cơ sở dữ liệu ──


def initialize():
    if DB_PATH.exists():
        with connect() as original:
            upgraded = original.execute("SELECT 1 FROM sqlite_master WHERE name='schema_versions'").fetchone()
            if upgraded and not original.execute('SELECT 1 FROM schema_versions WHERE version=5').fetchone():
                directory = DB_PATH.parent / 'backups'
                directory.mkdir(exist_ok=True)
                target = directory / 'before-portal-v5.db'
                if not target.exists():
                    backup = sqlite3.connect(target)
                    try:
                        original.backup(backup)
                    finally:
                        backup.close()
            if not upgraded:
                backup_dir = DB_PATH.parent / "backups"
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / "before-v2.db"
                if not backup_path.exists():
                    backup = sqlite3.connect(backup_path)
                    try:
                        original.backup(backup)
                    finally:
                        backup.close()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                price INTEGER NOT NULL CHECK(price >= 1000), stock INTEGER NOT NULL CHECK(stock >= 0),
                summary TEXT NOT NULL, description TEXT NOT NULL, specs TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                recipient TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL,
                note TEXT NOT NULL, total INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Chờ xác nhận',
                checkout_key TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
                product_id INTEGER NOT NULL REFERENCES products(id), name TEXT NOT NULL,
                price INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0)
            );
            CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id);
        """)
        if "image" not in {column["name"] for column in db.execute("PRAGMA table_info(products)")}:
            db.execute("ALTER TABLE products ADD COLUMN image TEXT NOT NULL DEFAULT ''")
            db.execute("UPDATE products SET image='earbuds' WHERE name='NEU Buds Mini'")
            db.execute("UPDATE products SET image='hub' WHERE name='NEU Hub Connect'")

        if not db.execute("SELECT 1 FROM users WHERE email = ?", ("admin@neushop.local",)).fetchone():
            db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                       ("Quản trị NEU SHOP", "admin@neushop.local", password_hash("Admin@12345"), "admin"))
        if not db.execute("SELECT 1 FROM products").fetchone():
            products = [
                ("NEU Book Air 14", "laptop", 16990000, 12, "16GB RAM / SSD 512GB / 14 inch", "Gọn nhẹ cho một ngày học tập và làm việc. Màn hình 14 inch, bàn phím đầy đủ và cấu hình cân bằng cho các tác vụ hằng ngày.", "Màn hình: 14 inch Full HD\nBộ nhớ: RAM 16GB\nLưu trữ: SSD 512GB\nKết nối: Wi-Fi, Bluetooth, USB-C"),
                ("NEU Phone S1", "phone", 7990000, 20, "8GB RAM / 128GB / OLED 6.4 inch", "Chiếc điện thoại cho nhu cầu liên lạc, chụp ảnh và giải trí mỗi ngày. Thiết kế tối giản với màn hình OLED.", "Màn hình: OLED 6.4 inch\nBộ nhớ: RAM 8GB\nLưu trữ: 128GB\nPin: 5.000 mAh"),
                ("NEU Sound Studio", "audio", 1490000, 30, "Bluetooth 5.3 / Chụp tai / USB-C", "Tạo một khoảng tập trung cho riêng bạn. Tai nghe chụp tai không dây với đệm tai mềm và kết nối tiện lợi.", "Kết nối: Bluetooth 5.3\nKiểu dáng: Chụp tai\nSạc: USB-C\nMàu sắc: Xanh đậm"),
                ("NEU Keys K2", "accessory", 890000, 18, "Bàn phím cơ / 75% / Có dây", "Một góc làm việc gọn gàng bắt đầu từ bàn phím. Bố cục 75% giữ lại các phím cần thiết cho công việc.", "Bố cục: 75%\nKết nối: USB-C có dây\nSwitch: Linear\nMàu sắc: Xám"),
                ("NEU Book Pro 16", "laptop", 24990000, 8, "32GB RAM / SSD 1TB / 16 inch", "Không gian hiển thị rộng cho những dự án lớn. Dung lượng RAM và SSD phục vụ học tập, lập trình và đa nhiệm.", "Màn hình: 16 inch 2.5K\nBộ nhớ: RAM 32GB\nLưu trữ: SSD 1TB\nKết nối: Wi-Fi, HDMI, USB-C"),
                ("NEU Phone S1 Plus", "phone", 10990000, 10, "12GB RAM / 256GB / OLED 6.7 inch", "Màn hình rộng hơn, không gian lưu trữ nhiều hơn. Phiên bản dành cho những ai sử dụng điện thoại xuyên suốt ngày dài.", "Màn hình: OLED 6.7 inch\nBộ nhớ: RAM 12GB\nLưu trữ: 256GB\nPin: 5.200 mAh"),
                ("NEU Buds Mini", "audio", 690000, 25, "True wireless / Hộp sạc USB-C", "Âm nhạc luôn trong túi áo. Tai nghe nhỏ gọn đi cùng hộp sạc, phù hợp khi di chuyển.", "Kết nối: Bluetooth 5.3\nKiểu dáng: In-ear\nSạc: USB-C\nMàu sắc: Xanh đậm"),
                ("NEU Hub Connect", "accessory", 490000, 16, "Hub USB-C / HDMI / USB-A", "Kết nối các thiết bị quen thuộc qua một cổng USB-C. Phụ kiện nhỏ gọn cho bàn học và góc làm việc.", "Đầu vào: USB-C\nĐầu ra: HDMI, USB-A, USB-C\nVỏ: Hợp kim\nMàu sắc: Xám"),
            ]
            db.executemany("INSERT INTO products(name,category,price,stock,summary,description,specs) VALUES(?,?,?,?,?,?,?)", products)
            db.execute("UPDATE products SET image='earbuds' WHERE name='NEU Buds Mini'")
            db.execute("UPDATE products SET image='hub' WHERE name='NEU Hub Connect'")

        _upgrade_schema(db)
        _upgrade_ui_schema(db)
        _upgrade_catalog_schema(db)
        _upgrade_portal_schema(db)


def _upgrade_portal_schema(db):
    if db.execute('SELECT 1 FROM schema_versions WHERE version=5').fetchone():
        return
    for table, fields in {
        'categories': {'parent_slug': 'TEXT REFERENCES categories(slug)'},
        'products': {'subcategory': 'TEXT REFERENCES categories(slug)', 'deleted_at': 'TEXT'},
        'articles': {'topic_id': 'INTEGER REFERENCES article_topics(id)', 'image': "TEXT NOT NULL DEFAULT ''"},
    }.items():
        existing = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
        for field, definition in fields.items():
            if field not in existing:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {field} {definition}')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS site_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS site_pages(slug TEXT PRIMARY KEY,title TEXT NOT NULL,summary TEXT NOT NULL,body TEXT NOT NULL,image TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS article_topics(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS contact_requests(id INTEGER PRIMARY KEY,receipt TEXT NOT NULL UNIQUE,visitor_key TEXT NOT NULL,name TEXT NOT NULL,email TEXT NOT NULL,phone TEXT NOT NULL DEFAULT '',address TEXT NOT NULL DEFAULT '',content TEXT NOT NULL,response TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','open','replied','closed')),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS visitor_sessions(visitor_key TEXT PRIMARY KEY,first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS page_visits(day TEXT PRIMARY KEY,views INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sales_contracts(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),user_id INTEGER NOT NULL REFERENCES users(id),number TEXT NOT NULL UNIQUE,snapshot TEXT NOT NULL,document_hash TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','signed','void')),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,signed_at TEXT,signer_name TEXT NOT NULL DEFAULT '',void_reason TEXT NOT NULL DEFAULT '',otp_hash TEXT NOT NULL DEFAULT '',otp_demo_code TEXT NOT NULL DEFAULT '',otp_session_hash TEXT NOT NULL DEFAULT '',otp_expires_at INTEGER NOT NULL DEFAULT 0,otp_sent_at INTEGER NOT NULL DEFAULT 0,otp_attempts INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS contract_events(id INTEGER PRIMARY KEY,contract_id INTEGER NOT NULL REFERENCES sales_contracts(id),actor_id INTEGER REFERENCES users(id),action TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS contact_visitor_time ON contact_requests(visitor_key,created_at);
        CREATE INDEX IF NOT EXISTS contract_owner ON sales_contracts(user_id,id);
        CREATE INDEX IF NOT EXISTS visitor_last_seen ON visitor_sessions(last_seen);
    ''')
    db.executemany('INSERT OR IGNORE INTO site_settings(key,value) VALUES(?,?)', {
        'shop_name': 'NEU SHOP', 'tagline': 'Công nghệ cho mỗi ngày', 'hotline': '', 'email': '', 'address': '',
        'opening_hours': '', 'map_query': '', 'facebook': '', 'youtube': '', 'zalo': '', 'skype': '',
        'show_statistics': '1',
    }.items())
    db.executemany('INSERT OR IGNORE INTO site_pages(slug,title,summary,body) VALUES(?,?,?,?)', [
        ('about', 'Về NEU SHOP', 'Tìm hiểu thiết bị, chọn đúng nhu cầu.', '## Giới thiệu\nNEU SHOP là dự án website bán đồ công nghệ, giúp bạn khám phá laptop, điện thoại, âm thanh và phụ kiện trong cùng một trải nghiệm.\n\n## Sứ mệnh\nGiúp người dùng dễ tìm kiếm, so sánh cấu hình và hiểu rõ thông tin trước khi lựa chọn thiết bị.\n\n## Tầm nhìn\nXây dựng trải nghiệm mua sắm rõ ràng, thuận tiện và nhất quán từ lúc tìm sản phẩm đến khi theo dõi đơn hàng.\n\n## Phạm vi hiện tại\nWebsite phục vụ học tập và trình diễn trên local. Giá tham khảo, đơn hàng, thanh toán và giao nhận không phải giao dịch thương mại thực tế.'),
        ('services', 'Dịch vụ & hỗ trợ', 'Mỗi bước mua sắm đều có thông tin để bạn theo dõi.', '## Tư vấn lựa chọn\nTìm kiếm theo từ khóa, danh mục, thương hiệu và ngân sách. So sánh tối đa ba sản phẩm và đặt câu hỏi ngay trên trang chi tiết.\n\n## Đặt hàng & theo dõi\nQuản lý giỏ hàng, chọn địa chỉ, áp dụng voucher và theo dõi lịch sử xử lý đơn trong tài khoản.\n\n## Hậu mãi\nGửi yêu cầu trả hàng trong thời hạn của chính sách ; theo dõi phản hồi và kết quả xử lý.\n\n## Liên hệ\nGửi biểu mẫu liên hệ công khai hoặc đăng nhập để trao đổi với admin trong mục Hỗ trợ khách hàng.'),
    ])
    db.executemany('INSERT OR IGNORE INTO article_topics(name) VALUES(?)', [('Cẩm nang',), ('Tin công nghệ',), ('Mua sắm & hậu mãi',)])
    topic = db.execute("SELECT id FROM article_topics WHERE name='Cẩm nang'").fetchone()[0]
    db.execute('UPDATE articles SET topic_id=? WHERE topic_id IS NULL', (topic,))
    for article in db.execute("SELECT id FROM articles WHERE image='' ORDER BY id").fetchall():
        photo = db.execute("SELECT media FROM products WHERE media!='' AND active=1 ORDER BY id LIMIT 1").fetchone()
        if photo:
            db.execute('UPDATE articles SET image=? WHERE id=?', (photo['media'], article['id']))
    groups = [
        ('laptop-gaming','Laptop gaming','laptop'),('laptop-work','Học tập & văn phòng','laptop'),
        ('phone-iphone','iPhone','phone'),('phone-android','Điện thoại Android','phone'),
        ('audio-headphones','Tai nghe chụp tai','audio'),('audio-earbuds','Tai nghe nhỏ gọn','audio'),
        ('accessory-input','Chuột & bàn phím','accessory'),('accessory-power','Sạc, cáp & pin dự phòng','accessory'),('accessory-hub','Hub & kết nối','accessory'),
    ]
    db.executemany('INSERT OR IGNORE INTO categories(slug,name,parent_slug) VALUES(?,?,?)', groups)
    for product in db.execute('SELECT id,name,category FROM products WHERE subcategory IS NULL').fetchall():
        name, category = product['name'].lower(), product['category']
        if category == 'laptop':
            sub = 'laptop-gaming' if any(term in name for term in ('gaming','loq','tuf','rog','katana','victus')) else 'laptop-work'
        elif category == 'phone':
            sub = 'phone-iphone' if 'iphone' in name else 'phone-android'
        elif category == 'audio':
            sub = 'audio-headphones' if any(term in name for term in ('chụp tai','studio','headphone')) else 'audio-earbuds'
        elif category == 'accessory':
            sub = 'accessory-input' if any(term in name for term in ('chuột','bàn phím','keys','keyboard')) else 'accessory-hub' if any(term in name for term in ('hub','connect')) else 'accessory-power'
        else:
            continue
        db.execute('UPDATE products SET subcategory=? WHERE id=?', (sub, product['id']))
    db.execute('INSERT INTO schema_versions(version) VALUES(5)')


def get_settings(db):
    return {row['key']: row['value'] for row in db.execute('SELECT * FROM site_settings')}


def _upgrade_catalog_schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS product_sources(
        product_id INTEGER PRIMARY KEY REFERENCES products(id),
        source_id TEXT NOT NULL UNIQUE, source_url TEXT NOT NULL,
        listing_url TEXT NOT NULL, image_url TEXT NOT NULL,
        collected_at TEXT NOT NULL, image_sha256 TEXT NOT NULL)""")
    db.execute("INSERT OR IGNORE INTO schema_versions(version) VALUES(4)")


def import_catalog(path):
    initialize()
    products = json.loads(Path(path).read_text(encoding='utf-8'))['products']
    seen = set()
    for product in products:
        if product['source_id'] in seen or product['price'] < 1000 or product['category'] not in CATEGORIES:
            raise ValueError('Duplicate or invalid catalogue entry')
        seen.add(product['source_id'])
        image = (ROOT / 'app' / product['media'].removeprefix('/')).resolve()
        if not image.is_relative_to((ROOT / 'app/static/images/catalog').resolve()):
            raise ValueError('Invalid image path')
        if hashlib.sha256(image.read_bytes()).hexdigest() != product['image_sha256']:
            raise ValueError('Image integrity check failed')
    with connect() as db:
        backup_dir = DB_PATH.parent / 'backups'
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / 'before-real-catalog.db'
        if not backup_path.exists():
            backup = sqlite3.connect(backup_path)
            try:
                db.backup(backup)
            finally:
                backup.close()
        added = 0
        for product in products:
            if db.execute('SELECT 1 FROM product_sources WHERE source_id=?', (product['source_id'],)).fetchone():
                continue
            brand = product['brand'].strip()
            if not brand:
                raise ValueError('Product brand missing')
            db.execute('INSERT OR IGNORE INTO brands(name) VALUES(?)', (brand,))
            brand_id = db.execute('SELECT id FROM brands WHERE name=?', (brand,)).fetchone()[0]
            description = product['name'] + '\n\n' + product['specs']
            pid = db.execute('INSERT INTO products(name,category,price,stock,summary,description,specs,brand_id,media,warranty,featured) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (product['name'],product['category'],product['price'],product['stock'],product['summary'],description,product['specs'],brand_id,product['media'],'Bảo hành thử nghiệm; tham khảo chính sách tại nguồn sản phẩm',int(added < 8))).lastrowid
            vid = db.execute('INSERT INTO variants(product_id,sku,color,storage,price,stock,media) VALUES(?,?,?,?,?,?,?)',
                (pid,'CPS-'+product['source_id'],product['color'],product['storage'],product['price'],product['stock'],product['media'])).lastrowid
            db.execute('INSERT INTO product_images(product_id,url,alt) VALUES(?,?,?)', (pid,product['media'],product['name']))
            db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason) VALUES(?,?,'Tồn đầu thử nghiệm — nhập danh mục thực tế')", (vid,product['stock']))
            db.execute('INSERT INTO product_sources VALUES(?,?,?,?,?,?,?)', (pid,product['source_id'],product['source_url'],product['listing_url'],product['image_url'],product['collected_at'],product['image_sha256']))
            added += 1
        if added:
            db.execute("UPDATE products SET featured=0,active=0 WHERE id<=8 AND name LIKE 'NEU %' AND brand_id=(SELECT id FROM brands WHERE name='NEU')")
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Foreign key consistency check failed')
    return f'Imported {added} products ({added * 5} linked records, excluding brands). Existing data preserved.'


def _upgrade_ui_schema(db):
    if db.execute("SELECT 1 FROM schema_versions WHERE version=3").fetchone():
        return
    for table, columns in {
        "variants": {"list_price": "INTEGER NOT NULL DEFAULT 0", "sale_end": "TEXT NOT NULL DEFAULT ''"},
        "reviews": {"admin_reply": "TEXT NOT NULL DEFAULT ''", "is_demo": "INTEGER NOT NULL DEFAULT 0"},
    }.items():
        existing = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        for column, definition in columns.items():
            if column not in existing:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS product_images(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id),url TEXT NOT NULL,alt TEXT NOT NULL DEFAULT '',sort_order INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS newsletter_subscriptions(email TEXT PRIMARY KEY,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS demo_imports(name TEXT PRIMARY KEY,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    db.execute("INSERT INTO schema_versions(version) VALUES(3)")


def seed_ui_demo():
    initialize()
    fixture = json.loads((ROOT / "docs/mock-data.json").read_text(encoding="utf-8"))
    with connect() as db:
        if db.execute("SELECT 1 FROM demo_imports WHERE name=?", (fixture["fixture_id"],)).fetchone():
            _sync_demo_points(db, fixture["fixture_id"])
            return ' fixture already imported; existing records preserved.'
        backup_dir = DB_PATH.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / "before-ui-demo.db"
        if not backup_path.exists():
            backup = sqlite3.connect(backup_path)
            try:
                db.backup(backup)
            finally:
                backup.close()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM demo_imports WHERE name=?", (fixture["fixture_id"],)).fetchone():
            return ' fixture already imported; no rows changed.'
        users, orders = {}, {}
        for customer in fixture["customers"]:
            existing = db.execute("SELECT id FROM users WHERE email=?", (customer["email"],)).fetchone()
            user_id = existing["id"] if existing else db.execute("INSERT INTO users(name,email,password,phone) VALUES(?,?,?,?)", (customer["name"], customer["email"], password_hash("Demo@12345"), customer["phone"])).lastrowid
            users[customer["id"]] = user_id
            if not db.execute("SELECT 1 FROM addresses WHERE user_id=?", (user_id,)).fetchone():
                db.execute("INSERT INTO addresses(user_id,recipient,phone,address,is_default) VALUES(?,?,?,?,1)", (user_id, customer["name"], customer["phone"], customer["address"]))
        for sample in fixture["orders"]:
            customer = next(c for c in fixture["customers"] if c["id"] == sample["customer_id"])
            lines, subtotal = [], 0
            for item in sample["items"]:
                variant = db.execute("SELECT v.*,p.name,p.image,p.category FROM variants v JOIN products p ON p.id=v.product_id WHERE v.sku=?", (item["sku"],)).fetchone()
                if not variant or variant["stock"] < item["quantity"]:
                    raise ValueError(' SKU missing or insufficient stock: ' + item["sku"])
                lines.append((variant, item["quantity"]))
                subtotal += variant["price"] * item["quantity"]
            total = subtotal + 30000
            age = sample["days_ago"]
            timestamp = db.execute("SELECT datetime('now',?)", (f"-{age} days",)).fetchone()[0]
            completed = sample["status"] == "Hoàn tất"
            user_id = users[sample["customer_id"]]
            order_id = db.execute("INSERT INTO orders(user_id,recipient,phone,address,note,total,subtotal,shipping_fee,status,payment_method,payment_status,checkout_key,created_at,completed_at,tracking_code) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (user_id, customer["name"], customer["phone"], customer["address"], "DỮ LIỆU MINH HỌA — " + sample["id"], total, subtotal, 30000, sample["status"], sample["payment_method"], "Đã thanh toán" if completed or sample["payment_method"] != "cod" else "Chưa thanh toán", fixture["fixture_id"] + ":" + sample["id"], timestamp, timestamp if completed else None, "DEMO-" + sample["id"] if sample["status"] in ("Đang giao", "Hoàn tất") else "")).lastrowid
            orders[sample["id"]] = order_id
            for variant, quantity in lines:
                db.execute("INSERT INTO order_items(order_id,product_id,variant_id,name,variant_label,price,quantity,image) VALUES(?,?,?,?,?,?,?,?)", (order_id, variant["product_id"], variant["id"], variant["name"], variant["color"] + " / " + variant["storage"], variant["price"], quantity, f"/static/images/{variant['image'] or variant['category']}.svg"))
                db.execute("UPDATE variants SET stock=stock-? WHERE id=?", (quantity, variant["id"]))
                db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason) VALUES(?,?,?)", (variant["id"], -quantity, 'Đơn thử nghiệm ' + sample["id"]))
            paid = completed or sample["payment_method"] != "cod"
            if completed:
                points = total // 100000
                db.execute("UPDATE orders SET points_awarded=? WHERE id=?", (points, order_id))
                db.execute("UPDATE users SET points=points+? WHERE id=?", (points, user_id))
            db.execute("INSERT INTO payments(order_id,method,amount,status,reference,created_at,paid_at) VALUES(?,?,?,?,?,?,?)", (order_id, sample["payment_method"], total, "Thành công" if paid else "Chờ thanh toán", "DEMO-PAY-" + sample["id"], timestamp, timestamp if paid else None))
            stages = ["Chờ xác nhận", "Đang chuẩn bị", "Đang giao", "Hoàn tất"]
            for stage in stages[:stages.index(sample["status"]) + 1]:
                db.execute("INSERT INTO order_events(order_id,status,note,created_at) VALUES(?,?,?,?)", (order_id, stage, 'Bước xử lý tham khảo', timestamp))
            db.execute("INSERT INTO notifications(user_id,title,content,url) VALUES(?,?,?,?)", (user_id, 'Đơn hàng tham khảo ' + sample["id"], sample["status"], f"/orders/{order_id}"))
        for review in fixture["reviews"]:
            order_id = orders[review["order_id"]]
            product = db.execute("SELECT product_id FROM order_items WHERE order_id=? ORDER BY id LIMIT 1", (order_id,)).fetchone()
            db.execute("INSERT INTO reviews(user_id,order_id,product_id,rating,content,is_demo,admin_reply) VALUES(?,?,?,?,?,1,?)", (users[review["customer_id"]], order_id, product["product_id"], review["rating"], review["content"], review["reply"]))
        for message in fixture["messages"]:
            db.execute("INSERT INTO support_messages(user_id,sender_id,content) VALUES(?,?,?)", (users[message["customer_id"]], users[message["customer_id"]], message["content"]))
        for sample_return in fixture.get("returns", []):
            db.execute("INSERT INTO return_requests(order_id,user_id,reason,status) VALUES(?,?,?,?)", (orders[sample_return["order_id"]], users[sample_return["customer_id"]], sample_return["reason"], sample_return["status"]))
        for sale in fixture["flash_sales"]:
            variant = db.execute("SELECT * FROM variants WHERE sku=?", (sale["sku"],)).fetchone()
            if variant:
                db.execute("UPDATE variants SET list_price=price,price=price-?,sale_end=datetime('now','+7 days') WHERE id=?", (sale["discount"], variant["id"]))
        for product in db.execute("SELECT * FROM products").fetchall():
            db.execute("UPDATE products SET stock=COALESCE((SELECT SUM(stock) FROM variants WHERE product_id=? AND active=1),0),price=COALESCE((SELECT MIN(price) FROM variants WHERE product_id=? AND active=1),price) WHERE id=?", (product["id"], product["id"], product["id"]))
            if not db.execute("SELECT 1 FROM product_images WHERE product_id=?", (product["id"],)).fetchone():
                urls = [f"/static/images/{product['image'] or product['category']}.svg"]
                if product["category"] == "laptop":
                    urls.append("/static/images/hero-laptop.svg")
                for index, url in enumerate(urls):
                    db.execute("INSERT INTO product_images(product_id,url,alt,sort_order) VALUES(?,?,?,?)", (product["id"], url, product["name"] + ' — Tham khảo ' + str(index+1), index))
        db.execute("INSERT INTO demo_imports(name) VALUES(?)", (fixture["fixture_id"],))
    return 'Imported linked UI data. Existing accounts and orders preserved.'


def _sync_demo_points(db, fixture_id):
    for order in db.execute("SELECT id,user_id,total FROM orders WHERE checkout_key LIKE ? AND status='Hoàn tất' AND points_awarded=0 AND total>=100000", (fixture_id+":%",)).fetchall():
        points = order["total"] // 100000
        db.execute("UPDATE orders SET points_awarded=? WHERE id=?", (points,order["id"]))
        db.execute("UPDATE users SET points=points+? WHERE id=?", (points,order["user_id"]))


def session_secret():
    configured = os.environ.get("NEU_SESSION_SECRET")
    if configured:
        return configured
    path = ROOT / "data" / ".session-secret"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-demo", action="store_true")
    parser.add_argument("--import-catalog", type=Path)
    args = parser.parse_args()
    if args.seed_demo:
        print(seed_ui_demo())
    if args.import_catalog:
        print(import_catalog(args.import_catalog))
