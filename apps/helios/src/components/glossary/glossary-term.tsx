"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Popover } from "@base-ui/react/popover";
import type { GlossaryEntry } from "@/lib/glossary";

interface GlossaryTermProps {
  entry: GlossaryEntry;
  children: React.ReactNode;
}

export function GlossaryTerm({ entry, children }: GlossaryTermProps) {
  const t = useTranslations("learn.glossary");

  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={200}
        closeDelay={300}
        nativeButton={false}
        render={<span />}
        className="decoration-dotted underline underline-offset-2 decoration-primary cursor-pointer hover:decoration-solid"
      >
        {children}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={8} align="center">
          <Popover.Popup className="z-50 max-w-xs rounded-lg border bg-popover p-4 shadow-md">
            <p className="text-sm font-semibold">{entry.term}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {entry.shortDef}
            </p>
            {entry.formula && (
              <code className="mt-2 block rounded bg-muted p-2 font-mono text-xs">
                {entry.formula}
              </code>
            )}
            <Link
              href={`/learn/${entry.category}#${entry.id}`}
              className="mt-2 inline-block text-xs text-primary hover:underline"
              aria-label={t("viewDetailsLabel", { term: entry.term })}
            >
              {t("viewDetails")}
            </Link>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
