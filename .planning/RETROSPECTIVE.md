# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-16
**Phases:** 6 | **Plans:** 23 | **Sessions:** ~5

### What Was Built
- Full data pipeline crawling ~400 HOSE stocks (OHLCV, financials, corporate actions) with PostgreSQL storage
- Multi-dimensional analysis engine: 11 technical indicators, fundamental ratios, sentiment via LLM, macro context
- AI scoring engine (0-100) with configurable weights, sector rotation detection, and score change alerts
- Vietnamese-language AI reports via local Ollama LLM with T+3 settlement awareness
- Automated daily pipeline (APScheduler) with Telegram bot notifications
- Next.js 16 dark-theme web dashboard with rankings, candlestick charts, and market overview

### What Worked
- GSD workflow kept 6 phases well-structured — each phase was coherent with clear boundaries
- Wave-based execution within phases (parallel-safe plans in same wave) kept plans manageable
- TDD approach in Phase 3 (scoring engine) caught edge cases early — 326 total tests by end
- vnstock v3.5.1 provided stable Vietnamese market data API — no custom scraping needed
- lightweight-charts v5 for candlestick charts — fast, financial-grade quality with minimal code

### What Was Inefficient
- SUMMARY.md `one_liner` field was poorly populated for many phases — milestone archival had to manually extract accomplishments
- REQUIREMENTS.md checkboxes weren't updated during phase completion — had to fix 9 unchecked items at milestone time
- DB migrations not auto-run on fresh start — caused "relation does not exist" error during UAT
- Some executor agents hit `Author identity unknown` error — required mid-session git config fix

### Patterns Established
- CORS middleware restricted to `localhost:3000` (not wildcard) for security
- All Vietnamese text in frontend uses dedicated formatter utilities
- Phase verification gates (code review + verification + human UAT) catch issues before milestone
- Dark theme using `#020817` background as standard for all UI

### Key Lessons
1. Always run `alembic upgrade head` as part of startup/deploy checklist — never assume DB is up to date
2. Mark requirements as `[x]` during phase completion, not at milestone time — avoids drift
3. SUMMARY.md quality determines milestone quality — enforce `one_liner` field in executor prompts
4. Code review advisory items (like falsy checks on `0.0`) should be addressed before milestone, not deferred

### Cost Observations
- Model mix: ~20% opus (planning), ~60% sonnet (execution), ~20% haiku (exploration)
- Sessions: ~5 across 3 days
- Notable: Wave-based parallel execution saved time in Phases 1-4 (2 plans per wave)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~5 | 6 | Established GSD workflow, wave execution, UAT gates |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 326 | N/A | 23 plans |

### Top Lessons (Verified Across Milestones)

1. Run DB migrations as part of startup — never assume schema is current
2. Keep requirement tracking up-to-date per phase, not per milestone
