"use client";

import { useRef, useEffect } from "react";
import { useAdminJobs } from "@/lib/queries";
import type { AdminJob } from "@/lib/types";

export interface JobTransition {
  job: AdminJob;
  previousStatus: string;
}

/**
 * Detects job status transitions from running/pending to completed/failed
 * by diffing the current poll data against the previous snapshot.
 *
 * Skips the initial data load to avoid false-positive toasts for historical jobs.
 * Calls onTransition for each detected transition (per D-02).
 */
export function useJobTransitions(
  onTransition: (transition: JobTransition) => void
) {
  const { data } = useAdminJobs();
  const prevJobsRef = useRef<Map<number, string>>(new Map());
  const isInitialLoadRef = useRef(true);

  useEffect(() => {
    if (!data?.jobs) return;

    const currentMap = new Map<number, string>();
    for (const job of data.jobs) {
      currentMap.set(job.id, job.status);
    }

    // Skip transition detection on first data arrival (Pitfall 2)
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      prevJobsRef.current = currentMap;
      return;
    }

    // Collect all transitions first, then fire callbacks (Pitfall 4)
    const transitions: JobTransition[] = [];
    for (const job of data.jobs) {
      const prevStatus = prevJobsRef.current.get(job.id);
      if (
        prevStatus &&
        prevStatus !== job.status &&
        (job.status === "completed" || job.status === "failed")
      ) {
        transitions.push({ job, previousStatus: prevStatus });
      }
    }

    prevJobsRef.current = currentMap;

    for (const t of transitions) {
      onTransition(t);
    }
  }, [data, onTransition]);
}
