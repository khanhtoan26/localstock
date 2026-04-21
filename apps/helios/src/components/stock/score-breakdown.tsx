"use client";
import { useTranslations } from "next-intl";
import { cn, formatScore } from "@/lib/utils";
import type { StockScore } from "@/lib/types";

const DIMENSION_KEYS = [
  { key: "technical_score" as const, tKey: "technical" as const, color: "bg-blue-500" },
  { key: "fundamental_score" as const, tKey: "fundamental" as const, color: "bg-emerald-500" },
  { key: "sentiment_score" as const, tKey: "sentiment" as const, color: "bg-amber-500" },
  { key: "macro_score" as const, tKey: "macro" as const, color: "bg-violet-500" },
] as const;

interface ScoreBreakdownProps {
  score: StockScore;
}

export function ScoreBreakdown({ score }: ScoreBreakdownProps) {
  const t = useTranslations("stock.score");

  return (
    <div className="space-y-4">
      {DIMENSION_KEYS.map((dim) => {
        const value = score[dim.key];
        const percent = value != null ? Math.min(Math.max(value, 0), 100) : 0;
        return (
          <div key={dim.key}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">{t(dim.tKey)}</span>
              <span className="text-sm font-mono text-muted-foreground">
                {formatScore(value)}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted">
              <div
                className={cn("h-2 rounded-full transition-all", dim.color)}
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
