"use client";

import { Badge } from "@/components/ui/badge";

type JobStatus = "pending" | "running" | "completed" | "failed";

const statusStyles: Record<string, string> = {
  completed:
    "border-transparent text-[var(--stock-up)] bg-[color-mix(in_srgb,var(--stock-up)_10%,transparent)]",
  running:
    "border-transparent text-[var(--stock-warning)] bg-[color-mix(in_srgb,var(--stock-warning)_10%,transparent)]",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  if (status === "failed") {
    return <Badge variant="destructive">{status}</Badge>;
  }
  if (status === "pending") {
    return <Badge variant="secondary">{status}</Badge>;
  }
  return <Badge className={statusStyles[status]}>{status}</Badge>;
}
