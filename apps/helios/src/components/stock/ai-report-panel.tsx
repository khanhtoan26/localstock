"use client";

import { useTranslations } from "next-intl";
import { GlossaryMarkdown } from "@/components/glossary/glossary-markdown";
import { Skeleton } from "@/components/ui/skeleton";
import { GradeBadge } from "@/components/rankings/grade-badge";
import { RecommendationBadge } from "@/components/stock/recommendation-badge";
import { formatScore } from "@/lib/utils";
import type { StockReport } from "@/lib/types";

interface AIReportPanelProps {
  report: StockReport | undefined;
  isLoading: boolean;
  isError: boolean;
}

export function AIReportPanel({ report, isLoading, isError }: AIReportPanelProps) {
  const t = useTranslations("stock.report");

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    );
  }

  if (isError || !report) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("noReport")}
      </p>
    );
  }

  const content = report.summary || null;
  const fallbackJson = report.content_json;

  return (
    <div className="space-y-4">
      {/* Signal header: recommendation + grade + score + T+3 */}
      {(report.recommendation || report.grade || report.total_score != null) && (
        <div className="flex flex-wrap items-center gap-2">
          {report.recommendation && (
            <RecommendationBadge recommendation={report.recommendation} />
          )}
          {report.grade && <GradeBadge grade={report.grade} />}
          {report.total_score != null && (
            <span className="font-mono text-sm font-semibold text-muted-foreground">
              {formatScore(report.total_score)}/100
            </span>
          )}
          {report.t3_prediction && (
            <span className="text-xs text-muted-foreground border rounded px-1.5 py-0.5">
              T+3: {report.t3_prediction}
            </span>
          )}
        </div>
      )}

      {/* Report content */}
      {content ? (
        <div className="prose dark:prose-invert prose-sm max-w-none">
          <GlossaryMarkdown content={content} />
        </div>
      ) : fallbackJson ? (
        <div className="space-y-4">
          {Object.entries(fallbackJson).map(([key, value]) => (
            <div key={key}>
              <h3 className="text-sm font-semibold capitalize mb-1">
                {key.replace(/_/g, " ")}
              </h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          {t("emptyContent")}
        </p>
      )}
    </div>
  );
}
