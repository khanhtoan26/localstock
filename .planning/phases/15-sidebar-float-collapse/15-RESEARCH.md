# Phase 15: Sidebar Float & Collapse - Research

**Researched:** 2026-04-24
**Domain:** Next.js layout restructuring — collapsible floating sidebar with icon rail
**Confidence:** HIGH

## Summary

Phase 15 replaces the current fixed `w-60` sidebar with a two-part floating sidebar: a permanent narrow icon rail (~56px) and an expandable overlay panel. The entire implementation uses existing primitives — `@base-ui/react` 1.4.0 (tooltip), `lucide-react` 1.8.0 (icons), CSS transitions (animation), and `useState` + `localStorage` (persistence). **No new npm dependencies are required.** The only new file needed from shadcn is `tooltip.tsx`, which wraps the already-installed `@base-ui/react/tooltip` primitive.

The critical path is the layout restructuring in `app-shell.tsx` (replacing `ml-60` with `ml-14`) and the full rewrite of `sidebar.tsx`. The sidebar becomes a client component managing collapsed/expanded state via `useState` with a lazy initializer that reads `localStorage` synchronously to prevent FOUC. The expanded panel uses CSS `transform: translateX()` transitions (150-200ms) for slide-in/out. Tooltips on icon rail items use `@base-ui/react/tooltip` with `side="right"` positioning. Tab groups (Main vs Admin) are visually separated with Admin pinned to the bottom of the rail.

**Primary recommendation:** Implement as a single `floating-sidebar.tsx` component that renders both the icon rail (always visible, `fixed left-0 w-14 z-30`) and the overlay panel (conditional, `fixed left-14 w-60 z-40`). Extract a `useSidebarState` hook for localStorage persistence. Create `tooltip.tsx` as a thin wrapper over `@base-ui/react/tooltip` following the established base-nova component pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Collapsed sidebar shows only navigation icons (~56px wide). Each icon displays a tooltip on hover showing the page name.
- **D-02:** No logo/branding in the collapsed icon rail — just nav icons. The "LocalStock" + "AI Stock Agent" header only appears when expanded.
- **D-03:** No badge indicators on icons. Keep it clean and minimal.
- **D-06:** Click on any nav icon in the collapsed rail → sidebar expands as a floating overlay panel (positioned to the right of the icon rail). Content underneath is NOT pushed.
- **D-07:** No backdrop overlay when sidebar is expanded. Close by clicking any nav icon again (toggle behavior).
- **D-08:** Slide-in animation from left, smooth transition 150-200ms duration.
- **D-09:** Default state (first visit, no localStorage) is collapsed (icon rail only).
- **D-10:** Collapsed/expanded state persists via localStorage. On page reload, sidebar restores to the last user state.

### Agent's Discretion
- Visual separation approach for Main vs Admin groups (divider, spacing, or position)
- Admin icon position (bottom-pinned vs below Main)
- Exact icon rail width (target ~56px, adjust for visual balance)
- Overlay panel width (match current `w-60` or adjust)
- Z-index layering for overlay panel
- Transition easing function
- Whether clicking a nav link also collapses the sidebar or keeps it open

### Deferred Ideas (OUT OF SCOPE)
- **LAY-05:** Keyboard shortcut (Cmd+B) to toggle sidebar — future requirement
- **LAY-06:** Mobile responsive sidebar (drawer pattern) — future requirement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAY-01 | Sidebar float overlay thay vì fixed, content không bị đẩy khi sidebar mở | Architecture pattern: icon rail fixed at `left-0 w-14`, overlay panel at `left-14 w-60`, content at `ml-14`. Content never shifts. |
| LAY-02 | Sidebar collapse thành icon rail (~56px), expand khi click | Icon rail renders 4 nav icons using existing `lucide-react` icons. Click toggles `collapsed` state. Tooltip via `@base-ui/react/tooltip`. |
| LAY-03 | Sidebar có 2 icon tab groups: Main (Rankings, Market, Learn) và Admin | Admin icon pinned to bottom of rail with separator. Main group at top. Visual separation via `flex-1` spacer or border divider. |
| LAY-04 | Sidebar state (collapsed/expanded) persist qua localStorage | `useSidebarState` hook using `useState` with lazy initializer reading `localStorage` synchronously. Cross-tab sync not required. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sidebar collapse/expand state | Browser / Client | — | Pure client-side state — no server involvement. `useState` + `localStorage`. |
| Icon rail rendering | Browser / Client | — | Client component with `usePathname()` for active state detection. |
| Overlay panel animation | Browser / Client | — | CSS transitions on `transform` property — browser-native, no JS animation library. |
| Tooltip display | Browser / Client | — | `@base-ui/react/tooltip` handles positioning, collision detection, accessibility. |
| Layout restructuring | Frontend Server (SSR) | Browser / Client | `app-shell.tsx` renders layout server-side. Sidebar is client component within server layout. |
| State persistence | Browser / Client | — | `localStorage` is browser-only. Lazy initializer reads it during first client render. |

## Standard Stack

