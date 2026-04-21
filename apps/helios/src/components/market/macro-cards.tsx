"use client";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MacroIndicator } from "@/lib/types";

/** Format indicator value based on type */
function formatMacroValue(type: string, value: number): string {
  if (type === "exchange_rate_usd_vnd") {
    return new Intl.NumberFormat("vi-VN").format(Math.round(value));
  }
  return `${value.toFixed(1)}%`;
}

interface MacroCardsProps {
  indicators: MacroIndicator[];
  isLoading?: boolean;
}

export function MacroCards({ indicators, isLoading }: MacroCardsProps) {
  const t = useTranslations("market.macroLabels");
  const orderedTypes = ["interest_rate", "exchange_rate_usd_vnd", "cpi", "gdp"];

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {orderedTypes.map((type) => (
          <Card key={type} className="border border-border">
            <CardContent className="p-4">
              <Skeleton className="h-3 w-20 mb-2" />
              <Skeleton className="h-6 w-24" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const lookup = new Map(indicators.map((ind) => [ind.indicator_type, ind]));

  return (
    <div className="grid grid-cols-2 gap-4">
      {orderedTypes.map((type) => {
        const ind = lookup.get(type);
        return (
          <Card key={type} className="border border-border">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">
                {t(type as "interest_rate" | "exchange_rate_usd_vnd" | "cpi" | "gdp")}
              </p>
              <p className="text-xl font-semibold font-mono text-foreground mt-1">
                {ind ? formatMacroValue(type, ind.value) : "—"}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
