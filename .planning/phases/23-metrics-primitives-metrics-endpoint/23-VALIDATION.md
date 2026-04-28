# Phase 23 — VALIDATION (Nyquist contract)

Mapping each requirement to its observable test (Nyquist principle: every requirement has a test that would fail if the requirement is violated).

| Req ID | Requirement | Test file → test name | Type | Notes |
|---|---|---|---|---|
| **OBS-07** | `/metrics` endpoint expose Prometheus-format metrics qua `prometheus-fastapi-instrumentator` | `tests/test_observability/test_metrics_endpoint.py::test_metrics_endpoint_returns_200_with_correct_content_type` | integration | Asserts status=200, header `text/plain; version=0.0.4; charset=utf-8` |
| **OBS-07** | (continued) — exposes default `http_request_duration_seconds` histogram | `tests/test_observability/test_metrics_endpoint.py::test_metrics_endpoint_exposes_default_http_histogram` | integration | Body contains `http_request_duration_seconds_bucket` lines after a request |
| **OBS-08** | Module-level metric primitives định nghĩa: `http_*`, `op_*`, `cache_*`, `db_query_*`, `pipeline_step_*`, `dq_*` | `tests/test_observability/test_metrics.py::test_metrics_module_level_import_does_not_raise` | unit | `import localstock.observability.metrics` succeeds |
| **OBS-08** | (continued) — primitives có thể gọi từ outside | `tests/test_observability/test_metrics.py::test_init_metrics_returns_all_primitive_families` | unit | Returned dict has keys covering all 6 families |
| **OBS-08** | (continued) — namespace prefix `localstock_` (D-01) | `tests/test_observability/test_metrics.py::test_metrics_namespace_prefix` | unit | All custom (non-instrumentator-default) metrics start with `localstock_` |
| **OBS-08** | (continued) — pipeline buckets per D-03 | `tests/test_observability/test_metrics.py::test_pipeline_step_histogram_buckets` | unit | Asserts `localstock_pipeline_step_duration_seconds` has expected bucket boundaries `(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)` |
| **OBS-09** | Cardinality budget — KHÔNG metric nào declare label `symbol` | `tests/test_observability/test_metrics.py::test_no_metric_has_symbol_label` | unit | Walks `registry._names_to_collectors`, asserts no collector's `_labelnames` contains `"symbol"` |
| **OBS-09** | (continued) — label sets match D-06 budget | `tests/test_observability/test_metrics.py::test_label_schema_matches_budget` | unit | Per-family expected labelnames frozen as fixture, asserted set-equality |
| **OBS-10** | Idempotent registry init — không lỗi `Duplicated timeseries` khi gọi nhiều lần | `tests/test_observability/test_metrics.py::test_init_metrics_idempotent_on_same_registry` | unit | `init_metrics(reg); init_metrics(reg)` does not raise; second call returns same collector instances |
| **OBS-10** | (continued) — pytest collection không lỗi `Duplicated timeseries` | (entire `tests/test_observability/test_metrics*.py` files run cleanly with function-scoped `metrics_registry` fixture) | system | No dedicated assertion — coverage by fixture isolation |

---

## Coverage table — Success Criteria → Test

| Roadmap Success Criterion | Tests covering it |
|---|---|
| 1. `GET /metrics` → 200 + `text/plain; version=0.0.4` + `http_request_duration_seconds` | `test_metrics_endpoint_returns_200_with_correct_content_type`, `test_metrics_endpoint_exposes_default_http_histogram` |
| 2. Module primitives import được mà không raise | `test_metrics_module_level_import_does_not_raise`, `test_init_metrics_returns_all_primitive_families` |
| 3. Test suite không lỗi `Duplicated timeseries in CollectorRegistry` | `test_init_metrics_idempotent_on_same_registry` + `metrics_registry` fixture isolation |
| 4. Không metric label `symbol`; cardinality ≤ 50 series/metric | `test_no_metric_has_symbol_label`, `test_label_schema_matches_budget` |

---

## Sampling adequacy (Nyquist)

- 4 requirements × ≥1 test each = 8 distinct test cases (≥2× sampling rate)
- Both unit (no I/O) and integration (TestClient) layers covered
- Negative test (`test_no_metric_has_symbol_label`) ensures violations FAIL — not just smoke
- Idempotent test exercises the actual failure mode (`Duplicated timeseries` would raise on second register without guard)

---

## Out of scope (per D-08)

- `@observe` decorator coverage → Phase 24 validation
- Slow query log → Phase 24
- Health endpoint split → Phase 25

No `.inc()/.observe()/.set()` calls in service code introduced this phase, so no service-level metric assertion tests required.
