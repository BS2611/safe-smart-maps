import { fromLocalInput, hourIn, tonightTimes, toLocalInput, zonedDate } from "./time";

describe("zonedDate (Los Angeles)", () => {
  it("handles daylight saving time (UTC-7)", () => {
    expect(zonedDate(2026, 10, 24, 20, 0).toISOString()).toBe("2026-10-25T03:00:00.000Z");
  });

  it("handles standard time after the change on 1 Nov 2026 (UTC-8)", () => {
    expect(zonedDate(2026, 11, 2, 20, 0).toISOString()).toBe("2026-11-03T04:00:00.000Z");
  });

  it("is correct across the day the clocks change", () => {
    // 1 AM on 1 Nov 2026 is still daylight time (the change happens at 2 AM).
    expect(zonedDate(2026, 11, 1, 1, 0).toISOString()).toBe("2026-11-01T08:00:00.000Z");
  });
});

describe("tonightTimes", () => {
  it("on Saturday afternoon: 8 PM tonight and 1 AM after midnight", () => {
    const t = tonightTimes(new Date("2026-10-24T22:30:00Z")); // 3:30 PM Saturday
    expect(t.eightPm.toISOString()).toBe("2026-10-25T03:00:00.000Z");
    expect(t.oneAm.toISOString()).toBe("2026-10-25T08:00:00.000Z");
  });

  it("at 2 AM it is still tonight (the 8 PM was yesterday)", () => {
    const t = tonightTimes(new Date("2026-10-25T09:00:00Z")); // 2 AM Sunday
    expect(t.eightPm.toISOString()).toBe("2026-10-25T03:00:00.000Z");
    expect(t.oneAm.toISOString()).toBe("2026-10-25T08:00:00.000Z");
  });

  it("from 5 AM the next night starts", () => {
    const t = tonightTimes(new Date("2026-10-25T12:30:00Z")); // 5:30 AM Sunday
    expect(t.eightPm.toISOString()).toBe("2026-10-26T03:00:00.000Z");
  });
});

describe("datetime-local conversion", () => {
  it("round-trips a Los Angeles wall-clock time", () => {
    const d = fromLocalInput("2026-10-24T20:00");
    expect(d?.toISOString()).toBe("2026-10-25T03:00:00.000Z");
    expect(toLocalInput(d as Date)).toBe("2026-10-24T20:00");
  });

  it("rejects bad input", () => {
    expect(fromLocalInput("")).toBeNull();
    expect(fromLocalInput("tonight")).toBeNull();
  });

  it("reports the hour on the Los Angeles clock", () => {
    expect(hourIn(new Date("2026-10-25T08:00:00Z"))).toBe(1);
    expect(hourIn(new Date("2026-10-25T03:00:00Z"))).toBe(20);
  });
});
