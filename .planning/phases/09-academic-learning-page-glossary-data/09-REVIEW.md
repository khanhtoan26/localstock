---
phase: 09-academic-learning-page-glossary-data
reviewed: 2026-04-20T12:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - apps/helios/src/lib/glossary.ts
  - apps/helios/src/components/layout/sidebar.tsx
  - apps/helios/src/components/ui/input.tsx
  - apps/helios/src/components/learn/glossary-entry-card.tsx
  - apps/helios/src/components/learn/glossary-search.tsx
  - apps/helios/src/app/learn/page.tsx
  - apps/helios/src/app/learn/[category]/page.tsx
  - apps/helios/src/app/globals.css
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-04-20T12:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 9 adds an academic/learning section with glossary data — a typed glossary module (`glossary.ts`), hub page, category pages with expandable entry cards, diacritic-insensitive search, and a sidebar navigation item. The implementation is well-structured and closely follows the UI-SPEC and CONTEXT decisions.

Overall code quality is good:
- Clean type definitions matching the data contract
- Proper validation of dynamic route params with `notFound()` fallback
- Well-implemented diacritic-insensitive search (including `đ`/`Đ` handling)
- Good accessibility patterns (sr-only labels, aria-live, aria-label)
- Correct use of Server vs Client component boundaries
- No security vulnerabilities detected (no hardcoded secrets, no dangerous functions, no user-controlled markdown)

Two warnings were identified: a minor bug in the Escape key handler and a redundant `focus()` call. Three info items for minor improvements.

## Warnings

### WR-01: Escape key handler calls focus() on already-focused element

**File:** `apps/helios/src/components/learn/glossary-search.tsx:68`
**Issue:** When the user presses Escape, the handler calls `(e.target as HTMLInputElement).focus()`. Since the Escape key event fires on the input that already has focus, this is a no-op. However, the type assertion `as HTMLInputElement` is the real concern — while `e.target` will be the input in practice (the `onKeyDown` is on the `<Input>` element), using `e.currentTarget` would be type-safe without a cast, since `currentTarget` in a React `KeyboardEvent<HTMLInputElement>` handler is always the element the handler is attached to.
**Fix:**
```tsx
onKeyDown={(e) => {
  if (e.key === "Escape") {
    setQuery("");
    // e.currentTarget is already typed as HTMLInputElement
    // and is the element the handler is attached to
  }
}}
```
If the intent is to keep focus after clearing (for screen readers), the call is harmless but the `as HTMLInputElement` cast should be removed by using `e.currentTarget.focus()` instead.

### WR-02: Glossary entry record keys could mismatch with `id` field

**File:** `apps/helios/src/lib/glossary.ts:19-402` (and lines 406-775, 779-930)
**Issue:** The glossary uses `Record<string, GlossaryEntry>` where the object key (e.g., `rsi`) and the `id` field (e.g., `id: "rsi"`) must match for correct behavior. Currently all 25 entries are consistent, but this is not enforced by the type system. A future contributor could add an entry with a mismatched key and `id`, causing bugs in URL anchors and deep-linking (the card would have `id={entry.id}` but lookup via object key would differ).
**Fix:** Add a build-time or runtime assertion, or use a helper function to derive entries:
```typescript
// Option A: Runtime assertion (dev-only check)
if (process.env.NODE_ENV === "development") {
  for (const [key, entry] of Object.entries(glossary)) {
    if (key !== entry.id) {
      console.error(`Glossary key "${key}" does not match entry id "${entry.id}"`);
    }
  }
}

// Option B: Use a factory function that sets id from the key
function defineEntries<K extends string>(entries: Record<K, Omit<GlossaryEntry, "id"> & { id?: never }>): Record<K, GlossaryEntry> {
  // derive id from key
}
```

## Info

### IN-01: Redundant `as const` on mutable array

**File:** `apps/helios/src/app/learn/page.tsx:29`
**Issue:** The `categories` array has `as const` on line 29 at the end of the array declaration, but `slug` values already use `as const` inline (e.g., `"technical" as const` on line 9). The outer `as const` makes the entire array deeply readonly, which is fine and intentional, but the inline `as const` on each slug is then redundant.
**Fix:** Either keep only the trailing `as const` (and remove `as const` from individual slugs), or remove the trailing `as const` and keep the inline ones. Using only the trailing `as const` is cleaner:
```typescript
const categories = [
  {
    slug: "technical",
    // ...
  },
  // ...
] as const;
```

### IN-02: Search result count always shown, even without active query

**File:** `apps/helios/src/components/learn/glossary-search.tsx:86-88`
**Issue:** The result count `"{N} kết quả"` is displayed even when no search query is active, showing the total entry count (e.g., "10 kết quả"). Per the UI-SPEC, the result count should update reactively, but showing it without an active search may be slightly confusing. This is a minor UX consideration, not a bug.
**Fix:** Optionally only show the count when a search query is active:
```tsx
{query && (
  <p className="text-xs text-muted-foreground mt-2" aria-live="polite">
    {filtered.length} kết quả
  </p>
)}
```

### IN-03: Large single-file data module (957 lines)

**File:** `apps/helios/src/lib/glossary.ts`
**Issue:** The glossary data file is 957 lines, with most content being Vietnamese markdown string literals. While this is correct per the design decision (D-04: single TypeScript module, no JSON/MDX), the file will grow as more entries are added. For ~25 entries this is manageable, but it may become unwieldy at 50+ entries.
**Fix:** No action needed now. If the file grows significantly in future phases, consider splitting data into per-category files (`glossary/technical.ts`, `glossary/fundamental.ts`, `glossary/macro.ts`) re-exported from a barrel `glossary/index.ts`, while preserving the single-module API contract.

---

_Reviewed: 2026-04-20T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
