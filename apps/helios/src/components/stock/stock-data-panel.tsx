"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { ChevronDown } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TimeframeSelector } from "@/components/charts/timeframe-selector";
import { ScoreBreakdown } from "@/components/stock/score-breakdown";
import { useStockPrices, useStockIndicators } from "@/lib/queries";
import type { StockScore } from "@/lib/types";

const PriceChart = dynamic(
  () =>
    import("@/components/charts/price-chart").then((m) => ({
      default: m.PriceChart,
    })),
  { ssr: false, loading: () => <Skeleton className="h-[300px] w-full" /> }
);
const SubPanel = dynamic(
  () =>
    import("@/components/charts/sub-panel").then((m) => ({
      default: m.SubPanel,
    })),
  { ssr: false, loading: () => <Skeleton className="h-[120px] w-full" /> }
);

const TAB_KEY = "stock-data-tab";
const VALID_TABS = ["chart", "indicators", "score"] as const;
type TabValue = (typeof VALID_TABS)[number];

interface StockDataPanelProps {
  symbol: string;
  score: StockScore | undefined;
}

export function StockDataPanel({ symbol, score }: StockDataPanelProps) {
  const [days, setDays] = useState(365);
  const [activeTab, setActiveTab] = useState<TabValue>("chart");

  const priceQuery = useStockPrices(symbol, days);
  const indicatorQuery = useStockIndicators(symbol, days);

  // Read tab preference from localStorage on mount (SSR-safe)
  useEffect(() => {
    const stored = localStorage.getItem(TAB_KEY);
    if (stored && VALID_TABS.includes(stored as TabValue)) {
      setActiveTab(stored as TabValue);
    }
  }, []);

  function handleTabChange(value: unknown) {
    const tab = value as TabValue;
    setActiveTab(tab);
    localStorage.setItem(TAB_KEY, tab);
  }

  // Shared content renderers
  const chartContent = (
    <>
      <TimeframeSelector selectedDays={days} onChange={setDays} />
      {priceQuery.isLoading ? (
        <Skeleton className="h-[300px] w-full" />
      ) : priceQuery.isError ? (
        <ErrorState body="Không thể tải dữ liệu giá." />
      ) : !priceQuery.data || priceQuery.data.count === 0 ? (
        <EmptyState body="Chưa có dữ liệu giá." />
      ) : (
        <PriceChart
          prices={priceQuery.data.prices}
          indicators={indicatorQuery.data?.indicators}
        />
      )}
    </>
  );

  const indicatorsContent =
    indicatorQuery.isLoading ? (
      <Skeleton className="h-[240px] w-full" />
    ) : indicatorQuery.data && indicatorQuery.data.indicators.length > 0 ? (
      <div className="space-y-0">
        <SubPanel
          type="macd"
          indicators={indicatorQuery.data.indicators}
          height={120}
        />
        <SubPanel
          type="rsi"
          indicators={indicatorQuery.data.indicators}
          height={120}
        />
      </div>
    ) : (
      <EmptyState body="Chưa có dữ liệu chỉ số kỹ thuật." />
    );

  const scoreContent = score ? (
    <ScoreBreakdown score={score} />
  ) : (
    <EmptyState body="Chưa có dữ liệu điểm." />
  );

  return (
    <>
      {/* Desktop: Tabs (per D-20) */}
      <div className="hidden md:block">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList>
            <TabsTrigger value="chart" className="text-sm">
              Biểu đồ
            </TabsTrigger>
            <TabsTrigger value="indicators" className="text-sm">
              Chỉ số
            </TabsTrigger>
            <TabsTrigger value="score" className="text-sm">
              Điểm số
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chart">{chartContent}</TabsContent>
          <TabsContent value="indicators">{indicatorsContent}</TabsContent>
          <TabsContent value="score">{scoreContent}</TabsContent>
        </Tabs>
      </div>

      {/* Mobile: Accordion (per D-26) */}
      <div className="block md:hidden space-y-2">
        <Collapsible defaultOpen>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border border-border px-4 py-3 text-sm font-medium hover:bg-muted">
            Biểu đồ
            <ChevronDown className="h-4 w-4 transition-transform [[data-state=open]_&]:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent className="px-1 pt-2">
            {chartContent}
          </CollapsibleContent>
        </Collapsible>

        <Collapsible>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border border-border px-4 py-3 text-sm font-medium hover:bg-muted">
            Chỉ số kỹ thuật
            <ChevronDown className="h-4 w-4 transition-transform [[data-state=open]_&]:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent className="px-1 pt-2">
            {indicatorsContent}
          </CollapsibleContent>
        </Collapsible>

        <Collapsible>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border border-border px-4 py-3 text-sm font-medium hover:bg-muted">
            Điểm số
            <ChevronDown className="h-4 w-4 transition-transform [[data-state=open]_&]:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent className="px-1 pt-2">
            {scoreContent}
          </CollapsibleContent>
        </Collapsible>
      </div>
    </>
  );
}
