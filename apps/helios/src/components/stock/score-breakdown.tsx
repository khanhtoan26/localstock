import { cn, formatScore } from "@/lib/utils";
import type { StockScore } from "@/lib/types";

const DIMENSIONS = [
  { key: "technical_score" as const, label: "Kỹ Thuật", color: "bg-blue-500" },
  { key: "fundamental_score" as const, label: "Cơ Bản", color: "bg-emerald-500" },
  { key: "sentiment_score" as const, label: "Tin Tức", color: "bg-amber-500" },
  { key: "macro_score" as const, label: "Vĩ Mô", color: "bg-violet-500" },
] as const;

interface ScoreBreakdownProps {
  score: StockScore;
}

export function ScoreBreakdown({ score }: ScoreBreakdownProps) {
  return (
    <div className="space-y-4">
      {DIMENSIONS.map((dim) => {
        const value = score[dim.key];
        const percent = value != null ? Math.min(Math.max(value, 0), 100) : 0;
        return (
          <div key={dim.key}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">{dim.label}</span>
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
