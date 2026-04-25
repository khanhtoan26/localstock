# Phase 16: Table, Search & Session Bar - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 10
**Analogs found:** 9 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/helios/src/components/rankings/stock-table.tsx` | component | request-response | self (modify in place) | exact |
| `apps/helios/src/app/rankings/page.tsx` | component (page) | request-response | self (modify in place) | exact |
| `apps/helios/src/components/layout/app-shell.tsx` | component (layout) | request-response | self (modify in place) | exact |
| `apps/helios/src/components/layout/market-session-bar.tsx` | component | event-driven (setInterval) | `src/components/theme/theme-toggle.tsx` | role-match |
| `apps/helios/src/components/rankings/stock-search-input.tsx` | component | request-response | `src/components/learn/glossary-search.tsx` | exact |
| `apps/helios/src/app/layout.tsx` | config (layout) | request-response | self (modify in place) | exact |
| `apps/helios/messages/en.json` | config (i18n) | — | self (modify in place) | exact |
| `apps/helios/messages/vi.json` | config (i18n) | — | self (modify in place) | exact |
| `apps/helios/tests/sort-comparator.test.ts` | test | — | `src/lib/__tests__/glossary-linker.test.ts` | role-match |
| `apps/helios/tests/search-filter.test.ts` | test | — | `src/lib/__tests__/glossary-linker.test.ts` | role-match |
| `apps/helios/tests/hose-session.test.ts` | test | — | `src/lib/__tests__/glossary-linker.test.ts` | role-match |

**Note on i18n file location:** CONTEXT.md references `public/locales/{en,vi}/common.json` but the actual codebase uses `apps/helios/messages/{en,vi}.json` (flat JSON, not nested under `public/locales/`). All i18n edits target `messages/en.json` and `messages/vi.json`.

---

## Pattern Assignments

### `apps/helios/src/components/rankings/stock-table.tsx` (component, modify in place)

**Analog:** self — current file at lines 1–107

**Imports pattern** (lines 1–16 of current file):
```tsx
"use client";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { GradeBadge } from "./grade-badge";
import { RecommendationBadge } from "@/components/stock/recommendation-badge";
import { formatScore } from "@/lib/utils";
import type { StockScore } from "@/lib/types";
import { useState } from "react";
```

**Add to imports — sort icons:**
```tsx
import { ChevronUp, ChevronDown } from "lucide-react";
```

**GRADE_RANK map — add above component:**
```tsx
const GRADE_RANK: Record<string, number> = {
  "A+": 1,
  "A": 2,
  "B+": 3,
  "B": 4,
  "C": 5,
};
```

**Sort comparator — replace lines 40–46 (current `sorted` block):**
```tsx
// D-01: tiebreaker; D-04: grade semantic; D-05: -Infinity for null
const sorted = [...data].sort((a, b) => {
  let aVal: number;
  let bVal: number;

  if (sortKey === "grade") {
    // Grade: rank 1 = best (A+). "desc" user intent = best first = sort ascending on rank number.
    aVal = GRADE_RANK[a.grade] ?? 99;
    bVal = GRADE_RANK[b.grade] ?? 99;
    if (aVal < bVal) return sortDir === "desc" ? -1 : 1;
    if (aVal > bVal) return sortDir === "desc" ? 1 : -1;
  } else {
    aVal = (a[sortKey] as number | null) ?? -Infinity;
    bVal = (b[sortKey] as number | null) ?? -Infinity;
    if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
  }
  // D-01: tiebreaker
  return a.symbol.localeCompare(b.symbol);
});
```

**Sort icon render — replace `sortIndicator` function (lines 48–49) and its usage in TableHead (line 73):**

Remove `sortIndicator` function entirely. In the `TableHead` render replace `{col.header}{sortIndicator(col.key)}` with:
```tsx
<span className="inline-flex items-center gap-0.5">
  {col.header}
  {sortKey === col.key && (
    <span className="inline-flex align-middle">
      {sortDir === "asc"
        ? <ChevronUp className="h-3 w-3" />
        : <ChevronDown className="h-3 w-3" />
      }
    </span>
  )}
