"use client";
import { useQuery, useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { apiFetch } from "./api";
import type {
  TopScoresResponse,
  PriceHistoryResponse,
  IndicatorHistoryResponse,
  MacroLatestResponse,
  SectorsLatestResponse,
  StockScore,
  StockReport,
  TechnicalData,
  FundamentalData,
  TrackedStocksResponse,
  AdminJob,
  AdminJobsResponse,
  AdminJobDetail,
  TriggerResponse,
} from "./types";

export function useTopScores(limit = 20) {
  return useQuery({
    queryKey: ["scores", "top", limit],
    queryFn: () => apiFetch<TopScoresResponse>(`/api/scores/top?limit=${limit}`),
    staleTime: 5 * 60 * 1000,
  });
}

export function useStockScore(symbol: string) {
  return useQuery({
    queryKey: ["scores", symbol],
    queryFn: () => apiFetch<StockScore>(`/api/scores/${symbol}`),
    staleTime: 5 * 60 * 1000,
    enabled: !!symbol,
  });
}

export function useStockPrices(symbol: string, days = 365) {
  return useQuery({
    queryKey: ["prices", symbol, days],
    queryFn: () => apiFetch<PriceHistoryResponse>(`/api/prices/${symbol}?days=${days}`),
    staleTime: 60 * 60 * 1000, // 1 hour — prices don't change after market close
    enabled: !!symbol,
  });
}

export function useStockIndicators(symbol: string, days = 365) {
  return useQuery({
    queryKey: ["indicators", symbol, days],
    queryFn: () => apiFetch<IndicatorHistoryResponse>(`/api/prices/${symbol}/indicators?days=${days}`),
    staleTime: 60 * 60 * 1000,
    enabled: !!symbol,
  });
}

export function useStockTechnical(symbol: string) {
  return useQuery({
    queryKey: ["technical", symbol],
    queryFn: () => apiFetch<TechnicalData>(`/api/analysis/${symbol}/technical`),
    staleTime: 5 * 60 * 1000,
    enabled: !!symbol,
  });
}

export function useStockFundamental(symbol: string) {
  return useQuery({
    queryKey: ["fundamental", symbol],
    queryFn: () => apiFetch<FundamentalData>(`/api/analysis/${symbol}/fundamental`),
    staleTime: 5 * 60 * 1000,
    enabled: !!symbol,
  });
}

export function useStockReport(symbol: string) {
  return useQuery({
    queryKey: ["report", symbol],
    queryFn: () => apiFetch<StockReport>(`/api/reports/${symbol}`),
    staleTime: 5 * 60 * 1000,
    enabled: !!symbol,
  });
}

export function useMacroLatest() {
  return useQuery({
    queryKey: ["macro", "latest"],
    queryFn: () => apiFetch<MacroLatestResponse>(`/api/macro/latest`),
    staleTime: 60 * 60 * 1000,
  });
}

export function useSectorsLatest() {
  return useQuery({
    queryKey: ["sectors", "latest"],
    queryFn: () => apiFetch<SectorsLatestResponse>(`/api/sectors/latest`),
    staleTime: 60 * 60 * 1000,
  });
}

export function useTriggerPipeline() {
  return useMutation({
    mutationFn: () => apiFetch<Record<string, unknown>>(`/api/automation/run`, { method: "POST" }),
  });
}

// --- Admin: Stock Management (ADMIN-05) ---

export function useTrackedStocks() {
  return useQuery({
    queryKey: ["admin", "stocks"],
    queryFn: () => apiFetch<TrackedStocksResponse>("/api/admin/stocks"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAddStock() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      apiFetch<{ symbol: string; name: string | null; is_tracked: boolean; message: string }>(
        "/api/admin/stocks",
        { method: "POST", body: JSON.stringify({ symbol }) }
      ),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "stocks"] });
    },
  });
}

export function useRemoveStock() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      apiFetch<{ symbol: string; is_tracked: boolean; message: string }>(
        `/api/admin/stocks/${symbol}`,
        { method: "DELETE" }
      ),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "stocks"] });
    },
  });
}

