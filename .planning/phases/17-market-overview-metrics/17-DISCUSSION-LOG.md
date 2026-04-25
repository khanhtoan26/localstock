# Phase 17: Market Overview Metrics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 17-market-overview-metrics
**Areas discussed:** Data source & staleness, Card content & layout, Auto-refresh cadence

---

## Data source & staleness

### VN-Index data source

| Option | Description | Selected |
|--------|-------------|----------|
| VNINDEX as tracked stock | Store/crawl VNINDEX like any stock — reuse existing prices table and crawl path | ✓ |
| Dedicated vnstock market API | Call vnstock market-level API at query time or via separate crawl job | |

**User's choice:** VNINDEX as tracked stock
**Notes:** Simpler, no new infrastructure needed. Advances/declines derived from existing ~400 tracked stocks.

### Staleness UX

| Option | Description | Selected |
|--------|-------------|----------|
| Show 'as of [date]' timestamp | Small label near section title showing data date | ✓ |
| Show warning badge when data is old | Yellow 'Yesterday' badge on each card | |
| No staleness indicator | Show values without date context | |

**User's choice:** Show 'as of [date]' timestamp
**Notes:** Transparent about data age without visual clutter.

---

## Card content & layout

### Card content

| Option | Description | Selected |
|--------|-------------|----------|
| Value + % change + trend arrow | E.g. 'VN-Index: 1,245.3 +0.8% ↑' | ✓ |
| Value only | Just the number, matches current MacroCards style | |

**User's choice:** Value + % change + trend arrow

### Placement on Market page

| Option | Description | Selected |
|--------|-------------|----------|
| New section at top, before MacroCards | Market summary first, then macro indicators | ✓ |
| Replace MacroCards section | Swap out macro grid | |
| New section below MacroCards, above SectorTable | Between macro and sectors | |

**User's choice:** New section at top, before MacroCards
**Notes:** Natural reading order — market index first, then macro context.

---

## Auto-refresh cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 30 minutes | Simple, matches daily-crawl data rhythm | ✓ |
| Smart: 5min during market hours, 1hr outside | More responsive but requires market-hours detection | |
| Same as MacroCards (1 hour) | Align with existing stale time | |

**User's choice:** Fixed stale time — 30 minutes

---

## Deferred Ideas

- Smart refresh based on market hours — too complex for this phase, 30min is sufficient
- Intraday live price feeds
- HNX/UPCOM indices
- Volume breakdown by sector
