import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MacroIndicator } from "@/lib/types";

/** Map indicator_type to Vietnamese label */
const MACRO_LABELS: Record<string, string> = {
  interest_rate: "Lãi Suất SBV",
  exchange_rate_usd_vnd: "Tỷ Giá USD/VND",
  cpi: "CPI",
  gdp: "GDP",
};

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
  // Order: interest_rate, exchange_rate, cpi, gdp
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

  // Build lookup from indicators array
  const lookup = new Map(indicators.map((ind) => [ind.indicator_type, ind]));

  return (
    <div className="grid grid-cols-2 gap-4">
      {orderedTypes.map((type) => {
        const ind = lookup.get(type);
        return (
          <Card key={type} className="border border-border">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">
                {MACRO_LABELS[type] || type}
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
