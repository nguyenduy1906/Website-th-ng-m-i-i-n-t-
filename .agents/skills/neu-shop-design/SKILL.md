---
name: neu-shop-design
description: Thiết kế, xây dựng hoặc chỉnh sửa giao diện website bán đồ công nghệ NEU SHOP, thống nhất màu, chữ, bố cục, thành phần và responsive. Áp dụng cho trang khách hàng và quản trị NEU SHOP; không áp dụng cho dự án khác hoặc thay đổi chỉ ở backend.
---

# NEU SHOP Design

## Nguồn quy chuẩn

Đọc [DESIGN.md](../../../DESIGN.md) ở gốc dự án trước khi làm UI. Đây là nguồn duy nhất cho token và quy tắc thị giác. Đọc AGENTS.md áp dụng tại nơi sửa code. Không sao chép bảng token vào skill.

## Cách thực hiện

1. Xác định trang, tác vụ người dùng và phạm vi được yêu cầu. Không tự thêm chức năng ngoài nhiệm vụ.
2. Đọc mã nguồn, kiểm tra công nghệ, theme và component hiện có. Khi chưa có code, xác định công nghệ trong nhiệm vụ xây dựng website; skill này không áp đặt framework hoặc tự cài dependency.
3. Chọn bố cục trang tương ứng trong DESIGN.md. Giữ cấu trúc cửa hàng công nghệ dễ mua sắm và nhận diện NEU SHOP; không ép các trang thành Bento.
4. Ánh xạ token vào theme chung, tái sử dụng shell và component. Các route dùng cùng header/footer, thẻ sản phẩm, cách hiển thị giá và trạng thái tương tác.
5. Ưu tiên dữ liệu thật. Dữ liệu mẫu chỉ dùng khi nhiệm vụ cho phép hoặc cần minh họa giai đoạn dựng UI, tách rõ khỏi dữ liệu vận hành. Không bịa thông tin cửa hàng, đánh giá hoặc cam kết.
6. Kiểm tra theo checklist DESIGN.md, chạy script npm hiện có phù hợp. Báo cáo trang/thành phần thay đổi, kiểm tra đã chạy và phần chưa thể kiểm tra.

## Quyết định mới

Tự quyết chi tiết nhỏ bằng quy chuẩn và mẫu hiện có. Nếu người dùng yêu cầu đổi nhận diện hoặc quy tắc dùng chung, cập nhật DESIGN.md và triển khai liên quan. Chỉ hỏi khi thông tin thiếu ảnh hưởng đáng kể tới thương hiệu, nội dung thật hoặc phạm vi chức năng; tiếp tục phần độc lập có thể thực hiện.
