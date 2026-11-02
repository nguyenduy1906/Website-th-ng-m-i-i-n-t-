import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import account, admin, auth, store, portal, contracts
from .portal import track_visit
from .core import UPLOAD_DIR, expire_orders, redirect, render
from .db import ROOT, connect, initialize, session_secret


@asynccontextmanager
async def lifespan(app):
    initialize()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="NEU SHOP Local", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")


@app.middleware("http")
async def browser_headers(request: Request, call_next):
    request.session.setdefault("csrf", secrets.token_urlsafe(32))
    if not request.url.path.startswith(("/static", "/media")):
        expire_orders()
    response = await call_next(request)
    if response.status_code==200:
        track_visit(request)
    response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin", "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-src https://www.google.com; form-action 'self'; frame-ancestors 'none'; base-uri 'self'", "Cache-Control": "no-store"})
    return response


app.add_middleware(SessionMiddleware, secret_key=session_secret(), same_site="lax", max_age=86400, https_only=False)


@app.exception_handler(StarletteHTTPException)
async def app_error(request, error):
    if error.status_code == 401:
        return redirect("/admin/login" if request.url.path.startswith("/admin") else "/login", request, "Vui lòng đăng nhập để tiếp tục.")
    return render(request, "admin/error.html" if request.url.path.startswith("/admin") else "customer/error.html", error.status_code, title="Không thể hoàn tất yêu cầu", message=error.detail, code=error.status_code)


for router in (auth.router, portal.router, contracts.router, store.router, account.router, admin.router):
    app.include_router(router)


@app.get("/api/health")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok", "mode": "local-demo", "version": 2}
