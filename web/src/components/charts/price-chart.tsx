"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  type IChartApi,
} from "lightweight-charts";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { PricePoint, IndicatorPoint } from "@/lib/types";

interface PriceChartProps {
  prices: PricePoint[];
  indicators?: IndicatorPoint[];
}

export function PriceChart({ prices, indicators }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || !prices.length) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: CHART_COLORS.chartBg },
        textColor: CHART_COLORS.chartText,
      },
      grid: {
        vertLines: { color: CHART_COLORS.chartGrid },
        horzLines: { color: CHART_COLORS.chartGrid },
      },
      width: containerRef.current.clientWidth,
      height: 400,
      crosshair: { mode: 0 },
    });
    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: CHART_COLORS.candleUp,
      downColor: CHART_COLORS.candleDown,
      borderUpColor: CHART_COLORS.candleUp,
      borderDownColor: CHART_COLORS.candleDown,
      wickUpColor: CHART_COLORS.candleUp,
      wickDownColor: CHART_COLORS.candleDown,
    });
    candleSeries.setData(
      prices.map((p) => ({
        time: p.time,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      }))
    );

    // Volume histogram overlay on same chart (bottom 20%)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(
      prices.map((p) => ({
        time: p.time,
        value: p.volume,
        color:
          p.close >= p.open
            ? CHART_COLORS.volumeUp
            : CHART_COLORS.volumeDown,
      }))
    );

    // Indicator overlays (per D-08: SMA/EMA/BB on main chart)
    if (indicators && indicators.length > 0) {
      // SMA 20 — blue
      const sma20Data = indicators
        .filter((ind) => ind.sma_20 != null)
        .map((ind) => ({ time: ind.time, value: ind.sma_20! }));
      if (sma20Data.length > 0) {
        const sma20Series = chart.addSeries(LineSeries, {
          color: CHART_COLORS.sma20,
          lineWidth: 1,
          priceScaleId: "right",
        });
        sma20Series.setData(sma20Data);
      }

      // EMA 12 — purple
      const ema12Data = indicators
        .filter((ind) => ind.ema_12 != null)
        .map((ind) => ({ time: ind.time, value: ind.ema_12! }));
      if (ema12Data.length > 0) {
        const ema12Series = chart.addSeries(LineSeries, {
          color: CHART_COLORS.ema12,
          lineWidth: 1,
          priceScaleId: "right",
        });
        ema12Series.setData(ema12Data);
      }

      // Bollinger Bands upper/lower — gray semi-transparent
      const bbUpperData = indicators
        .filter((ind) => ind.bb_upper != null)
        .map((ind) => ({ time: ind.time, value: ind.bb_upper! }));
      if (bbUpperData.length > 0) {
        const bbUpperSeries = chart.addSeries(LineSeries, {
          color: CHART_COLORS.bbBands,
          lineWidth: 1,
          lineStyle: 2, // dashed
          priceScaleId: "right",
        });
        bbUpperSeries.setData(bbUpperData);
      }

      const bbLowerData = indicators
        .filter((ind) => ind.bb_lower != null)
        .map((ind) => ({ time: ind.time, value: ind.bb_lower! }));
      if (bbLowerData.length > 0) {
        const bbLowerSeries = chart.addSeries(LineSeries, {
          color: CHART_COLORS.bbBands,
          lineWidth: 1,
          lineStyle: 2,
          priceScaleId: "right",
        });
        bbLowerSeries.setData(bbLowerData);
      }
    }

    chart.timeScale().fitContent();

    // ResizeObserver for responsive width
    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [prices, indicators]);

  return <div ref={containerRef} className="w-full" />;
}
