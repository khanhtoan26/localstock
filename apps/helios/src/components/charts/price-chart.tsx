"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import type { PricePoint, IndicatorPoint } from "@/lib/types";

interface PriceChartProps {
  prices: PricePoint[];
  indicators?: IndicatorPoint[];
}

export function PriceChart({ prices, indicators }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const chartColors = useChartTheme();

  // Effect 1: Create chart (NO chartColors in deps — only runs on data change)
  useEffect(() => {
    if (!containerRef.current || !prices.length) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: chartColors.chartBg },
        textColor: chartColors.chartText,
      },
      grid: {
        vertLines: { color: chartColors.chartGrid },
        horzLines: { color: chartColors.chartGrid },
      },
      width: containerRef.current.clientWidth,
      height: 400,
      crosshair: { mode: 0 },
    });
    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.candleUp,
      downColor: chartColors.candleDown,
      borderUpColor: chartColors.candleUp,
      borderDownColor: chartColors.candleDown,
      wickUpColor: chartColors.candleUp,
      wickDownColor: chartColors.candleDown,
    });
    candleRef.current = candleSeries;
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
    volumeRef.current = volumeSeries;
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(
      prices.map((p) => ({
        time: p.time,
        value: p.volume,
        color:
          p.close >= p.open
            ? chartColors.volumeUp
            : chartColors.volumeDown,
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
          color: chartColors.sma20,
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
          color: chartColors.ema12,
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
          color: chartColors.bbBands,
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
          color: chartColors.bbBands,
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
      candleRef.current = null;
      volumeRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prices, indicators]); // NO chartColors — preserves zoom/scroll on theme toggle

  // Effect 2: Re-theme on toggle (only runs when chartColors changes, preserves zoom/scroll)
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    chart.applyOptions({
      layout: {
        background: { color: chartColors.chartBg },
        textColor: chartColors.chartText,
      },
      grid: {
        vertLines: { color: chartColors.chartGrid },
        horzLines: { color: chartColors.chartGrid },
      },
    });

    if (candleRef.current) {
      candleRef.current.applyOptions({
        upColor: chartColors.candleUp,
        downColor: chartColors.candleDown,
        borderUpColor: chartColors.candleUp,
        borderDownColor: chartColors.candleDown,
        wickUpColor: chartColors.candleUp,
        wickDownColor: chartColors.candleDown,
      });
    }

    // Volume histogram: setData needed to update per-bar colors (lightweight-charts constraint)
    if (volumeRef.current && prices.length) {
      volumeRef.current.setData(
        prices.map((p) => ({
          time: p.time,
          value: p.volume,
          color:
            p.close >= p.open ? chartColors.volumeUp : chartColors.volumeDown,
        }))
      );
    }
  }, [chartColors, prices]);

  return <div ref={containerRef} className="w-full" />;
}