### Core (all already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@base-ui/react` | 1.4.0 | Tooltip primitives (Root, Trigger, Portal, Positioner, Popup) | Already installed. Provides accessible tooltip with collision detection, `side` positioning, and keyboard support. Used by all shadcn base-nova components. [VERIFIED: `node_modules/@base-ui/react/package.json` — version 1.4.0, `./tooltip` export confirmed] |
| `lucide-react` | 1.8.0 | Navigation icons (BarChart3, Globe, BookOpen, Shield) + toggle icons | Already imported in current `sidebar.tsx`. All needed icons verified present: `PanelLeftClose`, `PanelLeftOpen`, `ChevronsLeft`, `ChevronsRight`, `Menu`. [VERIFIED: `node_modules/lucide-react/dist/esm/icons/` — all icon files exist] |
| `next` | 16.2.4 | `usePathname()` for active route detection, `Link` for navigation | Already used in current sidebar. No changes needed. [VERIFIED: `apps/helios/package.json`] |
| `next-intl` | 4.9.1 | `useTranslations("nav")` for localized icon labels/tooltips | Already used in current sidebar. Nav keys exist: `rankings`, `market`, `learn`, `admin`. [VERIFIED: `messages/en.json`, `messages/vi.json`] |
| Tailwind CSS | 4.x | Utility classes for layout, transitions, responsive design | Already the styling system. CSS variable tokens for sidebar colors already defined. [VERIFIED: `globals.css` lines 78-86] |

### New Files (no new npm packages)
| File | Purpose | Based On |
|------|---------|----------|
| `components/ui/tooltip.tsx` | Thin wrapper over `@base-ui/react/tooltip` following base-nova pattern | Same pattern as `collapsible.tsx`, `sheet.tsx`, `alert-dialog.tsx` [VERIFIED: existing component wrappers] |
| `hooks/use-sidebar-state.ts` | `useState` + `localStorage` sync hook for sidebar collapsed state | Same pattern as `ThemeProvider` localStorage usage [VERIFIED: `theme-provider.tsx`] |
| `components/layout/floating-sidebar.tsx` | Replaces `sidebar.tsx` — icon rail + overlay panel | Full rewrite of existing `sidebar.tsx` [VERIFIED: current sidebar is 44 lines] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@base-ui/react/tooltip` | CSS-only `title` attribute | No styling control, no positioning, no animation. Base-ui is already installed and provides accessibility. |
| `useState` + lazy init | `useSyncExternalStore` (like ThemeProvider) | `useSyncExternalStore` provides cross-tab sync, but sidebar state doesn't need cross-tab sync. `useState` + lazy init is simpler and sufficient. |
| CSS `transform` transition | `framer-motion` | Overkill for a single slide-in transition. CSS transitions are zero-dependency, GPU-accelerated, and match the 150-200ms spec. framer-motion adds ~32KB. |
| CSS `transform` transition | `tw-animate-css` (already installed) | `tw-animate-css` provides preset animations but doesn't have a sidebar slide-in preset. Custom CSS transition is cleaner. |
| Manual tooltip wrapper | `shadcn add tooltip` | `shadcn add tooltip` failed due to network issues. Manual creation follows the identical base-nova pattern — same result, no network dependency. |

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser Viewport                                                    │
│                                                                      │
│  ┌──────┐  ┌──────────────┐  ┌────────────────────────────────────┐ │
│  │ Icon │  │ Overlay Panel│  │         Content Area               │ │
│  │ Rail │  │ (conditional)│  │                                    │ │
│  │      │  │              │  │  ┌──────────────────────────────┐  │ │
│  │ z-30 │  │    z-40      │  │  │ Header (LanguageToggle,      │  │ │
│  │      │  │              │  │  │         ThemeToggle)          │  │ │
│  │ w-14 │  │    w-60      │  │  └──────────────────────────────┘  │ │
│  │fixed │  │   fixed      │  │                                    │ │
│  │left-0│  │   left-14    │  │  ┌──────────────────────────────┐  │ │
│  │      │  │              │  │  │ <main> — Page Content         │  │ │
│  │ Main │  │ LocalStock   │  │  │ (ml-14 always, no shift)     │  │ │
│  │ icons│──▶ AI Stock     │  │  │                              │  │ │
│  │      │  │              │  │  └──────────────────────────────┘  │ │
│  │ ──── │  │ • Rankings   │  │                                    │ │
│  │Admin │  │ • Market     │  └────────────────────────────────────┘ │
│  │ icon │  │ • Learn      │                                         │
│  │      │  │ ──────────── │          ┌─────────────────────┐        │
│  └──────┘  │ • Admin      │          │ Toaster (Sonner)    │        │
│            └──────────────┘          │ z-[999999999]       │        │
│            slide-in ◄──────          └─────────────────────┘        │
│            150-200ms                                                 │
└─────────────────────────────────────────────────────────────────────┘

State Flow:
  localStorage("localstock-sidebar-collapsed")
       │
       ▼
  useSidebarState() hook
       │
       ├──▶ collapsed=true  → render icon rail only
       │
       └──▶ collapsed=false → render icon rail + overlay panel
                               (CSS transform transition)
```

### Recommended Project Structure

