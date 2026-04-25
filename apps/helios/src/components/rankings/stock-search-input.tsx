"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useQueryState, parseAsString } from "nuqs";

export function StockSearchInput() {
  const t = useTranslations("rankings.search");
  const [q, setQ] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: true })
  );
  // Local state for immediate input display; URL updated after 150ms debounce.
  const [localValue, setLocalValue] = useState(q);

  // Sync localValue if q changes externally (e.g., browser back/forward).
  useEffect(() => {
    setLocalValue(q);
  }, [q]);

  // Debounce: update URL only after 150ms idle (Claude's Discretion).
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(localValue.trim() ? localValue : null);
    }, 150);
    return () => clearTimeout(timer);
  }, [localValue, setQ]);

  return (
    <div className="relative max-w-xs mb-4">
      <label htmlFor="rankings-search" className="sr-only">
        {t("placeholder")}
      </label>
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
      <Input
        id="rankings-search"
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setLocalValue("");
            setQ(null); // D-10: null removes ?q= from URL entirely (Pitfall 4)
          }
        }}
        placeholder={t("placeholder")}
        className="h-9 pl-8 pr-8 text-sm"
      />
      {localValue && (
        <button
          type="button"
          onClick={() => {
            setLocalValue("");
            setQ(null); // D-10: null, not "", to remove param (Pitfall 4)
          }}
          className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground transition-colors"
          aria-label={t("clear")}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
