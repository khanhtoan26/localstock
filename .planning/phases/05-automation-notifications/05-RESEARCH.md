# Phase 5: Automation & Notifications - Research

**Researched:** 2026-04-16
**Domain:** Scheduler automation, Telegram bot notifications, score change detection, sector rotation
**Confidence:** HIGH

## Summary

Phase 5 transforms LocalStock from a manually-triggered tool into a fully automated daily pipeline with intelligent Telegram notifications. The existing codebase already has a complete `run_daily.py` script that chains all 6 pipeline steps (crawl → analyze → news → sentiment → score → report). This phase wraps that pipeline in APScheduler for automated daily execution after market close, adds python-telegram-bot for sending digests and alerts, implements score change detection by comparing consecutive days' CompositeScore records, and adds sector rotation tracking via aggregated industry-level volume/score data over time.

The key technical challenges are: (1) Vietnamese holiday awareness — HOSE doesn't trade on VN public holidays, so the scheduler must skip those days; (2) integrating APScheduler with the existing FastAPI async lifecycle; (3) score change detection requiring new DB queries to compare today's vs yesterday's scores; and (4) sector rotation needing aggregation of per-stock data into industry-level metrics tracked over time.

**Primary recommendation:** Use APScheduler v3.11.2 AsyncIOScheduler integrated into FastAPI's lifespan, `python-telegram-bot` v22.7 for async message sending, and the `holidays` v0.94 package for Vietnamese holiday calendar. New DB models: `ScoreChangeAlert` and `SectorSnapshot` for tracking detected changes and sector rotation data.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Implementation Decisions — Agent's Discretion (entire phase)
- **D-01:** Agent tự thiết kế Telegram bot: format tin nhắn, kênh/nhóm, tần suất.
- **D-02:** Agent tự cấu hình scheduler: thời gian chạy, xử lý lỗi, nhận biết ngày nghỉ/lễ VN.
- **D-03:** Agent tự thiết kế score change alerts: ngưỡng cảnh báo, loại tín hiệu, format.
- **D-04:** Agent tự implement sector rotation: cách đo dòng tiền, so sánh giữa các ngành.

### Carrying Forward
- Supabase database (Phase 1)
- Composite scores + grade letters (Phase 3)
- AI reports tiếng Việt (Phase 4)
- HOSE trading hours: 9:00-15:00, thứ 2-6

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTO-01 | Agent chạy tự động hàng ngày sau khi thị trường đóng cửa (sau 15:30) | APScheduler AsyncIOScheduler with CronTrigger + `holidays` package for VN calendar |
| AUTO-02 | Agent hỗ trợ chạy on-demand khi người dùng yêu cầu (phân tích 1 mã hoặc toàn bộ) | FastAPI API endpoint + Telegram bot command handler |
| NOTI-01 | Agent gửi thông báo qua Telegram bot khi có gợi ý mã đáng mua (daily digest) | `python-telegram-bot` v22.7 async API for formatted Markdown messages |
| NOTI-02 | Agent gửi alert đặc biệt qua Telegram khi phát hiện thay đổi điểm lớn hoặc tín hiệu mạnh | Score comparison queries on CompositeScore + alert deduplication logic |
| SCOR-04 | Agent phát hiện và cảnh báo khi điểm thay đổi đáng kể (>15 điểm) so với phiên trước | DB query comparing latest vs previous CompositeScore per symbol |
| SCOR-05 | Agent phân tích sector rotation — theo dõi dòng tiền chảy giữa các ngành | Aggregate volume + score by industry group over time into SectorSnapshot table |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 | In-process job scheduler | Cron-like triggers, AsyncIOScheduler for FastAPI integration, zero external deps (no Redis/RabbitMQ). v4 still alpha — v3 is stable. [VERIFIED: PyPI registry] |
| python-telegram-bot | 22.7 | Telegram bot API client | Most popular Python Telegram lib (v22.7 latest). Async-native since v20+. Supports Markdown/HTML formatting, inline keyboards. [VERIFIED: PyPI registry] |
| holidays | 0.94 | Vietnamese public holiday calendar | Supports `holidays.Vietnam(years=2026)` with all VN holidays (Tết, 30/4, 2/9, Giỗ Tổ Hùng Vương, etc.). [VERIFIED: tested locally] |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI | 0.135+ | API server with lifespan for scheduler | Scheduler starts/stops via FastAPI lifespan context manager |
| SQLAlchemy | 2.0+ | ORM for new score change + sector models | New queries for score comparison and sector aggregation |
| loguru | 0.7+ | Structured logging for scheduler/notification events | All scheduler and notification activities logged |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler | System cron | cron can't be containerized easily, no programmatic control, no error handling/retry, no async integration [CITED: research/ARCHITECTURE.md] |
| APScheduler | Celery | Requires Redis/RabbitMQ broker — overkill for single-machine tool [CITED: research/ARCHITECTURE.md] |
| python-telegram-bot | aiogram | aiogram is async-first but smaller community; python-telegram-bot is more battle-tested with better docs |
| holidays | Hardcoded list | holidays package handles lunar calendar dates (Tết shifts yearly), nghỉ bù (compensatory days); hardcoding is brittle |

