import hashlib
import re
import secrets
import time
from urllib.parse import quote, urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .core import audit, form_data, integer, redirect, render, require_admin, richtext, upload
from .db import connect, get_settings

router = APIRouter()
CONTACT_STATUSES = {'new':'Mới nhận','open':'Đang xử lý','replied':'Đã phản hồi','closed':'Đã đóng'}
SETTING_FIELDS = {'shop_name':80,'tagline':150,'hotline':30,'email':200,'address':300,'opening_hours':150,'map_query':300,'facebook':300,'youtube':300,'zalo':300,'skype':160}


def visitor_key(request):
    key = request.session.setdefault('visitor_key', secrets.token_urlsafe(24))
    return hashlib.sha256(key.encode()).hexdigest()


def track_visit(request):
    path = request.url.path
    if request.method != 'GET' or not (path=='/' or path in ('/products','/about','/services','/contact','/offers','/news','/policies') or re.fullmatch(r'/(products|news)/\d+',path)):
        return
    key, now = visitor_key(request), int(time.time())
    with connect() as db:
        db.execute('INSERT INTO visitor_sessions VALUES(?,?,?) ON CONFLICT(visitor_key) DO UPDATE SET last_seen=excluded.last_seen', (key,now,now))
        db.execute("INSERT INTO page_visits(day,views) VALUES(date('now','+7 hours'),1) ON CONFLICT(day) DO UPDATE SET views=views+1")


@router.post('/api/visits/heartbeat')
async def heartbeat(request: Request):
    await form_data(request)
    if request.session.get('visitor_key'):
        with connect() as db:
            db.execute('UPDATE visitor_sessions SET last_seen=? WHERE visitor_key=?',(int(time.time()),visitor_key(request)))
    return {'ok':True}


@router.get('/api/visits/stats')
def visit_stats():
    with connect() as db:
        return {'views':db.execute('SELECT COALESCE(SUM(views),0) FROM page_visits').fetchone()[0],'visitors':db.execute('SELECT COUNT(*) FROM visitor_sessions').fetchone()[0],'online':db.execute('SELECT COUNT(*) FROM visitor_sessions WHERE last_seen>=?',(int(time.time())-180,)).fetchone()[0]}


@router.get('/about')
@router.get('/services')
def page(request: Request):
    with connect() as db:
        record = db.execute('SELECT * FROM site_pages WHERE slug=? AND active=1',(request.url.path.strip('/'),)).fetchone()
    if not record:
        raise HTTPException(404,'Nội dung chưa được công bố.')
    template = 'customer/about.html' if record['slug'] == 'about' else 'customer/site_page.html'
    return render(request,template,title=record['title'],page=record)


@router.get('/contact')
def contact(request: Request):
    visitor_key(request)
    return render(request,'customer/contact.html',title='Liên hệ NEU SHOP')


@router.post('/contact')
async def contact_send(request: Request):
    data = await form_data(request)
    values = {name:data.get(name,'').strip() for name in ('name','email','phone','address','content')}
    errors = {}
    for field,low,high in (('name',2,80),('content',10,3000),('address',0,300),('phone',0,20)):
        if not low<=len(values[field])<=high:
            errors[field]=f'Nhập từ {low} đến {high} ký tự.'
    if len(values['email'])>200 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',values['email']):
        errors['email']='Nhập email hợp lệ để ghi nhận thông tin liên hệ.'
    if values['phone'] and not re.fullmatch(r'[+0-9 ()-]{8,20}',values['phone']):
        errors['phone']='Số điện thoại chưa đúng định dạng.'
    if data.get('website',''):
        errors['general']='Không thể gửi biểu mẫu. Vui lòng thử lại.'
    if errors:
        return render(request,'customer/contact.html',400,title='Kiểm tra thông tin liên hệ',values=values,errors=errors)
    key, receipt = visitor_key(request),secrets.token_urlsafe(24)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM contact_requests WHERE visitor_key=? AND created_at>datetime('now','-1 minute')",(key,)).fetchone():
            return render(request,'customer/contact.html',429,title='Liên hệ',values=values,errors={'general':'Bạn vừa gửi yêu cầu. Vui lòng chờ một phút hoặc xem lại phiếu đã gửi.'})
        db.execute('INSERT INTO contact_requests(receipt,visitor_key,name,email,phone,address,content) VALUES(?,?,?,?,?,?,?)',(receipt,key,values['name'],values['email'].lower(),values['phone'],values['address'],values['content']))
    return redirect('/contact/requests/'+receipt,request,'Đã tiếp nhận yêu cầu liên hệ. Lưu đường dẫn phiếu này để xem phản hồi.')


@router.get('/contact/requests/{receipt}')
def contact_receipt(request: Request,receipt:str):
    with connect() as db:
        record=db.execute('SELECT * FROM contact_requests WHERE receipt=?',(receipt,)).fetchone()
    if not record:
        raise HTTPException(404,'Không tìm thấy phiếu liên hệ.')
    return render(request,'customer/contact_receipt.html',title='Phiếu liên hệ',record=record,contact_statuses=CONTACT_STATUSES)


