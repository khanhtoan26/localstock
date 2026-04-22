import { cn } from "@/lib/utils";

const recommendationStyles: Record<string, string> = {
  "strong_buy": "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700",
  "buy":        "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700",
  "hold":       "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700",
  "sell":       "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-700",
  "strong_sell":"bg-red-100 text-red-800 border-red-300 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700",
};

const recommendationLabels: Record<string, string> = {
  "strong_buy":  "Mua mạnh",
  "buy":         "Mua",
  "hold":        "Nắm giữ",
  "sell":        "Bán",
  "strong_sell": "Bán mạnh",
};

function normalizeKey(raw: string): string {
  const lower = raw.toLowerCase().trim();
  if (lower.includes("mua mạnh") || lower === "strong_buy" || lower === "strong buy") return "strong_buy";
  if (lower.includes("bán mạnh") || lower === "strong_sell" || lower === "strong sell") return "strong_sell";
  if (lower.includes("mua") || lower === "buy") return "buy";
  if (lower.includes("bán") || lower === "sell") return "sell";
  return "hold";
}

export function RecommendationBadge({ recommendation }: { recommendation: string }) {
  const key = normalizeKey(recommendation);
  const style = recommendationStyles[key] || recommendationStyles.hold;
  const label = recommendationLabels[key] || recommendation;

  return (
    <span className={cn("inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border", style)}>
      {label}
    </span>
  );
}
