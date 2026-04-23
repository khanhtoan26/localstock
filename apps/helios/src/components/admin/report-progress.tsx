"use client";

import { useTranslations } from "next-intl";
import { Check, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type StepStatus = "pending" | "active" | "completed" | "failed";

interface ReportProgressProps {
  jobStatus: "pending" | "running" | "completed" | "failed";
  currentSymbol?: string;
}

function getStepStatuses(jobStatus: ReportProgressProps["jobStatus"]): [StepStatus, StepStatus, StepStatus] {
  switch (jobStatus) {
    case "pending":
      return ["active", "pending", "pending"];
    case "running":
      return ["completed", "active", "pending"];
    case "completed":
      return ["completed", "completed", "completed"];
    case "failed":
      return ["completed", "failed", "pending"];
  }
}

function StepDot({ status }: { status: StepStatus }) {
  if (status === "completed") {
    return <Check className="h-3 w-3 text-[var(--stock-up)]" />;
  }
  if (status === "failed") {
    return <AlertCircle className="h-3 w-3 text-destructive" />;
  }
  if (status === "active") {
    return (
      <div className="h-2 w-2 rounded-full bg-primary step-active-pulse" />
    );
  }
  return (
    <div className="h-2 w-2 rounded-full border border-muted-foreground" />
  );
}

export function ReportProgress({ jobStatus, currentSymbol }: ReportProgressProps) {
  const t = useTranslations("admin");

  const stepKeys = ["stepQueued", "stepGenerating", "stepComplete"] as const;
  const statuses = getStepStatuses(jobStatus);

  return (
    <div className="space-y-3" aria-live="polite">
      {stepKeys.map((key, i) => {
        const status = statuses[i];
        return (
          <div key={key}>
            <div className="flex items-center gap-2">
              <div className="flex h-4 w-4 items-center justify-center">
                <StepDot status={status} />
              </div>
              <span
                className={cn(
                  "text-sm",
                  status === "pending" && "text-muted-foreground",
                  status === "active" && "text-foreground font-medium",
                  status === "completed" && "text-muted-foreground line-through",
                  status === "failed" && "text-destructive",
                )}
              >
                {t(`report.${key}`)}
              </span>
              {status === "active" && key === "stepGenerating" && (
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
              )}
            </div>
            {status === "active" && key === "stepGenerating" && currentSymbol && (
              <span className="text-xs text-muted-foreground ml-6">
                {t("report.generatingFor", { symbol: currentSymbol })}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
