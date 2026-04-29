# Observability

Tài liệu vận hành cho stack observability của LocalStock (logging Phase 22 +
Prometheus metrics Phase 23). Audience: operator chạy app trên máy local
hoặc đang cân nhắc deploy.

## Logging

Cấu hình bởi `localstock.observability.logging.configure_logging()` —
structured JSON logs qua loguru, có correlation ID gắn theo request và
contextualization theo `run_id` cho pipeline jobs. Xem
`docs/DEVELOPMENT.md` §Backend cho lệnh chạy uvicorn; log level đặt qua biến
môi trường `LOG_LEVEL` (mặc định `INFO`).

Source: `apps/prometheus/src/localstock/observability/logging.py`.

## Metrics — Prometheus

Phase 23 expose Prometheus metrics qua HTTP endpoint:

| Property | Value |
|---|---|
| Endpoint path | `GET /metrics` |
| Content-Type | `text/plain; version=0.0.4; charset=utf-8` |
| Auth | **None** (local-first, xem cảnh báo bên dưới) |
| OpenAPI schema | Ẩn (`include_in_schema=False`) |
| Library | [`prometheus-fastapi-instrumentator`](https://github.com/trallnag/prometheus-fastapi-instrumentator) v7.1+ |
| Direct Prometheus client | `prometheus-client` v0.21+ |

### Metric families
- **Default (instrumentator)**: `http_request_duration_seconds`,
  `http_requests_total`, `http_requests_inprogress`, response/request size
  summaries — giữ nguyên tên gốc của library (CONTEXT.md D-01 exception).
- **Custom (`localstock_` prefix)**: HTTP, op (business operations), cache,
  DB query, pipeline step, data quality. Định nghĩa trong
  `apps/prometheus/src/localstock/observability/metrics.py`. Phase 23 chỉ
  khai báo primitives — Phase 24 mới gắn instrumentation calls (increment /
  observe) vào service code.

### Quick check
```bash
# App đang chạy ở localhost:8000
curl -s http://localhost:8000/metrics | head -20
```
Bạn sẽ thấy các dòng dạng `# HELP …`, `# TYPE …` và các bucket
`http_request_duration_seconds_bucket{...}`.

## ⚠ Security warning — `/metrics` is public-on-localhost

Phase 23 cố tình **không** thêm auth cho `/metrics`. Quyết định này (CONTEXT.md
D-02) chỉ an toàn trong deployment local-first hiện tại — app bind localhost,
chỉ developer truy cập.

**Không được expose port 8000 ra public network mà không có reverse-proxy
auth layer** (nginx basic auth, Cloudflare Access, Tailscale ACL, v.v.).
Nếu thiếu, bất kỳ ai trên internet đều có thể:
- Đọc histogram latency → fingerprint hệ thống, đoán mô hình traffic
- Dò endpoint thật qua label `handler` (cardinality bị giới hạn nhưng vẫn lộ
  shape của router)
- Tạo DoS bằng scrape liên tục (cấu hình `should_ignore_untemplated=True` đã
  giảm rủi ro cardinality, nhưng không miễn dịch flooding)

**Khi cần hardening (deploy production)**:
1. Reverse proxy với basic auth hoặc mTLS — recommended
2. FastAPI dependency check `request.client.host in {"127.0.0.1", "::1"}` —
   acceptable cho on-prem
3. Network-level allowlist (firewall) — minimum bar

Hardening item **chưa scope vào Phase 23** — xem backlog
"Auth/IP allowlist for `/metrics`" trong CONTEXT.md "Out of scope".

## Cardinality budget (D-06)

Mỗi metric primitive khai báo label set rõ ràng và **không** có label `symbol`
(ticker → dùng structured logs). Ngân sách dự kiến:

| Family prefix | Labels | Upper bound (estimated series) |
|---|---|---|
| `localstock_http_*` | `method, status_class` | 25 |
| `localstock_op_*` | `domain, subsystem, action, outcome` | ~40 |
| `localstock_cache_*` | `cache_name, [reason]` | ~20 |
| `localstock_db_query_*` | `query_type, table_class, [outcome]` | ~16 |
| `localstock_pipeline_step_*` | `step, outcome` | ~8 |
| `localstock_dq_*` | `validator, severity\|outcome` | ~20 |

Test `test_no_metric_has_symbol_label` enforce ràng buộc này tại CI time.

## Coming next — Future phases

- **Phase 24** — wire `@observe` decorator + DB query timing instrumentation
  vào service layer (sử dụng primitives đã khai báo Phase 23).
- **Phase 25** — split health endpoints (`/health/live` vs `/health/ready`) +
  thêm scheduled health probe job.
- **Backlog** — Auth / IP allowlist cho `/metrics` khi deploy production
  (trigger: bất kỳ deploy non-localhost nào).

## References
- `apps/prometheus/src/localstock/api/app.py` — wiring + Instrumentator config
- `apps/prometheus/src/localstock/observability/metrics.py` — primitives + `init_metrics()`
- `apps/prometheus/src/localstock/observability/logging.py` — loguru config + correlation ID
- `.planning/phases/23-metrics-primitives-metrics-endpoint/23-CONTEXT.md` — locked decisions D-01..D-08
- `.planning/phases/22-logging-foundation/` — logging foundation phase summary