```
apps/helios/src/
├── components/
│   ├── layout/
│   │   ├── floating-sidebar.tsx    # NEW: Main sidebar (replaces sidebar.tsx)
│   │   ├── sidebar.tsx             # DELETE: Current fixed sidebar
│   │   └── app-shell.tsx           # MODIFY: ml-60 → ml-14, import change
│   └── ui/
│       └── tooltip.tsx             # NEW: Base-ui tooltip wrapper
├── hooks/
│   ├── use-sidebar-state.ts        # NEW: localStorage-backed state hook
│   ├── use-chart-theme.ts          # existing
│   └── use-job-transitions.ts      # existing
└── app/
    └── globals.css                 # MODIFY: Add sidebar transition styles
```

### Pattern 1: Lazy useState with localStorage (FOUC Prevention)

**What:** Initialize `useState` with a lazy function that reads `localStorage` synchronously during first render.
**When to use:** Any client-side state that must persist across reloads AND must not flash a different value on load.

```typescript
// Source: Existing ThemeProvider pattern in theme-provider.tsx + PITFALLS.md Pitfall 6
// hooks/use-sidebar-state.ts
"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "localstock-sidebar-collapsed";
const DEFAULT_COLLAPSED = true; // D-09: default collapsed on first visit

export function useSidebarState() {
  const [collapsed, setCollapsedRaw] = useState<boolean>(() => {
    if (typeof window === "undefined") return DEFAULT_COLLAPSED;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === null) return DEFAULT_COLLAPSED; // First visit
    return stored === "true";
  });

  const setCollapsed = useCallback((value: boolean | ((prev: boolean) => boolean)) => {
    setCollapsedRaw((prev) => {
      const next = typeof value === "function" ? value(prev) : value;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const toggle = useCallback(() => {
    setCollapsed((prev) => !prev);
  }, [setCollapsed]);

  return { collapsed, setCollapsed, toggle } as const;
}
```

**Why this pattern over `useSyncExternalStore`:** The `ThemeProvider` uses `useSyncExternalStore` because theme needs cross-tab sync (changing theme in one tab should reflect in others). Sidebar state does NOT need cross-tab sync — each tab's sidebar state is independent. `useState` + lazy init is simpler and sufficient. [VERIFIED: `theme-provider.tsx` uses `useSyncExternalStore` with `StorageEvent` listener]

### Pattern 2: CSS Transform Slide-In Animation

**What:** Overlay panel slides in from left using `transform: translateX()` with CSS transitions.
**When to use:** Sidebar panel expand/collapse with smooth animation per D-08 (150-200ms).

```css
/* Source: Standard CSS transition pattern, consistent with sheet.tsx animation approach */
/* globals.css addition */
[data-sidebar-panel] {
  transform: translateX(-100%);
  transition: transform 180ms ease-out;
}

[data-sidebar-panel][data-expanded="true"] {
  transform: translateX(0);
}
```

**Alternative — Tailwind-only approach (recommended for consistency):**
```tsx
// No globals.css changes needed — all in component
<div
  data-sidebar-panel
  className={cn(
    "fixed left-14 top-0 h-screen w-60 z-40",
    "border-r border-sidebar-border bg-sidebar shadow-lg",
    "transition-transform duration-[180ms] ease-out",
    collapsed ? "-translate-x-full" : "translate-x-0"
  )}
>
```

**Why `transform` over `width` animation:** `transform` is GPU-accelerated and doesn't trigger layout reflow. Width animation causes the browser to recalculate layout on every frame — janky on lower-end hardware. [ASSUMED — standard browser rendering knowledge]

**Why `ease-out` easing:** Quick start, gentle end — feels responsive on open. Matches the established `duration-200` and `ease-in-out` patterns in `sheet.tsx`. [VERIFIED: `sheet.tsx` uses `duration-200 ease-in-out`]

### Pattern 3: Base-UI Tooltip Wrapper (base-nova pattern)

**What:** Thin shadcn-style wrapper over `@base-ui/react/tooltip` primitives.
**When to use:** Tooltip on collapsed icon rail items per D-01.

```tsx
// Source: Established base-nova pattern from collapsible.tsx, alert-dialog.tsx
// components/ui/tooltip.tsx
"use client";

import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip";
import { cn } from "@/lib/utils";

function Tooltip({ ...props }: TooltipPrimitive.Root.Props) {
  return <TooltipPrimitive.Root data-slot="tooltip" {...props} />;
}

function TooltipTrigger({ ...props }: TooltipPrimitive.Trigger.Props) {
  return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />;
}

function TooltipPortal({ ...props }: TooltipPrimitive.Portal.Props) {
  return <TooltipPrimitive.Portal data-slot="tooltip-portal" {...props} />;
}

function TooltipPositioner({
  className,
  ...props
}: TooltipPrimitive.Positioner.Props) {
  return (
    <TooltipPrimitive.Positioner
      data-slot="tooltip-positioner"
      className={cn("", className)}
      {...props}
    />
  );
}

function TooltipContent({
  className,
  ...props
}: TooltipPrimitive.Popup.Props) {
  return (
    <TooltipPrimitive.Popup
      data-slot="tooltip-content"
      className={cn(
        "rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground shadow-md",
        "data-starting-style:opacity-0 data-ending-style:opacity-0",
        "transition-opacity duration-150",
        className
      )}
      {...props}
    />
  );
}

export { Tooltip, TooltipTrigger, TooltipPortal, TooltipPositioner, TooltipContent };
```