@router.get('/admin/settings')
def settings(request: Request):
    require_admin(request)
    with connect() as db:
        pages=db.execute('SELECT * FROM site_pages ORDER BY rowid').fetchall()
    return render(request,'admin/settings.html',title='Thông tin cửa hàng',section='settings',pages=pages)


@router.post('/admin/settings')
async def settings_save(request: Request):
    actor=require_admin(request)
    data=await form_data(request)
    values={key:data.get(key,'').strip() for key in SETTING_FIELDS}
    for key,limit in SETTING_FIELDS.items():
        if len(values[key])>limit:
            raise HTTPException(400,f'Trường {key} tối đa {limit} ký tự.')
    if len(values['shop_name'])<2:
        raise HTTPException(400,'Tên cửa hàng cần từ 2 đến 80 ký tự.')
    if values['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',values['email']):
        raise HTTPException(400,'Email cửa hàng không hợp lệ.')
    for key in ('facebook','youtube','zalo'):
        if values[key] and (urlparse(values[key]).scheme!='https' or not urlparse(values[key]).netloc or any(c in values[key] for c in '\r\n\t')):
            raise HTTPException(400,'Liên kết mạng xã hội phải là URL HTTPS đầy đủ.')
    if values['skype'] and not re.fullmatch(r'skype:[\w.+:@-]{2,100}\?chat',values['skype']):
        raise HTTPException(400,'Liên kết Skype có dạng skype:ten_tai_khoan?chat.')
    values['show_statistics']='1' if data.get('show_statistics')=='1' else '0'
    with connect() as db:
        db.executemany('INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',values.items())
        audit(db,actor['id'],'Cập nhật thông tin cửa hàng','Thông tin liên hệ và liên kết công khai')
    return redirect('/admin/settings',request,'Đã lưu thông tin cửa hàng.')


@router.post('/admin/pages/{slug}')
async def page_save(request: Request,slug:str):
    actor=require_admin(request)
    data=await form_data(request)
    title,summary,body=(data.get(key,'').strip() for key in ('title','summary','body'))
    if not 3<=len(title)<=150 or not 10<=len(summary)<=500 or not 30<=len(body)<=15000:
        raise HTTPException(400,'Tiêu đề 3–150, giới thiệu ngắn 10–500, nội dung 30–15.000 ký tự.')
    media=await upload(data)
    with connect() as db:
        row=db.execute('SELECT * FROM site_pages WHERE slug=?',(slug,)).fetchone()
        if not row:
            raise HTTPException(404,'Không tìm thấy trang nội dung.')
        db.execute('UPDATE site_pages SET title=?,summary=?,body=?,image=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE slug=?',(title,summary,body,media or row['image'],int(data.get('active')=='1'),slug))
        audit(db,actor['id'],'Cập nhật trang giới thiệu',slug)
    return redirect('/admin/settings',request,'Đã cập nhật trang nội dung.')


@router.post('/admin/content/preview')
async def preview(request: Request):
    require_admin(request)
    data=await form_data(request)
    return {'html':str(richtext(data.get('content','')[:15000]))}


@router.get('/admin/contact')
@router.get('/admin/contact/{message_id}')
def inbox(request: Request,message_id:int=0,status:str='',q:str=''):
    require_admin(request)
    with connect() as db:
        rows=db.execute("SELECT * FROM contact_requests WHERE (?='' OR status=?) AND (name LIKE ? OR email LIKE ? OR content LIKE ?) ORDER BY id DESC LIMIT 200",(status,status,*([f'%{q[:100]}%']*3))).fetchall()
        selected=db.execute('SELECT * FROM contact_requests WHERE id=?',(message_id,)).fetchone() if message_id else None
        if message_id and not selected:
            raise HTTPException(404,'Không tìm thấy yêu cầu liên hệ.')
    return render(request,'admin/contact.html',title='Hộp thư liên hệ',section='contact',records=rows,selected=selected,contact_statuses=CONTACT_STATUSES,selected_status=status,q=q[:100])


