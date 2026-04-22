"use client";

import React, { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, Loader2, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { useAdminJobs, useAdminJobDetail } from "@/lib/queries";
import type { AdminJob } from "@/lib/types";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "./status-badge";
import { cn } from "@/lib/utils";

type JobSortKey = "job_type" | "status" | "created_at";
type SortDir = "asc" | "desc";

const JOB_STATUSES = ["all", "pending", "running", "completed", "failed"] as const;
const JOB_TYPES = ["all", "crawl", "analyze", "score", "report", "pipeline"] as const;

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
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<JobSortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function toggleSort(key: JobSortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "created_at" ? "desc" : "asc");
    }
  }

  const jobs = data?.jobs;

  const filteredAndSorted = useMemo(() => {
    if (!jobs) return [];
    let list = jobs;
    if (statusFilter !== "all") {
      list = list.filter((j: AdminJob) => j.status === statusFilter);
    }
    if (typeFilter !== "all") {
      list = list.filter((j: AdminJob) => j.job_type === typeFilter);
    }
    return [...list].sort((a: AdminJob, b: AdminJob) => {
      let cmp: number;
      if (sortKey === "created_at") {
        cmp = (a.created_at ?? "").localeCompare(b.created_at ?? "");
      } else {
        cmp = (a[sortKey] ?? "").localeCompare(b[sortKey] ?? "");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [jobs, statusFilter, typeFilter, sortKey, sortDir]);

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
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-muted-foreground">{t("jobs.filterStatus")}:</span>
          {JOB_STATUSES.map((s) => (
            <Button
              key={s}
              variant={statusFilter === s ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? t("jobs.all") : s}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-sm text-muted-foreground">{t("jobs.filterType")}:</span>
          {JOB_TYPES.map((jt) => (
            <Button
              key={jt}
              variant={typeFilter === jt ? "default" : "outline"}
              size="sm"
              onClick={() => setTypeFilter(jt)}
            >
              {jt === "all" ? t("jobs.all") : jt}
            </Button>
          ))}
        </div>
      </div>

      {filteredAndSorted.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          {t("jobs.noResults")}
        </p>
      ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>
              <button
                className="flex items-center gap-1 hover:text-foreground transition-colors"
                onClick={() => toggleSort("job_type")}
              >
                {t("jobs.columns.type")}
                {sortKey === "job_type" ? (
                  sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                ) : (
                  <ArrowUpDown className="h-3 w-3 opacity-30" />
                )}
              </button>
            </TableHead>
            <TableHead>
              <button
                className="flex items-center gap-1 hover:text-foreground transition-colors"
                onClick={() => toggleSort("status")}
              >
                {t("jobs.columns.status")}
                {sortKey === "status" ? (
                  sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                ) : (
                  <ArrowUpDown className="h-3 w-3 opacity-30" />
                )}
              </button>
            </TableHead>
            <TableHead>{t("jobs.columns.duration")}</TableHead>
            <TableHead>
              <button
                className="flex items-center gap-1 hover:text-foreground transition-colors"
                onClick={() => toggleSort("created_at")}
              >
                {t("jobs.columns.created")}
                {sortKey === "created_at" ? (
                  sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                ) : (
                  <ArrowUpDown className="h-3 w-3 opacity-30" />
                )}
              </button>
            </TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredAndSorted.map((job) => (
            <React.Fragment key={job.id}>
              <TableRow
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
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
      )}
    </div>
  );
}
