---
phase: 26
slug: caching
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for Phase 26 (Caching). Closes ROADMAP
> Success Criteria #1–#5. Framework already exists (pytest 8.x +
> pytest-asyncio + pytest-timeout); `cachetools>=5,<6` is the new dep
> installed in 26-01 Task 1.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (auto mode) + pytest-timeout (30s) |
| **Config file** | `apps/prometheus/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd apps/prometheus && uv run pytest tests/test_cache/ -x -q` |
| **Versioning + repo** | `cd apps/prometheus && uv run pytest tests/test_cache/test_versioning.py tests/test_db/test_pipeline_run_repo.py -x -q` |
| **Full suite command** | `cd apps/prometheus && uv run pytest -x -q` |
| **Estimated runtime** | ~30 s quick · ~3 min full (perf tests dominate at ~5s each) |

No new test framework dependency added — `pytest-benchmark` deliberately
avoided per RESEARCH §1 Q-4 in favour of stdlib `time.perf_counter` +
`statistics.quantiles`.

---

## Sampling Rate

- **After every task commit:** quick run on touched test file
- **After every plan wave:** full cache suite + lint
- **Before `/gsd-verify-work`:** full project suite must be green
- **Max feedback latency:** 30 s (quick) · 180 s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-00 | 01 | 1 (Wave 0) | (B2 fixture prereq) | n/a | shared async fixtures (`db_session`, `async_client`) in `tests/conftest.py` | unit | `uv run pytest tests/test_dq/ -q` | ✅ created here | ⬜ pending |
| 26-01-01 | 01 | 1 | CACHE-04 | T-26-01-01 | cachetools dep + settings + RED scaffolds | unit | `uv run pytest tests/test_cache/ -q --collect-only` | ❌ created here | ⬜ pending |
| 26-01-02 | 01 | 1 | CACHE-04 (SC #3) | T-26-01-02..05 | InstrumentedTTLCache + single-flight + get_or_compute | unit | `uv run pytest tests/test_cache/test_single_flight.py tests/test_cache/test_registry.py tests/test_cache/test_invalidate.py -x -q` | ✅ from 26-01-01 | ⬜ pending |
| 26-02-01 | 02 | 1 | CACHE-07 (SC #5 metrics) | T-26-02-03 | 5 cache counters with cache_name label only | unit | `uv run pytest tests/test_cache/test_metrics_exposed.py -x -q` | ✅ created here | ⬜ pending |
| 26-02-02 | 02 | 1 | CACHE-07 (SC #1 header) | T-26-02-01..04 | CacheHeaderMiddleware emits X-Cache hit/miss | unit | `uv run pytest tests/test_cache/test_middleware.py -x -q` | ✅ created here | ⬜ pending |
| 26-03-01 | 03 | 2 | CACHE-02 | T-26-03-02 | PipelineRunRepository.get_latest_completed | integration | `uv run pytest tests/test_db/test_pipeline_run_repo.py -x -q` | ✅ created here | ⬜ pending |
| 26-03-02 | 03 | 2 | CACHE-02 (SC #2) | T-26-03-01,T-26-03-03 | resolve_latest_run_id + 5s TTL + version-bump test | integration | `uv run pytest tests/test_cache/test_versioning.py -x -q` | ✅ created here | ⬜ pending |
| 26-04-01 | 04 | 2 | CACHE-01 | T-26-04-01,T-26-04-04 | /scores/top + /market/summary wrapped in get_or_compute; ROADMAP doc fix | static | `uvx ruff check src/localstock/api/routes/scores.py src/localstock/api/routes/market.py && ! grep -n '/api/scores/ranking' .planning/ROADMAP.md` | n/a | ⬜ pending |
| 26-04-02 | 04 | 2 | CACHE-01 (SC #1) | T-26-04-02 | p95 < 50ms hot path + miss→hit→miss-after-invalidate | perf | `uv run pytest tests/test_cache/test_perf_ranking.py tests/test_cache/test_perf_market.py tests/test_cache/test_route_caching_integration.py -x -q` | ✅ created here | ⬜ pending |
| 26-04-03 | 04 | 2 | CACHE-01 (W1) | T-26-04-01 | extract `build_market_summary(session)` data-builder helper for pre-warm reuse | static | `uv run pytest tests/test_api/ tests/test_cache/test_perf_market.py tests/test_cache/test_route_caching_integration.py -x -q` | n/a | ⬜ pending |
| 26-05-01 | 05 | 3 | CACHE-03 | T-26-05-01 | 4 invalidate hooks in automation_service.py | integration | `uv run pytest tests/test_cache/test_invalidation_integration.py -x -q` | ✅ created here | ⬜ pending |
| 26-05-02 | 05 | 3 | CACHE-05 (SC #4) | T-26-05-02,T-26-05-03 | prewarm_hot_keys via get_or_compute; first user request is hit | integration | `uv run pytest tests/test_cache/test_prewarm.py -x -q` | ✅ created here | ⬜ pending |
| 26-05-03 | 05 | 3 | CACHE-05 (D-06) | T-26-05-04,T-26-05-05 | indicator cache wrapper at analyze_technical_single | unit | `uv run pytest tests/test_cache/test_indicator_cache.py -x -q` | ✅ created here | ⬜ pending |
| 26-06-01 | 06 | 4 | CACHE-06 (SC #5) | T-26-06-01..03 | cache_janitor 60s sweep + log + reason='expire' counter | unit + scheduler | `uv run pytest tests/test_cache/test_janitor.py -x -q` | ✅ created here | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Plan → Success Criterion Closure Map

| SC | Verbatim Text | Closing Plan | Closing Test |
|----|---------------|--------------|--------------|
| **#1** | `/api/scores/ranking` lần thứ 2 (cùng `pipeline_run_id`) trả về < 50 ms p95 với header/log `cache=hit`; lần đầu sau pipeline write `cache=miss` | **26-04** | `test_perf_ranking.py::test_ranking_cache_hit_p95_under_50ms` |
| **#2** | Cache key cho scoring outputs include `pipeline_run_id` — verified bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data, không cần đợi TTL | **26-03** | `test_versioning.py::test_new_pipeline_run_invalidates_old_keys` |
| **#3** | Concurrent 100 requests vào cùng cold key chỉ trigger 1 backend computation (single-flight via `asyncio.Lock`) — verified bằng counter `cache_compute_total` chỉ tăng 1 | **26-01** | `test_single_flight.py::test_concurrent_cold_key_single_compute` |
| **#4** | Sau `run_daily_pipeline`, cache cho hot keys (ranking + market summary) đã pre-warm — first request từ user log `cache=hit` không phải `miss` | **26-05** | `test_prewarm.py::test_prewarm_fills_ranking_and_market_summary` |
| **#5** | `/metrics` expose `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` với label `namespace`; `cache_janitor` job chạy mỗi 60s và log số entries swept | **26-06** | `test_janitor.py::test_janitor_*` (+ supporting `test_metrics_exposed.py` from 26-02) |

Note on SC #5 label: ROADMAP says `namespace`; CONTEXT D-08 ratification
(2026-04-29) settled on `cache_name` to match existing `metrics.py`
scaffolding. Concept matches; only the column header differs.

---

## Plan → Requirement Closure Map

| Req ID | Closing Plan | Tests |
|--------|--------------|-------|
| CACHE-01 | 26-04 | `test_perf_ranking`, `test_perf_market`, `test_route_caching_integration` |
| CACHE-02 | 26-03 | `test_versioning`, `test_pipeline_run_repo` |
| CACHE-03 | 26-05 | `test_invalidation_integration` |
| CACHE-04 | 26-01 | `test_single_flight`, `test_registry`, `test_invalidate` |
| CACHE-05 | 26-05 | `test_prewarm`, `test_indicator_cache` |
| CACHE-06 | 26-06 | `test_janitor` |
| CACHE-07 | 26-02 | `test_metrics_exposed`, `test_middleware` |

Every requirement closed by exactly one plan. Every SC closed by exactly
one plan.

---

## Wave 0 Requirements

Wave 0 work is folded into 26-01 — Task 0 (B2 fix) lands shared async
test fixtures BEFORE any cache code, and Task 1 lands the cache package
skeleton + RED tests. After 26-01 lands, set `wave_0_complete: true` and
`nyquist_compliant: true` in this file's frontmatter.

**26-01 Task 0 (Wave-0 prerequisite — B2 fix):**

- [ ] `apps/prometheus/tests/conftest.py` — adds project-wide async
      fixtures: `db_session` (SQLAlchemy AsyncSession, transactional
      rollback, gated by `requires_pg`) and `async_client`
      (`httpx.AsyncClient` over `ASGITransport(app=create_app())`).
- [ ] `apps/prometheus/tests/test_dq/test_quarantine_repo.py` — drops
      its file-local `db_session` (lines 22-50); now relies on the
      project-wide fixture. Existing DQ test outcomes must match
      pre-refactor (`uv run pytest tests/test_dq/ -q`).

This Wave-0 task UNBLOCKS:

- 26-03 `test_pipeline_run_repo`, `test_versioning` (use `db_session`)
- 26-04 `test_perf_ranking`, `test_perf_market`,
      `test_route_caching_integration` (use `async_client` + `db_session`)
- 26-05 `test_prewarm` (uses `db_session`)

Without it, those test modules raise `fixture '<name>' not found` at
collection time — Nyquist violation.

**26-01 Task 1 — RED test scaffolds (cache package):**

Test files created in 26-01 Task 1 (RED → GREEN within same plan):

- [ ] `tests/test_cache/__init__.py`
- [ ] `tests/test_cache/conftest.py` (autouse cleanup of `_locks` + caches)
- [ ] `tests/test_cache/test_single_flight.py` — CACHE-04 (SC #3)
- [ ] `tests/test_cache/test_registry.py` — D-02 + Q-2 evictions
- [ ] `tests/test_cache/test_invalidate.py` — D-04

Test files created later (each in their owning plan):

- [ ] `tests/test_cache/test_metrics_exposed.py` — 26-02 (CACHE-07)
- [ ] `tests/test_cache/test_middleware.py` — 26-02 (SC #1 header)
- [ ] `tests/test_db/test_pipeline_run_repo.py` — 26-03 (CACHE-02)
- [ ] `tests/test_cache/test_versioning.py` — 26-03 (SC #2)
- [ ] `tests/test_cache/test_perf_ranking.py` — 26-04 (SC #1)
- [ ] `tests/test_cache/test_perf_market.py` — 26-04
- [ ] `tests/test_cache/test_route_caching_integration.py` — 26-04
- [ ] `tests/test_cache/test_invalidation_integration.py` — 26-05 (CACHE-03)
- [ ] `tests/test_cache/test_prewarm.py` — 26-05 (SC #4)
- [ ] `tests/test_cache/test_indicator_cache.py` — 26-05 (D-06)
- [ ] `tests/test_cache/test_janitor.py` — 26-06 (SC #5)

Infrastructure created in 26-01 Task 1:

- [ ] `pyproject.toml` — `cachetools>=5,<6` added
- [ ] `localstock/config.py` — 6 new cache settings
- [ ] `localstock/cache/{__init__,registry,single_flight,invalidate,_context}.py` — package skeleton

(No DB schema change; no new Alembic migration required for Phase 26.)

---

## Dependency Graph

```
Wave 1 (parallel, no within-wave file conflicts)
  ├── 26-01: cache core + single-flight + InstrumentedTTLCache  (CACHE-04, SC #3)
  └── 26-02: metrics + middleware + contextvar                  (CACHE-07)

Wave 2 (parallel; both depend on Wave 1)
  ├── 26-03: PipelineRunRepository + version-key resolver       (CACHE-02, SC #2)
  └── 26-04: route wrapping + perf test + ROADMAP doc fix       (CACHE-01, SC #1)
      depends on 26-01 + 26-02 + 26-03

Wave 3 (depends on Waves 1+2)
  └── 26-05: invalidate hooks + prewarm + indicator cache       (CACHE-03/05, SC #4)

Wave 4 (depends on Wave 1; can parallel with Wave 3)
  └── 26-06: cache_janitor scheduler job                        (CACHE-06, SC #5)
```

File-conflict matrix verified zero overlaps within each wave (RESEARCH §6).

---

## Manual-Only Verifications

*All phase behaviors have automated verification.* The only manual
sanity check (optional) is curl-against-running-app:

```bash
# After deployment, observe X-Cache header progression:
curl -s -i 'http://localhost:8000/api/scores/top?limit=20' | grep -i X-Cache  # → miss
curl -s -i 'http://localhost:8000/api/scores/top?limit=20' | grep -i X-Cache  # → hit

# /metrics exposes the 5 counters:
curl -s 'http://localhost:8000/metrics' | grep -E 'localstock_cache_(hits|misses|evictions|compute|prewarm_errors)_total'

# Cache janitor log every 60s:
journalctl -u prometheus-app -f | grep cache.janitor.sweep
```

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify (✅ all 12 task rows above resolve to commands)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (✅)
- [ ] Wave 0 covers all MISSING references (✅ — folded into 26-01 Task 1)
- [ ] No watch-mode flags (✅ — all `pytest -q`, no `--ff` / `--watch`)
- [ ] Feedback latency < 30 s (quick) / 180 s (full) (✅)
- [ ] Every SC #1..#5 closed by exactly one plan (✅ — see SC closure map)
- [ ] Every CACHE-01..07 closed by exactly one plan (✅ — see Req closure map)
- [ ] `nyquist_compliant: true` to be set after 26-01 lands.

**Approval:** pending
