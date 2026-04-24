# Phase 16: Table, Search & Session Bar - Research

**Researched:** 2026-04-24
**Domain:** Next.js 16 / React 19 client components — URL state management, table sort, timezone-aware session display
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Table Sort Fix**
- D-01: Tiebreaker: `a.symbol.localeCompare(b.symbol)` as secondary sort key when values are equal (replace current `return 0`)
- D-02: Sort icons: `ChevronUp` / `ChevronDown` from `lucide-react` (already installed). Show only active column icon.
- D-03: Recommendation column is NOT sortable. Grade IS sortable (semantic).
- D-04: Grade semantic sort rank map `{ 'A+': 1, 'A': 2, 'B+': 3, 'B': 4, 'C': 5 }`. Desc puts A+ first.
- D-05: Null values continue using `-Infinity` sentinel (current behavior unchanged).

**Search on Rankings Page**
- D-06: Search input placed above the table in rankings page content area, between page title and table.
- D-07: Client-side filter only. Matches `symbol` prefix (case-insensitive) OR `name` substring (defensive, `StockScore` has no `name` field yet).
- D-08: URL param `?q=VNM` via `nuqs` library (new dependency). Next.js App Router compatible.
- D-09: Search term persists via URL param — survives navigation naturally.
- D-10: Clear button (×) appears inside input when query is non-empty.

**Market Session Bar — Header Layout**
- D-11: Session bar in center section of `h-12` header in `flex-1` region between logo block and right controls.
- D-12: Visual format: slim horizontal progress bar + phase label + time remaining. `[ ATO ████░░░░░░ 8m left ]`
- D-13: Pure client-side `"use client"` component. `Date.now()` with 1-minute `setInterval`.

**HOSE Session Phases (UTC+7)**
- D-14: Phase boundaries:
  - Pre-market: 08:30–09:00
  - ATO: 09:00–09:15
  - Morning: 09:15–11:30
  - Lunch: 11:30–13:00
  - Afternoon: 13:00–14:30
  - ATC: 14:30–14:45
  - Closed: 14:45+
- D-15: Mon–Fri only. No public holiday handling in v1.

**Outside Trading Hours**
- D-16: Closed state: `● Closed · Opens in 14h 30m` with live countdown to next weekday 08:30.
- D-17: Weekends skip to Monday 08:30. Weekday evenings target next-day 08:30.
- D-18: Progress bar 0% fill when market is closed.

### Claude's Discretion
- Exact CSS for progress bar (height, color, border-radius — use neutral palette tokens)
- Whether to debounce search input (recommend 150ms)
- Exact width of session bar in center section
- Session indicator visibility on small screens (`sm:hidden` is fine)
- nuqs version to install (latest stable)

### Deferred Ideas (OUT OF SCOPE)
- Vietnamese public holiday awareness (Tết, 30/4, 2/9) — add TODO comment in component
- Sidebar ⌘K search (command palette)
- Search suggestions/autocomplete (TBL-05/TBL-06)
- Recommendation column sort order (Recommendation is non-sortable in this phase)

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TBL-01 | Table sort hoạt động đúng: numeric sort cho số, tiebreaker bằng symbol | Current sort logic identified in `stock-table.tsx`; comparator fix + GRADE_RANK map pattern documented |
| TBL-02 | Sort state hiển thị rõ (icon direction) trên column đang sort | `ChevronUp`/`ChevronDown` from lucide-react already installed; inline icon pattern documented |
| TBL-03 | Search bar trên rankings page filter stocks theo symbol/tên | `StockSearchInput` component spec; client-side `useMemo` filter in `rankings/page.tsx` |
| TBL-04 | Search state persist khi chuyển trang/tab (URL params) | nuqs 2.8.9 verified; `useQueryState("q")` + `NuqsAdapter` required in layout.tsx |
| MKT-01 | Header hiển thị market session progress bar (HOSE 9:00-15:00 với các phiên) | `MarketSessionBar` client component spec; header integration point identified in `app-shell.tsx` |
| MKT-02 | Session bar hiện trạng thái phiên (Pre-market / Trading / Lunch / Closed) | HOSE phase boundaries (UTC+7) fully specified; timezone conversion pattern via `toLocaleString("en-US", { timeZone: "Asia/Ho_Chi_Minh" })` |

