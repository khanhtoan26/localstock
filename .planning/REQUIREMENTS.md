# Requirements — Milestone v1.5: Performance & Data Quality

**Goal:** Tối ưu toàn diện pipeline (tốc độ, độ tin cậy, observability) để hệ thống chạy nhanh hơn, ít lỗi hơn, và dễ chẩn đoán khi có sự cố — không thêm feature mới cho user.

**Scope principle:** Single-process, single-user, local-first. Sáu thư viện thuần Python, không thêm dịch vụ ngoài (no Redis, no Celery, no OTel collector). Đo trước, tối ưu sau.

**Phase order:** A → B → C → D → E → F → G (dependency-driven; instrumentation precedes optimization).

---

## v1.5 Requirements (Active)

### Observability — Logging (Phase A)

- [x] **OBS-01
**: Backend logs emitted as structured JSON (loguru `serialize=True` + `enqueue=True`) thay cho f-string lines
- [ ] **OBS-02**: Mỗi HTTP request được gắn `request_id` (CorrelationIdMiddleware) và propagate qua contextvar vào mọi log
- [x] **OBS-03
**: Mỗi pipeline run được gắn `run_id` qua `logger.contextualize(run_id=...)`, hiển thị trong toàn bộ log của run đó
- [ ] **OBS-04**: Request log middleware ghi method, path, status, duration_ms cho mỗi request
- [x] **OBS-05
**: Secret/PII redaction patcher cho `Settings` — không log token/API key/URL có credentials
- [ ] **OBS-06**: CI lint rule: zero f-string log lines (`grep 'logger\.[a-z]*(f"'` returns 0)

### Observability — Metrics & /metrics (Phase B)

- [ ] **OBS-07**: `/metrics` endpoint expose Prometheus-format metrics qua `prometheus-fastapi-instrumentator`
- [ ] **OBS-08**: Module-level metric primitives định nghĩa: `http_*`, `op_*`, `cache_*`, `db_query_*`, `pipeline_step_*`, `dq_*`
- [ ] **OBS-09**: Label cardinality budget tuân thủ ≤50 series per metric — `symbol` KHÔNG xuất hiện làm label (chỉ trong logs)
- [ ] **OBS-10**: Idempotent registry init — không lỗi `Duplicated timeseries` khi chạy test suite

### Observability — Instrumentation & Health (Phase C)

- [ ] **OBS-11**: `@observe("domain.subsystem.action")` decorator (timing + log + Prometheus histogram) áp dụng lên service methods + scheduler jobs
- [ ] **OBS-12**: `@timed_query` decorator + SQLAlchemy `before/after_cursor_execute` events ghi DB query duration
- [ ] **OBS-13**: Slow query log (queries > 250 ms) emit log + counter
- [ ] **OBS-14**: `/health/live`, `/health/ready`, `/health/pipeline`, `/health/data` tách từ endpoint `/health` hiện tại
- [ ] **OBS-15**: `health_self_probe` scheduler job (30s) populate gauges: DB pool size, `last_pipeline_age_seconds`, last successful crawl count
- [ ] **OBS-16**: APScheduler `EVENT_JOB_ERROR` listener emit counter + Telegram alert khi scheduled job fail
- [ ] **OBS-17**: Per-stage timing trên `PipelineRun` table: crawl/analyze/score/report durations persisted

### Data Quality (Phase D)

- [ ] **DQ-01**: Tier 1 validators (block per-symbol) — pandera schemas reject corrupt OHLCV: negative price, future date, NaN ratio > threshold, duplicate (symbol,date) PK
- [ ] **DQ-02**: Tier 2 advisory validators (warn + metric, no block): RSI > 99.5, gap > 30%, missing rows > 20%
- [ ] **DQ-03**: Shadow mode mặc định 14 ngày cho Tier 2 rules trước khi cho phép promote sang Tier 1 (operational policy documented)
- [ ] **DQ-04**: NaN/Inf sanitizer ở JSONB write boundary — `df.replace([±inf], NaN).where(notna(), None)` áp dụng trước mọi insert vào JSONB column
- [ ] **DQ-05**: Per-stock try/except isolation trong pipeline — một mã fail KHÔNG kill batch (`return_exceptions=True`)
- [ ] **DQ-06**: `PipelineRun.stats` JSONB column ghi succeeded/failed/skipped count + danh sách failed symbol
- [ ] **DQ-07**: Stale-data detection — `/health/data` so sánh `MAX(date)` với trading-calendar; flag nếu lệch > 1 phiên
- [ ] **DQ-08**: Quarantine table cho rejected rows — không silently drop, có thể inspect/replay sau

