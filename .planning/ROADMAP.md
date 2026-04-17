# Roadmap: LocalStock

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-04-16) — [Archive](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 UX Polish & Educational Depth** — Phases 7-10 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-04-16</summary>

- [x] Phase 1: Foundation & Data Pipeline (4/4 plans) — completed 2026-04-14
- [x] Phase 2: Technical & Fundamental Analysis (4/4 plans) — completed 2026-04-14
- [x] Phase 3: Sentiment Analysis & Scoring Engine (4/4 plans) — completed 2026-04-15
- [x] Phase 4: AI Reports, Macro Context & T+3 Awareness (4/4 plans) — completed 2026-04-15
- [x] Phase 5: Automation & Notifications (3/3 plans) — completed 2026-04-15
- [x] Phase 6: Web Dashboard (4/4 plans) — completed 2026-04-16

</details>

### 🚧 v1.1 UX Polish & Educational Depth

- [ ] **Phase 7: Theme Foundation & Visual Identity** - Warm-light default theme + dark toggle, FOUC-free switching, chart re-theming, WCAG-passing financial tokens
- [ ] **Phase 8: Stock Page Reading-First Redesign** - AI report full-width center scroll, right drawer for charts/data on demand, structured Markdown rendering
- [ ] **Phase 9: Academic/Learning Page & Glossary Data** - Educational pages for technical/fundamental/macro concepts, typed glossary data module, diacritic-insensitive search
- [ ] **Phase 10: Interactive Glossary Linking** - Auto-link terms in AI reports to definitions, hover card previews, deep-link navigation to learn pages

## Phase Details

### Phase 7: Theme Foundation & Visual Identity
**Goal**: Users experience a warm, professional visual identity with persistent theme choice
**Depends on**: Phase 6 (existing dashboard)
**Requirements**: THEME-01, THEME-02, THEME-03, THEME-04, THEME-05
**Success Criteria** (what must be TRUE):
  1. App loads with warm-light cream+orange theme by default — no dark flash on first visit
  2. User can toggle between warm-light and dark themes via a visible control, and preference persists across browser sessions
  3. Charts (candlestick, volume, indicators) automatically update their colors when theme changes — no page reload needed
  4. Financial color indicators (grade badges, stock up/down) remain clearly legible on both theme backgrounds
**Plans**: TBD
**UI hint**: yes

### Phase 8: Stock Page Reading-First Redesign
**Goal**: Users read AI analysis as the primary stock page experience, with charts and data available on demand
**Depends on**: Phase 7
**Requirements**: STOCK-01, STOCK-02, STOCK-03, STOCK-04, STOCK-05
**Success Criteria** (what must be TRUE):
  1. Stock page opens with AI report as full-width center content — charts and raw data are not visible by default
  2. AI report renders structured sections (headers, paragraphs, tables, lists) with proper typography — not raw text or JSON dump
  3. User can open a right-side drawer with Chart and Raw Data tabs to view supplementary data
  4. Opening and closing the drawer preserves the user's scroll position in the main report
  5. Drawer state is reflected in URL search params — shareable links preserve drawer tab, browser back closes drawer
**Plans**: TBD
**UI hint**: yes

### Phase 9: Academic/Learning Page & Glossary Data
**Goal**: Users can browse and search educational content explaining the financial indicators used in AI reports
**Depends on**: Phase 7
**Requirements**: LEARN-01, LEARN-02, LEARN-03, LEARN-04
**Success Criteria** (what must be TRUE):
  1. User can navigate to /learn and browse entries across three categories: Technical Indicators, Fundamental Ratios, and Macro Concepts
  2. Each category has its own URL (/learn/technical, /learn/fundamental, /learn/macro) loading as a dedicated page
  3. Glossary data module contains ≥15 typed entries serving as the single source of truth for learn pages and glossary linking
  4. User can search and filter entries with Vietnamese diacritic-insensitive matching (e.g., typing "chi so" finds "chỉ số")
**Plans**: TBD
**UI hint**: yes

### Phase 10: Interactive Glossary Linking
**Goal**: Users can discover term definitions inline while reading AI reports, bridging analysis and education
**Depends on**: Phase 8, Phase 9
**Requirements**: GLOSS-01, GLOSS-02, GLOSS-03, GLOSS-04
**Success Criteria** (what must be TRUE):
  1. Known glossary terms in AI report text are automatically highlighted as interactive links — visually distinct from regular text
  2. Hovering a linked term shows a preview card with the short definition and a link to the full learn page
  3. Clicking through from a hover card navigates to /learn/[category]#[term] with the entry scrolled into view
  4. Multiple surface forms of the same term (e.g., "RSI", "chỉ số RSI", "Relative Strength Index") all resolve to the same glossary entry
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Data Pipeline | v1.0 | 4/4 | Complete | 2026-04-14 |
| 2. Technical & Fundamental Analysis | v1.0 | 4/4 | Complete | 2026-04-14 |
| 3. Sentiment Analysis & Scoring Engine | v1.0 | 4/4 | Complete | 2026-04-15 |
| 4. AI Reports, Macro Context & T+3 | v1.0 | 4/4 | Complete | 2026-04-15 |
| 5. Automation & Notifications | v1.0 | 3/3 | Complete | 2026-04-15 |
| 6. Web Dashboard | v1.0 | 4/4 | Complete | 2026-04-16 |
| 7. Theme Foundation & Visual Identity | v1.1 | 0/0 | Not started | - |
| 8. Stock Page Reading-First Redesign | v1.1 | 0/0 | Not started | - |
| 9. Academic/Learning Page & Glossary Data | v1.1 | 0/0 | Not started | - |
| 10. Interactive Glossary Linking | v1.1 | 0/0 | Not started | - |
