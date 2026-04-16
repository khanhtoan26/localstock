---
phase: 05-automation-notifications
verified: 2026-04-16T15:25:00Z
status: human_needed
score: 5/5
overrides_applied: 0
human_verification:
  - test: "Trigger full pipeline and verify Telegram daily digest message is received"
    expected: "Telegram bot sends formatted HTML message with top stocks, score changes, and sector rotation"
    why_human: "Requires real Telegram bot token and chat ID to verify actual message delivery"
  - test: "Run full pipeline end-to-end with live database and market data"
    expected: "All 6 pipeline steps complete successfully, score changes detected, sector rotation computed, notifications sent"
    why_human: "Requires running PostgreSQL with seeded data, Ollama LLM service, and network access to Vietnamese data sources"
---

# Phase 5: Automation & Notifications Verification Report

**Phase Goal:** Fully automated daily pipeline that runs after market close and sends intelligent alerts via Telegram
**Verified:** 2026-04-16T15:25:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Full pipeline (crawl→analyze→score→report→notify) runs automatically every day after market close (after 15:30) without manual intervention | ✓ VERIFIED | `AutomationService.run_daily_pipeline()` orchestrates 6 steps + post-pipeline score change + sector rotation + notifications. `APScheduler` with `CronTrigger(hour=15, minute=45, day_of_week="mon-fri", timezone="Asia/Ho_Chi_Minh")` in `scheduler.py`. Lifespan integration in `app.py` via `get_lifespan`. 9 tests confirm pipeline orchestration behavior. |
| 2 | User can trigger on-demand analysis for a single ticker or full market scan | ✓ VERIFIED | `POST /api/automation/run` triggers full pipeline with `force=True`. `POST /api/automation/run/{symbol}` runs single-symbol analysis with regex validation `^[A-Z0-9]+$`. Both routes registered in `app.py`. Spot-check confirms routes: `['POST'] /api/automation/run`, `['POST'] /api/automation/run/{symbol}`, `['GET'] /api/automation/status`. |
| 3 | Telegram bot sends daily digest of top buy suggestions after each automated run | ✓ VERIFIED | `_send_notifications()` in `AutomationService` calls `format_daily_digest()` → `TelegramNotifier.send_message()`. Formatter produces Vietnamese HTML with top 10 stocks, scores, grades, emojis. Spot-check output: `"📊 LocalStock Daily Digest"`, `"🏆 Top Gợi ý mua"`. TelegramNotifier uses `python-telegram-bot` `Bot.send_message()` with `ParseMode.HTML`. |
| 4 | Telegram sends special alerts when significant score changes (>15 points) or strong signals are detected | ✓ VERIFIED | `detect_score_changes()` in `score_change_service.py` compares consecutive scoring dates, threshold from `Settings.score_change_threshold` (default 15.0). `format_score_alerts()` produces HTML with grade transitions (C→B) and delta values. `_send_notifications()` checks `score_changes` and sends alert via separate `notif_repo.log_notification("score_alert")`. 4 unit tests for score change detection, 7 for formatters. |
| 5 | System detects and reports sector rotation patterns — tracking money flow between industries over time | ✓ VERIFIED | `SectorService.compute_snapshot()` aggregates avg_score per industry group using `IndustryRepository.get_all_groups()` + `get_symbols_by_group()`. `get_rotation_summary()` classifies sectors as inflow (>2.0 change), outflow (<-2.0), or stable. `SectorSnapshot` model stores date, group_code, avg_score, avg_volume, stock_count. `format_sector_rotation()` produces Vietnamese output with 💰/📤 indicators. 3 sector rotation tests pass. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/localstock/services/automation_service.py` | Full pipeline orchestrator with notifications | ✓ VERIFIED | 278 lines. AutomationService with `run_daily_pipeline()` (6-step pipeline + score changes + sector rotation + notifications), `run_on_demand()`, `_run_single_symbol()`. Imports and uses all downstream services. |
| `src/localstock/scheduler/scheduler.py` | APScheduler with FastAPI lifespan | ✓ VERIFIED | 76 lines. AsyncIOScheduler with CronTrigger, `setup_scheduler()`, `get_lifespan()` async context manager. Misfire grace time 3600s. |
| `src/localstock/scheduler/calendar.py` | Vietnamese trading day detection | ✓ VERIFIED | 45 lines. `is_trading_day()` and `get_next_trading_day()` using `holidays.Vietnam`. Spot-check: Sunday=False, Monday=True, April 30 (Reunification Day)=False. |
| `src/localstock/services/score_change_service.py` | Score change detection >15pt | ✓ VERIFIED | 87 lines. `detect_score_changes()` async function. Uses `ScoreRepository.get_previous_date_scores()`, configurable threshold, returns sorted changes with direction. Handles Pitfall 5 (no previous data). |
| `src/localstock/services/sector_service.py` | Sector rotation tracking | ✓ VERIFIED | 144 lines. `SectorService` with `compute_snapshot()` and `get_rotation_summary()`. Aggregates avg_score per industry group, classifies inflow/outflow/stable. |
| `src/localstock/notifications/telegram.py` | Telegram message sending | ✓ VERIFIED | 89 lines. `TelegramNotifier` with `send_message()`, HTML parse mode, `_split_message()` at 4000 chars. Gracefully returns False when unconfigured. |
| `src/localstock/notifications/formatters.py` | Vietnamese message formatters | ✓ VERIFIED | 147 lines. `format_daily_digest()`, `format_score_alerts()`, `format_sector_rotation()`. All produce HTML with Vietnamese text and emoji indicators. |
| `src/localstock/api/routes/automation.py` | On-demand trigger endpoints | ✓ VERIFIED | 72 lines. 3 endpoints: POST /run, POST /run/{symbol}, GET /status. Symbol regex validation `^[A-Z0-9]+$`. 409 on pipeline lock. |
| `src/localstock/api/app.py` | Updated with automation router + lifespan | ✓ VERIFIED | 37 lines. Imports `automation_router` and `get_lifespan`. 7 total routers. `lifespan=get_lifespan` on FastAPI constructor. 27 total routes. |
| `src/localstock/config.py` | Extended with Telegram + scheduler settings | ✓ VERIFIED | 5 new settings: `telegram_bot_token`, `telegram_chat_id`, `scheduler_run_hour` (15), `scheduler_run_minute` (45), `score_change_threshold` (15.0). |
| `src/localstock/db/models.py` | 3 new ORM models | ✓ VERIFIED | `ScoreChangeAlert` (line 401), `SectorSnapshot` (line 425), `NotificationLog` (line 444). All with proper columns, unique constraints, indexes. |
| `src/localstock/db/repositories/sector_repo.py` | SectorSnapshot repository | ✓ VERIFIED | 71 lines. `bulk_upsert()`, `get_latest()`, `get_by_date()`, `get_by_date_range()`. PostgreSQL upsert on conflict. |
| `src/localstock/db/repositories/notification_repo.py` | Notification dedup repository | ✓ VERIFIED | 57 lines. `log_notification()` with upsert, `was_sent_today()` checks status="sent". |
| `src/localstock/db/repositories/score_repo.py` | Extended with previous-date query | ✓ VERIFIED | `get_previous_date_scores()` (line 83) and `get_latest_date()` (line 107) added. |
| `alembic/versions/add_phase5_automation_tables.py` | Merge migration + 3 tables | ✓ VERIFIED | Revision `b5c6d7e8f901` merging two heads. Creates score_change_alerts, sector_snapshots, notification_logs. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `automation_service.py` | `pipeline.py` | `Pipeline(session)` | ✓ WIRED | Line 83, 254 |
| `automation_service.py` | `telegram.py` | `TelegramNotifier()` | ✓ WIRED | Import line 25, usage line 46 |
| `automation_service.py` | `score_change_service.py` | `detect_score_changes(session)` | ✓ WIRED | Import line 31, usage line 153 |
| `automation_service.py` | `sector_service.py` | `SectorService(session)` | ✓ WIRED | Import line 33, usage line 162 |
| `automation_service.py` | `formatters.py` | `format_daily_digest/format_score_alerts` | ✓ WIRED | Import lines 20-23, usage lines 199, 221 |
| `automation_service.py` | `notification_repo.py` | `NotificationRepository.was_sent_today()` | ✓ WIRED | Import line 19, usage lines 192, 219 |
| `automation_service.py` | `calendar.py` | `is_trading_day()` | ✓ WIRED | Import line 26, usage line 67 |
| `score_change_service.py` | `score_repo.py` | `ScoreRepository.get_previous_date_scores()` | ✓ WIRED | Line 56 |
| `sector_service.py` | `sector_repo.py` | `SectorSnapshotRepository.bulk_upsert()` | ✓ WIRED | Line 84 |
| `telegram.py` | `telegram.Bot` | `Bot(token=self.bot_token)` | ✓ WIRED | Line 32 |
| `calendar.py` | `holidays.Vietnam` | `holidays.Vietnam(years=d.year)` | ✓ WIRED | Line 28 |
| `app.py` | `automation.py` | `include_router(automation_router)` | ✓ WIRED | Import line 6, usage line 33 |
| `app.py` | `scheduler.py` | `lifespan=get_lifespan` | ✓ WIRED | Import line 12, usage line 25 |
| `scheduler.py` | `automation_service.py` | `AutomationService().run_daily_pipeline()` | ✓ WIRED | Lazy import line 29, usage line 37 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `automation_service.py` | `summary` dict | Pipeline steps, score_changes, sector_rotation | ✓ Each step writes results to summary | ✓ FLOWING |
| `score_change_service.py` | `changes` list | `ScoreRepository.get_by_date()` + `get_previous_date_scores()` | ✓ Real DB queries via SQLAlchemy | ✓ FLOWING |
| `sector_service.py` | `snapshots` list | `IndustryRepository` + `ScoreRepository` → aggregation | ✓ Real DB queries, computes avg_score per group | ✓ FLOWING |
| `formatters.py` | `lines` list | Input params from automation_service | ✓ Formats real data from callers | ✓ FLOWING |
| `telegram.py` | `text` param | From formatters | ✓ Passes to `Bot.send_message()` | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 9 Phase 5 modules import cleanly | `uv run python -c "from localstock.X import Y"` | All 9 print "OK" | ✓ PASS |
| Automation API routes registered | `uv run python -c "...app.routes..."` | POST /api/automation/run, POST /api/automation/run/{symbol}, GET /api/automation/status (27 total routes) | ✓ PASS |
| Calendar identifies trading days correctly | `uv run python -c "...is_trading_day..."` | Sunday=False, Monday=True, April 30=False, Next after Fri=Monday | ✓ PASS |
| Formatter produces Vietnamese HTML output | `uv run python -c "...format_daily_digest..."` | "📊 LocalStock Daily Digest — 16/04/2026", "🏆 Top Gợi ý mua", 289 chars | ✓ PASS |
| TelegramNotifier graceful skip when unconfigured | `uv run python -c "...TelegramNotifier..."` | `is_configured=False`, `send_message()` returns False | ✓ PASS |
| Message splitting at 4000 chars | `uv run python -c "..._split_message..."` | 6000-char input → 2 parts: 3999 + 2000 chars | ✓ PASS |
| Scheduler is AsyncIOScheduler with VN timezone | `uv run python -c "...scheduler..."` | `AsyncIOScheduler`, timezone=`Asia/Ho_Chi_Minh` | ✓ PASS |
| Phase 5 tests all pass | `uv run pytest tests/test_scheduler/ tests/test_phase5/ tests/test_notifications/ tests/test_services/test_automation_service.py tests/test_services/test_score_changes.py tests/test_services/test_sector_rotation.py -v` | 51 passed in 1.39s | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTO-01 | 05-01, 05-03 | Scheduled pipeline execution (APScheduler, auto-run after market close) | ✓ SATISFIED | AsyncIOScheduler + CronTrigger at 15:45, mon-fri, Asia/Ho_Chi_Minh. Lifespan integration starts/stops scheduler with FastAPI. |
| AUTO-02 | 05-03 | Manual trigger API endpoints (single or full) | ✓ SATISFIED | POST /api/automation/run (full, force=True), POST /api/automation/run/{symbol} (single). Both with 409 on lock. |
| NOTI-01 | 05-02, 05-03 | Telegram notification support (daily digest) | ✓ SATISFIED | TelegramNotifier sends HTML messages via python-telegram-bot. format_daily_digest() produces top 10 with scores/grades in Vietnamese. |
| NOTI-02 | 05-02, 05-03 | Notification deduplication | ✓ SATISFIED | NotificationLog model with UQ on (date, notification_type). NotificationRepository.was_sent_today() checked before sending. Upsert pattern for retries. |
| SCOR-04 | 05-01, 05-02 | Score change detection (>15pt changes between scoring dates) | ✓ SATISFIED | detect_score_changes() compares consecutive scoring dates via ScoreRepository.get_previous_date_scores(). Configurable threshold (default 15.0). Handles no-previous-data edge case. |
| SCOR-05 | 05-01, 05-02 | Sector rotation tracking (industry-level aggregation) | ✓ SATISFIED | SectorService.compute_snapshot() aggregates avg_score per industry group. get_rotation_summary() classifies inflow (>2.0)/outflow (<-2.0)/stable. SectorSnapshot model persists data. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `score_change_service.py` | 48, 53, 59 | `return []` | ℹ️ Info | Legitimate early returns for empty/missing data scenarios — not stubs. Each guards against no-scoring-data, no-current-scores, no-previous-date conditions. |
| `sector_service.py` | 42, 47 | `return []` | ℹ️ Info | Legitimate early returns for no scoring data / no scores. |

No TODO, FIXME, PLACEHOLDER, HACK, or stub patterns found in any Phase 5 file.

### Human Verification Required

### 1. Telegram Message Delivery

**Test:** Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars, then trigger `POST /api/automation/run` via curl. Check Telegram for the daily digest message.
**Expected:** Telegram bot sends formatted HTML message with top stocks (with scores and grades), score changes (with arrows and delta), and sector rotation summary in Vietnamese.
**Why human:** Requires real Telegram bot token and chat ID to verify actual message delivery through Telegram's API.

### 2. End-to-End Pipeline with Live Data

**Test:** Start FastAPI server with `uv run uvicorn localstock.api.app:app`, verify scheduler starts, wait for 15:45 VN time or trigger manually via API. Check database for pipeline results.
**Expected:** All 6 pipeline steps complete, score_change_alerts populated, sector_snapshots computed, notification_logs show "sent" status, Telegram message received.
**Why human:** Requires running PostgreSQL with seeded data, Ollama LLM service active, and network access to Vietnamese stock data sources.

### Gaps Summary

No automated gaps found. All 5 observable truths verified, all 15 artifacts exist and are substantive, all 14 key links wired, all 6 requirements satisfied, 51 tests passing, 8 behavioral spot-checks pass. 

Two items require human verification: (1) actual Telegram message delivery with real credentials, and (2) full end-to-end pipeline execution with live infrastructure.

---

_Verified: 2026-04-16T15:25:00Z_
_Verifier: the agent (gsd-verifier)_