</span>
```

**Guard recommendation column — add at top of `handleSort` (lines 31–38):**
```tsx
const handleSort = (key: SortKey) => {
  if (key === "recommendation") return; // D-03: not sortable
  if (sortKey === key) {
    setSortDir(sortDir === "asc" ? "desc" : "asc");
  } else {
    setSortKey(key);
    setSortDir("desc");
  }
};
```

**TableHead className — remove `cursor-pointer` for recommendation column:**
```tsx
<TableHead
  key={col.key}
  className={cn(
    col.width,
    "select-none text-xs hover:text-foreground",
    col.key !== "recommendation" && "cursor-pointer"
  )}
  onClick={() => handleSort(col.key)}
>
```
This requires adding `import { cn } from "@/lib/utils"` (already imported via formatScore file, but cn must be imported explicitly).

---

### `apps/helios/src/app/rankings/page.tsx` (page component, modify in place)

**Analog:** self — current file at lines 1–56

**Imports to add:**
```tsx
import { useQueryState, parseAsString } from "nuqs";
import { useMemo } from "react";
// NEW component (created this phase):
import { StockSearchInput } from "@/components/rankings/stock-search-input";
```

**Search state + filtered data — add inside `RankingsPage` before return statements:**
```tsx
const [q] = useQueryState("q", parseAsString.withDefault(""));

const filtered = useMemo(() => {
  if (!data?.stocks) return [];
  if (!q.trim()) return data.stocks;
  const lower = q.toLowerCase();
  return data.stocks.filter(
    (s) =>
      s.symbol.toLowerCase().startsWith(lower) ||
      (s.name ?? "").toLowerCase().includes(lower)
  );
}, [data?.stocks, q]);
```

**Final return — add `<StockSearchInput />` between title and table:**
```tsx
return (
  <div>
    <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
    <StockSearchInput />         {/* NEW: add between title and table */}
    <StockTable data={filtered} />  {/* CHANGED: filtered not data.stocks */}
  </div>
);
```

**Pattern note:** Filter logic stays in the page, not in StockTable (see anti-pattern in RESEARCH.md, Pitfall 6). `StockTable` receives `filtered` — its existing sort logic operates on the already-filtered list.

---

### `apps/helios/src/components/rankings/stock-search-input.tsx` (new component)

**Analog:** `apps/helios/src/components/learn/glossary-search.tsx` (exact analog — same role: search input with clear button, same pattern: local `useState` + filter)

**Full pattern from analog (glossary-search.tsx lines 1–80):**

```tsx
"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
```

**Imports pattern for new file** (differs: uses nuqs instead of local state for URL persistence):
```tsx
"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useQueryState, parseAsString } from "nuqs";
```

**Debounced nuqs pattern** (from RESEARCH.md Pattern 5):
```tsx
export function StockSearchInput() {
  const t = useTranslations("rankings.search");
  const [q, setQ] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: true })
  );
  const [localValue, setLocalValue] = useState(q);

  // Debounce: update URL only after 150ms idle (Claude's discretion)
  useEffect(() => {
    const timer = setTimeout(() => setQ(localValue || null), 150);
    return () => clearTimeout(timer);
  }, [localValue, setQ]);

  return (
    <div className="relative mb-4">
      <label htmlFor="rankings-search" className="sr-only">
        {t("placeholder")}
      </label>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      <Input
        id="rankings-search"
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setLocalValue("");
            setQ(null); // D-10 / Pitfall 4: null removes ?q= from URL
          }
        }}
        placeholder={t("placeholder")}
        className="h-9 w-full max-w-xs pl-10 pr-10"
      />
      {localValue && (
        <button
          onClick={() => { setLocalValue(""); setQ(null); }} // D-10
          className="absolute right-3 top-1/2 -translate-y-1/2"
          aria-label={t("clear")}
        >
          <X className="h-4 w-4 text-muted-foreground" />
        </button>
      )}
    </div>
  );
}
```

**Clear analog reference:** `glossary-search.tsx` lines 71–79 — `{query && <button onClick={() => setQuery("")}>}` with `aria-label={t("clearSearch")}` — same pattern, adapted to use `setQ(null)` for URL removal.

---

### `apps/helios/src/components/layout/market-session-bar.tsx` (new component)

**Analog:** `apps/helios/src/components/theme/theme-toggle.tsx` — closest match: pure `"use client"` component, header placement, uses `useSyncExternalStore`/`useMounted` SSR guard pattern.

**SSR hydration guard pattern** from `theme-toggle.tsx` lines 8–24:
```tsx
"use client";
import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};
function useMounted() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}

