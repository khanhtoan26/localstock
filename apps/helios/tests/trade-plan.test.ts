import { describe, it, expect } from "vitest";
import { extractTradePlan, getRiskColors } from "@/components/stock/trade-plan-section";

describe("extractTradePlan", () => {
  it("returns null when content_json is null", () => {
    expect(extractTradePlan(null)).toBeNull();
  });

  it("returns null when all price fields are missing (pre-v1.4)", () => {
    expect(extractTradePlan({ summary: "old report" })).toBeNull();
  });

  it("returns null when all price fields are explicitly null", () => {
    expect(
      extractTradePlan({
        entry_price: null,
        stop_loss: null,
        target_price: null,
      }),
    ).toBeNull();
  });

  it("returns TradePlanData when price fields are numbers", () => {
    const result = extractTradePlan({
      entry_price: 45200,
      stop_loss: 43000,
      target_price: 52000,
      risk_rating: "medium",
      signal_conflicts: "RSI overbought vs MACD bullish",
      catalyst: "Q4 earnings beat",
    });
    expect(result).toEqual({
      entry_price: 45200,
      stop_loss: 43000,
      target_price: 52000,
      risk_rating: "medium",
      signal_conflicts: "RSI overbought vs MACD bullish",
      catalyst: "Q4 earnings beat",
    });
  });

  it("handles partial price data (only entry_price present)", () => {
    const result = extractTradePlan({ entry_price: 45200 });
    expect(result).not.toBeNull();
    expect(result!.entry_price).toBe(45200);
    expect(result!.stop_loss).toBeNull();
    expect(result!.target_price).toBeNull();
  });

  it("rejects invalid risk_rating values", () => {
    const result = extractTradePlan({
      entry_price: 45200,
      risk_rating: "extreme",
    });
    expect(result!.risk_rating).toBeNull();
  });

  it("rejects non-string signal_conflicts", () => {
    const result = extractTradePlan({
      entry_price: 45200,
      signal_conflicts: 12345,
    });
    expect(result!.signal_conflicts).toBeNull();
  });
});

describe("getRiskColors", () => {
  it("returns red classes for high", () => {
    expect(getRiskColors("high")).toContain("red");
  });

  it("returns yellow classes for medium", () => {
    expect(getRiskColors("medium")).toContain("yellow");
  });

  it("returns green classes for low", () => {
    expect(getRiskColors("low")).toContain("green");
  });

  it("returns empty string for unknown rating", () => {
    expect(getRiskColors("unknown")).toBe("");
  });
});
