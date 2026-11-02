import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .core import audit, form_data, integer, notify, order_for, redirect, render, require_admin, require_user, templates, void_contract
from .db import connect, get_settings

router = APIRouter()
LABELS = {'draft':'Chờ xác nhận','signed':'Đã xác nhận OTP','void':'Đã hủy hiệu lực'}
TERMS = '## 1. Phạm vi áp dụng\nĐây là hợp đồng mua hàng thử nghiệm của NEU SHOP trên local, không phát sinh thu tiền, giao hàng hoặc ký số qua nhà cung cấp bên ngoài.\n## 2. Hàng hóa và giá trị\nDanh sách hàng hóa, phiên bản, số lượng, đơn giá, phí vận chuyển và giảm giá được lưu theo đơn hàng tại thời điểm lập bản hợp đồng này.\n## 3. Giao nhận và thanh toán\nThông tin người nhận, địa chỉ và phương thức thanh toán được thể hiện trong bản nội dung đã lưu. Khách xác nhận hợp đồng trước khi thanh toán online hoặc chờ admin duyệt đơn COD. Nếu thanh toán online thất bại, khách có thể thử lại hoặc chủ động chuyển sang COD; việc chuyển phương thức được ghi trong lịch sử đơn và không thay đổi tổng tiền hay bản nội dung gốc. Trạng thái xử lý tiếp tục được theo dõi trong đơn hàng.\n## 4. Chính sách hậu mãi\nÁp dụng chính sách được ghi trong bản hợp đồng: được yêu cầu hủy trước khi chuẩn bị; được gửi yêu cầu trả toàn bộ đơn trong 7 ngày từ khi hoàn tất. Admin xét duyệt và hoàn tiền thử nghiệm khi đủ điều kiện.\n## 5. Xác nhận và lưu trữ\nKhách đọc nội dung, đồng ý và nhập mã OTP để xác nhận. Sau xác nhận, nội dung gốc không được chỉnh sửa. Hủy đơn hoặc hoàn tiền sẽ ghi nhận hủy hiệu lực nhưng giữ lại lịch sử và bản nội dung đã xác nhận.'


def contract_for(db,user,contract_id):
    row=db.execute('SELECT c.*,o.status AS order_status,o.payment_status FROM sales_contracts c JOIN orders o ON o.id=c.order_id WHERE c.id=?',(contract_id,)).fetchone()
    if not row or (row['user_id']!=user['id'] and user['role']!='admin'):
        raise HTTPException(404,'Không tìm thấy hợp đồng.')
    return row


def ensure_order(order):
    status=order['order_status'] if 'order_status' in order.keys() else order['status']
    if status in ('Đã hủy','Đã trả hàng') or order['payment_status']=='Đã hoàn tiền':
        raise HTTPException(409,'Đơn đã hủy hoặc hoàn trả, không thể lập/xác nhận hợp đồng mới.')


