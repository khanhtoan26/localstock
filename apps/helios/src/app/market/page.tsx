"use client";
import { useMacroLatest, useMarketSummary, useSectorsLatest } from "@/lib/queries";
import { useTranslations } from "next-intl";
import { MacroCards } from "@/components/market/macro-cards";
import { MarketSummaryCards } from "@/components/market/market-summary-cards";
import { SectorTable } from "@/components/market/sector-table";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";

export default function MarketPage() {
  const macro = useMacroLatest();
  const sectors = useSectorsLatest();
  const summary = useMarketSummary();
  const t = useTranslations("market");

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>

      {/* Market Summary section — FIRST after page title (D-08) */}
      <section className="mb-8">
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-sm font-semibold text-muted-foreground">{t("summaryTitle")}</h2>
          {summary.data?.as_of && (
            <span className="text-xs text-muted-foreground">
              {t("asOf", { date: summary.data.as_of })}
            </span>
          )}
        </div>
        {summary.isError ? (
          <ErrorState body={t("summaryError")} />
        ) : (
          <MarketSummaryCards data={summary.data} isLoading={summary.isLoading} />
        )}
      </section>

      {/* Macro indicator cards */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-muted-foreground mb-4">{t("macroTitle")}</h2>
        {macro.isError ? (
          <ErrorState body={t("macroError")} />
        ) : (
          <MacroCards
            indicators={macro.data?.indicators || []}
            isLoading={macro.isLoading}
          />
        )}
      </section>

      {/* Sector performance table */}
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground mb-4">{t("sectorTitle")}</h2>
        {sectors.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : sectors.isError ? (
          <ErrorState body={t("sectorError")} />
        ) : !sectors.data || sectors.data.count === 0 ? (
          <EmptyState body={t("emptyBody")} />
        ) : (
          <SectorTable sectors={sectors.data.sectors} />
        )}
      </section>
    </div>
  );
}
