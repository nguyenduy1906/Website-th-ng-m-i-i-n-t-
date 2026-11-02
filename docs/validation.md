# Kiểm tra bản làm lại

## Thiết kế lại ngày 29/10/2026 — UI UX Pro Max

- Đã cài skill và giữ repo gốc/giấy phép, đối chiếu hướng dẫn retail, Data-Dense Dashboard và Web UX. Font Be Vietnam Pro gồm 8 WOFF2 (4 độ đậm × Latin/tiếng Việt) lưu local; không gọi font CDN khi dùng web.
- `npm run check`: **30 bài backend đạt**, bổ sung kiểm tra cảnh báo tồn thấp loại sản phẩm đã ẩn và số KPI khớp danh sách kho.
- `npm run check:browser`: **176 trường hợp trang/kích thước đạt**, cùng luồng OTP/mua hàng/xử lý đơn/đánh giá/trả hàng/no-JavaScript/reduced-motion trên template mới.
- `npm run check:layout:customer`: **32 phép kiểm tra đạt**; `npm run check:layout:admin`: **27 phép kiểm tra đạt**. Đã xem ảnh thực tế trang chủ, danh mục, chi tiết, dashboard, đăng nhập và form sửa sản phẩm.
- `npm run check:live-filters`: **13 hành vi đạt** sau khi thiết kế lại; tìm/lọc/sắp xếp giữ focus, cập nhật phiên bản/phí giao/voucher đúng và không tự tạo đơn.
- Theo yêu cầu bổ sung, toàn bộ 134 khai báo bo góc trong 4 stylesheet được chuẩn hóa về token `--radius: 5px` (giữ cạnh 0); có kiểm tra bổ sung các giá trị bo góc thực tế bằng trình duyệt.
- `npm run check:redesign`: **17 trang/trạng thái/kích thước đạt**, gồm 375/1440px, dialog lọc mobile và CSS zoom 200%; 12 điểm focus bàn phím, 2 kiểm tra nút cuộn dải sản phẩm. Không có tràn ngang, lỗi tương phản chữ tính được, điều khiển dưới 44px, mức bo góc khác 0/5px hoặc lỗi JavaScript trong các trang được đo. Các phép đo này không thay thế chứng nhận WCAG đầy đủ.

## Bổ sung ngày 28/10/2026 — dữ liệu và bố cục

- Danh mục hoạt động có 356 sản phẩm thật: 128 laptop, 89 điện thoại, 40 âm thanh, 99 phụ kiện; toàn bộ 356 ảnh local giải mã được trong Chrome. SQLite `integrity_check` trả `ok`, `foreign_key_check` không có lỗi.
- `npm run check`: 29 bài backend đạt. `npm run check:browser`: 176 trường hợp trang/kích thước và các luồng tương tác đạt sau khi chuyển lọc/sắp xếp/phiên bản/preview checkout sang tự cập nhật.
- `npm run check:layout:customer`: 32 trang/kích thước đạt ở 320, 375, 768, 1024, 1280, 1440, 1920, 2560px; kiểm tra chiều cao thẻ, vị trí giá/nút, hàng đầy của trang thường và tràn ngang.
- `npm run check:layout:admin`: 27 trang/kích thước đạt trên 9 trang admin ở 320, 768, 1280px; có kiểm tra căn hàng điều khiển và số liệu.
- `npm run check:live-filters`: 13 hành vi đạt trên bản sao SQLite riêng: giữ focus, chống kết quả cũ ghi đè, giữ bộ lọc/sắp xếp, giỏ sau khi thay kết quả, dialog mobile, preview giá và admin search. Xác nhận không tạo đơn khi tìm/lọc/preview.
- Lượt `npm run design:check` mới có 0 FAIL, 0 WARN và 44 REFLEX từ checker về link tên sản phẩm xuống hai dòng. Lệnh trả mã 1 vì các gợi ý REFLEX này; đây là cách hiển thị chủ ý của thẻ theo DESIGN (tên thật dài, tối đa hai dòng), đã đối chiếu bằng kiểm tra hình học/thị giác; không sửa checker để bỏ cảnh báo. Kết quả cũ bên dưới là của lượt kiểm tra trước khi thay dữ liệu thật.

Ngày kiểm tra: 27/10/2026. Môi trường: Windows, Python 3.14, Chrome headless.

