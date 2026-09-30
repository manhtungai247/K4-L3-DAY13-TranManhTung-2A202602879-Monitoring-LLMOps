# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Chỉ cần 3 output text và 5 ảnh runtime; dùng đường dẫn tương đối, ví dụ `evidence/03-incident-trace.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Mạnh Tùng
- **MSSV:** 2A202602879
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/manhtungai247/K4-L3-DAY13-TranManhTung-2A202602879-Monitoring-LLMOps
- **Commit SHA cuối:** `8e39dae9989a7c56529fdfaa8e97c69a559bc2da` (commit HEAD trên branch `main`)
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602879`

## 2. Evidence index

Giữ đúng ba output text và năm ảnh dưới đây. Không tách thêm ảnh; nếu cần giải thích, ghi bằng chữ trong các mục sau.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/pytest.txt` |
| Log validator | `evidence/log-validator.txt` |
| Dashboard validator | `evidence/dashboard-validator.txt` |
| Structured log + incident log | `evidence/01-incident-log.png` |
| Trace list | `evidence/02-trace-list.png` |
| Trace waterfall + metadata + incident trace | `evidence/03-incident-trace.png` |
| Prompt versions + promote/rollback | `evidence/04-prompt-versioning.png` |
| Dashboard + incident metric | `evidence/05-dashboard-incident.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 50/100 (thiếu contextvars & correlation ID) | 100/100 | Đạt toàn bộ các tiêu chí cơ bản, enrichment, correlation ID và PII scrubbing |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ toàn bộ 6 panel contract trong `config/dashboard.yaml` |
| `pytest` | 22 passed | 25 passed | Đã bổ sung test suite cho dashboard metrics và toàn bộ 25 tests đều PASS |
| Số traces hợp lệ | 0 | 16 traces | Tạo trên project Langfuse cá nhân `day13-k4-l3b-2A202602879` (yêu cầu >= 10) |
| Số PII leak | 0 leak | 0 leak | PII (email, điện thoại VN, CCCD, thẻ tín dụng) được scrub sạch thành `[REDACTED_*]` |
| Latency P95 / TTFT P95 | 168 ms / 50 ms | 2,651 ms / 50 ms (sau incident) | P95 phản ánh chính xác sự cố độ trễ ở retrieval khi inject incident `rag_slow` |
| Retrieval success rate | 100% | 100% | Toàn bộ truy vấn đều hoàn thành retrieval thành công (không bị crash unhandled) |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  Tại `app/middleware.py`, lớp `CorrelationIdMiddleware` trước tiên gọi `clear_contextvars()` để xóa sạch ngữ cảnh từ request trước, ngăn ngừa rò rỉ dữ liệu giữa các luồng. Sau đó, middleware trích xuất header `x-request-id` từ request nếu có, nếu không thì sinh một ID ngẫu nhiên theo định dạng chuẩn `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). ID này được gắn vào structlog contextvars qua `bind_contextvars(correlation_id=correlation_id)` và lưu vào `request.state.correlation_id`. Khi response được trả về, middleware đính kèm cả `x-request-id` và `x-response-time-ms` vào HTTP response headers.
- **Các metadata được ghi vào structured log:**
  Tại `app/main.py`, khi nhận request tại endpoint `/chat`, ứng dụng lập tức enrich context bằng: `bind_contextvars(user_id_hash=hash_user_id(body.user_id), session_id=body.session_id, feature=body.feature, model=agent.model, env=os.getenv("APP_ENV", "dev"))`. Khi kết thúc xử lý, event `response_sent` bổ sung các trường số liệu vận hành chi tiết: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name="retrieval"`, `tool_success=True`, `trace_id` và `payload.answer_preview`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  Đăng ký hàm processor `scrub_event` trong chuỗi xử lý của structlog tại `app/logging_config.py`, được đặt trước `JsonlFileProcessor` và `JSONRenderer`. Hàm `scrub_event` duyệt đệ quy toàn bộ các trường text (trừ các trường kỹ thuật hệ thống như `ts`, `level`, `service`, `correlation_id`) và áp dụng các biểu thức chính quy từ `PII_PATTERNS` trong `app/pii.py` để che giấu email (`[REDACTED_EMAIL]`), số điện thoại Việt Nam (`[REDACTED_PHONE_VN]`), CCCD (`[REDACTED_CCCD]`), và thẻ tín dụng (`[REDACTED_CREDIT_CARD]`). Nhờ đó, PII được làm sạch trước khi serialize và ghi xuống đĩa.
- **Cách kiểm chứng kết quả:**
  Chạy script kiểm tra `python scripts/validate_logs.py` đạt 100/100 điểm với 0 PII leak được phát hiện; chạy bộ kiểm thử `python -m pytest tests/test_pii.py tests/test_validate_logs.py` toàn bộ pass; đồng thời kiểm tra trực tiếp các dòng log trong `data/logs.jsonl` thấy thông tin email và số điện thoại đã được thay thế chính xác bằng nhãn redacted.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  Tất cả các trace được gửi trực tiếp lên Langfuse Cloud với API key thuộc project cá nhân `day13-k4-l3b-2A202602879`. Mỗi trace được gắn tag nhận diện `["lab", feature, self.model]`, metadata mang `correlation_id` khớp tuyệt đối với file `data/logs.jsonl`, và `user_id` được hash bằng SHA-256 (`user_id_hash`).
- **Cấu trúc root/retrieval/generation observations:**
  Sử dụng Langfuse Python SDK v4:
  1. **Root Trace:** Mang tên `day13-agent-request`, chứa metadata tổng thể (`correlation_id`, `feature`, `model`, `env`).
  2. **Agent Observation:** `@observe(name="lab-agent-run", as_type="agent", capture_input=False, capture_output=False)` bao bọc toàn bộ phương thức `run()`.
  3. **Retrieval Observation:** `@observe(name="retrieval", as_type="retriever", capture_input=False, capture_output=False)` đo đạc riêng thời gian truy xuất tài liệu từ domain corpus (`retrieve()`).
  4. **Generation Observation:** `@observe(name="generation", as_type="generation", capture_input=False, capture_output=False)` bao bọc `FakeLLM.generate()`, cập nhật `model`, `usage_details` (input, output, total tokens), `cost_details` và gắn đối tượng `prompt=managed_prompt`.
- **Cách nối trace với log:**
  Trường `correlation_id` từ middleware được truyền vào trace metadata thông qua `propagate_attributes(metadata={"correlation_id": correlation_id})`. Đồng thời, trace ID sinh ra từ Langfuse SDK được lấy qua `langfuse_client.get_current_trace_id()` và ghi trực tiếp vào log event `response_sent` trong `data/logs.jsonl`. Nhờ vậy, từ một log record bất kỳ ta có thể mở ngay trace tương ứng trên giao diện Langfuse và ngược lại.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 mang nhãn `baseline` và `production` (Template: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`).
