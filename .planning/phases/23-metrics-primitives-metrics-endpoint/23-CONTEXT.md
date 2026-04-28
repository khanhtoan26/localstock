# Phase 23 — Metrics Primitives & /metrics Endpoint — CONTEXT

**Phase**: 23
**Goal** (from ROADMAP.md): Prometheus registry và `/metrics` endpoint sẵn sàng; module-level metric primitives định nghĩa với label schema có giới hạn cardinality — chuẩn bị bề mặt instrumentation cho Phase 24.
**Depends on**: Phase 22 (Logging Foundation) — failures trong registry init cần logs để debug.
**Requirements**: OBS-07, OBS-08, OBS-09, OBS-10
**Discussion mode**: `--auto` (recommendations locked by agent, user delegated all 8 gray areas)

---

## Locked Decisions

### D-01: Metric naming convention — namespace prefix `localstock_`

**Decision**: Tất cả custom metrics dùng prefix `localstock_` theo Prometheus naming convention `<namespace>_<subsystem>_<name>_<unit>`.

- ✅ `localstock_http_requests_total` (counter)
- ✅ `localstock_op_duration_seconds` (histogram)
- ✅ `localstock_cache_hits_total`, `localstock_cache_misses_total`
- ✅ `localstock_db_query_duration_seconds`
- ✅ `localstock_pipeline_step_duration_seconds`
- ✅ `localstock_dq_validation_failures_total`

**Exception**: `prometheus-fastapi-instrumentator` default metrics (`http_request_duration_seconds`, `http_requests_inprogress`) giữ nguyên tên gốc — không rewrite library defaults.

**Rationale**: Multi-app Prometheus setups cần namespace để grep/aggregate. Conventional và future-proof.

---

### D-02: `/metrics` endpoint protection — public on localhost, no auth

**Decision**: `/metrics` endpoint expose **public không auth** ở deployment local-first hiện tại.

- App chạy local (CLAUDE.md: "all running locally")
- Doc cảnh báo trong README/runbook: "Don't expose port 8000 to public network without reverse-proxy auth"
- Future hardening (nếu deploy production): wrap behind FastAPI dependency check `request.client.host in {127.0.0.1, ::1}` — defer to a backlog item, not this phase

**Rationale**: Aligned với project's local-first architecture. Avoid premature complexity.

---

### D-03: Histogram buckets — custom per metric category

**Decision**: Custom buckets phù hợp với phân phối thực tế của từng metric type:

```python
HTTP_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
DB_QUERY_BUCKETS     = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
PIPELINE_STEP_BUCKETS = (1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)  # seconds
OP_DURATION_BUCKETS  = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)  # generic
```

**Rationale**: Pipeline crawl/analyze chạy minute-scale; default Prometheus buckets (max 10s) sẽ overflow vào `+Inf`. DB queries thường sub-ms tới hundreds of ms.

---

### D-04: Idempotent registry init — explicit `init_metrics()` helper với try/except

**Decision**: Pattern hybrid:

1. Metrics định nghĩa **module-level** trong `localstock/observability/metrics.py` (Python module cache đảm bảo single init khi import path ổn định).
2. Cung cấp helper `init_metrics(registry: CollectorRegistry | None = None) -> dict[str, Metric]` để:
   - Test fixture có thể truyền fresh registry
   - Idempotent: nếu metric đã exist → catch `ValueError` và return existing collector từ `registry._names_to_collectors`
3. Pytest conftest fixture `metrics_registry` (function-scoped) tạo `CollectorRegistry()` mới mỗi test, prevent `Duplicated timeseries`.
4. Production: `init_metrics()` gọi 1 lần trong app lifespan startup (sau `configure_logging`).

**Rationale**: Module-level alone đủ cho production, nhưng pytest collection multiple imports (e.g., parallel tests) có thể trigger duplicate. Helper + fixture giải quyết cả hai.

---

### D-05: File structure — single `observability/metrics.py`

**Decision**: Single file với section comments cho v1.5:

```python
# === HTTP metrics ===
# === Operation metrics (op_*) ===
# === Cache metrics ===
# === DB query metrics ===
# === Pipeline step metrics ===
# === Data Quality metrics ===
```

Total expected: ~15-25 primitives. Không justify split sub-modules ở phase này.

**Future**: Nếu vượt ~40 primitives, split thành package `observability/metrics/` với `__init__.py` re-export.

---

### D-06: Label schema cardinality budget — bounded label sets

**Decision**: Mỗi metric primitive khai báo labels rõ ràng, **không có `symbol`** (dùng logs structured field thay thế per OBS-09).

