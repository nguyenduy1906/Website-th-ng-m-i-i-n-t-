import math
import json
import re
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .core import METHODS, SHIPPING, cart_lines, event, form_data, image_for, integer, move_stock, order_for, read_cart, redirect, render, require_signed_contract, require_user, user_of, voucher_discount, write_cart
from .contracts import create_order_contract
from .db import ROOT, connect

router = APIRouter()
PRODUCT_SELECT = """SELECT p.*,b.name AS brand_name,
    (SELECT ROUND(AVG(rating),1) FROM reviews r WHERE r.product_id=p.id AND r.visible=1) AS rating,
    (SELECT COUNT(*) FROM reviews r WHERE r.product_id=p.id AND r.visible=1) AS review_count,
    (SELECT COUNT(*) FROM reviews r WHERE r.product_id=p.id AND r.visible=1 AND r.is_demo=1) AS demo_review_count,
    (SELECT id FROM variants v WHERE v.product_id=p.id AND v.active=1 ORDER BY v.price,v.id LIMIT 1) AS default_variant,
    (SELECT list_price FROM variants v WHERE v.product_id=p.id AND v.active=1 ORDER BY v.price,v.id LIMIT 1) AS list_price,
    (SELECT sale_end FROM variants v WHERE v.product_id=p.id AND v.active=1 ORDER BY v.price,v.id LIMIT 1) AS sale_end
    FROM products p JOIN brands b ON b.id=p.brand_id JOIN categories c ON c.slug=p.category"""
PUBLIC = "p.active=1 AND p.deleted_at IS NULL AND b.active=1 AND c.active=1 AND (p.subcategory IS NULL OR EXISTS(SELECT 1 FROM categories sub WHERE sub.slug=p.subcategory AND sub.active=1))"


def product_or_404(db, product_id):
    product = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND p.id=?", (product_id,)).fetchone()
    if not product:
        raise HTTPException(404, "Không tìm thấy sản phẩm.")
    return product


