"use client";

import { useState, useMemo, useCallback, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Plus, X, Loader2, Search, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight } from "lucide-react";
import { useTrackedStocks, useAddStock, useRemoveStock } from "@/lib/queries";
import type { TrackedStock } from "@/lib/types";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";

type SortKey = "symbol" | "name" | "exchange" | "industry";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 50;

export function StockTable() {
  const t = useTranslations("admin");
  const { data, isLoading, isError } = useTrackedStocks();
  const addStock = useAddStock();
  const removeStock = useRemoveStock();
  const [symbolInput, setSymbolInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);

  const toggleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return prev;
      }
      setSortDir("asc");
      return key;
    });
    setPage(0);
  }, []);

  const stocks = data?.stocks;

  const filteredAndSorted = useMemo(() => {
    if (!stocks) return [];
    let list = stocks;
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter(
        (s: TrackedStock) =>
          s.symbol.toLowerCase().includes(q) ||
          (s.name ?? "").toLowerCase().includes(q) ||
          (s.exchange ?? "").toLowerCase().includes(q) ||
          (s.industry ?? "").toLowerCase().includes(q),
      );
    }
    return [...list].sort((a: TrackedStock, b: TrackedStock) => {
      const av = (a[sortKey] ?? "").toLowerCase();
      const bv = (b[sortKey] ?? "").toLowerCase();
      const cmp = av.localeCompare(bv);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [stocks, searchQuery, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filteredAndSorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageSlice = filteredAndSorted.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(0);
  }, []);

  const handleSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    const trimmed = symbolInput.trim();
    if (!trimmed || !/^[A-Z0-9]+$/.test(trimmed)) return;
    addStock.mutate(trimmed, {
      onSuccess: () => {
        setSymbolInput("");
        toast(t("toast.stockAdded", { symbol: trimmed }));
      },
      onError: (error: Error) => {
        if (error.message.includes("409")) {
          toast.error(t("toast.alreadyTracked", { symbol: trimmed }));
        } else {
          toast.error(t("toast.error", { detail: error.message }));
        }
      },
    });
  }, [symbolInput, addStock, t]);

  const handleRemove = useCallback((symbol: string) => {
    removeStock.mutate(symbol, {
      onSuccess: () => {
        toast(t("toast.stockRemoved", { symbol }));
      },
      onError: (error: Error) => {
        toast.error(t("toast.error", { detail: error.message }));
      },
    });
  }, [removeStock, t]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return <ErrorState />;
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <Input
            placeholder={t("stocks.placeholder")}
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
            className="max-w-xs"
          />
          <Button type="submit" disabled={addStock.isPending}>
            {addStock.isPending ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Plus className="h-4 w-4 mr-1" />
            )}
            {t("stocks.add")}
          </Button>
        </form>
        <div className="relative ml-auto">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t("stocks.search")}
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-8 max-w-xs"
          />
        </div>
      </div>

      {data && data.count === 0 ? (
        <EmptyState
          heading={t("stocks.emptyHeading")}
          body={t("stocks.emptyBody")}
        />
      ) : filteredAndSorted.length === 0 && searchQuery ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          {t("stocks.noResults")}
        </p>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                {(["symbol", "name", "exchange", "industry"] as SortKey[]).map(
                  (key) => (
                    <TableHead key={key}>
                      <button
                        className="flex items-center gap-1 hover:text-foreground transition-colors"
                        onClick={() => toggleSort(key)}
                      >
                        {t(`stocks.columns.${key}`)}
                        {sortKey === key ? (
                          sortDir === "asc" ? (
                            <ArrowUp className="h-3 w-3" />
                          ) : (
                            <ArrowDown className="h-3 w-3" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3 w-3 opacity-30" />
                        )}
                      </button>
                    </TableHead>
                  ),
                )}
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {pageSlice.map((stock) => (
                <TableRow key={stock.symbol}>
                  <TableCell className="font-medium">{stock.symbol}</TableCell>
                  <TableCell>{stock.name ?? "—"}</TableCell>
                  <TableCell>{stock.exchange ?? "—"}</TableCell>
                  <TableCell>{stock.industry ?? "—"}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemove(stock.symbol)}
                      aria-label={t("stocks.remove")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-sm text-muted-foreground">
              <span>
                {safePage * PAGE_SIZE + 1}–{Math.min((safePage + 1) * PAGE_SIZE, filteredAndSorted.length)}{" "}
                / {filteredAndSorted.length}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  disabled={safePage === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="px-2">
                  {safePage + 1} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  disabled={safePage >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
