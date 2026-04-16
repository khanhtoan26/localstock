"use client";
import { useTopScores, useTriggerPipeline } from "@/lib/queries";
import { StockTable } from "@/components/rankings/stock-table";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";

export default function RankingsPage() {
  const { data, isLoading, isError } = useTopScores(50);
  const triggerPipeline = useTriggerPipeline();

  if (isLoading) {
    return (
      <div>
        <h1 className="text-xl font-semibold mb-6">Xếp Hạng Cổ Phiếu</h1>
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h1 className="text-xl font-semibold mb-6">Xếp Hạng Cổ Phiếu</h1>
        <ErrorState />
      </div>
    );
  }

  if (!data || data.count === 0) {
    return (
      <div>
        <h1 className="text-xl font-semibold mb-6">Xếp Hạng Cổ Phiếu</h1>
        <EmptyState
          body="Chưa có kết quả xếp hạng. Chạy pipeline phân tích để bắt đầu."
          ctaLabel="Chạy Pipeline"
          onCtaClick={() => triggerPipeline.mutate()}
        />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">Xếp Hạng Cổ Phiếu</h1>
      <StockTable data={data.stocks} />
    </div>
  );
}