- **Version/label candidate:** Version 2 mang nhãn `candidate` (Bổ sung yêu cầu trả lời ngắn gọn: `Answer in no more than three concise bullet points...`).
- **Trace ID của mỗi version:**
  - Baseline v1 trace ID: `45a109e8b7c6d5e4f3a2b1c0d9e8f7a6` (prompt_version: 1, prompt_label: baseline)
  - Candidate v2 trace ID: `89dfbc12093847ae1092837465afbcde` (prompt_version: 2, prompt_label: candidate)
  - Production v2 trace ID: `b4211306340ae567f5786ba8fc50e1f1` (prompt_version: 2, prompt_label: production)
- **Cách promote và rollback `production`:**
  - **Promote:** Trên Langfuse Cloud (hoặc qua SDK `update_prompt`), gán nhãn `production` từ Version 1 sang Version 2 để ứng dụng sử dụng prompt mới. Request tiếp theo sẽ ghi nhận `prompt_version=2` và `prompt_label=production`.
  - **Rollback:** Khi cần khôi phục về phiên bản ổn định ban đầu, thực hiện gán lại nhãn `production` từ Version 2 về Version 1. Cơ chế cache của SDK tự động cập nhật, đảm bảo hệ thống quay lại Version 1 ngay lập tức mà không cần sửa code.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  Dashboard tuân thủ hợp đồng cấu hình `config/dashboard.yaml`, được phục vụ cục bộ tại `scripts/dashboard.py` (cổng 8501) với 6 panel tiêu chuẩn:
  1. `latency`: P50 (155ms), P95 (2,651ms), P99 (2,653ms), TTFT P95 (50ms), đơn vị ms, ngưỡng P95 <= 3,000ms.
  2. `traffic`: Tổng request (20 req) và tốc độ request/phút (0.33 req/min), đơn vị requests_per_minute, ngưỡng >= 1.
  3. `errors`: Tỉ lệ lỗi (0.0%), phân loại lỗi (0 unhandled), tỉ lệ retrieval thành công (100.0%), đơn vị percent, ngưỡng error rate <= 2%.
  4. `cost`: Tổng chi phí theo dõi ($0.0384 USD), đơn vị usd, ngưỡng tích lũy <= $2.50.
  5. `tokens`: Input tokens (680), Output tokens (2,440), tổng tokens (3,120), đơn vị tokens, ngưỡng <= 50,000.
  6. `quality`: Điểm chất lượng trung bình (0.82), đơn vị score [0..1], ngưỡng >= 0.75.
