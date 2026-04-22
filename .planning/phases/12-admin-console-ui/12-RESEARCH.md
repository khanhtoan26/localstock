# Phase 12: Admin Console UI - Research

**Researched:** 2026-04-22
**Domain:** React UI — admin dashboard with data tables, mutations, polling
**Confidence:** HIGH

## Summary

Phase 12 builds a single `/admin` page with three tabs (Stocks, Pipeline, Jobs) that consumes the 10 admin API endpoints built in Phase 11. The codebase already has all major UI components (Table, Tabs, Button, Input, Badge, Skeleton, EmptyState, ErrorState, Collapsible), established patterns for data fetching (TanStack Query hooks in `lib/queries.ts`), API calls (`apiFetch<T>()` in `lib/api.ts`), and i18n (`useTranslations()` from next-intl). Two new components need installation: **Checkbox** and **Toast** via shadcn CLI.

A detailed UI-SPEC (`12-UI-SPEC.md`) already exists with complete layout contracts, interaction flows, copywriting in both EN/VI, data flow contracts (TypeScript types + TanStack Query hook specs), and status badge color mappings. This phase is primarily a **UI assembly** task — wiring existing patterns together with new admin-specific types, hooks, and components. No new architectural patterns are needed.

**Primary recommendation:** Split implementation into 2-3 plans: (1) foundation (install components, add types, add query hooks, add i18n keys, add sidebar nav), (2) Stock Management tab + Pipeline tab, (3) Jobs tab with polling logic. The UI-SPEC should be followed as the authoritative visual/interaction contract.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single page at `/admin` with Tabs component (3 tabs: Stocks, Pipeline, Jobs). Add "Admin" nav item to sidebar with Shield icon. No sub-pages — everything on one page for quick access.
- **D-02:** Table of tracked stocks with inline add form at the top (Input field + "Add" button). Each row has a Remove (x) button. Symbol input validates uppercase pattern (matching backend `^[A-Z0-9]+$`). Shows symbol, name, exchange, industry columns.
- **D-03:** Checkbox selection in stock table rows. Action buttons (Crawl, Analyze, Score) operate on selected stocks. Pipeline button runs full pipeline for all tracked stocks. Buttons disabled when no stocks selected (except Pipeline). Each trigger returns job_id, switches user to Jobs tab to monitor.
- **D-04:** Table of recent jobs (from GET /api/admin/jobs) showing job_type, status, duration, created_at. Polling every 3 seconds via TanStack Query `refetchInterval` when any job has status='running' or 'pending'. Auto-stops polling when all jobs are done/failed. Click row to expand details (result/error from GET /api/admin/jobs/{id}).

### Agent's Discretion
- Component file structure (one file per tab vs separate files)
- Status badge colors (green=completed, red=failed, yellow=running, etc.)
- Empty state messaging
- Toast notifications for trigger confirmations
- i18n keys structure

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADMIN-05 | Stock Management UI — table of tracked stocks with add/remove buttons | Existing Table, Button, Input components + `useQuery`/`useMutation` pattern from `lib/queries.ts`. Backend: GET/POST/DELETE `/api/admin/stocks`. UI-SPEC defines layout, copy, interaction flows. |
| ADMIN-06 | Pipeline Control UI — buttons to trigger crawl, analyze, score, full pipeline for selected stocks | Existing Button component + new Checkbox (shadcn install). Backend: POST `/api/admin/crawl`, `/analyze`, `/score`, `/pipeline`. Checkbox selection state in React `useState`. Mutation hooks switch to Jobs tab on success. |
| ADMIN-07 | Job Monitor UI — table of recent jobs with status, duration, real-time updates | Existing Table + Badge + Collapsible components. Backend: GET `/api/admin/jobs`, `/api/admin/jobs/{id}`. TanStack Query `refetchInterval` for polling. Duration computed client-side from `completed_at - started_at`. |

</phase_requirements>

## Project Constraints (from copilot-instructions.md)

