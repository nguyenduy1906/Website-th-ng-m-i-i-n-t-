import csv
import io
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from .core import TRANSITIONS, audit, cancel_order, event, finish_order, form_data, integer, move_stock, notify, order_for, redirect, refresh_product, refund, render, require_admin, upload
from .db import IMAGES, connect, password_hash

router = APIRouter(prefix="/admin")


@router.get("")
def dashboard(request: Request):
    require_admin(request)
    with connect() as db:
        stats = {"products": db.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0], "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], "pending": db.execute("SELECT COUNT(*) FROM orders WHERE status='Chờ xác nhận'").fetchone()[0], "revenue": db.execute("SELECT COALESCE(SUM(CASE WHEN kind='refund' THEN -amount ELSE amount END),0) FROM payments WHERE status='Thành công'").fetchone()[0]}
        orders = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8").fetchall()
        low_stock = db.execute("SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id WHERE v.stock<=5 AND v.active=1 AND p.active=1 ORDER BY v.stock LIMIT 6").fetchall()
        recent = db.execute("SELECT l.*,u.name FROM audit_logs l LEFT JOIN users u ON u.id=l.actor_id ORDER BY l.id DESC LIMIT 6").fetchall()
        series = {row["day"]: row["amount"] for row in db.execute("SELECT date(COALESCE(paid_at,created_at),'+7 hours') AS day,SUM(CASE WHEN kind='refund' THEN -amount ELSE amount END) AS amount FROM payments WHERE status='Thành công' AND date(COALESCE(paid_at,created_at),'+7 hours')>=date('now','+7 hours','-13 days') GROUP BY day")}
        today = datetime.now(timezone(timedelta(hours=7))).date()
        revenue_days = [{"day": (today-timedelta(days=13-i)).isoformat(), "amount": series.get((today-timedelta(days=13-i)).isoformat(),0)} for i in range(14)]
        scale = max([abs(day["amount"]) for day in revenue_days]+[1])
        for index, day in enumerate(revenue_days):
            day.update(x=50+index*42, height=abs(day["amount"])/scale*150, label=day["day"][5:])
        status_rows = db.execute("SELECT status,COUNT(*) AS count FROM orders GROUP BY status ORDER BY count DESC").fetchall()
        total = sum(row["count"] for row in status_rows)
        status_data, offset = [], 0
        for index,row in enumerate(status_rows):
            fraction = row["count"]/max(total,1)
            status_data.append({**dict(row),"length":fraction*100,"offset":-offset,"index":index%6})
            offset += fraction*100
        stock_alert_count = db.execute("SELECT COUNT(*) FROM variants v JOIN products p ON p.id=v.product_id WHERE v.active=1 AND p.active=1 AND v.stock<=5").fetchone()[0]
    return render(request, "admin/dashboard.html", title="Tổng quan cửa hàng", section="overview", stats=stats, orders=orders, low_stock=low_stock, recent=recent, revenue_days=revenue_days, status_data=status_data, stock_alert_count=stock_alert_count)


@router.get("/products")
def products(request: Request, q: str = "", category: str = ""):
    require_admin(request)
    with connect() as db:
        products = db.execute("SELECT p.*,b.name AS brand_name,(SELECT COUNT(*) FROM variants WHERE product_id=p.id) AS variant_count FROM products p LEFT JOIN brands b ON b.id=p.brand_id WHERE p.deleted_at IS NULL AND p.name LIKE ? AND (?='' OR p.category=? OR p.subcategory=?) ORDER BY p.id DESC", (f"%{q[:100]}%",category,category,category)).fetchall()
    return render(request, "admin/products.html", title="Quản lý sản phẩm", section="products", products=products, q=q[:100], selected_category=category)


@router.get("/products/new")
@router.get("/products/{product_id}/edit")
def product_form(request: Request, product_id: int = 0):
    require_admin(request)
    with connect() as db:
        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone() if product_id else None
        if product_id and not product:
            raise HTTPException(404, "Không tìm thấy sản phẩm.")
        variants = db.execute("SELECT * FROM variants WHERE product_id=? ORDER BY id", (product_id,)).fetchall()
        all_categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
        all_brands = db.execute("SELECT * FROM brands ORDER BY name").fetchall()
        gallery_photos = db.execute("SELECT * FROM product_images WHERE product_id=? ORDER BY sort_order,id", (product_id,)).fetchall()
    return render(request, "admin/product_form.html", title="Sửa sản phẩm" if product_id else "Thêm sản phẩm", section="products", values=dict(product) if product else {}, variants=variants, all_categories=all_categories, all_brands=all_brands, gallery_photos=gallery_photos, editing=bool(product_id))


