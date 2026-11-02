import hmac
import html
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from .db import DB_PATH, IMAGES, ROOT, connect, get_settings

templates = Jinja2Templates(directory=ROOT / "app/templates")
METHODS = {"cod": "Thanh toán khi nhận hàng", "qr": "QR demo", "card": "Thẻ ATM / quốc tế demo", "wallet": "Ví điện tử demo"}
SHIPPING = {"standard": ("Giao tiêu chuẩn demo", 30000), "express": ("Giao nhanh demo", 50000), "pickup": ("Nhận tại điểm demo", 0)}
STATUSES = ("Chờ thanh toán", "Chờ xác nhận", "Đang chuẩn bị", "Đang giao", "Hoàn tất", "Đã hủy", "Đã trả hàng")
TRANSITIONS = {"Chờ xác nhận": ("Đang chuẩn bị", "Đã hủy"), "Đang chuẩn bị": ("Đang giao", "Đã hủy"), "Đang giao": ("Hoàn tất",)}
UPLOAD_DIR = DB_PATH.parent / "uploads"


def money(value):
    return f"{int(value or 0):,}".replace(",", ".") + " ₫"


def localtime(value):
    if not value:
        return "—"
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M")


templates.env.filters.update(money=money, localtime=localtime)


def richtext(value):
    def inline(text):
        text = html.escape(text)
        text = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\[([^\]\n]+)\]\((https://[^\s)]+|/[^\s)]*)\)', r'<a href="\2" rel="noopener noreferrer">\1</a>', text)
        return text
    result, paragraph, listing = [], [], False
    for line in str(value or '').splitlines() + ['']:
        line = line.strip()
        if not line or line.startswith(('## ', '### ', '- ')):
            if paragraph:
                result.append('<p>' + '<br>'.join(paragraph) + '</p>')
                paragraph = []
            if listing and not line.startswith('- '):
                result.append('</ul>')
                listing = False
            if line.startswith('- '):
                if not listing:
                    result.append('<ul>')
                    listing = True
                result.append('<li>' + inline(line[2:]) + '</li>')
            elif line.startswith('### '):
                result.append('<h3>' + inline(line[4:]) + '</h3>')
            elif line.startswith('## '):
                result.append('<h2>' + inline(line[3:]) + '</h2>')
        else:
            paragraph.append(inline(line))
    return Markup('\n'.join(result))


templates.env.filters['richtext'] = richtext


def user_of(request):
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE id=? AND active=1", (request.session.get("user_id"),)).fetchone()
    if user and user["auth_rev"] == request.session.get("auth_rev", 0):
        return user
    request.session.pop("user_id", None)
    return None


def require_user(request):
    user = user_of(request)
    if not user:
        raise HTTPException(401, "Vui lòng đăng nhập để tiếp tục.")
    return user


def require_admin(request):
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(403, "Bạn không có quyền quản trị.")
    return user


def integer(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def redirect(path, request=None, message=None):
    if request and message:
        request.session["flash"] = message
    return RedirectResponse(path, status_code=303)


async def form_data(request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0]
    if content_type not in ("application/x-www-form-urlencoded", "multipart/form-data"):
        raise HTTPException(415, "Định dạng biểu mẫu không hợp lệ.")
    if integer(request.headers.get("content-length")) > 4_500_000:
        raise HTTPException(413, "Biểu mẫu quá lớn. Ảnh tối đa 2 MB.")
    data = await request.form(max_files=2, max_fields=80, max_part_size=3_000_000)
    if any(key != "photo" and not isinstance(value, str) for key, value in data.multi_items()):
        raise HTTPException(400, "Trường dữ liệu trong biểu mẫu không hợp lệ.")
    token = data.get("csrf", "")
    if not isinstance(token, str) or not hmac.compare_digest(token.encode(), request.session["csrf"].encode()):
        raise HTTPException(403, "Phiên biểu mẫu đã hết hạn. Tải lại trang rồi thử lại.")
    return data


async def upload(data, name="photo"):
    file = data.get(name)
    if not file or not getattr(file, "filename", ""):
        return ""
    try:
        content = await file.read(2_000_001)
    finally:
        await file.close()
    if len(content) > 2_000_000:
        raise HTTPException(400, "Ảnh tối đa 2 MB.")
    extension = "png" if content.startswith(b"\x89PNG\r\n\x1a\n") else "jpg" if content.startswith(b"\xff\xd8\xff") else ""
    if not extension:
        raise HTTPException(400, "Chỉ chấp nhận ảnh PNG hoặc JPEG.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(16)}.{extension}"
    (UPLOAD_DIR / name).write_bytes(content)
    return "/media/" + name


def image_for(product):
    return product["media"] or f"/static/images/{product['image'] or product['category']}.svg"


templates.env.globals["image_for"] = image_for


def read_cart(request):
    user = user_of(request)
    if user:
        with connect() as db:
            return {str(row["variant_id"]): {"quantity": row["quantity"], "selected": row["selected"]} for row in db.execute("SELECT * FROM account_cart WHERE user_id=?", (user["id"],))}
    raw = request.session.get("cart", {})
    if request.session.get("cart_version") != 2:
        converted = {}
        with connect() as db:
            for key, quantity in raw.items():
                row = db.execute("SELECT id FROM variants WHERE product_id=? ORDER BY id LIMIT 1", (key,)).fetchone()
                if row:
                    converted[str(row["id"])] = {"quantity": quantity, "selected": 1}
        raw = converted
        request.session.update(cart=raw, cart_version=2)
    return raw


def write_cart(request, cart):
    user = user_of(request)
    if user:
        with connect() as db:
            db.execute("DELETE FROM account_cart WHERE user_id=?", (user["id"],))
            db.executemany("INSERT INTO account_cart(user_id,variant_id,quantity,selected) VALUES(?,?,?,?)", [(user["id"], integer(key), value["quantity"], value["selected"]) for key, value in cart.items()])
    else:
        request.session.update(cart=cart, cart_version=2)


def sign_in(request, user):
    voucher = request.session.get("cart_voucher", "")
    visitor_key = request.session.get('visitor_key')
    guest = read_cart(request) if not user_of(request) else {}
    request.session.clear()
    request.session.update(user_id=user["id"], auth_rev=user["auth_rev"], csrf=secrets.token_urlsafe(32), cart_version=2)
    if visitor_key:
        request.session['visitor_key'] = visitor_key
    if voucher:
        request.session["cart_voucher"] = voucher
    cart = read_cart(request)
    with connect() as db:
        for key, value in guest.items():
            variant = db.execute("SELECT stock FROM variants WHERE id=? AND active=1", (key,)).fetchone()
            if variant and variant["stock"]:
                cart[key] = {"quantity": min(99, variant["stock"], value["quantity"] + cart.get(key, {}).get("quantity", 0)), "selected": 1}
    write_cart(request, cart)


def cart_lines(request, selected_only=False, db=None):
    cart = read_cart(request)
    lines = []
    def fill(connection):
        for key, value in cart.items():
            if selected_only and not value["selected"]:
                continue
            row = connection.execute("SELECT v.*,p.name,p.category,p.image,p.media AS product_media,(p.active*b.active*c.active*COALESCE(sc.active,1)*CASE WHEN p.deleted_at IS NULL THEN 1 ELSE 0 END) AS product_active,p.summary FROM variants v JOIN products p ON p.id=v.product_id JOIN brands b ON b.id=p.brand_id JOIN categories c ON c.slug=p.category LEFT JOIN categories sc ON sc.slug=p.subcategory WHERE v.id=?", (key,)).fetchone()
            if row:
                item = dict(row)
                item.update(quantity=value["quantity"], selected=value["selected"], subtotal=row["price"] * value["quantity"], photo=row["media"] or row["product_media"] or f"/static/images/{row['image'] or row['category']}.svg")
                lines.append(item)
        return lines
    if db:
        return fill(db)
    with connect() as connection:
        return fill(connection)


def render(request, template, status_code=200, **context):
    user = user_of(request)
    with connect() as db:
        category_rows = db.execute('SELECT * FROM categories WHERE active=1 ORDER BY rowid').fetchall()
        categories = {row['slug']: row['name'] for row in category_rows if not row['parent_slug']}
        category_labels = {row['slug']: row['name'] for row in category_rows if not row['parent_slug'] or row['parent_slug'] in categories}
        category_tree = {slug: [row for row in category_rows if row['parent_slug']==slug] for slug in categories}
        brands = db.execute("SELECT * FROM brands WHERE active=1 ORDER BY name").fetchall()
        unread = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user["id"],)).fetchone()[0] if user else 0
        demo_loaded = db.execute("SELECT 1 FROM demo_imports LIMIT 1").fetchone() is not None
        ceiling = db.execute("SELECT COALESCE(MAX(price),1000000) FROM variants").fetchone()[0]
        admin_alerts = db.execute("SELECT COUNT(*) FROM orders WHERE status='Chờ xác nhận'").fetchone()[0] if user and user["role"] == "admin" else 0
        site = get_settings(db)
        site_pages = db.execute('SELECT slug,title,summary,image FROM site_pages WHERE active=1 ORDER BY rowid').fetchall()
        visits = {'views': db.execute('SELECT COALESCE(SUM(views),0) FROM page_visits').fetchone()[0], 'visitors': db.execute('SELECT COUNT(*) FROM visitor_sessions').fetchone()[0], 'online': db.execute('SELECT COUNT(*) FROM visitor_sessions WHERE last_seen>=?', (int(time.time())-180,)).fetchone()[0]}
    base = {"request": request, "user": user, "categories": categories, "brands": brands, "images": IMAGES,
            "statuses": STATUSES, "methods": METHODS, "shipping_options": SHIPPING, "csrf": request.session["csrf"],
            "cart_count": sum(v["quantity"] for v in read_cart(request).values()), "unread": unread,
            "flash": request.session.pop("flash", None),
            "title": "NEU SHOP", "errors": {}, "values": {}, "section": "", "account_section": ""}
    base.update(demo_loaded=demo_loaded, price_ceiling=max(1000000, ((ceiling+99999)//100000)*100000), admin_alerts=admin_alerts)
    base.update(site=site,site_pages=site_pages,category_labels=category_labels,category_tree=category_tree,visits=visits)
    base.update(context)
    return templates.TemplateResponse(request=request, name=template, context=base, status_code=status_code)


def notify(db, user_id, title, content, url="/account"):
    db.execute("INSERT INTO notifications(user_id,title,content,url) VALUES(?,?,?,?)", (user_id, title, content, url))


def audit(db, actor_id, action, detail):
    db.execute("INSERT INTO audit_logs(actor_id,action,detail) VALUES(?,?,?)", (actor_id, action, detail))


def refresh_product(db, product_id):
    db.execute("UPDATE products SET stock=COALESCE((SELECT SUM(stock) FROM variants WHERE product_id=? AND active=1),0),price=COALESCE((SELECT MIN(price) FROM variants WHERE product_id=? AND active=1),price) WHERE id=?", (product_id, product_id, product_id))


def move_stock(db, variant_id, quantity, reason, actor_id=None):
    row = db.execute("SELECT * FROM variants WHERE id=?", (variant_id,)).fetchone()
    if not row or row["stock"] + quantity < 0:
        raise HTTPException(400, "Tồn kho không đủ cho thao tác này.")
    db.execute("UPDATE variants SET stock=stock+? WHERE id=?", (quantity, variant_id))
    db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason,actor_id) VALUES(?,?,?,?)", (variant_id, quantity, reason, actor_id))
    refresh_product(db, row["product_id"])


def event(db, order, status, note=""):
    db.execute("INSERT INTO order_events(order_id,status,note) VALUES(?,?,?)", (order["id"], status, note))
    notify(db, order["user_id"], f"Đơn NEU-{order['id']:05d}", status + (": " + note if note else ""), f"/orders/{order['id']}")


def finish_order(db, order):
    if order["status"] != "Đang giao":
        raise HTTPException(400, "Đơn chưa ở trạng thái đang giao/chờ nhận.")
    points = order["total"] // 100000
    db.execute("UPDATE orders SET status='Hoàn tất',completed_at=CURRENT_TIMESTAMP,points_awarded=? WHERE id=?", (points, order["id"]))
    db.execute("UPDATE users SET points=points+? WHERE id=?", (points, order["user_id"]))
    if order["payment_method"] == "cod":
        db.execute("UPDATE payments SET status='Thành công',paid_at=CURRENT_TIMESTAMP WHERE order_id=? AND method='cod' AND status='Chờ thanh toán'", (order["id"],))
        db.execute("UPDATE orders SET payment_status='Đã thanh toán' WHERE id=?", (order["id"],))


def cancel_order(db, order, actor_id=None, note=""):
    if order["status"] not in ("Chờ thanh toán", "Chờ xác nhận", "Đang chuẩn bị"):
        raise HTTPException(400, "Đơn không còn ở trạng thái có thể hủy.")
    db.execute("UPDATE orders SET status='Đã hủy',expires_at=NULL WHERE id=?", (order["id"],))
    for item in db.execute("SELECT * FROM order_items WHERE order_id=?", (order["id"],)).fetchall():
        if item["variant_id"]:
            move_stock(db, item["variant_id"], item["quantity"], f"Hoàn tồn đơn {order['id']}", actor_id)
    if order["voucher_id"]:
        db.execute("UPDATE vouchers SET used_count=MAX(used_count-1,0) WHERE id=?", (order["voucher_id"],))
    db.execute("UPDATE payments SET status='Đã hủy' WHERE order_id=? AND status='Chờ thanh toán'", (order["id"],))
    if order["payment_status"] == "Đã thanh toán":
        refund(db, order)
    event(db, order, "Đã hủy", note)
    void_contract(db, order['id'], actor_id, note or 'Đơn hàng đã hủy.')


def void_contract(db, order_id, actor_id, reason):
    contract = db.execute("SELECT id FROM sales_contracts WHERE order_id=? AND status!='void'", (order_id,)).fetchone()
    if contract:
        db.execute("UPDATE sales_contracts SET status='void',void_reason=?,otp_hash='',otp_demo_code='',otp_session_hash='' WHERE id=?", (reason,contract['id']))
        db.execute("INSERT INTO contract_events(contract_id,actor_id,action,detail) VALUES(?,?,'void',?)", (contract['id'],actor_id,reason))


def refund(db, order):
    if db.execute("SELECT 1 FROM payments WHERE order_id=? AND kind='refund' AND status='Thành công'", (order["id"],)).fetchone():
        return
    db.execute("INSERT INTO payments(order_id,method,amount,status,reference,kind,paid_at) VALUES(?,?,?,'Thành công',?,'refund',CURRENT_TIMESTAMP)", (order["id"], order["payment_method"], order["total"], "RF-" + secrets.token_hex(8)))
    db.execute("UPDATE orders SET payment_status='Đã hoàn tiền' WHERE id=?", (order["id"],))
    void_contract(db,order['id'],None,'Đơn hàng đã được hoàn tiền.')


def expire_orders():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        expired = db.execute("SELECT DISTINCT product_id FROM variants WHERE sale_end!='' AND sale_end<=datetime('now') AND list_price>price").fetchall()
        db.execute("UPDATE variants SET price=list_price,list_price=0,sale_end='' WHERE sale_end!='' AND sale_end<=datetime('now') AND list_price>price")
        for row in expired:
            refresh_product(db, row["product_id"])
        for order in db.execute("SELECT * FROM orders WHERE status='Chờ thanh toán' AND expires_at<=?", (int(time.time()),)).fetchall():
            cancel_order(db, order, note="Hết thời hạn thanh toán 15 phút.")


def order_for(db, user, order_id):
    row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row or (row["user_id"] != user["id"] and user["role"] != "admin"):
        raise HTTPException(404, "Không tìm thấy đơn hàng.")
    return row


def voucher_discount(db, code, subtotal):
    if not code:
        return None, 0
    voucher = db.execute("SELECT * FROM vouchers WHERE code=? AND active=1 AND date('now','+7 hours') BETWEEN start_date AND end_date", (code.strip().upper(),)).fetchone()
    if not voucher or voucher["used_count"] >= voucher["usage_limit"]:
        raise HTTPException(400, "Voucher không hợp lệ, đã hết hạn hoặc hết lượt sử dụng.")
    if subtotal < voucher["min_total"]:
        raise HTTPException(400, f"Voucher áp dụng cho đơn từ {money(voucher['min_total'])}.")
    discount = voucher["value"] if voucher["kind"] == "fixed" else subtotal * voucher["value"] // 100
    if voucher["kind"] == "percent" and voucher["max_discount"]:
        discount = min(discount, voucher["max_discount"])
    return voucher, min(discount, subtotal)
