# NEU SHOP — Quy chuẩn giao diện

## Phạm vi

Website bán đồ công nghệ, phong cách cửa hàng hiện đại, tiếng Việt, tiền tệ VND. Theo yêu cầu ngày 02/11/2026, giao diện cố định tiếng Việt; không có nút đổi ngôn ngữ hoặc chức năng so sánh sản phẩm trên header, menu hay trang chi tiết. Áp dụng cho giao diện khách hàng và quản trị khi được yêu cầu; tài liệu không tự mở rộng phạm vi chức năng.

Đây là nguồn quy chuẩn thiết kế duy nhất. Skill `.agents/skills/neu-shop-design/SKILL.md` hướng dẫn cách áp dụng; không duy trì bảng token thứ hai trong skill. Không phụ thuộc framework.

## Định hướng

Tham khảo cấu trúc mua sắm của [FPT Shop](https://fptshop.com.vn/) và [CellphoneS](https://cellphones.com.vn/): tìm kiếm nổi bật, danh mục, banner, nhóm sản phẩm, bộ lọc và đường mua hàng rõ ràng. Dùng nhận diện NEU SHOP riêng; không sao chép logo, nội dung hoặc tài sản thương hiệu tham khảo.

Ưu tiên sản phẩm, thông số và giá; nền trung tính, ít hiệu ứng. Bento chỉ phù hợp với cụm banner, không ép mọi trang thành hero lớn hoặc thẻ bất đối xứng. Lưới sản phẩm dùng thẻ đều nhau để dễ so sánh.

## Tích hợp Hallmark

- Repo gốc nằm trong `tools/hallmark`, skill chạy trong `.agents/skills/hallmark`. Bản tải ban đầu: commit `7ec868225c6caa040558c321ee0fefa0e73f83a8`, Hallmark 2.0.0. Giữ nguyên giấy phép MIT và các thông báo bản quyền trong bản upstream.
- Bản skill cục bộ lược bỏ hai trường frontmatter `argument-hint` và `version`, đổi placeholder `<path>` trong ví dụ lệnh redesign thành `path` để tương thích validator; các quy tắc thiết kế giữ nguyên. Repo trong `tools/hallmark` không chỉnh sửa. Khi cập nhật skill, kiểm tra lại tính tương thích này.
- Dùng Hallmark cho thiết kế mới, hoặc redesign/audit khi người dùng yêu cầu; đọc hướng dẫn và chỉ nạp tài liệu liên quan. Sửa giao diện thông thường theo quy chuẩn dự án.
- Đây là hệ thiết kế đã chốt: màu, font, container, bố cục thương mại điện tử trong tài liệu này ưu tiên hơn theme được Hallmark đề xuất. Không đổi ngẫu nhiên theme giữa các trang.
- Tiếp nhận các kiểm tra về phân cấp, tương phản, focus, responsive, reduced motion, dữ liệu thật và trạng thái tương tác. Không ép cửa hàng theo số section, số từ, hero hoặc tỷ lệ ảnh dành cho landing page; giữ tên sản phẩm, thông số và thông tin mua hàng cần thiết.
- Tuân thủ AGENTS.md: không đặt comment ở hai dòng đầu source file. Nếu dùng stamp Hallmark, đặt sau các khai báo đầu file; báo cáo ngoại lệ nếu công cụ lint đòi stamp đầu file, không sửa quy tắc dự án chỉ để làm lint xanh.
- Dùng công cụ kiểm tra upstream khi phù hợp với framework. Render cần trình duyệt và dependency phù hợp; nếu thiếu phải báo rõ, không coi static check là kiểm tra hình ảnh. Không cài global package, hook hoặc dịch vụ tạo ảnh chỉ để hoàn tất tích hợp skill.

## Áp dụng UI UX Pro Max

- Theo yêu cầu người dùng ngày 29/10/2026, skill nằm tại `.agents/skills/ui-ux-pro-max`, repo gốc tại `tools/ui-ux-pro-max`, commit `28b3b8dee8c976df4fa3e94aed4e092ad43fcb03`. Giữ bản upstream và giấy phép MIT. Chi tiết lựa chọn/truy vấn trong `docs/ui-ux-pro-max.md`.
- Lấy hướng dẫn về phân cấp, bố cục retail, Data-Dense Dashboard, phản hồi tương tác, bàn phím và responsive để thiết kế lại. Đây vẫn là giao diện sáng với header/sidebar navy; không thêm dark mode toàn trang hoặc áp dụng bảng màu/style được sinh tự động khi không phù hợp.
- Header mua sắm dùng nền navy và ô tìm kiếm trắng, nav phụ sáng; banner dùng ảnh sản phẩm thật và thông tin từ dữ liệu hiện tại. Sidebar admin navy chia nhóm điều hành; workspace, bảng và form dùng nền sáng.
- Thẻ sản phẩm có vùng ảnh/tên/thông số/giá/nút thống nhất; gallery và khu mua tách rõ, tóm tắt đơn có thứ bậc. Không bịa số lượt mua, xu hướng, cam kết giao hàng hoặc giảm giá.
- Dải sản phẩm có nút trước/sau, focus và bàn phím, vẫn hỗ trợ cuộn/vuốt. Chuyển động 150–200ms, dùng trạng thái tĩnh khi reduced-motion; không thay đổi kích thước/vị trí điều khiển khi nhấn.
- Các nhãn gợi ý và bố cục được tùy biến cho tiếng Việt, FastAPI/Jinja2 và CSS thuần. Quy tắc trong file này ưu tiên hơn gợi ý thêm framework hoặc giới hạn chiều ngang của skill.

## Token màu triển khai

Khai báo biến ngữ nghĩa trong theme/stylesheet chung; component dùng token, không rải mã màu trực tiếp.

| Token | Giá trị | Công dụng |
| --- | --- | --- |
| brand | #0EA5E9 | Nhận diện, điểm nhấn trang trí |
| primary | #0369A1 | Nút chính với chữ trắng, liên kết |
| primary-hover | #075985 | Hover/active hành động chính |
| primary-soft | #E0F2FE | Nền chọn, nhãn thông tin |
| page | #F5F7FA | Nền trang |
| surface | #FFFFFF | Thẻ, form, menu |
| surface-muted | #F1F5F9 | Vùng phụ, khung ảnh/loading |
| text | #0F172A | Nội dung chính |
| text-muted | #475569 | Mô tả, metadata |
| border | #E2E8F0 | Viền trang trí, phân chia vùng |
| control-border | #64748B | Viền input và điều khiển |
| price | #B91C1C | Giá bán, giảm giá có dữ liệu |
| success | #15803D | Thành công, còn hàng |
| warning | #92400E | Cảnh báo |
| danger | #B91C1C | Lỗi, hành động xóa |
| focus | #0369A1 | Vòng focus 2px, offset 2px |
| shell (navy tương thích) | #E0F2FE | Nền xanh nước nhạt của header, footer, rail quản trị và vùng tài khoản |
| on-shell (on-navy tương thích) | #0F172A | Chữ chính trên nền xanh nước nhạt |
| shell-muted (navy-muted tương thích) | #475569 | Chữ phụ trên nền xanh nước nhạt |
| shell-border | #BAE6FD | Đường phân cách vùng nền xanh nước nhạt |
| surface-raised | #FFFFFF | Bề mặt nổi, panel và vùng mua |

Mặc định giao diện sáng. Không dùng brand sáng làm nền chữ trắng cỡ nhỏ. Kiểm tra tương phản thực tế: chữ thường 4.5:1, chữ lớn và điều khiển 3:1. Trạng thái phải kèm nhãn hoặc biểu tượng, không chỉ có màu.

## Logo cửa hàng

- Theo ảnh người dùng cung cấp ngày 02/11/2026, dùng `app/static/images/neu-shop-logo.png` làm logo chính: biểu tượng túi mua sắm/sách/mũi tên xanh đỏ và chữ NEU SHOP. Giữ nguyên ảnh gốc; không vẽ lại hoặc đổi màu logo theo palette giao diện.
- Macro `shop_logo()` dùng chung tại header/footer khách hàng, sidebar admin và trang đăng nhập admin. Biểu tượng tab trình duyệt dùng cùng ảnh PNG.
- `.shop-logo` tạo vùng hiển thị nền trắng, bo theo `--radius`, chỉ cắt phần lề trắng của ảnh bằng CSS, giữ nguyên tỷ lệ và đủ biểu tượng/chữ. Header desktop rộng 112px, mobile 84px, footer/đăng nhập admin 144px, sidebar admin 120px và thu gọn 48px.
- Logo khách hàng liên kết về `/`; logo sidebar liên kết về `/admin`. Có tên truy cập NEU SHOP và kích thước ảnh khai báo sẵn để tránh xê dịch bố cục.

## Typography

- Font: `"Be Vietnam Pro", system-ui, -apple-system, "Segoe UI", sans-serif`. Dùng nguồn hợp lệ, ưu tiên WOFF2 cục bộ với `font-display: swap`; luôn có fallback. Không cần tải font để tạo quy chuẩn.
- Đợt thiết kế lại đã đóng gói WOFF2 cục bộ (Latin + tiếng Việt, 400/500/600/700) trong `app/static/fonts`, kèm SIL OFL. `style.css` nạp file khai báo font cục bộ, không gọi CDN khi sử dụng web.
- Nội dung: 16px/1.5, weight 400. Nhãn/nút: 14px/1.4, weight 500–600. Metadata: 12px/1.5.
- Tên sản phẩm: 14px/1.5, weight 500. Giá thẻ: 18px/1.4, weight 700. Giá chi tiết: 28px desktop, 24px mobile.
- H1: 32px desktop, 24px mobile. H2: 24px desktop, 20px mobile. H3: 18px. Tiêu đề weight 600–700, line-height 1.25–1.35.
- Heading HTML theo ngữ nghĩa; tránh viết hoa toàn bộ đoạn dài. Font phải hiển thị đủ dấu tiếng Việt.

## Khoảng cách và hình khối

- Thang khoảng cách: 4, 8, 12, 16, 24, 32, 48, 64px.
- Padding thẻ 12–16px; khoảng cách section 24–32px mobile, 32–48px desktop.
- Theo yêu cầu người dùng ngày 29/10/2026, mọi thành phần giao diện có bo góc dùng duy nhất **5px**, qua token `--radius`. Áp dụng cho badge, nút, input/select/textarea, thẻ, ảnh trong khung, banner, avatar, menu, dialog và giao diện admin. Giữ `0` tại cạnh nối hoặc vị trí cần vuông; không dùng pill/50% hoặc mức bo góc khác trong CSS giao diện.
- Shadow mặc định nhẹ hoặc không có; hover thẻ `0 4px 16px rgb(15 23 42 / 8%)`; dialog `0 16px 48px rgb(15 23 42 / 16%)`.
- Một bộ icon thống nhất 20–24px; không trộn emoji vào điều hướng. Icon-only button có tên truy cập.

## Khung trang và responsive

- Mobile-first; mốc tham chiếu 640, 1024, 1280px, điều chỉnh theo nội dung.
- Theo yêu cầu mở rộng toàn màn hình của người dùng: container co giãn 100% chiều ngang, không giới hạn 1200px; lề ngang 16px mobile, 24px tablet/desktop. Header, breadcrumb, banner, lưới và admin dùng cùng trục căn. Form đăng nhập và nội dung bài viết vẫn giữ độ rộng đọc phù hợp bên trong khung trang.
- Header desktop: logo NEU SHOP, danh mục, tìm kiếm nổi bật, tài khoản, giỏ hàng. Chỉ hiển thị tiện ích có chức năng thật.
- Điều hướng chung luôn có liên kết chữ “Trang chủ” kèm icon nhà, hiển thị trực tiếp trên desktop/mobile và trong menu danh mục mobile; trỏ về `/`, đánh dấu `aria-current="page"` khi đang ở trang chủ. Logo tiếp tục dẫn về trang chủ.
- Header mobile: logo, hành động thiết yếu và hàng tìm kiếm đủ rộng; danh mục mở bằng drawer. Thanh cố định không che nội dung hoặc focus.
- Danh mục gợi ý: điện thoại, laptop, máy tính bảng, PC/màn hình, âm thanh, phụ kiện, đồng hồ thông minh. Chỉ hiển thị danh mục có dữ liệu hoặc thuộc phạm vi đã duyệt.
- Footer có thông tin cửa hàng, hỗ trợ và chính sách thật. Không tự bịa hotline, địa chỉ, chứng nhận hoặc cam kết giao hàng.

## Trang chủ

Header → danh mục/banner → danh mục nổi bật → nhóm sản phẩm → hỗ trợ/footer. Desktop có thể đặt danh mục trái, banner chính giữa, tối đa hai banner phụ phải; mobile xếp theo thứ tự đọc và giảm banner phụ. Đường vào sản phẩm phải xuất hiện sớm, không dành toàn màn hình đầu cho khẩu hiệu.

## Danh sách và tìm kiếm

- Breadcrumb, tên danh mục/từ khóa, số kết quả, bộ lọc, sắp xếp, lưới và phân trang/tải thêm khi có hỗ trợ.
- Desktop có sidebar lọc khoảng 240px nếu cần; mobile dùng drawer. Tìm kiếm/lọc/sắp xếp cập nhật khi gõ hoặc chọn, không yêu cầu nút xác nhận khi có JavaScript. Giữ nút áp dụng cho chế độ không JavaScript hoặc khi tải kết quả lỗi. Thuộc tính lọc phụ thuộc ngành hàng.
- Danh mục dùng 12 sản phẩm mỗi trang và số cột chia hết cho 12: 1 dưới 360px, 2 từ 360px, 3 từ 1024px, 4 từ 1280px, 6 từ 1744px, 12 từ 3200px. Container vẫn trải toàn màn hình. Nhờ vậy trang thường đủ ô mỗi hàng ở các kích thước; trang cuối có ít kết quả thì giữ đúng số sản phẩm thực và căn giữa phần còn lại, không tạo ô giả hoặc lặp sản phẩm.
- Nhóm sản phẩm trang chủ và liên quan dùng dải ngang một hàng, có thanh cuộn, focus bàn phím và gợi ý vuốt. Số thẻ thấy được theo màn hình: 1 dưới 360px, 2 mobile, 3 tablet, 4 desktop, 6 từ 1600px, 8 từ 2200px; nhóm liên quan tối đa 4. Thương hiệu cũng dùng dải ngang để tránh hàng cuối lẻ.
- Không hiển thị nút/liên kết “Xóa bộ lọc”, kể cả trạng thái không có kết quả. Người dùng sửa/xóa từ khóa hoặc đổi từng tiêu chí để kết quả tự cập nhật. Giữ trạng thái tìm kiếm/lọc khi quay lại nếu luồng hiện có hỗ trợ.
- Phân trang danh mục dài chỉ hiển thị trang đầu/cuối, trang hiện tại và lân cận, dấu lược bỏ cùng nút trước/sau; tránh dàn hàng chục nút số trên mobile.

## Chi tiết sản phẩm

- Breadcrumb, tên, gallery và thông tin mua hai cột desktop, một cột mobile.
- Hiển thị giá, biến thể nếu có, tồn kho, hành động mua; chọn biến thể cập nhật đúng giá/ảnh/tồn kho theo dữ liệu.
- “Mua ngay” là primary, “Thêm vào giỏ” là secondary. Nếu chỉ có một hành động, dùng primary.
- Bên dưới có mô tả, bảng thông số, chính sách thật; đánh giá và sản phẩm liên quan khi được triển khai.
- Thanh mua cố định mobile là tùy chọn; chừa khoảng trống và không che lỗi form.

## Giỏ hàng và thanh toán

- Giỏ: ảnh, tên, biến thể, đơn giá, số lượng, xóa, tổng tiền. Tóm tắt đơn bên phải desktop và phía dưới mobile.
- Thanh toán: người nhận, địa chỉ, giao hàng/thanh toán theo chức năng thực tế, tóm tắt đơn và nút đặt hàng. Giảm nội dung quảng cáo trong luồng này.
- Nút cuối form là “Tiếp tục xem hợp đồng”: lưu đơn và mở ngay hợp đồng được lập tự động. Hiển thị các bước thông tin → hợp đồng → thanh toán/chờ duyệt COD → xử lý/giao hàng. Khách đọc, đồng ý và xác nhận OTP trước khi mở thanh toán online hoặc admin duyệt COD; sau xác nhận có nút tiếp tục rõ ràng. Chi tiết đơn đặt trạng thái hợp đồng ở đầu trang. Thời hạn giữ hàng online 15 phút bao gồm bước xác nhận hợp đồng và phải được ghi rõ.
- Tách tiền hàng, vận chuyển, giảm giá, tổng cuối; khoản chưa biết ghi rõ. Giữ dữ liệu nhập khi có lỗi, ngăn gửi đơn trùng lúc xử lý.
- Hoàn tất chỉ hiện sau thành công thực tế, dùng mã đơn và bước tiếp theo từ dữ liệu thật.

## Tài khoản và quản trị khi có yêu cầu

Tài khoản dùng menu và vùng nội dung, lịch sử đơn theo cùng token. Quản trị dùng sidebar, tiêu đề, bộ lọc, bảng và form; mật độ cao hơn trang mua hàng, không dùng hero quảng cáo. Bảng mobile cuộn trong vùng riêng hoặc chuyển nhãn–giá trị.

Phiên admin chỉ sử dụng giao diện quản trị. Không có liên kết về cửa hàng hoặc hồ sơ khách hàng trong shell admin; URL mua sắm mở trong phiên admin đưa về `/admin`, thao tác ghi phía khách hàng bị chặn. Đăng xuất admin về `/admin/login`. Xem/in/tải hợp đồng của admin dùng đường dẫn `/admin/contracts/...` và giữ điều hướng trong khu quản trị.

## Thành phần chung

- Ưu tiên component hiện có. Dùng chung button, input, select, badge, product card, price, quantity control, dialog/drawer, pagination và shell trang khi có nhu cầu tái sử dụng thật.
- Thẻ sản phẩm: khung ảnh vuông ổn định, `object-fit: contain`, tên tối đa hai dòng và tên đầy đủ đọc được ở trang chi tiết, thông số ngắn, giá hiện tại. Căn đều nội dung lặp.
- Các thẻ cùng hàng dùng cùng chiều cao ảnh, tên, thông số, đánh giá và vùng giá gốc; giá hiện tại/nút mua thẳng hàng. Vùng không có giá gốc/đánh giá giữ chỗ về bố cục, không bịa số liệu.
- Chỉ có giá gốc gạch ngang/giảm giá khi dữ liệu hợp lệ. Không bịa đánh giá, lượt bán, đếm ngược hoặc khan hiếm hàng.
- Không lồng button trong link. Hành động phụ trên thẻ phải hoạt động bàn phím độc lập bằng HTML hợp lệ.
- Nút/input cao tối thiểu 44px. Secondary viền primary; tertiary dạng chữ; destructive dùng danger. Một cụm chỉ có một hành động nhấn mạnh nhất.
- Form có label, placeholder chỉ gợi ý; lỗi sát trường và hướng dẫn sửa. Lỗi thanh toán không chỉ nằm trong toast.
- Form admin hai cột căn nhãn, điều khiển và phần hướng dẫn theo các hàng chung; cột số/giá căn phải và dùng chữ số có độ rộng đều. Header mobile giữ menu/tài khoản cùng hàng và tìm kiếm toàn chiều ngang ở hàng kế tiếp.
- Mọi ô tìm kiếm khách hàng/quản trị tự cập nhật kết quả khi nhập, dán hoặc xóa chữ, kể cả một ký tự và khi xóa hết; ô tìm kiếm sản phẩm trên header hoạt động từ mọi trang công khai. Không cần Enter hay nút xác nhận. Lọc/tìm kiếm dùng debounce 320ms, chờ hoàn tất bộ gõ tiếng Việt, hủy yêu cầu cũ, giữ focus và con trỏ khi thay kết quả. Lựa chọn phiên bản cập nhật ngay; phí vận chuyển và voucher ở checkout tự tính lại bản xem trước. Đặt hàng, thanh toán, lưu thay đổi quản trị và xóa dữ liệu vẫn là hành động rõ ràng của người dùng.
- Giá dùng `Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })`; tính toán bằng số. Ngày định dạng nhất quán theo ngữ cảnh Việt Nam.

## Trạng thái, chuyển động và khả năng tiếp cận

- Có default, hover, active, focus-visible, disabled; loading/error/success khi phù hợp. Disabled vẫn đọc được.
- Loading giữ kích thước vùng, thông báo tiến trình cho công nghệ hỗ trợ. Empty/error giải thích và có hành động thích hợp. Ảnh lỗi có fallback trong cùng khung.
- Dialog/drawer quản lý focus, đóng bằng Escape, trả focus về nút mở và có nút đóng rõ ràng. Điều khiển không phụ thuộc hover.
- Transition 120–200ms, tôn trọng `prefers-reduced-motion`. Banner không tự chạy mặc định; nếu có tự chạy phải cho dừng.
- Semantic HTML trước ARIA, bàn phím hoạt động, focus rõ, mục tiêu chạm 44px khi khả thi. Kiểm tra zoom 200%, không tràn ngang toàn trang tại 320px.

## Quy trình sửa và kiểm tra

Đọc code trước khi sửa; giữ nội dung, route, dữ liệu và hành vi ngoài phạm vi yêu cầu. Chỉnh token/component chung trước các bản vá riêng từng trang. Không thay ảnh thật bằng placeholder. Khi đổi quy tắc chung, cập nhật tài liệu này và nơi triển khai token cùng nhau.

Trước khi bàn giao:

- Kiểm tra trang bị ảnh hưởng ở 375, 768, 1280px; thêm 320px với form/bảng/thanh cố định.
- Kiểm tra căn lề, chữ, giá, ảnh và component lặp trên các trang liên quan.
- Kiểm tra tương phản, bàn phím, focus, menu/dialog, tràn chữ, loading/empty/error và luồng mua hàng bị tác động.
- Chạy script sẵn có phù hợp bằng `npm run <script>`. Báo cáo đúng kiểm tra đã chạy và hạn chế; nút chỉ có hình thức chưa phải chức năng hoàn tất.

## Áp dụng trong bản demo local

- FastAPI render HTML/Jinja2; token dùng chung nằm trong `app/static/style.css`. Giữ nguyên màu trắng và palette đã chốt dù checker Hallmark đề xuất đổi; ngoại lệ được ghi trong stamp CSS.
- CSS bắt đầu bằng `@charset`, sau đó mới đặt stamp và ghi chú để tuân thủ AGENTS.md về hai dòng đầu source file. Không sửa công cụ upstream để đổi quy tắc này.
- Font Be Vietnam Pro đã đóng gói cục bộ. Minh họa SVG cũ vẫn có cho sản phẩm mẫu trong admin; trang chủ/danh mục hiện tại ưu tiên ảnh thật đã nhập và lưu tại local.
- Sản phẩm, cấu hình, giá và tồn kho khởi tạo là dữ liệu demo được công bố rõ. COD, QR, thẻ và ví phục vụ mô phỏng. Phí giao tiêu chuẩn 30.000 đồng, nhanh 50.000 đồng, nhận tại điểm demo 0 đồng; không có cam kết giao hàng hay thông tin cửa hàng tự tạo.
- Bộ lọc mobile mở bằng dialog bên phải; khi tắt JavaScript hiển thị form lọc trực tiếp. Giỏ hàng, tài khoản và đặt hàng vẫn dùng form HTML gửi về server.
- Giao diện public/khách hàng nằm trong `app/templates/customer`, giao diện quản trị trong `app/templates/admin`. Khu admin dùng sidebar và header điều hành riêng, không dùng header/footer mua sắm. Khách đã đăng nhập có menu tài khoản và các trang thông tin riêng.
- `style.css` cung cấp token/thành phần chung; `customer.css` và `admin.css` triển khai hai bố cục trên. Trang sản phẩm đổi phiên bản bằng GET để giá/ảnh/tồn đúng cả khi tắt JavaScript. Điều kiện voucher/phí giao được cập nhật rõ trước khi xác nhận đặt hàng.

- Tương tác bổ sung theo đặc tả frontend nằm trong `ui.css`/`ui.js`: popup menu và gợi ý, gallery/zoom, toast và loading, bảng biến thể, charts SVG và carousel điều khiển thủ công. Màu và font tiếp tục lấy token chung; nhãn/badge minh họa không trình bày dữ liệu demo như bằng chứng mua bán thật.
- Flash Sale chỉ hiển thị khi biến thể có giá gốc cao hơn giá bán và thời hạn tương lai. Dữ liệu JSON mẫu phải được nhập rõ ràng và đánh dấu minh họa; biểu đồ/dashboard đọc dữ liệu SQLite hiện tại, không vẽ số liệu riêng không liên kết.
- Theo yêu cầu bổ sung danh mục thực tế, các sản phẩm nhập từ CellphoneS dùng tên/cấu hình/ảnh nguồn, lưu ảnh local và hiển thị nguồn tại trang chi tiết. Giá là ảnh chụp dữ liệu tại thời điểm thu thập; tồn kho và giao dịch vẫn mô phỏng. Phân trang được xuống dòng để danh mục lớn không gây tràn màn hình.

## Các trang bổ sung 31/10/2026

Giới thiệu, dịch vụ, liên hệ, tin tức theo chủ đề và hợp đồng dùng chung shell khách hàng. Admin bổ sung hộp thư, thông tin cửa hàng, thống kê, hợp đồng và lưu trữ. Giữ toàn bộ token hiện có, mọi góc bo khác 0 đều là 5px. Nội dung dài dùng cột đọc chính và bảng thông tin phụ; chuyển về một cột ở màn hình nhỏ. Hợp đồng có bản in riêng bỏ điều hướng/nút thao tác, giữ nội dung và mã đối chiếu. Các chức năng chia sẻ, xem bản đồ và xem trước có liên kết/form thay thế phù hợp khi JavaScript tắt.

## Chatbot tư vấn

Chatbot khách hàng mở bằng nút Tư vấn NEU SHOP ở góc dưới, dialog responsive dùng token hiện có. Tra cứu sản phẩm công khai trực tiếp từ SQLite, lọc ngân sách và dẫn đến sản phẩm; không truy cập đơn hàng hay dữ liệu riêng tư. Phiên bản local dùng truy xuất từ khóa và câu trả lời nghiệp vụ, không gọi mô hình AI hoặc dịch vụ bên ngoài.

Theo yêu cầu riêng của người dùng, nút chatbot dùng logo shop hình tròn (ngoại lệ `border-radius: 50%`), kéo thả bằng chuột/cảm ứng trong giới hạn màn hình, hỗ trợ phím mũi tên. Chỉ shell khách hàng hiển thị chatbot; admin không có nút này.

Chatbot đã bổ sung provider Ollama local mặc định và Gemini cấu hình sau bằng `.env`. Chi tiết thiết lập, dữ liệu gửi và giới hạn tại `docs/chatbot-ai.md`. Khi provider không sẵn sàng, UI ghi rõ đang tra cứu local. Khả năng hiểu ngôn ngữ tự nhiên yêu cầu runtime/model hoặc API key thực tế.

Khung hội thoại neo theo vị trí logo: ưu tiên cạnh bên, đổi sang trên/dưới khi thiếu chỗ và giới hạn trong viewport. Kéo logo khi khung đang mở cập nhật khung ngay; resize/viewport bàn phím cũng tính lại vị trí. Trạng thái AI hiển thị ở footer, không chèn lỗi kỹ thuật trước mọi câu trả lời tra cứu.

Chatbot không có câu hỏi gợi ý sẵn hoặc dòng chú thích dưới ô nhập. Header chỉ có nút đóng; hành động “Xóa dữ liệu” ở footer xóa lịch sử hội thoại trong phiên, hủy yêu cầu/hiệu ứng đang chạy và trả màn hình chào. Không xóa dữ liệu sản phẩm của cửa hàng.

Câu trả lời sản phẩm có thẻ ảnh local, tên, giá/phiên bản, tồn kho, thông số và liên kết Xem chi tiết tới đúng variant. Xóa dữ liệu dùng chữ nhỏ căn phải ở cuối khung, giữ vùng bấm tối thiểu 44px.

Kết quả tìm sản phẩm trong chat mở đầu bằng một câu đếm đúng tổng số sản phẩm phù hợp. Nếu chỉ hiển thị một phần, ghi rõ số thẻ đang hiển thị. Không lặp tên, giá, tồn kho hoặc thông số của các thẻ thành đoạn văn phía trên.

Header/nav khách hàng và topbar admin bám đầu viewport khi cuộn. Chiều cao header được theo dõi để chừa khoảng cuộn tới anchor và tránh che tóm tắt đơn. Gỡ toàn bộ cụm chia sẻ/sao chép liên kết ở sản phẩm, bài viết và phiếu liên hệ; không hiển thị nút chia sẻ Facebook.

## Thương hiệu và bài viết

Dải thương hiệu dùng logo SVG thật từ nguồn Simple Icons, giữ nguyên tỷ lệ qua object-fit contain; hiển thị các thương hiệu có file logo đã tải, liên kết lọc thương hiệu như cũ. Logo bên thứ ba chỉ dùng để nhận diện thương hiệu sản phẩm; ngoại lệ này được người dùng yêu cầu, không áp dụng cho logo/nhận diện của NEU SHOP. Trang chủ hiển thị 6 bài mới; trang đọc có cột bài chính, mục lục anchor và 6 bài đọc tiếp, xuống một cột trên mobile. Nội dung biên soạn có nguồn rõ ràng, không nhập giá/ưu đãi nguồn thành chính sách cửa hàng.

## Phiên riêng theo tab và logo đầy đủ

Theo yêu cầu người dùng: trình duyệt lưu phiên ký trong sessionStorage riêng từng tab, truyền bằng header nội bộ; không dùng cookie đăng nhập chung giữa tab. Trang riêng tư mở qua bước khởi tạo phiên và yêu cầu JavaScript. Mở tab mới cần đăng nhập lại; tải lại/điều hướng trong tab hiện tại giữ phiên. Trang công khai vẫn xem được khi tắt JavaScript. Logo thương hiệu thay bằng 24 ảnh wordmark PNG từ nguồn CellphoneS và hai SVG đã căn khung; nguồn từng ảnh nằm trong docs/brand-logos.json.

Điều hướng liên kết nội bộ trong cùng tab giữ giao diện đang hiển thị trong lúc lấy trang mới, không ẩn toàn bộ root hoặc khởi tạo lại phiên tab. URL và lịch sử Back được cập nhật; Ctrl/Cmd-click và target blank vẫn mở tab riêng cần đăng nhập. Các timer trang cũ được hủy trước khi chuyển để tránh cập nhật nhầm nội dung.

Điều hướng cùng shell chỉ thay `main[data-live-results]`, giữ nguyên DOM header, sidebar admin, menu tài khoản và chatbot. Chỉ cập nhật mục đang chọn, tiêu đề và vùng nội dung; vị trí cuộn sidebar giữ nguyên. Listener/timer của trang cũ được dọn trước khi khởi tạo tương tác trang mới. Chỉ dựng lại toàn document khi đổi loại shell hoặc chuyển trạng thái đăng nhập.

## Rà soát giao diện chi tiết ngày 02/11/2026

Trang chi tiết sản phẩm nhấn phần giá và phiên bản; đơn hàng chia rõ sản phẩm, thanh toán và lịch sử. Hợp đồng dùng phần thông tin hai bên cân đối, tổng tiền có nền phân biệt, cột trạng thái bên phải trên màn hình rộng và một cột trên điện thoại. Mã đối chiếu dài nằm trong phần mở rộng. Nội dung hợp đồng đã xác nhận được giữ nguyên trong mục Điều khoản đã xác nhận; không sửa ảnh chụp dữ liệu hoặc mã băm để thay câu chữ.

Nhãn giao diện và nội dung có thể chỉnh sửa dùng cách viết rõ ràng, bỏ từ demo/minh họa không cần thiết. Các dịch vụ chưa kết nối vẫn được mô tả chính xác tại nơi thực hiện, không đổi tên để tạo cảm giác đã tích hợp ngân hàng hay vận chuyển. Email tài khoản, mã kỹ thuật, dữ liệu giao dịch và lịch sử xác nhận không thay đổi chỉ nhằm làm đẹp câu chữ.

Đã rà 40 trang công khai, tài khoản và quản trị ở 375/768/1280px: 120 lượt không ghi nhận lỗi JavaScript hoặc tràn ngang toàn trang. Đây là kiểm tra bố cục và tải trang, không thay thế kiểm thử từng thao tác nghiệp vụ.

## Hồ sơ quản trị ngày 03/11/2026

Avatar quản trị dẫn trực tiếp đến /admin/profile. Trang chỉ hiển thị thông tin cá nhân và hai thao tác chỉnh sửa thông tin, đổi mật khẩu; dùng card rộng tối đa 800px và một cột trên điện thoại. Nút Đăng xuất thay ô trạng thái NEU SHOP ở cuối sidebar, dùng POST và CSRF hiện có. Không có menu mua sắm hay thông tin tài khoản khách hàng trong trang này.


## Bố cục quản trị thống nhất ngày 03/11/2026

Bảng và ô nhập dùng cỡ chữ 14px, nhãn form 13px; tiêu đề trang phân cách với nội dung bằng đường viền mảnh. Thanh lọc dùng khoảng cách 16px, bảng đặt trong khung cuộn riêng. Trang danh mục chia cột theo nội dung, nhóm thao tác phụ tách khỏi dòng chỉnh sửa. Form viết bài mới mặc định thu gọn để ưu tiên danh sách. Mục mở rộng có ký hiệu cộng/trừ. Đăng xuất luôn có thể truy cập ở cuối thanh bên, kể cả sidebar thu gọn và mobile. Giữ màu navy, primary và góc bo 5px. Đã kiểm tra 22 trang/trạng thái ở 320/768/1280px: 66 lượt không tràn ngang, bộ lọc và cặp ô nhập thẳng hàng, không lỗi JavaScript.


## Đăng nhập chung

/login và /admin/login dùng cùng giao diện đăng nhập. Vai trò lưu trong tài khoản quyết định chuyển đến /admin hoặc khu tài khoản/checkout sau xác thực; không dựa vào trường portal do trình duyệt gửi. Trang xác thực dùng ảnh thật giếng trời/cầu thang trung tâm A2 NEU, giữ tỷ lệ. Theo yêu cầu chỉnh ngày 03/11/2026, bỏ chú thích dưới ảnh, nguồn lưu tại THIRD_PARTY_NOTICES.md; vùng ảnh dùng token cục bộ --auth-surface #F3EEE6 (kem ấm), chữ tối theo token chung, padding 40px 32px và góc bo 5px.



## Cập nhật nền xanh nước nhạt và chuyển form xác thực

Theo yêu cầu ngày 03/11/2026, các vùng nền navy cũ trên khách hàng và quản trị chuyển sang shell #E0F2FE, chữ tối #0F172A và chữ phụ #475569. Quyết định này thay thế các mô tả navy cũ bên trên, kể cả nền kem quanh ảnh xác thực. Giữ màu nút primary và chữ trắng trên primary; không đổi màu logo hoặc ảnh. Desktop: form đăng nhập bên trái, ảnh bên phải; đăng ký ngược lại. Khi đổi giữa hai form, hai vùng trượt sang vị trí mới trong 420ms, tắt chuyển động khi reduced-motion. Mobile dùng một cột.

Chuyển login/register giữ nguyên DOM khung xác thực và ảnh, chỉ thay form; không chạy lại script trang hoặc cuộn về đầu. Giữ email đã nhập, không sao chép mật khẩu. Desktop dùng chiều cao khung tối thiểu 620px, padding dọc 28px và khoảng cách field 14px để không nhảy bố cục giữa hai form. Kiểm tra bằng npm run check:auth-transition tại 375/768/1280px.


## Trang giới thiệu ngày 04/11/2026
Trang /about dùng bố cục ảnh NEU và phần mở đầu hai cột, lịch sử/định hướng Đại học, nội dung NEU SHOP chỉnh sửa từ admin và CTA sản phẩm/liên hệ. Mobile xếp một cột. Dùng ảnh A2 local có nguồn trong THIRD_PARTY_NOTICES.md, góc bo và token chung. Thông tin Đại học dẫn nguồn neu.edu.vn (lịch sử, sứ mệnh, liên hệ), tách địa chỉ Đại học khỏi cửa hàng; không suy diễn quan hệ bảo trợ. Trang dịch vụ giữ template cũ.