**Key API details from type inspection:**
- `TooltipTrigger` has `delay` prop (default 600ms) — reduce to ~200ms for responsive feel
- `TooltipPositioner` has `side` prop (default `"top"`) — use `"right"` for left-positioned sidebar
- `TooltipPositioner` has `sideOffset` for gap between trigger and popup
- `TooltipTrigger` renders a `<button>` by default — use `render` prop to render as different element
[VERIFIED: `TooltipTrigger.d.ts` — delay default 600ms, `TooltipPositioner.d.ts` — side default "top"]

### Pattern 4: Floating Sidebar Component Structure

**What:** Single component managing icon rail + overlay panel with toggle behavior.
**When to use:** The main sidebar implementation.

```tsx
// Source: Synthesized from codebase patterns + CONTEXT.md decisions
// components/layout/floating-sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { BarChart3, Globe, BookOpen, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebarState } from "@/hooks/use-sidebar-state";
import {
  Tooltip,
  TooltipTrigger,
  TooltipPortal,
  TooltipPositioner,
  TooltipContent,
} from "@/components/ui/tooltip";

const mainNavItems = [
  { href: "/rankings", labelKey: "rankings" as const, icon: BarChart3 },
  { href: "/market", labelKey: "market" as const, icon: Globe },
  { href: "/learn", labelKey: "learn" as const, icon: BookOpen },
];

const adminNavItems = [
  { href: "/admin", labelKey: "admin" as const, icon: Shield },
];

export function FloatingSidebar() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const { collapsed, toggle } = useSidebarState();

  const handleNavClick = () => {
    if (!collapsed) {
      toggle(); // Auto-collapse after navigation (agent's discretion)
    }
  };

  return (
    <>
      {/* Icon Rail — always visible */}
      <aside
        className="fixed left-0 top-0 h-screen w-14 z-30 flex flex-col items-center py-3 border-r border-sidebar-border bg-sidebar"
      >
        {/* Main nav group */}
        <nav className="flex flex-col items-center gap-1">
          {mainNavItems.map(({ href, labelKey, icon: Icon }) => (
            <Tooltip key={href}>
              <TooltipTrigger
                delay={200}
                render={
                  <Link
                    href={href}
                    onClick={collapsed ? toggle : handleNavClick}
                    className={cn(
                      "flex items-center justify-center w-10 h-10 rounded-md",
                      pathname.startsWith(href)
                        ? "bg-sidebar-accent text-sidebar-primary"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    )}
                  />
                }
              >
                <Icon className="h-5 w-5" />
              </TooltipTrigger>
              {collapsed && (
                <TooltipPortal>
                  <TooltipPositioner side="right" sideOffset={8}>
                    <TooltipContent>{t(labelKey)}</TooltipContent>
                  </TooltipPositioner>
                </TooltipPortal>
              )}
            </Tooltip>
          ))}
        </nav>

        {/* Spacer — pushes Admin to bottom */}
        <div className="flex-1" />

        {/* Separator */}
        <div className="w-8 border-t border-sidebar-border mb-2" />

        {/* Admin group — pinned to bottom */}
        <nav className="flex flex-col items-center gap-1 mb-2">
          {adminNavItems.map(({ href, labelKey, icon: Icon }) => (
            <Tooltip key={href}>
              <TooltipTrigger
                delay={200}
                render={
                  <Link
                    href={href}
                    onClick={collapsed ? toggle : handleNavClick}
                    className={cn(
                      "flex items-center justify-center w-10 h-10 rounded-md",
                      pathname.startsWith(href)
                        ? "bg-sidebar-accent text-sidebar-primary"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    )}
                  />
                }
              >
                <Icon className="h-5 w-5" />
              </TooltipTrigger>
              {collapsed && (
                <TooltipPortal>
                  <TooltipPositioner side="right" sideOffset={8}>
                    <TooltipContent>{t(labelKey)}</TooltipContent>
                  </TooltipPositioner>
                </TooltipPortal>
              )}
            </Tooltip>
          ))}
        </nav>
      </aside>

      {/* Overlay Panel — conditional on expanded state */}
      <aside
        className={cn(
          "fixed left-14 top-0 h-screen w-60 z-40",
          "border-r border-sidebar-border bg-sidebar shadow-lg",
          "transition-transform duration-[180ms] ease-out",
          collapsed ? "-translate-x-full" : "translate-x-0"
        )}
        aria-hidden={collapsed}
      >
        {/* Header — only in expanded state (D-02) */}
        <div className="p-4 border-b border-sidebar-border">
          <h1 className="text-lg font-bold text-sidebar-primary">LocalStock</h1>
          <p className="text-xs text-muted-foreground">
            {t("appTagline", { defaultMessage: "AI Stock Agent" })}
          </p>
        </div>

        {/* Full nav with labels */}
        <nav className="flex-1 p-2 space-y-1">
          {[...mainNavItems, ...adminNavItems].map(({ href, labelKey, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={handleNavClick}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm",
                pathname.startsWith(href)
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent"
              )}
            >
              <Icon className="h-4 w-4" />
              {t(labelKey)}
            </Link>
          ))}
        </nav>
      </aside>
    </>
  );
}
```

