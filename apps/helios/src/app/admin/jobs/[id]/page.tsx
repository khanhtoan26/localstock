"use client";

import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, AlertCircle } from "lucide-react";
import { useAdminJobDetail, useStockReport, getJobSymbols } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/admin/status-badge";
import { ReportProgress } from "@/components/admin/report-progress";
import { AIReportPanel } from "@/components/stock/ai-report-panel";
import { Skeleton } from "@/components/ui/skeleton";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const t = useTranslations("admin");
  const jobId = Number(params.id);

  const {
    data: job,
    isLoading: jobLoading,
    isError: jobError,
  } = useAdminJobDetail(Number.isFinite(jobId) ? jobId : null);

  const symbols = job ? getJobSymbols(job) : [];
  const isReportJob = job?.job_type === "report";
  const lastSymbol = symbols[symbols.length - 1] ?? "";

  const {
    data: report,
    isLoading: reportLoading,
    isError: reportError,
  } = useStockReport(isReportJob && job?.status === "completed" ? lastSymbol : "");

  if (jobLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (jobError || !job) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <AlertCircle className="h-10 w-10 text-destructive" />
        <p className="text-sm text-muted-foreground">{t("jobs.notFound")}</p>
        <Button variant="outline" onClick={() => router.push("/admin")}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          {t("jobs.backToAdmin")}
        </Button>
      </div>
    );
  }

  const createdAt = job.created_at
    ? new Date(job.created_at).toLocaleString()
    : "—";
  const duration = getDuration(job.started_at, job.completed_at);

  return (
    <div>
      <Button
        variant="ghost"
        size="sm"
        className="mb-4"
        onClick={() => router.push("/admin")}
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        {t("jobs.backToAdmin")}
      </Button>

      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-xl font-semibold">
          {t("jobs.detailTitle", { id: job.id })}
        </h1>
        <StatusBadge status={job.status} />
      </div>

      {/* Job metadata */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 p-4 border rounded-lg bg-card">
        <div>
          <span className="text-xs text-muted-foreground block">{t("jobs.columns.type")}</span>
          <Badge variant="outline" className="mt-1">{job.job_type}</Badge>
        </div>
        <div>
          <span className="text-xs text-muted-foreground block">{t("jobs.columns.symbols")}</span>
          <span className="text-sm mt-1 block">
            {symbols.length > 0 ? symbols.join(", ") : "—"}
          </span>
        </div>
        <div>
          <span className="text-xs text-muted-foreground block">{t("jobs.columns.created")}</span>
          <span className="text-sm mt-1 block">{createdAt}</span>
        </div>
        <div>
          <span className="text-xs text-muted-foreground block">{t("jobs.columns.duration")}</span>
          <span className="text-sm mt-1 block">{duration}</span>
        </div>
      </div>

      {/* Progress section for report jobs */}
      {isReportJob && (job.status === "pending" || job.status === "running") && (
        <div className="mb-8 p-4 border rounded-lg">
          <h2 className="text-base font-medium mb-4">{t("report.sheetTitle")}</h2>
          <ReportProgress jobStatus={job.status} currentSymbol={symbols[0]} />
        </div>
      )}

      {/* Error section */}
      {job.status === "failed" && (
        <div className="mb-8 p-6 border border-destructive/30 rounded-lg bg-destructive/5">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
            <div>
              <h2 className="text-base font-medium text-destructive">
                {isReportJob ? t("report.errorHeading") : t("jobs.errorHeading")}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                {job.error || (isReportJob ? t("report.errorGeneric") : t("jobs.errorGeneric"))}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Report content for completed report jobs */}
      {isReportJob && job.status === "completed" && (
        <div className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-medium">{t("report.sheetTitle")}</h2>
            {lastSymbol && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(`/stock/${lastSymbol}`, "_blank")}
              >
                {t("report.viewStockPage")}
              </Button>
            )}
          </div>
          <AIReportPanel
            report={report}
            isLoading={reportLoading}
            isError={reportError}
          />
        </div>
      )}

      {/* Generic result for non-report jobs */}
      {!isReportJob && job.status === "completed" && job.result && (
        <div className="border rounded-lg p-4">
          <h2 className="text-base font-medium mb-4">{t("jobs.result")}</h2>
          <pre className="text-xs font-mono bg-muted p-3 rounded overflow-x-auto">
            {JSON.stringify(job.result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function getDuration(
  startedAt: string | null,
  completedAt: string | null,
): string {
  if (!startedAt || !completedAt) return "—";
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}