// --- Admin: Pipeline Triggers (ADMIN-06) ---

export function useTriggerAdminCrawl() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbols: string[]) =>
      apiFetch<TriggerResponse>("/api/admin/crawl", {
        method: "POST",
        body: JSON.stringify({ symbols }),
      }),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "jobs"] });
    },
  });
}

export function useTriggerAdminAnalyze() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbols: string[]) =>
      apiFetch<TriggerResponse>("/api/admin/analyze", {
        method: "POST",
        body: JSON.stringify({ symbols }),
      }),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "jobs"] });
    },
  });
}

export function useTriggerAdminScore() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbols: string[]) =>
      apiFetch<TriggerResponse>("/api/admin/score", {
        method: "POST",
        body: JSON.stringify({ symbols }),
      }),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "jobs"] });
    },
  });
}

export function useTriggerAdminReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbols: string[]) =>
      apiFetch<TriggerResponse>("/api/admin/report", {
        method: "POST",
        body: JSON.stringify({ symbols }),
      }),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "jobs"] });
    },
  });
}

export function useTriggerAdminPipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbols: string[]) =>
      apiFetch<TriggerResponse>("/api/admin/pipeline", {
        method: "POST",
        body: JSON.stringify({ symbols }),
      }),
    retry: 2,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "jobs"] });
    },
  });
}

// --- Admin: Job Monitor (ADMIN-07) ---

export function useAdminJobs(limit = 50) {
  return useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: () => apiFetch<AdminJobsResponse>(`/api/admin/jobs?limit=${limit}`),
    staleTime: 10 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const hasActive = data.jobs.some(
        (j) => j.status === "running" || j.status === "pending"
      );
      return hasActive ? 3000 : false;
    },
  });
}

export function useAdminJobDetail(jobId: number | null) {
  return useQuery({
    queryKey: ["admin", "jobs", jobId],
    queryFn: () => apiFetch<AdminJobDetail>(`/api/admin/jobs/${jobId}`),
    enabled: !!jobId,
  });
}

// --- Admin: Cache Invalidation (Phase 12.1 D-01) ---

/** Extract symbols array from job params with type safety */
export function getJobSymbols(job: AdminJob): string[] {
  return Array.isArray(job.params?.symbols) ? (job.params.symbols as string[]) : [];
}

/** Invalidate caches affected by a completed job (per D-01: targeted by symbol + job type) */
export function invalidateForJob(queryClient: QueryClient, job: AdminJob): void {
  const symbols = getJobSymbols(job);

  switch (job.job_type) {
    case "crawl":
      for (const s of symbols) {
        queryClient.invalidateQueries({ queryKey: ["prices", s] });
        queryClient.invalidateQueries({ queryKey: ["indicators", s] });
      }
      queryClient.invalidateQueries({ queryKey: ["admin", "stocks"] });
      break;

    case "analyze":
      for (const s of symbols) {
        queryClient.invalidateQueries({ queryKey: ["technical", s] });
        queryClient.invalidateQueries({ queryKey: ["fundamental", s] });
      }
      break;

    case "score":
      for (const s of symbols) {
        queryClient.invalidateQueries({ queryKey: ["scores", s] });
      }
      queryClient.invalidateQueries({ queryKey: ["scores", "top"] });
      break;

    case "report":
      for (const s of symbols) {
        queryClient.invalidateQueries({ queryKey: ["report", s] });
      }
      break;

    case "pipeline":
      for (const s of symbols) {
        queryClient.invalidateQueries({ queryKey: ["prices", s] });
        queryClient.invalidateQueries({ queryKey: ["indicators", s] });
        queryClient.invalidateQueries({ queryKey: ["technical", s] });
        queryClient.invalidateQueries({ queryKey: ["fundamental", s] });
        queryClient.invalidateQueries({ queryKey: ["scores", s] });
        queryClient.invalidateQueries({ queryKey: ["report", s] });
      }
      queryClient.invalidateQueries({ queryKey: ["scores", "top"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stocks"] });
      break;
  }
}
