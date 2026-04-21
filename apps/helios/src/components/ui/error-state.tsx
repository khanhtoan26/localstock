"use client";
import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";

interface ErrorStateProps {
  heading?: string;
  body?: string;
}

export function ErrorState({
  heading,
  body,
}: ErrorStateProps) {
  const t = useTranslations("common");
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <AlertCircle className="h-12 w-12 text-red-700 dark:text-red-400" />
      <h2 className="mt-4 text-lg font-semibold text-foreground">{heading ?? t("loadError")}</h2>
      <p className="mt-2 text-sm text-muted-foreground text-center max-w-md">{body ?? t("connectionError")}</p>
    </div>
  );
}
