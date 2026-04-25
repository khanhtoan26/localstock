// These imports will resolve after Wave 2 creates the filter-stocks module.
// For now, stubs are written to fail with "not implemented".
import { filterStocks } from "../src/components/rankings/filter-stocks";

import { describe, it, expect } from "vitest";

describe("filterStocks", () => {
  it("empty query returns all stocks unchanged", () => {
    // STUB: filterStocks([stock1, stock2, stock3], "")
    // Expected: result.length === 3 (all stocks returned)
    expect(true).toBe(false); // not implemented
  });

  it("'vnm' matches symbol 'VNM' (case-insensitive prefix match)", () => {
    // STUB: filterStocks([{symbol:'VNM', ...}, {symbol:'FPT', ...}], "vnm")
    // Expected: result.length === 1 && result[0].symbol === 'VNM'
    expect(true).toBe(false); // not implemented
  });

  it("'NM' does NOT match symbol 'VNM' (substring that is not a prefix is rejected)", () => {
    // STUB: filterStocks([{symbol:'VNM', ...}], "NM")
    // Expected: result.length === 0 (NM is not a prefix of VNM)
    expect(true).toBe(false); // not implemented
  });

  it("name substring match — 'vinamilk' matches stock with name containing 'Vinamilk'", () => {
    // STUB: filterStocks([{symbol:'VNM', name:'Công ty Vinamilk', ...}], "vinamilk")
    // Expected: result.length === 1 (name substring match, case-insensitive)
    expect(true).toBe(false); // not implemented
  });

  it("null name field — treated as empty string, no crash", () => {
    // STUB: filterStocks([{symbol:'AAA', name: null, ...}], "vinamilk")
    // Expected: no error thrown, result.length === 0 (null name treated as empty string)
    expect(true).toBe(false); // not implemented
  });

  it("whitespace-only query — treated as empty, returns all stocks", () => {
    // STUB: filterStocks([stock1, stock2], "   ")
    // Expected: result.length === 2 (whitespace trimmed to empty, all stocks returned)
    expect(true).toBe(false); // not implemented
  });
});
