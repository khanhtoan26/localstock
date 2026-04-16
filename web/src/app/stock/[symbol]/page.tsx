"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { GradeBadge } from "@/components/rankings/grade-badge";
import { TimeframeSelector } from "@/components/charts/timeframe-selector";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { formatScore } from "@/lib/utils";
import {
  useStockPrices,
  useStockIndicators,
  useStockScore,
  useStockReport,
} from "@/lib/queries";

// Dynamic imports with ssr: false — lightweight-charts crashes in SSR (Pitfall 1)
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
  { ssr: false, loading: () => <Skeleton className="h-[152px] w-full" /> }
);

export default function StockDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() || "";
  const [days, setDays] = useState(365); // Default 1N (1 year) per D-09

  const priceQuery = useStockPrices(symbol, days);
  const indicatorQuery = useStockIndicators(symbol, days);
  const scoreQuery = useStockScore(symbol);
  const reportQuery = useStockReport(symbol);

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex items-center gap-4">
        <Link
          href="/rankings"
          className="text-muted-foreground hover:text-foreground text-sm flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-[28px] font-semibold">{symbol}</h1>
          {scoreQuery.data && (
            <>
              <GradeBadge grade={scoreQuery.data.grade} />
              <span className="font-mono text-lg text-muted-foreground">
                {formatScore(scoreQuery.data.total_score)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Price chart section */}
      <section>
        {priceQuery.isLoading ? (
          <Skeleton className="h-[400px] w-full" />
        ) : priceQuery.isError ? (
          <ErrorState body={`Không thể tải dữ liệu giá cho ${symbol}.`} />
        ) : !priceQuery.data || priceQuery.data.count === 0 ? (
          <EmptyState
            body={`Chưa có dữ liệu cho mã ${symbol}. Kiểm tra mã cổ phiếu hoặc chạy pipeline.`}
          />
        ) : (
          <PriceChart
            prices={priceQuery.data.prices}
            indicators={indicatorQuery.data?.indicators}
          />
        )}
      </section>

      {/* Timeframe selector */}
      <TimeframeSelector selectedDays={days} onChange={setDays} />

      {/* Sub-panels: MACD + RSI (per D-08) */}
      {indicatorQuery.data &&
        indicatorQuery.data.indicators.length > 0 && (
          <section className="space-y-0">
            <SubPanel
              type="macd"
              indicators={indicatorQuery.data.indicators}
            />
            <SubPanel
              type="rsi"
              indicators={indicatorQuery.data.indicators}
            />
          </section>
        )}

      {/* AI Report card */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="text-base">Báo Cáo AI</CardTitle>
        </CardHeader>
        <CardContent>
          {reportQuery.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ) : reportQuery.isError || !reportQuery.data ? (
            <p className="text-sm text-muted-foreground">
              Chưa có báo cáo — chạy pipeline để tạo báo cáo AI.
            </p>
          ) : (
            <ScrollArea className="max-h-[400px]">
              <div className="text-sm leading-relaxed whitespace-pre-wrap">
                {reportQuery.data.summary ||
                  JSON.stringify(reportQuery.data.content_json, null, 2)}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Score breakdown card */}
      {scoreQuery.data && (
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="text-base">Phân Tích Điểm</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              {[
                {
                  label: "Kỹ Thuật",
                  value: scoreQuery.data.technical_score,
                },
                {
                  label: "Cơ Bản",
                  value: scoreQuery.data.fundamental_score,
                },
                {
                  label: "Tin Tức",
                  value: scoreQuery.data.sentiment_score,
                },
                {
                  label: "Vĩ Mô",
                  value: scoreQuery.data.macro_score,
                },
              ].map((dim) => (
                <div key={dim.label}>
                  <p className="text-xs text-muted-foreground">{dim.label}</p>
                  <p className="text-xl font-semibold font-mono mt-1">
                    {formatScore(dim.value)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
