## 26-03 — Out-of-scope discoveries

- **test_market_route.py::TestMarketSummaryResponse::test_endpoint_calls_repo** fails in full-suite run but passes in isolation. Root cause: 26-04 wrapped `/market/summary` with `get_or_compute`, so cached results from prior tests bypass the mock the test installs. **Owner: 26-04** (or downstream cache-isolation fixture). Not introduced by 26-03 (versioning + repo only). Verified by re-running tests/test_market_route.py alone (8/8 pass) at HEAD f208c4a (just 26-04, no 26-03 commits).
- **test_db/test_migration_24_pipeline_durations.py::test_migration_downgrade_removes_columns** — pre-existing Phase-24 failure, documented as ignored by 26-01/02/03 prompts.
