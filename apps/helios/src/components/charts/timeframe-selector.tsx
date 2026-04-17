"use client";
import { Button } from "@/components/ui/button";

export interface TimeframeOption {
  label: string;
  days: number;
}

const TIMEFRAMES: TimeframeOption[] = [
  { label: "1T", days: 30 },
  { label: "3T", days: 90 },
  { label: "6T", days: 180 },
  { label: "1N", days: 365 },
  { label: "2N", days: 730 },
];

interface TimeframeSelectorProps {
  selectedDays: number;
  onChange: (days: number) => void;
}

export function TimeframeSelector({
  selectedDays,
  onChange,
}: TimeframeSelectorProps) {
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
          {tf.label}
        </Button>
      ))}
    </div>
  );
}