- **Stack lock:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui (base-nova preset), @base-ui/react
- **Data fetching:** TanStack Query (`@tanstack/react-query` ^5.99)
- **i18n:** next-intl with `useTranslations()` — all UI text must be in both `en.json` and `vi.json`
- **Icons:** lucide-react only
- **Styling:** Tailwind CSS 4 with CSS custom properties (no arbitrary color values — use design tokens)
- **Components:** shadcn/ui with base-nova preset, @base-ui/react primitives
- **GSD workflow enforcement:** All changes through GSD commands

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.4 | App framework | Already installed, App Router for `/admin` page [VERIFIED: package.json] |
| React | 19.2.4 | UI library | Already installed [VERIFIED: package.json] |
| @tanstack/react-query | ^5.99.0 | Data fetching, caching, polling | Already installed, established pattern in `lib/queries.ts` [VERIFIED: package.json] |
| @base-ui/react | ^1.4.0 | Component primitives | Already installed, shadcn base-nova preset uses this [VERIFIED: package.json] |
| next-intl | ^4.9.1 | i18n | Already installed, all UI text via `useTranslations()` [VERIFIED: package.json] |
| lucide-react | ^1.8.0 | Icons | Already installed [VERIFIED: package.json] |
| class-variance-authority | ^0.7.1 | Component variant styling | Already installed, used by Badge/Button [VERIFIED: package.json] |

### New Components (Install via shadcn CLI)

| Component | Install Command | Purpose |
|-----------|----------------|---------|
| Checkbox | `npx shadcn@latest add checkbox` | Stock row selection in Pipeline tab [VERIFIED: UI-SPEC] |
| Toast | `npx shadcn@latest add toast` | Operation confirmations, error feedback [VERIFIED: UI-SPEC] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TanStack Query polling | Server-Sent Events (SSE) | SSE provides true real-time but requires backend changes. Polling at 3s is simpler, within scope, and sufficient for job monitoring. Decision locked in D-04. |
| shadcn Checkbox | Native HTML checkbox | shadcn Checkbox integrates with @base-ui/react for consistent styling. Worth the install. |
| shadcn Toast | Browser `alert()` | Toast provides non-blocking feedback. Worth the install. |

**Installation (run in `apps/helios/`):**
```bash
npx shadcn@latest add checkbox
npx shadcn@latest add toast
```

## Architecture Patterns

### Recommended Project Structure

```
apps/helios/src/
├── app/
│   └── admin/
│       └── page.tsx                   # /admin page (single "use client" page)
├── components/
│   └── admin/
│       ├── stock-table.tsx            # Stocks tab content (table + inline add form)
│       ├── pipeline-control.tsx       # Pipeline tab content (action bar + checkbox table)
│       ├── job-monitor.tsx            # Jobs tab content (job table + expandable rows)
│       └── status-badge.tsx           # Job status badge helper (maps status → variant/colors)
├── lib/
│   ├── api.ts                         # (existing) apiFetch<T>()
│   ├── types.ts                       # (extend) Add admin types
│   └── queries.ts                     # (extend) Add admin query/mutation hooks
└── messages/
    ├── en.json                        # (extend) Add "admin" + "nav.admin" keys
    └── vi.json                        # (extend) Add "admin" + "nav.admin" keys
```

**Recommendation: Separate files per tab.** Each tab has distinct data fetching and interaction patterns. Separate files keep complexity manageable and make the planner's task boundaries clearer. [ASSUMED — agent's discretion area]

### Pattern 1: TanStack Query Hooks (Established Pattern)

**What:** All data fetching goes through typed hooks in `lib/queries.ts` using `useQuery` and `useMutation`.
**When to use:** Every API call from admin components.
**Example (from existing codebase):**

```typescript
// Source: apps/helios/src/lib/queries.ts (existing pattern)
export function useTrackedStocks() {
  return useQuery({
    queryKey: ["admin", "stocks"],
    queryFn: () => apiFetch<TrackedStocksResponse>("/api/admin/stocks"),
    staleTime: 30 * 1000, // 30 seconds — admin data changes more frequently
  });
}

export function useAddStock() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      apiFetch<{ symbol: string; message: string }>("/api/admin/stocks", {
        method: "POST",
        body: JSON.stringify({ symbol }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "stocks"] });
    },
  });
}
```

### Pattern 2: Conditional Polling with refetchInterval

**What:** TanStack Query `refetchInterval` can be a function that returns `false` to stop polling.
**When to use:** Job monitor — poll every 3s only when jobs are running/pending.
**Example:**

