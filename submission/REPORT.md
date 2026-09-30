# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Chỉ cần 3 output text và 5 ảnh runtime; dùng đường dẫn tương đối, ví dụ `evidence/03-incident-trace.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Hữu Đức
- **MSSV:** 2A202602459
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/J4ck13Ch4n/K4-L3B-Day13-Monitoring-LLMOps
- **Commit SHA cuối:** `30b70f1db9f55851aad8622f58082cf42590f157` (commit chứa toàn bộ source và evidence; commit kế tiếp chỉ ghi SHA này vào report)
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602459`

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

### Evidence theo `docs/SCREENSHOT_GUIDE.md`

Các file dưới đây đặt tên theo hướng dẫn chụp evidence mới; nhiều mục dùng lại cùng ảnh chụp ở bảng trên (cùng nội dung, khác tên).

| Mục guide | File | Nguồn |
|---|---|---|
| 01 pytest | `evidence/01-pytest.txt` | output lệnh `python -m pytest -q` |
| 02 log validator | `evidence/02-log-validator.txt` | output `scripts/validate_logs.py` |
| 03 dashboard validator | `evidence/03-dashboard-validator.txt` | output `scripts/validate_dashboard.py` |
| 04 structured log | `evidence/04-structured-log.png` | `data/logs.jsonl` |
| 05 PII redaction | `evidence/05-pii-redaction.png` | `data/logs.jsonl`: `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` kèm `correlation_id` |
| 06 trace list | `evidence/06-trace-list.png` | Langfuse, 32 trace |
| 07 trace waterfall | `evidence/07-trace-waterfall.png` | Langfuse Timeline, `retrieval` 2.50s |
| 08 trace metadata | `evidence/08-trace-metadata.png` | Langfuse, `correlation_id`, prompt, token, cost |
| 09 prompt versions | `evidence/09-prompt-versions.png` | Langfuse, `day13-chat` v1/v2 |
| 10 prompt rollback | `evidence/10-prompt-rollback.png` | trace `production` v2 + trang versions sau rollback; trace ID ở mục 5 |
| 11 dashboard overview | `evidence/11-dashboard-overview.png` | `scripts/dashboard_server.py`, 60 phút |
| 12 incident metric | `evidence/12-incident-metric.png` | `scripts/dashboard_server.py`, 240 phút, P95 4420ms |
| 13 incident log | `evidence/13-incident-log.png` | `req-b714a2b0` |
| 14 incident trace | `evidence/14-incident-trace.png` | trace `871694390b94865518a8c447284dc3db` |

> `05-dashboard-incident.png` là ảnh chụp dashboard chạy thật `scripts/dashboard_server.py` (đọc trực tiếp `data/logs.jsonl`, 6 panel theo `config/dashboard.yaml`, time range 60 phút, refresh 30s). Các ảnh 01–04 phải tự chụp từ VS Code / Langfuse theo `docs/SUBMISSION.md` mục 5.3.

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | chưa đạt (TODO CP1) | 100/100 | đủ correlation, enrichment, 0 PII leak |
| `validate_dashboard.py` | HỢP LỆ 6/6 (contract sẵn) | HỢP LỆ 6/6 | giữ nguyên 6 panel contract |
| `pytest` | 22 passed | 22 passed | xem `evidence/pytest.txt` |
| Số traces hợp lệ | 0 | ≥10 traces trên Langfuse: 28 trace root trong ảnh 02 (10 baseline + 5 challenge + các lần chạy thử), 32 trace sau khi tạo thêm trace `production`/`baseline`/`candidate` | kiểm tra ảnh 02 |
| Số PII leak | - | 0 | sample queries có email/phone/thẻ giả đều bị redact |
| Latency P95 / TTFT P95 | - | overall P50=152ms P95=20335ms (lẫn 1 request cold-start 20s sau restart); incident window 5/5 requests 2651–2652ms; TTFT P95=50ms | cold-start là request đầu sau restart (fetch prompt); incident vượt ngưỡng 2000ms |
| Retrieval success rate | - | 100% (tool_success=true, error_rate=0%) | incident rag_slow chỉ chậm, không lỗi |

Môi trường chạy: Python 3.14 trên Windows với `pydantic>=2.12` (bản pin `pydantic==2.11.4` không build được trên 3.14; trên Python 3.11 dùng `requirements.txt` nguyên bản). Chi tiết workload cuối: 15 `response_sent`, quality_mean=0.867, cost_total=0.0288 USD, tokens_in=524, tokens_out=1817.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `app/middleware.py` — `clear_contextvars()` đầu request; nhận `x-request-id` nếu khớp `^req-[0-9a-fA-F]{8}$` (lowercase) else sinh `req-<uuid4hex[:8]>`; `bind_contextvars(correlation_id=...)`; lưu `request.state.correlation_id`; trả về header `x-request-id` + `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `app/main.py` bind trước `request_received`: `user_id_hash` (sha256[:12] của `user_id`), `session_id`, `feature`, `model` (từ `agent.model`), `env` (từ `APP_ENV`). `response_sent` thêm `latency_ms, ttft_ms, tokens_in/out, cost_usd, quality_score, tool_name=retrieval, tool_success`. Nhờ `merge_contextvars` mọi log trong request đều có các field này.
- **Cách bảo đảm PII được scrub trước khi ghi:** `app/logging_config.py` đăng ký `scrub_event` trước `JsonlFileProcessor` và `JSONRenderer`. `scrub_event` duyệt đệ quy mọi string trong `event_dict` qua `pii.scrub_text`. `pii.py` có rule email, `phone_vn` (0/+84, chấp nhận space/dot/dash), `credit_card` (4x4 digits), `cccd` (12 digits), `passport_vn`. `summarize_text` cũng scrub trước khi đưa vào `message_preview/answer_preview`.
- **Cách kiểm chứng kết quả:** xóa `data/logs.jsonl`, restart API, `load_test.py` (sample có email/phone/thẻ giả) → `validate_logs.py` 100/100, `grep` không còn PII thô, chỉ còn `[REDACTED_*]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** mở project `day13-k4-l3b-2A202602459` → Traces → time range chứa lần chạy challenge; ảnh 02 phải thấy tên project + ≥10 dòng trace mới (không dùng trace người khác).
- **Cấu trúc root/retrieval/generation observations:** `app/agent.py` — root `@observe(name=lab-agent-run, as_type=agent)` + trace `day13-agent-request`; child `retrieval` (`as_type=retriever`, metadata `doc_count/query_preview/correlation_id`) bọc `retrieve()`; child `llm-generation` (`as_type=generation`, `model/prompt/usage_details/cost_details`, input/output preview đã scrub) bọc `FakeLLM.generate()`. `_observation_context/_safe_update_*` fallback `nullcontext` nên stub client trong test vẫn pass.
- **Cách nối trace với log:** cùng `correlation_id` (vd `req-b714a2b0`) xuất hiện trong `data/logs.jsonl` và trong trace metadata; `propagate_attributes` gắn `correlation_id/feature/model` ở root và `prompt` ở generation.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** version 1 / label `baseline` (resolve `source=langfuse`)
- **Version/label candidate:** version 2 / label `candidate` (resolve `source=langfuse`)
- **Trace ID của mỗi version:** `baseline` v1 = `b94692257211e573e9b04cf13a4be031` (`correlation_id=req-aed3e007`); `candidate` v2 = `27540059735e371ecfea1dc9bd3b1f00` (`correlation_id=req-a7eac3c7`); `production` v2 (sau promote) = `c2fb89434545a8b7b195bfc3d1c12175` (`correlation_id=req-b2ab8db4`).
- **Cách promote và rollback `production`:** trên Langfuse chuyển label `production` v1→v2, chạy 1 request (`production,v2`), rồi chuyển `production` v2→v1 (rollback), chụp ảnh 04 gồm trace `production,v2` bên trái + trang versions (v1 có `baseline+production`, v2 có `candidate`) bên phải.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `config/dashboard.yaml` (contract) + runtime `evidence/05-dashboard-incident.png` render từ `data/logs.jsonl`: Latency (P50/P95/P99+TTFT, ms, thresh p95≤3000), Traffic (req/min, ≥1), Errors (error%+retrieval success, ≤2%), Cost (USD, total≤2.5), Tokens (tổng in/out, ≤50000), Quality (mean 0–1, ≥0.75). Time range 60m.
- **SLO và lý do chọn:** `config/slo.yaml` — `fast_successful_requests`: `response_sent AND latency_ms<=3000` trên tổng `request_received`, target 99.5% window 28d. Chọn vì khớp threshold latency panel và ngưỡng challenge 2000–3000ms; TTFT và quality làm guardrail phụ.
- **Cách tính error budget:** SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO.
- **Ba alert và runbook tương ứng:** `config/alert_rules.yaml` + `docs/alerts.md` — `HighLatencyP95` (warning, p95>3000ms 5m), `HighErrorRate` (critical, err>2% hoặc retr<90% 5m), `LowQualityProxy` (warning, mean<0.75 10m); channel Slack `#k4-l3b-alerts`; runbook mỗi alert đều 3 bước dashboard → lọc log lấy `correlation_id` → mở trace so span.

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1 (cohort K4, seed 1312, incident `rag_slow`, affected_feature `monitoring`, threshold 2000ms)
- **Khoảng thời gian điều tra:** từ `request_received` challenge đầu đến `response_sent` challenge cuối trong `data/logs.jsonl` (5 requests challenge sau 10 requests baseline; xem timestamp trong ảnh 01/05)
- **Triệu chứng từ metrics:** dashboard panel Latency: baseline ~151ms, challenge window 5/5 requests 2651–2652ms (P95 incident ≫ 2000ms); TTFT P95=50ms bình thường; Errors panel: error_rate=0%, retrieval_success=100% (không lỗi, chỉ chậm); Quality/Cost không bất thường.
- **Log line và correlation ID liên quan:** `event=response_sent correlation_id=req-b714a2b0 session_id=k4-l3b-challenge-s04 feature=monitoring latency_ms=2652 ttft_ms=50 quality_score=0.9 cost_usd=0.001941 tool_success=true` (dòng `request_received` cùng ID có `message_preview="Which signal should be checked after latency increases?"`).
- **Trace ID và span gây ảnh hưởng:** trace `871694390b94865518a8c447284dc3db` (cùng `correlation_id=req-b714a2b0`, tổng 2.65s) — span `retrieval` duration ~2500ms (chậm), span `llm-generation` ~150ms bình thường, `prompt_name=day13-chat production v1`.
- **Root cause:** `STATE["rag_slow"]=True` (bật qua `POST /incidents/rag_slow/enable` từ `config/challenge.json`) khiến `app/mock_rag.py:retrieve()` `sleep(2.5s)` với mọi query → latency cộng ~2.5s vào mọi challenge request, TTFT và error không đổi nên loại trừ LLM/prompt.
- **Fix action:** `python scripts/inject_incident.py --disable` (tương đương `POST /incidents/rag_slow/disable`) — đã chạy, `/health` về `rag_slow:false`.
- **Preventive measure:** alert `HighLatencyP95` (p95>3000ms 5m → Slack `#k4-l3b-alerts` + runbook `docs/alerts.md#alert-1`); guardrail SLO latency trong CI/load test (fail nếu P95 challenge >2000ms).

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** dùng child observation lồng trong root thay vì log thủ công — vì chỉ span tree mới tách được 2.5s retrieval khỏi 0.15s generation khi TTFT bình thường; log đơn lẻ không làm được.
- **Một lỗi/blocker đã gặp:** `.env` ban đầu để `LANGFUSE_PROMPT_NAME=day13-mlops` → 404 `Prompt not found`, trace `local-fallback`; request đầu sau restart 20s (cold-start fetch prompt).
- **Cách tìm nguyên nhân và xử lý:** đọc `/tmp` uvicorn log thấy 404 prompt + `resolve_prompt` trả `local-fallback`; đổi về `day13-chat`, tạo đủ labels `baseline/candidate/production`, restart API → cả 3 labels resolve `source=langfuse`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics (P95 latency spike, TTFT flat) khoanh triệu chứng + window; Logs (lọc `response_sent` chậm → 1 `correlation_id`); Traces (cùng ID → span `retrieval` chậm nhất) → kết luận, không đoán mò.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** prompt là config ảnh hưởng quality/latency/cost nên phải version + label + rollback như code; token/cost phát hiện cost_spike; SLO/error budget biến "chậm bao nhiêu là xấu" thành số (ở đây 2000–3000ms); rollback `production` v2→v1 là mitigation nhanh nhất khi version mới gây regression.
- **Điều quan trọng nhất đã học:** incident chậm-nhưng-không-lỗi (slow-no-error) chỉ bắt được bằng tail latency + span timing, không bắt bằng error rate.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** dashboard (ảnh 05) là web app local tự viết `scripts/dashboard_server.py`, chưa dùng Grafana; cold-start 20s của request đầu làm P99 lớn; ảnh 04 ghép 2 ảnh chụp thật (trace `production` v2 bên trái, trang versions sau rollback bên phải) do không đặt được hai cửa sổ cạnh nhau; ảnh 01 chụp từ `data/logs.jsonl` mở trong trình duyệt (không phải VS Code); giá trị `public_key` trên ảnh 03/04 đã được che.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Có đúng 3 file text và 5 ảnh runtime theo hướng dẫn.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