def create_order_contract(db,user,order):
    ensure_order(order)
    order_id=order['id']
    previous=db.execute('SELECT id FROM sales_contracts WHERE order_id=?',(order_id,)).fetchone()
    if previous:
        return previous['id']
    settings=get_settings(db)
    snapshot={'version':'NEU-SALES-DEMO-1','seller':{key:settings.get(key,'') for key in ('shop_name','email','hotline','address')},
              'buyer':{'name':user['name'],'email':user['email']},
              'order':{key:order[key] for key in ('id','recipient','phone','address','receive_method','shipping_method','payment_method','subtotal','shipping_fee','discount','total','created_at')},
              'items':[dict(row) for row in db.execute('SELECT name,variant_label,quantity,price FROM order_items WHERE order_id=? ORDER BY id',(order_id,))],
              'terms':TERMS}
    raw=json.dumps(snapshot,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(raw.encode()).hexdigest()
    number=f'HD-{datetime.now().year}-{order_id:06d}'
    contract_id=db.execute('INSERT INTO sales_contracts(order_id,user_id,number,snapshot,document_hash) VALUES(?,?,?,?,?)',(order_id,user['id'],number,raw,digest)).lastrowid
    db.execute("INSERT INTO contract_events(contract_id,actor_id,action,detail) VALUES(?,?,'created',?)",(contract_id,user['id'],'Đã lưu bản nội dung '+digest))
    notify(db,user['id'],'Hợp đồng '+number,'Đọc và xác nhận hợp đồng trước khi thanh toán hoặc chờ duyệt đơn COD.',f'/contracts/{contract_id}')
    audit(db,user['id'],'Lập hợp đồng ',number)
    return contract_id


@router.post('/orders/{order_id}/contract')
async def create(request: Request,order_id:int):
    user=require_user(request)
    await form_data(request)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        order=order_for(db,user,order_id)
        if order['user_id']!=user['id']:
            raise HTTPException(403,'Chỉ chủ đơn hàng được lập hợp đồng.')
        contract_id=create_order_contract(db,user,order)
    return redirect(f'/contracts/{contract_id}')


@router.get('/account/contracts')
@router.get('/admin/contracts')
def listing(request: Request,status:str=''):
    user=require_user(request)
    admin_view=request.url.path.startswith('/admin')
    if admin_view:
        require_admin(request)
    with connect() as db:
        rows=db.execute("SELECT c.*,o.total,u.name AS customer_name FROM sales_contracts c JOIN orders o ON o.id=c.order_id JOIN users u ON u.id=c.user_id WHERE (?=1 OR c.user_id=?) AND (?='' OR c.status=?) ORDER BY c.id DESC",(int(admin_view),user['id'],status,status)).fetchall()
    return render(request,'admin/contracts.html' if admin_view else 'customer/contracts.html',title='Hợp đồng điện tử ',section='contracts',account_section='contracts',contracts=rows,contract_statuses=LABELS,selected_status=status)


@router.get('/contracts/{contract_id}')
@router.get('/admin/contracts/{contract_id}')
def detail(request: Request,contract_id:int):
    user=require_user(request)
    admin_view=request.url.path.startswith('/admin')
    if admin_view:
        require_admin(request)
    with connect() as db:
        contract=contract_for(db,user,contract_id)
        events=db.execute('SELECT e.*,u.name FROM contract_events e LEFT JOIN users u ON u.id=e.actor_id WHERE contract_id=? ORDER BY e.id',(contract_id,)).fetchall()
        payment=db.execute("SELECT id FROM payments WHERE order_id=? AND kind='payment' AND method!='cod' AND status='Chờ thanh toán' ORDER BY id DESC LIMIT 1",(contract['order_id'],)).fetchone()
    snapshot=json.loads(contract['snapshot'])
    integrity=hmac.compare_digest(hashlib.sha256(contract['snapshot'].encode()).hexdigest(),contract['document_hash'])
    session_hash=hashlib.sha256(request.session.get('contract_nonce','').encode()).hexdigest()
    show_code=contract['user_id']==user['id'] and contract['status']=='draft' and contract['otp_expires_at']>=int(time.time()) and bool(contract['otp_session_hash']) and hmac.compare_digest(session_hash,contract['otp_session_hash'])
    return render(request,'admin/contract.html' if admin_view else 'customer/contract.html',title=contract['number'],section='contracts',account_section='contracts',contract=contract,snapshot=snapshot,contract_events=events,contract_statuses=LABELS,integrity=integrity,show_code=show_code,pending_payment=payment)


@router.post('/contracts/{contract_id}/otp')
async def issue_otp(request: Request,contract_id:int):
    user=require_user(request)
    await form_data(request)
    nonce=request.session.setdefault('contract_nonce',secrets.token_urlsafe(32))
    now=int(time.time())
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        contract=contract_for(db,user,contract_id)
        if contract['user_id']!=user['id']:
            raise HTTPException(403,'Chỉ khách sở hữu hợp đồng được nhận mã xác nhận.')
        ensure_order(contract)
        if contract['status']!='draft':
            raise HTTPException(409,'Hợp đồng không còn ở trạng thái chờ xác nhận.')
        if contract['otp_sent_at']>now-30:
            return redirect(f'/contracts/{contract_id}',request,'Vui lòng chờ 30 giây trước khi lấy mã mới.')
        code=f'{secrets.randbelow(1000000):06d}'
        db.execute('UPDATE sales_contracts SET otp_hash=?,otp_demo_code=?,otp_session_hash=?,otp_expires_at=?,otp_sent_at=?,otp_attempts=0 WHERE id=?',(hashlib.sha256(code.encode()).hexdigest(),code,hashlib.sha256(nonce.encode()).hexdigest(),now+300,now,contract_id))
        db.execute("INSERT INTO contract_events(contract_id,actor_id,action,detail) VALUES(?,?,'otp_issued','Mã có hiệu lực 5 phút; tối đa 5 lần thử.')",(contract_id,user['id']))
    return redirect(f'/contracts/{contract_id}',request,'Đã tạo mã OTP riêng cho hợp đồng này.')


@router.post('/contracts/{contract_id}/sign')
async def sign(request: Request,contract_id:int):
    user=require_user(request)
    data=await form_data(request)
    error=''
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        contract=contract_for(db,user,contract_id)
        if contract['user_id']!=user['id']:
            raise HTTPException(403,'Không thể xác nhận thay khách hàng.')
        ensure_order(contract)
        if contract['status']=='signed':
            return redirect(f'/contracts/{contract_id}',request,'Hợp đồng đã được xác nhận trước đó.')
        if contract['status']!='draft':
            raise HTTPException(409,'Hợp đồng đã bị hủy hiệu lực.')
        snapshot=json.loads(contract['snapshot'])
        session_hash=hashlib.sha256(request.session.get('contract_nonce','').encode()).hexdigest()
        if hashlib.sha256(contract['snapshot'].encode()).hexdigest()!=contract['document_hash']:
            error='Nội dung hợp đồng không khớp bản đã lưu. Không thể xác nhận.'
        elif data.get('consent')!='1' or ' '.join(data.get('signer_name','').split()).casefold()!=' '.join(snapshot['buyer']['name'].split()).casefold():
            error='Đọc, đồng ý nội dung và nhập đúng họ tên chủ tài khoản trên hợp đồng.'
        elif not contract['otp_hash'] or contract['otp_expires_at']<int(time.time()) or contract['otp_attempts']>=5:
            error='Mã đã hết hạn hoặc quá 5 lần thử. Lấy mã mới để tiếp tục.'
        elif not contract['otp_session_hash'] or not hmac.compare_digest(session_hash,contract['otp_session_hash']):
            error='Mã thuộc phiên đăng nhập khác. Hãy lấy mã mới trong phiên này.'
        elif not hmac.compare_digest(hashlib.sha256(data.get('code','').encode()).hexdigest(),contract['otp_hash']):
            db.execute('UPDATE sales_contracts SET otp_attempts=otp_attempts+1 WHERE id=?',(contract_id,))
            error='Mã OTP chưa đúng.'
        else:
            db.execute("UPDATE sales_contracts SET status='signed',signed_at=CURRENT_TIMESTAMP,signer_name=?,otp_hash='',otp_demo_code='',otp_session_hash='' WHERE id=?",(snapshot['buyer']['name'],contract_id))
            db.execute("INSERT INTO contract_events(contract_id,actor_id,action,detail) VALUES(?,?,'signed',?)",(contract_id,user['id'],'Khách đồng ý và xác nhận OTP. SHA-256: '+contract['document_hash']))
            notify(db,user['id'],'Đã xác nhận '+contract['number'],'Bạn có thể xem, tải và in bản hợp đồng trong tài khoản.',f'/contracts/{contract_id}')
            audit(db,user['id'],'Xác nhận hợp đồng OTP ',contract['number'])
    return redirect(f'/contracts/{contract_id}',request,error or 'Đã xác nhận hợp đồng bằng OTP.')


@router.post('/admin/contracts/{contract_id}/void')
async def void(request: Request,contract_id:int):
    actor=require_admin(request)
    data=await form_data(request)
    reason=data.get('reason','').strip()
    if not 5<=len(reason)<=500:
        raise HTTPException(400,'Lý do hủy từ 5 đến 500 ký tự.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        contract=contract_for(db,actor,contract_id)
        void_contract(db,contract['order_id'],actor['id'],reason)
        audit(db,actor['id'],'Hủy hiệu lực hợp đồng',contract['number']+': '+reason)
    return redirect(f'/admin/contracts/{contract_id}',request,'Đã ghi nhận hủy hiệu lực; nội dung và lịch sử vẫn được giữ.')


@router.get('/contracts/{contract_id}/print')
@router.get('/contracts/{contract_id}/download')
@router.get('/admin/contracts/{contract_id}/print')
@router.get('/admin/contracts/{contract_id}/download')
def document(request: Request,contract_id:int):
    user=require_user(request)
    admin_view=request.url.path.startswith('/admin/')
    if admin_view:
        require_admin(request)
    with connect() as db:
        contract=contract_for(db,user,contract_id)
    snapshot=json.loads(contract['snapshot'])
    integrity=hashlib.sha256(contract['snapshot'].encode()).hexdigest()==contract['document_hash']
    if not integrity:
        raise HTTPException(409,'Không thể xuất bản hợp đồng có nội dung không toàn vẹn.')
    html=templates.env.get_template('customer/contract_document.html').render(contract=contract,snapshot=snapshot,contract_statuses=LABELS,request=request,download=request.url.path.endswith('/download'),admin_view=admin_view)
    headers={'Content-Disposition':f'attachment; filename="NEUSHOP-{contract["number"]}.html"'} if request.url.path.endswith('/download') else {}
    return HTMLResponse(html,headers=headers)
