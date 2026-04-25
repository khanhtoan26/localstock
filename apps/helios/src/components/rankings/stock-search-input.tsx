"use client";

import { useTranslations } from "next-intl";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";

interface StockSearchInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function StockSearchInput({ value, onChange }: StockSearchInputProps) {
  const t = useTranslations("rankings.search");

  return (
    <div className="relative max-w-xs mb-4">
      <label htmlFor="rankings-search" className="sr-only">
        {t("placeholder")}
      </label>
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
      <Input
        id="rankings-search"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onChange("");
        }}
        placeholder={t("placeholder")}
        className="h-9 pl-8 pr-8 text-sm"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground transition-colors"
          aria-label={t("clear")}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