- `npm run check`: **29 kiểm thử tích hợp đạt**. Bao gồm OTP và giới hạn thử, khôi phục mật khẩu, phân quyền/CSRF, hồ sơ/địa chỉ, giỏ theo tài khoản, biến thể, voucher, chống đơn trùng, thanh toán thất bại/thử lại/thành công, hủy/hoàn tồn, hết hạn giữ hàng, trả hàng/hoàn tiền/điểm, đánh giá đã mua, hỏi đáp/chat/thông báo, ảnh tải lên, quản trị và đối soát.
- Có kiểm tra **hai khách cùng mua sản phẩm chỉ còn một đơn vị**: một đơn được tạo, đơn còn lại bị từ chối, tồn không âm.
- Có kiểm tra **migration database cũ và chạy lại migration**: giữ mật khẩu, tên sản phẩm tại thời điểm mua, đơn và tồn; không nhân bản biến thể. Kiểm tra tồn tại bản sao trước nâng cấp.
- `npm run check:browser`: **176 trường hợp trang/kích thước đạt**, tương ứng 44 trang/trạng thái tại 320, 375, 768, 1280px. Kiểm tra tràn ngang toàn trang, ảnh, nhãn form và HTML tương tác lồng sai; lưu ảnh desktop/mobile.
- Các luồng trực tiếp trên Chrome: đăng ký/OTP, đặt hàng, lưu địa chỉ, so sánh, admin xử lý đơn, đánh giá người mua, gửi yêu cầu trả hàng; kiểm tra dialog/Escape/trả focus, mua sắm cơ bản khi tắt JavaScript và reduced motion.
- `npm run design:check`: **0 FAIL, 0 WARN, không còn REFLEX mở** trên CSS chung/khách hàng/admin và render trang chủ/đăng nhập admin. Giữ các ngoại lệ đã ghi cho màu trắng, palette và mật độ thành phần theo `DESIGN.md`.
- Ảnh kiểm tra đã được xem cho trang chủ, thanh toán mobile và dashboard admin desktop/mobile.

Backend và browser dùng SQLite thử nghiệm riêng. Dữ liệu runtime chính ở `data/shop.db`; bản sao trước khi nâng cấp ở `data/backups/before-v2.db`. Bản chính được khởi động lại tại `http://127.0.0.1:8000` và endpoint health xác nhận phiên bản 2.

Kết quả này không thay thế kiểm tra dịch vụ thanh toán/vận chuyển thực tế, kiểm thử tải production hoặc tương thích đầy đủ Firefox/Safari/Edge. Những giới hạn của bản local được nêu trong `implementation.md` và README ở gốc dự án.

## Kiểm tra tương tác frontend bổ sung

Đã mở trực tiếp trang chủ, danh sách, chi tiết và admin trên Chrome trước/sau sửa. Kiểm tra thêm carousel, tìm kiếm Mega Menu, đổi VI/EN, quick add và toast/badge, gallery/zoom/Escape, tăng giảm số lượng, thu gọn sidebar, biểu đồ có dữ liệu, sinh 4 tổ hợp biến thể và modal trả hàng. Kiểm thử browser dùng bộ JSON nhập vào SQLite riêng; kiểm thử backend xác nhận JSON không bị nhập trùng, gallery/phản hồi đánh giá, lưu bản tin, API giỏ, bảng biến thể và hoàn giá khi Flash Sale hết hạn.

## Hoàn thiện nội dung và hợp đồng — 31/10/2026

- `npm run check`: 37 kiểm thử tích hợp đạt, gồm quyền riêng tư, OTP hợp đồng, nội dung đóng băng, kiểm tra sửa dữ liệu, hủy hiệu lực, liên hệ/phản hồi, XSS nội dung, danh mục hai cấp, lưu trữ và thống kê.
- `npm run check:browser`: 176 trường hợp trang/kích thước đạt; báo cáo `test-results/browser-7qdfDt/report.json`.
- `npm run check:portal`: 11 nhóm kiểm tra luồng đạt, 64 trường hợp bố cục mới ở 320/375/768/1440px, không tràn ngang, mọi góc bo khác 0 là 5px, không lỗi JavaScript; báo cáo `test-results/portal-browser-vnO3AP/report.json`.
- Đã xem ảnh hợp đồng mobile và cấu hình admin desktop. Kiểm tra tải HTML, bản in, liên hệ/phản hồi, bài có ảnh/định dạng, tìm tin tức trực tiếp và hủy hiệu lực hợp đồng. Các kiểm thử dùng SQLite riêng, không đưa thông tin liên hệ minh họa vào database chính.

Kết quả mới thay thế các số lượng kiểm thử cũ cho phiên bản hiện tại. Chưa kiểm chứng tích hợp dịch vụ thật, chữ ký số pháp lý, khả năng chịu tải hoặc tương thích đầy đủ các trình duyệt khác.

Đã nâng cấp database chính lên schema 5: giữ nguyên 364 sản phẩm (gồm dữ liệu cũ đã ẩn), 4 tài khoản, 7 đơn; integrity_check=ok, foreign_key_check không lỗi. Các trang mới trả HTTP 200 trên cổng 8000.
