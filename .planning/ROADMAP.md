# Roadmap: LocalStock

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-04-16) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 UX Polish & Educational Depth** — Phases 7-10 (shipped 2026-04-21) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Admin Console** — Phases 11-13 (shipped 2026-04-23) — [Archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 UI/UX Refinement** — Phases 14-17 (shipped 2026-04-25) — [Archive](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 AI Analysis Depth** — Phases 18-21 (shipped 2026-04-28) — [Archive](milestones/v1.4-ROADMAP.md)
- 🚧 **v1.5 Performance & Data Quality** — Phases 22-28 (started 2026-04-28)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-04-16</summary>

- [x] Phase 1: Foundation & Data Pipeline (4/4 plans) — completed 2026-04-14
- [x] Phase 2: Technical & Fundamental Analysis (4/4 plans) — completed 2026-04-14
- [x] Phase 3: Sentiment Analysis & Scoring Engine (4/4 plans) — completed 2026-04-15
- [x] Phase 4: AI Reports, Macro Context & T+3 Awareness (4/4 plans) — completed 2026-04-15
- [x] Phase 5: Automation & Notifications (3/3 plans) — completed 2026-04-15
- [x] Phase 6: Web Dashboard (4/4 plans) — completed 2026-04-16

</details>

<details>
<summary>✅ v1.1 UX Polish & Educational Depth (Phases 7-10) — SHIPPED 2026-04-21</summary>

- [x] Phase 7: Theme Foundation & Visual Identity (4/4 plans) — completed 2026-04-20
- [x] Phase 8: Stock Page Reading-First Redesign (merged into Phase 7) — completed 2026-04-20
- [x] Phase 9: Academic/Learning Page & Glossary Data (2/2 plans) — completed 2026-04-20
- [x] Phase 10: Interactive Glossary Linking (2/2 plans) — completed 2026-04-21

</details>

<details>
<summary>✅ v1.2 Admin Console (Phases 11-13) — SHIPPED 2026-04-23</summary>

- [x] Phase 11: Admin API Endpoints (2/2 plans) — completed 2026-04-22
- [x] Phase 12: Admin Console UI (2/2 plans) — completed 2026-04-22
- [x] Phase 12.1: Performance & Polish (2/2 plans) — completed 2026-04-23
- [x] Phase 13: AI Report Generation UI (2/2 plans) — completed 2026-04-23

</details>

<details>
<summary>✅ v1.3 UI/UX Refinement (Phases 14-17) — SHIPPED 2026-04-25</summary>

- [x] Phase 14: Visual Foundation — Source Sans 3 font + warm neutral color palette (1/1 plans) — completed 2026-04-24
- [x] Phase 15: Sidebar Redesign — Claude Desktop floating card sidebar (3/3 plans) — completed 2026-04-24
- [x] Phase 16: Table, Search & Session Bar — Sort fix, search filter, HOSE session bar (6/6 plans) — completed 2026-04-25
- [x] Phase 17: Market Overview Metrics — Live 4-card market summary + backend API (4/4 plans) — completed 2026-04-25

</details>

<details>
<summary>✅ v1.4 AI Analysis Depth (Phases 18-21) — SHIPPED 2026-04-28</summary>

- [x] Phase 18: Signal Computation (4/4 plans) — completed 2026-04-26
- [x] Phase 19: Prompt & Schema Restructuring (3/3 plans) — completed 2026-04-28
- [x] Phase 20: Service Wiring & Report Content (2/2 plans) — completed 2026-04-28
- [x] Phase 21: Frontend Trade Plan Display (2/2 plans) — completed 2026-04-28

</details>

<details open>
<summary>🚧 v1.5 Performance & Data Quality (Phases 22-28) — IN PROGRESS</summary>

- [ ] **Phase 22: Logging Foundation** — Structured JSON logs với request_id/run_id correlation, secret redaction, CI lint gate
- [x] **Phase 23: Metrics Primitives & /metrics** — Prometheus registry + endpoint, label-cardinality budget, idempotent init
- [x] **Phase 24: Instrumentation & Health** — `@observe`/`@timed_query` decorators, slow-query log, /health/{live,ready,pipeline,data}, scheduler error listener
- [x] **Phase 25: Data Quality** — Pandera Tier 1 validators, NaN/Inf JSONB sanitizer, per-stock isolation, stats persistence, quarantine table
- [ ] **Phase 26: Caching** — `cachetools.TTLCache` với version-aware keys, single-flight lock, invalidation hooks, pre-warm, janitor job
- [ ] **Phase 27: Pipeline Performance** — `asyncio.Semaphore(8)` crawler, token-bucket + circuit breaker, tenacity retries, pool tuning, fire-and-forget Telegram
- [ ] **Phase 28: Database Optimization** — `CREATE INDEX CONCURRENTLY` migrations, batch upserts, `pg_stat_statements` baseline, runbook

</details>

## Phase Details

### Phase 22: Logging Foundation
**Goal**: Mọi log line từ backend là structured JSON, có thể grep/correlate theo request hoặc pipeline run, không leak secrets — nền tảng debug cho tất cả phase sau.
**Depends on**: Nothing (foundational; phải có trước Phase 23 vì failures ở metrics layer cần logs để chẩn đoán — research §"A → B → C is non-negotiable")
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, OBS-06
**Success Criteria** (what must be TRUE):
  1. Mỗi log line emit từ backend là valid JSON (parse được bằng `jq`), kể cả error/exception traces — verified bằng `tail -f logs/*.log | jq .` không lỗi
  2. Mỗi HTTP request có `request_id` UUID xuất hiện trong tất cả log line phát sinh từ request đó (request log + service log + repo log)
  3. Pipeline run hiển thị `run_id` trong toàn bộ log của run (crawl/analyze/score/report) — grep `run_id=<uuid>` trả về toàn bộ chuỗi log của 1 run
  4. Settings dump hoặc exception chứa token/URL có credentials được redact (`***`) trước khi log — verified bằng test inject fake secret
  5. CI fail nếu có f-string log line: `grep -rE 'logger\.[a-z]+\(f"' src/` returns 0
**Plans**: 7 plans
- [ ] 22-00-PLAN.md — Wave 0 test scaffolds + lint script skeleton (Nyquist setup; RED tests for OBS-01..06)
- [ ] 22-01-PLAN.md — Core observability package (configure_logging, redaction patcher, InterceptHandler, contextvars) — OBS-01, OBS-05
- [ ] 22-02-PLAN.md — Pydantic Settings log_level field_validator (fail-fast on bad value) — OBS-01
- [ ] 22-03-PLAN.md — CorrelationId + RequestLog middleware + api/app.py wiring + global handler logging — OBS-02, OBS-04
- [ ] 22-04-PLAN.md — Pipeline run_id contextualize + scheduler lifespan configure_logging — OBS-03
- [ ] 22-05-PLAN.md — F-string log call sweep across ~30 remaining files — OBS-01, OBS-06
- [ ] 22-06-PLAN.md — Pre-commit hook + GitHub Actions lint workflow (OBS-06 gate enforcement)

### Phase 23: Metrics Primitives & /metrics Endpoint
**Goal**: Prometheus registry và `/metrics` endpoint sẵn sàng; module-level metric primitives định nghĩa với label schema có giới hạn cardinality — chuẩn bị bề mặt instrumentation cho Phase 24.
**Depends on**: Phase 22 (Logging) — failures trong registry init cần logs để debug; research §"B depends on A"
**Requirements**: OBS-07, OBS-08, OBS-09, OBS-10
**Success Criteria** (what must be TRUE):
  1. `GET /metrics` trả về 200 với content-type `text/plain; version=0.0.4`, expose default `http_request_duration_seconds` histogram của instrumentator
  2. Module-level primitives `http_*`, `op_*`, `cache_*`, `db_query_*`, `pipeline_step_*`, `dq_*` import được từ `src/observability/metrics.py` mà không raise
  3. Test suite chạy đủ pytest collection không lỗi `Duplicated timeseries in CollectorRegistry` (idempotent init verified)
  4. Không có metric nào declare label `symbol` — verified bằng grep + unit test scan `_metrics` dict; cardinality mỗi metric ≤ 50 series ở runtime
**Plans**: TBD

### Phase 24: Instrumentation & Health
**Goal**: Service methods, scheduler jobs, DB queries, và HTTP layer đều emit metrics + structured timing log; health endpoints tách thành 4 probe rõ ràng cho ops; scheduler errors không còn bị nuốt.
**Depends on**: Phase 23 (Metrics) — decorators cần registry; research §"C depends on B"
**Requirements**: OBS-11, OBS-12, OBS-13, OBS-14, OBS-15, OBS-16, OBS-17
**Success Criteria** (what must be TRUE):
  1. `@observe("crawl.ohlcv.fetch")`-decorated call xuất hiện trong `/metrics` dưới `op_duration_seconds{op="crawl.ohlcv.fetch"}` và emit 1 log line `op_complete` với `duration_ms` field
  2. Query > 250 ms emit log `slow_query` + tăng counter `db_query_slow_total` — verified bằng injected `pg_sleep(0.3)` query
  3. `/health/live` luôn 200 nếu process up; `/health/ready` 503 nếu DB pool unhealthy; `/health/pipeline` trả `last_pipeline_age_seconds`; `/health/data` trả freshness của `MAX(stock_prices.date)`
  4. APScheduler job raise exception → counter `scheduler_job_errors_total{job_id=...}` tăng + Telegram alert gửi (verified với fault-injected job)
  5. `PipelineRun` row sau mỗi run có cột `crawl_duration_ms`, `analyze_duration_ms`, `score_duration_ms`, `report_duration_ms` populated (non-null)
**Plans**: TBD

### Phase 25: Data Quality
**Goal**: Pipeline reject corrupt rows ở boundary thay vì silent-corrupt downstream; một symbol fail không kill batch; rejected rows quarantine để inspect; `/health/data` flag stale data — phải xong trước parallelism (research §"D before F").
**Depends on**: Phase 24 (Instrumentation) — DQ outcomes phải observable qua `dq_*` metrics + logs trước khi enforce
**Requirements**: DQ-01, DQ-02, DQ-03, DQ-04, DQ-05, DQ-06, DQ-07, DQ-08
**Success Criteria** (what must be TRUE):
  1. Pandera Tier 1 reject row OHLCV với negative price / future date / NaN ratio > threshold / duplicate `(symbol,date)` PK — row đi vào `quarantine_rows` table thay vì `stock_prices`
  2. JSONB write boundary chuyển `±Inf` và `NaN` thành SQL `NULL` — verified bằng injected DataFrame có inf, sau insert `report.content_json` không chứa string `"NaN"` hoặc `"Infinity"`
  3. Pipeline với 1 mã inject lỗi (raise trong crawler) hoàn thành full run; `PipelineRun.stats` JSONB hiển thị `{succeeded: 399, failed: 1, failed_symbols: ["BAD"]}` thay vì abort
  4. Tier 2 advisory rules (RSI > 99.5, gap > 30%, missing > 20%) emit log `dq_warn` + counter `dq_violations_total{rule, tier="advisory"}` nhưng KHÔNG block — shadow mode flag default true
  5. `/health/data` trả status `stale` khi `MAX(stock_prices.date)` lệch trading-calendar > 1 phiên — verified bằng manual rollback date
**Plans**: 8 plans
- [x] 25-01-PLAN.md — Wave 0 scaffolds: pandera install + dq/ package + Alembic migration + Settings + metric + RED test scaffolds
- [x] 25-02-PLAN.md — DQ-04 sanitize_jsonb + repo wiring (closes SC #2)
- [x] 25-03-PLAN.md — DQ-08 QuarantineRepository + APScheduler cleanup cron
- [x] 25-04-PLAN.md — DQ-06 PipelineRun.stats dual-write + _truncate_error
- [x] 25-05-PLAN.md — DQ-01 OHLCVSchema + reject-to-quarantine in _crawl_prices (closes SC #1)
- [x] 25-06-PLAN.md — DQ-05 per-symbol try/except across services (closes SC #3)
- [x] 25-07-PLAN.md — DQ-02 + DQ-03 Tier 2 dispatcher + shadow-mode promotion runbook (closes SC #4)
- [x] 25-08-PLAN.md — DQ-07 /health/data stale extension (closes SC #5)

### Phase 26: Caching
**Goal**: Hot read-paths (`/api/scores/ranking`, `/api/market/summary`, indicator computations) trả về < 50 ms p95 từ cache, invalidate đúng lúc pipeline ghi xong, không stampede khi cache cold — phải có invalidation hooks trước Phase 27 (research §"E before F").
**Depends on**: Phase 24 (Instrumentation) — cache hit/miss metrics cần registry; coexist với Phase 25 shadow-mode
**Requirements**: CACHE-01, CACHE-02, CACHE-03, CACHE-04, CACHE-05, CACHE-06, CACHE-07
**Success Criteria** (what must be TRUE):
  1. `/api/scores/ranking` lần thứ 2 (cùng `pipeline_run_id`) trả về < 50 ms p95 với header/log `cache=hit`; lần đầu sau pipeline write `cache=miss`
  2. Cache key cho scoring outputs include `pipeline_run_id` — verified bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data, không cần đợi TTL
  3. Concurrent 100 requests vào cùng cold key chỉ trigger 1 backend computation (single-flight via `asyncio.Lock`) — verified bằng counter `cache_compute_total` chỉ tăng 1
  4. Sau `run_daily_pipeline`, cache cho hot keys (ranking + market summary) đã pre-warm — first request từ user log `cache=hit` không phải `miss`
  5. `/metrics` expose `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` với label `namespace`; `cache_janitor` job chạy mỗi 60s và log số entries swept
**Plans**: 26-01 ✅ (CACHE-04 — cache core + single-flight + Wave-0 fixtures + canonical cache_compute_total; SC #3 ✅ closed); 26-02/03/04/05/06 pending

### Phase 27: Pipeline Performance
**Goal**: Toàn bộ pipeline (crawl + analyze + score + report cho ~400 mã) hoàn thành nhanh hơn baseline ≥ 3× nhờ concurrent crawl, không trigger vnstock soft-ban, không exhaust DB pool, không block event loop bằng pandas-ta.
**Depends on**: Phase 24 (measure the win), Phase 25 (DQ catch corruption mà concurrency amplify), Phase 26 (cache invalidation hooks tồn tại trước khi restructure write boundaries) — research §"F depends on C, D, E"
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06
**Success Criteria** (what must be TRUE):
  1. Daily pipeline end-to-end duration giảm ≥ 3× so với baseline đo ở cuối Phase 24 — verified bằng `pipeline_duration_seconds` histogram trước/sau
  2. Crawler dùng `asyncio.Semaphore(8) + gather(return_exceptions=True)` + per-source `aiolimiter` token-bucket; vnstock không trả 429 trong 5 lần chạy liên tiếp; circuit breaker mở sau 3 consecutive 429s
  3. Mọi external HTTP call site được wrap bằng `@retry` (tenacity, exponential backoff + jitter, max 3 attempts) — verified bằng injected transient 503 → request thành công sau retry
  4. `pandas-ta` chạy qua `asyncio.to_thread` — verified bằng event-loop lag metric không spike khi compute indicators cho 400 mã (loop responsive < 100 ms)
  5. SQLAlchemy pool tuning áp dụng (`pool_size=10, max_overflow=10, pool_timeout=5, pool_pre_ping=True`, giữ `prepared_statement_cache_size=0`); pipeline 15:30 không log `QueuePool limit ... overflow` lỗi
  6. Telegram digest send là background task (không await trong pipeline finalize) — pipeline marks complete trước khi Telegram message đi
**Plans**: TBD

### Phase 28: Database Optimization
**Goal**: P95 query duration trên hot paths (`stock_prices` time-series read, `pipeline_runs` listing, `stock_scores` ranking) giảm rõ rệt nhờ composite indexes chọn từ slow-query metrics; bulk upsert thay per-row writes; runbook ngăn migration chạy trùng pipeline window.
**Depends on**: Phase 24 (slow-query log để chọn indexes), Phase 27 (parallel write workload để chọn upsert pattern) — research §"G last because it's lowest-leverage if everything else is right"
**Requirements**: DB-01, DB-02, DB-03, DB-04
**Success Criteria** (what must be TRUE):
  1. Top 3 slow queries từ `db_query_duration_seconds` p95 (đo cuối Phase 27) giảm ≥ 5× sau khi composite btree indexes apply — `stock_prices(symbol, date DESC)`, `pipeline_runs(started_at DESC)`, `stock_scores(date, symbol)` (set cuối cùng dẫn xuất từ data, không guess)
  2. Index migrations chạy với `CREATE INDEX CONCURRENTLY` trong file Alembic riêng có `op.execute(... )` + `transaction_per_migration=False` — không lock table khi apply trên Supabase
  3. Repository upsert path dùng `INSERT ... ON CONFLICT (symbol, date) DO UPDATE` cho 1 batch ≥ 100 rows; throughput ≥ 5× per-row loop baseline
  4. Runbook tài liệu (CONTRIBUTING.md hoặc docs/runbook.md) ghi rõ: index migrations chỉ chạy ngoài 15:30–16:30 UTC+7; có lệnh thực thi cụ thể; baseline + post-milestone snapshot từ `pg_stat_statements` lưu trong `.planning/milestones/v1.5-db-baseline.md`
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Data Pipeline | v1.0 | 4/4 | Complete | 2026-04-14 |
| 2. Technical & Fundamental Analysis | v1.0 | 4/4 | Complete | 2026-04-14 |
| 3. Sentiment Analysis & Scoring Engine | v1.0 | 4/4 | Complete | 2026-04-15 |
| 4. AI Reports, Macro Context & T+3 | v1.0 | 4/4 | Complete | 2026-04-15 |
| 5. Automation & Notifications | v1.0 | 3/3 | Complete | 2026-04-15 |
| 6. Web Dashboard | v1.0 | 4/4 | Complete | 2026-04-16 |
| 7. Theme Foundation & Visual Identity | v1.1 | 4/4 | Complete | 2026-04-20 |
| 8. Stock Page Reading-First Redesign | v1.1 | - | Complete (merged) | 2026-04-20 |
| 9. Academic/Learning Page & Glossary Data | v1.1 | 2/2 | Complete | 2026-04-20 |
| 10. Interactive Glossary Linking | v1.1 | 2/2 | Complete | 2026-04-21 |
| 11. Admin API Endpoints | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12. Admin Console UI | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12.1 Performance & Polish | v1.2 | 2/2 | Complete | 2026-04-23 |
| 13. AI Report Generation UI | v1.2 | 2/2 | Complete | 2026-04-23 |
| 14. Visual Foundation | v1.3 | 1/1 | Complete | 2026-04-24 |
| 15. Sidebar Redesign | v1.3 | 3/3 | Complete | 2026-04-24 |
| 16. Table, Search & Session Bar | v1.3 | 6/6 | Complete | 2026-04-25 |
| 17. Market Overview Metrics | v1.3 | 4/4 | Complete | 2026-04-25 |
| 18. Signal Computation | v1.4 | 4/4 | Complete | 2026-04-26 |
| 19. Prompt & Schema Restructuring | v1.4 | 3/3 | Complete | 2026-04-28 |
| 20. Service Wiring & Report Content | v1.4 | 2/2 | Complete | 2026-04-28 |
| 21. Frontend Trade Plan Display | v1.4 | 2/2 | Complete | 2026-04-28 |
| 22. Logging Foundation | v1.5 | 0/? | Not started | - |
| 23. Metrics Primitives & /metrics | v1.5 | 0/? | Not started | - |
| 24. Instrumentation & Health | v1.5 | 6/6 | Complete | 2026-04-29 |
| 25. Data Quality | v1.5 | 8/8 | Complete ✅ | All 5 SCs ✅; 25-08 closed SC #5 (data_freshness block on /health/data) |
| 26. Caching | v1.6 | 1/6 | In Progress | 26-01 ✅ CACHE-04 + SC #3 closed; 26-02/03/04 next (Wave 2 parallel) |
| 27. Pipeline Performance | v1.5 | 0/? | Not started | - |
| 28. Database Optimization | v1.5 | 0/? | Not started | - |

## Backlog

### Phase 999.1: Paper Trading Emulator (BACKLOG)

**Goal:** Giả lập mua/bán cổ phiếu (paper trading) để kiểm chứng độ chính xác của khuyến nghị AI. Người dùng đặt lệnh mua thử với số lượng tùy chọn, hệ thống theo dõi P&L theo thời gian thực để đánh giá nhận định đúng/sai.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
