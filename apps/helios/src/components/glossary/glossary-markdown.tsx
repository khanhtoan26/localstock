"use client";

import { isValidElement, Children, cloneElement } from "react";
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

// Process ReactNode children, scanning text for glossary terms.
// Each call creates a fresh linkedIds set to avoid React strict mode
// and react-markdown internal memoization issues.
function processChildren(children: ReactNode): ReactNode {
  const linkedIds = new Set<string>();
  return processNode(children, linkedIds);
}

function processNode(children: ReactNode, linkedIds: Set<string>): ReactNode {
  if (typeof children === "string") {
    const segments: TextSegment[] = scanText(children, aliasMap, linkedIds);
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
        return processNode(child, linkedIds);
      }
      if (isValidElement(child)) {
        const el = child as ReactElement<{ children?: ReactNode }>;
        if (el.type === "code") return child;
        return cloneElement(el, {
          children: processNode(el.props.children, linkedIds),
        });
      }
      return child;
    });
  }

  if (isValidElement(children)) {
    const el = children as ReactElement<{ children?: ReactNode }>;
    if (el.type === "code") return children;
    return cloneElement(el, {
      children: processNode(el.props.children, linkedIds),
    });
  }

  return children;
}

// Filter out react-markdown's `node` prop to avoid DOM attribute warnings
function filterProps(props: Record<string, unknown>) {
  const { node, ...domProps } = props;
  return domProps;
}

export function GlossaryMarkdown({ content }: GlossaryMarkdownProps) {
  return (
    <Markdown
      components={{
        p: ({ children, ...props }) => (
          <p {...filterProps(props)}>{processChildren(children)}</p>
        ),
        li: ({ children, ...props }) => (
          <li {...filterProps(props)}>{processChildren(children)}</li>
        ),
        td: ({ children, ...props }) => (
          <td {...filterProps(props)}>{processChildren(children)}</td>
        ),
        th: ({ children, ...props }) => (
          <th {...filterProps(props)}>{processChildren(children)}</th>
        ),
      }}
    >
      {content}
    </Markdown>
  );
}
