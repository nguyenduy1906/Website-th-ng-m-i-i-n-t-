# Đối chiếu nghiệp vụ và bản local

Nguồn: `nghiep-vu-goc.txt`, mục 2.1.3 (FR01–FR26) và quy trình To-Be. Phạm vi giao diện theo `README.md` trong thư mục docs: khách hàng/public và admin, không tách màn hình cho các phòng ban.

| Yêu cầu | Triển khai local | Trang / khu vực |
| --- | --- | --- |
| FR01 Đăng ký | Email, mật khẩu, OTP mô phỏng có hạn và giới hạn lần thử. Chưa đăng ký bằng số điện thoại. | `/register`, `/verify` |
| FR02–03 Xác thực | Đăng nhập/đăng xuất, quên/đổi mật khẩu, bật OTP đăng nhập; thu hồi phiên khi đổi thông tin bảo mật. | `/login`, `/forgot-password`, `/account/security`, `/admin/login` |
| FR04 Tìm kiếm | Từ khóa và gợi ý tên sản phẩm. | `/products`, `/api/search` |
| FR05 Lọc | Danh mục, thương hiệu, giá, đánh giá đã có, cấu hình/dung lượng. | `/products` |
| FR06 Sắp xếp | Nổi bật, mới nhất, giá tăng/giảm, tên. Có Flash Sale và giá gốc; chưa có tùy chọn sắp theo % giảm. | `/products` |
| FR07 Chi tiết | Mô tả, thông số, thương hiệu, biến thể, giá, tồn, ảnh, bảo hành mẫu, đánh giá. Thư viện nhiều ảnh, thumbnail, zoom và ảnh riêng theo biến thể. | `/products/{id}` |
| FR08 So sánh | Đã gỡ theo yêu cầu người dùng ngày 02/11/2026. | Không triển khai |
| FR09 Giỏ | Thêm/xóa/số lượng/chọn dòng đặt hàng, lưu theo tài khoản, hợp nhất giỏ vãng lai. | `/cart` |
| FR10 Khuyến mãi | Một voucher/đơn, kiểm tra thời hạn, min đơn, giới hạn lượt, trần giảm và tính lại phía server. | `/offers`, `/checkout` |
| FR11 Đặt hàng | Địa chỉ nhập mới/đã lưu, hình thức nhận, phí giao, giá/giảm/tổng minh bạch, giữ tồn trong transaction, chống tạo trùng theo khóa checkout. | `/checkout` |
| FR12 Thanh toán | COD, QR, thẻ, ví qua sandbox local; thử thành công/thất bại, thử lại, đổi COD, hết hạn trả tồn. Không tích hợp cổng thật hay callback ngân hàng. | `/payments/{id}`, `/orders/{id}` |
| FR13 Hồ sơ | Thông tin cá nhân, nhiều địa chỉ, mặc định, mật khẩu/OTP, điểm tích lũy demo. Chưa đổi điểm thành thanh toán. | `/account/*` |
| FR14 Theo dõi | Timeline, trạng thái vận hành và thanh toán tách biệt, mã theo dõi demo, tự kiểm tra cập nhật khi mở trang, xác nhận đã nhận. | `/orders/{id}` |
| FR15 Hậu mãi | Hủy trước chuẩn bị; yêu cầu trả toàn bộ đơn trong 7 ngày; duyệt/từ chối có lý do, kiểm hàng, hoàn tiền demo về phương thức gốc. Đổi sang mặt hàng khác bằng đơn mới, chưa xử lý trả từng dòng. | `/orders/{id}`, `/admin/returns` |
| FR16 Đánh giá | Chỉ đơn đã hoàn tất/đã mua, một lần/sản phẩm/đơn, 1–5 sao, nhận xét, ảnh tùy chọn. | `/products/{id}#reviews` |
| FR17 Hỏi đáp | Khách đăng nhập đặt câu hỏi, admin trả lời và tạo thông báo. | `/products/{id}#questions`, `/admin/support` |
| FR18 Chat | Hội thoại khách–admin, polling 5 giây, có lịch sử và phân quyền. | `/account/support`, `/admin/support` |
| FR19 Thông báo | Lưu thông báo nội bộ cho đơn, thanh toán, đổi trả và phản hồi, đánh dấu đã đọc. OTP hiển thị trong phiên demo. Không gửi email/SMS thật. | `/account/notifications` |
| FR20 Nội dung | Danh sách/chi tiết bài viết, admin thêm/sửa/ẩn. | `/news`, `/admin/content` |
| FR21 Sản phẩm | Thêm/sửa/ẩn, ảnh chính tải lên, biến thể có giá/ảnh, danh mục và thương hiệu thêm/sửa/ẩn. | `/admin/products`, `/admin/catalog` |
| FR22 Kho | Biến động nhập/xuất có lý do, không cho âm kho, lịch sử, tồn thấp ≤ 5; đồng bộ tổng tồn sản phẩm. | `/admin/inventory` |
| FR23 Đơn | Các bước hợp lệ: xác nhận → chuẩn bị → giao/chờ nhận → hoàn tất; hủy hoàn tồn; tiền COD ghi thu khi hoàn tất. | `/admin/orders` |
| FR24 Voucher | Bảng voucher, tạo/sửa điều kiện, thời hạn, giới hạn và bật/tắt; Flash Sale theo biến thể có giá gốc, giá giảm và thời hạn. | `/admin/vouchers` |
| FR25 Báo cáo | Thu, hoàn, thu ròng theo giao dịch; lọc ngày tạo giao dịch, tồn hiện tại, sản phẩm bán chạy toàn thời gian, CSV, xác nhận đối soát nội bộ. Chưa đồng bộ ERP/ngân hàng/hãng giao. | `/admin/reports` |
| FR26 Người dùng | Hai role customer/admin, tạo tài khoản demo, khóa/mở, đổi role, bảo vệ admin cuối cùng, thu hồi phiên cũ, audit log. Không tạo các role nhân viên riêng. | `/admin/users`, `/admin/logs` |

