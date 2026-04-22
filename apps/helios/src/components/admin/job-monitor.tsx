"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, Loader2 } from "lucide-react";
import { useAdminJobs, useAdminJobDetail } from "@/lib/queries";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "./status-badge";
import { cn } from "@/lib/utils";

function formatDuration(
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

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function JobDetailPanel({ jobId }: { jobId: number }) {
  const { data: detail, isLoading } = useAdminJobDetail(jobId);
  if (isLoading)
    return <Loader2 className="h-4 w-4 animate-spin" />;
  if (!detail) return <span>—</span>;
  if (detail.error)
    return (
      <pre className="text-sm text-destructive whitespace-pre-wrap p-3 bg-muted rounded-md">
        {detail.error}
      </pre>
    );
  if (detail.result)
    return (
      <pre className="text-sm whitespace-pre-wrap p-3 bg-muted rounded-md">
        {JSON.stringify(detail.result, null, 2)}
      </pre>
    );
  return <span className="text-sm text-muted-foreground">—</span>;
}

export function JobMonitor() {
  const t = useTranslations("admin");
  const { data, isLoading, isError } = useAdminJobs();
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return <ErrorState />;
  }

  if (!data || data.count === 0) {
    return (
      <EmptyState
        heading={t("jobs.emptyHeading")}
        body={t("jobs.emptyBody")}
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("jobs.columns.type")}</TableHead>
          <TableHead>{t("jobs.columns.status")}</TableHead>
          <TableHead>{t("jobs.columns.duration")}</TableHead>
          <TableHead>{t("jobs.columns.created")}</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.jobs.map((job) => (
          <>
            <TableRow
              key={job.id}
              className="cursor-pointer"
              onClick={() =>
                setExpandedJobId(expandedJobId === job.id ? null : job.id)
              }
            >
              <TableCell>
                <Badge variant="outline">{job.job_type}</Badge>
              </TableCell>
              <TableCell>
                <StatusBadge status={job.status} />
              </TableCell>
              <TableCell>
                {job.status === "running" ? (
                  <Loader2 className="h-3 w-3 animate-spin inline" />
                ) : (
                  formatDuration(job.started_at, job.completed_at)
                )}
              </TableCell>
              <TableCell>{formatTimestamp(job.created_at)}</TableCell>
              <TableCell>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 transition-transform",
                    expandedJobId === job.id && "rotate-180",
                  )}
                />
              </TableCell>
            </TableRow>
            {expandedJobId === job.id && (
              <TableRow key={`${job.id}-detail`}>
                <TableCell colSpan={5}>
                  <JobDetailPanel jobId={job.id} />
                </TableCell>
              </TableRow>
            )}
          </>
        ))}
      </TableBody>
    </Table>
  );
}
