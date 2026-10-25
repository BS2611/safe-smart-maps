import {
  BAND_SYMBOL, BAND_TEXT, fetchedAgo, formatClock, formatDayClock, formatExtra, formatMeters,
  formatMinutes, formatPercent, isStale, LABEL_NAMES, scoreWord, viaText,
} from "./format";
import { findBannedWording } from "./wording";

describe("labels and wording", () => {
  it("shows friendly route names; the API value 'safest' is never displayed", () => {
    expect(LABEL_NAMES.safest).toBe("Most lit & active");
    expect(Object.values(LABEL_NAMES).join(" ")).not.toMatch(/safest/i);
  });

  it("all visible text passes the wording rules", () => {
    const all = [...Object.values(LABEL_NAMES), ...Object.values(BAND_TEXT), "Mostly lit and active", "Mixed"];
    expect(findBannedWording(all.join(" . "))).toEqual([]);
  });

  it("every band has a symbol so color is never the only signal", () => {
    expect(Object.keys(BAND_SYMBOL).sort()).toEqual(["green", "red", "unknown", "yellow"]);
    expect(new Set(Object.values(BAND_SYMBOL)).size).toBe(4);
  });

  it("describes scores in words, and unknown as not sure", () => {
    expect(scoreWord(80)).toBe("Mostly lit and active");
    expect(scoreWord(50)).toBe("Mixed");
    expect(scoreWord(10)).toBe("Fewer supports");
    expect(scoreWord(null)).toBe("Not sure");
  });
});

describe("number formatting", () => {
  it("formats minutes, extra minutes, meters and percent", () => {
    expect(formatMinutes(46.4)).toBe("46 min");
    expect(formatExtra(0)).toBe("Fastest time");
    expect(formatExtra(5.2)).toBe("+5 min vs fastest");
    expect(formatMeters(110)).toBe("110 m");
    expect(formatMeters(2400)).toBe("2.4 km");
    expect(formatPercent(86.4)).toBe("86%");
    expect(formatPercent(null)).toBe("Not sure");
  });

  it("builds the via text", () => {
    expect(viaText(["Polk St", "Market St"])).toBe("via Polk St & Market St");
    expect(viaText([])).toBe("");
  });
});

describe("times", () => {
  it("shows clock times in Los Angeles", () => {
    expect(formatClock("2026-10-25T03:00:00Z")).toBe("8:00 PM");
    expect(formatDayClock("2026-10-25T08:00:00Z")).toBe("Sun 1:00 AM");
  });

  it("describes data age and staleness", () => {
    const now = new Date("2026-10-24T22:00:00Z");
    expect(fetchedAgo("2026-10-24T21:56:00Z", now)).toBe("Fetched 4 min ago");
    expect(fetchedAgo("2026-10-24T22:00:00Z", now)).toBe("Fetched just now");
    expect(fetchedAgo("2026-10-24T19:00:00Z", now)).toBe("Fetched 3 h ago");
    expect(fetchedAgo(null, now)).toBe("Data time not available");
    expect(isStale("2026-10-24T19:00:00Z", now)).toBe(true);
    expect(isStale("2026-10-24T21:30:00Z", now)).toBe(false);
    expect(isStale(null, now)).toBe(false);
  });
});
