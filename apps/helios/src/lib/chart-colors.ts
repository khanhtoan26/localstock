/** Chart color sets per theme — UI-SPEC.md contract */

export interface ChartColorSet {
  candleUp: string;
  candleDown: string;
  volumeUp: string;
  volumeDown: string;
  sma20: string;
  ema12: string;
  bbBands: string;
  macdLine: string;
  macdSignal: string;
  macdHistPositive: string;
  macdHistNegative: string;
  rsiLine: string;
  rsiOverbought: string;
  rsiOversold: string;
  chartBg: string;
  chartGrid: string;
  chartText: string;
}

const LIGHT_COLORS: ChartColorSet = {
  candleUp: "#15803d",       // green-700 for cream bg
  candleDown: "#b91c1c",     // red-700 for cream bg
  volumeUp: "#15803d60",     // 37.5% alpha on cream (higher than dark for visibility)
  volumeDown: "#b91c1c60",   // 37.5% alpha on cream
  sma20: "#2563eb",          // blue-600
  ema12: "#7c3aed",          // violet-600
  bbBands: "#6b728080",
  macdLine: "#2563eb",
  macdSignal: "#ea580c",     // orange-600
  macdHistPositive: "#15803d",
  macdHistNegative: "#b91c1c",
  rsiLine: "#7c3aed",
  rsiOverbought: "#b91c1c",
  rsiOversold: "#15803d",
  chartBg: "#faf9f5",        // Claude bg-100 (matches --background)
  chartGrid: "#e8e6dc",      // Claude bg-400 (matches --border)
  chartText: "#73726c",      // Claude text-400 (matches --muted-foreground)
};

const DARK_COLORS: ChartColorSet = {
  candleUp: "#22c55e",
  candleDown: "#ef4444",
  volumeUp: "#22c55e40",     // 25% alpha on dark
  volumeDown: "#ef444440",
  sma20: "#3b82f6",
  ema12: "#a855f7",
  bbBands: "#6b728080",
  macdLine: "#3b82f6",
  macdSignal: "#f97316",
  macdHistPositive: "#22c55e",
  macdHistNegative: "#ef4444",
  rsiLine: "#a855f7",
  rsiOverbought: "#ef4444",
  rsiOversold: "#22c55e",
  chartBg: "#262624",        // Claude bg-100 dark (warm dark gray)
  chartGrid: "#1f1e1d",      // Claude bg-200 dark
  chartText: "#c2c0b6",      // Claude text-200 dark
};

/** Get chart colors for the given theme */
export function getChartColors(theme: "light" | "dark"): ChartColorSet {
  return theme === "dark" ? DARK_COLORS : LIGHT_COLORS;
}

/** @deprecated Use getChartColors(theme) via useChartTheme() hook instead */
export const CHART_COLORS = DARK_COLORS;
