"use client";
import { useTranslations } from "next-intl";
import { BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  heading?: string;
  body: string;
  ctaLabel?: string;
  onCtaClick?: () => void;
}

export function EmptyState({
  heading,
  body,
  ctaLabel,
  onCtaClick,
}: EmptyStateProps) {
  const t = useTranslations("common");
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <BarChart3 className="h-12 w-12 text-muted-foreground" />
      <h2 className="mt-4 text-lg font-semibold text-foreground">{heading ?? t("noData")}</h2>
      <p className="mt-2 text-sm text-muted-foreground text-center max-w-md">{body}</p>
      {ctaLabel && onCtaClick && (
        <Button className="mt-4" onClick={onCtaClick}>
          {ctaLabel}
        </Button>
      )}
    </div>
  );
}
