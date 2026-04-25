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

## Milestone: v1.3 — UI/UX Refinement

**Shipped:** 2026-04-25
**Phases:** 4 (14–17) | **Plans:** 14 | **Commits:** 93

### What Was Built
- Source Sans 3 typography with Vietnamese subset + warm neutral color palette replacing all blue (Claude Desktop aesthetic)
- Claude Desktop-style floating sidebar: icon rail (w-14) always visible + overlay panel (w-60) with 180ms CSS transform, Admin nav group
- Table sort fixed (numeric + grade semantic sort-comparator.ts), live stock search filter (StockSearchInput, local state)
- HOSE market session bar in header — pure hose-session.ts with SSR guard, 6 session phases, 60s countdown
- GET /api/market/summary backend API (SQLAlchemy self-join for advances/declines) + MarketSummaryCards frontend (4 live metric cards)
- 52 new tests (44 frontend vitest + 8 backend pytest); code review fixes applied post-approval

### What Worked
- Wave 0 TDD stubs (RED → GREEN) pattern from Phase 16/17 — test contracts written before implementation locked the API surface
- Pure module extraction (sort-comparator.ts, hose-session.ts, filter-stocks.ts) — each testable in isolation without React overhead
- SSR guard via useSyncExternalStore (same pattern as theme-toggle.tsx) — zero hydration mismatches
- Code review post-execution with auto-fix agent — caught 3 warnings that were immediately fixed in same session
- Human visual approval checkpoint (plan -03) gave clear go/no-go on UI changes without blocking execution

### What Was Inefficient
- Sidebar design pivoted 6+ times within Phase 15 (multiple commits adjusting bg color, inset, layout) before final design settled
- nuqs was installed (Phase 16-01) then removed (Phase 16-05) — wasted one plan slot; should have decided earlier whether URL persistence was needed
- ROADMAP.md progress table still showed `[ ]` for Phase 16 plans at milestone start — not updated after each phase

### Patterns Established
- `useSyncExternalStore` for SSR-safe client state (market session, theme toggle)
- Lazy `useState` initializer (not `useEffect`) for FOUC-free localStorage reads
- Pure logic modules (no React imports) + dedicated test files — vitest runs without JSDOM overhead
- MAX(date) pattern for "today's trading day" — never `date.today()`, robust across weekends and holidays
- `or None` truthy coercion on integers is a bug — always use `is None` guard on nullable fields

### Key Lessons
1. Decide on URL vs local state persistence before writing the plan — avoids install-then-remove churn
2. Update ROADMAP.md plan checkboxes after each phase executes, not just at milestone close
3. Design decisions (sidebar layout, bg color) should be settled in CONTEXT.md before execution — prevents mid-execution pivots
4. Code review + auto-fix in same session is efficient — 3 warnings resolved in one agent call

### Cost Observations
- Model mix: ~15% opus (planning/context), ~75% sonnet (execution), ~10% haiku (verification)
- Sessions: ~3 across 1 day (intensive UI iteration)
- Notable: Phase 15 sidebar redesign consumed ~6 commits of iteration — design upfront saves execution cost

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~5 | 6 | Established GSD workflow, wave execution, UAT gates |
| v1.1 | ~3 | 4 | Theme system, educational hub, glossary linking |
| v1.2 | ~2 | 4 | Admin Console with job monitoring and pipeline control |
| v1.3 | ~3 | 4 | Pure module extraction + TDD stubs; code review auto-fix pattern |

### Cumulative Quality

| Milestone | Backend Tests | Frontend Tests | Plans |
|-----------|--------------|----------------|-------|
| v1.0 | 326 | 0 | 23 |
| v1.1 | 326 | 0 | 12 |
| v1.2 | 326 | 0 | 8 |
| v1.3 | 332 | 44 | 14 |

### Top Lessons (Verified Across Milestones)

1. Run DB migrations as part of startup — never assume schema is current
2. Keep requirement tracking up-to-date per phase, not per milestone
3. Pure module extraction (no React deps) enables fast vitest unit testing — establish this pattern early in UI phases
4. Settle design decisions in CONTEXT.md before execution — mid-execution pivots (sidebar, colors) are expensive