### Caching (Phase E)

- [ ] **CACHE-01**: In-process `cachetools.TTLCache` áp dụng cho `/api/scores/ranking` + `/api/market/summary` + service-layer indicator computations
- [ ] **CACHE-02**: Cache key bao gồm `pipeline_run_id` (hoặc `latest_ohlcv_date`) — không bao giờ chỉ TTL cho scoring outputs
- [ ] **CACHE-03**: `cache.invalidate_namespace(...)` gọi từ `automation_service.py` sau mỗi write phase
- [ ] **CACHE-04**: Single-flight wrapper (`asyncio.Lock` per key) — chống cold-start stampede
- [ ] **CACHE-05**: Pre-warm hot keys ở cuối `run_daily_pipeline` — không lazy-fill từ first request sau pipeline
- [ ] **CACHE-06**: `cache_janitor` scheduler job (60s) sweep expired TTLs để tránh unbounded memory growth
- [ ] **CACHE-07**: Cache hit/miss/eviction counters expose qua `/metrics`

### Pipeline Performance (Phase F)

- [ ] **PERF-01**: Crawler refactor `asyncio.Semaphore(8)` + `gather(..., return_exceptions=True)` cho concurrent crawl (gated empirically)
- [ ] **PERF-02**: Per-source token-bucket (`aiolimiter`) + circuit breaker (3 consecutive 429s → cool-off) cho vnstock client
- [ ] **PERF-03**: `tenacity` exponential backoff + jitter retry decorator trên mọi external HTTP call site
- [ ] **PERF-04**: `pandas-ta` (sync, CPU-bound) wrap trong `asyncio.to_thread(...)` để không block event loop
- [ ] **PERF-05**: SQLAlchemy pool tuning — `pool_size=10, max_overflow=10, pool_timeout=5, pool_pre_ping=True` (preserve `prepared_statement_cache_size=0`)
- [ ] **PERF-06**: Telegram digest send chuyển sang fire-and-forget background task — không block pipeline completion

### Database Optimization (Phase G)

- [ ] **DB-01**: Composite btree indexes via `CREATE INDEX CONCURRENTLY` Alembic migrations (non-transactional): `stock_prices(symbol, date DESC)`, `pipeline_runs(started_at DESC)`, `stock_scores(date, symbol)` — exact set xác định từ slow-query log p95 outliers
- [ ] **DB-02**: Repository batch upsert via `INSERT … ON CONFLICT … DO UPDATE` thay cho per-row insert/update loop
- [ ] **DB-03**: Migration runbook: index migrations chạy NGOÀI cửa sổ pipeline (15:30–16:30) — documented trong CONTRIBUTING/runbook
- [ ] **DB-04**: pg_stat_statements enabled trên Supabase dashboard, baseline top-N slow statements snapshot lúc start và end milestone (manual, không tự động poll)

---

## Future Requirements (Deferred to v1.6+)

- HTTP-layer caching qua `hishel` cho httpx clients (vnstock/news) — skip v1.5
- Persisted indicator results table — replace TTLCache khi schema ổn định
- Backfill CLI / admin button cho flagged-by-DQ symbols
- Admin observability dashboard (`/admin/observability` Helios page) — last 30 runs, slow-query top-10, freshness panel
- Automated `pg_stat_statements` polling + alert threshold
- ProcessPoolExecutor cho indicator computation (only nếu profiling chứng minh CPU-bound sau Semaphore(8))
- GIN index trên `report.content_json` (only khi JSONB-key queries become a pattern)
- Automated `EXPLAIN ANALYZE` capture tooling
- Redis cache backend adapter (only nếu multi-process trở nên thật)
- `diskcache` persistent tier (only khi cold-start cost rõ ràng đau)

