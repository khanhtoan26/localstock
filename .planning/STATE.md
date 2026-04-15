---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 03-02-PLAN.md
last_updated: "2026-04-15T11:44:12.583Z"
last_activity: 2026-04-15
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 12
  completed_plans: 10
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.
**Current focus:** Phase 03 — sentiment-analysis-scoring-engine

## Current Position

Phase: 03 (sentiment-analysis-scoring-engine) — EXECUTING
Plan: 3 of 4
Status: Ready to execute
Last activity: 2026-04-15

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 4
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 7min | 2 tasks | 22 files |
| Phase 01 P02 | 3min | 2 tasks | 6 files |
| Phase 01 P03 | 3min | 2 tasks | 5 files |
| Phase 01 P04 | 4min | 2 tasks | 9 files |
| Phase 02 P01 | 4min | 3 tasks | 9 files |
| Phase 02 P02 | 4min | 2 tasks | 4 files |
| Phase 02 P03 | 3min | 2 tasks | 4 files |
| Phase 02 P04 | 3min | 2 tasks | 4 files |
| Phase 03 P01 | 3min | 2 tasks | 12 files |
| Phase 03 P02 | 4min | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 6-phase pipeline architecture following data dependency chain (Data → Analysis → LLM/Scoring → Reports → Automation → Dashboard)
- [Roadmap]: SCOR-04/SCOR-05 placed in Phase 5 (Automation) — require historical run data for score change detection and sector rotation tracking
- [Roadmap]: MACR-01/MACR-02 placed in Phase 4 (Reports) — macro context enriches AI reports, and macro data is hardest to source so it comes after core pipeline works
- [Phase 01]: BigInteger for StockPrice.volume — Vietnamese stock volumes can exceed 2B
- [Phase 01]: pytest-timeout added as dev dependency for timeout=30 config support
- [Phase 01]: datetime.now(UTC) over deprecated utcnow() for Python 3.12+ timezone-aware timestamps
- [Phase 01]: Repository pattern with pg_insert().on_conflict_do_update() for idempotent writes
- [Phase 01]: run_in_executor bridge pattern for wrapping sync vnstock in async crawlers
- [Phase 01]: KBS source first for financials (more stable per research issue #218), VCI as fallback
- [Phase 01]: VCI source for company profiles (richer data via GraphQL endpoint with ICB classification)
- [Phase 01]: Unit normalization to billion_vnd at ingestion time (prevents Pitfall 4)
- [Phase 01]: Backward price adjustment: divide prices by ratio before ex_date, multiply volumes by ratio (DATA-05)
- [Phase 01]: Only split and stock_dividend types trigger price adjustment; unknown types stored but not applied (T-01-11)
- [Phase 01]: FastAPI app factory pattern: create_app() returns configured instance with modular routers
- [Phase 02]: pandas-ta moved from dev to main deps — required at runtime for indicator computation
- [Phase 02]: All analysis models use DateTime(timezone=True) for computed_at — Phase 1 UAT lesson
- [Phase 02]: Individual pandas-ta calls (not Study API) for per-indicator error handling
- [Phase 02]: BB column names use double suffix (BBL_20_2.0_2.0) — verified at runtime
- [Phase 02]: Manual peak/trough detection without scipy — minimal dependency footprint
- [Phase 02]: P/E uses market_cap/share_holder_income for more accurate per-share valuation
- [Phase 02]: 20 VN industry groups with 40+ ICB3 Vietnamese mappings, OTHER fallback for unmapped stocks
- [Phase 02]: AnalysisService follows Pipeline pattern — session-based orchestrator with per-symbol error isolation
- [Phase 02]: API endpoints return flat JSON dicts (no Pydantic response models) — consistent with health.py pattern
- [Phase 02]: POST /api/analysis/run is synchronous — acceptable for single-user tool per T-02-07
- [Phase 03]: URL as dedup key for NewsArticle (unique constraint on url column)
- [Phase 03]: Scoring weights default to 0.35/0.35/0.30/0.0 — macro_score weight 0.0 until Phase 4
- [Phase 03]: score_to_grade in scoring/__init__.py shared by Plan 02 and 03
- [Phase 03]: NewsCrawler standalone class — RSS feeds are not per-symbol, doesn't extend BaseCrawler
- [Phase 03]: SentimentResult Pydantic model as Ollama format schema for structured JSON output (D-03)
- [Phase 03]: Exponential time decay (half_life=3 days) for sentiment aggregation — prevents stale news dominance
- [Phase 03]: 2000-char article truncation — limits prompt injection surface and context overflow

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Corporate action data sourcing for HOSE needs investigation during Phase 1 planning — CafeF scraping likely but unvalidated
- [Research]: Qwen2.5 Vietnamese financial text performance unverified — may need fallback to 7B or Vistral during Phase 3
- [Research]: vnai dependency in vnstock has caused issues — may need patching if problematic on Linux

## Session Continuity

Last session: 2026-04-15T11:44:12.580Z
Stopped at: Completed 03-02-PLAN.md
Resume file: None
