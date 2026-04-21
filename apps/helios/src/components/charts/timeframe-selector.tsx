"use client";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

export interface TimeframeOption {
  tKey: string;
  days: number;
}

const TIMEFRAMES: TimeframeOption[] = [
  { tKey: "1m", days: 30 },
  { tKey: "3m", days: 90 },
  { tKey: "6m", days: 180 },
  { tKey: "1y", days: 365 },
  { tKey: "2y", days: 730 },
];

interface TimeframeSelectorProps {
  selectedDays: number;
  onChange: (days: number) => void;
}

export function TimeframeSelector({
  selectedDays,
  onChange,
}: TimeframeSelectorProps) {
  const t = useTranslations("timeframe");

  return (
    <div className="flex gap-1">
      {TIMEFRAMES.map((tf) => (
        <Button
          key={tf.days}
          variant={selectedDays === tf.days ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(tf.days)}
          className="text-xs px-3"
        >
          {t(tf.tKey as "1m" | "3m" | "6m" | "1y" | "2y")}
        </Button>
      ))}
    </div>
  );
}
