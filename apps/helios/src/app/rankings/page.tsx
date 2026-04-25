"use client";
import { useMemo } from "react";
import { useTopScores, useTriggerPipeline } from "@/lib/queries";
import { useTranslations } from "next-intl";
import { useQueryState, parseAsString } from "nuqs";
import { StockTable } from "@/components/rankings/stock-table";
import { StockSearchInput } from "@/components/rankings/stock-search-input";
import { filterStocks } from "@/components/rankings/filter-stocks";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";

export default function RankingsPage() {
  const { data, isLoading, isError } = useTopScores(50);
  const triggerPipeline = useTriggerPipeline();
  const t = useTranslations("rankings");
  const tc = useTranslations("common");
  // Hooks must come before early returns
  const [q] = useQueryState("q", parseAsString.withDefault(""));
  const filtered = useMemo(
    () => filterStocks(data?.stocks ?? [], q),
    [data?.stocks, q]
  );

  if (isLoading) {
    return (
      <div>
        <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
        <ErrorState />
      </div>
    );
  }

  if (!data || data.count === 0) {
    return (
      <div>
        <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
        <EmptyState
          body={t("emptyBody")}
          ctaLabel={tc("runPipeline")}
          onCtaClick={() => triggerPipeline.mutate()}
        />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
      <StockSearchInput />
      {filtered.length === 0 && q.trim() ? (
        <p className="text-sm text-muted-foreground py-8 text-center">
          {t("noResults", { query: q })}
        </p>
      ) : (
        <StockTable data={filtered} />
      )}
    </div>
  );
}
