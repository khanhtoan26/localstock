"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";
import { ProgressTrack, ProgressIndicator } from "@/components/ui/progress";
import { getCurrentHosePhase } from "./hose-session";

// SSR hydration guard — same pattern as theme-toggle.tsx.
// Required because Date.now() differs between server and client renders.
const emptySubscribe = () => () => {};
function useMounted() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}

export function MarketSessionBar() {
  const t = useTranslations("sessionBar");
  const [now, setNow] = useState<Date>(() => new Date());
  const mounted = useMounted();

  // D-13: Refresh every 60 seconds
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  // SSR guard: render nothing on server to avoid hydration mismatch
  if (!mounted) {
    return <div className="hidden sm:flex w-[248px]" aria-hidden="true" />;
  }

  const session = getCurrentHosePhase(now);

  // D-18: Closed state — single centered text, progress bar at 0%
  if (!session.isOpen) {
    const countdownTime = session.countdown.replace("Opens in ", "");
    return (
      <div className="hidden sm:flex items-center justify-center flex-1">
        <span className="text-xs text-muted-foreground">
          {/* D-16: "● Closed · Opens in Xh Ym" */}
          ● {t("closed")} · {t("opensIn", { time: countdownTime })}
        </span>
      </div>
    );
  }

  // D-12: Active state — phase label | progress bar | countdown
  // Phase key to i18n key mapping
  const phaseI18nKey = {
    "Pre-market": "preMarket",
    "ATO": "ato",
    "Morning": "morning",
    "Lunch": "lunch",
    "Afternoon": "afternoon",
    "ATC": "atc",
  } as const;
  const i18nKey = phaseI18nKey[session.phase as keyof typeof phaseI18nKey] ?? "closed";

  const countdownTime = session.countdown.replace(" left", "");

  return (
    <div className="hidden sm:flex items-center justify-center flex-1">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {/* Phase label: fixed width 80px, right-aligned to keep bar centered */}
        <span className="w-20 text-right font-medium text-foreground">
          {t(i18nKey)}
        </span>
        {/* Progress track: 96px wide, 4px tall, token-based colors */}
        <ProgressTrack className="w-24 h-1">
          <ProgressIndicator style={{ width: `${session.pct}%` }} />
        </ProgressTrack>
        {/* Countdown: fixed width 64px, left-aligned */}
        <span className="w-16 text-muted-foreground">
          {t("left", { time: countdownTime })}
        </span>
      </div>
    </div>
  );
}