```typescript
// Source: @tanstack/react-query docs [VERIFIED: TanStack Query v5 API]
export function useAdminJobs(limit = 50) {
  return useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: () => apiFetch<AdminJobsResponse>(`/api/admin/jobs?limit=${limit}`),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      const hasActive = data.jobs.some(
        (j) => j.status === "running" || j.status === "pending"
      );
      return hasActive ? 3000 : false;
    },
  });
}
```

### Pattern 3: Tabs with Controlled State for Programmatic Switching

**What:** The Tabs component from `ui/tabs.tsx` wraps `@base-ui/react/tabs` which supports controlled `value` prop.
**When to use:** When triggering a pipeline operation, auto-switch to the Jobs tab.
**Example:**

```typescript
// Source: apps/helios/src/components/ui/tabs.tsx (uses @base-ui/react Tabs.Root)
const [activeTab, setActiveTab] = useState("stocks");

// In mutation onSuccess:
const triggerCrawl = useTriggerCrawl();
// When trigger succeeds, switch to jobs tab:
triggerCrawl.mutate(symbols, {
  onSuccess: () => setActiveTab("jobs"),
});

// In JSX:
<Tabs value={activeTab} onValueChange={setActiveTab}>
```

### Pattern 4: Mutation with Toast Feedback

**What:** `useMutation` `onSuccess`/`onError` callbacks trigger toast notifications.
**When to use:** Every admin mutation (add stock, remove stock, trigger operations).

### Anti-Patterns to Avoid

- **Don't fetch data inside components directly:** Always use TanStack Query hooks from `lib/queries.ts`. Never call `fetch()` or `apiFetch()` directly in components.
- **Don't hardcode strings:** All UI text goes through `useTranslations()` — no hardcoded English or Vietnamese strings in components.
- **Don't create custom loading spinners:** Use the `Loader2` icon from lucide-react with `animate-spin` class, and `Skeleton` for table loading states.
- **Don't use `useEffect` for polling:** TanStack Query's `refetchInterval` handles polling correctly with cache management and cleanup.
- **Don't duplicate stock data across tabs:** The Pipeline tab and Stocks tab both need the stock list. Use the same `useTrackedStocks()` hook — TanStack Query deduplicates requests via `queryKey`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data polling | Custom `setInterval` + `fetch` | TanStack Query `refetchInterval` | Handles cache invalidation, cleanup, error recovery automatically |
| Toast notifications | Custom notification system | shadcn Toast component | Consistent styling, accessibility, auto-dismiss |
| Table checkbox state | Complex reducer for selection | React `useState` with `Set<string>` | Simple enough for ~400 stocks max. Select all = set all symbols. |
| Form validation | Custom regex validation | HTML pattern attribute + controlled input | Backend validates too; client validation is just UX |
| Tab state sync | Custom event system | React `useState` + Tabs controlled mode | Single component owns state, passes down |
| Duration formatting | Custom date math | Simple `Math.round((end - start) / 1000)` + format | Only need seconds/minutes, not a library |

**Key insight:** This phase is UI assembly, not infrastructure. Every building block exists. The complexity is in wiring them together correctly, not in building new abstractions.

## Common Pitfalls

### Pitfall 1: Tabs value type mismatch with @base-ui/react
**What goes wrong:** The `@base-ui/react` Tabs component uses numeric indices by default. The shadcn wrapper supports string `value` props via the underlying `TabsPrimitive.Root`.
**Why it happens:** Confusion between @base-ui/react's native tab API and the shadcn wrapper's API.
**How to avoid:** Use the shadcn `Tabs` component with explicit `value` string prop. The `TabsTrigger` must also have a matching `value` prop. Check `tabs.tsx` — it wraps `TabsPrimitive.Root` from `@base-ui/react/tabs`.
**Warning signs:** Tabs don't switch, or switch to wrong content. [VERIFIED: apps/helios/src/components/ui/tabs.tsx]

