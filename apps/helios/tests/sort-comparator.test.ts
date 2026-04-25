// These imports will resolve after Wave 1 extracts the sort logic to a separate module.
// For now, stubs are written to fail with "not implemented".
import { sortStocks } from "../src/components/rankings/sort-comparator";

import { describe, it, expect } from "vitest";
import type { StockScore } from "../src/lib/types";

// Helper to create a minimal StockScore stub for testing
function makeStock(overrides: Partial<StockScore>): StockScore {
  return {
    symbol: "AAA",
    date: "2026-01-01",
    total_score: 50,
    grade: "B",
    rank: 1,
    technical_score: null,
    fundamental_score: null,
    sentiment_score: null,
    macro_score: null,
    dimensions_used: 0,
    weights: null,
    recommendation: null,
    ...overrides,
  };
}

describe("sortStocks", () => {
  it("numeric desc — stock with score 80 appears before stock with score 70", () => {
    // STUB: sortStocks([{total_score:70}, {total_score:80}], "total_score", "desc")
    // Expected: result[0].total_score === 80
    expect(true).toBe(false); // not implemented
  });

  it("numeric asc — stock with score 70 appears before stock with score 80", () => {
    // STUB: sortStocks([{total_score:80}, {total_score:70}], "total_score", "asc")
    // Expected: result[0].total_score === 70
    expect(true).toBe(false); // not implemented
  });

  it("null values — null score stock appears last in desc (via -Infinity sentinel)", () => {
    // STUB: sortStocks([{total_score:null}, {total_score:80}], "total_score", "desc")
    // Expected: result[1].total_score === null (null stock last)
    expect(true).toBe(false); // not implemented
  });

  it("tiebreaker — two stocks with equal scores sorted A→Z by symbol ('AAA' before 'BBB')", () => {
    // STUB: sortStocks([{symbol:'BBB', total_score:75}, {symbol:'AAA', total_score:75}], "total_score", "desc")
    // Expected: result[0].symbol === 'AAA'
    expect(true).toBe(false); // not implemented
  });

  it("grade desc — A+ (rank 1) appears before C (rank 5) when sortDir is 'desc'", () => {
    // STUB: sortStocks([{grade:'C'}, {grade:'A+'}], "grade", "desc")
    // Expected: result[0].grade === 'A+'
    expect(true).toBe(false); // not implemented
  });

  it("grade asc — C (rank 5) appears before A+ (rank 1) when sortDir is 'asc'", () => {
    // STUB: sortStocks([{grade:'A+'}, {grade:'C'}], "grade", "asc")
    // Expected: result[0].grade === 'C'
    expect(true).toBe(false); // not implemented
  });

  it("grade unknown — unknown grade string falls back to rank 99, appears last", () => {
    // STUB: sortStocks([{grade:'UNKNOWN'}, {grade:'C'}], "grade", "desc")
    // Expected: result[1].grade === 'UNKNOWN' (unknown grade last)
    expect(true).toBe(false); // not implemented
  });

  it("recommendation guard — calling sort with key 'recommendation' returns unchanged order", () => {
    // STUB: sortStocks([stockA, stockB], "recommendation", "desc")
    // Expected: result order is identical to input order (recommendation is non-sortable)
    expect(true).toBe(false); // not implemented
  });
});
