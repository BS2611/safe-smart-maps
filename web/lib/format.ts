// Display helpers. Wording follows AGENTS.md: never "safe"; the API value "safest" shows as
// "Most lit & active" (DECISIONS 2026-10-24 11:40).
import type { Band, Label } from "./types";

export const TIME_ZONE = "America/Los_Angeles"; // the demo area (San Francisco)

export const LABEL_NAMES: Record<Label, string> = {
  safest: "Most lit & active",
  balanced: "Balanced",
  fastest: "Fastest",
};

// CSS accent class per route label (kept here so UI source never spells the API value).
export const LABEL_CLASS: Record<Label, string> = { safest: "most-lit", balanced: "balanced", fastest: "fastest" };

export const BAND_TEXT: Record<Band, string> = {
  green: "Better lit & active",
  yellow: "Mixed",
  red: "Fewer supports",
  unknown: "Not sure",
};

// Color is never the only signal: every band also has a symbol (brief section 3).
export const BAND_SYMBOL: Record<Band, string> = { green: "✓", yellow: "–", red: "▲", unknown: "?" };

export function scoreWord(score: number | null): string {
  if (score === null) return "Not sure";
  if (score >= 70) return "Mostly lit and active";
  if (score >= 45) return "Mixed";
  return "Fewer supports";
}

export function formatMinutes(min: number): string {
  return `${Math.round(min)} min`;
}

export function formatExtra(extra: number): string {
  const rounded = Math.round(extra);
  return rounded <= 0 ? "Fastest time" : `+${rounded} min vs fastest`;
}

export function formatMeters(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

export function formatPercent(value: number | null): string {
  return value === null ? "Not sure" : `${Math.round(value)}%`;
}

export function formatClock(iso: string, timeZone: string = TIME_ZONE): string {
  return new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone }).format(new Date(iso));
}

export function formatDayClock(iso: string, timeZone: string = TIME_ZONE): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short", hour: "numeric", minute: "2-digit", timeZone,
  }).format(new Date(iso));
}

/** "Fetched 4 min ago" / "Fetched just now" / "Fetched 3 h ago". */
export function fetchedAgo(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "Data time not available";
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return "Fetched just now";
  if (minutes < 60) return `Fetched ${minutes} min ago`;
  return `Fetched ${Math.round(minutes / 60)} h ago`;
}

export function isStale(iso: string | null, now: Date = new Date(), maxHours = 2): boolean {
  if (!iso) return false;
  return now.getTime() - new Date(iso).getTime() > maxHours * 3600 * 1000;
}

export function viaText(via: string[]): string {
  return via.length ? `via ${via.join(" & ")}` : "";
}
