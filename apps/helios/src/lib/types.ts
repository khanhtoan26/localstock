/* API response types — derived from FastAPI endpoint return shapes */

export interface StockScore {
  symbol: string;
  date: string;
  total_score: number;
  grade: string;
  rank: number;
  technical_score: number | null;
  fundamental_score: number | null;
  sentiment_score: number | null;
  macro_score: number | null;
  dimensions_used: number;
  weights: Record<string, number> | null;
}

export interface TopScoresResponse {
  stocks: StockScore[];
  count: number;
  message?: string;
}

export interface PricePoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceHistoryResponse {
  symbol: string;
  count: number;
  prices: PricePoint[];
}

export interface IndicatorPoint {
  time: string;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_12: number | null;
  ema_26: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
}

export interface IndicatorHistoryResponse {
  symbol: string;
  count: number;
  indicators: IndicatorPoint[];
}

export interface MacroIndicator {
  indicator_type: string;
  value: number;
  period: string;
  source: string;
  trend: string | null;
  recorded_at: string;
}

export interface MacroLatestResponse {
  indicators: MacroIndicator[];
  count: number;
}

export interface SectorPerformance {
  group_code: string;
  group_name_vi: string;
  avg_score: number;
  stock_count: number;
  avg_score_change: number | null;
}

export interface SectorsLatestResponse {
  date: string | null;
  count: number;
  sectors: SectorPerformance[];
}

export interface StockReport {
  symbol: string;
  report_type: string;
  content_json: Record<string, unknown> | null;
  summary: string | null;
  generated_at: string;
}

export interface TopReportsResponse {
  reports: StockReport[];
  count: number;
  message?: string;
}

export interface TechnicalData {
  symbol: string;
  date: string;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_12: number | null;
  ema_26: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  trend_direction: string | null;
  trend_strength: number | null;
}

export interface FundamentalData {
  symbol: string;
  year: number;
  period: string;
  pe_ratio: number | null;
  pb_ratio: number | null;
  eps: number | null;
  roe: number | null;
  roa: number | null;
  de_ratio: number | null;
  revenue_qoq: number | null;
  revenue_yoy: number | null;
  profit_qoq: number | null;
  profit_yoy: number | null;
  market_cap: number | null;
  current_price: number | null;
}
