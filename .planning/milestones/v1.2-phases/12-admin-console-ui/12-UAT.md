---
status: testing
phase: 12-admin-console-ui
source: [12-01-SUMMARY.md, 12-02-SUMMARY.md]
started: 2026-04-22T05:10:00Z
updated: 2026-04-22T05:10:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Admin sidebar navigation
expected: |
  Sidebar shows "Admin" nav item with a Shield icon. Clicking it navigates to /admin.
awaiting: user response

## Tests

### 1. Admin sidebar navigation
expected: Sidebar shows "Admin" nav item with a Shield icon. Clicking it navigates to /admin.
result: [pending]

### 2. Admin page loads with 3 tabs
expected: /admin page renders with page title "Admin Console" and 3 tabs: Stocks, Pipeline, Jobs. Default tab is Stocks.
result: [pending]

### 3. Stock table with add form
expected: Stocks tab shows an inline input + "Add Stock" button at top. Typing a symbol (e.g. "VNM") and clicking Add (or pressing Enter) adds it to the table below. Invalid input (lowercase, special chars) is rejected. Table shows columns for symbol, name, exchange, industry.
result: [pending]

### 4. Stock remove button
expected: Each stock row has a Remove (x) button. Clicking it removes the stock from the table. A toast notification confirms the action.
result: [pending]

### 5. Pipeline control with checkbox selection
expected: Pipeline tab shows tracked stocks with checkboxes. Selecting stocks enables Crawl and Analyze buttons. Score and Pipeline buttons are always enabled. Clicking an action button triggers the operation and auto-switches to the Jobs tab.
result: [pending]

### 6. Job monitor with status badges
expected: Jobs tab shows a table of recent jobs with columns: type, status, duration, created time. Status badges show colored indicators (green=completed, red=failed, amber=running, gray=pending).
result: [pending]

### 7. Job detail expansion
expected: Clicking a job row expands to show job details — result JSON for completed jobs, error message for failed jobs.
result: [pending]

### 8. Job polling (real-time updates)
expected: When jobs are running/pending, the Jobs tab auto-refreshes every 3 seconds. When all jobs complete or fail, polling stops automatically.
result: [pending]

### 9. Toast notifications
expected: Toast notifications appear for: adding stock (success), removing stock (success), triggering pipeline operations (success), errors (operation failed), lock conflicts (409 - operation already running).
result: [pending]

### 10. i18n support
expected: Admin page labels, buttons, empty states, and toast messages display in the current language (English or Vietnamese) based on the app's locale setting.
result: [pending]

## Summary

total: 10
passed: 0
issues: 0
pending: 10
skipped: 0

## Gaps

[none yet]
