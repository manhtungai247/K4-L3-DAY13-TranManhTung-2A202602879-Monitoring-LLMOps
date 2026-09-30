# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: `response_sent.latency_ms` (P95 latency <= 3000ms)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ quá lâu (>3 giây) trước khi nhận câu trả lời, trải nghiệm tương tác bị chậm.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở dashboard panel `latency` để xác nhận P95/P99 và khoảng thời gian bắt đầu tăng đột biến.
  2. **Logs:** Lọc `data/logs.jsonl` trong khoảng thời gian xảy ra sự cố, tìm các log có `event == "response_sent"` và `latency_ms > 3000`, trích xuất `correlation_id`.
  3. **Traces:** Mở trace tương ứng trên Langfuse bằng `correlation_id`, kiểm tra span tree xem độ trễ nằm ở span `retrieval` hay `generation`.
- Mitigation tạm thời: Nếu do retrieval quá tải, chuyển tạm sang cache hoặc fallback search; nếu do LLM generation hoặc prompt v2 quá dài, thực hiện rollback prompt về version ổn định (v1).
- Owner: `student-2A202602879`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ lỗi request (`request_failed / request_received * 100`) <= 2%
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Nhiều người dùng nhận thông báo lỗi HTTP 500 hoặc không nhận được câu trả lời từ chatbot.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Kiểm tra panel `errors` trên dashboard để xác nhận error rate và các `error_type` phổ biến (ví dụ: `RuntimeError`, `TimeoutError`).
  2. **Logs:** Tìm log line có `event == "request_failed"`, đọc trường `error_type`, `payload.detail` và lấy `correlation_id`.
  3. **Traces:** Mở trace theo `correlation_id` trên Langfuse để xem exception stack trace và trạng thái span bị fail (retrieval lỗi hay generation lỗi).
- Mitigation tạm thời: Tắt incident practice nếu đang diễn tập (`python scripts/inject_incident.py --disable`), khởi động lại connection pool/vector store, hoặc bật chế độ trả lời fallback khi retrieval thất bại.
- Owner: `student-2A202602879`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: `tool_success_rate_pct` (Tỉ lệ retrieval thành công >= 90%)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Chatbot trả lời sai ngữ cảnh, thiếu thông tin tài liệu chính xác từ domain knowledge base.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel `errors` trên dashboard để theo dõi `retrieval success rate` và số lượng thất bại.
  2. **Logs:** Lọc log có `tool_name == "retrieval"` và `tool_success == false`, lấy `correlation_id` và thông điệp lỗi.
  3. **Traces:** Mở trace trên Langfuse, inspect span `retrieval` để kiểm tra input query và output lỗi trả về từ vector database.
- Mitigation tạm thời: Kiểm tra trạng thái dịch vụ vector DB / embedding model; chuyển hướng truy vấn sang replica hoặc dùng tài liệu tĩnh dự phòng (static fallback docs).
- Owner: `student-2A202602879`

