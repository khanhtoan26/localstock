# Domain Pitfalls — LocalStock v1.3

**Domain:** Stock analysis dashboard — UI/UX refinement
**Researched:** 2026-04-24

## Critical Pitfalls

### Pitfall 1: Font Variable Name Collision with Tailwind v4

**What goes wrong:** `next/font/google` with `variable: '--font-sans'` injects a CSS custom property on `<html>`. But the existing `@theme inline` block maps `--font-sans: var(--font-sans)` — a **circular reference** that resolves to the initial value (empty/inherit). Meanwhile, the body rule has `font-family: system-ui, -apple-system, sans-serif` which overrides the variable chain entirely.

**Why it happens:** Two competing font assignment paths: (1) CSS variable chain via `@theme inline` and (2) hardcoded `font-family` in body rule. If either is wrong, the font silently falls back.

**Consequences:** Font silently falls back to browser default or system-ui. No error appears — just wrong typography everywhere.

**Prevention:**
1. Apply `sourceSans.variable` as `className` on `<html>` element in `layout.tsx`
2. **Remove** the hardcoded `font-family: system-ui, -apple-system, sans-serif` from the body rule in `globals.css`
3. Verify the `@theme inline` `--font-sans` resolves correctly — `next/font` sets the variable at a higher specificity than theme defaults

**Detection:** DevTools → Computed tab → check `font-family` on `body`. If it shows `system-ui` instead of `"Source Sans 3"`, the chain is broken.

### Pitfall 2: Sidebar Overlay Blocking Click Events

**What goes wrong:** Float sidebar at `z-40` overlays main content when expanded. Users can see content beneath but can't click it. No way to close sidebar by clicking outside.

**Why it happens:** Without a backdrop element, the sidebar just sits on top. No click-outside-to-close behavior.

**Consequences:** Users get stuck — sidebar covers content, must find the collapse button.

**Prevention:**
1. Add a transparent backdrop div (`fixed inset-0 z-30`) when sidebar is expanded
2. Backdrop click → collapse sidebar
3. Sidebar sits at `z-40` above backdrop
4. Main content is at `z-0` — unaffected when sidebar is collapsed

**Detection:** Manual test — expand sidebar, try clicking content underneath.

### Pitfall 3: nuqs + next-intl Provider Ordering

**What goes wrong:** Both `NuqsAdapter` and `NextIntlClientProvider` wrap the app. Wrong ordering can cause hydration mismatches or URL search params not syncing with locale-based routing.

**Why it happens:** `NuqsAdapter` reads/writes `window.location` search params. If next-intl's locale routing interferes, params may not persist correctly.

**Consequences:** Hydration warnings, search params lost on navigation, or URL conflicts with locale prefixes.

**Prevention:**
1. Place `NuqsAdapter` **inside** `QueryProvider` and **outside** `AppShell`
2. Provider order: `NextIntlClientProvider → ThemeProvider → QueryProvider → NuqsAdapter → AppShell`
3. Test: navigate `/rankings?q=VNM` → `/market` → back → verify `q=VNM` survives

**Detection:** Navigate between routes with search params and verify URL state persists.

## Moderate Pitfalls

### Pitfall 4: Warm Primary Color Clashing with Financial Semantics

**What goes wrong:** Changing `--primary` from blue to warm terracotta creates visual confusion with `--stock-warning: hsl(48 96% 40%)` (yellow-gold) and `--chart-4: hsl(15 54.2% 51.2%)` (existing terracotta). Primary buttons look like "warning" or blend with chart colors.

**Prevention:**
1. Ensure new primary hue is distinct from `--stock-warning` (yellow ~48deg) and existing `--chart-4` (terracotta ~15deg). Target ~24deg (orange-terracotta) provides separation from both.
2. Test primary buttons alongside stock-up (green), stock-down (red), and warning badges
3. If using existing `--chart-4` as primary, reassign chart-4 to a different color

### Pitfall 5: Market Session Bar Timezone Assumptions

