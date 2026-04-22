"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  RefreshCw,
  BarChart3,
  Calculator,
  Play,
  Loader2,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import {
  useTrackedStocks,
  useTriggerAdminCrawl,
  useTriggerAdminAnalyze,
  useTriggerAdminScore,
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

interface PipelineControlProps {
  onOperationTriggered: () => void;
}

export function PipelineControl({ onOperationTriggered }: PipelineControlProps) {
  const t = useTranslations("admin");
  const { data, isLoading } = useTrackedStocks();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const triggerCrawl = useTriggerAdminCrawl();
  const triggerAnalyze = useTriggerAdminAnalyze();
  const triggerScore = useTriggerAdminScore();
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

  // Sync selection with filtered stock list
  const validSelected = useMemo(() => {
    const symbols = new Set(filteredAndSorted.map((s) => s.symbol));
    return new Set([...selected].filter((s) => symbols.has(s)));
  }, [filteredAndSorted, selected]);

  const allSelected =
    validSelected.size === filteredAndSorted.length && filteredAndSorted.length > 0;
  const someSelected =
    validSelected.size > 0 && validSelected.size < filteredAndSorted.length;

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filteredAndSorted.map((s) => s.symbol)));
    }
  }

  function toggleOne(symbol: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  }

  function handleMutationError(error: Error) {
    if (error.message.includes("409")) {
      toast.error(t("toast.operationLocked"));
    } else {
      toast.error(t("toast.error", { detail: error.message }));
    }
  }

  function handleSuccess(type: string) {
    toast(t("toast.operationStarted", { type }));
    onOperationTriggered();
  }

  const anyPending =
    triggerCrawl.isPending ||
    triggerAnalyze.isPending ||
    triggerScore.isPending ||
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
            onChange={(e) => setSearchQuery(e.target.value)}
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
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={allSelected}
                  indeterminate={someSelected}
                  onCheckedChange={toggleAll}
                />
              </TableHead>
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAndSorted.map((stock) => (
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
      )}
    </div>
  );
}