@router.get("/")
def home(request: Request):
    with connect() as db:
        products = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " ORDER BY p.featured DESC,p.id LIMIT 8").fetchall()
        vouchers = db.execute("SELECT * FROM vouchers WHERE active=1 AND date('now','+7 hours') BETWEEN start_date AND end_date AND used_count<usage_limit LIMIT 2").fetchall()
        articles = db.execute("SELECT a.* FROM articles a LEFT JOIN article_topics t ON t.id=a.topic_id WHERE a.active=1 AND (t.active=1 OR a.topic_id IS NULL) ORDER BY a.id DESC LIMIT 6").fetchall()
        latest = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND p.category='phone' ORDER BY p.id DESC LIMIT 8").fetchall()
        sales = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND EXISTS(SELECT 1 FROM variants WHERE product_id=p.id AND active=1 AND list_price>price AND sale_end>datetime('now')) ORDER BY p.id LIMIT 8").fetchall()
        sales = [p for p in sales if p["list_price"] and p["list_price"] > p["price"] and p["sale_end"]]
        featured_brands = db.execute("SELECT b.id,b.name,COUNT(*) AS products FROM brands b JOIN products p ON p.brand_id=b.id WHERE b.active=1 AND p.active=1 GROUP BY b.id").fetchall()
        category_sections = [(key, db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND p.category=? ORDER BY p.id DESC LIMIT 8", (key,)).fetchall()) for key in ('audio', 'accessory')]
        spotlight_products = {key: db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND p.category=? ORDER BY p.featured DESC,p.id LIMIT 1", (key,)).fetchone() for key in ('laptop', 'phone', 'audio', 'accessory')}
        category_counts = {row['category']: row['count'] for row in db.execute("SELECT p.category,COUNT(*) AS count FROM products p JOIN brands b ON b.id=p.brand_id JOIN categories c ON c.slug=p.category WHERE " + PUBLIC + " GROUP BY p.category")}
    logo_manifest = json.loads((ROOT / "docs/brand-logos.json").read_text(encoding="utf-8"))
    featured_brands = [{**dict(brand), 'logo':logo_manifest[str(brand['id'])]['path']} for brand in featured_brands if str(brand['id']) in logo_manifest]
    return render(request, "customer/home.html", title="NEU SHOP | Công nghệ cho học tập và cuộc sống", products=products, latest=latest, sales=sales, featured_brands=featured_brands, vouchers=vouchers, articles=articles, category_sections=category_sections, spotlight_products=spotlight_products, category_counts=category_counts)


@router.get("/products")
def catalog(request: Request, q: str = "", category: str = "", brand: str = "", sort: str = "newest", page: int = 1, min_price: str = "", max_price: str = "", rating: str = "", storage: str = "", color: str = ""):
    q = q.strip()[:100]
    conditions, params = [PUBLIC], []
    if q:
        conditions.append("(p.name LIKE ? OR p.summary LIKE ?)")
        params.extend([f"%{q}%"] * 2)
    if category:
        conditions.append("(p.category=? OR p.subcategory=?)")
        params.extend([category,category])
    if brand:
        conditions.append("p.brand_id=?")
        params.append(integer(brand))
    for value, operator in ((min_price, ">="), (max_price, "<=")):
        if value.strip() and integer(value, -1) >= 0:
            conditions.append(f"p.price {operator} ?")
            params.append(integer(value))
    if integer(rating):
        conditions.append("(SELECT AVG(rating) FROM reviews WHERE product_id=p.id AND visible=1)>=?")
        params.append(integer(rating))
    if storage:
        conditions.append("EXISTS(SELECT 1 FROM variants WHERE product_id=p.id AND active=1 AND storage LIKE ?)")
        params.append(f"%{storage[:60]}%")
    if color:
        conditions.append("EXISTS(SELECT 1 FROM variants WHERE product_id=p.id AND active=1 AND color LIKE ?)")
        params.append(f"%{color[:60]}%")
    sorting = {"newest": "p.id DESC", "featured": "p.featured DESC,p.id DESC", "price_asc": "p.price ASC", "price_desc": "p.price DESC", "name": "p.name ASC"}
    sort = sort if sort in sorting else "newest"
    query = {"q": q, "category": category, "brand": brand, "sort": sort, "min_price": min_price, "max_price": max_price, "rating": rating, "storage": storage, "color": color}
    with connect() as db:
        rows = db.execute(PRODUCT_SELECT + " WHERE " + " AND ".join(conditions) + " ORDER BY " + sorting[sort], params).fetchall()
    count, pages = len(rows), max(1, math.ceil(len(rows) / 12))
    page = min(max(page, 1), pages)
    return render(request, "customer/products.html", title="Khám phá sản phẩm", products=rows[(page-1)*12:page*12], count=count, page=page, page_links=[(n, "/products?" + urlencode({**query, "page": n})) for n in range(1, pages+1)], **query)


@router.get("/api/search")
def search(q: str = ""):
    with connect() as db:
        rows = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND p.name LIKE ? LIMIT 5", (f"%{q.strip()[:100]}%",)).fetchall() if q.strip() else []
    return [{"id": p["id"], "name": p["name"], "price": p["price"], "image": image_for(p)} for p in rows]


@router.get("/products/{product_id}")
def product_page(request: Request, product_id: int, variant: int = 0):
    user = user_of(request)
    with connect() as db:
        product = product_or_404(db, product_id)
        source = db.execute('SELECT * FROM product_sources WHERE product_id=?', (product_id,)).fetchone()
        variants = db.execute("SELECT * FROM variants WHERE product_id=? AND active=1 ORDER BY (stock>0) DESC,id", (product_id,)).fetchall()
        chosen = next((v for v in variants if v["id"] == variant), variants[0] if variants else None)
        related = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC + " AND p.category=? AND p.id!=? LIMIT 4", (product["category"], product_id)).fetchall()
        reviews = db.execute("SELECT r.*,u.name FROM reviews r JOIN users u ON u.id=r.user_id WHERE product_id=? AND visible=1 ORDER BY id DESC", (product_id,)).fetchall()
        questions = db.execute("SELECT q.*,u.name FROM questions q JOIN users u ON u.id=q.user_id WHERE product_id=? ORDER BY id DESC", (product_id,)).fetchall()
        eligible = db.execute("SELECT DISTINCT o.id FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.user_id=? AND i.product_id=? AND o.completed_at IS NOT NULL AND NOT EXISTS(SELECT 1 FROM reviews r WHERE r.order_id=o.id AND r.product_id=i.product_id AND r.user_id=o.user_id)", (user["id"], product_id)).fetchall() if user else []
        gallery = [dict(row) for row in db.execute("SELECT url,alt FROM product_images WHERE product_id=? ORDER BY sort_order,id", (product_id,))]
        primary = chosen["media"] if chosen and chosen["media"] else image_for(product)
        if not any(photo["url"] == primary for photo in gallery):
            gallery.insert(0, {"url": primary, "alt": product["name"]})
    return render(request, "customer/product.html", title=product["name"], product=product, source=source, variants=variants, chosen=chosen, related=related, reviews=reviews, questions=questions, eligible=eligible, gallery=gallery)


@router.post("/newsletter")
async def newsletter(request: Request):
    data = await form_data(request)
    email = data.get("email", "").strip().lower()
    if len(email)>200 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(400, "Email đăng ký bản tin không hợp lệ.")
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO newsletter_subscriptions(email) VALUES(?)", (email,))
    return redirect("/", request, "Đã lưu đăng ký nhận bản tin. Dịch vụ gửi email chưa được kết nối.")


@router.get("/api/cart-summary")
def cart_summary(request: Request):
    return {"count": sum(v["quantity"] for v in read_cart(request).values())}


@router.post("/cart/add")
async def cart_add(request: Request):
    data = await form_data(request)
    with connect() as db:
        if data.get("variant_id"):
            variant = db.execute("SELECT * FROM variants WHERE id=? AND active=1", (integer(data["variant_id"]),)).fetchone()
        else:
            variant = db.execute("SELECT * FROM variants WHERE product_id=? AND active=1 ORDER BY id LIMIT 1", (integer(data.get("product_id")),)).fetchone()
        if not variant:
            raise HTTPException(404, "Không tìm thấy phiên bản sản phẩm.")
        product_or_404(db, variant["product_id"])
    quantity = integer(data.get("quantity"), 1)
    if not 1 <= quantity <= 99:
        raise HTTPException(400, "Số lượng phải từ 1 đến 99.")
    cart = read_cart(request)
    key = str(variant["id"])
    quantity += cart.get(key, {}).get("quantity", 0)
    if quantity > min(99, variant["stock"]):
        if request.headers.get("x-requested-with") == "fetch":
            return JSONResponse({"message": "Số lượng vượt tồn kho hoặc giới hạn 99 sản phẩm."}, status_code=400)
        return redirect(f"/products/{variant['product_id']}", request, "Số lượng vượt tồn kho hoặc giới hạn 99 sản phẩm.")
    if not user_of(request) and key not in cart and len(cart) >= 15:
        return redirect("/cart", request, "Đăng nhập để lưu thêm sản phẩm vào giỏ.")
    cart[key] = {"quantity": quantity, "selected": 1}
    write_cart(request, cart)
    if request.headers.get("x-requested-with") == "fetch":
        return {"message": "Đã thêm sản phẩm vào giỏ hàng.", "count": sum(value["quantity"] for value in cart.values())}
    return redirect("/checkout" if data.get("buy_now") else "/cart", request, "Đã thêm sản phẩm vào giỏ hàng.")


@router.get("/cart")
def cart_page(request: Request):
    lines = cart_lines(request)
    return render(request, "customer/cart.html", title="Giỏ hàng", lines=lines, total=sum(i["subtotal"] for i in lines if i["selected"]))


@router.post("/cart/update")
async def cart_update(request: Request):
    data = await form_data(request)
    cart, key = read_cart(request), str(integer(data.get("variant_id")))
    if key in cart:
        if data.get("remove"):
            del cart[key]
        else:
            quantity = integer(data.get("quantity"))
            with connect() as db:
                row = db.execute("SELECT stock FROM variants WHERE id=? AND active=1", (key,)).fetchone()
            if not row or not 1 <= quantity <= min(99, row["stock"]):
                return redirect("/cart", request, "Kiểm tra lại số lượng và tồn kho.")
            cart[key]["quantity"] = quantity
        write_cart(request, cart)
    return redirect("/cart", request, "Đã cập nhật giỏ hàng.")


@router.post("/cart/select")
async def cart_select(request: Request):
    data = await form_data(request)
    selected = set(data.getlist("items"))
    cart = read_cart(request)
    for key, value in cart.items():
        value["selected"] = int(key in selected)
    write_cart(request, cart)
    return redirect("/checkout" if selected else "/cart", request, None if selected else "Chọn ít nhất một sản phẩm để đặt hàng.")


@router.post("/cart/voucher")
async def cart_voucher(request: Request):
    data = await form_data(request)
    code = data.get("voucher", "").strip().upper()[:30]
    subtotal = sum(line["subtotal"] for line in cart_lines(request, True))
    with connect() as db:
        try:
            _, discount = voucher_discount(db, code, subtotal)
        except HTTPException as error:
            return redirect("/cart", request, error.detail)
    request.session["cart_voucher"] = code
    return redirect("/cart", request, f"Voucher hợp lệ, giảm {discount:,} đồng. Áp dụng tại bước thanh toán." if code else "Đã bỏ mã ưu đãi.")


def checkout_stock_error(lines):
    issues = []
    for line in lines:
        name = line['name'] + ' (' + line['color'] + ' / ' + line['storage'] + ')'
        if not line['product_active']:
            issues.append(name + ': sản phẩm hiện ngừng bán hoặc không còn hiển thị trong danh mục')
        elif not line['active']:
            issues.append(name + ': phiên bản này đã ngừng bán')
        elif line['quantity'] > line['stock']:
            issues.append(name + ': bạn chọn ' + str(line['quantity']) + ', hiện chỉ còn ' + str(line['stock']) + ' sản phẩm')
    return '; '.join(issues) + '. Về giỏ hàng để bỏ chọn, xóa hoặc điều chỉnh sản phẩm này rồi đặt lại.' if issues else ''


def checkout_context(request, values=None):
    lines = cart_lines(request, True)
    subtotal = sum(line["subtotal"] for line in lines)
    values = values if values is not None else {"voucher": request.session.get("cart_voucher", "")}
    shipping = values.get("shipping_method", "standard")
    if shipping not in SHIPPING:
        shipping = "standard"
    fee = SHIPPING[shipping][1]
    error, discount = "", 0
    with connect() as db:
        addresses = db.execute("SELECT * FROM addresses WHERE user_id=? ORDER BY is_default DESC,id", (require_user(request)["id"],)).fetchall()
        vouchers = db.execute("SELECT * FROM vouchers WHERE active=1 AND date('now','+7 hours') BETWEEN start_date AND end_date AND used_count<usage_limit").fetchall()
        try:
            _, discount = voucher_discount(db, values.get("voucher", ""), subtotal)
        except HTTPException as exc:
            error = exc.detail
    request.session.setdefault("checkout_key", secrets.token_urlsafe(32))
    return {"lines": lines, "subtotal": subtotal, "shipping_fee": fee, "discount": discount, "total": subtotal+fee-discount, "addresses": addresses, "vouchers": vouchers, "checkout_key": request.session["checkout_key"], "values": values, "errors": {"voucher": error} if error else {}}


@router.get("/checkout")
def checkout_page(request: Request):
    if not user_of(request):
        return redirect("/login", request, "Đăng nhập để đặt hàng và lưu giỏ hàng của bạn.")
    context = checkout_context(request)
    if not context["lines"]:
        return redirect("/cart", request, "Chọn ít nhất một sản phẩm trong giỏ hàng.")
    return render(request, "customer/checkout.html", title="Đặt hàng", **context)


@router.post("/checkout")
async def checkout(request: Request):
    user = require_user(request)
    data = await form_data(request)
    key = data.get("checkout_key", "")
    import hmac
    with connect() as db:
        previous = db.execute("SELECT id FROM orders WHERE checkout_key=? AND user_id=?", (key, user["id"])).fetchone()
    if previous:
        with connect() as db:
            contract = db.execute("SELECT id FROM sales_contracts WHERE order_id=? AND status='draft'", (previous['id'],)).fetchone()
        return redirect(f"/contracts/{contract['id']}" if contract else f"/orders/{previous['id']}")
    if not key or not hmac.compare_digest(key.encode(), request.session.get("checkout_key", "").encode()):
        raise HTTPException(400, "Phiên đặt hàng hết hạn. Về giỏ hàng để thử lại.")
    values = {name: data.get(name, "").strip() for name in ("recipient", "phone", "address", "note", "voucher", "shipping_method", "payment_method", "address_id", "province", "district")}
    values["shipping_method"] = values["shipping_method"] or "standard"
    values["payment_method"] = values["payment_method"] or "cod"
    if values["address_id"]:
        with connect() as db:
            address = db.execute("SELECT * FROM addresses WHERE id=? AND user_id=?", (integer(values["address_id"]), user["id"])).fetchone()
        if not address:
            raise HTTPException(400, "Địa chỉ đã lưu không hợp lệ.")
        values.update({name: address[name] for name in ("recipient", "phone", "address")})
        values["province"], values["district"] = "", ""
    context = checkout_context(request, values)
    errors = context["errors"]
    if data.get("action") == "preview":
        return render(request, "customer/checkout.html", title="Kiểm tra đơn hàng", **context)
    if not 2 <= len(values["recipient"]) <= 80:
        errors["recipient"] = "Nhập tên người nhận từ 2 đến 80 ký tự."
    if not re.fullmatch(r"(?:0|\+84)[0-9]{9}", values["phone"]):
        errors["phone"] = "Nhập số điện thoại 10 số bắt đầu bằng 0 hoặc +84."
    if values["shipping_method"] != "pickup" and not 10 <= len(values["address"]) <= 300:
        errors["address"] = "Nhập địa chỉ đầy đủ từ 10 đến 300 ký tự."
    if values["shipping_method"] not in SHIPPING or values["payment_method"] not in METHODS:
        errors["general"] = "Phương thức nhận hàng hoặc thanh toán không hợp lệ."
    if len(values["note"]) > 500:
        errors["note"] = "Ghi chú tối đa 500 ký tự."
    full_address = values["address"]
    if (values["province"] or values["district"]) and values["shipping_method"] != "pickup":
        if not 2 <= len(values["province"]) <= 60:
            errors["province"] = "Nhập tỉnh/thành phố từ 2 đến 60 ký tự."
        if not 2 <= len(values["district"]) <= 80:
            errors["district"] = "Nhập phường/xã hoặc quận/huyện từ 2 đến 80 ký tự."
        full_address = ", ".join([values["address"], values["district"], values["province"]])
        if len(full_address) > 500:
            errors["address"] = "Địa chỉ đầy đủ tối đa 500 ký tự."
    if not context["lines"]:
        return redirect("/cart")
    if not errors:
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT id FROM orders WHERE checkout_key=? AND user_id=?", (key, user["id"])).fetchone()
            if previous:
                contract = db.execute("SELECT id FROM sales_contracts WHERE order_id=? AND status='draft'", (previous['id'],)).fetchone()
                return redirect(f"/contracts/{contract['id']}" if contract else f"/orders/{previous['id']}")
            lines = cart_lines(request, True, db)
            stock_error = checkout_stock_error(lines)
            if stock_error:
                errors["general"] = stock_error
            subtotal = sum(line["subtotal"] for line in lines)
            try:
                voucher, discount = voucher_discount(db, values["voucher"], subtotal)
            except HTTPException as exc:
                errors["voucher"] = exc.detail
            if not errors:
                fee = SHIPPING[values["shipping_method"]][1]
                total, online = subtotal + fee - discount, values["payment_method"] != "cod"
                status = "Chờ thanh toán" if online else "Chờ xác nhận"
                order_id = db.execute("INSERT INTO orders(user_id,recipient,phone,address,note,total,checkout_key,status,subtotal,shipping_fee,discount,voucher_id,receive_method,shipping_method,payment_method,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (user["id"], values["recipient"], values["phone"], full_address if values["shipping_method"] != "pickup" else 'Nhận tại điểm (không có địa chỉ cửa hàng thực tế)', values["note"], total, key, status, subtotal, fee, discount, voucher["id"] if voucher else None, "pickup" if values["shipping_method"] == "pickup" else "delivery", values["shipping_method"], values["payment_method"], int(time.time()) + 900 if online else None)).lastrowid
                for line in lines:
                    db.execute("INSERT INTO order_items(order_id,product_id,variant_id,name,variant_label,price,quantity,image) VALUES(?,?,?,?,?,?,?,?)", (order_id, line["product_id"], line["id"], line["name"], line["color"] + " / " + line["storage"], line["price"], line["quantity"], line["photo"]))
                    move_stock(db, line["id"], -line["quantity"], f"Giữ hàng đơn {order_id}", user["id"])
                if voucher:
                    db.execute("UPDATE vouchers SET used_count=used_count+1 WHERE id=?", (voucher["id"],))
                payment_id = db.execute("INSERT INTO payments(order_id,method,amount,reference) VALUES(?,?,?,?)", (order_id, values["payment_method"], total, "PAY-" + secrets.token_hex(10))).lastrowid
                event(db, {"id": order_id, "user_id": user["id"]}, status, "Đã lưu đơn và giữ tồn kho.")
                order = order_for(db, user, order_id)
                contract_id = create_order_contract(db, user, order)
        if not errors:
            cart = read_cart(request)
            write_cart(request, {key: value for key, value in cart.items() if not value["selected"]})
            request.session.pop("checkout_key", None)
            request.session.pop("cart_voucher", None)
            return redirect(f"/contracts/{contract_id}", request, "Đọc và xác nhận hợp đồng trước khi tiếp tục. Đơn online giữ hàng tối đa 15 phút từ lúc tạo đơn.")
    return render(request, "customer/checkout.html", 400, title="Kiểm tra thông tin đặt hàng", **context)


@router.get("/payments/{payment_id}")
def payment_page(request: Request, payment_id: int):
    user = require_user(request)
    with connect() as db:
        payment = db.execute("SELECT * FROM payments WHERE id=? AND kind='payment'", (payment_id,)).fetchone()
        if not payment:
            raise HTTPException(404, "Không tìm thấy giao dịch.")
        order = order_for(db, user, payment["order_id"])
        contract = db.execute('SELECT id,status FROM sales_contracts WHERE order_id=?', (order['id'],)).fetchone()
        if order['status'] == 'Chờ thanh toán' and (not contract or contract['status'] != 'signed'):
            return redirect(f"/contracts/{contract['id']}" if contract else f"/orders/{order['id']}", request, 'Vui lòng xác nhận hợp đồng trước khi thanh toán.')
        if order['status'] == 'Chờ thanh toán':
            require_signed_contract(db, order['id'])
    return render(request, "customer/payment.html", title='Thanh toán ', payment=payment, order=order)


@router.post("/payments/{payment_id}/simulate")
async def simulate_payment(request: Request, payment_id: int):
    user = require_user(request)
    data = await form_data(request)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        payment = db.execute("SELECT * FROM payments WHERE id=? AND kind='payment'", (payment_id,)).fetchone()
        if not payment:
            raise HTTPException(404, "Không tìm thấy giao dịch.")
        order = order_for(db, user, payment["order_id"])
        if order["status"] != "Chờ thanh toán" or payment["status"] != "Chờ thanh toán" or payment["method"] == "cod":
            return redirect(f"/orders/{order['id']}", request, "Giao dịch này không còn chờ xử lý.")
        require_signed_contract(db, order['id'])
        result = data.get("result")
        if result not in ("success", "failed"):
            raise HTTPException(400, 'Kết quả thử nghiệm không hợp lệ.')
        if payment["amount"] != order["total"]:
            raise HTTPException(400, "Số tiền giao dịch không khớp đơn hàng.")
        success = result == "success"
        db.execute("UPDATE payments SET status=?,paid_at=CURRENT_TIMESTAMP WHERE id=?", ("Thành công" if success else "Thất bại", payment_id))
        if success:
            db.execute("UPDATE orders SET payment_status='Đã thanh toán',status='Chờ xác nhận',expires_at=NULL WHERE id=?", (order["id"],))
            event(db, order, "Chờ xác nhận", 'Thanh toán thành công.')
        else:
            event(db, order, "Chờ thanh toán", "Thanh toán thất bại; có thể thử lại trong thời hạn giữ hàng.")
    return redirect(f"/orders/{order['id']}")


@router.get("/offers")
def offers(request: Request):
    with connect() as db:
        vouchers = db.execute("SELECT * FROM vouchers WHERE active=1 AND date('now','+7 hours') BETWEEN start_date AND end_date AND used_count<usage_limit").fetchall()
    return render(request, "customer/offers.html", title="Ưu đãi dành cho bạn", vouchers=vouchers)


@router.get("/news")
@router.get("/news/{article_id}")
def news(request: Request, article_id: int = 0, topic: str = '', q: str = ''):
    with connect() as db:
        articles = db.execute("SELECT a.*,t.name AS topic_name FROM articles a LEFT JOIN article_topics t ON t.id=a.topic_id WHERE a.active=1 AND (t.active=1 OR a.topic_id IS NULL) AND (?='' OR a.topic_id=?) AND (a.title LIKE ? OR a.summary LIKE ?) ORDER BY a.id DESC",(topic,integer(topic),*([f'%{q[:100]}%']*2))).fetchall()
        article = db.execute("SELECT a.*,t.name AS topic_name FROM articles a LEFT JOIN article_topics t ON t.id=a.topic_id WHERE a.id=? AND a.active=1 AND (t.active=1 OR a.topic_id IS NULL)", (article_id,)).fetchone() if article_id else None
        topics = db.execute('SELECT * FROM article_topics WHERE active=1 ORDER BY name').fetchall()
        related = db.execute('SELECT * FROM articles WHERE active=1 AND id!=? ORDER BY (topic_id=?) DESC,id DESC LIMIT 6',(article_id,article['topic_id'])).fetchall() if article else []
    if article_id and not article:
        raise HTTPException(404, "Không tìm thấy bài viết.")
    article_sections = re.findall(r'^## (.+)$', article['content'], re.MULTILINE) if article else []
    reading_minutes = max(1, math.ceil(len(article['content'].split()) / 200)) if article else 0
    return render(request, "customer/news.html", title=article["title"] if article else "Góc công nghệ", articles=articles, article=article,topics=topics,related=related,topic=topic,q=q[:100],article_sections=article_sections,reading_minutes=reading_minutes)


@router.get("/policies")
def policies(request: Request):
    return render(request, "customer/policies.html", title='Hướng dẫn và chính sách ')


def retrieve_chatbot(q: str = ""):
    import unicodedata

    def normalize(value):
        return "".join(c for c in unicodedata.normalize("NFD", value.lower().replace("đ", "d")) if unicodedata.category(c) != "Mn")

    question = normalize(q.strip()[:500])
    conversation = question.strip(" !?.")
    if re.fullmatch(r"(?:ban|bot|chatbot|tro ly|shop) (?:la ai|la gi|ten (?:la )?gi)(?: vay| nhi| a| the)?", conversation) or conversation in {"who are you", "gioi thieu ban than", "ban co phai ai khong"}:
        return {"answer": "Mình là trợ lý tư vấn của NEU SHOP. Mình giúp bạn tìm sản phẩm, xem giá, phiên bản, thông số và hướng dẫn mua hàng từ dữ liệu cửa hàng. Bạn đang cần hỗ trợ gì?", "products": [], "intent": "conversation"}
    if conversation in {"ban lam duoc gi", "ban giup duoc gi", "ban co the lam gi", "chuc nang cua ban", "huong dan su dung chatbot"}:
        return {"answer": "Mình có thể tìm thiết bị theo tên hoặc ngân sách, tra cứu giá và tồn kho từng phiên bản, và hướng dẫn đặt hàng, thanh toán, giao hàng, đổi trả tại NEU SHOP. Bạn hãy nêu nhu cầu hoặc tên sản phẩm nhé.", "products": [], "intent": "conversation"}
    if conversation in {"cam on", "cam on ban", "thanks", "thank you", "tam biet", "bye"}:
        return {"answer": "Rất vui được hỗ trợ bạn! Khi cần tư vấn sản phẩm NEU SHOP, bạn cứ nhắn mình nhé.", "products": [], "intent": "conversation"}
    if not question or question.strip(" !?.") in {"xin chao", "chao", "hello", "hi", "chao shop", "chao ban"}:
        return {"answer": "Chào bạn! Bạn muốn tìm sản phẩm nào, với ngân sách bao nhiêu?", "products": [], "intent": "conversation"}
    if 'thanh toan' in question and not any(term in question for term in ('tra gop', 'chuyen khoan')):
        return {"answer": 'Bạn thanh toán trên NEU SHOP theo các bước sau:\n1. Mở Giỏ hàng ở đầu trang, tích chọn sản phẩm muốn mua rồi bấm Đặt hàng đã chọn. Nếu chưa đăng nhập, hãy đăng nhập trước khi tiếp tục.\n2. Ở trang Hoàn tất đơn hàng, chọn địa chỉ đã lưu hoặc nhập họ tên, số điện thoại và địa chỉ nhận hàng.\n3. Chọn Vận chuyển / nhận hàng và Phương thức thanh toán; nhập Mã ưu đãi nếu có.\n4. Kiểm tra sản phẩm, tiền hàng, phí vận chuyển, giảm giá và Tổng thanh toán, rồi bấm Tiếp tục xem hợp đồng, đọc và xác nhận bằng OTP.\n5. Sau khi xác nhận hợp đồng, nếu chọn COD, theo dõi đơn chờ admin duyệt. Nếu chọn QR, thẻ hoặc ví, bấm Tiếp tục thanh toán để mở màn hình thử nghiệm: bấm Ghi nhận thanh toán thành công để ghi nhận kết quả, hoặc Ghi nhận thanh toán thất bại để thử luồng lỗi.\nBạn có thể xem lại kết quả trong Đơn hàng của tôi. Không nhập thông tin ngân hàng thật vào màn hình thử nghiệm.', "products": [], "url": "/cart", "link_label": "Mở giỏ hàng"}
    policies = [
        (("doi tra", "hoan tien", "huy don"), 'Bạn có thể hủy đơn trước khi chuẩn bị hàng; yêu cầu trả toàn bộ đơn trong 7 ngày sau hoàn tất. Admin xét duyệt, kiểm hàng và hoàn tiền thử nghiệm. Xem chi tiết tại Chính sách mua hàng.', "/policies"),
        (("thanh toan", "tra gop", "chuyen khoan"), 'Bản local hỗ trợ thử nghiệm COD, QR, thẻ và ví. Chưa tích hợp ngân hàng hay trả góp thực tế; không thu tiền thật.', "/policies"),
        (("giao hang", "van chuyen", "phi ship"), 'Phí giao tiêu chuẩn 30.000 đồng, nhanh 50.000 đồng; nhận tại điểm 0 đồng. Website chỉ thử nghiệm giao hàng. Tổng phí được hiển thị khi thanh toán.', "/policies"),
        (("dat hang", "mua hang", "gio hang"), "Để mua hàng: mở sản phẩm → chọn Phiên bản và Số lượng → bấm Thêm vào giỏ hoặc Mua ngay. Nếu vào giỏ, tích sản phẩm muốn mua và bấm Đặt hàng đã chọn. Đăng nhập nếu được yêu cầu, nhập thông tin nhận hàng, chọn cách vận chuyển và thanh toán, kiểm tra tổng tiền rồi bấm Tiếp tục xem hợp đồng, đọc và xác nhận bằng OTP.", "/products"),
        (("don hang", "theo doi don"), "Đăng nhập và mở Đơn hàng của tôi để xem trạng thái và chi tiết đơn. Chatbot không truy cập thông tin đơn hàng cá nhân.", "/account/orders"),
    ]
    for keywords, answer, url in policies:
        if any(word in question for word in keywords):
            return {"answer": answer, "products": [], "url": url}
    words = re.findall(r"[a-z0-9]+", question)
    ignored = set("ai duoc lam the vay nhi a oi ten giup ho tro chuc nang ve noi dung ngay hom nay toi minh ban cho hoi co nao la cua voi va can tim muon mua gia bao nhieu duoi tren tam khoang trieu dong san pham tot phu hop khong gi hay tu van con hang shop neu dang ban re nhat dat nhat nhung cac mot chiec may tinh xach tay dien thoai tai nghe phu kien laptop smartphone loai den tu trong xin chao".split())
    category = next((value for key, value in [("may tinh xach tay", "laptop"), ("laptop", "laptop"), ("dien thoai", "phone"), ("smartphone", "phone"), ("tai nghe", "audio"), ("loa", "audio"), ("phu kien", "accessory")] if key in question), None)
    amounts = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*(trieu|tr|k|nghin|ngan)\b", question))
    minimum, maximum = 0, float("inf")
    if amounts:
        values = [float(m[1].replace(',', '.')) * (1000000 if m[2] in ('trieu','tr') else 1000) for m in amounts]
        if len(values)>1 and any(word in question for word in (' den ', ' toi ', ' - ')):
            minimum, maximum = min(values), max(values)
        elif re.search(r"(?:tren|hon|tu)\s*$", question[:amounts[0].start()]):
            minimum = values[0]
        else:
            maximum = values[0]
    product_question = question
    for amount in reversed(amounts):
        product_question = product_question[:amount.start()] + ' ' + product_question[amount.end():]
    terms = [word for word in re.findall(r"[a-z0-9]+", product_question) if word not in ignored]
    if any(word in question for word in ("thoi tiet", "chinh tri", "bong da", "nau an")):
        return {"answer": "Mình chỉ hỗ trợ sản phẩm công nghệ và mua sắm tại NEU SHOP. Bạn muốn tìm thiết bị nào?", "products": []}
    with connect() as db:
        rows = db.execute(PRODUCT_SELECT + " WHERE " + PUBLIC).fetchall()
        brands = {normalize(row['name']) for row in db.execute('SELECT name FROM brands WHERE active=1')}
        matches = []
        for row in rows:
            if category and row['category'] != category:
                continue
            title = normalize(row['name'])
            title_tokens = set(re.findall(r"[a-z0-9]+", title))
            requested_brands = [brand for brand in brands if re.search(r"\b" + re.escape(brand) + r"\b", question)]
            if requested_brands and normalize(row['brand_name']) not in requested_brands:
                continue
            identifiers = [term for term in terms if any(c.isdigit() for c in term) or term in {"pro", "max", "air", "ultra", "plus", "mini"}]
            if identifiers and not all(term in title_tokens for term in identifiers):
                continue
            title_hits = sum(term in title_tokens for term in terms)
            if not title_hits and not category:
                continue
            variants = [dict(v) for v in db.execute('SELECT id,color,storage,price,stock,media FROM variants WHERE product_id=? AND active=1 AND price>=? AND price<=? ORDER BY price,id', (row['id'],minimum, min(maximum,1000000000000)))]
            if not variants:
                continue
            if 'con hang' in question:
                variants = [v for v in variants if v['stock']>0]
                if not variants:
                    continue
            chosen = variants[0]
            score = title_hits * 10 + sum(term in normalize(row['specs'] or '').split() for term in terms)
            matches.append((score, {'image':chosen['media'] or image_for(row), 'name':row['name'], 'price':chosen['price'], 'specs':row['specs'], 'summary':row['summary'], 'stock':chosen['stock'], 'warranty':row['warranty'], 'variant':chosen['color']+' / '+chosen['storage'], 'variants':variants, 'url':'/products/'+str(row['id'])+'?variant='+str(chosen['id'])}))
    matches.sort(key=lambda item:(-item[0], -item[1]['price'] if 'dat nhat' in question else item[1]['price']))
    products = [item[1] for item in matches[:4]]
    if products:
        total = len(matches)
        response = f"NEU SHOP hiện có {total} sản phẩm phù hợp với yêu cầu của bạn."
        if total > len(products):
            response += f" Mình hiển thị {len(products)} sản phẩm đầu tiên bên dưới."
    else:
        response = 'Mình chưa tìm thấy sản phẩm phù hợp trong dữ liệu NEU SHOP. Bạn thử ghi rõ tên model, loại thiết bị hoặc ngân sách. Mình không tự lấy giá hay tồn kho của cửa hàng khác để trả lời thay NEU SHOP.'
    return {'answer':response, 'products':products, 'total':len(matches), 'shown':len(products)}



@router.get("/api/chatbot")
def chatbot(q: str = ""):
    from .chatbot_ai import answer
    return answer(q, retrieve_chatbot(q), [])


@router.post("/api/chatbot")
async def chatbot_conversation(request: Request):
    import json
    from starlette.concurrency import run_in_threadpool
    from .chatbot_ai import answer

    data = await form_data(request)
    question = str(data.get("q", "")).strip()[:500]
    if not question:
        raise HTTPException(400, "Vui lòng nhập câu hỏi.")
    raw_history = str(data.get("history", "[]"))
    if len(raw_history) > 20000:
        raise HTTPException(400, "Lịch sử quá dài.")
    try:
        history = json.loads(raw_history)
    except ValueError:
        raise HTTPException(400, "Lịch sử không hợp lệ.")
    if not isinstance(history, list):
        raise HTTPException(400, "Lịch sử không hợp lệ.")
    search_question = question
    import unicodedata
    normalized_question = ''.join(c for c in unicodedata.normalize('NFD', question.lower().replace('đ','d')) if unicodedata.category(c) != 'Mn')
    followup = re.match(r"^(?:con (?:mau|con|cai)|mau (?:nao|khac)|re hon|dat hon|duoi \d|tren \d|tam \d|gia cua (?:no|may do)|(?:ram|pin|bao hanh) (?:cua no|the nao))", normalized_question)
    if followup and history:
        previous = next((entry.get("text", "") for entry in reversed(history[-8:]) if isinstance(entry, dict) and entry.get("role") == "user" and isinstance(entry.get("text"), str)), "")
        search_question = question + " " + previous[:300]
    context = await run_in_threadpool(retrieve_chatbot, search_question)
    return await run_in_threadpool(answer, question, context, history)