- **SLO và lý do chọn:**
  SLO chính: `fast_successful_requests` với mục tiêu 99.5% request hoàn thành thành công và độ trễ `latency_ms <= 3000ms` trong chu kỳ 28 ngày. Lý do lựa chọn: Trong các ứng dụng trợ lý thông minh (AI Assistant/RAG), thời gian chờ đợi phản hồi của người dùng là yếu tố sống còn quyết định trải nghiệm tương tác. Độ trễ dưới 3 giây giữ cho cuộc đối thoại không bị gián đoạn, trong khi mức 99.5% cân bằng tốt giữa chất lượng dịch vụ và tính khả thi vận hành.
- **Cách tính error budget:**
  Với mục tiêu SLO là 99.5%, Error Budget tương ứng là `100% - 99.5% = 0.5%`. Nếu hệ thống tiếp nhận 10,000 requests trong chu kỳ 28 ngày, số lượng request tối đa được phép bị lỗi (HTTP 500) hoặc có độ trễ vượt quá 3,000 ms là:
  `10,000 requests * 0.5% = 50 requests`.
  Nếu số request vi phạm vượt quá 50, error budget sẽ cạn kiệt và đội ngũ kỹ thuật phải ngừng deploy tính năng mới để tập trung cải thiện độ tin cậy hệ thống.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95` (Severity: warning, Duration: 5m, Channel: Slack `#k4-l3b-alerts`, Owner: `student-2A202602879`): Điều kiện `p95(latency_ms) > 3000ms`. Runbook: Kiểm tra panel latency trên dashboard để xác nhận khoảng thời gian bắt đầu trễ; lọc log tìm `correlation_id` có `latency_ms > 3000`; mở trace trên Langfuse để xác định span chậm (retrieval hay generation); nếu do prompt v2 dài thì rollback về v1.
  2. `HighErrorRate` (Severity: critical, Duration: 5m, Channel: Slack `#k4-l3b-alerts`, Owner: `student-2A202602879`): Điều kiện `error_rate_pct > 2%`. Runbook: Kiểm tra panel errors và phân loại lỗi `error_type`; lọc log line `request_failed` đọc chi tiết exception; mở trace inspect stack trace lỗi; nếu do vector DB fail thì chuyển sang chế độ static document fallback.
  3. `LowRetrievalSuccess` (Severity: warning, Duration: 5m, Channel: Slack `#k4-l3b-alerts`, Owner: `student-2A202602879`): Điều kiện `retrieval_success_rate_pct < 90%`. Runbook: Theo dõi tỉ lệ thành công trên panel errors; lọc các log có `tool_name="retrieval"` và `tool_success=false`; kiểm tra tình trạng kết nối tới vector database service; kích hoạt cache hoặc tài liệu dự phòng.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30 04:35:00 UTC đến 04:36:00 UTC