**Installation:**
```bash
uv add apscheduler python-telegram-bot holidays
```

## Architecture Patterns

### Recommended Module Structure
```
src/localstock/
├── scheduler/              # NEW: Automation layer
│   ├── __init__.py
│   ├── scheduler.py        # APScheduler setup + job definitions
│   └── calendar.py         # VN trading calendar (holidays + weekends)
├── notifications/          # NEW: Telegram integration
│   ├── __init__.py
│   ├── telegram.py         # TelegramNotifier class (send messages)
│   └── formatters.py       # Message formatting (digest, alert, sector)
├── services/
│   ├── automation_service.py    # NEW: Full pipeline orchestrator for scheduler
│   └── sector_service.py       # NEW: Sector rotation detection
├── api/routes/
│   ├── automation.py       # NEW: On-demand trigger endpoints
│   └── ...existing...
├── db/
│   ├── models.py           # ADD: ScoreChangeAlert, SectorSnapshot models
│   └── repositories/
│       ├── score_repo.py   # EXTEND: Add get_previous_date_scores() method
│       └── sector_repo.py  # NEW: SectorSnapshot repository
```

### Pattern 1: APScheduler + FastAPI Lifespan Integration
**What:** Bind APScheduler's lifecycle to FastAPI's lifespan context manager so the scheduler starts with the server and shuts down cleanly.
**When to use:** Any time APScheduler runs alongside FastAPI in the same process.
**Example:**
```python
# scheduler/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

def setup_scheduler(daily_job_func):
    """Configure and return the scheduler with daily pipeline job."""
    scheduler.add_job(
        daily_job_func,
        trigger=CronTrigger(
            hour=15, minute=45,  # 15:45 — 15 min after market close for data settle
            day_of_week="mon-fri",
            timezone="Asia/Ho_Chi_Minh",
        ),
        id="daily_pipeline",
        name="Daily full pipeline",
        replace_existing=True,
        misfire_grace_time=3600,  # 1hr grace if missed (e.g., machine was off)
    )
    return scheduler

# api/app.py — lifespan integration
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```
[ASSUMED — standard APScheduler+FastAPI pattern from training data]

### Pattern 2: Trading Calendar with Holiday Skip
**What:** Before executing the daily pipeline, check if today is a VN trading day (not weekend, not holiday). If not, skip silently.
**When to use:** Every scheduled pipeline execution.
**Example:**
```python
# scheduler/calendar.py
from datetime import date
import holidays

def is_trading_day(check_date: date | None = None) -> bool:
    """Check if the given date is a HOSE trading day."""
    d = check_date or date.today()
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    vn_holidays = holidays.Vietnam(years=d.year)
    return d not in vn_holidays
```
[VERIFIED: holidays.Vietnam tested locally, supports all VN holidays including Tết, 30/4, 2/9, nghỉ bù]

