# Các chức năng bổ sung của bản local

| Khu vực | Chức năng và đường dẫn |
| --- | --- |
| Giới thiệu | `/about`, `/services`: giới thiệu, sứ mệnh, tầm nhìn, dịch vụ; admin chỉnh nội dung/ảnh/ẩn hiện ở `/admin/settings`. |
| Liên hệ | `/contact`: họ tên, email, điện thoại/địa chỉ tùy chọn và nội dung; có mã tra cứu riêng. `/admin/contact`: lọc trạng thái, tiếp nhận, phản hồi. Khách xem phản hồi qua liên kết riêng sau khi gửi. |
| Danh mục | `/admin/catalog`: tối đa hai cấp; lọc sản phẩm theo nhóm cha hoặc nhóm con. Danh mục đang được sử dụng có thể ẩn, chỉ xóa khi không còn phụ thuộc. |
| Nội dung | `/admin/content`: chủ đề, ảnh, tạo/sửa/ẩn/xóa bài; thanh định dạng Markdown và xem trước an toàn. `/news`: tìm kiếm/lọc trực tiếp, bài liên quan, chia sẻ. Chi tiết sản phẩm cũng có chia sẻ. |
| Tiện ích | `/admin/settings`: hotline, email, địa chỉ, giờ hỗ trợ, mạng xã hội, truy vấn bản đồ. Chỉ hiển thị thông tin đã cấu hình. Bản đồ Google tải khi người dùng bấm xem và cần Internet. |
| Thống kê | `/admin/analytics`: lượt xem, phiên khách, online trong 3 phút và lịch sử 30 ngày. Footer có thể bật/tắt thống kê. Dữ liệu đo trên local, phiên trình duyệt không đồng nghĩa số người thật. |
| Lưu trữ | Sản phẩm có thể lưu trữ/khôi phục tại `/admin/archive`, giữ nguyên lịch sử đơn. |
| Hợp đồng | Tự lập và mở ngay sau checkout, xác nhận trước thanh toán/duyệt đơn; danh sách tại `/account/contracts`, quản trị tại `/admin/contracts`. |

## Hợp đồng điện tử demo

Hợp đồng được lập tự động cùng transaction tạo đơn. Khách bấm “Tiếp tục xem hợp đồng” tại checkout, đọc bản nội dung đóng băng, nhập đúng họ tên, đồng ý điều khoản và xác nhận OTP. Sau đó khách tiếp tục thanh toán online hoặc theo dõi đơn COD chờ admin duyệt. OTP hiển thị trong phiên demo, hết hạn sau 5 phút, giới hạn 5 lần thử và giãn cách cấp mã. Thời hạn giữ hàng online 15 phút từ lúc tạo đơn bao gồm bước xác nhận hợp đồng. Máy chủ chặn thanh toán/thử lại/chuyển COD và duyệt sang chuẩn bị hàng khi hợp đồng chưa xác nhận hoặc không toàn vẹn. Đơn cũ chưa có hợp đồng có thể lập từ chi tiết đơn. Admin xem và hủy hiệu lực có lý do; không xác nhận thay khách. Hủy đơn hoặc hoàn tiền làm hợp đồng mất hiệu lực, vẫn giữ bản nội dung và lịch sử.

Nội dung người mua, người bán, sản phẩm và số tiền được chụp tại lúc lập; thay đổi sản phẩm sau đó không sửa bản hợp đồng. SHA-256 phục vụ đối chiếu nội dung, không phải chữ ký số được chứng thực. Chủ sở hữu và admin có thể tải HTML hoặc mở bản in rồi dùng Save as PDF của trình duyệt. Không gửi OTP qua SMS/email thật và không tích hợp nhà cung cấp ký số. Đây là hợp đồng mua hàng demo; không phải module tài chính trả góp trong ERD gốc.

## Vận hành

Chạy `npm run dev`, mở http://127.0.0.1:8000. Admin: `admin@neushop.local` / `Admin@12345`. Khách demo: `demo.lan@example.test` / `Demo@12345`.

Vào **Thông tin cửa hàng** để nhập thông tin liên hệ thật; mặc định các trường chưa được cung cấp để trống. Dữ liệu thử trong báo cáo/ảnh kiểm thử chỉ tồn tại trên database riêng. Không nhập thông tin doanh nghiệp hoặc hotline giả vào bản chính.

Khởi động ứng dụng tự nâng cấp schema, giữ dữ liệu hiện có và lưu bản sao trước v5 tại `data/backups/before-portal-v5.db` nếu cần nâng cấp. Toàn bộ schema/migration nằm trong một file `app/db.py`; các bản sao và database kiểm thử không phải nguồn dữ liệu runtime.