</phase_requirements>

---

## Summary

Phase 16 is a pure frontend phase touching three areas: fixing table sort correctness, adding a URL-persisted search filter on the rankings page, and inserting a market session status bar in the app header. No backend changes are required. All three areas are well-specified in CONTEXT.md and the UI-SPEC.md — the research job is primarily to verify library compatibility, identify exact codebase integration points, and flag edge cases.

The codebase is a Next.js 16 / React 19 app using the App Router. The `stock-table.tsx` component has an existing sort implementation that needs two changes: a tiebreaker and a grade semantic sort. The `rankings/page.tsx` page needs a search input wired via `nuqs` URL state. The `app-shell.tsx` header currently has no center flex section — one must be added to host `MarketSessionBar`.

`nuqs` 2.8.9 is the latest stable version. It is NOT installed yet (`nuqs NOT installed` confirmed). It requires `NuqsAdapter` wrapping in `layout.tsx` for App Router. The existing `layout.tsx` uses `NextIntlClientProvider → ThemeProvider → QueryProvider → AppShell` nesting — `NuqsAdapter` must be added at the correct layer. Peer dep `next >= 14.2.0` is satisfied by Next.js 16.2.4 in this project.

**Primary recommendation:** Three task waves: (1) table sort fix + sort icons, (2) search input + nuqs install + NuqsAdapter in layout, (3) MarketSessionBar new component + header integration + i18n keys. The only external dependency to install is `nuqs`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Table sort (numeric + grade + tiebreaker) | Browser / Client | — | Pure in-memory array sort on already-fetched data; no server round-trip |
| Search filter | Browser / Client | — | Client-side `useMemo` filter on loaded 50 stocks; no API call |
| Search URL persistence | Browser / Client | Frontend Server (SSR) | `nuqs` writes `?q=` to URL; shallow by default (client-only). SSR tier is secondary — `shallow: true` means no server notification |
| Market session calculation | Browser / Client | — | `Date.now()` + timezone math; purely computed, no API |
| Header layout (center section) | Browser / Client | — | DOM/CSS change to `app-shell.tsx` |
| i18n copy for new UI strings | Frontend Server (SSR) | Browser / Client | `next-intl` message files consumed server-side; client reads via `useTranslations` |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nuqs | 2.8.9 | URL query state management | Type-safe, Next.js App Router native, replaces verbose `useSearchParams` + `router.replace` patterns |
| lucide-react | 1.8.0 (installed) | Sort icon chevrons | Already project standard; `ChevronUp`/`ChevronDown` present |
| next-intl | 4.9.1 (installed) | i18n copy for new UI strings | Already project standard; existing pattern for all user-facing copy |

[VERIFIED: npm registry — `npm view nuqs version` returned `2.8.9`]
[VERIFIED: package.json — lucide-react `^1.8.0`, next-intl `^4.9.1`]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @base-ui/react Progress | 1.4.0 (installed) | Progress track/indicator in session bar | Existing `progress.tsx` component wraps it — prefer reuse |
| shadcn Input | installed | Search input field | Existing `input.tsx` component — already styled to design system |

[VERIFIED: package.json — `@base-ui/react ^1.4.0`]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nuqs `useQueryState` | `useSearchParams` + `router.replace` | Manual approach is verbose and error-prone; nuqs handles serialization, hydration, and SSR correctly |
| CSS div for progress bar | `<Progress>` from `@base-ui/react` | `<Progress>` already uses `bg-muted`/`bg-primary` tokens correctly — less CSS to write |
| `new Date()` UTC offset math | `Intl.DateTimeFormat` via `toLocaleString` | `toLocaleString("en-US", { timeZone: "Asia/Ho_Chi_Minh" })` is the standard IANA timezone approach, more reliable than manual `+7` offset arithmetic |

**Installation:**
```bash
npm install nuqs
```

