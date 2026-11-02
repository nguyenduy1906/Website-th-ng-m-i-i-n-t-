# Tài liệu nghiệp vụ NEU SHOP

Bộ UI UX Pro Max được tích hợp và áp dụng thiết kế lại theo [ui-ux-pro-max.md](ui-ux-pro-max.md). Quy chuẩn giao diện cuối cùng vẫn nằm tại `DESIGN.md`.

Danh mục thực tế bổ sung và cách nhập khoảng 1.000 bản ghi được ghi tại [catalog-import.md](catalog-import.md); dữ liệu cùng nguồn tham chiếu nằm trong [catalog-real.json](catalog-real.json).

[nghiep-vu-goc.txt](nghiep-vu-goc.txt) là bản sao nguyên văn tài liệu **Phân tích nghiệp vụ website thương mại điện tử** do người dùng cung cấp. Giữ nguyên tài liệu này làm nguồn tham chiếu nghiệp vụ.

## Phạm vi triển khai đã chốt

Theo xác nhận của người dùng ngày 27/10/2026:

- Công nghệ: Python, FastAPI và HTML/Jinja2; bản demo full stack chạy trên local.
- Chỉ triển khai hai nhóm giao diện: **quản trị viên (admin)** và **khách hàng**.
- Giao diện khách hàng dùng chung phần mua sắm công khai (public). Khi đăng nhập, khách có thêm các trang thông tin cá nhân, tài khoản, đơn hàng và những trang riêng phù hợp với nghiệp vụ được triển khai.
- Không xây dựng giao diện riêng cho nhân viên CSKH, nhân viên kho, nhân viên sản phẩm hoặc kế toán. Các chức năng vận hành được triển khai sẽ tập trung trong giao diện admin.
- Khách vãng lai là trạng thái chưa đăng nhập của khu vực public, không cần một giao diện quản trị hoặc role lưu riêng.

Tài liệu gốc mô tả nghiệp vụ rộng hơn phạm vi giao diện đã chốt. Danh sách tác nhân trong tài liệu không đồng nghĩa với yêu cầu tạo thêm role hoặc giao diện riêng. Ghi chú này xác định phạm vi triển khai, không khẳng định mọi chức năng trong tài liệu gốc đã được hoàn thành.

Đối chiếu từng FR với phần đã triển khai, các quy tắc demo và giới hạn tích hợp được ghi trong [implementation.md](implementation.md). HTML được tách thành `app/templates/customer/` và `app/templates/admin/`.

Đặc tả frontend bổ sung được lưu nguyên văn trong [frontend-brief.txt](frontend-brief.txt); dữ liệu minh họa có liên kết trong [mock-data.json](mock-data.json).

## Bổ sung hoàn thiện ngày 31/10/2026

Theo yêu cầu bổ sung toàn quyền của người dùng, bản local đã có các trang giới thiệu/dịch vụ có thể chỉnh sửa, liên hệ công khai và hộp thư admin, danh mục hai cấp, chủ đề/ảnh/nội dung định dạng cho tin tức, chia sẻ bài viết/sản phẩm, cấu hình thông tin cửa hàng, thống kê truy cập và hợp đồng mua hàng điện tử demo. Chi tiết sử dụng và giới hạn tại [feature-completion.md](feature-completion.md).

Schema phiên bản 5 vẫn được quản lý duy nhất tại `app/db.py`, dữ liệu chính ở `data/shop.db`. Không thêm role nhân viên hay tích hợp ngân hàng, SMS, email hoặc chữ ký số bên ngoài.

## Điều chỉnh phạm vi ngày 02/11/2026

Theo yêu cầu người dùng, gỡ chức năng so sánh sản phẩm (FR08), các đường dẫn GET/POST `/compare` và chức năng đổi ngôn ngữ ở cả khách hàng lẫn admin. Giao diện cố định tiếng Việt. Tài liệu nghiệp vụ gốc giữ nguyên làm tham chiếu; điều chỉnh này là phạm vi triển khai hiện tại.

## Chatbot tư vấn local

Nút Tư vấn NEU SHOP xuất hiện trong shell khách hàng. API GET `/api/chatbot?q=...` tra cứu tên, thông số, giá, tồn kho, bảo hành của sản phẩm công khai; hỗ trợ ngân sách dạng “20 triệu”. Trả lời các hướng dẫn mua hàng và chính sách demo. Đây là chatbot truy xuất theo từ khóa, chưa dùng mô hình ngôn ngữ; chưa ghi nhớ hội thoại hoặc hiểu mọi cách diễn đạt. Không đọc tài khoản/đơn hàng riêng tư.

Chatbot đã bổ sung provider Ollama local mặc định và Gemini cấu hình sau bằng `.env`. Chi tiết thiết lập, dữ liệu gửi và giới hạn tại `docs/chatbot-ai.md`. Khi provider không sẵn sàng, UI ghi rõ đang tra cứu local. Khả năng hiểu ngôn ngữ tự nhiên yêu cầu runtime/model hoặc API key thực tế.
