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
- SLI/SLO liên quan: SLO `fast_successful_requests` — `p95(response_sent.latency_ms) <= 3000ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: người dùng chờ lâu mới nhận được câu trả lời, TTFT tăng theo
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Latency, xác nhận P95/P99/TTFT P95 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó (`event == "response_sent"`), lấy một `correlation_id` có `latency_ms` cao nhất.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh span `retrieval` vs `llm-generation` để xác định bước chậm.
- Mitigation tạm thời: rollback prompt `production` về version ổn định nếu generation chậm sau promote; tắt scenario `rag_slow` nếu retrieval chậm; giảm concurrency khi demo.
- Owner: `student`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` — `error_rate_pct <= 2%`, guardrail `retrieval_success_rate >= 90%`
- Điều kiện và thời gian duy trì: `count(request_failed)/count(request_received)*100 > 2%` hoặc `retrieval_success_rate < 90%` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: request trả 500 hoặc RAG không tìm được context, chất lượng trả lời rớt
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Errors, xem error_rate, breakdown theo `error_type` và `tool_success_rate`.
  2. Lọc `data/logs.jsonl` `event == "request_failed"`, lấy `correlation_id` + `error_type` + `tool_name`.
  3. Mở trace cùng `correlation_id`, kiểm tra span lỗi (thường là `retrieval` khi `Vector store timeout`).
- Mitigation tạm thời: tắt scenario `tool_fail` nếu đang practice; rollback config/prompt liên quan; kiểm tra `/metrics` `error_breakdown`.
- Owner: `student`

## Alert 3

- Tên: `LowQualityProxy`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: guardrail `quality_score_avg >= 0.75` trên `response_sent.quality_score`
- Điều kiện và thời gian duy trì: `mean(quality_score) < 0.75` liên tục trong 10 phút
- Ảnh hưởng tới người dùng: câu trả lời ngắn/cụt, thiếu context, dù chưa lỗi 500
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Quality + Tokens/Cost để xem quality giảm có kèm token/cost bất thường không.
  2. Lọc `data/logs.jsonl` `event == "response_sent"`, lấy `correlation_id` có `quality_score` thấp nhất và xem `answer_preview`.
  3. Mở trace cùng `correlation_id`, đối chiếu `prompt_name/version/label`, `doc_count` và output generation.
- Mitigation tạm thời: rollback prompt `production` về `baseline` nếu version mới làm quality giảm; kiểm tra retrieval có trả `No domain document matched` không.
- Owner: `student`
