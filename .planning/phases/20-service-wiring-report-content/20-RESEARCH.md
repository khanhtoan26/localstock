# Phase 20: Service Wiring & Report Content - Research

**Researched:** 2026-04-28
**Domain:** Python service orchestration — pre-computed financial metrics + LLM prompt injection + persistence
**Confidence:** HIGH

## Summary

Phase 20 wires pre-computed financial metrics (entry zone, stop-loss, target price, signal conflict detection, catalyst synthesis) into the existing `ReportService` → `ReportDataBuilder` → LLM prompt → `content_json` pipeline. All six StockReport fields (`entry_price`, `stop_loss`, `target_price`, `risk_rating`, `catalyst`, `signal_conflicts`) already exist in the Pydantic model from Phase 19, and `content_json` is already populated via `StockReport.model_dump()`. The work is entirely in Python — no new dependencies, no DB migrations, no new API endpoints.

The critical architectural insight is that entry zone, stop-loss, and target price are **pre-computed in Python** and **injected into the prompt as hard numbers** — the LLM does NOT decide prices. Risk rating and catalyst are LLM-generated. Signal conflict uses a Python boolean gate (`|tech_score − fund_score| > 25`) to conditionally inject conflict context into the prompt.

**Primary recommendation:** Implement computations as pure functions in `generator.py` (or a small `price_levels.py` helper), wire them in `report_service.py` between indicator gathering and prompt building, extend `REPORT_USER_TEMPLATE` with new sections, and verify via unit tests on the computation functions + integration tests on the full pipeline.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Entry zone is pre-computed in Python before LLM call — injected as hard numbers
- **D-02:** Entry zone range: lower = nearest_support, upper = Bollinger upper band (bb_upper)
- **D-03:** Fallback: < 40 price history rows → use close ± 2%
- **D-04:** How to store range in entry_price field — Agent's Discretion
- **D-05:** Stop-loss = max(support_2, close × 0.93)
- **D-06:** Target price = nearest_resistance if available, else close × 1.10
- **D-07:** SL/TP pre-computed in Python, injected into prompt
- **D-08:** Risk rating is LLM-generated; _normalize_risk_rating() handles post-gen normalization
- **D-09:** Vietnamese reasoning text for risk rating is part of existing prompt output
- **D-10:** Signal conflict gate: abs(tech_score - fund_score) > 25
- **D-11:** Inject into prompt: both scores + gap direction with Vietnamese label
- **D-12:** LLM generates signal_conflicts text when conflict detected; None otherwise
- **D-13:** Catalyst implementation — Agent's Discretion
- **D-14:** News from get_aggregated_sentiment(); score delta from comparing current vs previous CompositeScore
- **D-15:** content_json persistence — Agent's Discretion (StockReport.model_dump() auto-includes new fields)

