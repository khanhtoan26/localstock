import { filterStocks } from "../src/components/rankings/filter-stocks";

import { describe, it, expect } from "vitest";
import type { StockScore } from "../src/lib/types";

function makeStock(symbol: string, extraProps?: Record<string, unknown>): StockScore {
  return {
    symbol,
    date: "2024-01-01",
    total_score: 80,
    grade: "A",
    rank: 1,
    technical_score: null,
    fundamental_score: null,
    sentiment_score: null,
    macro_score: null,
    dimensions_used: 0,
    weights: null,
    recommendation: null,
    ...extraProps,
  } as StockScore;
}

const vnm = makeStock("VNM", { name: "Công ty Vinamilk" });
const fpt = makeStock("FPT", { name: "Công ty FPT" });
const aaa = makeStock("AAA", { name: null });

describe("filterStocks", () => {
  it("empty query returns all stocks unchanged", () => {
    const stocks = [vnm, fpt, aaa];
    const result = filterStocks(stocks, "");
    expect(result).toHaveLength(3);
  });

  it("'vnm' matches symbol 'VNM' (case-insensitive prefix match)", () => {
    const stocks = [vnm, fpt];
    const result = filterStocks(stocks, "vnm");
    expect(result).toHaveLength(1);
    expect(result[0].symbol).toBe("VNM");
  });

  it("'NM' does NOT match symbol 'VNM' (substring that is not a prefix is rejected)", () => {
    const stocks = [vnm, fpt];
    const result = filterStocks(stocks, "NM");
    expect(result).toHaveLength(0);
  });

  it("name substring match — 'vinamilk' matches stock with name containing 'Vinamilk'", () => {
    const stocks = [vnm, fpt];
    const result = filterStocks(stocks, "vinamilk");
    expect(result).toHaveLength(1);
    expect(result[0].symbol).toBe("VNM");
  });

  it("null name field — treated as empty string, no crash", () => {
    const stocks = [aaa];
    let result: StockScore[] | undefined;
    expect(() => {
      result = filterStocks(stocks, "vinamilk");
    }).not.toThrow();
    expect(result).toHaveLength(0);
  });

  it("whitespace-only query — treated as empty, returns all stocks", () => {
    const stocks = [vnm, fpt, aaa];
    expect(filterStocks(stocks, "   ")).toHaveLength(3);
  });
});
