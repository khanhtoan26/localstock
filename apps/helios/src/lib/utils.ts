import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format a score value with 1 decimal, or em dash if null */
export function formatScore(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toFixed(1);
}

/** Format Vietnamese price (VND uses dots as thousand separators) */
const vnFormatter = new Intl.NumberFormat("vi-VN");
export function formatVND(value: number | null | undefined): string {
  if (value == null) return "—";
  return vnFormatter.format(Math.round(value));
}

/** Format percentage with 1 decimal + % */
export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}%`;
}

/** Format large volumes with K/M suffix */
export function formatVolume(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return String(value);
}

/** Grade color map — returns Tailwind classes for badge styling */
export const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  B: "bg-stone-500/20 text-stone-700 dark:text-stone-400 border-stone-500/30",
  C: "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
  D: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
  F: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
};