**Version verification:** [VERIFIED: npm registry] nuqs 2.8.9 published, peer deps include `next: >=14.2.0` — satisfied by project's Next.js 16.2.4.

---

## Architecture Patterns

### System Architecture Diagram

```
User Input
    │
    ├─[Type in search]─────────────────────────────────────────────┐
    │                                                               ▼
    │                                                   StockSearchInput (client)
    │                                                   useQueryState("q") → URL ?q=VNM
    │                                                         │ q value
    ▼                                                         ▼
rankings/page.tsx ──[useTopScores(50)]──▶ TanStack Query   useMemo filter
    │                                     (cached 5min)      │
    │◀────────────────────────────────────────────────────────┘
    │  filteredData[]
    ▼
StockTable (client)
    │  internal sort state (sortKey, sortDir)
    │  sorted = [...filteredData].sort(comparator)
    ▼
DOM table rows

app-shell.tsx (header)
    ├─[left] toggle + logo
    ├─[center flex-1] MarketSessionBar (client)
    │         │  setInterval(60s)
    │         │  Date.now() → toLocaleString("en-US", {timeZone: "Asia/Ho_Chi_Minh"})
    │         │  → phaseInfo { label, pct, countdown }
    │         ▼
    │         [ Phase label | Progress bar | Countdown ]
    └─[right] LanguageToggle + ThemeToggle
```

### Recommended Project Structure
```
apps/helios/src/
├── components/
│   ├── layout/
│   │   ├── app-shell.tsx          # MODIFIED — add center flex-1 + <MarketSessionBar />
│   │   └── market-session-bar.tsx # NEW — "use client" HOSE session component
│   └── rankings/
│       ├── stock-table.tsx        # MODIFIED — sort fix + ChevronUp/Down icons
│       └── stock-search-input.tsx # NEW — "use client" search input with nuqs
├── app/
│   ├── layout.tsx                 # MODIFIED — add NuqsAdapter
│   └── rankings/
│       └── page.tsx               # MODIFIED — add search state + useMemo filter
└── messages/
    ├── en.json                    # MODIFIED — add search + session bar keys
    └── vi.json                    # MODIFIED — add search + session bar keys
```

### Pattern 1: nuqs useQueryState with string default

```tsx
// Source: Context7 /47ng/nuqs
"use client";
import { useQueryState, parseAsString } from "nuqs";

export function StockSearchInput() {
  const [q, setQ] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: true })
  );
  // ...
}
```

`parseAsString.withDefault("")` ensures `q` is never `null`, simplifying the
consumer. `shallow: true` (default) means no server round-trip — correct for
this pure client-side filter.

### Pattern 2: NuqsAdapter in Next.js App Router layout

```tsx
// Source: Context7 /47ng/nuqs
import { NuqsAdapter } from "nuqs/adapters/next/app";

export default async function RootLayout({ children }) {
  return (
    <html>
      <body>
        <NuqsAdapter>
          {/* existing providers nest inside or outside — see pitfall below */}
          {children}
        </NuqsAdapter>
      </body>
    </html>
  );
}
```

[VERIFIED: Context7 /47ng/nuqs — NuqsAdapter required for App Router nuqs 2.x]

### Pattern 3: Grade semantic sort with GRADE_RANK map

```ts
// Source: CONTEXT.md D-04 + UI-SPEC.md
const GRADE_RANK: Record<string, number> = {
  "A+": 1,
  "A": 2,
  "B+": 3,
  "B": 4,
  "C": 5,
};

// In the sort comparator:
const aVal = sortKey === "grade"
  ? (GRADE_RANK[a.grade] ?? 99)
  : (a[sortKey] ?? -Infinity);
const bVal = sortKey === "grade"
  ? (GRADE_RANK[b.grade] ?? 99)
  : (b[sortKey] ?? -Infinity);
```

Desc on grade: `GRADE_RANK["A+"] = 1` is the lowest number → floats to top. This matches the user expectation "clicking Grade desc puts A+ first".

### Pattern 4: HOSE timezone calculation

