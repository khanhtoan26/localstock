"use client";

import { useTranslations } from "next-intl";
import { AIReportPanel } from "@/components/stock/ai-report-panel";
import { useStockReport } from "@/lib/queries";

interface ReportPreviewProps {
  symbol: string;
}

export function ReportPreview({ symbol }: ReportPreviewProps) {
  const t = useTranslations("admin");
  const { data: report, isLoading, isError } = useStockReport(symbol);

  if (!symbol) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("report.emptyPreview")}
      </p>
    );
  }

  return (
    <div className="space-y-4" aria-live="polite">
      <AIReportPanel report={report} isLoading={isLoading} isError={isError} />
    </div>
  );
}