**What goes wrong:** Using `new Date().getHours()` assumes user's local timezone matches ICT (UTC+7). If machine is in a different timezone, session indicators are wrong.

**Prevention:**
1. Always use `Intl.DateTimeFormat` with `timeZone: 'Asia/Ho_Chi_Minh'`
2. Never use `getHours()` / `getMinutes()` directly
3. Add "ICT" label next to time display for clarity
4. Test by changing system timezone

### Pitfall 6: Sidebar Collapse Flash on Page Load

**What goes wrong:** Sidebar renders expanded (SSR default), then collapses after `useEffect` reads `localStorage`. Visual flash — sidebar jumps from 240px to 56px.

**Prevention:**
1. Use `useState` lazy initializer with `typeof window !== 'undefined'` guard:
   ```typescript
   const [collapsed, setCollapsed] = useState(() => {
     if (typeof window === 'undefined') return false;
     return localStorage.getItem('sidebar-collapsed') === 'true';
   });
   ```
2. This works because `useState` lazy init runs synchronously during first render — no flash
3. Alternative: inline `<script>` in `<head>` that sets a `data-sidebar-collapsed` attribute (similar to existing theme flash prevention)

### Pitfall 7: Sort State in URL Polluting Browser History

**What goes wrong:** Using `nuqs` for sort column + direction means every sort click creates a URL history entry. User hits "back" and gets previous sort state instead of previous page.

**Prevention:**
1. Use `history: 'replace'` option for sort params:
   ```typescript
   const [sortKey, setSortKey] = useQueryState('sort',
     parseAsString.withDefault('total_score').withOptions({ history: 'replace' })
   );
   ```
2. Only search query (`q`) should use default `push` history
3. Sort direction (`dir`) should also use `replace`

## Minor Pitfalls

### Pitfall 8: Tooltip Positioning at Screen Edges

**What goes wrong:** Collapsed sidebar tooltips on bottom nav items may overflow below viewport.

**Prevention:** Set tooltip `side="right"` since sidebar is on the left. Base UI tooltip handles collision detection, but explicit `side` ensures correct default.

### Pitfall 9: Progress Bar Useless During Closed Hours

**What goes wrong:** Market session bar shows "Closed" for ~18 hours/day and all weekend. Component feels wasted.

**Prevention:**
1. During closed hours: show "Opens in Xh Ym" countdown
2. On weekends: show "Reopens Monday 9:00"
3. During trading: show session name + progress + time remaining
4. Don't hide — transform display for context

### Pitfall 10: Market Overview Backend API Not Ready

**What goes wrong:** `GET /api/market/overview` doesn't exist yet. Component shows error state.

**Prevention:**
1. Build with graceful fallback: skeleton → error → "Coming soon" message
2. Use existing macro data as interim display
3. Make this the last feature in the phase
4. Define API contract upfront so backend can implement in parallel

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Font + Color | Font variable collision (P1) | Test computed styles immediately |
| Font + Color | Warm color vs financial semantics (P4) | Side-by-side visual test |
| Sidebar | Overlay click blocking (P2) | Backdrop element |
| Sidebar | Collapse flash (P6) | useState lazy initializer |
| Search persistence | nuqs + next-intl conflict (P3) | Provider ordering test |
| Search persistence | Sort polluting history (P7) | `history: 'replace'` |
| Market session bar | Timezone assumption (P5) | `Intl.DateTimeFormat` always |
| Market metrics | Backend API not ready (P10) | Build last, graceful fallback |

## Sources

- Direct code inspection of `globals.css` (lines 53–136), `layout.tsx`, `sidebar.tsx`, `stock-table.tsx`, `app-shell.tsx`
- `nuqs` v2 documentation: history mode options (`push` vs `replace`)
- `next/font` documentation: CSS variable injection via `variable` prop
- MDN `Intl.DateTimeFormat.formatToParts()`: structured timezone-aware date parts
- Existing codebase patterns: `next-themes` inline script for flash prevention (analogous to sidebar flash)