## Quy tắc demo cụ thể

- Phí giao tiêu chuẩn: 30.000 đồng; nhanh: 50.000 đồng; nhận tại điểm demo: 0 đồng. Giá đã gồm thuế mô phỏng, không xuất hóa đơn thuế thật. Không có địa chỉ điểm nhận hàng thực tế.
- Online giữ hàng tối đa 15 phút. Khi có request mới, các đơn chờ thanh toán quá hạn được tự hủy/hoàn tồn. COD không có thời hạn chờ thanh toán online.
- Hủy đơn đã thanh toán thực hiện hoàn tiền mô phỏng đúng một lần. Trả hàng hoàn tồn khi admin xác nhận nhận hàng, hoàn tiền ở bước sau. Không đảo ngược trạng thái đã kết thúc.
- Mỗi 100.000 đồng trong đơn hoàn tất được 1 điểm demo; hoàn toàn bộ đơn thu hồi số điểm đã cộng.
- Kiểm tra OTP tối đa 5 lần, hiệu lực 5 phút, gửi lại sau ít nhất 30 giây. Mã demo chỉ có trên phiên đang xác thực.
- HTML khách hàng/public ở `app/templates/customer`; HTML admin ở `app/templates/admin`. Admin dùng shell điều hành riêng. Các macro và fragment chi tiết đơn có thể dùng chung để không nhân đôi nội dung.
- Sơ đồ ERD người dùng gửi được giữ nguyên trong `data/erd.mmd` và bản in HTML. Schema SQLite triển khai bổ sung tài khoản, audit, OTP, kho, hậu mãi và nội dung để phục vụ các luồng trên; không giả định module trả góp đã được bật.

## Kiểm chứng và giới hạn

Chạy `npm run check` và `npm run check:browser` để kiểm chứng nghiệp vụ và giao diện. Các thư mục báo cáo/ảnh kiểm thử là dữ liệu tạm, tách khỏi database demo chính. Bản local chưa chứng minh các yêu cầu production về HTTPS, CDN, chịu tải, SLA, kiểm toán pháp lý, toàn bộ trình duyệt hoặc dịch vụ bên thứ ba. Theo yêu cầu ngày 02/11/2026, giao diện chỉ dùng tiếng Việt; đã gỡ chức năng đổi ngôn ngữ. Module trả góp vẫn ngoài bản triển khai.

## Tổ chức cơ sở dữ liệu

Toàn bộ schema, migration, dữ liệu khởi tạo và hàm kết nối được gom vào `app/db.py`. Ứng dụng dùng một database chính `data/shop.db`; bản sao trong `data/backups` chỉ phục vụ khôi phục, không được dùng song song làm nguồn dữ liệu. Database trong `test-results` thuộc các lần kiểm thử độc lập.

## Bổ sung theo đặc tả frontend

Đã kiểm tra trực tiếp website local và bổ sung: Mega Menu theo nhóm danh mục và liên kết lọc, dropdown tài khoản, gợi ý tìm kiếm có ảnh/giá, carousel có điều khiển, Flash Sale và thời hạn thật trong dữ liệu, danh sách mới/nổi bật/thương hiệu, gallery/zoom, nút số lượng, voucher ở giỏ, địa chỉ nhập tách vùng, modal trả hàng, sidebar admin thu gọn, biểu đồ, bảng tổ hợp biến thể, kéo/thả ảnh, phản hồi đánh giá và bảng voucher. Các dữ liệu mẫu lấy từ `mock-data.json`, được gắn nhãn minh họa rõ ràng.

Bản tin chỉ lưu đăng ký trên local. Không tự bịa đường dẫn mạng xã hội hoặc địa chỉ cửa hàng chưa được cung cấp. Bộ JSON không được dùng như số liệu kinh doanh thật.

## Bổ sung hoàn thiện ngày 31/10/2026

Theo yêu cầu bổ sung toàn quyền của người dùng, bản local đã có các trang giới thiệu/dịch vụ có thể chỉnh sửa, liên hệ công khai và hộp thư admin, danh mục hai cấp, chủ đề/ảnh/nội dung định dạng cho tin tức, chia sẻ bài viết/sản phẩm, cấu hình thông tin cửa hàng, thống kê truy cập và hợp đồng mua hàng điện tử demo. Chi tiết sử dụng và giới hạn tại [feature-completion.md](feature-completion.md).

Schema phiên bản 5 vẫn được quản lý duy nhất tại `app/db.py`, dữ liệu chính ở `data/shop.db`. Không thêm role nhân viên hay tích hợp ngân hàng, SMS, email hoặc chữ ký số bên ngoài.
