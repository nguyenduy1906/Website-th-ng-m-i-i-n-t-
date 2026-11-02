import re
import secrets
from datetime import date

from fastapi import APIRouter, HTTPException, Request

from .core import audit, cancel_order, event, finish_order, form_data, integer, localtime, notify, order_for, redirect, render, require_signed_contract, require_user, upload
from .db import connect, password_hash, password_matches

router = APIRouter()


@router.get("/api/support")
def support_feed(request: Request, customer: int = 0):
    user = require_user(request)
    selected = customer if user["role"] == "admin" and customer else user["id"]
    if user["role"] != "admin" and customer and customer != user["id"]:
        raise HTTPException(403, "Bạn không có quyền xem cuộc trò chuyện này.")
    with connect() as db:
        messages = db.execute("SELECT m.*,u.name,u.role FROM support_messages m JOIN users u ON u.id=m.sender_id WHERE m.user_id=? ORDER BY m.id DESC LIMIT 100", (selected,)).fetchall()
    return [{"id": m["id"], "name": "NEU SHOP" if m["role"] == "admin" else m["name"], "admin": m["role"] == "admin", "content": m["content"], "time": localtime(m["created_at"])} for m in reversed(messages)]


@router.get("/api/orders/{order_id}")
def order_feed(request: Request, order_id: int):
    user = require_user(request)
    with connect() as db:
        order = order_for(db, user, order_id)
        returns = db.execute("SELECT status FROM return_requests WHERE order_id=?", (order_id,)).fetchone()
    return {"signature": order["status"] + "|" + order["payment_status"] + "|" + (returns["status"] if returns else "")}


@router.post("/orders/{order_id}/confirm")
async def confirm_received(request: Request, order_id: int):
    user = require_user(request)
    await form_data(request)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        order = order_for(db, user, order_id)
        if order["user_id"] != user["id"]:
            raise HTTPException(403, "Chỉ người đặt đơn được xác nhận đã nhận hàng.")
        finish_order(db, order)
        event(db, order, "Hoàn tất", "Khách hàng xác nhận đã nhận hàng.")
    return redirect(f"/orders/{order_id}", request, "Đã xác nhận nhận hàng. Bạn có thể đánh giá sản phẩm.")


@router.get("/account")
@router.get("/account/{section}")
def account_page(request: Request, section: str = "overview"):
    user = require_user(request)
    if section not in ("overview", "profile", "addresses", "security", "orders", "notifications", "support"):
        raise HTTPException(404, "Không tìm thấy trang tài khoản.")
    with connect() as db:
        orders = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
        addresses = db.execute("SELECT * FROM addresses WHERE user_id=? ORDER BY is_default DESC,id", (user["id"],)).fetchall()
        notifications = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100", (user["id"],)).fetchall()
        messages = db.execute("SELECT m.*,u.name,u.role FROM support_messages m JOIN users u ON u.id=m.sender_id WHERE m.user_id=? ORDER BY m.id", (user["id"],)).fetchall()
    titles = {"overview": "Tài khoản của bạn", "profile": "Thông tin cá nhân", "addresses": "Sổ địa chỉ", "security": "Bảo mật tài khoản", "orders": "Đơn hàng của tôi", "notifications": "Thông báo", "support": "Hỗ trợ khách hàng"}
    return render(request, "customer/account.html", title=titles[section], account_section=section, orders=orders, addresses=addresses, notifications=notifications, messages=messages, values=dict(user))


