"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { GlossaryEntryCard } from "./glossary-entry-card";
import { normalizeForSearch, type GlossaryEntry, type GlossaryCategory } from "@/lib/glossary";

interface GlossarySearchProps {
  entries: GlossaryEntry[];
  category: GlossaryCategory;
}

export function GlossarySearch({ entries, category }: GlossarySearchProps) {
  const t = useTranslations("learn.glossary");
  const [query, setQuery] = useState("");
  const [hashId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const hash = window.location.hash.slice(1);
    return hash || null;
  });

  // Scroll to hash target after initial render (Phase 10 deep-link support)
  useEffect(() => {
    if (!hashId) return;
    const el = document.getElementById(hashId);
    if (el) {
      setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    }
  }, [hashId]);

  const filtered = query
    ? entries.filter((entry) => {
        const normalized = normalizeForSearch(query);
        return (
          normalizeForSearch(entry.term).includes(normalized) ||
          normalizeForSearch(entry.termEn).includes(normalized) ||
          normalizeForSearch(entry.shortDef).includes(normalized) ||
          entry.aliases.some((alias) =>
            normalizeForSearch(alias).includes(normalized)
          )
        );
      })
    : entries;

  const placeholder = t(`searchPlaceholders.${category}`);

  return (
    <div>
      {/* Search input */}
      <div className="relative">
        <label htmlFor={`search-${category}`} className="sr-only">
          {placeholder}
        </label>
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <Input
          id={`search-${category}`}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setQuery("");
              (e.target as HTMLInputElement).focus();
            }
          }}
          placeholder={placeholder}
          className="h-10 w-full pl-10 pr-10"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2"
            aria-label={t("clearSearch")}
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Result count */}
      <p className="text-xs text-muted-foreground mt-2" aria-live="polite">
        {t("resultCount", { count: filtered.length })}
      </p>

      {/* Entry list */}
      <div className="mt-4 space-y-4">
        {filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            {t("noResultsFor", { query })}
          </p>
        ) : (
          filtered.map((entry) => (
            <GlossaryEntryCard
              key={entry.id}
              entry={entry}
              defaultOpen={entry.id === hashId}
            />
          ))
        )}
      </div>
    </div>
  );
}
