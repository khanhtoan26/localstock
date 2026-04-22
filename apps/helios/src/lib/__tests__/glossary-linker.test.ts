import { describe, it, expect } from "vitest";
import {
  buildAliasMap,
  scanText,
  isWordBoundary,
  type AliasMapping,
  type GlossaryMatch,
} from "../glossary-linker";

describe("isWordBoundary", () => {
  it("returns true for undefined (start/end of string)", () => {
    expect(isWordBoundary(undefined)).toBe(true);
  });

  it("returns true for space", () => {
    expect(isWordBoundary(" ")).toBe(true);
  });

  it("returns true for punctuation", () => {
    expect(isWordBoundary(",")).toBe(true);
    expect(isWordBoundary(".")).toBe(true);
    expect(isWordBoundary("(")).toBe(true);
    expect(isWordBoundary(")")).toBe(true);
  });

  it("returns false for letters", () => {
    expect(isWordBoundary("a")).toBe(false);
    expect(isWordBoundary("Z")).toBe(false);
  });

  it("returns false for digits", () => {
    expect(isWordBoundary("0")).toBe(false);
    expect(isWordBoundary("9")).toBe(false);
  });

  it("returns false for Unicode letters (Vietnamese)", () => {
    expect(isWordBoundary("ệ")).toBe(false);
    expect(isWordBoundary("ớ")).toBe(false);
  });
});

describe("buildAliasMap", () => {
  it("returns array of AliasMapping sorted by aliasLower.length descending", () => {
    const map = buildAliasMap();
    expect(Array.isArray(map)).toBe(true);
    expect(map.length).toBeGreaterThan(0);

    // Verify sorted by length descending
    for (let i = 1; i < map.length; i++) {
      expect(map[i - 1].aliasLower.length).toBeGreaterThanOrEqual(
        map[i].aliasLower.length,
      );
    }
  });

  it("each mapping has aliasLower, alias, and entry", () => {
    const map = buildAliasMap();
    for (const m of map) {
      expect(typeof m.aliasLower).toBe("string");
      expect(typeof m.alias).toBe("string");
      expect(m.entry).toBeDefined();
      expect(m.aliasLower).toBe(m.alias.toLowerCase());
    }
  });
});

describe("scanText", () => {
  // Build the alias map once for all tests
  let aliasMap: AliasMapping[];

  function getAliasMap() {
    if (!aliasMap) aliasMap = buildAliasMap();
    return aliasMap;
  }

  it("longest match beats shorter: 'Chỉ số RSI' beats 'RSI'", () => {
    const result = scanText(
      "Chỉ số RSI hiện tại là 72",
      getAliasMap(),
      new Set<string>(),
    );

    // Should contain a GlossaryMatch for "Chỉ số RSI" (longest alias)
    const matches = result.filter(
      (seg): seg is GlossaryMatch => typeof seg !== "string",
    );
    expect(matches.length).toBe(1);
    expect(matches[0].matchedText).toBe("Chỉ số RSI");
    expect(matches[0].entry.id).toBe("rsi");
  });

  it("first occurrence only — second RSI is NOT linked", () => {
    const result = scanText(
      "RSI là 72. RSI tiếp tục tăng",
      getAliasMap(),
      new Set<string>(),
    );

    const matches = result.filter(
      (seg): seg is GlossaryMatch => typeof seg !== "string",
    );
    expect(matches.length).toBe(1);
    expect(matches[0].matchedText).toBe("RSI");
  });

  it("case-insensitive match, preserves original case", () => {
    const result = scanText(
      "rsi đang tăng",
      getAliasMap(),
      new Set<string>(),
    );

    const matches = result.filter(
      (seg): seg is GlossaryMatch => typeof seg !== "string",
    );
    expect(matches.length).toBe(1);
    expect(matches[0].matchedText).toBe("rsi"); // preserves original casing
    expect(matches[0].entry.id).toBe("rsi");
  });

  it("word boundary prevents partial matches: MA should NOT match inside 'thematic'", () => {
    const result = scanText(
      "thematic content",
      getAliasMap(),
      new Set<string>(),
    );

    const matches = result.filter(
      (seg): seg is GlossaryMatch => typeof seg !== "string",
    );
    expect(matches.length).toBe(0);

    // Should be returned as a single string segment
    expect(result).toEqual(["thematic content"]);
  });

  it("no glossary matches returns single string segment", () => {
    const result = scanText(
      "no terms here",
      getAliasMap(),
      new Set<string>(),
    );

    expect(result).toEqual(["no terms here"]);
  });

  it("respects linkedIds — skips already-linked entries", () => {
    const linkedIds = new Set<string>(["rsi"]);
    const result = scanText(
      "RSI đang tăng",
      getAliasMap(),
      linkedIds,
    );

    const matches = result.filter(
      (seg): seg is GlossaryMatch => typeof seg !== "string",
    );
    expect(matches.length).toBe(0);
  });

  it("does not produce empty string segments", () => {
    const result = scanText(
      "RSI là chỉ báo",
      getAliasMap(),
      new Set<string>(),
    );

    for (const seg of result) {
      if (typeof seg === "string") {
        expect(seg.length).toBeGreaterThan(0);
      }
    }
  });

  it("handles multiple different terms in one text", () => {
    const result = scanText(
      "RSI là 72 và MACD đang tăng",
      getAliasMap(),
      new Set<string>(),
    );

    const matches = result.filter(
      (seg): seg is GlossaryMatch => typeof seg !== "string",
    );
    expect(matches.length).toBe(2);
    const ids = matches.map((m) => m.entry.id);
    expect(ids).toContain("rsi");
    expect(ids).toContain("macd");
  });
});
