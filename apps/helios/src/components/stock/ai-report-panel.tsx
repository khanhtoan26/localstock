"use client";

import Markdown from "react-markdown";
import { Skeleton } from "@/components/ui/skeleton";
import type { StockReport } from "@/lib/types";

interface AIReportPanelProps {
  report: StockReport | undefined;
  isLoading: boolean;
  isError: boolean;
}

export function AIReportPanel({ report, isLoading, isError }: AIReportPanelProps) {
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
        Chưa có báo cáo — chạy pipeline để tạo báo cáo AI.
      </p>
    );
  }

  const content = report.summary || null;
  const fallbackJson = report.content_json;

  return content ? (
    <div className="prose dark:prose-invert prose-sm max-w-none">
      <Markdown>{content}</Markdown>
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
      Báo cáo không có nội dung.
    </p>
  );
}
