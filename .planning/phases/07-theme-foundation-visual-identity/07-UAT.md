---
status: testing
phase: 07-theme-foundation-visual-identity
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md]
started: 2026-04-17T10:30:00Z
updated: 2026-04-17T10:30:00Z
---

## Current Test

number: 1
name: Warm Cream Default Theme
expected: |
  Open http://localhost:3000 in an incognito/private window (no prior localStorage).
  The page background should be a warm cream color — not white, not dark navy.
  Sidebar should have a slightly warmer/different shade than the main content area.
  Primary accents (buttons, active states) should show a terracotta/orange tone.
awaiting: user response

## Tests

### 1. Warm Cream Default Theme
expected: Open http://localhost:3000 in an incognito/private window (no prior localStorage). The page background should be a warm cream color — not white, not dark navy. Sidebar should have a slightly warmer/different shade than the main content area. Primary accents (buttons, active states) should show a terracotta/orange tone.
result: [pending]

### 2. No FOUC on Page Load
expected: Hard-refresh the page (Ctrl+Shift+R / Cmd+Shift+R) 5 times rapidly. You should NOT see the page flash dark before the cream theme loads. The cream background should appear immediately from first paint — no dark-then-light transition.
result: [pending]

### 3. Theme Toggle Button Present
expected: A sun or moon icon button is visible in the top-right area of the header (above the main content, right of the sidebar). Hovering over it should show a ghost button highlight.
result: [pending]

### 4. Dark Theme Switch
expected: Click the sun/moon icon. The entire page should switch to a dark navy/slate background instantly — no page reload. Charts, sidebar, content area, and text all update. The icon should now show the sun (indicating you can switch back to light).
result: [pending]

### 5. Theme Preference Persistence
expected: Toggle to dark mode. Close the browser tab. Reopen http://localhost:3000 in a regular (non-incognito) window. The page should load in dark mode immediately — no flash of cream before going dark.
result: [pending]

### 6. Financial Grade Badge Contrast
expected: Navigate to the Rankings page (/rankings). Find grade badges (A, B, C, D, or F labels). In warm-light mode: badge text should be a darker shade (green-700, blue-700, etc.) — clearly readable on cream. Toggle to dark: badge text should switch to brighter shades (green-400, blue-400, etc.) — clearly readable on dark background.
result: [pending]

### 7. Stock Up/Down Colors in Both Themes
expected: On the Rankings page, find stocks with positive (up) and negative (down) price changes. In warm-light: up should be a darker green, down a darker red (strong contrast on cream). Toggle to dark: up should be a brighter green (#22c55e), down a brighter red (#ef4444).
result: [pending]

### 8. Chart Re-theming Without Page Reload
expected: Navigate to a stock detail page that shows a candlestick chart (e.g., /stock/VNM or click a stock from Rankings). In warm-light mode: chart background should be warm cream, candle wicks/bars in darker green/red. Toggle theme to dark — charts should instantly update to dark background with bright green/red candles. No page reload required. Toggle back to light — charts return to warm cream.
result: [pending]

### 9. Zoom and Scroll Preserved Across Theme Switch
expected: On a stock chart page, zoom in by scrolling (mouse wheel or pinch) and scroll to a specific date range. Then toggle the theme. The chart should repaint colors but keep the SAME zoom level and date range — it should NOT reset to the full data range after toggling.
result: [pending]

## Summary

total: 9
passed: 0
issues: 0
pending: 9
skipped: 0
blocked: 0

## Gaps

[none yet]
