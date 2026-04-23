"use client";

import { useState, useMemo, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  RefreshCw,
  BarChart3,
  Calculator,
  FileText,
  Play,
  Loader2,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  useTrackedStocks,
  useTriggerAdminCrawl,
  useTriggerAdminAnalyze,
  useTriggerAdminScore,
  useTriggerAdminReport,
  useTriggerAdminPipeline,
} from "@/lib/queries";
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
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

type SortKey = "symbol" | "name" | "exchange" | "industry";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 50;

interface PipelineControlProps {
  onOperationTriggered: () => void;
  onReportTriggered?: (data: { jobId: number; symbols: string[] }) => void;
  reportMinimized?: boolean;
  onReportReopen?: () => void;
}

export function PipelineControl({ onOperationTriggered, onReportTriggered, reportMinimized, onReportReopen }: PipelineControlProps) {
  const t = useTranslations("admin");
  const { data, isLoading } = useTrackedStocks();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);

  const triggerCrawl = useTriggerAdminCrawl();
  const triggerAnalyze = useTriggerAdminAnalyze();
  const triggerScore = useTriggerAdminScore();
  const triggerReport = useTriggerAdminReport();
  const triggerPipeline = useTriggerAdminPipeline();

  const rawStocks = data?.stocks;

  const filteredAndSorted = useMemo(() => {
    if (!rawStocks) return [];
    let list = rawStocks;
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
  }, [rawStocks, searchQuery, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filteredAndSorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageSlice = filteredAndSorted.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  // Selection uses all filtered items, not just visible page
  const validSelected = useMemo(() => {
    const symbols = new Set(filteredAndSorted.map((s) => s.symbol));
    return new Set([...selected].filter((s) => symbols.has(s)));
  }, [filteredAndSorted, selected]);

  // Page-level select all
  const pageSymbols = pageSlice.map((s) => s.symbol);
  const allPageSelected =
    pageSymbols.length > 0 && pageSymbols.every((s) => validSelected.has(s));
  const somePageSelected =
    pageSymbols.some((s) => validSelected.has(s)) && !allPageSelected;

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

  const toggleAll = useCallback(() => {
    setSelected((prev) => {
      const next = new Set(prev);
      const symbols = pageSlice.map((s) => s.symbol);
      const allChecked = symbols.every((s) => next.has(s));
      if (allChecked) {
        symbols.forEach((s) => next.delete(s));
      } else {
        symbols.forEach((s) => next.add(s));
      }
      return next;
    });
  }, [pageSlice]);

  const toggleOne = useCallback((symbol: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  }, []);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(0);
  }, []);

  const handleMutationError = useCallback((error: Error) => {
    if (error.message.includes("409")) {
      toast.error(t("toast.operationLocked"));
    } else {
      toast.error(t("toast.error", { detail: error.message }));
    }
  }, [t]);

  const handleSuccess = useCallback((type: string) => {
    toast(t("toast.operationStarted", { type }));
    onOperationTriggered();
  }, [t, onOperationTriggered]);

  const anyPending =
    triggerCrawl.isPending ||
    triggerAnalyze.isPending ||
    triggerScore.isPending ||
    triggerReport.isPending ||
    triggerPipeline.isPending;

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (!rawStocks || rawStocks.length === 0) {
    return (
      <EmptyState
        heading={t("stocks.emptyHeading")}
        body={t("pipeline.noSelection")}
      />
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <Button
          variant="outline"
          disabled={validSelected.size === 0 || triggerCrawl.isPending}
          onClick={() =>
            triggerCrawl.mutate([...validSelected], {
              onSuccess: () => handleSuccess(t("pipeline.crawl")),
              onError: handleMutationError,
            })
          }
        >
          {triggerCrawl.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-1" />
          )}
          {t("pipeline.crawl")}
        </Button>

        <Button
          variant="outline"
          disabled={validSelected.size === 0 || triggerAnalyze.isPending}
          onClick={() =>
            triggerAnalyze.mutate([...validSelected], {
              onSuccess: () => handleSuccess(t("pipeline.analyze")),
              onError: handleMutationError,
            })
          }
        >
          {triggerAnalyze.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <BarChart3 className="h-4 w-4 mr-1" />
          )}
          {t("pipeline.analyze")}
        </Button>

        <Button
          variant="outline"
          disabled={validSelected.size === 0 || triggerScore.isPending}
          onClick={() =>
            triggerScore.mutate([...validSelected], {
              onSuccess: () => handleSuccess(t("pipeline.score")),
              onError: handleMutationError,
            })
          }
        >
          {triggerScore.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Calculator className="h-4 w-4 mr-1" />
          )}
          {t("pipeline.score")}
        </Button>

        <Button
          variant="outline"
          disabled={reportMinimized ? false : (validSelected.size === 0 || triggerReport.isPending)}
          onClick={() => {
            if (reportMinimized) {
              onReportReopen?.();
              return;
            }
            triggerReport.mutate([...validSelected], {
              onSuccess: (data) => {
                handleSuccess(t("pipeline.report"));
                onReportTriggered?.({ jobId: data.job_id, symbols: [...validSelected] });
              },
              onError: handleMutationError,
            });
          }}
          className="relative"
        >
          {triggerReport.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <FileText className="h-4 w-4 mr-1" />
          )}
          {t("pipeline.report")}
          {reportMinimized && (
            <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-primary step-active-pulse" />
          )}
        </Button>

        <Button
          disabled={validSelected.size === 0 || triggerPipeline.isPending || anyPending}
          onClick={() =>
            triggerPipeline.mutate([...validSelected], {
              onSuccess: () => handleSuccess(t("pipeline.runAll")),
              onError: handleMutationError,
            })
          }
        >
          {triggerPipeline.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-1" />
          )}
          {t("pipeline.runAll")}
        </Button>

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

      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-muted-foreground">
          {t("pipeline.selected", { count: validSelected.size })}
        </span>
        {searchQuery && (
          <span className="text-xs text-muted-foreground">
            {filteredAndSorted.length}/{rawStocks.length}
          </span>
        )}
      </div>

      {filteredAndSorted.length === 0 && searchQuery ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          {t("stocks.noResults")}
        </p>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={allPageSelected}
                    indeterminate={somePageSelected}
                    onCheckedChange={toggleAll}
                  />
                </TableHead>
                {(["symbol", "name", "exchange", "industry"] as SortKey[]).map(
                  (key) => (
                    <TableHead key={key}>
                      <button
                        className="flex items-center gap-1 hover:text-foreground transition-colors"
                        onClick={() => toggleSort(key)}
                        aria-label={t(`stocks.columns.${key}`) + (sortKey === key ? `, ${sortDir === "asc" ? "ascending" : "descending"}` : "")}
                        aria-pressed={sortKey === key}
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
              </TableRow>
            </TableHeader>
            <TableBody>
              {pageSlice.map((stock) => (
                <TableRow key={stock.symbol}>
                  <TableCell>
                    <Checkbox
                      checked={validSelected.has(stock.symbol)}
                      onCheckedChange={() => toggleOne(stock.symbol)}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{stock.symbol}</TableCell>
                  <TableCell>{stock.name ?? "—"}</TableCell>
                  <TableCell>{stock.exchange ?? "—"}</TableCell>
                  <TableCell>{stock.industry ?? "—"}</TableCell>
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
