"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { RefreshCw, BarChart3, Calculator, Play, Loader2 } from "lucide-react";
import {
  useTrackedStocks,
  useTriggerAdminCrawl,
  useTriggerAdminAnalyze,
  useTriggerAdminScore,
  useTriggerAdminPipeline,
} from "@/lib/queries";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

interface PipelineControlProps {
  onOperationTriggered: () => void;
}

export function PipelineControl({ onOperationTriggered }: PipelineControlProps) {
  const t = useTranslations("admin");
  const { data, isLoading } = useTrackedStocks();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const triggerCrawl = useTriggerAdminCrawl();
  const triggerAnalyze = useTriggerAdminAnalyze();
  const triggerScore = useTriggerAdminScore();
  const triggerPipeline = useTriggerAdminPipeline();

  const stocks = useMemo(() => data?.stocks ?? [], [data?.stocks]);

  // Sync selection with current stock list (pitfall 5: stale selection state)
  const validSelected = useMemo(() => {
    const symbols = new Set(stocks.map((s) => s.symbol));
    return new Set([...selected].filter((s) => symbols.has(s)));
  }, [stocks, selected]);

  const allSelected = validSelected.size === stocks.length && stocks.length > 0;
  const someSelected =
    validSelected.size > 0 && validSelected.size < stocks.length;

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(stocks.map((s) => s.symbol)));
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

  if (stocks.length === 0) {
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
          disabled={triggerScore.isPending}
          onClick={() =>
            triggerScore.mutate(undefined, {
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
          disabled={triggerPipeline.isPending || anyPending}
          onClick={() =>
            triggerPipeline.mutate(undefined, {
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

        <span className="text-sm text-muted-foreground ml-auto">
          {t("pipeline.selected", { count: validSelected.size })}
        </span>
      </div>

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
            <TableHead>{t("stocks.columns.symbol")}</TableHead>
            <TableHead>{t("stocks.columns.name")}</TableHead>
            <TableHead>{t("stocks.columns.exchange")}</TableHead>
            <TableHead>{t("stocks.columns.industry")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {stocks.map((stock) => (
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
    </div>
  );
}
