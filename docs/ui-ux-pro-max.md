# UI UX Pro Max — tích hợp cho NEU SHOP

Nguồn: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Ngày tải: 29/10/2026. Commit: `28b3b8dee8c976df4fa3e94aed4e092ad43fcb03`. Bản repo gốc nằm tại `tools/ui-ux-pro-max`, bản skill dùng trong workspace tại `.agents/skills/ui-ux-pro-max`. Giữ nguyên giấy phép MIT trong cả hai nơi. Cài bằng công cụ `skill-installer`, không cài npm package global.

## Cách áp dụng

Đã đọc `SKILL.md`, các phần Web trong `references/quick-reference.md` và phạm vi của `pro-rules.md`. Công cụ tìm kiếm chạy bằng Python, dùng dữ liệu cục bộ. Stack thực tế vẫn là FastAPI, Jinja2, HTML, CSS và JavaScript thuần; không chuyển sang React/Tailwind.

Các truy vấn đã đối chiếu:

- `electronics retail ecommerce --design-system --density 6`: nhận Feature-Rich Showcase / Vibrant & Block-based; dùng ý tưởng nhóm thông tin rõ và ảnh sản phẩm trung tâm. Không tự đổi màu xanh đã chốt sang bảng màu xanh lá/cam được đề xuất.
- `general ecommerce clean --design-system --density 6`: trả Glassmorphism và khung landing Hero + Features; đây không phải khớp đầy đủ với danh mục bán lẻ hiện tại. Không dùng phần gợi ý này làm hệ thiết kế của dự án.
- `ecommerce storefront --domain product`: xác nhận nhóm E-commerce và cách tổ chức Feature-Rich Showcase. Áp dụng vào nhóm hàng thật, không thêm social proof, cam kết hoặc khuyến mãi không có dữ liệu.
- `minimalism swiss --domain style`: một kết quả đã xác nhận, dùng nguyên tắc phân cấp chữ, lưới, khoảng cách và ít hiệu ứng để tinh chỉnh các trang tác vụ.
- `data dense dashboard --domain style`: khớp chính xác Data-Dense Dashboard; áp dụng bảng số liệu, KPI, bộ lọc và điều hướng trong admin. Phần hero marketing của đề xuất hệ thống admin bị loại vì không phù hợp tác vụ.
- `live search filtering feedback --domain ux`: xác nhận autocomplete, empty-state hữu ích và thông báo kết quả có ngữ cảnh, giữ focus.

Kết quả tìm kiếm là tham khảo thiết kế. `DESIGN.md` là quy chuẩn cuối cùng của dự án, không tạo thêm một `MASTER.md` có thể xung đột. Quy tắc nghiệp vụ trong `docs/nghiep-vu-goc.txt` và phạm vi hai giao diện trong `docs/README.md` tiếp tục áp dụng.

## Hướng thiết kế lại

- Giao diện mua sắm sáng, header navy, tìm kiếm trắng, ảnh sản phẩm thật và bộ chữ Be Vietnam Pro cục bộ.
- Trang chủ tổ chức theo danh mục, ảnh spotlight và các dải sản phẩm. Điều khiển trước/sau bổ sung cho thao tác vuốt/cuộn, không tự xoay banner.
- Danh mục giữ bộ lọc tức thời; thẻ đồng đều, giá/nút thẳng hàng và phân trang gọn.
- Trang chi tiết ưu tiên gallery, cấu hình và khu mua hàng; giỏ/checkout/tài khoản dùng cùng thành phần, khoảng cách và phân cấp.
- Admin có sidebar navy chia nhóm, workspace sáng, KPI dữ liệu thật, biểu đồ và bảng rõ ràng; bộ lọc GET tự cập nhật, thao tác ghi dữ liệu vẫn có nút thực hiện.
- Bảo toàn dữ liệu SQLite, 356 sản phẩm thật, nguồn ảnh và nghiệp vụ. Không tự tạo thêm role hay giao dịch thực tế.
- Theo chỉnh sửa trực tiếp của người dùng, toàn bộ mức bo góc giao diện thống nhất 5px qua token `--radius`; các cạnh vốn vuông vẫn là 0. Quy tắc này áp dụng cả khách hàng và admin, ưu tiên hơn gợi ý radius của skill.

Font tải từ Google Fonts và lưu trong `app/static/fonts/`, gồm Latin và tiếng Việt ở bốn độ đậm 400/500/600/700. Giấy phép SIL Open Font License được lưu cùng font. Chạy web không cần truy cập CDN font.
