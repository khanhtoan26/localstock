"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StockTable } from "@/components/admin/stock-table";
import { PipelineControl } from "@/components/admin/pipeline-control";
import { JobMonitor } from "@/components/admin/job-monitor";
import { useJobTransitions } from "@/hooks/use-job-transitions";
import { invalidateForJob, getJobSymbols } from "@/lib/queries";
import type { AdminJob } from "@/lib/types";
import { ReportGenerationSheet, type SheetState } from "@/components/admin/report-generation-sheet";

export default function AdminPage() {
  const t = useTranslations("admin");
  const [activeTab, setActiveTab] = useState("stocks");
  const [focusedJobId, setFocusedJobId] = useState<number | null>(null);
  const [sheetState, setSheetState] = useState<SheetState>({ status: "closed" });
  const queryClient = useQueryClient();

  const handleTransition = useCallback(
    ({ job }: { job: AdminJob }) => {
      // 1. Targeted cache invalidation (per D-01, D-02)
      invalidateForJob(queryClient, job);

      // 2. Toast notification (per D-04)
      const symbols = getJobSymbols(job);
      const symbolStr = symbols.length > 0 ? symbols.slice(0, 3).join(", ") : null;
      const hasMore = symbols.length > 3 ? ` +${symbols.length - 3}` : "";

      const isCompleted = job.status === "completed";
      const toastMethod = isCompleted ? toast.success : toast.error;
      const duration = isCompleted ? 5000 : 8000;

      let message: string;
      if (symbols.length > 0) {
        message = isCompleted
          ? t("toast.jobCompleted", { type: job.job_type, symbols: symbolStr + hasMore })
          : t("toast.jobFailed", { type: job.job_type, symbols: symbolStr + hasMore });
      } else {
        message = isCompleted
          ? t("toast.jobCompletedGeneric", { type: job.job_type })
          : t("toast.jobFailedGeneric", { type: job.job_type });
      }

      toastMethod(message, {
        duration,
        action: {
          label: t("toast.viewJob"),
          onClick: () => {
            setActiveTab("jobs");
            setFocusedJobId(job.id);
          },
        },
      });

      // 3. Update sheet state for report jobs (Phase 13)
      if (job.job_type === "report") {
        setSheetState((prev) => {
          if (prev.status !== "generating" && prev.status !== "minimized") return prev;
          if (prev.jobId !== job.id) return prev;
          const jobSymbols = getJobSymbols(job);
          if (job.status === "completed") {
            return {
              status: "completed",
              symbols: prev.symbols,
              lastSymbol: jobSymbols[jobSymbols.length - 1] || prev.symbols[prev.symbols.length - 1] || "",
            };
          }
          if (job.status === "failed") {
            return {
              status: "failed",
              symbols: prev.symbols,
              failedSymbol: prev.symbols[0] || "",
            };
          }
          return prev;
        });
      }
    },
    [queryClient, t],
  );

  useJobTransitions(handleTransition);

  const handleFocusHandled = useCallback(() => {
    setFocusedJobId(null);
  }, []);

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="stocks">{t("tabs.stocks")}</TabsTrigger>
          <TabsTrigger value="pipeline">{t("tabs.pipeline")}</TabsTrigger>
          <TabsTrigger value="jobs">{t("tabs.jobs")}</TabsTrigger>
        </TabsList>
        <TabsContent value="stocks" className="pt-6">
          <StockTable />
        </TabsContent>
        <TabsContent value="pipeline" className="pt-6">
          <PipelineControl
            onOperationTriggered={() => setActiveTab("jobs")}
            onReportTriggered={({ jobId, symbols }) => {
              setSheetState({ status: "generating", symbols, jobId });
            }}
            reportMinimized={sheetState.status === "minimized"}
            onReportReopen={() => {
              if (sheetState.status === "minimized") {
                setSheetState({ status: "generating", symbols: sheetState.symbols, jobId: sheetState.jobId });
              }
            }}
          />
        </TabsContent>
        <TabsContent value="jobs" className="pt-6" keepMounted>
          <JobMonitor focusedJobId={focusedJobId} onFocusHandled={handleFocusHandled} />
        </TabsContent>
      </Tabs>
      <ReportGenerationSheet
        sheetState={sheetState}
        onStateChange={setSheetState}
      />
    </div>
  );
}