### Pattern 3: Score Change Detection
**What:** After scoring completes, query today's and previous day's CompositeScore to detect changes >15 points.
**When to use:** After every scoring pipeline run, before sending notifications.
**Example:**
```python
# Logic: compare latest two dates with scores for each symbol
async def detect_score_changes(session, threshold=15.0):
    """Find stocks with significant score changes."""
    # Get the two most recent scoring dates
    # For each symbol: today_score - prev_score
    # Filter where abs(delta) > threshold
    changes = []
    # Query today's and yesterday's scores, compute deltas
    return changes  # [{symbol, old_score, new_score, delta, direction}, ...]
```

### Pattern 4: Telegram Message Formatting
**What:** Format structured stock data into readable Telegram messages using MarkdownV2 or HTML.
**When to use:** All Telegram notifications.
**Key constraints:**
- Telegram message limit: 4096 characters per message
- Rate limit: ~30 messages/second per chat, but batch into 1-2 messages per run
- Use HTML mode (simpler escaping than MarkdownV2)

**Example digest format:**
```
📊 LocalStock Daily Digest — 16/04/2026

🏆 Top 5 Gợi ý mua:
1. VNM (A) — 87.3 điểm | Mua mạnh
   Tech ▲ Fund ★★★ Sent 🟢
2. FPT (A) — 84.1 điểm | Mua
   Tech ▲ Fund ★★★ Sent 🟡
...

⚠️ Thay đổi lớn (>15 điểm):
📈 HPG: 45.2 → 68.7 (+23.5)
📉 MWG: 72.1 → 54.3 (-17.8)

🔄 Sector Rotation:
Dòng tiền vào: Ngân hàng ↑, Thép ↑
Dòng tiền ra: BĐS ↓, Chứng khoán ↓
```

### Pattern 5: Sector Rotation via Volume+Score Aggregation
**What:** Track money flow between industries by aggregating per-industry average volume changes and average score trends over a rolling window (e.g., 5-day and 20-day).
**When to use:** Daily, after scoring completes.
**Approach:**
1. Group all stocks by `group_code` (from StockIndustryMapping)
2. For each industry: compute avg relative_volume and avg total_score
3. Compare current period vs previous period
4. Industries with rising volume + rising scores = "money flowing in"
5. Industries with falling volume + falling scores = "money flowing out"

### Anti-Patterns to Avoid
- **Running LLM during the notification step:** Notifications should use pre-computed data from reports. Don't generate new LLM content during notification — just format existing data.
- **Hardcoding Vietnamese holidays:** Use the `holidays` package — Tết dates shift yearly based on lunar calendar.
- **Sending one Telegram message per stock:** Batch all information into 1-2 messages per run. Telegram rate limits apply.
- **Not handling scheduler re-runs:** If the machine reboots and the scheduler fires twice, the pipeline should be idempotent (upsert-based storage handles this) and notifications should be deduplicated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vietnamese holiday calendar | Manual list of holidays per year | `holidays.Vietnam()` | Lunar calendar dates shift yearly; nghỉ bù logic is complex |
| Telegram API interaction | Raw HTTP calls to api.telegram.org | `python-telegram-bot` | Handles rate limiting, retries, message formatting, bot updates |
| Cron-like scheduling | Custom loop with sleep/timers | APScheduler `CronTrigger` | Handles timezone, misfire, missed runs, graceful shutdown |
| Async job scheduling | Threading + asyncio bridges | APScheduler `AsyncIOScheduler` | Native asyncio integration, runs in the same event loop as FastAPI |

**Key insight:** All three main components (scheduler, notifications, holiday calendar) have mature, well-tested Python libraries. Custom implementations would be fragile and miss edge cases (timezone DST, Telegram rate limiting, lunar calendar calculations).

## Common Pitfalls

### Pitfall 1: Scheduler Running on Non-Trading Days
**What goes wrong:** Pipeline runs on weekends and Vietnamese holidays, fetching stale data, sending duplicate notifications, wasting compute.
**Why it happens:** APScheduler's `day_of_week="mon-fri"` handles weekends but doesn't know about VN holidays.
**How to avoid:** Add a trading-day check at the start of the scheduled job function. If `not is_trading_day()`, log and return immediately.
**Warning signs:** Duplicate daily digests on holiday weekends; error logs from data fetchers returning empty on non-trading days.
[CITED: .planning/research/PITFALLS.md line 331]

