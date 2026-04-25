/**
 * HOSE Market Session Logic
 * Pure functions for Vietnam time extraction and HOSE phase calculation.
 * Extracted to a separate module for unit testability.
 */

export interface VNTimeParts {
  h: number;   // hour 0–23 in Vietnam time (UTC+7)
  m: number;   // minute 0–59
  dow: number; // day of week: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
}

export interface HosePhaseResult {
  isOpen: boolean;
  phase: string;    // "Pre-market" | "ATO" | "Morning" | "Lunch" | "Afternoon" | "ATC" | "Closed"
  pct: number;      // 0–100 progress through current phase (0 when closed)
  countdown: string; // e.g. "8m left" | "1h 15m left" | "Opens in 14h 30m"
}

// HOSE phase definitions — all times in UTC+7 (Asia/Ho_Chi_Minh)
// D-14: Pre-market 08:30–09:00, ATO 09:00–09:15, Morning 09:15–11:30,
//       Lunch 11:30–13:00, Afternoon 13:00–14:30, ATC 14:30–14:45
export const HOSE_PHASES = [
  { key: "Pre-market", startH: 8,  startM: 30, endH: 9,  endM: 0  },
  { key: "ATO",        startH: 9,  startM: 0,  endH: 9,  endM: 15 },
  { key: "Morning",    startH: 9,  startM: 15, endH: 11, endM: 30 },
  { key: "Lunch",      startH: 11, startM: 30, endH: 13, endM: 0  },
  { key: "Afternoon",  startH: 13, startM: 0,  endH: 14, endM: 30 },
  { key: "ATC",        startH: 14, startM: 30, endH: 14, endM: 45 },
] as const;

/**
 * Extract hour, minute, and day-of-week from a Date in Vietnam time (Asia/Ho_Chi_Minh).
 * Uses Intl.DateTimeFormat.formatToParts for reliable IANA timezone handling.
 * Avoids Pitfall 5: never do raw UTC offset math.
 */
export function getVNTimeParts(now: Date): VNTimeParts {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(now);

  const h = parseInt(parts.find((p) => p.type === "hour")!.value, 10);
  const m = parseInt(parts.find((p) => p.type === "minute")!.value, 10);

  // Day of week: get short weekday string then map to 0–6
  const dowStr = now.toLocaleString("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "short",
  });
  const dow = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(dowStr);

  return { h, m, dow };
}

/** Format minutes as "Xm" (< 60 min) or "Xh Ym" (≥ 60 min). */
function formatDuration(totalMinutes: number): string {
  if (totalMinutes < 60) return `${totalMinutes}m`;
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;
  return `${hours}h ${mins}m`;
}

/**
 * Calculate the number of minutes until next weekday 08:30 Vietnam time.
 * D-17: Weekends skip to Monday 08:30. Weekday evenings target next-day 08:30.
 */
function minutesUntilNextOpen(vnParts: VNTimeParts): number {
  const { h, m, dow } = vnParts;
  const currentMinutes = h * 60 + m;
  const openMinutes = 8 * 60 + 30; // 08:30

  let daysUntilOpen: number;
  // TODO: Add Vietnamese public holiday awareness (Tết, 30/4, 2/9, etc.) in future
  if (dow === 0) {
    // Sunday → Monday: 1 day
    daysUntilOpen = 1;
  } else if (dow === 6) {
    // Saturday → Monday: 2 days
    daysUntilOpen = 2;
  } else {
    // Weekday after market close: next calendar day (Mon–Thu → next day, Fri → Monday)
    daysUntilOpen = dow === 5 ? 3 : 1; // Friday → Monday (3 days), else next day
  }

  const minutesIntoNextDay = openMinutes; // 08:30 = 510 minutes from midnight
  const minutesRemainingToday = 24 * 60 - currentMinutes;
  return minutesRemainingToday + (daysUntilOpen - 1) * 24 * 60 + minutesIntoNextDay;
}

/**
 * Get current HOSE session phase and progress.
 * D-14: Phase boundaries in UTC+7. D-15: Mon–Fri only.
 * D-18: Progress bar 0% when closed.
 */
export function getCurrentHosePhase(now: Date): HosePhaseResult {
  const vnParts = getVNTimeParts(now);
  const { h, m, dow } = vnParts;
  const currentMinutes = h * 60 + m;

  // D-15: Weekends → always closed
  if (dow === 0 || dow === 6) {
    const minsUntil = minutesUntilNextOpen(vnParts);
    return {
      isOpen: false,
      phase: "Closed",
      pct: 0,
      countdown: `Opens in ${formatDuration(minsUntil)}`,
    };
  }

  // Check which phase the current VN time falls in
  for (const phase of HOSE_PHASES) {
    const phaseStartMinutes = phase.startH * 60 + phase.startM;
    const phaseEndMinutes = phase.endH * 60 + phase.endM;

    if (currentMinutes >= phaseStartMinutes && currentMinutes < phaseEndMinutes) {
      const elapsed = currentMinutes - phaseStartMinutes;
      const total = phaseEndMinutes - phaseStartMinutes;
      const pct = Math.round((elapsed / total) * 100);
      const remaining = phaseEndMinutes - currentMinutes;
      return {
        isOpen: true,
        phase: phase.key,
        pct,
        countdown: `${formatDuration(remaining)} left`,
      };
    }
  }

  // Before 08:30 on weekday or after 14:45 — closed
  const minsUntil = minutesUntilNextOpen(vnParts);
  return {
    isOpen: false,
    phase: "Closed",
    pct: 0,
    countdown: `Opens in ${formatDuration(minsUntil)}`,
  };
}
