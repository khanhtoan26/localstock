// Glossary Text Scanner — finds glossary term aliases in text and returns segments
// Pure functions: buildAliasMap, scanText, isWordBoundary
// Used by GlossaryMarkdown to inject interactive term links into AI report text

import { getAllEntries, type GlossaryEntry } from "@/lib/glossary";

export interface AliasMapping {
  aliasLower: string; // Lowercased alias for case-insensitive matching
  alias: string; // Original alias text
  entry: GlossaryEntry;
}

export interface GlossaryMatch {
  entry: GlossaryEntry;
  matchedText: string; // Original text from source (preserves casing)
}

export type TextSegment = string | GlossaryMatch;

/**
 * Build a sorted alias map from all glossary entries.
 * Aliases are sorted by length descending (longest first) so that
 * "chỉ số RSI" matches before "RSI" (per D-05).
 */
export function buildAliasMap(): AliasMapping[] {
  const entries = getAllEntries();
  const mappings: AliasMapping[] = [];

  for (const entry of entries) {
    for (const alias of entry.aliases) {
      mappings.push({
        aliasLower: alias.toLowerCase(),
        alias,
        entry,
      });
    }
  }

  // Longest-first sort (D-05)
  mappings.sort((a, b) => b.aliasLower.length - a.aliasLower.length);
  return mappings;
}

/**
 * Check if a character is a word boundary.
 * Returns true for undefined (start/end of string) or non-letter/non-digit characters.
 * Uses Unicode-aware regex to handle Vietnamese diacritics correctly.
 */
export function isWordBoundary(char: string | undefined): boolean {
  if (char === undefined) return true;
  return !/[\p{L}\p{N}]/u.test(char);
}

/**
 * Scan text for glossary term aliases and return an array of text segments.
 *
 * - Case-insensitive matching via toLowerCase() (NOT diacritic normalization per D-06)
 * - Only links the first occurrence of each entry (per D-07) using linkedIds Set
 * - Checks word boundaries to prevent partial matches (e.g. "MA" inside "thematic")
 * - Returns array of string | GlossaryMatch segments, no empty strings
 */
export function scanText(
  text: string,
  aliasMap: AliasMapping[],
  linkedIds: Set<string>,
): TextSegment[] {
  const segments: TextSegment[] = [];
  const textLower = text.toLowerCase();
  let cursor = 0;
  let textStart = 0; // Start of current unmatched text run

  while (cursor < text.length) {
    let matched = false;

    for (const { aliasLower, entry } of aliasMap) {
      // Skip if this entry already linked (first-occurrence-only per D-07)
      if (linkedIds.has(entry.id)) continue;

      // Check if alias matches at current cursor position
      if (!textLower.startsWith(aliasLower, cursor)) continue;

      // Word boundary check
      const before = text[cursor - 1];
      const after = text[cursor + aliasLower.length];
      if (!isWordBoundary(before) || !isWordBoundary(after)) continue;

      // Found a match — push preceding text if any
      if (textStart < cursor) {
        segments.push(text.slice(textStart, cursor));
      }
      const matchedText = text.slice(cursor, cursor + aliasLower.length);
      segments.push({ entry, matchedText });
      linkedIds.add(entry.id);
      cursor = cursor + aliasLower.length;
      textStart = cursor;
      matched = true;
      break;
    }

    if (!matched) {
      cursor++;
    }
  }

  // Push remaining text
  if (textStart < text.length) {
    segments.push(text.slice(textStart));
  }

  // Filter out empty string segments
  return segments.filter(
    (seg) => typeof seg !== "string" || seg.length > 0,
  );
}
