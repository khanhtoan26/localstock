"use client";

import { useTranslations } from "next-intl";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useQueryState, parseAsString } from "nuqs";

export function StockSearchInput() {
  const t = useTranslations("rankings.search");
  // shallow: false keeps the Next.js router cache in sync so back-navigation restores the search term.
  // throttleMs: 150 throttles router.replace calls to avoid excessive navigations while typing.
  const [q, setQ] = useQueryState(
    "q",
    parseAsString.withDefault("").withOptions({ shallow: false, throttleMs: 150 })
  );

  return (
    <div className="relative max-w-xs mb-4">
      <label htmlFor="rankings-search" className="sr-only">
        {t("placeholder")}
      </label>
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
      <Input
        id="rankings-search"
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value || null)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setQ(null);
        }}
        placeholder={t("placeholder")}
        className="h-9 pl-8 pr-8 text-sm"
      />
      {q && (
        <button
          type="button"
          onClick={() => setQ(null)}
          className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground transition-colors"
          aria-label={t("clear")}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