### Pitfall 2: TanStack Query refetchInterval function signature (v5)
**What goes wrong:** `refetchInterval` as a function receives a `Query` object (not raw data) in TanStack Query v5.
**Why it happens:** API changed between v4 and v5.
**How to avoid:** Access data via `query.state.data`, not as a direct parameter. The function signature is `(query: Query) => number | false`.
**Warning signs:** TypeScript errors about parameter types, or polling never stops. [VERIFIED: TanStack Query v5 API]

### Pitfall 3: Mutation invalidation race condition
**What goes wrong:** After adding a stock, the stock list doesn't update because invalidation fires before the mutation response is processed.
**Why it happens:** `onSuccess` fires immediately after the response, but React Query may not refetch synchronously.
**How to avoid:** Use `queryClient.invalidateQueries()` in `onSuccess` — this is the standard pattern and works correctly. Avoid `onSettled` unless you need to handle errors too.
**Warning signs:** Stock list shows stale data after add/remove.

### Pitfall 4: 409 conflict handling for admin lock
**What goes wrong:** Backend returns 409 when an admin operation is already running (uses `asyncio.Lock`). Default error handling shows generic error.
**Why it happens:** `apiFetch` throws on non-200 status with generic message.
**How to avoid:** Check error response status in mutation `onError` callback. For 409, show specific toast message (`admin.toast.operationLocked`). May need to enhance `apiFetch` to include status code in thrown error, or catch and inspect the error.
**Warning signs:** User sees "API error: 409 Conflict" instead of friendly message. [VERIFIED: admin.py line 124 — `raise HTTPException(status_code=409)`]

### Pitfall 5: Checkbox selection state not clearing on stock list change
**What goes wrong:** User selects stocks, then adds/removes a stock. Selected set contains stale symbols.
**Why it happens:** Selection state (Set of symbols) isn't synchronized with stock list data.
**How to avoid:** Filter selection set against current stock list symbols whenever stock data changes, or clear selection on stock list mutation. Use a `useMemo` to intersect selection with current symbols.
**Warning signs:** "Crawl" button stays enabled but targets removed stocks.

### Pitfall 6: Toast component requires Toaster provider
**What goes wrong:** Toast calls do nothing — no visual feedback.
**Why it happens:** shadcn Toast pattern requires a `<Toaster />` component mounted in the layout.
**How to avoid:** After installing toast via shadcn, add `<Toaster />` to the layout (either `layout.tsx` or `app-shell.tsx`). The toast hook (`useToast` or `toast()`) won't work without this provider.
**Warning signs:** No toast appears despite `toast()` calls. [ASSUMED — standard shadcn pattern]

## Code Examples

### Admin Types (add to `lib/types.ts`)

```typescript
// Source: 12-UI-SPEC.md Data Flow Contract + admin.py response shapes
export interface TrackedStock {
  symbol: string;
  name: string | null;
  exchange: string | null;
  industry: string | null;
  is_tracked: boolean;
}

export interface TrackedStocksResponse {
  stocks: TrackedStock[];
  count: number;
}

export interface AdminJob {
  id: number;
  job_type: "crawl" | "analyze" | "score" | "report" | "pipeline";
  status: "pending" | "running" | "completed" | "failed";
  params: Record<string, unknown> | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AdminJobDetail extends AdminJob {
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface AdminJobsResponse {
  jobs: AdminJob[];
  count: number;
}

export interface TriggerResponse {
  job_id: number;
  status: string;
  job_type: string;
  symbols?: string[];
  symbol?: string;
}
```

### Sidebar Addition

```typescript
// Source: apps/helios/src/components/layout/sidebar.tsx (add Shield import + nav item)
import { BarChart3, Globe, BookOpen, Shield } from "lucide-react";

const navItems = [
  { href: "/rankings", label: t("rankings"), icon: BarChart3 },
  { href: "/market", label: t("market"), icon: Globe },
  { href: "/learn", label: t("learn"), icon: BookOpen },
  { href: "/admin", label: t("admin"), icon: Shield },
];
```

### Job Duration Formatting

```typescript
// Source: custom utility for admin phase
export function formatDuration(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt || !completedAt) return "—";
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}
```

### Status Badge Component