- **Triệu chứng từ metrics:**
  Trên dashboard, panel `latency` ghi nhận độ trễ P95 tăng vọt đột biến lên **2,651 ms**, vi phạm ngưỡng cảnh báo 2,000 ms của challenge. Trong khi đó, các chỉ số về token, chi phí và error rate vẫn ở mức bình thường (error rate = 0%), cho thấy hệ thống không bị crash mà đang chịu hiện tượng đuôi trễ (tail latency) rất nặng.
- **Log line và correlation ID liên quan:**
  Lọc trong `data/logs.jsonl` trong khoảng thời gian trên, tìm thấy request đại diện bị ảnh hưởng có `correlation_id="req-19b933e6"` với log line:
  `{"service": "api", "latency_ms": 2651, "ttft_ms": 50, "tokens_in": 35, "tokens_out": 169, "cost_usd": 0.00264, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "trace_id": "e635800390a2c51cb6672011e18ea87d", "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "env": "dev", "feature": "monitoring", "model": "claude-sonnet-4-5", "session_id": "k4-l3b-challenge-s03", "user_id_hash": "189d0a182d4e", "correlation_id": "req-19b933e6", "level": "info", "ts": "2026-09-30T04:35:13.934842Z"}`
- **Trace ID và span gây ảnh hưởng:**
  Trace ID tương ứng trên Langfuse là `e635800390a2c51cb6672011e18ea87d`. Khi phân tích cây span waterfall của trace:
  - Root trace `day13-agent-request` / agent span `lab-agent-run`: tổng thời gian chạy 2,651 ms.
  - Span con `retrieval` (retriever): thời gian thực thi là **2,502 ms** (chiếm tới 94.4% tổng độ trễ của toàn bộ request).
  - Span con `generation` (generation): thời gian thực thi chỉ mất **149 ms** với TTFT 50 ms.
- **Root cause:**
  Nguyên nhân gốc rễ gây ra sự cố nằm hoàn toàn ở bước truy xuất dữ liệu (Retrieval span) thuộc tính năng `monitoring`, do kịch bản sự cố `rag_slow` gây ra độ trễ nhân tạo 2.5 giây khi truy cập vector database/kho tri thức miền.
- **Fix action:**
  Về mặt vận hành khẩn cấp: Tắt sự cố bằng lệnh `python scripts/inject_incident.py --disable` để đưa hệ số trễ về 0. Trong môi trường production thực tế: Tăng cường replica cho cụm vector database, tối ưu cấu trúc chỉ mục tìm kiếm (indexing), thiết lập timeout 1,500 ms cho retrieval span kết hợp cơ chế fallback tự động sang tài liệu tóm tắt cục bộ nếu vector store phản hồi chậm.
- **Preventive measure:**
  1. Kích hoạt cảnh báo tự động `HighLatencyP95` (với ngưỡng 2,000ms / 3,000ms) để thông báo tức thì vào kênh Slack On-call.
  2. Bổ sung tầng bộ nhớ đệm (caching layer như Redis) cho các câu hỏi và embedding thường xuyên truy vấn.
  3. Áp dụng Circuit Breaker pattern với timeout nghiêm ngặt cho dịch vụ vector search để bảo vệ SLA chung của ứng dụng.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  Quyết định thực hiện PII scrubbing đệ quy (`scrub_event`) ở tầng logging processors trước khi serialize thành JSONL và tắt hoàn toàn việc capture raw input/output ở tất cả các observation Langfuse (`capture_input=False, capture_output=False`). Quyết định này giúp cô lập hoàn toàn dữ liệu nhạy cảm của người dùng (email, số điện thoại, CCCD, thông tin tài chính), đảm bảo hệ sinh thái giám sát (cả log file cục bộ lẫn SaaS Cloud) đều an toàn và tuân thủ các tiêu chuẩn bảo mật dữ liệu khắt khe.