export function ThemeToggle() {
  const mounted = useMounted();
  if (!mounted) {
    return <Button variant="ghost" size="icon" ...>...</Button>; // SSR placeholder
  }
  // real render
}
```

**Apply same SSR guard to MarketSessionBar** — the component calls `Date.now()` which differs between server and client, so a hydration guard is required.

**Progress component pattern** from `apps/helios/src/components/ui/progress.tsx` lines 1–52:
```tsx
import { ProgressTrack, ProgressIndicator } from "@/components/ui/progress";

// Usage with direct track/indicator (no Root wrapper needed for slim bar):
<ProgressTrack className="w-24 h-1">
  <ProgressIndicator style={{ width: `${pct}%` }} />
</ProgressTrack>
```
Note: `ProgressTrack` uses `bg-muted` and `rounded-full h-1` by default; `ProgressIndicator` uses `bg-primary`. These token-based classes satisfy the CSS variable requirement (D-11, no hardcoded colors).

**Full component structure for market-session-bar.tsx:**
```tsx
"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";
import { ProgressTrack, ProgressIndicator } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

// SSR guard (same pattern as theme-toggle.tsx)
const emptySubscribe = () => () => {};
function useMounted() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}

// HOSE phase boundaries (D-14): all times in UTC+7 / Asia/Ho_Chi_Minh
// TODO: Add Vietnamese public holiday awareness (Tết, 30/4, 2/9, etc.) — deferred to v2
const PHASES = [
  { label: "Pre-market", start: [8, 30],  end: [9, 0]   },
  { label: "ATO",        start: [9, 0],   end: [9, 15]  },
  { label: "Morning",    start: [9, 15],  end: [11, 30] },
  { label: "Lunch",      start: [11, 30], end: [13, 0]  },
  { label: "Afternoon",  start: [13, 0],  end: [14, 30] },
  { label: "ATC",        start: [14, 30], end: [14, 45] },
] as const;

// Use Intl.DateTimeFormat.formatToParts for reliable IANA timezone extraction (RESEARCH Pattern 4)
function getVNTimeParts(now: Date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "numeric", minute: "numeric", hour12: false,
  }).formatToParts(now);
  const h = parseInt(parts.find((p) => p.type === "hour")!.value, 10);
  const m = parseInt(parts.find((p) => p.type === "minute")!.value, 10);
  const dow = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].indexOf(
    now.toLocaleString("en-US", { timeZone: "Asia/Ho_Chi_Minh", weekday: "short" })
  );
  return { h, m, dow };
}
```

**setInterval refresh pattern** (1-minute interval, D-13):
```tsx
useEffect(() => {
  const id = setInterval(() => setNow(new Date()), 60_000);
  return () => clearInterval(id);
}, []);
```

**i18n integration for session labels** — use `useTranslations("sessionBar")` consistent with all other components.

---

### `apps/helios/src/components/layout/app-shell.tsx` (layout, modify in place)

**Analog:** self — current file lines 1–62

**Header div — current structure (lines 20–41):**
```tsx
<header className="shrink-0 h-12 flex items-center justify-between px-4 border-b border-border bg-card z-40">
  <div className="flex items-center gap-3">
    {/* toggle + logo */}
  </div>
  <div className="flex items-center gap-2">
    <LanguageToggle />
    <ThemeToggle />
  </div>
