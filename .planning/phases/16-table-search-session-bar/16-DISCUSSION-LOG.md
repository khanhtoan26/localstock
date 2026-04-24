# Phase 16: Table, Search & Session Bar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 16-table-search-session-bar
**Areas discussed:** Sort fix details, Search input placement, Session bar layout, Outside trading hours display

---

## Sort fix details

| Option | Description | Selected |
|--------|-------------|----------|
| Numeric only | Only numeric columns sortable; grade/recommendation non-clickable | |
| All columns sortable | Grade + Recommendation sortable alphabetically | |
| Grade sortable (semantic) | Grade sortable with semantic order, Recommendation non-sortable | ✓ |

**User's choice:** Grade IS sortable (semantic order A+ > A > B+ > B > C). Recommendation is NOT sortable.

| Option | Description | Selected |
|--------|-------------|----------|
| Lucide ChevronUp/ChevronDown | Replace text arrows with icons | ✓ |
| Keep text arrows ↑ ↓ | Minimal change | |

**User's choice:** ChevronUp/ChevronDown icons from lucide-react.

| Option | Description | Selected |
|--------|-------------|----------|
| Semantic order | A+ > A > B+ > B > C via grade rank lookup | ✓ |
| Alphabetical | Standard string sort | |

**User's choice:** Semantic grade sort (A+ = rank 1, best; C = rank 5, worst).

---

## Search input placement

| Option | Description | Selected |
|--------|-------------|----------|
| Above the table | Search bar above table in rankings page | ✓ |
| In page header row | Next to page title | |

**User's choice:** Above the table.

| Option | Description | Selected |
|--------|-------------|----------|
| ?q=VNM (short) | Standard short URL param | ✓ |
| ?search=VNM (explicit) | Longer, more descriptive | |

**User's choice:** `?q=VNM`

| Option | Description | Selected |
|--------|-------------|----------|
| Client-side only | Filter 50 loaded stocks in browser | ✓ |
| Server-side | API call with search param | |

**User's choice:** Client-side filtering.

| Option | Description | Selected |
|--------|-------------|----------|
| nuqs library | Standard Next.js App Router URL state | ✓ |
| Manual useSearchParams | Native hooks, no new dep | |

**User's choice:** nuqs library.

---

## Session bar layout

| Option | Description | Selected |
|--------|-------------|----------|
| Center of header | flex-1 center section | ✓ |
| Right side before toggles | Appended to right controls | |

**User's choice:** Center of header.

| Option | Description | Selected |
|--------|-------------|----------|
| Progress bar + phase + countdown | Slim bar, phase name, time remaining | ✓ |
| Status pill only | Badge with phase + time, no bar | |

**User's choice:** Progress bar format.

| Option | Description | Selected |
|--------|-------------|----------|
| Standard HOSE schedule | Pre-market 8:30, ATO 9:00, Trading 9:15, Lunch 11:30, Afternoon 13:00, ATC 14:30, Closed 14:45 | ✓ |
| Custom schedule | User-defined phase times | |

**User's choice:** Standard HOSE schedule (UTC+7).

---

## Outside trading hours display

| Option | Description | Selected |
|--------|-------------|----------|
| Countdown to next open | "Opens in 14h 30m" — live dynamic countdown | ✓ |
| Static text only | "Opens Mon 9:00" — no live countdown | |

**User's choice:** Live countdown.

| Option | Description | Selected |
|--------|-------------|----------|
| No — weekdays only | Skip public holidays, complex to maintain | ✓ |
| Yes — hardcode holidays | Static 2026 holiday list | |

**User's choice:** No holiday handling in v1.

---

## Claude's Discretion

- Exact CSS for the progress bar (height, color, border-radius)
- Search input debounce (recommend 150ms)
- Session bar width in center section
- Hiding session bar on very small screens (sm:hidden acceptable)
- nuqs version to install

## Deferred Ideas

- Vietnamese public holidays awareness (Tết, 30/4, 2/9...)
- Global ⌘K command palette / sidebar search wiring
- Search suggestions/autocomplete (TBL-05/TBL-06)
- Recommendation column sorting
