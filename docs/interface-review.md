# Rà soát giao diện NEU SHOP

Ngày 02/11/2026. Dùng FastAPI/Jinja2 hiện tại, không cài thêm thư viện.

- 40 trang × 3 chiều rộng 375, 768, 1280px = 120 lượt tải trang bằng Chrome.
- Không ghi nhận lỗi JavaScript hoặc tràn ngang toàn trang trong phạm vi này.
- Công khai: trang chủ, danh mục, sản phẩm, danh sách/chi tiết bài viết, giới thiệu, liên hệ, ưu đãi, chính sách, đăng nhập, đăng ký, khôi phục mật khẩu, giỏ hàng.
- Tài khoản: tổng quan, hồ sơ, địa chỉ, bảo mật, đơn hàng, hợp đồng, thông báo, hỗ trợ; chi tiết đơn hàng và hợp đồng hiện có.
- Quản trị: tổng quan, sản phẩm, thêm/sửa sản phẩm, đơn hàng, danh mục, tồn kho, đổi trả, báo cáo, người dùng, ưu đãi, nội dung, hợp đồng, liên hệ, thiết lập; chi tiết đơn hàng và hợp đồng.
- Đã xem ảnh hợp đồng trên máy tính và điện thoại; các vùng dài dùng bảng cuộn trong khung và phần mở rộng cho mã đối chiếu.
- Bộ kiểm thử nghiệp vụ: 41 kiểm thử qua trong lần chạy kiểm tra của đợt chỉnh sửa.

Ảnh và báo cáo JSON được lưu cục bộ tại test-results/interface-review, được loại khỏi bản đưa lên GitHub. Kiểm tra này không khẳng định mọi tổ hợp dữ liệu và mọi thao tác đều đã thử thủ công.

Đợt chỉnh câu chữ cập nhật 370 bản ghi có thể chỉnh sửa, có bản sao lưu SQLite trước khi cập nhật. Không đổi email, mật khẩu, hợp đồng đã xác nhận, mã băm, lịch sử OTP hoặc giao dịch. Bản hợp đồng cũ có thể còn tên/câu chữ ban đầu vì đây là nội dung đã xác nhận.
