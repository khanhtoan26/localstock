import type { StockScore } from "@/lib/types";

export type SortKey = keyof StockScore;
export type SortDir = "asc" | "desc";

// D-04: Grade semantic rank map. Lower number = better grade.
// "desc" user intent for grade = best first = ascending on rank value.
export const GRADE_RANK: Record<string, number> = {
  "A+": 1,
  "A": 2,
  "B+": 3,
  "B": 4,
  "C": 5,
};

/**
 * Sort an array of StockScore objects by the given key and direction.
 * - Grade column: uses GRADE_RANK semantic sort (desc = A+ first, asc = C first).
 * - Recommendation column: no-op guard — returns original order (D-03).
 * - Null numeric values: -Infinity sentinel keeps them last in desc (D-05).
 * - Equal values: tiebreaker by symbol.localeCompare (D-01).
 */
export function sortStocks(
  data: StockScore[],
  sortKey: SortKey,
  sortDir: SortDir,
): StockScore[] {
  // D-03: Recommendation is not sortable — return original order unchanged.
  if (sortKey === "recommendation") return [...data];

  return [...data].sort((a, b) => {
    if (sortKey === "grade") {
      // D-04: Grade sort direction inversion (Pitfall 2 in RESEARCH.md).
      // GRADE_RANK["A+"] = 1 is the smallest number.
      // User clicks "desc" to mean "best first" = A+ first.
      // Achieving "A+ first" requires ascending sort on rank numbers.
      // Therefore: when sortDir === "desc", we invert the comparator direction.
      const aRank = GRADE_RANK[a.grade] ?? 99;
      const bRank = GRADE_RANK[b.grade] ?? 99;
      if (aRank < bRank) return sortDir === "desc" ? -1 : 1;
      if (aRank > bRank) return sortDir === "desc" ? 1 : -1;
    } else {
      // D-05: Use -Infinity for null numeric values.
      const aVal = (a[sortKey] as number | null) ?? -Infinity;
      const bVal = (b[sortKey] as number | null) ?? -Infinity;
      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
    }
    // D-01: Tiebreaker — alphabetical by symbol.
    return a.symbol.localeCompare(b.symbol);
  });
}