@router.post("/account/profile")
async def profile(request: Request):
    user = require_user(request)
    data = await form_data(request)
    values = {name: data.get(name, "").strip() for name in ("name", "phone", "birth_date", "gender")}
    errors = {}
    if not 2 <= len(values["name"]) <= 80:
        errors["name"] = "Họ tên cần từ 2 đến 80 ký tự."
    if values["phone"] and not re.fullmatch(r"(?:0|\+84)[0-9]{9}", values["phone"]):
        errors["phone"] = "Số điện thoại không hợp lệ."
    try:
        if values["birth_date"] and date.fromisoformat(values["birth_date"]) > date.today():
            errors["birth_date"] = "Ngày sinh không thể ở tương lai."
    except ValueError:
        errors["birth_date"] = "Ngày sinh không hợp lệ."
    if values["gender"] not in ("", "Nam", "Nữ", "Khác"):
        errors["gender"] = "Chọn giới tính hợp lệ."
    if errors:
        return render(request, "customer/account.html", 400, title="Thông tin cá nhân", account_section="profile", errors=errors, values=values)
    with connect() as db:
        db.execute("UPDATE users SET name=?,phone=?,birth_date=?,gender=? WHERE id=?", (*values.values(), user["id"]))
    return redirect("/account/profile", request, "Đã cập nhật thông tin cá nhân.")


@router.post("/account/security")
async def security(request: Request):
    user = require_user(request)
    data = await form_data(request)
    errors = {}
    if not password_matches(data.get("current_password", "")[:128], user["password"]):
        errors["current_password"] = "Mật khẩu hiện tại chưa đúng."
    new_password = data.get("password", "")
    if new_password and (not 8 <= len(new_password) <= 128 or new_password != data.get("confirm")):
        errors["password"] = "Mật khẩu mới cần 8–128 ký tự và nhập lại trùng khớp."
    if errors:
        return render(request, "customer/account.html", 400, title="Bảo mật tài khoản", account_section="security", errors=errors, values=dict(user))
    with connect() as db:
        db.execute("UPDATE users SET password=?,otp_enabled=?,auth_rev=auth_rev+1 WHERE id=?", (password_hash(new_password) if new_password else user["password"], int(data.get("otp_enabled") == "1"), user["id"]))
    request.session["auth_rev"] = user["auth_rev"] + 1
    return redirect("/account/security", request, "Đã cập nhật bảo mật và vô hiệu hóa các phiên đăng nhập cũ.")


@router.post("/account/addresses")
async def save_address(request: Request):
    user = require_user(request)
    data = await form_data(request)
    address_id = integer(data.get("id"))
    recipient, phone, address = (data.get(key, "").strip() for key in ("recipient", "phone", "address"))
    if not 2 <= len(recipient) <= 80 or not re.fullmatch(r"(?:0|\+84)[0-9]{9}", phone) or not 10 <= len(address) <= 300:
        raise HTTPException(400, "Kiểm tra họ tên (2–80 ký tự), số điện thoại và địa chỉ (10–300 ký tự).")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        count = db.execute("SELECT COUNT(*) FROM addresses WHERE user_id=?", (user["id"],)).fetchone()[0]
        if address_id and not db.execute("SELECT 1 FROM addresses WHERE id=? AND user_id=?", (address_id, user["id"])).fetchone():
            raise HTTPException(404, "Không tìm thấy địa chỉ.")
        if not address_id and count >= 10:
            raise HTTPException(400, "Tối đa 10 địa chỉ cho mỗi tài khoản.")
        default = int(data.get("is_default") == "1" or count == 0)
        if default:
            db.execute("UPDATE addresses SET is_default=0 WHERE user_id=?", (user["id"],))
        if address_id:
            db.execute("UPDATE addresses SET recipient=?,phone=?,address=?,is_default=? WHERE id=? AND user_id=?", (recipient, phone, address, default, address_id, user["id"]))
        else:
            db.execute("INSERT INTO addresses(user_id,recipient,phone,address,is_default) VALUES(?,?,?,?,?)", (user["id"], recipient, phone, address, default))
    return redirect("/account/addresses", request, "Đã lưu địa chỉ.")


