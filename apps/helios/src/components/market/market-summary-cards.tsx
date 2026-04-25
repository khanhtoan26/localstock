"use client";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MarketSummaryResponse } from "@/lib/types";

interface MarketSummaryCardsProps {
  data: MarketSummaryResponse | undefined;
  isLoading?: boolean;
}

const CARD_KEYS = ["vnindex", "totalVolume", "advances", "breadth"] as const;

export function MarketSummaryCards({ data, isLoading }: MarketSummaryCardsProps) {
  const t = useTranslations("market");

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {CARD_KEYS.map((key) => (
          <Card key={key} className="border border-border">
            <CardContent className="p-4">
              <Skeleton className="h-3 w-20 mb-2" />
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-3 w-16 mt-1" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const vnindexValue = data?.vnindex?.value;
  const vnindexChange = data?.vnindex?.change_pct;
  const totalVolume = data?.total_volume;
  const volumeChange = data?.total_volume_change_pct;
  const advances = data?.advances ?? 0;
  const declines = data?.declines ?? 0;
  const breadth = data?.breadth;
  const total = advances + declines;

  function formatChange(pct: number | null | undefined): string {
    if (pct == null) return "—";
    const sign = pct >= 0 ? "+" : "";
    return `${sign}${pct.toFixed(2)}%`;
  }

  function formatVolume(vol: number | null | undefined): string {
    if (vol == null) return "—";
    if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toFixed(1)}B`;
    if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
    return new Intl.NumberFormat("vi-VN").format(vol);
  }

  function ChangeRow({ pct }: { pct: number | null | undefined }) {
    if (pct == null) return <p className="text-xs text-muted-foreground mt-1">—</p>;
    const positive = pct >= 0;
    return (
      <p className={`text-xs mt-1 ${positive ? "text-green-600 dark:text-green-500" : "text-red-500 dark:text-red-400"}`}>
        {positive ? "↑" : "↓"} {formatChange(pct)}
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Card 1: VN-Index (D-06) */}
      <Card className="border border-border">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{t("summaryLabels.vnindex")}</p>
          <p className="text-xl font-semibold font-mono text-foreground mt-1">
            {vnindexValue != null
              ? new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(vnindexValue)
              : "—"}
          </p>
          <ChangeRow pct={vnindexChange} />
        </CardContent>
      </Card>

      {/* Card 2: Total Volume (D-06) */}
      <Card className="border border-border">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{t("summaryLabels.totalVolume")}</p>
          <p className="text-xl font-semibold font-mono text-foreground mt-1">
            {formatVolume(totalVolume)}
          </p>
          <ChangeRow pct={volumeChange} />
        </CardContent>
      </Card>

      {/* Card 3: Advances (D-06) */}
      <Card className="border border-border">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{t("summaryLabels.advances")}</p>
          <p className="text-xl font-semibold font-mono text-foreground mt-1">
            {total > 0
              ? `${advances} / ${declines}`
              : "—"}
          </p>
          {total > 0 ? (
            <p className="text-xs text-muted-foreground mt-1">
              {advances} up · {declines} down
            </p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">—</p>
          )}
        </CardContent>
      </Card>

      {/* Card 4: Market Breadth (D-06) */}
      <Card className="border border-border">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{t("summaryLabels.breadth")}</p>
          <p className="text-xl font-semibold font-mono text-foreground mt-1">
            {breadth != null ? `${breadth.toFixed(1)}%` : "—"}
          </p>
          {breadth != null ? (
            <p className={`text-xs mt-1 ${breadth >= 50 ? "text-green-600 dark:text-green-500" : "text-red-500 dark:text-red-400"}`}>
              {breadth >= 50 ? "↑" : "↓"} {breadth >= 50 ? "Bullish" : "Bearish"}
            </p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">—</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
