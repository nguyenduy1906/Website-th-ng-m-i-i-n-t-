# Chatbot AI NEU SHOP

Mặc định gọi Ollama local tại 127.0.0.1:11434; không tự gửi dữ liệu sang Gemini khi local lỗi. Khi AI không sẵn sàng, trả lời bằng dữ liệu tra cứu và ghi rõ trạng thái.

## AI local

Cài Ollama từ https://ollama.com/download rồi chạy `ollama pull qwen3:4b`. Mở Ollama (hoặc `ollama serve` nếu chưa có dịch vụ). Model có thể thay bằng tên model đã tải qua NEU_OLLAMA_MODEL. Chọn model phù hợp RAM/VRAM máy.

Sao chép `.env.example` thành `.env` tại gốc dự án. Mặc định NEU_AI_PROVIDER=ollama. Khởi động web bằng npm run dev sau khi kích hoạt .venv. Không cần thêm thư viện Python.

## Gemini sau này

Trong `.env`, đặt NEU_AI_PROVIDER=gemini, điền GEMINI_API_KEY và NEU_GEMINI_MODEL bằng model khả dụng trong tài khoản Google AI Studio. Khóa chỉ dùng phía server, không trả về trình duyệt. Khi chọn Gemini, câu hỏi, tối đa 8 lượt lịch sử và dữ liệu sản phẩm công khai liên quan được gửi đến Google. Không gửi dữ liệu tài khoản hay đơn hàng riêng tư.

## Giới hạn

Ngữ cảnh gồm dữ liệu sản phẩm đang công khai và câu trả lời chính sách của bộ tra cứu. Lịch sử hỗ trợ nối tiếp hội thoại, nhưng truy xuất theo từ khóa vẫn có thể bỏ sót sản phẩm trong câu hỏi quá mơ hồ. Prompt giới hạn phạm vi và yêu cầu không bịa dữ liệu; câu trả lời mô hình vẫn cần đối chiếu trang sản phẩm. Không có công cụ sửa dữ liệu/đặt hàng cho AI. Lịch sử lưu sessionStorage của trình duyệt, nút thùng rác xóa hội thoại.

Tích hợp REST dựa trên https://github.com/ollama/ollama/blob/main/docs/api.md và https://ai.google.dev/api/generate-content.

## Nhận diện câu hỏi hội thoại

Lời chào, giới thiệu trợ lý, khả năng hỗ trợ và cảm ơn được xử lý trước bước tìm sản phẩm, không gửi sang mô hình để tránh trả danh sách thiết bị có tên trùng từ thông dụng (ví dụ AI). Lịch sử chỉ được bổ sung cho câu hỏi nối tiếp rõ ràng; không ghép chủ đề sản phẩm trước đó vào câu hỏi giới thiệu.
