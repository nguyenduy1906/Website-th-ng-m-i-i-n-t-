# NEU SHOP — Full stack demo local

Ứng dụng bán đồ công nghệ bằng **Python + FastAPI + HTML/Jinja2 + SQLite**. Hai giao diện riêng: **khách hàng/public** và **admin**. Nghiệp vụ gốc ở `docs/nghiep-vu-goc.txt`; phạm vi và đối chiếu tính năng ở `docs/README.md`, `docs/implementation.md`.

Giao diện đã được thiết kế lại bằng hướng dẫn UI UX Pro Max, dùng font Be Vietnam Pro cục bộ, ảnh thật và bo góc thống nhất 5px. Nguồn bộ skill, phiên bản và cách áp dụng ghi tại [docs/ui-ux-pro-max.md](docs/ui-ux-pro-max.md); quy chuẩn nằm trong `DESIGN.md`.

## Chạy ứng dụng

Yêu cầu Python 3.11+ và npm. Đã kiểm tra trên Python 3.14.

```powershell
cd path/to/neu-shop
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm run dev
```

Mở [Cửa hàng](http://127.0.0.1:8000) hoặc [Đăng nhập quản trị](http://127.0.0.1:8000/admin/login). Dừng bằng `Ctrl+C`. `npm run start` chạy không tự reload.

Nếu PowerShell chặn script kích hoạt:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Tài khoản và dữ liệu mẫu

| Vai trò | Email | Mật khẩu |
| --- | --- | --- |
| Admin | `admin@neushop.local` | `Admin@12345` |
| Khách hàng | Tự đăng ký | Từ 8 đến 128 ký tự |

Khách tự đăng ký cần xác thực OTP. **Hộp thư mô phỏng trên trang xác thực hiển thị mã cho phiên của bạn**, có hiệu lực 5 phút, tối đa 5 lần thử. Có quên mật khẩu và bật/tắt OTP đăng nhập trong phần Bảo mật. Không gửi email hoặc SMS thật.

Tám sản phẩm mẫu, các biến thể và hai voucher `NEU100` / `WELCOME5` được khởi tạo lần đầu. Điều kiện và thời hạn thực tế của mã được đọc từ SQLite và hiển thị ở trang Ưu đãi. Không tạo đơn hàng/đánh giá giả vào dữ liệu sử dụng.

## Các luồng có thể demo

1. **Mua sắm:** tìm kiếm có gợi ý, lọc danh mục/thương hiệu/giá/đánh giá/cấu hình, sắp xếp, phân trang và chọn biến thể cập nhật giá/ảnh/tồn.
2. **Tài khoản:** thông tin cá nhân, nhiều địa chỉ (thêm/sửa/xóa/mặc định), đổi mật khẩu, OTP đăng nhập, lịch sử đơn, thông báo và trò chuyện hỗ trợ.
3. **Giỏ & đặt hàng:** giỏ lưu theo tài khoản, hợp nhất giỏ khách vãng lai khi đăng nhập, chọn các dòng cần mua, áp dụng một voucher, chọn giao tiêu chuẩn/nhanh hoặc nhận tại điểm demo.
4. **Thanh toán:** COD, QR, thẻ, ví đều mô phỏng. Online có màn hình chọn kết quả thành công/thất bại, thanh toán lại hoặc chuyển COD. Giữ tồn 15 phút; đơn quá hạn được hủy/hoàn tồn khi có yêu cầu tiếp theo vào ứng dụng. Tổng tiền và tồn kho được kiểm tra lại trong transaction; gửi lại cùng phiên đặt hàng không tạo đơn trùng.
5. **Theo dõi & hậu mãi:** timeline trạng thái, mã vận đơn demo, in biên nhận, khách xác nhận nhận hàng, hủy trước khi chuẩn bị; yêu cầu trả toàn bộ đơn trong 7 ngày sau hoàn tất. Admin duyệt → nhận hàng hợp lệ → hoàn tiền demo. Nhận trả hoàn tồn đúng một lần; hoàn tiền thu hồi điểm.
6. **Đánh giá & nội dung:** chỉ khách có đơn hoàn tất mới được đánh giá, mỗi sản phẩm một lần/đơn; ảnh PNG/JPEG tùy chọn. Có hỏi đáp, bài viết/cẩm nang và phản hồi admin.
7. **Admin:** dashboard từ dữ liệu thực trong SQLite; quản lý sản phẩm, biến thể, ảnh tải lên, danh mục/thương hiệu, nhập/xuất kho có lý do, cảnh báo tồn thấp, đơn, trả hàng, voucher, hai vai trò tài khoản, chat/hỏi đáp, bài viết/đánh giá, báo cáo/CSV, đối soát nội bộ và nhật ký thao tác.

## Cấu trúc

```text
app/
  main.py                   Điểm vào Uvicorn
  application.py            Khởi tạo FastAPI, middleware, router
  core.py                   Phiên đăng nhập, CSRF, giỏ và nghiệp vụ chung
  db.py                     Toàn bộ schema, migration, seed, kết nối SQLite và băm mật khẩu
  auth.py                   Đăng ký, đăng nhập, OTP, khôi phục mật khẩu
  store.py                  Sản phẩm, giỏ, checkout, thanh toán demo
  account.py                Tài khoản, đơn, đánh giá, đổi trả, hỗ trợ
  admin.py                  Quản trị nghiệp vụ
  templates/
    customer/               Toàn bộ HTML public và khách hàng
    admin/                  Toàn bộ HTML quản trị
  static/
    style.css               Token và thành phần dùng chung
    customer.css            Bố cục khách hàng/public
    admin.css               Bố cục quản trị
    app.js                  Dialog, tìm kiếm, polling, form và in
    images/                 Minh họa SVG cục bộ
```

Admin có shell, menu, đăng nhập và các trang quản lý riêng. Một số macro/form và nội dung chi tiết đơn được dùng chung từ thư mục customer để giữ thống nhất, không sao chép logic hiển thị. Không có HTML trang nằm lẫn ở gốc `templates`.

## Dữ liệu và nâng cấp

- Toàn bộ định nghĩa cơ sở dữ liệu nằm trong **một file `app/db.py`**: kết nối, tạo bảng, migration, dữ liệu mẫu và khởi tạo. Không dùng module `schema.py` riêng.
- Database runtime duy nhất của bản local: `data/shop.db`. Ảnh tải lên: `data/uploads`. Khóa ký phiên: `data/.session-secret`. Các dữ liệu này không đưa lên Git.
- Trước lần nâng cấp đầu tiên của database cũ, ứng dụng lưu bản sao SQLite tại `data/backups/before-v2.db`. Migration bổ sung bảng/cột, giữ tài khoản, đơn, tên/giá tại thời điểm mua và tồn kho hiện tại. Khởi động lại không nhân bản biến thể/voucher.
- Có thể đặt `NEU_DB_PATH` và `NEU_SESSION_SECRET` qua biến môi trường. Ảnh tải lên được lưu cạnh database đang dùng, nên các bài kiểm thử không ghi vào dữ liệu demo chính.
- Mật khẩu băm PBKDF2 có salt; phiên ký và cookie HttpOnly; form ghi dữ liệu kiểm tra CSRF; quyền và chủ sở hữu dữ liệu được kiểm tra ở backend. Đổi mật khẩu/khóa tài khoản/đổi role thu hồi phiên cũ. Không cho tự khóa hoặc tự bỏ quyền admin.

## Giới hạn được công bố

Đây là bản local: **không thu tiền, giao hàng, gửi email/SMS, kết nối ngân hàng/vận chuyển/ERP hoặc phát hành hóa đơn thuế thật**. Biên nhận, đối soát, bảo hành, thuế, phí giao và OTP phục vụ mô phỏng. Dùng thông tin giả để thử.

Chat và trang chi tiết đơn kiểm tra cập nhật mỗi 5 giây khi đang mở. Cơ chế dọn đơn hết hạn chạy khi có request, không phải worker nền. Điểm demo được tích lũy/thu hồi, chưa quy đổi thành tiền. Trả hàng hiện xử lý toàn bộ đơn và hoàn tiền; đổi sang sản phẩm khác thực hiện bằng đơn mua mới. Có thư viện nhiều ảnh, thumbnail/zoom, Flash Sale có giá gốc và thời hạn, bảng sinh biến thể và biểu đồ dashboard. Giao diện dùng tiếng Việt; chức năng so sánh sản phẩm và đổi ngôn ngữ đã gỡ theo yêu cầu người dùng ngày 02/11/2026. Chưa có trả góp, sàn đa người bán hoặc ứng dụng native. Font dùng fallback hệ thống nếu chưa cung cấp Be Vietnam Pro cục bộ. Chưa kiểm chứng tải lớn hoặc toàn bộ trình duyệt ngoài Chrome.

## Kiểm tra

Backend không cần dependency kiểm thử bổ sung:

```powershell
npm run check
```

Để kiểm tra bằng Chrome headless, cài các thư viện Node qua **npm**:

```powershell
npm install
npm run check:browser
```

Kiểm thử tự khởi động server và SQLite riêng trong `test-results`. Kiểm tra các trang ở 320/375/768/1280px, OTP, giỏ, đặt hàng, vận hành admin, đánh giá, yêu cầu trả hàng, dialog/bàn phím, không JavaScript và reduced motion. Ảnh và báo cáo nằm trong `test-results/browser-*`.

Khi bản demo đang chạy ở cổng 8000:

```powershell
npm run design:check
```

Dựng lại HTML ERD để mở/in offline từ `data/erd.mmd`:

```powershell
npm run docs:erd
```

File sơ đồ ở `data/erd.html` giữ mô hình do người dùng cung cấp, kể cả module trả góp tùy chọn. Sơ đồ này là tài liệu tham chiếu; schema runtime local có thêm các bảng nghiệp vụ và không triển khai trả góp.

## Bộ dữ liệu và giao diện minh họa nâng cao

- Đặc tả frontend người dùng cung cấp: `docs/frontend-brief.txt`. Bộ JSON dùng chung: `docs/mock-data.json` (khách hàng, sản phẩm/biến thể, đơn và chi tiết, đánh giá, hội thoại, đổi trả, Flash Sale).
- `npm run demo:seed` nhập dữ liệu minh họa có liên kết vào database đang cấu hình, lưu bản sao trước nhập tại `data/backups/before-ui-demo.db`. Lệnh có khóa đánh dấu để chạy lại không nhân đôi đơn hoặc đánh giá. Các đơn và đánh giá mẫu được ghi rõ là minh họa; không thay thế tài khoản hoặc đơn hiện có.
- Tài khoản khách minh họa: `demo.lan@example.test` / `Demo@12345`. Có lịch sử đơn, thông báo và yêu cầu trả hàng để thử khu khách hàng. Tài khoản admin giữ nguyên.
- Trang chủ có carousel điều khiển thủ công, sản phẩm nổi bật/mới, Flash Sale đếm ngược theo thời hạn lưu trong SQLite và thương hiệu thực sự có dữ liệu. Không tự tạo giá gốc hoặc reset đồng hồ mỗi lần tải trang.
- Thêm giỏ nhanh dùng JSON và cập nhật badge; form HTML vẫn hoạt động nếu tắt JavaScript. Tìm kiếm có ảnh/giá gợi ý và hỗ trợ bàn phím.
- Admin có sidebar thu gọn, tìm kiếm, chuông đơn chờ xử lý, biểu đồ SVG theo tiền đã thu/trạng thái đơn, bảng voucher, gallery tải ảnh, bảng tổ hợp màu/dung lượng để nhập SKU/giá/tồn.
- `app/static/ui.js` và `ui.css` chứa các tương tác/kiểu dùng chung. Component template tái sử dụng nằm trong `admin/components/` cùng các macro và fragment phía khách hàng. Không chuyển dự án sang React hoặc thêm dependency biểu đồ từ CDN.

## Chức năng bổ sung

Đã có liên hệ công khai/hộp thư admin, giới thiệu và dịch vụ có thể chỉnh sửa, danh mục hai cấp, tin tức theo chủ đề, thống kê truy cập và hợp đồng mua hàng điện tử demo. Xem [hướng dẫn chi tiết](docs/feature-completion.md). Cấu hình thông tin cửa hàng tại `/admin/settings`. Hợp đồng nằm trong chi tiết đơn và `/account/contracts`; admin quản lý tại `/admin/contracts`. OTP chỉ mô phỏng trên local; tải HTML hoặc in thành PDF bằng trình duyệt.

Chạy kiểm thử bổ sung bằng `npm run check:portal` (database thử riêng).

## Chuẩn bị GitHub

Xem [hướng dẫn đưa dự án lên GitHub](docs/github-setup.md), [lưu ý bảo mật](SECURITY.md) và [nguồn tài sản bên thứ ba](THIRD_PARTY_NOTICES.md). Sau khi clone, dùng `npm ci` để cài đúng dependency từ lockfile. Cấu hình chatbot AI tại [docs/chatbot-ai.md](docs/chatbot-ai.md); không đưa `.env` hay database cá nhân lên kho.