</header>
```

**Modified header — insert center flex-1 section (D-11, RESEARCH integration point):**
```tsx
<header className="shrink-0 h-12 flex items-center justify-between px-4 border-b border-border bg-card z-40">
  <div className="flex items-center gap-3">
    {/* toggle + logo — unchanged */}
  </div>

  {/* NEW: center flex-1 for MarketSessionBar (D-11) */}
  <div className="flex-1 flex items-center justify-center sm:block hidden">
    <MarketSessionBar />
  </div>

  <div className="flex items-center gap-2">
    <LanguageToggle />
    <ThemeToggle />
  </div>
</header>
```

**Import to add:**
```tsx
import { MarketSessionBar } from "./market-session-bar";
```

**Pattern note:** `justify-between` is preserved on the header — the `flex-1` center div pushes right controls to the edge while centering the session bar. `sm:block hidden` hides the bar on very small screens (Claude's discretion per CONTEXT.md).

---

### `apps/helios/src/app/layout.tsx` (root layout, modify in place)

**Analog:** self — current file lines 1–52

**Current provider nesting (lines 42–50):**
```tsx
<NextIntlClientProvider messages={messages}>
  <ThemeProvider>
    <QueryProvider>
      <AppShell>{children}</AppShell>
    </QueryProvider>
  </ThemeProvider>
</NextIntlClientProvider>
```

**Import to add:**
```tsx
import { NuqsAdapter } from "nuqs/adapters/next/app";
```

**Modified nesting — wrap AppShell with NuqsAdapter (RESEARCH Pattern 2, A3):**
```tsx
<NextIntlClientProvider messages={messages}>
  <ThemeProvider>
    <QueryProvider>
      <NuqsAdapter>
        <AppShell>{children}</AppShell>
      </NuqsAdapter>
    </QueryProvider>
  </ThemeProvider>
</NextIntlClientProvider>
```

**Pattern note:** `NuqsAdapter` only needs to wrap any ancestor of components calling `useQueryState`. Wrapping `AppShell` is the minimal correct insertion (RESEARCH A3). Must be present before any `useQueryState` call — do not omit or nuqs will throw at runtime (Pitfall 1).

---

### `apps/helios/messages/en.json` (i18n config, modify in place)

**Analog:** self — current file at `rankings` key (lines 36–50) and `learn.glossary` key (lines 127–148) for clear button pattern.

**Add `rankings.search` sub-key** (sibling to existing `rankings.columns`):
```json
"rankings": {
  "title": "Stock Rankings",
  "emptyBody": "...",
  "search": {
    "placeholder": "Search by symbol...",
    "clear": "Clear search",
    "noResults": "No stocks match \"{query}\""
  },
  "columns": { ... }
}
```

**Add `sessionBar` top-level key** (sibling to `rankings`, `market`, etc.):
```json
"sessionBar": {
  "preMarket": "Pre-market",
  "ato": "ATO",
  "morning": "Morning",
  "lunch": "Lunch",
  "afternoon": "Afternoon",
  "atc": "ATC",
  "closed": "Closed",
  "left": "{time} left",
  "opensIn": "Opens in {time}"
}
```

**Pattern note:** Interpolation syntax `{param}` matches existing patterns e.g. `"removeConfirmDescription": "Are you sure you want to remove {symbol}..."` (en.json line 184). Use the same `{param}` tokens for `left` and `opensIn`.

---

### `apps/helios/messages/vi.json` (i18n config, modify in place)

**Analog:** self — same structure as en.json but in Vietnamese. Current `rankings` block starts at line 36 (mirrors en.json).

**Add same keys in Vietnamese:**
```json
"rankings": {
  "search": {
    "placeholder": "Tìm theo mã CK...",
    "clear": "Xóa tìm kiếm",
    "noResults": "Không có cổ phiếu nào khớp với \"{query}\""
  }
}
```
```json
"sessionBar": {
  "preMarket": "Trước giờ",
  "ato": "ATO",
  "morning": "Buổi sáng",
  "lunch": "Nghỉ trưa",
  "afternoon": "Buổi chiều",
  "atc": "ATC",
  "closed": "Đóng cửa",
  "left": "còn {time}",
  "opensIn": "Mở cửa sau {time}"
}
```

---

### `apps/helios/tests/sort-comparator.test.ts` (new test file)

**Analog:** `apps/helios/src/lib/__tests__/glossary-linker.test.ts` — only existing vitest test in the project.

**Test file structure pattern** (glossary-linker.test.ts lines 1–10):
```ts
import { describe, it, expect } from "vitest";
// import the pure function under test