---

## Out of Scope (Explicitly Excluded)

- **Redis / Memcached infra** — single-process, không có process thứ hai để share cache; YAGNI
- **Celery / RQ task queue** — APScheduler in-process đã đủ cho 1 daily job + ad-hoc triggers
- **OpenTelemetry full stack (collector + exporter)** — pull-based `/metrics` đã đủ; tránh agent overhead
- **Sentry / external error tracking** — vi phạm data sovereignty + local-only constraint
- **Great Expectations framework** — pandera nhẹ hơn nhiều, đủ cho DataFrame-shape validation
- **Time-series partitioning (pg_partman)** — chỉ ~500k rows; defer cho đến > 10M rows
- **TimescaleDB / Citus extensions** — Supabase free tier không cho phép
- **BRIN indexes trên stock_prices** — btree composite nhanh hơn ở scale hiện tại
- **Distributed tracing (Jaeger/Zipkin)** — single-process, không có cross-service hops
- **Per-symbol Prometheus labels** — cardinality explosion (~18k+ series) — symbols belong in logs
- **Multi-process workers** — single uvicorn worker giữ scheduler binding đơn giản
- **Prometheus push-gateway** — sync push blocks event loop; pull-only

---

## Traceability

(Filled by gsd-roadmapper khi tạo ROADMAP.md.)

| REQ-ID | Phase | Plan(s) | Status |
|--------|-------|---------|--------|
| OBS-01 | Phase 22 | TBD | Pending |
| OBS-02 | Phase 22 | TBD | Pending |
| OBS-03 | Phase 22 | TBD | Pending |
| OBS-04 | Phase 22 | TBD | Pending |
| OBS-05 | Phase 22 | TBD | Pending |
| OBS-06 | Phase 22 | TBD | Pending |
| OBS-07 | Phase 23 | TBD | Pending |
| OBS-08 | Phase 23 | TBD | Pending |
| OBS-09 | Phase 23 | TBD | Pending |
| OBS-10 | Phase 23 | TBD | Pending |
| OBS-11 | Phase 24 | TBD | Pending |
| OBS-12 | Phase 24 | TBD | Pending |
| OBS-13 | Phase 24 | TBD | Pending |
| OBS-14 | Phase 24 | TBD | Pending |
| OBS-15 | Phase 24 | TBD | Pending |
| OBS-16 | Phase 24 | TBD | Pending |
| OBS-17 | Phase 24 | TBD | Pending |
| DQ-01  | Phase 25 | TBD | Pending |
| DQ-02  | Phase 25 | TBD | Pending |
| DQ-03  | Phase 25 | TBD | Pending |
| DQ-04  | Phase 25 | TBD | Pending |
| DQ-05  | Phase 25 | TBD | Pending |
| DQ-06  | Phase 25 | TBD | Pending |
| DQ-07  | Phase 25 | TBD | Pending |
| DQ-08  | Phase 25 | TBD | Pending |
| CACHE-01 | Phase 26 | TBD | Pending |
| CACHE-02 | Phase 26 | TBD | Pending |
| CACHE-03 | Phase 26 | TBD | Pending |
| CACHE-04 | Phase 26 | TBD | Pending |
| CACHE-05 | Phase 26 | TBD | Pending |
| CACHE-06 | Phase 26 | TBD | Pending |
| CACHE-07 | Phase 26 | TBD | Pending |
| PERF-01 | Phase 27 | TBD | Pending |
| PERF-02 | Phase 27 | TBD | Pending |
| PERF-03 | Phase 27 | TBD | Pending |
| PERF-04 | Phase 27 | TBD | Pending |
| PERF-05 | Phase 27 | TBD | Pending |
| PERF-06 | Phase 27 | TBD | Pending |
| DB-01 | Phase 28 | TBD | Pending |
| DB-02 | Phase 28 | TBD | Pending |
| DB-03 | Phase 28 | TBD | Pending |
| DB-04 | Phase 28 | TBD | Pending |

**Coverage:** 42/42 v1.5 requirements mapped ✓ (no orphans, no duplicates)

---

*Last updated: 2026-04-28 — v1.5 Performance & Data Quality milestone defined*
