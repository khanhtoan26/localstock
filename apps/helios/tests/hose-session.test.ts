import { describe, it, expect } from "vitest";
import { getVNTimeParts, getCurrentHosePhase } from "../src/components/layout/hose-session";

describe("getVNTimeParts", () => {
  it("UTC timestamp at 02:00 UTC converts to 09:00 VN time (UTC+7)", () => {
    // 2024-01-15 (Monday) 02:00 UTC = 2024-01-15 09:00 VN time
    const parts = getVNTimeParts(new Date("2024-01-15T02:00:00.000Z"));
    expect(parts.h).toBe(9);
    expect(parts.m).toBe(0);
    expect(parts.dow).toBe(1); // Monday
  });

  it("UTC midnight (00:00 UTC) converts to 07:00 VN time — not 00:00", () => {
    // 2024-01-15 (Monday) 00:00 UTC = 2024-01-15 07:00 VN time
    // Pitfall 5: midnight UTC is 07:00 in Vietnam (UTC+7), not midnight
    const parts = getVNTimeParts(new Date("2024-01-15T00:00:00.000Z"));
    expect(parts.h).toBe(7);
    expect(parts.m).toBe(0);
    expect(parts.dow).toBe(1); // Monday
  });
});

describe("getCurrentHosePhase", () => {
  it("08:45 VN on weekday → returns 'Pre-market' label", () => {
    // 2024-01-15 (Monday) 08:45 VN = 2024-01-15 01:45 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T01:45:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("Pre-market");
  });

  it("09:05 VN on weekday → returns 'ATO' label", () => {
    // 2024-01-15 (Monday) 09:05 VN = 2024-01-15 02:05 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T02:05:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("ATO");
  });

  it("10:00 VN on weekday → returns 'Morning' label", () => {
    // 2024-01-15 (Monday) 10:00 VN = 2024-01-15 03:00 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T03:00:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("Morning");
  });

  it("12:00 VN on weekday → returns 'Lunch' label", () => {
    // 2024-01-15 (Monday) 12:00 VN = 2024-01-15 05:00 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T05:00:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("Lunch");
  });

  it("13:30 VN on weekday → returns 'Afternoon' label", () => {
    // 2024-01-15 (Monday) 13:30 VN = 2024-01-15 06:30 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T06:30:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("Afternoon");
  });

  it("14:35 VN on weekday → returns 'ATC' label", () => {
    // 2024-01-15 (Monday) 14:35 VN = 2024-01-15 07:35 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T07:35:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("ATC");
  });

  it("15:00 VN on weekday → returns 'Closed' state, pct = 0", () => {
    // 2024-01-15 (Monday) 15:00 VN = 2024-01-15 08:00 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T08:00:00.000Z"));
    expect(result.isOpen).toBe(false);
    expect(result.phase).toBe("Closed");
    expect(result.pct).toBe(0);
  });

  it("Saturday → returns 'Closed' state, pct = 0", () => {
    // 2024-01-13 is a Saturday
    const result = getCurrentHosePhase(new Date("2024-01-13T06:00:00.000Z"));
    expect(result.isOpen).toBe(false);
    expect(result.phase).toBe("Closed");
    expect(result.pct).toBe(0);
  });

  it("Sunday → returns 'Closed' state, pct = 0", () => {
    // 2024-01-14 is a Sunday
    const result = getCurrentHosePhase(new Date("2024-01-14T06:00:00.000Z"));
    expect(result.isOpen).toBe(false);
    expect(result.phase).toBe("Closed");
    expect(result.pct).toBe(0);
  });

  it("active phase pct is between 0 and 100 (exclusive)", () => {
    // 2024-01-15 (Monday) 09:07 VN = 2024-01-15 02:07 UTC (mid-ATO phase)
    const result = getCurrentHosePhase(new Date("2024-01-15T02:07:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.pct).toBeGreaterThan(0);
    expect(result.pct).toBeLessThan(100);
  });

  it("progress pct is 50 at midpoint of Pre-market phase", () => {
    // Pre-market: 08:30–09:00, midpoint = 08:45 VN = 01:45 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T01:45:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("Pre-market");
    expect(result.pct).toBe(50);
  });

  it("progress pct is 50 at midpoint of Afternoon phase", () => {
    // Afternoon: 13:00–14:30, midpoint = 13:45 VN = 06:45 UTC
    const result = getCurrentHosePhase(new Date("2024-01-15T06:45:00.000Z"));
    expect(result.isOpen).toBe(true);
    expect(result.phase).toBe("Afternoon");
    expect(result.pct).toBe(50);
  });
});
