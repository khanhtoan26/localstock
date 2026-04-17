"use client";
import { useQuery, useMutation } from "@tanstack/react-query";
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
