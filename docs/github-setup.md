# Chuẩn bị đưa NEU SHOP lên GitHub

## File cần đưa lên

`app/`, `tests/`, `docs/`, `tools/` (bỏ metadata `.git` lồng), `.agents/skills/`, `AGENTS.md`, `DESIGN.md`, `README.md`, `requirements.txt`, `package.json`, `package-lock.json`, `.env.example`, `.gitignore`, `.gitattributes`, `.github/workflows/check.yml`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`. Giữ giấy phép upstream và font. `data/erd.mmd` và `data/erd.html` được phép đưa lên.

Không tải nguyên thư mục dự án bằng kéo thả trên web: nên dùng Git/GitHub Desktop để tôn trọng `.gitignore`.

## File không đưa lên

`.env`, `.venv/`, `node_modules/`, `test-results/`, database và toàn bộ dữ liệu runtime trong `data/` (trừ ERD), ảnh tải lên, khóa phiên, backup, log, thư mục IDE và `.git` của hai công cụ upstream. Không sửa hoặc xóa database hiện tại chỉ để upload.

## Chạy lại sau khi clone

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
Copy-Item .env.example .env
npm run news:import
npm run dev
```

Database local được tạo khi khởi động. Để có danh mục đã nhập, chạy `npm run catalog:import` từ JSON đã đóng gói; các ảnh danh mục trong `app/static/images/catalog` phải được giữ cùng source. Chỉ chạy `npm run demo:seed` khi muốn thêm dữ liệu minh họa. Xem `docs/catalog-import.md` và `docs/chatbot-ai.md` trước khi thiết lập dữ liệu/AI.

## Tạo bản sạch để đưa lên (khuyến nghị)

Chạy `npm run github:prepare`. Script tạo bản sao mới trong `github-export/neu-shop-<thời gian>`, không đụng dữ liệu gốc và không sao chép `.git` lồng trong tools. Script chặn một số mẫu khóa nhạy cảm và file quá 50 MB; đây là kiểm tra giới hạn, không thay thế rà soát thủ công. Dùng thư mục xuất này với GitHub Desktop hoặc các lệnh bên dưới. Không đẩy chính thư mục `github-export` từ kho gốc. Báo cáo file/size nằm trong `GITHUB_EXPORT_REPORT.json`.

## Tạo repository và đẩy mã

Tạo repository trống trong tài khoản của bạn. Nên chọn private nếu chưa xác nhận quyền phân phối ảnh và dữ liệu bên thứ ba. Sau đó tại gốc dự án:

```powershell
git init
git add .
git status --short
git diff --cached --stat
```

Dừng ở đây để xem danh sách staged; không được có `.env`, `shop.db`, `uploads`, `.session-secret`, `node_modules`, `.venv` hoặc Git metadata trong `tools`. Nếu Git nhận tools thành embedded repository, bỏ staging riêng hai thư mục đó và xử lý metadata trước khi thêm lại; không xóa source hoặc giấy phép upstream.

Sau khi kiểm tra, dùng URL repository của chính bạn:

```powershell
git commit -m "Initial NEU SHOP project"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

Không chèn mật khẩu, token hay API key vào URL remote hoặc README. Nếu đã có repository/remote, kiểm tra `git status` và `git remote -v` thay vì chạy lại các bước tạo mới.

## Kiểm tra

`npm run check` kiểm thử backend trên database tạm. GitHub Actions tự chạy bước này cùng `npm ci` khi push/PR. Kiểm thử trình duyệt dùng Chrome local và đường dẫn Windows trong các script, chưa cấu hình chạy toàn bộ trong CI. AI được cấu hình bằng `.env` riêng của máy; GitHub Actions không cần API key hay Ollama cho bộ backend hiện tại.

Chưa tạo file LICENSE cho mã nguồn tự viết vì chưa có quyết định giấy phép của chủ dự án. Đây không phải điều kiện bắt buộc để tạo kho riêng, nhưng cần quyết định nếu muốn người khác được phép tái sử dụng mã.
