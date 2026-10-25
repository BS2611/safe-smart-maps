// The trip the user is planning. Kept in sessionStorage only (cleared when the tab closes), which
// matches "This trip stays in this tab" on the welcome screen.
import type { Place } from "./types";

export const PRIORITY_OPTIONS = [
  { id: "lighting", label: "Lighting" },
  { id: "open_places", label: "Open places" },
  { id: "main_road", label: "Main roads" },
  { id: "help_points", label: "Help points" },
  { id: "transit", label: "Transit" },
] as const;

export const MAX_PRIORITIES = 2;
export const EXTRA_MINUTE_STEPS = [0, 5, 10, 15, 20] as const;

export type Settings = {
  maxExtraMinutes: number;
  withCompanion: boolean;
  priorities: string[];
};

export type Trip = {
  from: Place | null;
  to: Place | null;
  departISO: string | null; // null = "leave now"
  settings: Settings;
};

export const DEFAULT_SETTINGS: Settings = { maxExtraMinutes: 10, withCompanion: false, priorities: [] };
export const EMPTY_TRIP: Trip = { from: null, to: null, departISO: null, settings: DEFAULT_SETTINGS };

export function togglePriority(current: string[], id: string): string[] {
  if (current.includes(id)) return current.filter((p) => p !== id);
  if (current.length >= MAX_PRIORITIES) return current;
  return [...current, id];
}

export function isReady(trip: Trip): boolean {
  return Boolean(trip.from && trip.to && !(trip.from.lat === trip.to.lat && trip.from.lng === trip.to.lng));
}

export function departDate(trip: Trip, now: Date = new Date()): Date {
  return trip.departISO ? new Date(trip.departISO) : now;
}

/** Request body for POST /v1/routes. Locations are sent only here and never stored by us. */
export function toRequestBody(trip: Trip, now: Date = new Date()) {
  if (!trip.from || !trip.to) throw new Error("Trip needs a start and a destination");
  return {
    from: { lat: trip.from.lat, lng: trip.from.lng },
    to: { lat: trip.to.lat, lng: trip.to.lng },
    depart_time: departDate(trip, now).toISOString(),
    settings: {
      max_extra_minutes: trip.settings.maxExtraMinutes,
      with_companion: trip.settings.withCompanion,
      priorities: trip.settings.priorities,
    },
  };
}

const KEY = "ssm.trip.v1";

export function loadTrip(storage: Pick<Storage, "getItem"> | undefined = safeStorage()): Trip {
  try {
    const raw = storage?.getItem(KEY);
    if (!raw) return EMPTY_TRIP;
    const parsed = JSON.parse(raw) as Partial<Trip>;
    return {
      from: parsed.from ?? null,
      to: parsed.to ?? null,
      departISO: parsed.departISO ?? null,
      settings: { ...DEFAULT_SETTINGS, ...(parsed.settings ?? {}) },
    };
  } catch {
    return EMPTY_TRIP;
  }
}

export function saveTrip(trip: Trip, storage: Pick<Storage, "setItem"> | undefined = safeStorage()): void {
  try {
    storage?.setItem(KEY, JSON.stringify(trip));
  } catch {
    // storage blocked (private window): the app still works, it just forgets on refresh
  }
}

export function clearTrip(storage: Pick<Storage, "removeItem"> | undefined = safeStorage()): void {
  try {
    storage?.removeItem(KEY);
  } catch {
    // ignore
  }
}

function safeStorage(): Storage | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.sessionStorage;
  } catch {
    return undefined;
  }
}