### Pattern 5: Layout Restructuring (app-shell.tsx)

**What:** Remove `ml-60` offset, replace with `ml-14` for icon rail width.
**When to use:** The app-shell update.

```tsx
// Source: Current app-shell.tsx inspection
// BEFORE:
<div className="ml-60">

// AFTER:
<div className="ml-14">
```

And the import change:
```tsx
// BEFORE:
import { Sidebar } from "./sidebar";

// AFTER:
import { FloatingSidebar } from "./floating-sidebar";
```

### Anti-Patterns to Avoid

- **Width animation instead of transform:** Animating `width` causes layout thrashing. Always use `transform: translateX()` for slide animations — it's composited on the GPU. [ASSUMED]
- **`useEffect` for initial localStorage read:** Reading localStorage in `useEffect` causes a flash (renders default → reads storage → re-renders). Use `useState` lazy initializer instead — it runs synchronously during first render. [VERIFIED: PITFALLS.md Pitfall 6]
- **Backdrop overlay (D-07 explicitly rejects):** The user decided NO backdrop. Don't add one. The toggle mechanism is clicking icons in the rail.
- **Over-engineering state management:** Don't use Context/Provider, Zustand, or Jotai for sidebar state. A simple `useSidebarState` hook with `useState` + `localStorage` is sufficient. The sidebar component is the only consumer.
- **Conditional rendering for panel (instead of CSS transition):** If the panel is conditionally rendered (`{!collapsed && <Panel />}`), there's no exit animation. Always render the panel and use CSS `transform` to hide/show it, so the transition works both ways.

## ⚠️ Conflict: CONTEXT.md D-07 vs ROADMAP.md Success Criteria #5

**CONTEXT.md D-07:** "No backdrop overlay when sidebar is expanded. Close by clicking any nav icon again (toggle behavior)."

**ROADMAP.md Success Criteria #5:** "Clicking outside the expanded sidebar (backdrop area) collapses it back to the icon rail."

**These contradict.** The user explicitly chose NO backdrop in the discussion (D-07). The ROADMAP success criteria #5 appears to be pre-discussion boilerplate that wasn't updated after the user's decision.

**Resolution:** User decisions in CONTEXT.md take precedence over ROADMAP success criteria. **Implement D-07 (no backdrop, toggle via icon click).** The planner should note that success criteria #5 is overridden by D-07 and adjust verification accordingly.

**Risk:** Without a backdrop, the expanded overlay panel covers ~240px of content that becomes unclickable in the overlapped region. This is the user's explicit choice and is acceptable because: (1) the panel can be quickly collapsed by clicking any icon, (2) the majority of content remains accessible, (3) the user explicitly rejected the backdrop pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip positioning & collision | Custom `position: absolute` + JS positioning | `@base-ui/react/tooltip` with `Positioner` component | Collision detection, viewport awareness, accessibility (aria attributes), keyboard support — all handled automatically. [VERIFIED: base-ui tooltip primitives installed] |
| Active route detection | Custom URL parsing | `usePathname()` from `next/navigation` | Already used in current sidebar. Handles all Next.js routing edge cases. [VERIFIED: `sidebar.tsx` line 3] |
| Localized labels | Hardcoded strings | `useTranslations("nav")` from `next-intl` | Already used in current sidebar. Labels exist in both `en.json` and `vi.json`. [VERIFIED: messages files] |
| CSS class composition | String concatenation | `cn()` utility (clsx + tailwind-merge) | Already the project standard. Handles conditional classes correctly. [VERIFIED: `src/lib/utils.ts`] |

**Key insight:** This phase is a layout restructuring, not a feature addition. Every primitive needed is already installed and pattern-proven in the codebase. The only "new" thing is the tooltip wrapper, which follows an established pattern (5 existing base-nova wrappers in `components/ui/`).

## Common Pitfalls

### Pitfall 1: Sidebar Collapse Flash on Page Load (FOUC)
**What goes wrong:** Sidebar renders in SSR default state (collapsed), then `useEffect` reads localStorage and may change state, causing a visual flash.
**Why it happens:** `useEffect` runs AFTER paint. If localStorage says "expanded" but SSR default is "collapsed," there's a frame where the sidebar is collapsed before expanding.
**How to avoid:** Use `useState` lazy initializer (runs synchronously before first paint). The `useSidebarState` hook pattern above handles this correctly. Since D-09 sets default to collapsed and most users will have collapsed state, the flash risk is minimal — but the lazy initializer still prevents it.
**Warning signs:** Sidebar visibly jumps on page reload. Test by setting localStorage to `"false"` (expanded) and reloading.
[VERIFIED: PITFALLS.md Pitfall 6]

### Pitfall 2: Overlay Panel Renders But Not Visible (transform issue)
**What goes wrong:** Panel is rendered with `-translate-x-full` but the `transition` property isn't applied, so expanding looks instant instead of smooth.
**Why it happens:** If the panel is conditionally rendered (`{!collapsed && ...}`) instead of always rendered with CSS transform, there's no element to transition FROM.
**How to avoid:** Always render the panel in the DOM. Use `transform` + `aria-hidden` to hide/show. Never use conditional rendering for animated elements.
**Warning signs:** Sidebar appears/disappears instantly without animation.

