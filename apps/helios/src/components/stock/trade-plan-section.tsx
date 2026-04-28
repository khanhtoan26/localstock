"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipTrigger,
  TooltipPortal,
  TooltipPositioner,
  TooltipContent,
} from "@/components/ui/tooltip";
import { formatVND } from "@/lib/utils";
import type { StockReport, TradePlanData } from "@/lib/types";

// --- Exported helpers (also used by tests) ---

export function extractTradePlan(
  contentJson: Record<string, unknown> | null,
): TradePlanData | null {
  if (!contentJson) return null;

  const entry =
    typeof contentJson.entry_price === "number"
      ? contentJson.entry_price
      : null;
  const sl =
    typeof contentJson.stop_loss === "number" ? contentJson.stop_loss : null;
  const tp =
    typeof contentJson.target_price === "number"
      ? contentJson.target_price
      : null;

  if (entry === null && sl === null && tp === null) return null;

  return {
    entry_price: entry,
    stop_loss: sl,
    target_price: tp,
    risk_rating: ["high", "medium", "low"].includes(
      contentJson.risk_rating as string,
    )
      ? (contentJson.risk_rating as "high" | "medium" | "low")
      : null,
    signal_conflicts:
      typeof contentJson.signal_conflicts === "string"
        ? contentJson.signal_conflicts
        : null,
    catalyst:
      typeof contentJson.catalyst === "string" ? contentJson.catalyst : null,
  };
}

const riskColors: Record<string, string> = {
  high: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
  medium:
    "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
  low: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
};

export function getRiskColors(rating: string): string {
  return riskColors[rating] ?? "";
}

// --- Sub-components ---

const riskLabelKeys: Record<string, string> = {
  high: "riskHigh",
  medium: "riskMedium",
  low: "riskLow",
};

function RiskBadge({
  rating,
  tooltipText,
}: {
  rating: string;
  tooltipText: string | null;
}) {
  const t = useTranslations("stock.tradePlan");
  const colors = getRiskColors(rating);
  const labelKey = riskLabelKeys[rating];
  if (!colors || !labelKey) return null;

  const badge = (
    <span
      className={`px-2 py-0.5 rounded text-xs font-bold border ${colors}`}
    >
      {t(labelKey)}
    </span>
  );

  if (!tooltipText) return badge;

  return (
    <Tooltip>
      <TooltipTrigger className="cursor-default">{badge}</TooltipTrigger>
      <TooltipPortal>
        <TooltipPositioner sideOffset={5}>
          <TooltipContent className="max-w-xs">{tooltipText}</TooltipContent>
        </TooltipPositioner>
      </TooltipPortal>
    </Tooltip>
  );
}

function PriceLevelRow({
  label,
  price,
  currentClose,
}: {
  label: string;
  price: number | null;
  currentClose: number | null;
}) {
  if (price === null) return null;

  let pctText: string | null = null;
  let isPositive = false;
  if (currentClose && currentClose > 0) {
    const pct = ((price - currentClose) / currentClose) * 100;
    isPositive = pct >= 0;
    pctText = `(${isPositive ? "+" : ""}${pct.toFixed(1)}%)`;
  }

  return (
    <div className="flex items-baseline justify-between py-1.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-semibold font-mono">
          {formatVND(price)}
        </span>
        {pctText && (
          <span
            className={`text-xs ${
              isPositive
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {pctText}
          </span>
        )}
      </div>
    </div>
  );
}

function SignalConflictAlert({ text }: { text: string }) {
  const t = useTranslations("stock.tradePlan");
  return (
    <div className="flex gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 mt-3">
      <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0" />
      <div>
        <p className="text-xs font-semibold text-yellow-700 dark:text-yellow-300">
          {t("signalConflict")}
        </p>
        <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
          {text}
        </p>
      </div>
    </div>
  );
}

// --- Main component ---

interface TradePlanSectionProps {
  report: StockReport | undefined;
  isLoading: boolean;
  currentClose: number | null;
}

export function TradePlanSection({
  report,
  isLoading,
  currentClose,
}: TradePlanSectionProps) {
  const t = useTranslations("stock.tradePlan");

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const tradePlan = extractTradePlan(report?.content_json ?? null);
  if (!tradePlan) return null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>{t("title")}</CardTitle>
          {tradePlan.risk_rating && (
            <RiskBadge
              rating={tradePlan.risk_rating}
              tooltipText={report?.summary ?? null}
            />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border">
          <PriceLevelRow
            label={t("entryZone")}
            price={tradePlan.entry_price}
            currentClose={currentClose}
          />
          <PriceLevelRow
            label={t("stopLoss")}
            price={tradePlan.stop_loss}
            currentClose={currentClose}
          />
          <PriceLevelRow
            label={t("targetPrice")}
            price={tradePlan.target_price}
            currentClose={currentClose}
          />
        </div>

        {tradePlan.catalyst && (
          <p className="text-xs text-muted-foreground mt-3">
            <span className="font-semibold">{t("catalyst")}:</span>{" "}
            {tradePlan.catalyst}
          </p>
        )}

        {tradePlan.signal_conflicts && (
          <SignalConflictAlert text={tradePlan.signal_conflicts} />
        )}
      </CardContent>
    </Card>
  );
}