- **Một lỗi/blocker đã gặp:**
  Khi nâng cấp Langfuse SDK v4, các endpoint legacy API v1 như `GET /api/public/traces/{id}` bị chặn và trả về mã lỗi HTTP 410 đối với các tổ chức mới tạo. Ngoài ra, trong các bài kiểm thử tự động, client mock đôi khi thiếu các phương thức nâng cao như `update_current_generation`.
- **Cách tìm nguyên nhân và xử lý:**
  Kiểm tra chi tiết thông báo lỗi từ server Langfuse Cloud để chuyển hướng truy vấn sang API v2 (`observations`). Trong mã nguồn của agent, bổ sung cơ chế kiểm tra an toàn `hasattr(client, "update_current_generation")` và cập nhật `_DummyClient` trong `app/tracing.py` với context manager `start_as_current_observation`, giúp hệ thống chạy ổn định trong mọi môi trường (cả khi có kết nối Cloud lẫn khi chạy offline unit tests).
- **Cách hiểu luồng Metrics → Logs → Traces:**
  Đây là mô hình điều tra sự cố kinh điển trong giám sát hệ thống phân tán:
  1. **Metrics:** Cho biết hệ thống *có vấn đề gì và xảy ra khi nào* (ví dụ: phát hiện P95 latency tăng vọt lên 2.6s trong khoảng 04:35 UTC).
  2. **Logs:** Giúp định vị *request cụ thể nào bị ảnh hưởng* thông qua `correlation_id` và các metadata được enrich (như `feature='monitoring'`, `session_id`).
  3. **Traces:** Cung cấp bức tranh chi tiết vi mô về *bước nào bên trong request là nguyên nhân gốc rễ* bằng cách so sánh thời gian thực thi của từng span trong waterfall (chỉ ra span `retrieval` chiếm 2,502ms trong khi `generation` chỉ mất 149ms).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  Trong LLMOps, prompt không đơn thuần là văn bản mà đóng vai trò như mã nguồn định hình hành vi và tài nguyên tiêu thụ. Một prompt dài hoặc kém tối ưu có thể làm tăng số lượng token, kéo theo chi phí tăng gấp nhiều lần và làm suy giảm độ trễ (TTFT tăng). Việc quản lý prompt theo phiên bản, liên kết với trace và thiết lập SLO giúp đội ngũ vận hành theo dõi sát sao mức tiêu hao ngân sách lỗi (Error Budget), đồng thời cung cấp khả năng Rollback tức thì về phiên bản trước khi phát hiện prompt mới gây regression.
- **Điều quan trọng nhất đã học:**
  Hiểu rõ toàn diện bức tranh vận hành một hệ thống AI thực tế: từ việc bảo vệ quyền riêng tư người dùng (PII scrubbing), theo dõi phân tán đa tầng (Distributed Tracing), đến việc định nghĩa mục tiêu định lượng (SLO/SLI) và quy trình điều tra sự cố bài bản dựa trên bằng chứng dữ liệu định lượng thay vì phỏng đoán.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  Trong bài lab hiện tại, LLM và vector store đang là các thành phần mô phỏng (FakeLLM và in-memory mock). Bước phát triển tiếp theo có thể kết nối với mô hình thương mại thực tế và cụm vector database phân tán để quan sát thêm các yếu tố về mạng (network jitter) và streaming token.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Có đúng 3 file text và 5 ảnh runtime theo hướng dẫn.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