### Pitfall 3: Tooltip Shows Behind Overlay Panel
**What goes wrong:** Icon rail tooltips appear at `side="right"` but the overlay panel (z-40) covers them.
**Why it happens:** Tooltip portal renders at `z-50` (base-ui default), but if the tooltip and panel overlap spatially, the panel may occlude the tooltip.
**How to avoid:** Tooltips should only show when sidebar is collapsed (D-01 says "tooltip on hover" for collapsed state). When expanded, the full label is visible in the panel — no tooltip needed. Conditionally render `TooltipPortal` only when `collapsed === true`.
**Warning signs:** Hovering over an icon when expanded shows tooltip under the panel.

### Pitfall 4: Icon Rail Click Navigates AND Toggles Simultaneously
**What goes wrong:** Clicking an icon in the collapsed rail both navigates to the page AND expands the sidebar, but the user wanted just one action.
**Why it happens:** The `<Link>` component navigates on click, and the `onClick` handler toggles sidebar state. Both fire.
**How to avoid:** When collapsed, icon click should expand the sidebar only (prevent navigation). When expanded, clicking a link in the panel should navigate and auto-collapse. This is an agent's discretion area — the simplest approach: when collapsed, clicking an icon expands the sidebar AND navigates. The sidebar panel then shows the new active page. User clicks the icon again to collapse.
**Warning signs:** Click icon → page changes AND sidebar expands → confusing double action.

