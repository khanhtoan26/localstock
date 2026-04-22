"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Plus, X, Loader2 } from "lucide-react";
import { useTrackedStocks, useAddStock, useRemoveStock } from "@/lib/queries";
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

export function StockTable() {
  const t = useTranslations("admin");
  const { data, isLoading, isError } = useTrackedStocks();
  const addStock = useAddStock();
  const removeStock = useRemoveStock();
  const [symbolInput, setSymbolInput] = useState("");

  function handleSubmit(e: FormEvent) {
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
  }

  function handleRemove(symbol: string) {
    removeStock.mutate(symbol, {
      onSuccess: () => {
        toast(t("toast.stockRemoved", { symbol }));
      },
      onError: (error: Error) => {
        toast.error(t("toast.error", { detail: error.message }));
      },
    });
  }

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
      <form onSubmit={handleSubmit} className="flex items-center gap-2 mb-4">
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

      {data && data.count === 0 ? (
        <EmptyState
          heading={t("stocks.emptyHeading")}
          body={t("stocks.emptyBody")}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("stocks.columns.symbol")}</TableHead>
              <TableHead>{t("stocks.columns.name")}</TableHead>
              <TableHead>{t("stocks.columns.exchange")}</TableHead>
              <TableHead>{t("stocks.columns.industry")}</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.stocks.map((stock) => (
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
      )}
    </div>
  );
}
