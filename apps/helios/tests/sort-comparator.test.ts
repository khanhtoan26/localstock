import { describe, it, expect } from "vitest";
import { sortStocks } from "../src/components/rankings/sort-comparator";
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
    const data: StockScore[] = [
      makeStock({ symbol: "VNM", total_score: 70 }),
      makeStock({ symbol: "FPT", total_score: 80 }),
    ];
    const result = sortStocks(data, "total_score", "desc");
    expect(result[0].symbol).toBe("FPT");
    expect(result[1].symbol).toBe("VNM");
  });

  it("numeric asc — stock with score 70 appears before stock with score 80", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "FPT", total_score: 80 }),
      makeStock({ symbol: "VNM", total_score: 70 }),
    ];
    const result = sortStocks(data, "total_score", "asc");
    expect(result[0].symbol).toBe("VNM");
    expect(result[1].symbol).toBe("FPT");
  });

  it("null values — null score stock appears last in desc (via -Infinity sentinel)", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "NULL", technical_score: null }),
      makeStock({ symbol: "HIGH", technical_score: 80 }),
    ];
    const result = sortStocks(data, "technical_score", "desc");
    expect(result[0].symbol).toBe("HIGH");
    expect(result[1].symbol).toBe("NULL");
  });

  it("tiebreaker — two stocks with equal scores sorted A→Z by symbol ('AAA' before 'BBB')", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "BBB", total_score: 75 }),
      makeStock({ symbol: "AAA", total_score: 75 }),
    ];
    const result = sortStocks(data, "total_score", "desc");
    expect(result[0].symbol).toBe("AAA");
    expect(result[1].symbol).toBe("BBB");
  });

  it("grade desc — A+ (rank 1) appears before C (rank 5) when sortDir is 'desc'", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "BAD", grade: "C" }),
      makeStock({ symbol: "TOP", grade: "A+" }),
    ];
    const result = sortStocks(data, "grade", "desc");
    expect(result[0].grade).toBe("A+");
    expect(result[1].grade).toBe("C");
  });

  it("grade asc — C (rank 5) appears before A+ (rank 1) when sortDir is 'asc'", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "TOP", grade: "A+" }),
      makeStock({ symbol: "BAD", grade: "C" }),
    ];
    const result = sortStocks(data, "grade", "asc");
    expect(result[0].grade).toBe("C");
    expect(result[1].grade).toBe("A+");
  });

  it("grade unknown — unknown grade string falls back to rank 99, appears last", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "UNK", grade: "Z" }),
      makeStock({ symbol: "BAD", grade: "C" }),
    ];
    const result = sortStocks(data, "grade", "desc");
    // C has rank 5, Z (unknown) has rank 99 — so C appears first in desc (best first)
    expect(result[0].grade).toBe("C");
    expect(result[1].grade).toBe("Z");
  });

  it("recommendation guard — calling sort with key 'recommendation' returns unchanged order", () => {
    const data: StockScore[] = [
      makeStock({ symbol: "FIRST", recommendation: "MUA" }),
      makeStock({ symbol: "SECOND", recommendation: "GIU" }),
    ];
    const result = sortStocks(data, "recommendation", "desc");
    // Original order preserved
    expect(result[0].symbol).toBe("FIRST");
    expect(result[1].symbol).toBe("SECOND");
  });
});
