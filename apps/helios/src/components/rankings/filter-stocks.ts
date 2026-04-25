import type { StockScore } from "@/lib/types";

/**
 * Client-side filter for StockScore[] by query string.
 * - Empty or whitespace-only query: returns all stocks (D-07).
 * - Symbol prefix match: case-insensitive, starts-with only (not substring).
 * - Name substring match: case-insensitive includes (forward-compatible; StockScore has no name field yet).
 * @param stocks - Array to filter (already fetched, not paginated)
 * @param q - Search query from URL param ?q=
 */
export function filterStocks(
  stocks: StockScore[],
  q: string,
): StockScore[] {
  if (!q.trim()) return stocks;
  const lower = q.toLowerCase();
  return stocks.filter(
    (s) =>
      s.symbol.toLowerCase().startsWith(lower) ||
      ((s as { name?: string | null }).name ?? "").toLowerCase().includes(lower)
  );
}
