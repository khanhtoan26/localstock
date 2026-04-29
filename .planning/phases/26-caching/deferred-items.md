## 26-03 — Out-of-scope discoveries

- **test_market_route.py::TestMarketSummaryResponse::test_endpoint_calls_repo** fails in full-suite run but passes in isolation. Root cause: 26-04 wrapped `/market/summary` with `get_or_compute`, so cached results from prior tests bypass the mock the test installs. **Owner: 26-04** (or downstream cache-isolation fixture). Not introduced by 26-03 (versioning + repo only). Verified by re-running tests/test_market_route.py alone (8/8 pass) at HEAD f208c4a (just 26-04, no 26-03 commits).
  - **RESOLVED in 26-04 (commit `3bc02f1`):** `tests/test_cache/conftest.py` extended to clear cache + dispose singleton DB engine post-test; route helper switched from `session_factory`-based to per-request-`session`-based `resolve_latest_run_id` to avoid touching the singleton at all. Full-suite passes 588/588 (this entry only); see 26-04-SUMMARY.md §Deviations Rule 1.
- **test_db/test_migration_24_pipeline_durations.py::test_migration_downgrade_removes_columns** — pre-existing Phase-24 failure, documented as ignored by 26-01/02/03 prompts.

## 26-05 ruff F401 — pre-existing unused imports (out of scope)

- `apps/prometheus/src/localstock/services/automation_service.py:25` — `format_sector_rotation`
- `apps/prometheus/src/localstock/services/analysis_service.py:25` — `VN_INDUSTRY_GROUPS`
- `apps/prometheus/src/localstock/services/analysis_service.py:36` — `StockPrice`

All three predate Phase 26; not introduced by 26-05. Auto-fixable with `ruff check --fix`.