@router.post('/admin/contact/{message_id}')
async def reply(request: Request,message_id:int):
    actor=require_admin(request)
    data=await form_data(request)
    status,response=data.get('status',''),data.get('response','').strip()
    if status not in CONTACT_STATUSES or len(response)>3000 or (status=='replied' and len(response)<5):
        raise HTTPException(400,'Chọn trạng thái; phản hồi cần 5–3.000 ký tự khi đánh dấu đã phản hồi.')
    with connect() as db:
        if not db.execute('SELECT 1 FROM contact_requests WHERE id=?',(message_id,)).fetchone():
            raise HTTPException(404,'Không tìm thấy phiếu liên hệ.')
        db.execute('UPDATE contact_requests SET status=?,response=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,response,message_id))
        audit(db,actor['id'],'Phản hồi liên hệ',str(message_id))
    return redirect(f'/admin/contact/{message_id}',request,'Đã lưu phản hồi trên phiếu liên hệ. Không gửi email thực tế.')


@router.get('/admin/analytics')
def analytics(request: Request):
    require_admin(request)
    with connect() as db:
        days=db.execute("SELECT v.day,v.views,(SELECT COUNT(*) FROM visitor_sessions s WHERE date(s.first_seen,'unixepoch','+7 hours')=v.day) AS visitors FROM page_visits v ORDER BY day DESC LIMIT 30").fetchall()
        today=db.execute("SELECT COALESCE(SUM(views),0) FROM page_visits WHERE day=date('now','+7 hours')").fetchone()[0]
    return render(request,'admin/analytics.html',title='Thống kê truy cập',section='analytics',days=days,today_views=today)


@router.post('/admin/content/articles/{article_id}/delete')
async def article_delete(request: Request,article_id:int):
    actor=require_admin(request)
    await form_data(request)
    with connect() as db:
        db.execute('DELETE FROM articles WHERE id=?',(article_id,))
        audit(db,actor['id'],'Xóa bài viết',str(article_id))
    return redirect('/admin/content',request,'Đã xóa bài viết.')


@router.post('/admin/products/{product_id}/archive')
async def archive_product(request: Request,product_id:int):
    actor=require_admin(request)
    await form_data(request)
    with connect() as db:
        if not db.execute('SELECT 1 FROM products WHERE id=?',(product_id,)).fetchone():
            raise HTTPException(404,'Không tìm thấy sản phẩm.')
        db.execute('UPDATE products SET active=0,featured=0,deleted_at=CURRENT_TIMESTAMP WHERE id=?',(product_id,))
        audit(db,actor['id'],'Xóa sản phẩm khỏi danh mục (lưu trữ)',str(product_id))
    return redirect('/admin/products',request,'Đã xóa khỏi danh mục; dữ liệu đơn và lịch sử vẫn được giữ.')


@router.get('/admin/archive')
def archive(request: Request):
    require_admin(request)
    with connect() as db:
        rows=db.execute('SELECT * FROM products WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC,id DESC').fetchall()
    return render(request,'admin/archive.html',title='Sản phẩm lưu trữ',section='products',products=rows)


@router.post('/admin/products/{product_id}/restore')
async def restore_product(request: Request,product_id:int):
    actor=require_admin(request)
    await form_data(request)
    with connect() as db:
        db.execute('UPDATE products SET deleted_at=NULL,active=0 WHERE id=?',(product_id,))
        audit(db,actor['id'],'Khôi phục sản phẩm từ lưu trữ',str(product_id))
    return redirect('/admin/products',request,'Đã khôi phục ở trạng thái ẩn. Kiểm tra thông tin trước khi công bố lại.')


@router.post('/admin/catalog/{kind}/{key}/delete')
async def catalog_delete(request: Request,kind:str,key:str):
    actor=require_admin(request)
    await form_data(request)
    with connect() as db:
        if kind=='category':
            used=db.execute('SELECT 1 FROM products WHERE category=? OR subcategory=?',(key,key)).fetchone() or db.execute('SELECT 1 FROM categories WHERE parent_slug=?',(key,)).fetchone()
            if used:
                raise HTTPException(409,'Danh mục đang được sử dụng. Hãy ẩn hoặc chuyển dữ liệu trước khi xóa.')
            db.execute('DELETE FROM categories WHERE slug=?',(key,))
        elif kind=='brand':
            if db.execute('SELECT 1 FROM products WHERE brand_id=?',(integer(key),)).fetchone():
                raise HTTPException(409,'Thương hiệu đang có sản phẩm. Hãy ẩn thay vì xóa.')
            db.execute('DELETE FROM brands WHERE id=?',(integer(key),))
        else:
            raise HTTPException(400,'Nhóm dữ liệu không hợp lệ.')
        audit(db,actor['id'],'Xóa danh mục/thương hiệu',kind+': '+key)
    return redirect('/admin/catalog',request,'Đã xóa mục chưa được sử dụng.')


@router.post('/admin/topics')
async def topic_save(request: Request):
    actor=require_admin(request)
    data=await form_data(request)
    name=data.get('name','').strip()
    if not 2<=len(name)<=80:
        raise HTTPException(400,'Tên chủ đề từ 2 đến 80 ký tự.')
    topic_id=integer(data.get('id'))
    with connect() as db:
        if db.execute('SELECT 1 FROM article_topics WHERE name=? AND id!=?',(name,topic_id)).fetchone():
            raise HTTPException(400,'Chủ đề đã tồn tại.')
        if topic_id:
            db.execute('UPDATE article_topics SET name=?,active=? WHERE id=?',(name,int(data.get('active')=='1'),topic_id))
        else:
            db.execute('INSERT INTO article_topics(name) VALUES(?)',(name,))
        audit(db,actor['id'],'Lưu chủ đề tin tức',name)
    return redirect('/admin/content',request,'Đã lưu chủ đề.')
