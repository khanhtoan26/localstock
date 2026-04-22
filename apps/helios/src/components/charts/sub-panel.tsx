"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import type { IndicatorPoint } from "@/lib/types";

interface SubPanelProps {
  type: "macd" | "rsi";
  indicators: IndicatorPoint[];
  height?: number;
}

export function SubPanel({ type, indicators, height = 152 }: SubPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRefs = useRef<{
    hist: ISeriesApi<"Histogram"> | null;
    line1: ISeriesApi<"Line"> | null;
    line2: ISeriesApi<"Line"> | null;
  }>({ hist: null, line1: null, line2: null });

  const chartColors = useChartTheme();

  // Effect 1: Create chart (NO chartColors in deps — only runs on data/type/height change)
  useEffect(() => {
    if (!containerRef.current || !indicators.length) return;

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
      height,
    });
    chartRef.current = chart;

    if (type === "macd") {
      // MACD histogram
      const histData = indicators
        .filter((d) => d.macd_histogram != null)
        .map((d) => ({
          time: d.time,
          value: d.macd_histogram!,
          color:
            d.macd_histogram! >= 0
              ? chartColors.macdHistPositive
              : chartColors.macdHistNegative,
        }));
      if (histData.length > 0) {
        const histSeries = chart.addSeries(HistogramSeries);
        seriesRefs.current.hist = histSeries;
        histSeries.setData(histData);
      }

      // MACD line — blue
      const macdData = indicators
        .filter((d) => d.macd != null)
        .map((d) => ({ time: d.time, value: d.macd! }));
      if (macdData.length > 0) {
        const macdLine = chart.addSeries(LineSeries, {
          color: chartColors.macdLine,
          lineWidth: 1,
        });
        seriesRefs.current.line1 = macdLine;
        macdLine.setData(macdData);
      }

      // Signal line — orange
      const signalData = indicators
        .filter((d) => d.macd_signal != null)
        .map((d) => ({ time: d.time, value: d.macd_signal! }));
      if (signalData.length > 0) {
        const signalLine = chart.addSeries(LineSeries, {
          color: chartColors.macdSignal,
          lineWidth: 1,
        });
        seriesRefs.current.line2 = signalLine;
        signalLine.setData(signalData);
      }
    }

    if (type === "rsi") {
      // RSI line — purple
      const rsiData = indicators
        .filter((d) => d.rsi_14 != null)
        .map((d) => ({ time: d.time, value: d.rsi_14! }));
      if (rsiData.length > 0) {
        const rsiSeries = chart.addSeries(LineSeries, {
          color: chartColors.rsiLine,
          lineWidth: 1,
        });
        seriesRefs.current.line1 = rsiSeries;
        rsiSeries.setData(rsiData);

        // Overbought line at 70 (red dashed)
        rsiSeries.createPriceLine({
          price: 70,
          color: chartColors.rsiOverbought,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
        });

        // Oversold line at 30 (green dashed)
        rsiSeries.createPriceLine({
          price: 30,
          color: chartColors.rsiOversold,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
        });
      }
    }

    chart.timeScale().fitContent();

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
      seriesRefs.current = { hist: null, line1: null, line2: null };
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indicators, type, height]); // NO chartColors — preserves zoom/scroll on theme toggle

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

    if (type === "macd") {
      // MACD histogram needs setData to update per-bar colors (lightweight-charts constraint)
      if (seriesRefs.current.hist && indicators.length) {
        const histData = indicators
          .filter((d) => d.macd_histogram != null)
          .map((d) => ({
            time: d.time,
            value: d.macd_histogram!,
            color:
              d.macd_histogram! >= 0
                ? chartColors.macdHistPositive
                : chartColors.macdHistNegative,
          }));
        seriesRefs.current.hist.setData(histData);
      }
      if (seriesRefs.current.line1) {
        seriesRefs.current.line1.applyOptions({ color: chartColors.macdLine });
      }
      if (seriesRefs.current.line2) {
        seriesRefs.current.line2.applyOptions({ color: chartColors.macdSignal });
      }
    }

    if (type === "rsi") {
      if (seriesRefs.current.line1) {
        seriesRefs.current.line1.applyOptions({ color: chartColors.rsiLine });
      }
      // Price lines (overbought/oversold) created via createPriceLine cannot be updated
      // via applyOptions — they use initial colors. Acceptable: threshold lines are
      // semantically the same color (red/green) across both themes.
    }
  }, [chartColors, type, indicators]);

  return (
    <div className="border-t border-border">
      <p className="text-xs text-muted-foreground px-2 py-1">
        {type === "macd" ? "MACD (12, 26, 9)" : "RSI (14)"}
      </p>
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