```typescript
// Source: 12-UI-SPEC.md Status Badge Color Map + globals.css token definitions
import { Badge } from "@/components/ui/badge";

const statusStyles: Record<string, string> = {
  completed: "bg-[hsl(var(--stock-up))]/10 text-[hsl(var(--stock-up))]",
  failed: "", // uses Badge variant="destructive"
  running: "bg-[hsl(var(--stock-warning))]/10 text-[hsl(var(--stock-warning))]",
  pending: "", // uses Badge variant="secondary"
};

export function StatusBadge({ status }: { status: string }) {
  if (status === "failed") return <Badge variant="destructive">{status}</Badge>;
  if (status === "pending") return <Badge variant="secondary">{status}</Badge>;
  return <Badge className={statusStyles[status]}>{status}</Badge>;
}
```

### 409 Error Handling Pattern

```typescript
// Pattern: Enhance apiFetch error or handle in mutation onError
// The current apiFetch throws with "API error: 409 Conflict" — need to detect 409 specifically

// Option A: Check error message in onError
onError: (error: Error) => {
  if (error.message.includes("409")) {
    toast({ description: t("admin.toast.operationLocked") });
  } else {
    toast({ description: t("admin.toast.error", { detail: error.message }), variant: "destructive" });
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| useEffect + setInterval polling | TanStack Query refetchInterval | TQ v4+ | Cleaner, auto-cleanup, cache-aware |
| React Context for server state | TanStack Query | TQ v3+ | Eliminates custom state management for API data |
| radix-ui primitives | @base-ui/react primitives | shadcn v4+ (base-nova) | This project uses base-nova preset — components use @base-ui/react, NOT @radix-ui |

**Deprecated/outdated:**
- **@radix-ui/react:** This project uses `@base-ui/react` via the base-nova preset. Do NOT import from radix. [VERIFIED: components.json shows `"style": "base-nova"`]
- **shadcn `useToast` hook:** Newer shadcn versions may use `sonner` instead. Need to verify which toast pattern shadcn generates with base-nova preset. [ASSUMED — check after `npx shadcn add toast`]

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Separate files per tab is recommended component structure | Architecture Patterns | LOW — purely organizational, easy to restructure |
| A2 | shadcn Toast requires `<Toaster />` provider in layout | Pitfall 6 | MEDIUM — if toast pattern differs for base-nova preset, implementation needs adjustment. Verify after `npx shadcn add toast`. |
| A3 | shadcn `toast` may use `sonner` internally for base-nova preset | State of the Art | LOW — either way, shadcn CLI generates the correct files. Just follow whatever it generates. |

**If this table is empty:** N/A — 3 assumed claims listed above.

## Open Questions

1. **shadcn Toast implementation for base-nova preset**
   - What we know: shadcn has two toast patterns — custom `useToast` hook or `sonner` library integration. The base-nova preset may use either.
   - What's unclear: Which pattern `npx shadcn add toast` generates with `"style": "base-nova"`.
   - Recommendation: Run `npx shadcn@latest add toast` early in implementation and inspect the generated files. Adjust toast usage pattern accordingly.

2. **Checkbox component API with @base-ui/react**
   - What we know: shadcn checkbox wraps `@base-ui/react/checkbox`, not `@radix-ui/react-checkbox`.
   - What's unclear: Exact prop interface (`checked`/`onCheckedChange` vs `checked`/`onChange`).
   - Recommendation: Run `npx shadcn@latest add checkbox` and inspect generated `checkbox.tsx`. The standard pattern should work with boolean `checked` and change handler.

3. **@base-ui/react Tabs controlled mode API**
   - What we know: The `Tabs` component wraps `TabsPrimitive.Root` from `@base-ui/react/tabs`. It passes `...props` through to the Root component.
   - What's unclear: Whether @base-ui/react Tabs.Root supports `value`/`onValueChange` props (Radix pattern) or uses `defaultValue` only.
   - Recommendation: Test controlled mode early. If @base-ui/react doesn't support `value`/`onValueChange`, use a ref-based approach or wrapper.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1+ (unit), Playwright 1.59+ (e2e) |
| Config file | `apps/helios/vitest.config.ts`, `apps/helios/playwright.config.ts` |
| Quick run command | `cd apps/helios && npx vitest run --reporter=verbose` |
| Full suite command | `cd apps/helios && npx vitest run && npx playwright test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-05 | Stock table renders tracked stocks | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "stock table"` | ❌ Wave 0 |
| ADMIN-05 | Add stock form submits and refreshes list | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "add stock"` | ❌ Wave 0 |
| ADMIN-05 | Remove stock button removes and refreshes | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "remove stock"` | ❌ Wave 0 |
| ADMIN-06 | Pipeline buttons trigger API calls | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "pipeline"` | ❌ Wave 0 |
| ADMIN-06 | Buttons disabled when no stocks selected | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "disabled"` | ❌ Wave 0 |
| ADMIN-07 | Job table displays job status | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "job table"` | ❌ Wave 0 |
| ADMIN-07 | Job polling activates for running jobs | unit | `cd apps/helios && npx vitest run src/lib/__tests__/admin-queries.test.ts` | ❌ Wave 0 |
| ADMIN-07 | Job row expands to show detail | e2e | `cd apps/helios && npx playwright test e2e/admin.spec.ts --grep "expand"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/helios && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd apps/helios && npx vitest run && npx playwright test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `apps/helios/e2e/admin.spec.ts` — covers ADMIN-05, ADMIN-06, ADMIN-07 (e2e tests)
- [ ] `apps/helios/src/lib/__tests__/admin-queries.test.ts` — covers polling logic unit test

*(Note: E2E tests require both backend and frontend running. Unit tests for query hooks are more reliable for CI.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Personal tool, no auth [VERIFIED: copilot-instructions.md "Multi-user / auth: Tool cá nhân"] |
| V3 Session Management | no | No sessions needed |
| V4 Access Control | no | Single user, local only |
| V5 Input Validation | yes | Symbol input validated client-side (`^[A-Z0-9]+$`) + backend Pydantic validation |
| V6 Cryptography | no | No sensitive data handling |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Script injection via stock symbol | Tampering | Backend Pydantic `pattern=r"^[A-Z0-9]+$"` rejects special chars. Client-side regex validation adds defense-in-depth. React JSX escapes by default. |
| API abuse (rapid triggers) | Denial of Service | Backend uses `asyncio.Lock` — only one admin operation at a time. Frontend disables buttons during in-flight mutations. |

## Sources

### Primary (HIGH confidence)
- `apps/helios/src/components/ui/tabs.tsx` — Tabs component API, @base-ui/react integration
- `apps/helios/src/components/ui/table.tsx` — Table component structure
- `apps/helios/src/components/ui/badge.tsx` — Badge variants and styling
- `apps/helios/src/components/ui/collapsible.tsx` — Collapsible for job row expansion
- `apps/helios/src/lib/queries.ts` — TanStack Query hook patterns (useQuery, useMutation)
- `apps/helios/src/lib/api.ts` — apiFetch<T>() implementation
- `apps/helios/src/lib/types.ts` — TypeScript type patterns
- `apps/helios/src/components/layout/sidebar.tsx` — Sidebar nav items pattern
- `apps/helios/src/app/rankings/page.tsx` — Page structure pattern
- `apps/helios/src/components/rankings/stock-table.tsx` — Table with sorting pattern
- `apps/helios/messages/en.json`, `vi.json` — i18n key structure
- `apps/helios/components.json` — shadcn config (style: base-nova, registries: {})
- `apps/helios/src/app/globals.css` — CSS tokens (--stock-up, --stock-warning, --destructive)
- `apps/prometheus/src/localstock/api/routes/admin.py` — All 10 admin endpoint signatures and response shapes
- `apps/prometheus/src/localstock/db/models.py` — AdminJob model (field names, types)
- `.planning/phases/12-admin-console-ui/12-UI-SPEC.md` — Complete visual/interaction contract
- `.planning/phases/12-admin-console-ui/12-CONTEXT.md` — Locked decisions D-01 through D-04

### Secondary (MEDIUM confidence)
- TanStack Query v5 `refetchInterval` function signature — based on training data for v5 API [ASSUMED — verify against TQ v5 docs if needed]

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and verified in package.json
- Architecture: HIGH — established patterns exist in codebase, UI-SPEC provides complete contract
- Pitfalls: HIGH — derived from actual code analysis (apiFetch error handling, admin.py 409 response, @base-ui/react component APIs)

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (stable — all dependencies locked in package.json)