@router.post("/account/addresses/{address_id}/delete")
async def delete_address(request: Request, address_id: int):
    user = require_user(request)
    await form_data(request)
    with connect() as db:
        db.execute("DELETE FROM addresses WHERE id=? AND user_id=?", (address_id, user["id"]))
        if not db.execute("SELECT 1 FROM addresses WHERE user_id=? AND is_default=1", (user["id"],)).fetchone():
            db.execute("UPDATE addresses SET is_default=1 WHERE id=(SELECT MIN(id) FROM addresses WHERE user_id=?)", (user["id"],))
    return redirect("/account/addresses", request, "Đã xóa địa chỉ.")


@router.post("/account/notifications/read")
async def read_notifications(request: Request):
    user = require_user(request)
    await form_data(request)
    with connect() as db:
        db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
    return redirect("/account/notifications", request, "Đã đánh dấu tất cả là đã đọc.")


@router.get("/orders/{order_id}")
@router.get("/admin/orders/{order_id}")
def order_detail(request: Request, order_id: int):
    user = require_user(request)
    admin_view = request.url.path.startswith("/admin")
    if admin_view and user["role"] != "admin":
        raise HTTPException(403, "Bạn không có quyền quản trị.")
    with connect() as db:
        order = order_for(db, user, order_id)
        items = db.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
        payments = db.execute("SELECT * FROM payments WHERE order_id=? ORDER BY id DESC", (order_id,)).fetchall()
        events = db.execute("SELECT * FROM order_events WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
        returns = db.execute("SELECT * FROM return_requests WHERE order_id=?", (order_id,)).fetchone()
        can_return = db.execute("SELECT 1 FROM orders WHERE id=? AND status='Hoàn tất' AND completed_at>=datetime('now','-7 days')", (order_id,)).fetchone() is not None and not returns
        contract=db.execute('SELECT id,number,status FROM sales_contracts WHERE order_id=?',(order_id,)).fetchone()
    return render(request, "admin/order.html" if admin_view else "customer/order.html", title=f"Đơn hàng NEU-{order_id:05d}", account_section="orders", section="orders", order=order, items=items, payments=payments, events=events, returns=returns, can_return=can_return,contract=contract)


@router.post("/orders/{order_id}/cancel")
async def customer_cancel(request: Request, order_id: int):
    user = require_user(request)
    data = await form_data(request)
    reason = data.get("reason", "Khách hàng hủy đơn").strip()[:300]
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        order = order_for(db, user, order_id)
        if order["user_id"] != user["id"] or order["status"] not in ("Chờ thanh toán", "Chờ xác nhận"):
            raise HTTPException(400, "Khách chỉ có thể hủy trước khi đơn được chuẩn bị.")
        cancel_order(db, order, user["id"], reason)
    return redirect(f"/orders/{order_id}", request, 'Đã hủy đơn và hoàn tồn kho. Khoản thanh toán đã thu được hoàn tự động.')


@router.post("/orders/{order_id}/pay")
async def pay_again(request: Request, order_id: int):
    user = require_user(request)
    data = await form_data(request)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        order = order_for(db, user, order_id)
        if order["status"] != "Chờ thanh toán":
            raise HTTPException(400, "Đơn không còn chờ thanh toán.")
        require_signed_contract(db, order_id)
        db.execute("UPDATE payments SET status='Đã hủy' WHERE order_id=? AND status='Chờ thanh toán'", (order_id,))
        cod = data.get("method") == "cod"
        method = "cod" if cod else order["payment_method"]
        payment_id = db.execute("INSERT INTO payments(order_id,method,amount,reference) VALUES(?,?,?,?)", (order_id, method, order["total"], "PAY-" + secrets.token_hex(10))).lastrowid
        if cod:
            db.execute("UPDATE orders SET status='Chờ xác nhận',payment_method='cod',expires_at=NULL WHERE id=?", (order_id,))
            event(db, order, "Chờ xác nhận", 'Chuyển sang COD thử nghiệm.')
    return redirect(f"/orders/{order_id}" if cod else f"/payments/{payment_id}")


@router.post("/orders/{order_id}/return")
async def request_return(request: Request, order_id: int):
    user = require_user(request)
    data = await form_data(request)
    reason = data.get("reason", "").strip()
    if not 10 <= len(reason) <= 1000:
        raise HTTPException(400, "Lý do đổi trả cần từ 10 đến 1.000 ký tự.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        order = order_for(db, user, order_id)
        if order["user_id"] != user["id"] or not db.execute("SELECT 1 FROM orders WHERE id=? AND status='Hoàn tất' AND completed_at>=datetime('now','-7 days')", (order_id,)).fetchone():
            raise HTTPException(400, "Chỉ nhận yêu cầu trả toàn bộ đơn trong 7 ngày kể từ khi hoàn tất.")
        if db.execute("SELECT 1 FROM return_requests WHERE order_id=?", (order_id,)).fetchone():
            raise HTTPException(400, "Đơn đã có yêu cầu đổi trả.")
        photo = await upload(data)
        db.execute("INSERT INTO return_requests(order_id,user_id,reason,image) VALUES(?,?,?,?)", (order_id, user["id"], reason, photo))
        notify(db, user["id"], "Đã nhận yêu cầu trả hàng", "Admin sẽ xem xét và cập nhật kết quả.", f"/orders/{order_id}")
    return redirect(f"/orders/{order_id}", request, "Đã gửi yêu cầu trả hàng và hoàn tiền.")


@router.post("/products/{product_id}/reviews")
async def review(request: Request, product_id: int):
    user = require_user(request)
    data = await form_data(request)
    order_id, rating = integer(data.get("order_id")), integer(data.get("rating"))
    content = data.get("content", "").strip()
    if not 1 <= rating <= 5 or not 10 <= len(content) <= 2000:
        raise HTTPException(400, "Chọn từ 1 đến 5 sao và viết nhận xét từ 10 đến 2.000 ký tự.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.id=? AND o.user_id=? AND o.completed_at IS NOT NULL AND i.product_id=?", (order_id, user["id"], product_id)).fetchone():
            raise HTTPException(403, "Chỉ khách đã nhận sản phẩm mới được đánh giá.")
        if db.execute("SELECT 1 FROM reviews WHERE user_id=? AND order_id=? AND product_id=?", (user["id"], order_id, product_id)).fetchone():
            raise HTTPException(400, "Bạn đã đánh giá sản phẩm trong đơn này.")
        photo = await upload(data)
        db.execute("INSERT INTO reviews(user_id,order_id,product_id,rating,content,image) VALUES(?,?,?,?,?,?)", (user["id"], order_id, product_id, rating, content, photo))
    return redirect(f"/products/{product_id}#reviews", request, "Đã đăng đánh giá từ người mua xác thực.")


@router.post("/products/{product_id}/questions")
async def question(request: Request, product_id: int):
    user = require_user(request)
    data = await form_data(request)
    content = data.get("content", "").strip()
    if not 5 <= len(content) <= 1000:
        raise HTTPException(400, "Câu hỏi cần từ 5 đến 1.000 ký tự.")
    with connect() as db:
        if not db.execute("SELECT 1 FROM products WHERE id=? AND active=1", (product_id,)).fetchone():
            raise HTTPException(404, "Không tìm thấy sản phẩm.")
        db.execute("INSERT INTO questions(user_id,product_id,content) VALUES(?,?,?)", (user["id"], product_id, content))
    return redirect(f"/products/{product_id}#questions", request, "Đã gửi câu hỏi.")


@router.post("/account/support")
async def support(request: Request):
    user = require_user(request)
    data = await form_data(request)
    content = data.get("content", "").strip()
    if not 1 <= len(content) <= 2000:
        raise HTTPException(400, "Tin nhắn cần từ 1 đến 2.000 ký tự.")
    with connect() as db:
        db.execute("INSERT INTO support_messages(user_id,sender_id,content) VALUES(?,?,?)", (user["id"], user["id"], content))
    return redirect("/account/support", request, "Đã gửi tin nhắn. Bạn có thể làm mới để xem phản hồi từ admin.")