describe("functionName", () => {
  it("description of behavior", () => {
    expect(result).toBe(expected);
  });
});
```

**Vitest config context** (`apps/helios/vitest.config.ts`):
- `globals: true` — `describe/it/expect` are global, but explicit import is fine and preferred
- `resolve.alias["@"]` → `./src` — path alias works in test files
- Test command: `npx vitest run` from `apps/helios/`
- **File location:** `apps/helios/tests/sort-comparator.test.ts` (flat `tests/` at package root, not `src/lib/__tests__/`)

**Test coverage targets for sort-comparator.test.ts:**
```ts
import { describe, it, expect } from "vitest";
// Import the comparator logic (extract to a pure function or test via sorted array)

describe("sort comparator", () => {
  it("numeric desc: higher score appears first");
  it("numeric asc: lower score appears first");
  it("null values use -Infinity sentinel — appear last in desc");
  it("tiebreaker: equal values sorted A→Z by symbol");
  it("grade desc: A+ appears before C (A+ has rank 1, C has rank 5)");
  it("grade asc: C appears before A+");
  it("grade unknown string falls back to rank 99 — appears last");
  it("recommendation column: handleSort returns early, sort state unchanged");
});
```

---

### `apps/helios/tests/search-filter.test.ts` (new test file)

**Analog:** `apps/helios/src/lib/__tests__/glossary-linker.test.ts`

**Test coverage targets:**
```ts
describe("search filter", () => {
  it("empty query returns all stocks");
  it("matches symbol prefix case-insensitively: 'vnm' matches 'VNM'");
  it("does NOT match symbol substring that isn't a prefix: 'NM' does not match 'VNM'");
  it("name substring match: 'vinamilk' matches stock with name containing 'Vinamilk'");
  it("name field undefined/null: treated as empty string, no crash");
  it("trims whitespace before filtering");
});
```

---

### `apps/helios/tests/hose-session.test.ts` (new test file)

**Analog:** `apps/helios/src/lib/__tests__/glossary-linker.test.ts`

**Test coverage targets (RESEARCH Validation, Wave 0 Gaps):**
```ts
describe("getVNTimeParts", () => {
  it("converts UTC timestamp to correct Vietnam hour/minute");
  it("handles UTC midnight correctly (should be 07:00 VN time — Pitfall 5)");
});

describe("getCurrentHosePhase", () => {
  it("returns Pre-market for 08:45 VN on weekday");
  it("returns ATO for 09:05 VN on weekday");
  it("returns Morning for 10:00 VN on weekday");
  it("returns Lunch for 12:00 VN on weekday");
  it("returns Afternoon for 13:30 VN on weekday");
  it("returns ATC for 14:35 VN on weekday");
  it("returns Closed for 15:00 VN on weekday");
  it("returns Closed with weekend countdown on Saturday");
  it("returns Closed with weekend countdown on Sunday");
  it("progress pct is 0 when Closed");
  it("progress pct is between 0 and 100 during active phase");
});
```

---

## Shared Patterns

### "use client" Declaration
**Source:** All interactive components (stock-table.tsx line 1, app-shell.tsx line 1, glossary-search.tsx line 1)
**Apply to:** `market-session-bar.tsx`, `stock-search-input.tsx`
```tsx
"use client";
```
Must be the first line of the file, before any imports.

### CSS Token Approach (No Hardcoded Colors)
**Source:** `apps/helios/src/components/ui/progress.tsx` lines 28–38
**Apply to:** `market-session-bar.tsx` progress bar, all new UI elements
```tsx
// ProgressTrack uses bg-muted
// ProgressIndicator uses bg-primary
// Text uses text-muted-foreground, text-foreground
// Never use hex colors like #6b7280 — use var(--muted-foreground)
<ProgressTrack className="w-24 h-1">
  <ProgressIndicator style={{ width: `${pct}%` }} />
