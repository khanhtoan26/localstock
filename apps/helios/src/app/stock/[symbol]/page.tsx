"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowLeft, TrendingUp, TrendingDown } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { GradeBadge } from "@/components/rankings/grade-badge";
import { TimeframeSelector } from "@/components/charts/timeframe-selector";
import { ScoreBreakdown } from "@/components/stock/score-breakdown";
import { AIReportPanel } from "@/components/stock/ai-report-panel";
import { formatScore, formatVND, formatVolume } from "@/lib/utils";
import {
  useStockScore,
  useStockReport,
  useStockPrices,
  useStockIndicators,
} from "@/lib/queries";

const PriceChart = dynamic(
  () =>
    import("@/components/charts/price-chart").then((m) => ({
      default: m.PriceChart,
    })),
  { ssr: false, loading: () => <Skeleton className="h-[400px] w-full" /> }
);
const SubPanel = dynamic(
  () =>
    import("@/components/charts/sub-panel").then((m) => ({
      default: m.SubPanel,
    })),
  { ssr: false, loading: () => <Skeleton className="h-[140px] w-full" /> }
);

export default function StockDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() || "";
  const [days, setDays] = useState(365);
  const t = useTranslations("stock");
  const td = useTranslations("stock.dimensions");

  const scoreQuery = useStockScore(symbol);
  const reportQuery = useStockReport(symbol);
  const priceQuery = useStockPrices(symbol, days);
  const indicatorQuery = useStockIndicators(symbol, days);

  // Derive latest price info from price data
  const prices = priceQuery.data?.prices;
  const latest = prices?.length ? prices[prices.length - 1] : null;
  const prev = prices && prices.length > 1 ? prices[prices.length - 2] : null;
  const priceChange = latest && prev ? latest.close - prev.close : null;
  const priceChangePct =
    priceChange != null && prev ? (priceChange / prev.close) * 100 : null;
  const isUp = priceChange != null && priceChange >= 0;

  return (
    <div className="space-y-6">
      {/* ─── Header ─── */}
      <div className="space-y-3">
        <Link
          href="/rankings"
          className="text-muted-foreground hover:text-foreground text-sm flex items-center gap-1 w-fit"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("back")}
        </Link>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          {/* Symbol + grade + total score */}
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-bold tracking-tight">{symbol}</h1>
            {scoreQuery.data && (
              <>
                <GradeBadge grade={scoreQuery.data.grade} />
                <span className="font-mono text-lg font-semibold text-muted-foreground">
                  {formatScore(scoreQuery.data.total_score)}
                </span>
              </>
            )}
          </div>

          {/* Price info */}
          {latest && (
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold font-mono">
                {formatVND(latest.close)}
              </span>
              {priceChange != null && (
                <span
                  className={`flex items-center gap-1 text-sm font-medium ${
                    isUp
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {isUp ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  {isUp ? "+" : ""}
                  {formatVND(priceChange)} ({priceChangePct!.toFixed(2)}%)
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {t("volume")}: {formatVolume(latest.volume)}
              </span>
            </div>
          )}
        </div>

        {/* Compact dimension scores */}
        {scoreQuery.data && (
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span>
              {td("technical")}:{" "}
              <strong className="text-foreground">
                {formatScore(scoreQuery.data.technical_score)}
              </strong>
            </span>
            <span>
              {td("fundamental")}:{" "}
              <strong className="text-foreground">
                {formatScore(scoreQuery.data.fundamental_score)}
              </strong>
            </span>
            <span>
              {td("sentiment")}:{" "}
              <strong className="text-foreground">
                {formatScore(scoreQuery.data.sentiment_score)}
              </strong>
            </span>
            <span>
              {td("macro")}:{" "}
              <strong className="text-foreground">
                {formatScore(scoreQuery.data.macro_score)}
              </strong>
            </span>
          </div>
        )}
      </div>

      {/* ─── Chart Section (full width) ─── */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>{t("priceChart")}</CardTitle>
          <TimeframeSelector selectedDays={days} onChange={setDays} />
        </CardHeader>
        <CardContent>
          {priceQuery.isLoading ? (
            <Skeleton className="h-[400px] w-full" />
          ) : priceQuery.isError ? (
            <ErrorState body={t("data.priceError")} />
          ) : !prices || prices.length === 0 ? (
            <EmptyState body={t("data.noPrice")} />
          ) : (
            <PriceChart
              prices={prices}
              indicators={indicatorQuery.data?.indicators}
            />
          )}
        </CardContent>
      </Card>

      {/* ─── Technical Indicators (MACD + RSI side by side) ─── */}
      {indicatorQuery.data && indicatorQuery.data.indicators.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardContent className="pt-2 pb-2 px-0">
              <SubPanel
                type="macd"
                indicators={indicatorQuery.data.indicators}
                height={160}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-2 pb-2 px-0">
              <SubPanel
                type="rsi"
                indicators={indicatorQuery.data.indicators}
                height={160}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* ─── Score + AI Report (two columns on desktop) ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        {/* Score breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>{t("scoreAnalysis")}</CardTitle>
          </CardHeader>
          <CardContent>
            {scoreQuery.isLoading ? (
              <Skeleton className="h-[180px] w-full" />
            ) : scoreQuery.data ? (
              <ScoreBreakdown score={scoreQuery.data} />
            ) : (
              <EmptyState body={t("data.noScore")} />
            )}
          </CardContent>
        </Card>

        {/* AI Report */}
        <Card>
          <CardHeader>
            <CardTitle>{t("aiReport")}</CardTitle>
          </CardHeader>
          <CardContent>
            <AIReportPanel
              report={reportQuery.data}
              isLoading={reportQuery.isLoading}
              isError={reportQuery.isError}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
