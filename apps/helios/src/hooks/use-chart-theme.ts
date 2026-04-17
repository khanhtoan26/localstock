"use client";
import { useTheme } from "next-themes";
import { getChartColors, type ChartColorSet } from "@/lib/chart-colors";

/** Returns the chart color set for the current theme */
export function useChartTheme(): ChartColorSet {
  const { resolvedTheme } = useTheme();
  // resolvedTheme can be undefined during SSR — default to light (warm-light is default)
  return getChartColors(resolvedTheme === "dark" ? "dark" : "light");
}