</ProgressTrack>
```

### i18n with useTranslations
**Source:** `apps/helios/src/components/rankings/stock-table.tsx` lines 27, `apps/helios/src/app/rankings/page.tsx` lines 13–14
**Apply to:** `stock-search-input.tsx`, `market-session-bar.tsx`
```tsx
const t = useTranslations("rankings.search");
// or
const t = useTranslations("sessionBar");
// Usage: t("placeholder"), t("clear"), t("left", { time: "8m" })
```

### cn() Conditional Classes
**Source:** `apps/helios/src/components/layout/app-shell.tsx` line 51, `apps/helios/src/components/ui/progress.tsx` line 5
**Apply to:** Any component with conditional classNames
```tsx
import { cn } from "@/lib/utils";
// Usage:
className={cn("base-class", condition && "conditional-class")}
```

### Search Input with Clear Button
**Source:** `apps/helios/src/components/learn/glossary-search.tsx` lines 52–80
**Apply to:** `stock-search-input.tsx`
```tsx
<div className="relative">
  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
  <Input
    type="text"
    value={localValue}
    onChange={(e) => setLocalValue(e.target.value)}
    className="h-9 w-full pl-10 pr-10"
  />
  {localValue && (
    <button
      onClick={() => { setLocalValue(""); setQ(null); }}
      className="absolute right-3 top-1/2 -translate-y-1/2"
      aria-label={t("clear")}
    >
      <X className="h-4 w-4 text-muted-foreground" />
    </button>
  )}
</div>
```

### SSR Hydration Guard (useSyncExternalStore)
**Source:** `apps/helios/src/components/theme/theme-toggle.tsx` lines 8–25
**Apply to:** `market-session-bar.tsx` (uses `Date.now()` which differs server/client)
```tsx
const emptySubscribe = () => () => {};
function useMounted() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}
// In component: if (!mounted) return <skeleton/placeholder>;
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `apps/helios/src/components/layout/market-session-bar.tsx` | component | event-driven | No existing timer/interval-driven display component in codebase. Pattern assembled from theme-toggle.tsx (SSR guard) + progress.tsx (bar) + RESEARCH patterns (HOSE timezone, setInterval). |

---

## Critical Implementation Notes

1. **nuqs must be installed before any test run:** `cd apps/helios && npm install nuqs` is a prerequisite step. The package is confirmed at version 2.8.9 (RESEARCH.md verified).

2. **Grade sort direction inversion (Pitfall 2):** When `sortDir === "desc"` for grade, the comparator sorts *ascending* on GRADE_RANK numbers (rank 1 = A+ = best = first). The comparator branch for grade flips the direction relative to numeric columns. This is intentional and must be preserved.

3. **i18n file is `messages/`, not `public/locales/`:** CONTEXT.md references `public/locales/{en,vi}/common.json` but the actual project uses `apps/helios/messages/en.json` and `apps/helios/messages/vi.json`. The planner must target the correct path.

4. **StockScore has no `name` field:** The `name` substring filter branch `(s.name ?? "").toLowerCase().includes(lower)` is forward-compatible dead code for now — it costs nothing and does not break TypeScript if written defensively.

5. **Test file location:** The only existing test in `apps/helios` is at `src/lib/__tests__/glossary-linker.test.ts`. The three new test files go in `apps/helios/tests/` (flat, at package root) per RESEARCH.md Validation Architecture section.

---

## Metadata

**Analog search scope:** `apps/helios/src/components/`, `apps/helios/src/app/`, `apps/helios/src/lib/`, `apps/helios/messages/`, `apps/helios/vitest.config.ts`
**Files scanned:** 13 source files read directly
**Pattern extraction date:** 2026-04-24