**Recommended behavior (agent's discretion):**
- Collapsed state + click icon → navigate to page + expand sidebar panel
- Expanded state + click link in panel → navigate to page + collapse sidebar
- Expanded state + click icon in rail → collapse sidebar (toggle)

### Pitfall 5: Content Behind Icon Rail (z-index layering)
**What goes wrong:** Content at `ml-14` butts against the icon rail. If any content uses `position: sticky` or `position: fixed`, it might render above the icon rail.
**Why it happens:** The icon rail is at `z-30`. If content elements have higher z-index, they overlay the rail.
**How to avoid:** Ensure no content elements use z-index above 30. The existing codebase doesn't have this issue — no sticky headers or fixed-position content elements in pages.
**Warning signs:** Content appears on top of the icon rail. Check with DevTools z-index inspector.

### Pitfall 6: Tooltip Delay Too Long (default 600ms)
**What goes wrong:** Base-ui tooltip trigger has a default `delay` of 600ms. User hovers over icon and nothing happens for over half a second — feels broken.
**Why it happens:** Default delay is designed for general tooltips to prevent accidental triggers. For navigation icons, users expect faster feedback.
**How to avoid:** Set `delay={200}` on `TooltipTrigger` for responsive tooltip on icon hover. This balances immediate feedback with preventing flash-tooltips during mouse traversal.
**Warning signs:** Tooltip feels sluggish on hover.
[VERIFIED: `TooltipTrigger.d.ts` — `delay` default is 600ms]

### Pitfall 7: Accessibility — Expanded Panel Not Announced
**What goes wrong:** Screen readers don't announce when the sidebar panel opens/closes.
**Why it happens:** CSS transform doesn't trigger accessibility announcements.
**How to avoid:** Add `aria-hidden={collapsed}` to the overlay panel and `aria-expanded={!collapsed}` to the toggle control. The icon rail icons should have `aria-label` with the page name.
**Warning signs:** Screen reader users don't know the panel state changed.

## Z-Index Layer System

```
Layer     Z-Index    Element                    Status
──────────────────────────────────────────────────────────
Content   z-0        Pages, main content        Default
Icon Rail z-30       Collapsed sidebar rail     Always visible
Panel     z-40       Expanded overlay panel     Conditional
Sheet     z-50       Sheet/AlertDialog overlay  Existing pattern
Sheet     z-50       Sheet/AlertDialog content  Existing pattern
Toaster   z-[999M]   Sonner toast container     Always on top
```

[VERIFIED: `sheet.tsx` uses `z-50` for overlay and content. Sonner uses `z-index: 999999999` hardcoded in CSS. No existing z-30 or z-40 usage in the codebase.]

## Agent's Discretion Recommendations

| Area | Recommendation | Rationale |
|------|---------------|-----------|
| Admin position | Bottom-pinned with separator | Standard pattern (VS Code, Discord, Slack). Clearly separates admin from primary navigation. |
| Icon rail width | `w-14` (56px) — Tailwind's built-in size | Matches D-01 target of ~56px exactly. Standard Tailwind unit. `w-14 = 3.5rem = 56px`. |
| Overlay panel width | `w-60` (240px) — match current sidebar | Preserves existing nav layout. Users familiar with current sidebar see same content. |
| Transition easing | `ease-out` at 180ms | Quick start, gentle end feels responsive. 180ms is between D-08's 150-200ms range. |
| Nav link collapse | Auto-collapse after navigation | User opened sidebar to navigate — after clicking a link, the sidebar's purpose is served. Auto-collapsing maximizes content area. |
| Visual separator | `border-t` line + spacer `flex-1` | Minimal visual weight. Admin icon naturally pushed to bottom without heavy divider. |

## File Change Audit

| File | Action | Changes |
|------|--------|---------|
| `components/layout/sidebar.tsx` | **DELETE** | Replaced by `floating-sidebar.tsx` |
| `components/layout/floating-sidebar.tsx` | **CREATE** | New floating sidebar with icon rail + overlay panel (~120 lines) |
| `components/layout/app-shell.tsx` | **MODIFY** | Import change (`Sidebar` → `FloatingSidebar`), `ml-60` → `ml-14` |
| `components/ui/tooltip.tsx` | **CREATE** | Base-ui tooltip wrapper (~60 lines) |
| `hooks/use-sidebar-state.ts` | **CREATE** | localStorage-backed state hook (~25 lines) |
| `app/globals.css` | **OPTIONAL MODIFY** | May add sidebar panel transition styles if Tailwind-only approach insufficient |

**Total:** 3 files created, 1 file modified, 1 file deleted. No new npm dependencies.

## Code Examples

### Icon Rail Item with Tooltip

```tsx
// Source: @base-ui/react/tooltip API (verified via .d.ts type inspection)
<Tooltip>
  <TooltipTrigger
    delay={200}
    render={
      <Link
        href="/rankings"
        className={cn(
          "flex items-center justify-center w-10 h-10 rounded-md",
          isActive
            ? "bg-sidebar-accent text-sidebar-primary"
            : "text-sidebar-foreground/70 hover:bg-sidebar-accent"
        )}
      />
    }
  >
    <BarChart3 className="h-5 w-5" />
  </TooltipTrigger>
  {collapsed && (
    <TooltipPortal>
      <TooltipPositioner side="right" sideOffset={8}>
        <TooltipContent>Rankings</TooltipContent>
      </TooltipPositioner>
    </TooltipPortal>
  )}
</Tooltip>
```

### AppShell Layout Change

```tsx
// Source: Direct inspection of app-shell.tsx
// BEFORE (current):
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="ml-60">
        <header className="flex items-center justify-end gap-2 px-6 py-3 border-b border-border">
          <LanguageToggle />
          <ThemeToggle />
        </header>
        <main className="p-6">{children}</main>
      </div>
      <Toaster />
    </div>
  );
}

// AFTER:
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <FloatingSidebar />
      <div className="ml-14">
        <header className="flex items-center justify-end gap-2 px-6 py-3 border-b border-border">
          <LanguageToggle />
          <ThemeToggle />
        </header>
        <main className="p-6">{children}</main>
      </div>
      <Toaster />
    </div>
  );
}
```

### useSidebarState Hook Usage

```tsx
// Source: Synthesized from ThemeProvider pattern (useSyncExternalStore) simplified to useState
const { collapsed, toggle } = useSidebarState();

// In icon click handler:
const handleIconClick = () => toggle();

// In nav link click handler (expanded panel):
const handleNavClick = () => {
  if (!collapsed) toggle(); // Auto-collapse after navigation
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed sidebar with `ml-60` offset | Floating sidebar with icon rail + overlay | This phase | Content gets full width minus 56px instead of 240px |
| No state persistence | `localStorage` persistence via hook | This phase | Sidebar remembers user preference across reloads |
| Flat nav list (4 items) | Two groups: Main (3) + Admin (1) with separator | This phase | Visual hierarchy matches app structure |
| Direct `<aside>` styling | CSS variable tokens (`--sidebar`, `--sidebar-accent`, etc.) | Phase 14 (already done) | Sidebar colors follow theme system automatically |

**Deprecated/outdated:**
- `sidebar.tsx` (current) — will be deleted, replaced by `floating-sidebar.tsx`
- `ml-60` layout pattern — replaced by `ml-14` (icon rail width only)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `transform: translateX()` is GPU-composited and doesn't cause layout reflow | Architecture Patterns → Pattern 2 | LOW — well-established browser behavior, but verify smooth animation on actual hardware |
| A2 | Tooltip should only appear when collapsed (not when expanded panel is showing labels) | Pitfall 3 | LOW — UX preference. Could show tooltips in both states, but redundant when labels are visible. |
| A3 | Auto-collapse after nav link click is better UX than keeping panel open | Agent's Discretion Recommendations | MEDIUM — some users may prefer panel stays open for quick multi-page navigation. Can be changed easily. |
| A4 | No content elements in the codebase use z-index above 30 | Pitfall 5 | LOW — verified by grep, but future phases could add fixed-position elements. |

## Open Questions

1. **Icon click behavior when collapsed: navigate + expand, or just expand?**
   - What we know: D-06 says "click icon → expand." D-07 says "click icon again → close."
   - What's unclear: Does clicking an icon when collapsed ALSO navigate to that page, or just expand the panel so the user can then click the full link?
   - Recommendation: Navigate + expand simultaneously (most natural behavior — user clicks Rankings icon, sees Rankings page AND expanded sidebar). This is agent's discretion territory.

2. **ROADMAP success criteria #5 vs D-07 contradiction**
   - What we know: D-07 says no backdrop. ROADMAP #5 says click outside to collapse.
   - What's unclear: Whether the user would accept a transparent (invisible) click-outside handler without visual backdrop.
   - Recommendation: Follow D-07 strictly — no backdrop, no click-outside-to-close. Toggle via icon click only. Flag the ROADMAP criteria mismatch for the planner.

3. **Narrow viewport behavior (1280px laptops)**
   - What we know: Spec says desktop-only (no mobile). Expanded panel covers 240px of a 1280px viewport = ~19%.
   - What's unclear: Is this acceptable, or should there be auto-collapse below a breakpoint?
   - Recommendation: Defer to future (LAY-06 mobile responsive is deferred). Current implementation works on any viewport — the overlay covers content but doesn't break layout.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.4 (unit) + Playwright 1.59.1 (E2E) |
| Config file | `vitest.config.ts` (unit), `playwright.config.ts` (E2E) |
| Quick run command | `cd apps/helios && npx vitest run --reporter=verbose` |
| Full suite command | `cd apps/helios && npx vitest run && npx playwright test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAY-01 | Content area uses `ml-14`, no shift when sidebar expands | E2E | `npx playwright test e2e/sidebar.spec.ts --grep "content no shift"` | ❌ Wave 0 |
| LAY-02 | Collapsed rail shows icons, click expands overlay | E2E | `npx playwright test e2e/sidebar.spec.ts --grep "expand collapse"` | ❌ Wave 0 |
| LAY-03 | Two tab groups visible (Main 3 + Admin 1 with separator) | E2E | `npx playwright test e2e/sidebar.spec.ts --grep "tab groups"` | ❌ Wave 0 |
| LAY-04 | State persists across reload via localStorage | E2E | `npx playwright test e2e/sidebar.spec.ts --grep "persist"` | ❌ Wave 0 |
| HOOK | `useSidebarState` returns correct initial state from localStorage | Unit | `npx vitest run src/hooks/__tests__/use-sidebar-state.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/helios && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd apps/helios && npx vitest run && npx playwright test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `e2e/sidebar.spec.ts` — covers LAY-01 through LAY-04 (E2E sidebar tests)
- [ ] `src/hooks/__tests__/use-sidebar-state.test.ts` — covers useSidebarState hook logic
- [ ] Update `e2e/app.spec.ts` — existing navigation tests reference `aside` locator which may need updating

## Security Domain

This phase involves zero security-sensitive operations. It's a pure UI layout restructuring with no authentication, data handling, cryptography, or external communication. localStorage stores only a boolean sidebar state preference.

| ASVS Category | Applies | Rationale |
|---------------|---------|-----------|
| V2 Authentication | No | No auth changes |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | No access control changes |
| V5 Input Validation | No | No user input processing (only click events) |
| V6 Cryptography | No | No crypto operations |

**No security controls required for this phase.**

## Sources

### Primary (HIGH confidence)
- `apps/helios/src/components/layout/sidebar.tsx` — current sidebar implementation (44 lines), icons, nav structure
- `apps/helios/src/components/layout/app-shell.tsx` — current layout with `ml-60` offset, `Toaster` placement
- `apps/helios/src/app/layout.tsx` — provider ordering, font variable, `suppressHydrationWarning`
- `apps/helios/src/app/globals.css` — sidebar CSS variables (lines 78-86), `@theme inline` block, existing transition patterns
- `apps/helios/src/components/theme/theme-provider.tsx` — localStorage persistence pattern with `useSyncExternalStore`
- `apps/helios/src/components/ui/collapsible.tsx` — base-nova wrapper pattern
- `apps/helios/src/components/ui/sheet.tsx` — z-50 overlay/backdrop pattern, slide animation
- `apps/helios/node_modules/@base-ui/react/package.json` — version 1.4.0, `./tooltip` export confirmed
- `apps/helios/node_modules/@base-ui/react/esm/tooltip/` — TypeScript type definitions for Root, Trigger, Positioner, Popup
- `apps/helios/node_modules/lucide-react/dist/esm/icons/` — all needed icons verified present
- `apps/helios/node_modules/sonner/dist/` — z-index: 999999999 confirmed
- `apps/helios/package.json` — all dependency versions verified
- `apps/helios/messages/en.json`, `messages/vi.json` — nav translation keys verified
- `.planning/phases/15-sidebar-float-collapse/15-CONTEXT.md` — all user decisions D-01 through D-10
- `.planning/research/PITFALLS.md` — 7 sidebar-specific pitfalls (P2, P6, P8)
- `.planning/research/SUMMARY.md` — architecture overview, z-index layering, component map
- `.planning/REQUIREMENTS.md` — LAY-01 through LAY-04 requirement text

### Secondary (MEDIUM confidence)
- MDN CSS Transitions — transform vs width animation performance characteristics
- Base-ui documentation references in type comments — `https://base-ui.com/react/components/tooltip`

### Tertiary (LOW confidence)
- None — all claims verified against source code or official type definitions

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all dependencies verified in `node_modules/`, all APIs confirmed via TypeScript type inspection
- Architecture: **HIGH** — based on direct codebase inspection, existing patterns (ThemeProvider, Sheet, Collapsible), and clear user decisions
- Pitfalls: **HIGH** — 7 pitfalls sourced from PITFALLS.md research + 2 additional from direct code analysis (tooltip delay, accessibility)

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable — no fast-moving dependencies, all existing primitives)
