import hashlib
import hmac
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, Request

from .core import audit, form_data, read_cart, redirect, render, require_user, sign_in, user_of
from .db import connect, password_hash, password_matches

router = APIRouter()


def start_challenge(request, user_id, purpose):
    key, code = secrets.token_urlsafe(24), f"{secrets.randbelow(1000000):06d}"
    with connect() as db:
        previous = request.session.get("challenge")
        if previous:
            db.execute("UPDATE otp_challenges SET consumed=1 WHERE id=?", (previous,))
        db.execute("INSERT INTO otp_challenges(id,user_id,purpose,code_hash,demo_code,expires_at) VALUES(?,?,?,?,?,?)", (key, user_id, purpose, hashlib.sha256(code.encode()).hexdigest(), code, int(time.time()) + 300))
    request.session["challenge"] = key


@router.get("/login")
@router.get("/admin/login")
def login_page(request: Request):
    admin = request.url.path.startswith("/admin")
    return render(request, "admin/login.html" if admin else "customer/auth.html", title="Đăng nhập quản trị" if admin else "Đăng nhập", mode="login", admin_login=admin)


@router.get("/register")
@router.get("/forgot-password")
def auth_page(request: Request):
    mode = "register" if request.url.path == "/register" else "forgot"
    return render(request, "customer/auth.html", title="Tạo tài khoản" if mode == "register" else "Quên mật khẩu", mode=mode)


@router.post("/register")
async def register(request: Request):
    data = await form_data(request)
    name, email, password = data.get("name", "").strip(), data.get("email", "").strip().lower(), data.get("password", "")
    errors = {}
    if not 2 <= len(name) <= 80:
        errors["name"] = "Họ tên cần từ 2 đến 80 ký tự."
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 200:
        errors["email"] = "Nhập địa chỉ email hợp lệ."
    if not 8 <= len(password) <= 128:
        errors["password"] = "Mật khẩu cần từ 8 đến 128 ký tự."
    if data.get("confirm") != password:
        errors["confirm"] = "Mật khẩu nhập lại chưa khớp."
    if not errors:
        try:
            with connect() as db:
                user_id = db.execute("INSERT INTO users(name,email,password,email_verified) VALUES(?,?,?,0)", (name, email, password_hash(password))).lastrowid
            start_challenge(request, user_id, "register")
            return redirect("/verify", request, "Xác thực email bằng mã OTP demo để hoàn tất đăng ký.")
        except sqlite3.IntegrityError:
            errors["email"] = "Email đã có tài khoản. Hãy đăng nhập hoặc khôi phục mật khẩu."
    return render(request, "customer/auth.html", 400, title="Tạo tài khoản", mode="register", errors=errors, values={"name": name, "email": email})


@router.post("/login")
async def login(request: Request):
    data = await form_data(request)
    email, password = data.get("email", "").strip().lower()[:200], data.get("password", "")
    admin_portal = data.get("portal") == "admin"
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
    if not user or len(password) > 128 or not password_matches(password, user["password"]) or (admin_portal and user["role"] != "admin"):
        return render(request, "admin/login.html" if admin_portal else "customer/auth.html", 400, title="Đăng nhập", mode="login", errors={"general": "Email hoặc mật khẩu không đúng, hoặc tài khoản không được phép truy cập."}, values={"email": email})
    if not user["email_verified"] or user["otp_enabled"]:
        start_challenge(request, user["id"], "register" if not user["email_verified"] else "login")
        return redirect("/verify")
    sign_in(request, user)
    return redirect("/admin" if user["role"] == "admin" else "/checkout" if read_cart(request) else "/account", request, "Đăng nhập thành công.")


@router.post("/forgot-password")
async def forgot(request: Request):
    data = await form_data(request)
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE email=? AND active=1", (data.get("email", "").strip().lower()[:200],)).fetchone()
    start_challenge(request, user["id"] if user else None, "reset")
    return redirect("/verify", request, "Nếu tài khoản tồn tại, bạn có thể dùng mã OTP demo để đặt lại mật khẩu.")


@router.get("/verify")
def verify_page(request: Request):
    with connect() as db:
        challenge = db.execute("SELECT * FROM otp_challenges WHERE id=?", (request.session.get("challenge"),)).fetchone()
    if not challenge or challenge["consumed"]:
        return redirect("/login", request, "Phiên xác thực không còn hiệu lực.")
    return render(request, "customer/verify.html", title="Xác thực tài khoản", challenge=challenge)


@router.post("/verify")
async def verify(request: Request):
    data = await form_data(request)
    error = ""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        challenge = db.execute("SELECT * FROM otp_challenges WHERE id=?", (request.session.get("challenge"),)).fetchone()
        if not challenge or challenge["consumed"]:
            return redirect("/login")
        if challenge["expires_at"] < time.time() or challenge["attempts"] >= 5:
            error = "Mã đã hết hạn hoặc quá 5 lần thử. Gửi mã mới để tiếp tục."
        elif not hmac.compare_digest(hashlib.sha256(data.get("code", "").encode()).hexdigest(), challenge["code_hash"]):
            db.execute("UPDATE otp_challenges SET attempts=attempts+1 WHERE id=?", (challenge["id"],))
            error = "Mã xác thực chưa đúng."
        elif not challenge["user_id"]:
            error = "Không thể xác thực tài khoản này. Kiểm tra email và thử lại."
        elif challenge["purpose"] == "reset" and (not 8 <= len(data.get("password", "")) <= 128 or data.get("password") != data.get("confirm")):
            error = "Mật khẩu cần từ 8 đến 128 ký tự và khớp với lần nhập lại."
        else:
            db.execute("UPDATE otp_challenges SET consumed=1 WHERE id=?", (challenge["id"],))
            if challenge["purpose"] == "reset":
                db.execute("UPDATE users SET password=?,auth_rev=auth_rev+1 WHERE id=?", (password_hash(data["password"]), challenge["user_id"]))
                request.session.pop("challenge", None)
                return redirect("/login", request, "Đã đặt lại mật khẩu. Vui lòng đăng nhập.")
            db.execute("UPDATE users SET email_verified=1 WHERE id=?", (challenge["user_id"],))
            user = db.execute("SELECT * FROM users WHERE id=? AND active=1", (challenge["user_id"],)).fetchone()
    if error:
        return render(request, "customer/verify.html", 400, title="Xác thực tài khoản", challenge=challenge, errors={"general": error})
    if not user:
        return redirect("/login")
    sign_in(request, user)
    return redirect("/admin" if user["role"] == "admin" else "/account", request, "Xác thực thành công.")


@router.post("/verify/resend")
async def resend(request: Request):
    await form_data(request)
    with connect() as db:
        old = db.execute("SELECT * FROM otp_challenges WHERE id=? AND consumed=0", (request.session.get("challenge"),)).fetchone()
    if old:
        if old["expires_at"] - time.time() > 270:
            return redirect("/verify", request, "Chờ 30 giây trước khi gửi mã mới.")
        start_challenge(request, old["user_id"], old["purpose"])
    return redirect("/verify")


@router.post("/logout")
async def logout(request: Request):
    await form_data(request)
    request.session.clear()
    return redirect("/")