```ts
// Source: CONTEXT.md D-13/D-14, MDN IANA timezone
function getVNTime(): { hours: number; minutes: number; dayOfWeek: number } {
  const vnStr = new Date().toLocaleString("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
    weekday: "narrow",
  });
  // Parse hours, minutes, weekday from result
}
```

**Important:** `toLocaleString` returns a string — must parse it carefully. Alternative: use `Intl.DateTimeFormat` with `formatToParts()` for reliable field extraction.

```ts
// Cleaner approach using formatToParts
const formatter = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Ho_Chi_Minh",
  hour: "numeric",
  minute: "numeric",
  hour12: false,
  weekday: "short",
});
const parts = formatter.formatToParts(new Date());
const hour = parseInt(parts.find(p => p.type === "hour")!.value);
const minute = parseInt(parts.find(p => p.type === "minute")!.value);
const dayOfWeek = parts.find(p => p.type === "weekday")!.value; // "Mon", "Tue" etc.
```

[ASSUMED] `Intl.DateTimeFormat.formatToParts` availability — reliable in all modern browsers and Node 18+; should be confirmed for any unusual deployment target. In a Next.js 16 / browser context this is standard.

### Pattern 5: Debounced search with immediate local state

```tsx
// Source: UI-SPEC.md + standard React debounce pattern
const [localValue, setLocalValue] = useState(q);
const [q, setQ] = useQueryState("q", parseAsString.withDefault("").withOptions({ shallow: true }));

// Debounce: update URL only after 150ms idle
useEffect(() => {
  const timer = setTimeout(() => setQ(localValue || null), 150);
  return () => clearTimeout(timer);
}, [localValue, setQ]);
```

Local `useState` drives the displayed input value immediately. URL is updated after debounce — avoids a URL push on every keystroke.

### Anti-Patterns to Avoid

