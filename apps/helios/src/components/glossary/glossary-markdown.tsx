"use client";

import { useMemo, useRef, isValidElement, Children, cloneElement } from "react";
import Markdown from "react-markdown";
import {
  buildAliasMap,
  scanText,
  type TextSegment,
} from "@/lib/glossary-linker";
import { GlossaryTerm } from "./glossary-term";
import type { ReactNode, ReactElement } from "react";

// Build alias map once at module level — glossary data is static
const aliasMap = buildAliasMap();

interface GlossaryMarkdownProps {
  content: string;
}

export function GlossaryMarkdown({ content }: GlossaryMarkdownProps) {
  // Track linked IDs across all elements in this render (shared ref per Pitfall 6)
  const linkedIdsRef = useRef(new Set<string>());

  // Reset linked IDs when content changes
  useMemo(() => {
    linkedIdsRef.current = new Set<string>();
  }, [content]);

  function processChildren(children: ReactNode): ReactNode {
    if (typeof children === "string") {
      const segments: TextSegment[] = scanText(
        children,
        aliasMap,
        linkedIdsRef.current,
      );
      return segments.map((seg, i) =>
        typeof seg === "string" ? (
          seg
        ) : (
          <GlossaryTerm key={`${seg.entry.id}-${i}`} entry={seg.entry}>
            {seg.matchedText}
          </GlossaryTerm>
        ),
      );
    }

    if (Array.isArray(children)) {
      return Children.map(children, (child) => {
        if (typeof child === "string") {
          return processChildren(child);
        }
        if (isValidElement(child)) {
          const el = child as ReactElement<{ children?: ReactNode }>;
          // Skip code elements — don't scan for glossary terms inside code (per RESEARCH A2)
          if (el.type === "code") {
            return child;
          }
          return cloneElement(el, {
            children: processChildren(el.props.children),
          });
        }
        return child;
      });
    }

    if (isValidElement(children)) {
      const el = children as ReactElement<{ children?: ReactNode }>;
      // Skip code elements
      if (el.type === "code") {
        return children;
      }
      return cloneElement(el, {
        children: processChildren(el.props.children),
      });
    }

    return children;
  }

  return (
    <Markdown
      components={{
        p: ({ children, ...props }) => (
          <p {...props}>{processChildren(children)}</p>
        ),
        li: ({ children, ...props }) => (
          <li {...props}>{processChildren(children)}</li>
        ),
        td: ({ children, ...props }) => (
          <td {...props}>{processChildren(children)}</td>
        ),
        th: ({ children, ...props }) => (
          <th {...props}>{processChildren(children)}</th>
        ),
      }}
    >
      {content}
    </Markdown>
  );
}