### Pitfall 2: Telegram Notification Deduplication
**What goes wrong:** If the scheduler re-runs (machine reboot, manual trigger), the same daily digest gets sent twice.
**Why it happens:** No record of what notifications have already been sent.
**How to avoid:** Store a notification log in DB (date + type + sent_at). Before sending, check if today's digest was already sent. For on-demand triggers, allow re-sending but mark as "manual."
**Warning signs:** Multiple identical Telegram messages in the chat on the same day.
[CITED: .planning/research/PITFALLS.md line 288]

### Pitfall 3: APScheduler Event Loop Conflict with FastAPI
**What goes wrong:** Starting APScheduler's `AsyncIOScheduler` before or outside FastAPI's event loop causes "no running event loop" errors or double-loop issues.
**Why it happens:** FastAPI uses its own asyncio event loop via uvicorn. APScheduler needs to share that loop.
**How to avoid:** Initialize and start the scheduler inside FastAPI's `lifespan` context manager, NOT at module import time. Use `AsyncIOScheduler` (not `BackgroundScheduler`).
**Warning signs:** `RuntimeError: This event loop is already running` or `RuntimeError: no current event loop`.
[ASSUMED — common integration pattern]

### Pitfall 4: Telegram Message Length Overflow
**What goes wrong:** Daily digest with 20 stocks + score changes + sector rotation exceeds Telegram's 4096 character limit.
**Why it happens:** Each stock entry takes ~100-150 chars. 20 stocks + alerts = easily 3000-4000 chars.
**How to avoid:** Split messages if content exceeds ~3800 chars. Send top 10 in digest (not 20), with a link/command to get more. Use concise formatting.
**Warning signs:** Telegram API returns 400 error with "message is too long."
[ASSUMED — Telegram API constraint from training data]

### Pitfall 5: Score Change False Positives After First Run
**What goes wrong:** On the very first run, all stocks show as "new" with massive score changes (0 → score) because there's no previous day's data.
**Why it happens:** Score change detection compares today vs yesterday. If yesterday has no data, delta is the full score.
**How to avoid:** Require at least 2 consecutive scoring dates before generating change alerts. Check that the previous date's scores exist before computing deltas.
**Warning signs:** First run generates 400+ "significant change" alerts.

### Pitfall 6: Timezone Mismatch in Scheduler
**What goes wrong:** Scheduler triggers at wrong time because server timezone differs from Vietnam timezone (UTC+7).
**Why it happens:** APScheduler defaults to local timezone. If deployed on a cloud server in a different timezone, 15:45 might be wrong.
**How to avoid:** Explicitly set `timezone="Asia/Ho_Chi_Minh"` in both the scheduler and the CronTrigger. Use `pytz` or `zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")`.
**Warning signs:** Pipeline runs at unexpected hours; logs show scheduling in wrong timezone.
[ASSUMED — standard timezone pitfall]

## Code Examples

### Example 1: Telegram Bot Setup
```python
# notifications/telegram.py
from telegram import Bot
from telegram.constants import ParseMode
from loguru import logger

class TelegramNotifier:
    """Sends stock analysis notifications via Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, text: str, parse_mode: str = ParseMode.HTML) -> bool:
        """Send a message to the configured chat."""
        try:
            # Split if too long
            if len(text) > 4000:
                parts = self._split_message(text, 4000)
                for part in parts:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=part,
                        parse_mode=parse_mode,
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode,
                )
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
```
[ASSUMED — python-telegram-bot v22.7 async API pattern]

