"use client";

import { useState, useEffect } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { GlossaryEntryCard } from "./glossary-entry-card";
import { normalizeForSearch, type GlossaryEntry, type GlossaryCategory } from "@/lib/glossary";

// Category-specific search placeholders per UI-SPEC Copywriting Contract
const SEARCH_PLACEHOLDERS: Record<GlossaryCategory, string> = {
  technical: "Tìm chỉ báo kỹ thuật...",
  fundamental: "Tìm tỷ số cơ bản...",
  macro: "Tìm yếu tố vĩ mô...",
};

interface GlossarySearchProps {
  entries: GlossaryEntry[];
  category: GlossaryCategory;
}

export function GlossarySearch({ entries, category }: GlossarySearchProps) {
  const [query, setQuery] = useState("");
  const [hashId, setHashId] = useState<string | null>(null);

  // Read URL hash on mount for deep-link auto-expand (Phase 10 support)
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash) {
      setHashId(hash);
      // Scroll to the matching entry after render
      const el = document.getElementById(hash);
      if (el) {
        setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
      }
    }
  }, []);

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

  return (
    <div>
      {/* Search input */}
      <div className="relative">
        <label htmlFor={`search-${category}`} className="sr-only">
          {SEARCH_PLACEHOLDERS[category]}
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
          placeholder={SEARCH_PLACEHOLDERS[category]}
          className="h-10 w-full pl-10 pr-10"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2"
            aria-label="Xóa tìm kiếm"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Result count */}
      <p className="text-xs text-muted-foreground mt-2" aria-live="polite">
        {filtered.length} kết quả
      </p>

      {/* Entry list */}
      <div className="mt-4 space-y-4">
        {filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            Không tìm thấy kết quả cho &quot;{query}&quot;
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
