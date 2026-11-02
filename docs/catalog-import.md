# Danh mục sản phẩm thực tế cho demo local

Đã nhập 356 sản phẩm từ dữ liệu danh mục công khai của CellphoneS: 128 laptop, 89 điện thoại, 40 sản phẩm âm thanh và 99 phụ kiện, thuộc 44 thương hiệu. Đợt bổ sung âm thanh/phụ kiện thêm 139 sản phẩm; nhóm phụ kiện gồm chuột, bàn phím, sạc, cáp, pin dự phòng và hub chuyển đổi. Không nhập khách hàng hoặc đánh giá của website nguồn.

Mỗi sản phẩm thêm 5 bản ghi liên kết: `products`, `variants`, `product_images`, `inventory_movements`, `product_sources`. Tổng cộng 1.780 bản ghi, chưa tính thương hiệu mới. Đây là số bản ghi liên quan, không phải 1.780 mẫu sản phẩm khác nhau.

`catalog-real.json` lưu tên, cấu hình có trong dữ liệu nguồn, giá tham khảo, URL trang sản phẩm, URL danh mục, URL ảnh, thời điểm thu thập và SHA-256 của ảnh. Ảnh tải về `app/static/images/catalog/`, giữ định dạng PNG/JPEG/WebP của nguồn; website chạy bằng ảnh local. Quyền đối với ảnh vẫn thuộc chủ sở hữu nguồn, việc nhập phục vụ bản demo local theo yêu cầu của người dùng.

Giá không đồng bộ trực tiếp và có thể thay đổi tại website nguồn. Tồn đầu 20 đơn vị mỗi sản phẩm là dữ liệu mô phỏng, không thể hiện tồn kho CellphoneS. Nhãn màu “Theo ảnh sản phẩm” tránh tự bịa màu hoặc tạo phiên bản chưa xác minh. Không nhập các cam kết giao hàng, khuyến mãi thành viên hoặc đánh giá của CellphoneS.

Tám sản phẩm NEU hư cấu ban đầu được ẩn khỏi danh mục (không xóa), để giữ liên kết đơn hàng/đánh giá cũ. Tài khoản và các giao dịch hiện có được bảo toàn. Bản sao trước khi nhập nằm ở `data/backups/before-real-catalog.db`; cơ sở dữ liệu hoạt động vẫn là `data/shop.db`, toàn bộ định nghĩa bảng nằm trong `app/db.py`.

## Lệnh

- `npm run catalog:collect`: đọc danh mục công khai, lưu cache HTML và ứng viên trong `data/`.
- `npm run catalog:images`: tải, kiểm tra chữ ký ảnh, tạo `docs/catalog-real.json`.
- `npm run catalog:import`: kiểm tra hash ảnh, tạo bản sao, nhập theo transaction; bỏ qua mã nguồn đã nhập để không trùng hoặc ghi đè dữ liệu đã sửa.
- `npm run catalog:check`: với server local đang chạy, kiểm tra giải mã toàn bộ ảnh và trang danh sách/chi tiết ở 320/768/1440px.

Các trang tổng hợp âm thanh/phụ kiện đã chuyển công nghệ được thay bằng danh mục con công khai tương ứng. Trang `laptop/macbook.html` trả 404 được bỏ qua; sản phẩm Apple vẫn có từ danh mục laptop chung. Thương hiệu phụ kiện lấy từ trường `phone_accessory_brands` của nguồn. Danh mục cuối cùng chỉ bao gồm bản ghi có tên, thương hiệu, giá và ảnh lấy được từ nguồn.