### Example 2: Full Pipeline with Notification
```python
# services/automation_service.py
async def run_daily_pipeline(self) -> dict:
    """Execute full pipeline and send notifications."""
    if not is_trading_day():
        logger.info("Non-trading day — skipping pipeline")
        return {"status": "skipped", "reason": "non_trading_day"}

    # Run the 6-step pipeline (same as bin/run_daily.py)
    result = {}
    async with self.session_factory() as session:
        pipeline = Pipeline(session)
        crawl = await pipeline.run_full(run_type="daily")
        result["crawl"] = crawl.symbols_success
    # ... analysis, news, sentiment, scoring, reports ...

    # Detect score changes
    async with self.session_factory() as session:
        changes = await self.detect_score_changes(session, threshold=15.0)

    # Compute sector rotation
    async with self.session_factory() as session:
        rotation = await self.compute_sector_rotation(session)

    # Send notifications
    await self.send_daily_digest(top_stocks, changes, rotation)

    return result
```

### Example 3: Sector Rotation Snapshot
```python
# Model for sector rotation tracking
class SectorSnapshot(Base):
    __tablename__ = "sector_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    group_code: Mapped[str] = mapped_column(String(20), index=True)
    avg_score: Mapped[float] = mapped_column(Float)         # avg total_score of stocks in group
    avg_volume: Mapped[float] = mapped_column(Float)         # avg daily volume
    total_volume: Mapped[int] = mapped_column(BigInteger)    # sum of volumes in group
    stock_count: Mapped[int] = mapped_column(Integer)        # number of stocks in group
    avg_score_change: Mapped[float | None] = mapped_column(Float, nullable=True)  # vs previous snapshot

    __table_args__ = (
        UniqueConstraint("date", "group_code", name="uq_sector_snapshot"),
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler v4 alpha | APScheduler v3.11.2 stable | v4 still alpha (6 alpha releases) | Use v3 — v4 has breaking API changes and isn't production-ready [VERIFIED: PyPI] |
| `telegram.ext` Runner API | Direct `Bot` class for notification-only use | python-telegram-bot v20+ | For send-only bots (no command handlers needed for daily digest), use `Bot` directly without `Application` |
| Manual holiday lists | `holidays` package v0.94 | Actively maintained | Package handles lunar calendar computations for Tết [VERIFIED: tested locally] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | APScheduler AsyncIOScheduler integrates cleanly with FastAPI lifespan | Architecture Patterns - Pattern 1 | Would need BackgroundScheduler + threading instead; more complex |
| A2 | python-telegram-bot v22.7 `Bot.send_message()` works without full Application setup | Code Examples | May need `Application` builder pattern for bot initialization |
| A3 | Telegram message limit is 4096 characters | Pitfall 4 | Would need different splitting strategy |
| A4 | Telegram rate limit is ~30 msg/sec per chat | Architecture Patterns | Unlikely to hit with 1-2 messages per run |
| A5 | Sector rotation can be meaningfully measured by volume+score aggregation at industry level | Pattern 5 | May need more sophisticated flow metrics; but simple approach is good starting point |
| A6 | `misfire_grace_time=3600` is the correct param for APScheduler v3 | Pattern 1 | Different param name would cause silent ignoring |

## Open Questions

1. **Telegram Bot Token Provisioning**
   - What we know: User must create a bot via @BotFather and provide token + chat_id
   - What's unclear: Should we prompt user to set up during first run, or document it?
   - Recommendation: Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to Settings with empty defaults. If not configured, notifications are silently skipped (pipeline still runs). Add setup instructions in README.

2. **On-Demand Trigger via Telegram Commands**
   - What we know: AUTO-02 requires on-demand analysis. This could be API only or API + Telegram.
   - What's unclear: Should Telegram bot accept commands like `/analyze VNM` to trigger analysis?
   - Recommendation: For v1, implement on-demand via API endpoints only (simpler). Telegram bot is send-only. Add Telegram commands in v2. This keeps scope manageable.

3. **Pipeline Concurrency Lock**
   - What we know: Existing API routes use `asyncio.Lock` to prevent concurrent runs.
   - What's unclear: How does scheduled run interact with on-demand API trigger?
   - Recommendation: Use a shared process-level lock. If scheduler is running, on-demand returns "pipeline in progress." If on-demand is running, scheduler job waits or skips.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | ✓ | 3.12.3 | — |
| uv | Package management | ✓ | 0.11.6 | pip |
| Docker | PostgreSQL hosting | ✓ | 29.3.1 | — |
| Ollama | Report generation | ✗ | — | Pipeline runs without reports (existing graceful skip) |
| Telegram Bot Token | Notifications | ✗ (not configured) | — | Pipeline runs, notifications silently skipped |

**Missing dependencies with no fallback:**
- None — all critical deps are available

**Missing dependencies with fallback:**
- Ollama: Pipeline runs without AI reports (already handled by ReportService health check)
- Telegram Token: Must be configured by user; pipeline runs fine without it

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.26 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x --timeout=30` |
| Full suite command | `uv run pytest tests/ --timeout=30` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTO-01 | Scheduler fires daily after 15:30, skips holidays | unit | `uv run pytest tests/test_scheduler/ -x` | ❌ Wave 0 |
| AUTO-02 | On-demand analysis via API endpoint | unit | `uv run pytest tests/test_api/test_automation.py -x` | ❌ Wave 0 |
| NOTI-01 | Daily digest sent via Telegram | unit | `uv run pytest tests/test_notifications/ -x` | ❌ Wave 0 |
| NOTI-02 | Special alert on score change >15pts | unit | `uv run pytest tests/test_notifications/test_alerts.py -x` | ❌ Wave 0 |
| SCOR-04 | Score change detection (>15 points) | unit | `uv run pytest tests/test_services/test_score_changes.py -x` | ❌ Wave 0 |
| SCOR-05 | Sector rotation tracking | unit | `uv run pytest tests/test_services/test_sector_rotation.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x --timeout=30`
- **Per wave merge:** `uv run pytest tests/ --timeout=30`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scheduler/__init__.py` + `test_calendar.py` — covers AUTO-01 (trading day logic)
- [ ] `tests/test_scheduler/test_scheduler.py` — covers AUTO-01 (scheduler config)
- [ ] `tests/test_notifications/__init__.py` + `test_telegram.py` — covers NOTI-01
- [ ] `tests/test_notifications/test_formatters.py` — covers NOTI-01, NOTI-02 (message formatting)
- [ ] `tests/test_services/test_score_changes.py` — covers SCOR-04
- [ ] `tests/test_services/test_sector_rotation.py` — covers SCOR-05

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — single-user local tool |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | Pydantic Settings for config; validate Telegram inputs |
| V6 Cryptography | No | N/A — no custom crypto |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Telegram bot token exposure | Information Disclosure | Store in `.env`, never log token, `.gitignore` `.env` |
| Bot token in source code | Information Disclosure | Use `pydantic_settings` with env_file; no hardcoded tokens |
| Unauthorized pipeline trigger | Elevation of Privilege | API lock prevents concurrent runs; single-user tool mitigates risk |

## Sources

### Primary (HIGH confidence)
- APScheduler v3.11.2 — [VERIFIED: PyPI registry, version confirmed]
- python-telegram-bot v22.7 — [VERIFIED: PyPI registry, version confirmed]
- holidays v0.94 with Vietnam support — [VERIFIED: installed and tested locally, 12 VN holidays for 2026 including Tết]
- Existing codebase — bin/run_daily.py, services/*.py, db/models.py, scoring/engine.py — [VERIFIED: source code review]

### Secondary (MEDIUM confidence)
- Architecture research (.planning/research/ARCHITECTURE.md) — APScheduler + FastAPI integration pattern
- Pitfalls research (.planning/research/PITFALLS.md) — Holiday handling, notification deduplication

### Tertiary (LOW confidence)
- Telegram message limit (4096 chars) and rate limits (~30/sec) — [ASSUMED: from training data]
- APScheduler misfire_grace_time behavior — [ASSUMED: from training data]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI, holidays tested locally
- Architecture: HIGH — follows established patterns from prior phases (service pattern, repository pattern, flat dict API responses)
- Pitfalls: HIGH — holiday handling verified, deduplication pattern well-understood
- Sector rotation: MEDIUM — approach is reasonable but unvalidated against real VN market data

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days — stable domain, mature libraries)
