"use client";

import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ReportProgress } from "./report-progress";
import { ReportPreview } from "./report-preview";

export type SheetState =
  | { status: "closed" }
  | { status: "generating"; symbols: string[]; jobId: number }
  | { status: "completed"; symbols: string[]; lastSymbol: string }
  | { status: "failed"; symbols: string[]; failedSymbol: string; error?: string }
  | { status: "minimized"; symbols: string[]; jobId: number };

interface ReportGenerationSheetProps {
  sheetState: SheetState;
  onStateChange: (state: SheetState) => void;
}

export function ReportGenerationSheet({
  sheetState,
  onStateChange,
}: ReportGenerationSheetProps) {
  const t = useTranslations("admin");

  const isOpen = sheetState.status !== "closed" && sheetState.status !== "minimized";
  const symbols = isOpen ? sheetState.symbols : [];

  return (
    <Sheet
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          if (sheetState.status === "generating") {
            onStateChange({ status: "minimized", symbols: sheetState.symbols, jobId: sheetState.jobId });
          } else {
            onStateChange({ status: "closed" });
          }
        }
      }}
    >
      <SheetContent side="right" className="sm:max-w-lg flex flex-col">
        <SheetHeader>
          <SheetTitle>{t("report.sheetTitle")}</SheetTitle>
          <SheetDescription>
            {symbols.length === 1 ? (
              <>
                {t("report.sheetDescriptionSingle", { symbol: symbols[0] })}{" "}
                <Badge variant="outline">{symbols[0]}</Badge>
              </>
            ) : symbols.length > 1 ? (
              t("report.sheetDescriptionBatch", { count: symbols.length })
            ) : null}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 px-4 py-4">
          {sheetState.status === "generating" && (
            <ReportProgress
              jobStatus="running"
              currentSymbol={sheetState.symbols[0]}
            />
          )}

          {sheetState.status === "completed" && (
            <ReportPreview symbol={sheetState.lastSymbol} />
          )}

          {sheetState.status === "failed" && (
            <div className="flex flex-col items-center gap-3 py-8">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <h3 className="text-base font-medium text-center">
                {t("report.errorHeading")}
              </h3>
              <p className="text-sm text-muted-foreground text-center">
                {t("report.errorGeneric")}
              </p>
            </div>
          )}
        </ScrollArea>

        {sheetState.status === "completed" && (
          <SheetFooter className="flex-row justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => onStateChange({ status: "closed" })}
            >
              {t("report.close")}
            </Button>
            <Button
              onClick={() =>
                window.open(`/stocks/${sheetState.lastSymbol}`, "_blank")
              }
            >
              {t("report.viewStockPage")}
            </Button>
          </SheetFooter>
        )}

        {sheetState.status === "failed" && (
          <SheetFooter className="flex-row justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => onStateChange({ status: "closed" })}
            >
              {t("report.close")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => onStateChange({ status: "closed" })}
            >
              {t("report.retry")}
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  );
}
