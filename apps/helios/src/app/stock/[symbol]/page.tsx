"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { GradeBadge } from "@/components/rankings/grade-badge";
import { formatScore } from "@/lib/utils";
import { useStockScore, useStockReport } from "@/lib/queries";
import { AIReportPanel } from "@/components/stock/ai-report-panel";
import { StockDataPanel } from "@/components/stock/stock-data-panel";

export default function StockDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() || "";

  const scoreQuery = useStockScore(symbol);
  const reportQuery = useStockReport(symbol);

  return (
    <div className="space-y-6">
      {/* Header bar — per D-15: score overview in header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <Link
          href="/rankings"
          className="text-muted-foreground hover:text-foreground text-sm flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại
        </Link>
        <div className="flex items-center gap-3 flex-wrap">
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
        {/* Compact 4-dimension score overview — per D-15 */}
        {scoreQuery.data && (
          <div className="flex gap-3 text-xs text-muted-foreground ml-0 sm:ml-auto">
            <span>KT: <strong className="text-foreground">{formatScore(scoreQuery.data.technical_score)}</strong></span>
            <span>CB: <strong className="text-foreground">{formatScore(scoreQuery.data.fundamental_score)}</strong></span>
            <span>TT: <strong className="text-foreground">{formatScore(scoreQuery.data.sentiment_score)}</strong></span>
            <span>VM: <strong className="text-foreground">{formatScore(scoreQuery.data.macro_score)}</strong></span>
          </div>
        )}
      </div>

      {/* Main content — side-by-side layout per D-13, D-14, D-16, D-25 */}
      <div className="flex flex-col md:flex-row gap-6">
        {/* LEFT: AI Report — primary content per D-13 (60-70% width) */}
        <div className="w-full md:w-[65%]">
          <AIReportPanel
            report={reportQuery.data}
            isLoading={reportQuery.isLoading}
            isError={reportQuery.isError}
          />
        </div>

        {/* RIGHT: Chart/Data panel — per D-13, D-14 (30-40% width, sticky) */}
        <div className="w-full md:w-[35%] md:sticky md:top-6 md:self-start">
          <StockDataPanel symbol={symbol} score={scoreQuery.data} />
        </div>
      </div>
    </div>
  );
}