| Metric prefix | Labels | Estimated cardinality |
|---|---|---|
| `localstock_http_*` | `method, status_class` (status_class ∈ 2xx/3xx/4xx/5xx) | 5 × 5 = 25 |
| `localstock_op_*` | `domain, subsystem, action, outcome` | ~20 ops × 2 outcomes = 40 |
| `localstock_cache_*` | `cache_name, operation` (op ∈ hit/miss/evict/expire) | ~5 × 4 = 20 |
| `localstock_db_query_*` | `query_type, table_class` (qt ∈ select/insert/update/delete; tc ∈ hot/cold) | 4 × 2 = 8 |
| `localstock_pipeline_step_*` | `step, outcome` (step ∈ crawl/analyze/score/report; outcome ∈ success/fail) | 4 × 2 = 8 |
| `localstock_dq_*` | `validator, severity` (severity ∈ block/warn) | ~10 × 2 = 20 |

**Enforcement**: Test `test_metrics_no_symbol_label` scan toàn bộ registry sau init, assert không có label name = `"symbol"`. Test `test_metrics_cardinality_budget` document expected upper bound (informational, not asserted at runtime).

---

### D-07: Instrumentator config — bounded defaults

**Decision**: `prometheus-fastapi-instrumentator.Instrumentator` config:

```python
Instrumentator(
    should_group_status_codes=True,        # gom 2xx/3xx/4xx/5xx → bound cardinality
    should_ignore_untemplated=True,        # bỏ raw URL không match route → tránh unbounded paths
    should_group_untemplated=True,         # untemplated paths → "untemplated"
    should_instrument_requests_inprogress=True,
    excluded_handlers=["^/metrics$", "^/health/live$"],  # anchored regex (instrumentator uses re.search) — avoid self-instrumentation noise without matching `/metrics-foo`
    inprogress_name="http_requests_inprogress",
    inprogress_labels=False,               # giảm label cardinality cho gauge
)
```

Default histogram of instrumentator (`http_request_duration_seconds`) giữ nguyên tên gốc (D-01 exception).

---

### D-08: Scope boundary với Phase 24 — KHÔNG instrument service code

**Decision**: Phase 23 chỉ:
1. Add deps `prometheus-client`, `prometheus-fastapi-instrumentator`
2. Tạo `localstock/observability/metrics.py` với module-level primitives + `init_metrics()` helper
3. Wire `Instrumentator().instrument(app).expose(app, endpoint="/metrics")` trong `api/app.py` lifespan
4. Tests: idempotent init, no `symbol` label, /metrics endpoint returns 200 + correct content-type
5. Update `observability/__init__.py` re-exports

Phase 23 **KHÔNG** thêm bất kỳ `.inc()`, `.observe()`, `.set()` call nào trong service/crawler/scheduler code. Phase 24 (`@observe` decorator) làm việc đó.

**Verification**: Grep `apps/prometheus/src/localstock/{services,crawlers,scheduler,api}/` cho `.inc(\|.observe(\|.set(` — không có occurrence mới sau phase 23.

---

## Requirements traceability

| Req ID | Description | Locked decision |
|---|---|---|
| OBS-07 | `/metrics` endpoint via prometheus-fastapi-instrumentator | D-02, D-07 |
| OBS-08 | Module-level primitives `http_*, op_*, cache_*, db_query_*, pipeline_step_*, dq_*` | D-01, D-05 |
| OBS-09 | Cardinality ≤50/metric, NO `symbol` label | D-06 |
| OBS-10 | Idempotent registry init | D-04 |

---

## Success Criteria (from ROADMAP)

1. `GET /metrics` → 200 + `text/plain; version=0.0.4`, expose default `http_request_duration_seconds` histogram
2. Module primitives import được mà không raise
3. Test suite không lỗi `Duplicated timeseries in CollectorRegistry`
4. Không metric nào declare label `symbol`; cardinality ≤ 50 series/metric ở runtime

---

## Out of scope (deferred)

- `@observe` decorator — Phase 24
- `@timed_query` decorator + SQLAlchemy events — Phase 24 (OBS-12)
- Slow query log — Phase 24 (OBS-13)
- `/health/live`, `/health/ready` split — Phase 25 (OBS-14)
- `health_self_probe` job — Phase 25 (OBS-15)
- Auth/IP allowlist cho `/metrics` — backlog (mention trong runbook)

---

## Notes for downstream agents

- **Researcher**: Focus vào (1) prometheus-fastapi-instrumentator API surface (`Instrumentator().instrument().expose()`); (2) `prometheus_client` registry/CollectorRegistry idempotency patterns; (3) làm sao test fixtures dùng fresh registry mà không leak state. Confirm version: pin `prometheus-fastapi-instrumentator>=7.0` (latest stable).
- **Planner**: Single Wave likely sufficient — primitives + endpoint + tests có thể parallelize 2 plans (W1: deps + metrics.py + tests; W2: app.py wiring + integration test). Aim ≤ 3 plans total.
- **Plan-checker**: Verify D-08 boundary explicitly — no `.inc()/.observe()` outside metrics.py + tests.