### Agent's Discretion
- Exact location of entry zone computation function (new module vs extend generator.py)
- How to handle Bollinger band unavailability beyond <40 rows fallback
- News article retrieval for catalyst (direct DB query or via existing crawlers)
- Score delta computation (query previous day's score or store delta in pipeline)
- Prompt template additions for conflict section layout
- How to store entry zone range in single entry_price float field (midpoint, lower bound, or add second field)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REPORT-01 | Entry zone as price range (nearest_support + Bollinger band range) with close ± 2% fallback | indicator_data already has nearest_support, bb_upper, bb_lower; price_repo.get_prices() can count rows for fallback gate |
| REPORT-02 | Stop-loss max(support_2, close × 0.93) and target price nearest_resistance or close × 1.10 | indicator_data has support_2, nearest_resistance; close available from latest_price |
| REPORT-03 | Risk rating high/medium/low with Vietnamese reasoning | StockReport.risk_rating already exists; _normalize_risk_rating() handles normalization; LLM generates text |
| REPORT-04 | Signal conflict explanation when |tech_score − fund_score| > 25 | score.technical_score and score.fundamental_score available in main loop |
| REPORT-05 | Catalyst from 7-day news + composite score delta | SentimentService + NewsRepository for news; ScoreRepository.get_previous_date_scores() for delta |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Entry zone computation | API / Backend (Python) | — | Pure math on indicator_data; must NOT be LLM-decided |
| Stop-loss / target price | API / Backend (Python) | — | Pre-computed from S/R levels + close price |
| Risk rating generation | API / Backend (LLM) | — | LLM generates text; Python normalizes post-gen |
| Signal conflict detection | API / Backend (Python) | — | Boolean gate on score gap; prompt injection |
| Signal conflict explanation | API / Backend (LLM) | — | LLM generates text when conflict detected |
| Catalyst synthesis | API / Backend (LLM) | Database (news query) | LLM synthesizes from news data fetched via repos |
| content_json persistence | Database / Storage | — | StockReport.model_dump() → AnalysisReport.content_json (already wired) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Primary language | All existing code [VERIFIED: codebase] |
| Pydantic | 2.13+ | StockReport model + validation | Already used for LLM structured output [VERIFIED: ai/client.py] |
| SQLAlchemy | 2.0+ | Async DB queries (score delta, news) | Already used throughout [VERIFIED: repositories/] |
| pandas-ta | installed | Bollinger bands already computed | Used in TechnicalAnalyzer [VERIFIED: analysis/technical.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.4+ | Unit + integration tests | All computation functions [VERIFIED: pyproject.toml] |
| pytest-asyncio | 0.26+ | Async test support | ReportService pipeline tests [VERIFIED: pyproject.toml] |
| loguru | installed | Logging fallback/warning paths | Already used everywhere [VERIFIED: codebase] |

No new dependencies needed. [VERIFIED: CONTEXT.md D-15, STATE.md decisions]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    ReportService.run_full()                      │
│                                                                  │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐   │
│  │ ScoreRepo    │   │ IndicatorRepo │   │ PriceRepo        │   │
│  │ get_top_     │   │ get_latest()  │   │ get_latest()     │   │
│  │ ranked()     │   │               │   │ get_prices()     │   │
│  └──────┬───────┘   └───────┬───────┘   └──────┬───────────┘   │
│         │                   │                    │               │
│         ▼                   ▼                    ▼               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           NEW: Pre-compute Price Levels                   │   │
│  │  • entry_zone(nearest_support, bb_upper, close, n_rows)  │   │
│  │  • stop_loss = max(support_2, close × 0.93)              │   │
│  │  • target_price = nearest_resistance or close × 1.10     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────┼───────────────────────────────┐   │
│  │           NEW: Signal Conflict Detection                  │   │
│  │  • gate = abs(tech_score − fund_score) > 25               │   │
│  │  • if gate: build conflict context string                 │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────┼───────────────────────────────┐   │
│  │           NEW: Catalyst Data Gathering                    │   │
│  │  • 7-day news summaries via SentimentService              │   │
│  │  • Score delta via ScoreRepo.get_previous_date_scores()   │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  ReportDataBuilder.build()  ← extended with new keys  │      │
│  └──────────────────────┬────────────────────────────────┘      │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  REPORT_USER_TEMPLATE  ← extended with new sections   │      │
│  └──────────────────────┬────────────────────────────────┘      │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  OllamaClient.generate_report()  → StockReport        │      │
│  └──────────────────────┬────────────────────────────────┘      │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  Post-gen: _validate_price_levels + _normalize_risk   │      │
│  └──────────────────────┬────────────────────────────────┘      │
│                         ▼                                        │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  report.model_dump() → AnalysisReport.content_json    │      │
│  └───────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | File | What Changes |
|-----------|------|-------------|
| Price level computation | `reports/generator.py` (new functions) | `compute_entry_zone()`, `compute_stop_loss()`, `compute_target_price()` |
| Signal conflict detection | `reports/generator.py` (new function) | `detect_signal_conflict()` |
| Catalyst data assembly | `services/report_service.py` | News summary + score delta gathering in main loop |
| ReportDataBuilder | `reports/generator.py` | Add new keys: entry_zone_*, conflict_*, catalyst_* |
| Prompt template | `ai/prompts.py` | Add entry zone, SL/TP, conflict, catalyst sections |
| Service orchestration | `services/report_service.py` | Wire new computations between data gathering and prompt building |

### Pattern 1: Pre-computed Values Injected into Prompt
**What:** Calculate exact numeric values in Python, inject into prompt template as formatted text, so LLM describes/contextualizes rather than invents numbers.
**When to use:** Any time the LLM would hallucinate numeric values (prices, scores, thresholds).
**Example:**
```python
# Source: [VERIFIED: existing pattern in report_service.py lines 204-212]
# Score data is pre-computed and passed to ReportDataBuilder
score_data = {
    "total": score.total_score,
    "technical": score.technical_score,
    "fundamental": score.fundamental_score,
}
# New price level computation follows same pattern:
entry_lower = indicator_data.get("nearest_support") or (close * 0.98)
entry_upper = indicator_data.get("bb_upper") or (close * 1.02)
```

### Pattern 2: Conditional Prompt Section
**What:** Include/exclude a prompt section based on a Python boolean gate.
**When to use:** Signal conflicts (only show when |gap| > 25), catalyst (only when data exists).
**Example:**
```python
# Conflict gate
tech = score.technical_score or 0
fund = score.fundamental_score or 0
gap = abs(tech - fund)
has_conflict = gap > 25

if has_conflict:
    conflict_text = (
        f"Xung đột tín hiệu: Tech={tech:.0f}, Fund={fund:.0f}, "
        f"gap={'+' if tech > fund else ''}{tech - fund:.0f} "
        f"({'kỹ thuật > cơ bản' if tech > fund else 'cơ bản > kỹ thuật'})"
    )
else:
    conflict_text = ""  # Empty → template section omitted or says "không có"
```

### Pattern 3: Score Delta via Repository
**What:** Use existing `ScoreRepository.get_previous_date_scores()` to compute composite score change.
**When to use:** Catalyst section needs "score moved from X to Y".
**Example:**
```python
# Source: [VERIFIED: score_repo.py lines 83-105]
prev_date, prev_scores = await self.score_repo.get_previous_date_scores(today)
prev_score_map = {s.symbol: s.composite_score for s in prev_scores} if prev_scores else {}
# But CompositeScore uses total_score not composite_score
prev_total = prev_score_map.get(symbol)
delta = score.total_score - prev_total if prev_total is not None else None
```

### Anti-Patterns to Avoid
- **LLM decides prices:** Never let the LLM compute entry/stop-loss/target — always inject pre-computed values. The LLM should describe/explain, not calculate. [VERIFIED: D-01, D-07]
- **Tight coupling of computation and orchestration:** Keep pure computation functions (entry zone, SL, TP) as standalone testable functions, not buried in ReportService methods.
- **Silent None propagation:** When indicator_data has None values (no Bollinger, no S/R), must explicitly trigger fallback, not silently pass None into math operations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Risk rating normalization | Custom string matching | Existing `_normalize_risk_rating()` in generator.py | Already handles Vietnamese + English + casing variants [VERIFIED: generator.py lines 91-132] |
| Price validation | Custom range checker | Existing `_validate_price_levels()` in generator.py | Already validates ordering + ±30% range [VERIFIED: generator.py lines 135-180] |
| Sentiment aggregation | Custom avg | Existing `SentimentService.get_aggregated_sentiment()` | Already time-weighted, handles edge cases [VERIFIED: sentiment_service.py] |
| Score previous-run lookup | Custom SQL | Existing `ScoreRepository.get_previous_date_scores()` | Already finds max date before target, returns scores [VERIFIED: score_repo.py lines 83-105] |
| Safe None formatting | Manual if/else chains | Existing `_safe()`, `_safe_float()`, `_safe_pct()` | Already handle None → "N/A" consistently [VERIFIED: generator.py lines 12-37] |

**Key insight:** Most supporting infrastructure already exists. This phase is primarily about (1) adding ~50 lines of pure computation functions, (2) ~20 lines of orchestration wiring, and (3) ~15 lines of prompt template additions.

## Common Pitfalls

### Pitfall 1: None Values in Arithmetic
**What goes wrong:** `indicator_data.get("nearest_support")` returns None when no S/R data exists → `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`
**Why it happens:** Not all stocks have sufficient price history for S/R or Bollinger computation.
**How to avoid:** Every computation function must handle None inputs gracefully with explicit fallback paths. Use the established `_safe_float()` pattern for prompt injection.
**Warning signs:** Tests that only use mock data with all fields populated.

### Pitfall 2: Entry Zone Fallback Threshold Mismatch
**What goes wrong:** Using `len(prices)` for the <40 row check but `prices` in report_service.py is sliced to `[-60:]` before being passed around.
**Why it happens:** The 60-row slice happens at line 187 of report_service.py for signal computation, but the raw `get_prices()` result has the full history.
**How to avoid:** Count rows from the *unsliced* `get_prices()` result or query `price_repo` separately for count.
**Warning signs:** Stocks with exactly 40-60 rows getting wrong behavior.

### Pitfall 3: CompositeScore Field Name Confusion
**What goes wrong:** Using `score.composite_score` when the actual field is `score.total_score`. The model has `total_score` not `composite_score`.
**Why it happens:** Mental model vs actual schema mismatch.
**How to avoid:** Always reference the verified model: `CompositeScore.total_score` [VERIFIED: models.py line 343].
**Warning signs:** AttributeError in production.

### Pitfall 4: News Articles Not Directly Linked to Symbols
**What goes wrong:** Trying to query news articles by symbol directly — `NewsArticle` has no `symbol` column.
**Why it happens:** News articles are linked to symbols via `SentimentScore` (article_id + symbol) after LLM classification.
**How to avoid:** For catalyst, use `SentimentScore` table to find article_ids linked to a symbol, then join to get article titles/summaries. OR just pass the existing `sentiment_data` (already retrieved) as catalyst context to the LLM.
**Warning signs:** Empty catalyst sections for stocks with news.

### Pitfall 5: Prompt Template Key Mismatch
**What goes wrong:** Adding new keys to `ReportDataBuilder.build()` but forgetting to add matching `{placeholders}` in `REPORT_USER_TEMPLATE`, or vice versa — `KeyError` on `.format()`.
**Why it happens:** Template and builder are in separate files (prompts.py vs generator.py).
**How to avoid:** Add keys and placeholders in the same task. Test the full `build_report_prompt(data)` path.
**Warning signs:** KeyError during report generation.

### Pitfall 6: Duplicate Report Service Methods
**What goes wrong:** Modifying `run_full()` but forgetting to apply the same changes to `generate_for_symbol()` — the two methods have largely duplicated logic.
**Why it happens:** `report_service.py` has two report generation paths (bulk and single-symbol) with copy-pasted code.
**How to avoid:** Apply all new computation/wiring changes to BOTH methods. Consider extracting shared logic into a private method.
**Warning signs:** Reports generated via API (single symbol) missing new fields.

## Code Examples

### Entry Zone Computation
```python
# Source: [VERIFIED: CONTEXT.md D-02, D-03; indicator_data structure from report_service.py]
def compute_entry_zone(
    nearest_support: float | None,
    bb_upper: float | None,
    close: float | None,
    price_history_count: int,
) -> tuple[float | None, float | None]:
    """Compute entry zone as (lower, upper) price range.

    Args:
        nearest_support: Nearest support level from S/R analysis.
        bb_upper: Bollinger upper band from indicator_data.
        close: Current closing price.
        price_history_count: Total rows of price history for this stock.

    Returns:
        Tuple of (entry_lower, entry_upper). Both None if close is None.
    """
    if close is None:
        return None, None

    # Fallback: insufficient history for Bollinger bands
    if price_history_count < 40 or (nearest_support is None and bb_upper is None):
        return round(close * 0.98, 1), round(close * 1.02, 1)

    lower = nearest_support if nearest_support is not None else round(close * 0.98, 1)
    upper = bb_upper if bb_upper is not None else round(close * 1.02, 1)

    # Sanity: ensure lower < upper
    if lower >= upper:
        lower, upper = round(close * 0.98, 1), round(close * 1.02, 1)

    return round(lower, 1), round(upper, 1)
```

### Stop-Loss & Target Price
```python
# Source: [VERIFIED: CONTEXT.md D-05, D-06]
def compute_stop_loss(support_2: float | None, close: float | None) -> float | None:
    """Stop-loss = max(support_2, close × 0.93). HOSE ±7% daily limit aware."""
    if close is None:
        return None
    floor = close * 0.93
    if support_2 is not None:
        return round(max(support_2, floor), 1)
    return round(floor, 1)


def compute_target_price(nearest_resistance: float | None, close: float | None) -> float | None:
    """Target = nearest_resistance if available, else close × 1.10."""
    if close is None:
        return None
    if nearest_resistance is not None:
        return round(nearest_resistance, 1)
    return round(close * 1.10, 1)
```

### Signal Conflict Detection
```python
# Source: [VERIFIED: CONTEXT.md D-10, D-11]
def detect_signal_conflict(
    tech_score: float | None,
    fund_score: float | None,
) -> str | None:
    """Detect and format signal conflict for prompt injection.

    Returns Vietnamese conflict description string if |gap| > 25, else None.
    """
    if tech_score is None or fund_score is None:
        return None
    gap = tech_score - fund_score
    if abs(gap) <= 25:
        return None
    direction = "kỹ thuật > cơ bản" if gap > 0 else "cơ bản > kỹ thuật"
    return (
        f"Xung đột tín hiệu: Tech={tech_score:.0f}, Fund={fund_score:.0f}, "
        f"gap={'+' if gap > 0 else ''}{gap:.0f} ({direction})"
    )
```

### Entry Price Storage Decision (Agent's Discretion — D-04)
```python
# Recommendation: Store midpoint of entry zone in entry_price field,
# and inject the full range into the prompt for LLM to describe.
# This is pragmatic — entry_price remains a single float (no schema change),
# while the prompt has the full range for rich text generation.
entry_lower, entry_upper = compute_entry_zone(...)
entry_midpoint = (entry_lower + entry_upper) / 2 if entry_lower and entry_upper else None
# Inject into prompt: both bounds as context
# Store in StockReport: entry_price = midpoint (single float)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM decides all prices | Python pre-computes, LLM contextualizes | Phase 19/20 design | Eliminates price hallucination |
| No entry zone | Entry zone from S/R + Bollinger | Phase 20 | Actionable trade recommendations |
| No signal conflict | Conditional conflict detection | Phase 20 | Transparent when tech vs fund disagree |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `indicator_data["bb_upper"]` is populated by TechnicalAnalyzer for stocks with sufficient history | Code Examples | Entry zone computation would always use fallback — verify bb_upper is stored in indicator table |
| A2 | `ScoreRepository.get_previous_date_scores()` returns scores with `.total_score` attribute usable for delta | Code Examples | Score delta computation would fail — field name already verified in models.py |
| A3 | Midpoint of entry zone is the most pragmatic storage for `entry_price` single float field | Code Examples (D-04) | Could store lower bound instead if frontend expects "minimum buy price" — low risk, easily changed |

**Note on A1:** Verified that `TechnicalAnalyzer.to_indicator_row()` maps `BBU_20_2.0_2.0` → `bb_upper` (line 281 of technical.py), and the indicator_data dict in report_service.py pulls all columns from the indicator model. So `bb_upper` will be available when Bollinger bands are computed (requires ≥20 rows of data). The <40 row fallback in D-03 provides a safety margin. [VERIFIED: technical.py line 281, report_service.py line 132-137]

## Open Questions

1. **Catalyst news article retrieval path**
   - What we know: `SentimentService.get_aggregated_sentiment()` returns a float score, not article text. `NewsArticle` has no symbol column — articles link to symbols via `SentimentScore`.
   - What's unclear: Should we join SentimentScore → NewsArticle to get article titles for catalyst synthesis, or just pass the sentiment score + direction as catalyst context?
   - Recommendation: Use a lightweight approach — query `SentimentScore` rows for the symbol (already done for sentiment_data), join to `NewsArticle` for titles only, pass top 3-5 article titles as catalyst context to LLM. This avoids adding heavy content to the prompt.

2. **Score delta for catalyst section**
   - What we know: `ScoreRepository.get_previous_date_scores(before_date)` returns (prev_date, scores). We can compute delta = current.total_score - previous.total_score.
   - What's unclear: What if there's no previous score (first run for this stock)?
   - Recommendation: If no previous score, set delta to None and prompt says "Chưa có dữ liệu so sánh" (no comparison data).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ with pytest-asyncio 0.26+ |
| Config file | `apps/prometheus/pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `cd apps/prometheus && uv run pytest tests/test_services/test_report_service.py -x -q` |
| Full suite command | `cd apps/prometheus && uv run pytest tests/ -x -q --timeout=30` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REPORT-01 | Entry zone = nearest_support → bb_upper, fallback close ± 2% | unit | `uv run pytest tests/test_reports/test_price_levels.py::test_entry_zone -x` | ❌ Wave 0 |
| REPORT-01 | Fallback triggers when < 40 price history rows | unit | `uv run pytest tests/test_reports/test_price_levels.py::test_entry_zone_fallback -x` | ❌ Wave 0 |
| REPORT-02 | Stop-loss = max(support_2, close × 0.93) | unit | `uv run pytest tests/test_reports/test_price_levels.py::test_stop_loss -x` | ❌ Wave 0 |
| REPORT-02 | Target price = nearest_resistance or close × 1.10 | unit | `uv run pytest tests/test_reports/test_price_levels.py::test_target_price -x` | ❌ Wave 0 |
| REPORT-03 | Risk rating normalized to high/medium/low | unit | `uv run pytest tests/test_reports/test_generator.py::test_normalize_risk_rating -x` | ✅ (in existing test_report_service.py pattern) |
| REPORT-04 | Signal conflict when |gap| > 25, None when ≤ 25 | unit | `uv run pytest tests/test_reports/test_price_levels.py::test_signal_conflict -x` | ❌ Wave 0 |
| REPORT-05 | Catalyst includes news summary + score delta | integration | `uv run pytest tests/test_services/test_report_service.py::test_catalyst_wiring -x` | ❌ Wave 0 |
| ALL | Full pipeline generates report with all 6 fields | integration | `uv run pytest tests/test_services/test_report_service.py::test_run_full_with_new_fields -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/prometheus && uv run pytest tests/test_reports/ tests/test_services/test_report_service.py -x -q`
- **Per wave merge:** `cd apps/prometheus && uv run pytest tests/ -x -q --timeout=30`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reports/__init__.py` — package init
- [ ] `tests/test_reports/test_price_levels.py` — covers REPORT-01, REPORT-02, REPORT-04 pure functions
- [ ] `tests/test_services/test_report_service.py` — extend existing file with new field integration tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Pydantic StockReport model validates LLM output; _validate_price_levels() enforces ±30% range |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM price hallucination | Tampering | Pre-compute prices in Python; _validate_price_levels() rejects out-of-range values |
| Prompt injection via news content | Tampering | Article text already truncated to 2000 chars in sentiment classification; catalyst uses titles only |

## Sources

### Primary (HIGH confidence)
- `apps/prometheus/src/localstock/services/report_service.py` — full orchestration pipeline reviewed
- `apps/prometheus/src/localstock/reports/generator.py` — ReportDataBuilder, validation, formatting
- `apps/prometheus/src/localstock/ai/client.py` — StockReport 15-field Pydantic model
- `apps/prometheus/src/localstock/ai/prompts.py` — REPORT_USER_TEMPLATE structure
- `apps/prometheus/src/localstock/analysis/technical.py` — TechnicalAnalyzer, Bollinger band mapping
- `apps/prometheus/src/localstock/db/models.py` — CompositeScore.total_score, AnalysisReport.content_json, NewsArticle, SentimentScore
- `apps/prometheus/src/localstock/db/repositories/score_repo.py` — get_previous_date_scores()
- `apps/prometheus/src/localstock/db/repositories/news_repo.py` — get_recent()
- `apps/prometheus/src/localstock/db/repositories/sentiment_repo.py` — get_by_symbol()
- `.planning/phases/20-service-wiring-report-content/20-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — REPORT-01 through REPORT-05 acceptance criteria
- `.planning/STATE.md` — project decisions, no new dependencies

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all existing libraries verified in codebase
- Architecture: HIGH — clear insertion points identified in report_service.py pipeline
- Pitfalls: HIGH — all pitfalls derived from direct code inspection of actual source files

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable — internal codebase, no external API changes)