- **Grade sort using string comparison:** `"A+" < "B"` in string ordering gives wrong results. Always use `GRADE_RANK` map.
- **Recommendation column sorting:** Must guard `handleSort` with `if (col.key === "recommendation") return;` and remove `cursor-pointer` from its header. Current code applies cursor-pointer to all columns uniformly.
- **nuqs without NuqsAdapter:** `useQueryState` will silently fail or throw if `NuqsAdapter` is absent. It must wrap the component tree in `layout.tsx`.
- **Manual UTC+7 offset (`new Date().getTime() + 7*3600000`):** Fails during DST transitions if Vietnam ever adopts DST (currently doesn't, but the IANA approach is more correct and readable).
- **Setting `q` to empty string instead of `null` to clear:** nuqs keeps `?q=` in the URL when set to the default value. Pass `null` or use `setQ(null)` to remove the param entirely on clear.
- **Filtering in StockTable:** Filter logic belongs in `rankings/page.tsx` (parent). `StockTable` should remain a dumb presentation component that only sorts what it receives.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL query param sync | Custom `useSearchParams` + `router.replace` wrapper | `nuqs useQueryState` | nuqs handles SSR hydration mismatch, history push/replace, serialization, and Next.js App Router specifics |
| Timezone-aware time | `Date.getTime() + offset` arithmetic | `Intl.DateTimeFormat` with `timeZone: "Asia/Ho_Chi_Minh"` | IANA timezone database handles edge cases; manual offset breaks at midnight boundary if mishandled |
| Progress bar | Raw `<div>` with width style | `<ProgressTrack>/<ProgressIndicator>` from existing `progress.tsx` | Reusing the existing component guarantees token consistency (`bg-muted`, `bg-primary`, `h-1`, `rounded-full`) |

---

## Runtime State Inventory

Step 2.5: SKIPPED — This is a greenfield feature addition phase with no rename/refactor/migration. No stored data, live service config, OS-registered state, secrets, or build artifacts are affected.

---

## Common Pitfalls

### Pitfall 1: NuqsAdapter Missing from Layout
**What goes wrong:** `useQueryState` throws at runtime or returns stale values; URL updates silently fail.
**Why it happens:** nuqs 2.x requires `NuqsAdapter` from `nuqs/adapters/next/app` in the root layout. Previous nuqs v1 did not require this.
**How to avoid:** Add `<NuqsAdapter>` to `layout.tsx` before any component that uses `useQueryState`.
**Warning signs:** Console errors mentioning "NuqsAdapter not found" or search input that doesn't update the URL.

### Pitfall 2: Grade Sort Direction Inversion
**What goes wrong:** Clicking "Grade" in "desc" shows C stocks first instead of A+ first.
**Why it happens:** `GRADE_RANK["A+"] = 1` is the smallest number. The comparator `aVal > bVal → sortDir === "asc" ? 1 : -1` means desc puts larger numbers first — i.e., C (rank 5) first.
**How to avoid:** Verify: desc sort should return `GRADE_RANK["A+"] = 1` stocks at top. This means the sort is actually ASCENDING on the rank numbers when user clicks "desc". The comparator logic must treat grade rank as "lower rank number = better = should appear first in desc". Equivalently: sort ascending on rank value when `sortDir === "desc"` for grade column, or invert the comparator direction for grade.
**Warning signs:** "A+" stocks appearing at the bottom after clicking grade header.

**Correct approach:** When `sortDir === "desc"` for grade, sort `aVal < bVal` returns -1 (ascending on rank = best grades first). Either invert the direction mapping for grade or negate the rank value: `GRADE_RANK_DESC = { "A+": -1, "A": -2, "B+": -3, "B": -4, "C": -5 }`.

### Pitfall 3: Recommendation Column Still Clickable
**What goes wrong:** Clicking the Recommendation column header triggers a sort, potentially reordering rows unexpectedly.
**Why it happens:** Current `columns` array has a uniform `onClick={() => handleSort(col.key)}` applied to all `TableHead` elements.
**How to avoid:** Add early return guard: `if (col.key === "recommendation") return;` at the start of `handleSort`. Also remove `cursor-pointer` from recommendation header's className.
**Warning signs:** Table reorders when clicking "Signal" column header.

### Pitfall 4: nuqs `setQ("")` vs `setQ(null)` for Clear
**What goes wrong:** Clicking clear leaves `?q=` in the URL instead of removing the param.
**Why it happens:** `parseAsString.withDefault("")` treats `""` as the default value — nuqs may omit it from URL, but `setQ(null)` is the explicit API to remove the param.
**How to avoid:** In the clear button handler, call `setQ(null)` not `setQ("")`.
**Warning signs:** URL shows `?q=` after clearing, or URL param unexpectedly persists.

### Pitfall 5: Midnight Boundary in HOSE Session Calculation
**What goes wrong:** Session shows wrong phase at midnight or around midnight UTC.
**Why it happens:** UTC midnight = 07:00 Vietnam time. If time math is done in UTC and compared against hardcoded Vietnam minutes, the phase boundaries will be wrong.
**How to avoid:** Always convert to Vietnam time first via `Intl.DateTimeFormat` before comparing against phase boundaries. Never compare raw UTC hour values to Vietnam phase boundaries.
**Warning signs:** Session bar shows wrong phase or flips unexpectedly around 07:00 Vietnam time (= midnight UTC).

### Pitfall 6: Filter in Wrong Component
**What goes wrong:** Moving filter logic into `StockTable` creates a "filter then sort" ordering issue, or duplicates state between parent and child.
**Why it happens:** Tempting to add filtering inside the table since sorting is there.
**How to avoid:** Parent (`rankings/page.tsx`) filters → passes `filteredData` → `StockTable` sorts internally. Separation is clean: filter is URL-state-aware (needs `q`), sort is local-state (no URL awareness needed).
**Warning signs:** `StockTable` importing nuqs, or props mismatch between parent and table.

---

## Code Examples

### Sort comparator fix (tiebreaker + grade)
```tsx
// Source: CONTEXT.md D-01, D-04, D-05 + UI-SPEC.md
const GRADE_RANK: Record<string, number> = {
  "A+": 1, "A": 2, "B+": 3, "B": 4, "C": 5,
};

const sorted = [...data].sort((a, b) => {
  let aVal: number;
  let bVal: number;

  if (sortKey === "grade") {
    // For grade: rank 1 = best. "desc" means best first = ascending on rank value.
    aVal = GRADE_RANK[a.grade] ?? 99;
    bVal = GRADE_RANK[b.grade] ?? 99;
    // Swap direction: when user clicks desc, show A+ (rank 1) first
    if (aVal < bVal) return sortDir === "desc" ? -1 : 1;
    if (aVal > bVal) return sortDir === "desc" ? 1 : -1;
  } else {
    aVal = (a[sortKey] as number | null) ?? -Infinity;
    bVal = (b[sortKey] as number | null) ?? -Infinity;
    if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
  }
  // Tiebreaker: alphabetical by symbol
  return a.symbol.localeCompare(b.symbol);
});
```

### Sort icon replacement
```tsx
// Source: UI-SPEC.md + lucide-react (already installed)
import { ChevronUp, ChevronDown } from "lucide-react";

// In TableHead render:
{col.header}
{sortKey === col.key && (
  <span className="inline-flex ml-0.5 align-middle">
    {sortDir === "asc"
      ? <ChevronUp className="h-3 w-3" />
      : <ChevronDown className="h-3 w-3" />
    }
  </span>
)}
```

### rankings/page.tsx filtered data pattern
```tsx
// Source: UI-SPEC.md
import { useQueryState, parseAsString } from "nuqs";
import { useMemo } from "react";

const [q] = useQueryState("q", parseAsString.withDefault(""));

const filtered = useMemo(() => {
  if (!q.trim()) return data.stocks;
  const lower = q.toLowerCase();
  return data.stocks.filter(
    (s) =>
      s.symbol.toLowerCase().startsWith(lower) ||
      (s.name ?? "").toLowerCase().includes(lower)
  );
}, [data.stocks, q]);
```

### NuqsAdapter in layout.tsx
```tsx
// Source: Context7 /47ng/nuqs
import { NuqsAdapter } from "nuqs/adapters/next/app";

// Wrap inside existing providers (position relative to other providers doesn't matter
// for nuqs itself, but must wrap any component that calls useQueryState)
<NuqsAdapter>
  <AppShell>{children}</AppShell>
</NuqsAdapter>
```

### app-shell.tsx header center section addition
```tsx
// Source: CONTEXT.md D-11 + UI-SPEC.md
// Insert between left block and right controls:
<div className="flex-1 flex items-center justify-center">
  <MarketSessionBar />
</div>
```

Current header uses `justify-between` — inserting a `flex-1` center div will push the right controls correctly to the edge while centering the session bar.

### HOSE timezone extraction
```ts
// Source: MDN Intl.DateTimeFormat.formatToParts + CONTEXT.md D-14
function getVNTimeParts(now: Date): { h: number; m: number; dow: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(now);
  const h = parseInt(parts.find((p) => p.type === "hour")!.value, 10);
  const m = parseInt(parts.find((p) => p.type === "minute")!.value, 10);
  const dow = now.toLocaleString("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "short",
  }); // "Mon", "Tue", ..., "Sat", "Sun"
  const dowNum = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].indexOf(dow);
  return { h, m, dow: dowNum };
}
```

---

## Codebase Integration Points (Verified)

| File | Current State | Required Change |
|------|--------------|-----------------|
| `apps/helios/src/app/layout.tsx` | `NextIntlClientProvider → ThemeProvider → QueryProvider → AppShell` | Wrap with `<NuqsAdapter>` (can wrap `AppShell` or the whole chain — wrap `AppShell` is cleanest) |
| `apps/helios/src/components/layout/app-shell.tsx` | Header: `justify-between`, left block + right block only, no center section | Insert `<div className="flex-1 flex items-center justify-center"><MarketSessionBar /></div>` between the two blocks |
| `apps/helios/src/components/rankings/stock-table.tsx` | `sortIndicator` string function, `return 0` on equal, no grade rank, recommendation sortable | Replace `sortIndicator` with icon render; add `GRADE_RANK` map; add tiebreaker; guard recommendation |
| `apps/helios/src/app/rankings/page.tsx` | Passes `data.stocks` directly to `StockTable`, no search | Add `useQueryState`, `useMemo` filter, `<StockSearchInput />`, pass `filtered` to `StockTable` |
| `apps/helios/messages/en.json` | Missing: search placeholder, clear aria-label, no-results, session bar labels | Add `rankings.search.*` and `sessionBar.*` keys |
| `apps/helios/messages/vi.json` | Same gaps | Add Vietnamese equivalents |

[VERIFIED: All files read directly from codebase in this research session]

**Key finding:** `StockScore` type in `types.ts` has no `name` field. `TrackedStock` has `name: string | null`. The defensive `(s.name ?? "").toLowerCase().includes(lower)` filter branch will always return false for current `StockScore` objects — it is forward-compatible code that costs nothing.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| nuqs v1 (no adapter needed) | nuqs v2 (NuqsAdapter required) | nuqs 2.0 | Must add `NuqsAdapter` to layout.tsx — one extra step vs v1 |
| `useSearchParams` + `router.replace` | `useQueryState` (nuqs) | nuqs ~1.0 onward | Less boilerplate, SSR-safe, type-safe |

**Deprecated/outdated:**
- nuqs v1 `useQueryState` without adapter: Works for older Next.js but nuqs 2.x requires the adapter pattern. Project is on Next.js 16 — must use nuqs 2.x adapter.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Intl.DateTimeFormat.formatToParts` is available in all target browsers for this app | Code Examples (HOSE timezone) | Low risk — this is baseline Web API available since 2016, all modern browsers, Node 18+. No polyfill needed. |
| A2 | Grade sort should invert comparator direction (desc = A+ first = ascending on GRADE_RANK numbers) | Pitfall 2 + Code Examples | If wrong, clicking "Grade" desc would show C first. Easy to catch in manual QA. |
| A3 | `NuqsAdapter` wrapping `AppShell` (innermost position) is sufficient for `useQueryState` in rankings/page | Code Examples | If nuqs needs to wrap higher up (e.g., outside `NextIntlClientProvider`), move it. nuqs docs say it only needs to wrap any ancestor of the components using `useQueryState`. Current placement is safe. |

**All other claims in this research were verified by direct codebase reads or confirmed via Context7/npm registry.**

---

## Open Questions (RESOLVED)

1. **Grade sort comparator direction**
   - What we know: `GRADE_RANK["A+"] = 1` (lowest number = best grade). User wants desc = A+ first.
   - What's unclear: The sort comparator direction for grade must be inverted relative to numeric columns. The planner should explicitly document this inversion in the task.
   - Recommendation: Use a dedicated branch for grade in the comparator (as shown in Code Examples) rather than trying to fit it into the numeric path.

2. **`?q=` URL param removal when cleared**
   - What we know: `parseAsString.withDefault("")` — when value equals default, nuqs may omit from URL.
   - What's unclear: Whether `setQ(null)` or `setQ("")` is the correct clear call in nuqs 2.x.
   - Recommendation: Use `setQ(null)` for explicit param removal (nuqs v2 canonical pattern). This is documented in nuqs README.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm install | ✓ | (WSL2 environment) | — |
| nuqs | TBL-03, TBL-04 | ✗ not installed | 2.8.9 (latest) | — (no fallback, must install) |
| lucide-react | TBL-02 | ✓ installed | ^1.8.0 | — |
| @base-ui/react | MKT-01 (Progress component) | ✓ installed | ^1.4.0 | Raw CSS div fallback (not preferred) |
| next-intl | i18n copy | ✓ installed | ^4.9.1 | — |

**Missing dependencies with no fallback:**
- `nuqs` — must be installed via `npm install nuqs` before any component using `useQueryState` can run.

**Missing dependencies with fallback:**
- None besides nuqs.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 4.1.4 |
| Config file | `apps/helios/vitest.config.ts` (exists) |
| Quick run command | `cd apps/helios && npx vitest run` |
| Full suite command | `cd apps/helios && npx vitest run` |

**Note:** No test files exist under `apps/helios/` currently (`tests/` directory absent). Vitest config exists but no tests are written. For this UI phase, the primary validation is manual visual/interaction testing. Automated unit tests for pure logic functions (sort comparator, phase calculation) can be added in Wave 0.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TBL-01 | Numeric sort with tiebreaker | unit | `npx vitest run --reporter=verbose apps/helios/tests/sort.test.ts` | ❌ Wave 0 |
| TBL-01 | Grade semantic sort (A+ first in desc) | unit | same file | ❌ Wave 0 |
| TBL-02 | ChevronUp/Down shown on active column | manual | Visual check | N/A |
| TBL-03 | Search filters by symbol prefix | unit | `npx vitest run apps/helios/tests/search-filter.test.ts` | ❌ Wave 0 |
| TBL-04 | URL param `?q=` set/clear | manual | navigate + check URL | N/A |
| MKT-01 | Session bar renders phase label + progress | manual | Visual check | N/A |
| MKT-02 | Correct phase for given UTC+7 time | unit | `npx vitest run apps/helios/tests/session-phase.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Manual visual check of affected component
- **Per wave merge:** `cd apps/helios && npx vitest run` (when unit tests exist)
- **Phase gate:** All manual interaction contracts from UI-SPEC.md verified before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `apps/helios/tests/sort.test.ts` — covers TBL-01 (comparator logic for numeric, grade, tiebreaker)
- [ ] `apps/helios/tests/search-filter.test.ts` — covers TBL-03 (filter function: symbol prefix, name substring)
- [ ] `apps/helios/tests/session-phase.test.ts` — covers MKT-02 (HOSE phase boundary logic for all 7 phases + weekend)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (search input) | No server submission; client-side only. URL param is user-controlled but never sent to API. No XSS risk from string → useMemo filter. |
| V6 Cryptography | no | — |

**Known Threat Patterns:**

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via search query in no-results message | Tampering | Use `{q}` interpolation in i18n message (next-intl escapes values automatically) — never `dangerouslySetInnerHTML` |
| Open redirect via `?q=` param | Tampering | `q` param is only used for client-side array filtering, never as a URL/route value — no redirect risk |

**Assessment:** This phase has minimal security surface. The search query is read from URL and used only for client-side array filtering. The session bar reads only `Date.now()` — no user input.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `apps/helios/src/components/rankings/stock-table.tsx` — current sort implementation, all columns, SortKey type
- [VERIFIED: codebase] `apps/helios/src/components/layout/app-shell.tsx` — header structure, no center section currently
- [VERIFIED: codebase] `apps/helios/src/app/rankings/page.tsx` — current page, no search
- [VERIFIED: codebase] `apps/helios/src/lib/types.ts` — StockScore interface (no `name` field confirmed)
- [VERIFIED: codebase] `apps/helios/src/app/layout.tsx` — provider nesting, NuqsAdapter insertion point
- [VERIFIED: codebase] `apps/helios/src/components/ui/progress.tsx` — Progress component API (ProgressTrack, ProgressIndicator, tokens)
- [VERIFIED: codebase] `apps/helios/src/components/ui/input.tsx` — Input component API
- [VERIFIED: codebase] `apps/helios/messages/en.json` — existing i18n keys, gap identified
- [VERIFIED: npm registry] nuqs 2.8.9 — latest version, `next >=14.2.0` peer dep
- [VERIFIED: Context7 /47ng/nuqs] `useQueryState`, `NuqsAdapter`, `parseAsString.withDefault`, `shallow` option

### Secondary (MEDIUM confidence)
- [CITED: MDN Intl.DateTimeFormat] `formatToParts` API for timezone-aware time extraction

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nuqs version verified via npm, all other libraries confirmed in package.json
- Architecture: HIGH — all integration points verified by reading actual source files
- Pitfalls: HIGH — most derived from direct code reading (existing sort logic, header structure)
- Grade sort direction: MEDIUM — logic is derived from spec, must be verified in manual QA

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable stack, 30-day window)
