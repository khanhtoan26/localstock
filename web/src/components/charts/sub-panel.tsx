"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  HistogramSeries,
  type IChartApi,
} from "lightweight-charts";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { IndicatorPoint } from "@/lib/types";

interface SubPanelProps {
  type: "macd" | "rsi";
  indicators: IndicatorPoint[];
  height?: number;
}

export function SubPanel({ type, indicators, height = 152 }: SubPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || !indicators.length) return;

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
              ? CHART_COLORS.macdHistPositive
              : CHART_COLORS.macdHistNegative,
        }));
      if (histData.length > 0) {
        const histSeries = chart.addSeries(HistogramSeries);
        histSeries.setData(histData);
      }

      // MACD line — blue
      const macdData = indicators
        .filter((d) => d.macd != null)
        .map((d) => ({ time: d.time, value: d.macd! }));
      if (macdData.length > 0) {
        const macdLine = chart.addSeries(LineSeries, {
          color: CHART_COLORS.macdLine,
          lineWidth: 1,
        });
        macdLine.setData(macdData);
      }

      // Signal line — orange
      const signalData = indicators
        .filter((d) => d.macd_signal != null)
        .map((d) => ({ time: d.time, value: d.macd_signal! }));
      if (signalData.length > 0) {
        const signalLine = chart.addSeries(LineSeries, {
          color: CHART_COLORS.macdSignal,
          lineWidth: 1,
        });
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
          color: CHART_COLORS.rsiLine,
          lineWidth: 1,
        });
        rsiSeries.setData(rsiData);

        // Overbought line at 70 (red dashed)
        rsiSeries.createPriceLine({
          price: 70,
          color: CHART_COLORS.rsiOverbought,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
        });

        // Oversold line at 30 (green dashed)
        rsiSeries.createPriceLine({
          price: 30,
          color: CHART_COLORS.rsiOversold,
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
    };
  }, [indicators, type, height]);

  return (
    <div className="border-t border-border">
      <p className="text-xs text-muted-foreground px-2 py-1">
        {type === "macd" ? "MACD (12, 26, 9)" : "RSI (14)"}
      </p>
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