@router.post("/products/save")
async def save_product(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    product_id = integer(data.get("id"))
    values = {name: data.get(name, "").strip() for name in ("name", "category", "summary", "description", "specs", "warranty", "image", "subcategory")}
    errors = {}
    for field, low, high in (("name", 2, 100), ("summary", 2, 150), ("description", 10, 5000), ("specs", 5, 3000), ("warranty", 2, 200)):
        if not low <= len(values[field]) <= high:
            errors[field] = f"Nhập từ {low} đến {high} ký tự."
    if values["image"] not in IMAGES:
        errors["image"] = "Chọn minh họa hợp lệ."
    brand_id = integer(data.get("brand_id"))
    with connect() as db:
        old = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone() if product_id else None
        if product_id and not old:
            raise HTTPException(404, "Không tìm thấy sản phẩm.")
        all_categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
        all_brands = db.execute("SELECT * FROM brands ORDER BY name").fetchall()
        variants = db.execute("SELECT * FROM variants WHERE product_id=?", (product_id,)).fetchall()
    if values["category"] not in {row["slug"] for row in all_categories}:
        errors["category"] = "Chọn danh mục hợp lệ."
    parent=next((row for row in all_categories if row['slug']==values['category']),None)
    if parent and parent['parent_slug']:
        errors['category']='Chọn danh mục cấp một cho nhóm sản phẩm.'
    if values['subcategory'] and not any(row['slug']==values['subcategory'] and row['parent_slug']==values['category'] for row in all_categories):
        errors['subcategory']='Danh mục cấp hai không thuộc nhóm sản phẩm đã chọn.'
    if brand_id not in {row["id"] for row in all_brands}:
        errors["brand_id"] = "Chọn thương hiệu hợp lệ."
    price, stock = integer(data.get("price")), integer(data.get("stock"), -1)
    if not product_id and (not 1000 <= price <= 1_000_000_000 or not 0 <= stock <= 100000):
        errors["price"] = "Giá từ 1.000 đến 1 tỷ đồng; tồn kho từ 0 đến 100.000."
    if errors:
        return render(request, "admin/product_form.html", 400, title="Kiểm tra thông tin sản phẩm", section="products", values={**values, "id": product_id, "brand_id": brand_id, "price": data.get("price", ""), "stock": data.get("stock", "")}, errors=errors, variants=variants, all_categories=all_categories, all_brands=all_brands, editing=bool(product_id))
    media = await upload(data)
    with connect() as db:
        params = (values["name"], values["category"], brand_id, values["summary"], values["description"], values["specs"], values["warranty"], values["image"], int(data.get("featured") == "1"), media or (old["media"] if old else ""))
        if product_id:
            db.execute("UPDATE products SET name=?,category=?,brand_id=?,summary=?,description=?,specs=?,warranty=?,image=?,featured=?,media=? WHERE id=?", (*params, product_id))
        else:
            product_id = db.execute("INSERT INTO products(name,category,brand_id,summary,description,specs,warranty,image,featured,media,price,stock) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (*params, price, stock)).lastrowid
            variant_id = db.execute("INSERT INTO variants(product_id,sku,color,storage,price,stock) VALUES(?,?,?,?,?,?)", (product_id, f"NEU-{product_id:04d}-01", "Tiêu chuẩn", "Tiêu chuẩn", price, stock)).lastrowid
            db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason,actor_id) VALUES(?,?,'Nhập tồn ban đầu',?)", (variant_id, stock, actor["id"]))
        audit(db, actor["id"], "Lưu sản phẩm", f"#{product_id}: {values['name']}")
        db.execute('UPDATE products SET subcategory=? WHERE id=?',(values['subcategory'] or None,product_id))
    return redirect(f"/admin/products/{product_id}/edit", request, "Đã lưu sản phẩm. Quản lý giá và tồn theo từng biến thể bên dưới.")


@router.post("/products/{product_id}/visibility")
async def visibility(request: Request, product_id: int):
    actor = require_admin(request)
    await form_data(request)
    with connect() as db:
        db.execute("UPDATE products SET active=1-active WHERE id=?", (product_id,))
        audit(db, actor["id"], "Đổi hiển thị sản phẩm", str(product_id))
    return redirect("/admin/products", request, "Đã cập nhật hiển thị.")


@router.post("/products/{product_id}/variants")
async def variant_save(request: Request, product_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    variant_id, price = integer(data.get("id")), integer(data.get("price"))
    color, storage = data.get("color", "").strip(), data.get("storage", "").strip()
    if not 1 <= len(color) <= 60 or not 1 <= len(storage) <= 60 or not 1000 <= price <= 1_000_000_000:
        raise HTTPException(400, "Màu và cấu hình cần 1–60 ký tự; giá từ 1.000 đến 1 tỷ đồng.")
    media = await upload(data)
    with connect() as db:
        if not db.execute("SELECT 1 FROM products WHERE id=?", (product_id,)).fetchone():
            raise HTTPException(404, "Không tìm thấy sản phẩm.")
        active = int(data.get("active") == "1")
        if variant_id:
            old = db.execute("SELECT * FROM variants WHERE id=? AND product_id=?", (variant_id, product_id)).fetchone()
            if not old:
                raise HTTPException(404, "Không tìm thấy biến thể.")
            if not active and old["active"] and not db.execute("SELECT 1 FROM variants WHERE product_id=? AND id!=? AND active=1", (product_id, variant_id)).fetchone():
                raise HTTPException(400, "Giữ ít nhất một biến thể hoạt động. Có thể ẩn cả sản phẩm.")
            db.execute("UPDATE variants SET color=?,storage=?,price=?,active=?,media=? WHERE id=?", (color, storage, price, active, media or old["media"], variant_id))
            if price != old["price"]:
                db.execute("UPDATE variants SET list_price=0,sale_end='' WHERE id=?", (variant_id,))
        else:
            variant_id = db.execute("INSERT INTO variants(product_id,sku,color,storage,price,stock,media) VALUES(?,?,?,?,?,0,?)", (product_id, f"NEU-{product_id}-{secrets.token_hex(3).upper()}", color, storage, price, media)).lastrowid
        refresh_product(db, product_id)
        audit(db, actor["id"], "Lưu biến thể", f"#{variant_id} sản phẩm #{product_id}")
    return redirect(f"/admin/products/{product_id}/edit", request, "Đã lưu biến thể. Nhập/xuất số lượng tại trang Tồn kho.")


@router.get("/catalog")
def catalog(request: Request):
    require_admin(request)
    with connect() as db:
        categories = db.execute("SELECT * FROM categories ORDER BY rowid").fetchall()
        brands = db.execute("SELECT * FROM brands ORDER BY id").fetchall()
    return render(request, "admin/catalog.html", title="Danh mục & thương hiệu", section="catalog", category_rows=categories, brand_rows=brands)


@router.post("/products/{product_id}/variants/batch")
async def variants_batch(request: Request, product_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    try:
        raw = data.get("variants", "")
        if len(raw) > 20000:
            raise ValueError()
        rows = json.loads(raw)
        if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
            raise ValueError()
        for row in rows:
            if not isinstance(row, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{3,50}", row.get("sku", "")) or not 1 <= len(row.get("color", "")) <= 60 or not 1 <= len(row.get("storage", "")) <= 60 or not 1000 <= integer(row.get("price")) <= 1000000000 or not 0 <= integer(row.get("stock"), -1) <= 100000:
                raise ValueError()
        if len({row["sku"] for row in rows}) != len(rows):
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(400, "Bảng biến thể không hợp lệ: tối đa 20 dòng, SKU không trùng, giá từ 1.000 và tồn không âm.") from None
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM products WHERE id=?", (product_id,)).fetchone():
            raise HTTPException(404, "Không tìm thấy sản phẩm.")
        if any(db.execute("SELECT 1 FROM variants WHERE sku=?", (row["sku"],)).fetchone() for row in rows):
            raise HTTPException(400, "SKU đã được sử dụng. Sửa SKU trước khi lưu.")
        for row in rows:
            variant_id = db.execute("INSERT INTO variants(product_id,sku,color,storage,price,stock) VALUES(?,?,?,?,?,?)", (product_id,row["sku"],row["color"],row["storage"],integer(row["price"]),integer(row["stock"]))).lastrowid
            db.execute("INSERT INTO inventory_movements(variant_id,quantity,reason,actor_id) VALUES(?,?,'Tồn ban đầu từ bảng biến thể',?)", (variant_id, integer(row["stock"]), actor["id"]))
        refresh_product(db, product_id)
        audit(db, actor["id"], "Tạo bảng biến thể", f"Sản phẩm #{product_id}: {len(rows)} dòng")
    return redirect(f"/admin/products/{product_id}/edit", request, "Đã tạo các biến thể và ghi nhận tồn kho ban đầu.")


@router.post("/products/{product_id}/gallery")
async def gallery_upload(request: Request, product_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    with connect() as db:
        if not db.execute("SELECT 1 FROM products WHERE id=?", (product_id,)).fetchone():
            raise HTTPException(404, "Không tìm thấy sản phẩm.")
    image = await upload(data)
    if not image:
        raise HTTPException(400, "Chọn ảnh để thêm vào thư viện.")
    with connect() as db:
        db.execute("INSERT INTO product_images(product_id,url,alt) VALUES(?,?,?)", (product_id,image,data.get("alt", "Ảnh sản phẩm")[:150]))
        audit(db, actor["id"], "Thêm ảnh thư viện", str(product_id))
    return redirect(f"/admin/products/{product_id}/edit", request, "Đã thêm ảnh vào thư viện sản phẩm.")


@router.post("/products/{product_id}/sale")
async def sale_save(request: Request, product_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        variant = db.execute("SELECT * FROM variants WHERE id=? AND product_id=?", (integer(data.get("variant_id")), product_id)).fetchone()
        if not variant:
            raise HTTPException(404, "Không tìm thấy biến thể.")
        if data.get("action") == "stop":
            db.execute("UPDATE variants SET price=CASE WHEN list_price>price THEN list_price ELSE price END,list_price=0,sale_end='' WHERE id=?", (variant["id"],))
        else:
            original, discounted = integer(data.get("list_price")), integer(data.get("sale_price"))
            try:
                end = datetime.fromisoformat(data.get("end", "")).replace(tzinfo=timezone(timedelta(hours=7))).astimezone(timezone.utc)
            except ValueError:
                raise HTTPException(400, "Nhập thời gian kết thúc hợp lệ theo giờ Việt Nam.") from None
            if not 1000 <= discounted < original <= 1000000000 or end <= datetime.now(timezone.utc):
                raise HTTPException(400, "Giá giảm phải nhỏ hơn giá gốc và thời gian kết thúc ở tương lai.")
            db.execute("UPDATE variants SET price=?,list_price=?,sale_end=? WHERE id=?", (discounted, original, end.strftime("%Y-%m-%d %H:%M:%S"), variant["id"]))
        refresh_product(db, product_id)
        audit(db, actor["id"], "Cập nhật Flash Sale", f"Biến thể #{variant['id']}")
    return redirect(f"/admin/products/{product_id}/edit", request, "Đã cập nhật khuyến mãi và giá bán.")


@router.post("/products/{product_id}/gallery/{image_id}/delete")
async def gallery_delete(request: Request, product_id: int, image_id: int):
    actor = require_admin(request)
    await form_data(request)
    with connect() as db:
        db.execute("DELETE FROM product_images WHERE id=? AND product_id=?", (image_id, product_id))
        audit(db,actor["id"],"Bỏ ảnh khỏi thư viện",f"Sản phẩm #{product_id}, ảnh #{image_id}")
    return redirect(f"/admin/products/{product_id}/edit",request,"Đã bỏ ảnh khỏi thư viện.")


@router.post("/reviews/{review_id}/reply")
async def review_reply(request: Request, review_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    reply = data.get("reply", "").strip()
    if not 2 <= len(reply) <= 2000:
        raise HTTPException(400, "Phản hồi cần từ 2 đến 2.000 ký tự.")
    with connect() as db:
        row = db.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy đánh giá.")
        db.execute("UPDATE reviews SET admin_reply=? WHERE id=?", (reply,review_id))
        notify(db,row["user_id"],"Phản hồi đánh giá",reply[:200],f"/products/{row['product_id']}#reviews")
        audit(db,actor["id"],"Trả lời đánh giá",str(review_id))
    return redirect("/admin/content",request,"Đã lưu phản hồi đánh giá.")


@router.post("/catalog")
async def catalog_save(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    kind, name = data.get("kind"), data.get("name", "").strip()
    if kind not in ("category", "brand") or not 2 <= len(name) <= 80:
        raise HTTPException(400, "Chọn nhóm và nhập tên từ 2 đến 80 ký tự.")
    with connect() as db:
        if kind == "category":
            slug = data.get("slug", "").strip()
            if not re.fullmatch(r"[a-z][a-z0-9-]{1,39}", slug):
                raise HTTPException(400, "Mã danh mục gồm 2–40 chữ thường, số hoặc dấu gạch ngang.")
            existing=db.execute('SELECT * FROM categories WHERE slug=?',(slug,)).fetchone()
            parent=data.get('parent_slug',existing['parent_slug'] if existing else None) or None
            if parent:
                row=db.execute('SELECT * FROM categories WHERE slug=?',(parent,)).fetchone()
                if not row or row['parent_slug'] or parent==slug or db.execute('SELECT 1 FROM categories WHERE parent_slug=?',(slug,)).fetchone():
                    raise HTTPException(400,'Chỉ hỗ trợ hai cấp; danh mục cha phải là cấp một và không được tạo vòng lặp.')
            if existing and existing['parent_slug']!=parent and db.execute('SELECT 1 FROM products WHERE subcategory=? OR category=?',(slug,slug)).fetchone():
                raise HTTPException(409,'Danh mục đã có sản phẩm. Chuyển sản phẩm sang danh mục khác trước khi đổi cấp.')
            db.execute("INSERT INTO categories(slug,name,parent_slug) VALUES(?,?,?) ON CONFLICT(slug) DO UPDATE SET name=excluded.name,parent_slug=excluded.parent_slug", (slug,name,parent))
        else:
            brand_id = integer(data.get("id"))
            if brand_id:
                if db.execute("SELECT 1 FROM brands WHERE name=? AND id!=?", (name, brand_id)).fetchone():
                    raise HTTPException(400, "Tên thương hiệu đã được sử dụng.")
                db.execute("UPDATE brands SET name=? WHERE id=?", (name, brand_id))
            else:
                db.execute("INSERT INTO brands(name) VALUES(?) ON CONFLICT(name) DO NOTHING", (name,))
        audit(db, actor["id"], "Lưu danh mục/thương hiệu", name)
    return redirect("/admin/catalog", request, "Đã lưu.")


@router.post("/catalog/visibility")
async def catalog_toggle(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    with connect() as db:
        if data.get("kind") == "category":
            db.execute("UPDATE categories SET active=1-active WHERE slug=?", (data.get("id"),))
        elif data.get("kind") == "brand":
            db.execute("UPDATE brands SET active=1-active WHERE id=?", (integer(data.get("id")),))
        else:
            raise HTTPException(400, "Nhóm không hợp lệ.")
        audit(db, actor["id"], "Đổi hiển thị danh mục/thương hiệu", str(data.get("id")))
    return redirect("/admin/catalog")


@router.get("/inventory")
def inventory(request: Request, low: int = 0):
    require_admin(request)
    with connect() as db:
        variants = db.execute("SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id" + (" WHERE v.stock<=5 AND v.active=1 AND p.active=1" if low else "") + " ORDER BY v.stock,v.id").fetchall()
        movements = db.execute("SELECT m.*,v.sku,p.name,u.name AS actor FROM inventory_movements m JOIN variants v ON v.id=m.variant_id JOIN products p ON p.id=v.product_id LEFT JOIN users u ON u.id=m.actor_id ORDER BY m.id DESC LIMIT 50").fetchall()
    return render(request, "admin/inventory.html", title="Quản lý tồn kho", section="inventory", variants=variants, movements=movements, low=low)


@router.post("/inventory")
async def inventory_change(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    quantity, reason = integer(data.get("quantity")), data.get("reason", "").strip()
    if not quantity or abs(quantity) > 100000 or not 5 <= len(reason) <= 300:
        raise HTTPException(400, "Số lượng khác 0, tối đa ±100.000; lý do từ 5 đến 300 ký tự.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        move_stock(db, integer(data.get("variant_id")), quantity, reason, actor["id"])
        audit(db, actor["id"], "Nhập/xuất kho", f"Biến thể {data.get('variant_id')}: {quantity}, {reason}")
    return redirect("/admin/inventory", request, "Đã ghi nhận nhập/xuất kho.")


@router.get("/orders")
def orders(request: Request, status: str = "", q: str = ""):
    require_admin(request)
    where, params = ["(recipient LIKE ? OR CAST(id AS TEXT)=?)"], [f"%{q[:100]}%", q[:100]]
    if status:
        where.append("status=?")
        params.append(status)
    with connect() as db:
        orders = db.execute("SELECT * FROM orders WHERE " + " AND ".join(where) + " ORDER BY id DESC", params).fetchall()
    return render(request, "admin/orders.html", title="Quản lý đơn hàng", section="orders", orders=orders, selected_status=status, q=q[:100])


@router.post("/orders/{order_id}/status")
async def order_status(request: Request, order_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    status, note = data.get("status"), data.get("note", "").strip()[:300]
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        order = order_for(db, actor, order_id)
        if status not in TRANSITIONS.get(order["status"], ()):
            raise HTTPException(400, "Không thể chuyển trạng thái theo bước này.")
        if status == "Đã hủy":
            cancel_order(db, order, actor["id"], note)
        else:
            if order["payment_method"] != "cod" and order["payment_status"] != "Đã thanh toán":
                raise HTTPException(400, "Đơn thanh toán online phải thanh toán thành công trước khi xử lý.")
            tracking = data.get("tracking_code", "").strip()[:80] or order["tracking_code"]
            if status == "Đang giao":
                tracking = tracking or f"DEMO-NEU-{order_id:05d}"
            if status == "Hoàn tất":
                finish_order(db, order)
            else:
                db.execute("UPDATE orders SET status=?,tracking_code=? WHERE id=?", (status, tracking, order_id))
            event(db, order, status, note)
        audit(db, actor["id"], "Cập nhật đơn", f"#{order_id}: {status}")
    return redirect(f"/admin/orders/{order_id}", request, "Đã cập nhật trạng thái đơn.")


@router.get("/returns")
def returns(request: Request):
    require_admin(request)
    with connect() as db:
        rows = db.execute("SELECT r.*,o.total,o.recipient FROM return_requests r JOIN orders o ON o.id=r.order_id ORDER BY r.id DESC").fetchall()
    return render(request, "admin/returns.html", title="Đổi trả & hoàn tiền", section="returns", returns=rows)


@router.post("/returns/{return_id}")
async def return_update(request: Request, return_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    status, response = data.get("status"), data.get("response", "").strip()[:500]
    transitions = {"Chờ duyệt": ("Đã duyệt", "Từ chối"), "Đã duyệt": ("Đã nhận hàng", "Từ chối"), "Đã nhận hàng": ("Đã hoàn tiền",)}
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM return_requests WHERE id=?", (return_id,)).fetchone()
        if not row or status not in transitions.get(row["status"], ()):
            raise HTTPException(400, "Bước xử lý đổi trả không hợp lệ.")
        if status == "Từ chối" and len(response) < 5:
            raise HTTPException(400, "Cần ghi rõ lý do từ chối, tối thiểu 5 ký tự.")
        order = order_for(db, actor, row["order_id"])
        db.execute("UPDATE return_requests SET status=?,response=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, response, return_id))
        if status == "Đã nhận hàng":
            for item in db.execute("SELECT * FROM order_items WHERE order_id=?", (order["id"],)).fetchall():
                move_stock(db, item["variant_id"], item["quantity"], f"Nhận trả đơn {order['id']}", actor["id"])
        if status == "Đã hoàn tiền":
            refund(db, order)
            db.execute("UPDATE orders SET status='Đã trả hàng',points_awarded=0 WHERE id=?", (order["id"],))
            db.execute("UPDATE users SET points=MAX(0,points-?) WHERE id=?", (order["points_awarded"], order["user_id"]))
            event(db, order, "Đã trả hàng", "Đã hoàn tiền mô phỏng về phương thức gốc.")
        notify(db, row["user_id"], "Cập nhật yêu cầu trả hàng", status + (": " + response if response else ""), f"/orders/{row['order_id']}")
        audit(db, actor["id"], "Xử lý trả hàng", f"#{return_id}: {status}")
    return redirect("/admin/returns", request, "Đã cập nhật yêu cầu trả hàng.")


@router.get("/vouchers")
def vouchers(request: Request):
    require_admin(request)
    with connect() as db:
        rows = db.execute("SELECT * FROM vouchers ORDER BY id DESC").fetchall()
    return render(request, "admin/vouchers.html", title="Quản lý khuyến mãi", section="vouchers", vouchers=rows)


@router.post("/vouchers")
async def voucher_save(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    code, kind = data.get("code", "").strip().upper(), data.get("kind")
    value, minimum, cap, limit = (integer(data.get(key), -1) for key in ("value", "min_total", "max_discount", "usage_limit"))
    try:
        start, end = date.fromisoformat(data.get("start_date", "")), date.fromisoformat(data.get("end_date", ""))
    except ValueError:
        raise HTTPException(400, "Ngày bắt đầu hoặc kết thúc không hợp lệ.") from None
    if not re.fullmatch(r"[A-Z0-9_-]{3,30}", code) or kind not in ("fixed", "percent") or not 1 <= value <= (100 if kind == "percent" else 1000000000) or not 0 <= minimum <= 1000000000 or not 0 <= cap <= 1000000000 or not 1 <= limit <= 1000000 or start > end:
        raise HTTPException(400, "Kiểm tra mã, giá trị giảm, điều kiện, thời hạn và số lượt sử dụng.")
    with connect() as db:
        existing = db.execute("SELECT * FROM vouchers WHERE code=?", (code,)).fetchone()
        if existing and limit < existing["used_count"]:
            raise HTTPException(400, "Giới hạn không thể thấp hơn số lượt đã sử dụng.")
        db.execute("INSERT INTO vouchers(code,kind,value,min_total,max_discount,start_date,end_date,usage_limit) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET kind=excluded.kind,value=excluded.value,min_total=excluded.min_total,max_discount=excluded.max_discount,start_date=excluded.start_date,end_date=excluded.end_date,usage_limit=excluded.usage_limit", (code, kind, value, minimum, cap, start.isoformat(), end.isoformat(), limit))
        audit(db, actor["id"], "Lưu voucher", code)
    return redirect("/admin/vouchers", request, "Đã lưu voucher.")


@router.post("/vouchers/{voucher_id}/visibility")
async def voucher_toggle(request: Request, voucher_id: int):
    actor = require_admin(request)
    await form_data(request)
    with connect() as db:
        db.execute("UPDATE vouchers SET active=1-active WHERE id=?", (voucher_id,))
        audit(db, actor["id"], "Bật/tắt voucher", str(voucher_id))
    return redirect("/admin/vouchers")


@router.get("/users")
def users(request: Request, q: str = ""):
    require_admin(request)
    with connect() as db:
        rows = db.execute("SELECT id,name,email,role,active,points,created_at FROM users WHERE name LIKE ? OR email LIKE ? ORDER BY id DESC", (f"%{q[:100]}%", f"%{q[:100]}%")).fetchall()
    return render(request, "admin/users.html", title="Tài khoản & phân quyền", section="users", users=rows, q=q[:100])


@router.post("/users")
async def user_create(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    name, email, password, role = (data.get(key, "").strip() for key in ("name", "email", "password", "role"))
    if not 2 <= len(name) <= 80 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 200 or not 8 <= len(password) <= 128 or role not in ("admin", "customer"):
        raise HTTPException(400, "Kiểm tra họ tên, email, mật khẩu 8–128 ký tự và vai trò.")
    with connect() as db:
        if db.execute("SELECT 1 FROM users WHERE email=?", (email.lower(),)).fetchone():
            raise HTTPException(400, "Email đã được sử dụng.")
        db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)", (name, email.lower(), password_hash(password), role))
        audit(db, actor["id"], "Tạo tài khoản", f"{email}: {role}")
    return redirect("/admin/users", request, "Đã tạo tài khoản demo.")


@router.post("/users/{user_id}")
async def user_update(request: Request, user_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    role, active = data.get("role"), int(data.get("active") == "1")
    if role not in ("admin", "customer"):
        raise HTTPException(400, "Chỉ có hai vai trò admin và customer.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not old:
            raise HTTPException(404, "Không tìm thấy tài khoản.")
        if actor["id"] == user_id and (role != "admin" or not active):
            raise HTTPException(400, "Không thể tự khóa hoặc tự bỏ quyền quản trị.")
        if old["role"] == "admin" and old["active"] and (role != "admin" or not active) and db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0] <= 1:
            raise HTTPException(400, "Phải giữ ít nhất một quản trị viên hoạt động.")
        db.execute("UPDATE users SET role=?,active=?,auth_rev=auth_rev+1 WHERE id=?", (role, active, user_id))
        audit(db, actor["id"], "Cập nhật phân quyền", f"#{user_id}: {role}, hoạt động={active}")
    if actor["id"] == user_id:
        request.session["auth_rev"] = old["auth_rev"] + 1
    return redirect("/admin/users", request, "Đã cập nhật tài khoản và thu hồi các phiên đăng nhập cũ.")


@router.get("/reports")
def reports(request: Request, start: str = "", end: str = "", export: int = 0):
    require_admin(request)
    for value in (start, end):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                raise HTTPException(400, "Ngày lọc báo cáo không hợp lệ.") from None
    if start and end and start > end:
        raise HTTPException(400, "Ngày bắt đầu phải trước ngày kết thúc.")
    where, params = ["1=1"], []
    if start:
        where.append("date(p.created_at,'+7 hours')>=?")
        params.append(start)
    if end:
        where.append("date(p.created_at,'+7 hours')<=?")
        params.append(end)
    with connect() as db:
        payments = db.execute("SELECT p.*,o.recipient FROM payments p JOIN orders o ON o.id=p.order_id WHERE " + " AND ".join(where) + " ORDER BY p.id DESC", params).fetchall()
        best = db.execute("SELECT i.name,SUM(i.quantity) AS quantity,SUM(i.quantity*i.price) AS revenue FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='Hoàn tất' GROUP BY i.product_id ORDER BY quantity DESC LIMIT 8").fetchall()
        inventory = db.execute("SELECT SUM(stock) AS units,COALESCE(SUM(stock*price),0) AS value FROM variants WHERE active=1").fetchone()
    collected = sum(p["amount"] for p in payments if p["status"] == "Thành công" and p["kind"] == "payment")
    refunded = sum(p["amount"] for p in payments if p["status"] == "Thành công" and p["kind"] == "refund")
    if export:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Mã giao dịch", "Đơn hàng", "Loại", "Phương thức", "Số tiền", "Trạng thái", "Đối soát", "Ngày tạo"])
        for p in payments:
            writer.writerow([p["reference"], p["order_id"], p["kind"], p["method"], p["amount"], p["status"], p["reconciled"], p["created_at"]])
        return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="neu-shop-payments.csv"'})
    return render(request, "admin/reports.html", title="Báo cáo & đối soát", section="reports", payments=payments, best=best, inventory=inventory, collected=collected, refunded=refunded, start=start, end=end)


@router.post("/payments/{payment_id}/reconcile")
async def reconcile(request: Request, payment_id: int):
    actor = require_admin(request)
    await form_data(request)
    with connect() as db:
        row = db.execute("SELECT * FROM payments WHERE id=? AND status='Thành công'", (payment_id,)).fetchone()
        if not row:
            raise HTTPException(400, "Chỉ đối soát giao dịch thành công.")
        db.execute("UPDATE payments SET reconciled=1 WHERE id=?", (payment_id,))
        audit(db, actor["id"], "Đối soát giao dịch demo", row["reference"])
    return redirect("/admin/reports", request, "Đã ghi nhận đối soát nội bộ demo.")


@router.get("/support")
def support(request: Request, customer: int = 0):
    require_admin(request)
    with connect() as db:
        threads = db.execute("SELECT u.id,u.name,u.email,MAX(m.created_at) AS last_message FROM users u JOIN support_messages m ON m.user_id=u.id GROUP BY u.id ORDER BY last_message DESC").fetchall()
        selected = customer or (threads[0]["id"] if threads else 0)
        messages = db.execute("SELECT m.*,u.name,u.role FROM support_messages m JOIN users u ON u.id=m.sender_id WHERE m.user_id=? ORDER BY m.id", (selected,)).fetchall()
        questions = db.execute("SELECT q.*,u.name,p.name AS product_name FROM questions q JOIN users u ON u.id=q.user_id JOIN products p ON p.id=q.product_id ORDER BY q.id DESC LIMIT 50").fetchall()
    return render(request, "admin/support.html", title="Chăm sóc khách hàng", section="support", threads=threads, selected_customer=selected, messages=messages, questions=questions)


@router.post("/support")
async def support_reply(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    content, user_id = data.get("content", "").strip(), integer(data.get("user_id"))
    if not 1 <= len(content) <= 2000:
        raise HTTPException(400, "Tin nhắn cần từ 1 đến 2.000 ký tự.")
    with connect() as db:
        if not db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            raise HTTPException(404, "Không tìm thấy khách hàng.")
        db.execute("INSERT INTO support_messages(user_id,sender_id,content) VALUES(?,?,?)", (user_id, actor["id"], content))
        notify(db, user_id, "Phản hồi từ NEU SHOP", content[:200], "/account/support")
        audit(db, actor["id"], "Trả lời hỗ trợ", f"Khách #{user_id}")
    return redirect(f"/admin/support?customer={user_id}")


@router.post("/questions/{question_id}")
async def answer(request: Request, question_id: int):
    actor = require_admin(request)
    data = await form_data(request)
    content = data.get("answer", "").strip()
    if not 2 <= len(content) <= 2000:
        raise HTTPException(400, "Phản hồi cần từ 2 đến 2.000 ký tự.")
    with connect() as db:
        row = db.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy câu hỏi.")
        db.execute("UPDATE questions SET answer=? WHERE id=?", (content, question_id))
        notify(db, row["user_id"], "Câu hỏi đã được trả lời", content[:200], f"/products/{row['product_id']}#questions")
        audit(db, actor["id"], "Trả lời câu hỏi", str(question_id))
    return redirect("/admin/support")


@router.get("/content")
def content(request: Request):
    require_admin(request)
    with connect() as db:
        articles = db.execute("SELECT * FROM articles ORDER BY id DESC").fetchall()
        reviews = db.execute("SELECT r.*,u.name,p.name AS product_name FROM reviews r JOIN users u ON u.id=r.user_id JOIN products p ON p.id=r.product_id ORDER BY r.id DESC LIMIT 100").fetchall()
        topics=db.execute('SELECT * FROM article_topics ORDER BY name').fetchall()
    return render(request, "admin/content.html", title="Bài viết & đánh giá", section="content", articles=articles, reviews=reviews,topics=topics)


@router.post("/content")
async def article_save(request: Request):
    actor = require_admin(request)
    data = await form_data(request)
    title, summary, content = (data.get(name, "").strip() for name in ("title", "summary", "content"))
    if not 5 <= len(title) <= 150 or not 10 <= len(summary) <= 300 or not 20 <= len(content) <= 15000:
        raise HTTPException(400, "Tiêu đề 5–150, tóm tắt 10–300, nội dung 20–15.000 ký tự.")
    media=await upload(data)
    with connect() as db:
        article_id = integer(data.get("id"))
        old=db.execute('SELECT * FROM articles WHERE id=?',(article_id,)).fetchone() if article_id else None
        if article_id and not old:
            raise HTTPException(404,'Không tìm thấy bài viết.')
        topic_id=integer(data.get('topic_id')) or (old['topic_id'] if old else None)
        if topic_id and not db.execute('SELECT 1 FROM article_topics WHERE id=?',(topic_id,)).fetchone():
            raise HTTPException(400,'Chủ đề không hợp lệ.')
        if article_id:
            db.execute("UPDATE articles SET title=?,summary=?,content=?,topic_id=?,image=? WHERE id=?", (title,summary,content,topic_id,media or old['image'],article_id))
        else:
            db.execute("INSERT INTO articles(title,summary,content,topic_id,image) VALUES(?,?,?,?,?)", (title,summary,content,topic_id,media))
        audit(db, actor["id"], "Lưu bài viết", title)
    return redirect("/admin/content", request, "Đã lưu bài viết.")


@router.post("/content/{kind}/{item_id}/visibility")
async def content_toggle(request: Request, kind: str, item_id: int):
    actor = require_admin(request)
    await form_data(request)
    with connect() as db:
        if kind == "article":
            db.execute("UPDATE articles SET active=1-active WHERE id=?", (item_id,))
        elif kind == "review":
            db.execute("UPDATE reviews SET visible=1-visible WHERE id=?", (item_id,))
        else:
            raise HTTPException(400, "Nội dung không hợp lệ.")
        audit(db, actor["id"], "Đổi hiển thị nội dung", f"{kind} #{item_id}")
    return redirect("/admin/content")


@router.get("/logs")
def logs(request: Request):
    require_admin(request)
    with connect() as db:
        rows = db.execute("SELECT l.*,u.name FROM audit_logs l LEFT JOIN users u ON u.id=l.actor_id ORDER BY l.id DESC LIMIT 200").fetchall()
    return render(request, "admin/logs.html", title="Nhật ký thao tác", section="logs", logs=rows)
