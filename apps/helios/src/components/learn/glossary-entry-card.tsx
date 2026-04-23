"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import type { GlossaryEntry } from "@/lib/glossary";

interface GlossaryEntryCardProps {
  entry: GlossaryEntry;
  defaultOpen?: boolean;
}

export function GlossaryEntryCard({ entry, defaultOpen = false }: GlossaryEntryCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const t = useTranslations("learn.glossary");

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card id={entry.id} className="scroll-mt-20">
        <CollapsibleTrigger
          className="w-full cursor-pointer text-left"
          aria-label={open ? t("collapse", { term: entry.term }) : t("expand", { term: entry.term })}
        >
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{entry.term}</CardTitle>
              {open ? (
                <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
              )}
            </div>
            <CardDescription>{entry.shortDef}</CardDescription>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent>
            {entry.formula && (
              <div className="mb-4">
                <span className="text-xs text-muted-foreground">{t("formula")}</span>
                <code className="block bg-muted rounded-md p-3 font-mono text-sm mt-1">
                  {entry.formula}
                </code>
              </div>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-code:text-muted-foreground">
              <ReactMarkdown>{entry.content}</ReactMarkdown>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
