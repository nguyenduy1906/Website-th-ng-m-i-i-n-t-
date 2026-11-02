# Bảo mật

Đây là dự án học tập chạy local, không phải hệ thống bán hàng production. Tài khoản demo và OTP mô phỏng được công bố để kiểm thử; không sử dụng thông tin cá nhân hoặc mật khẩu thật.

Không commit `.env`, API key Gemini, khóa ký phiên, database, ảnh khách tải lên hoặc bản sao lưu. Nếu khóa đã bị công khai, thu hồi và tạo khóa mới; chỉ xóa khỏi bản hiện tại không xóa được lịch sử Git.

Không đăng chi tiết lỗ hổng có chứa dữ liệu nhạy cảm vào issue công khai. Liên hệ riêng chủ repository qua thông tin họ công bố. Dự án chưa cung cấp địa chỉ nhận báo cáo chuyên biệt.

Phiên trình duyệt được lưu trong sessionStorage của từng tab và xác minh chữ ký phía server, không dùng cookie đăng nhập chung giữa tab. Không chia sẻ giá trị phiên, không đưa vào URL. JavaScript cần được bật để đăng nhập theo tab; trang công khai vẫn xem được khi tắt JavaScript. Kiểm tra tab trùng dùng BroadcastChannel, nên cần trình duyệt hiện đại.
