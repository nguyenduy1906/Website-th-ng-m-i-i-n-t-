# Dọn thành phần giao diện không dùng — 03/11/2026

Đối chiếu tham chiếu template trong Python/Jinja2, tên lớp trong HTML/JavaScript, nội dung dữ liệu SQLite và các nguồn nhập liên quan trước khi gỡ.

Đã gỡ:

- Template admin/login.html: không còn route hoặc include gọi; đăng nhập đã dùng customer/auth.html.
- app/static/images/favicon.svg: không còn tham chiếu; favicon hiện dùng logo PNG.
- CSS riêng của trang đăng nhập admin cũ, biểu tượng logo chữ cũ, banner demo-data-notice, sidebar/bố cục admin cũ, danh mục và thẻ tài khoản phiên bản cũ, cùng các selector không còn dùng khác. Tổng cộng hơn 80 selector trên năm stylesheet.
- Token hero-ring chỉ phục vụ hình trang trí đã bỏ.
- Truy vấn demo_loaded và biến context tương ứng: không còn template sử dụng.

Giữ ảnh dự phòng, ảnh được công cụ nhập dữ liệu tham chiếu, lớp sinh động như auth-login/auth-register và trạng thái do JavaScript tạo. Không dọn theo kết quả coverage của một trang riêng lẻ. Không thay dữ liệu cửa hàng hoặc lịch sử hợp đồng/giao dịch.

Đã kiểm tra tham chiếu sau khi dọn: không thiếu template được gọi và không còn template không có nơi gọi trong mã ứng dụng. Bộ 43 kiểm thử nghiệp vụ qua; kiểm tra khách hàng 32 lượt trang/kích thước màn hình qua. Báo cáo JSON chi tiết CSS gỡ nằm tại test-results/ui-cleanup.json, không đưa vào bản xuất GitHub.

Kiểm tra quản trị: 66 lượt trang/kích thước màn hình qua, bộ lọc và cặp ô nhập căn thẳng hàng, không tràn ngang hoặc lỗi JavaScript.

