// Numbers derived from a route for the detail and comparison screens (pure).
import { formatPercent, formatMeters, LABEL_NAMES } from "./format";
import type { Route, RoutesResponse } from "./types";

/** Length-weighted average of each factor over the segments where it is known; null if never known. */
export function averageFactors(route: Route): Record<string, number | null> {
  const sums: Record<string, { total: number; length: number }> = {};
  const names = new Set(route.segments.flatMap((s) => Object.keys(s.factors)));
  for (const n of names) sums[n] = { total: 0, length: 0 };
  for (const seg of route.segments) {
    for (const [name, value] of Object.entries(seg.factors)) {
      if (value !== null) {
        sums[name].total += value * seg.length_m;
        sums[name].length += seg.length_m;
      }
    }
  }
  const out: Record<string, number | null> = {};
  for (const [n, s] of Object.entries(sums)) out[n] = s.length > 0 ? Math.round(s.total / s.length) : null;
  return out;
}

export function primaryRoute(data: RoutesResponse): Route {
  return data.routes[0];
}

export type Comparison = {
  routeChanged: boolean;
  coverageEarly: number | null;
  coverageLate: number | null;
  coverageDelta: number | null;
  openEarly: number | null;
  openLate: number | null;
  headline: string;
  detail: string;
};

/** What changes between two times for the primary (best) route. Honest when data is missing. */
export function compareTimes(early: RoutesResponse, late: RoutesResponse): Comparison {
  const a = primaryRoute(early);
  const b = primaryRoute(late);
  const ca = a.continuity.coverage_pct;
  const cb = b.continuity.coverage_pct;
  const delta = ca !== null && cb !== null ? Math.round(cb - ca) : null;
  const routeChanged = a.route_id !== b.route_id;
  const openEarly = a.open_places_count;
  const openLate = b.open_places_count;

  let headline: string;
  if (delta === null) headline = "We are not sure how the two times compare, because some data was missing.";
  else if (delta <= -5) headline = `Coverage drops from ${formatPercent(ca)} to ${formatPercent(cb)}.`;
  else if (delta >= 5) headline = `Coverage rises from ${formatPercent(ca)} to ${formatPercent(cb)}.`;
  else headline = "Conditions are about the same at both times.";

  const bits: string[] = [];
  if (routeChanged) {
    bits.push(`${LABEL_NAMES[b.label]} changes to a different route${b.via.length ? ` (via ${b.via.join(" & ")})` : ""}.`);
  } else {
    bits.push("The same route is recommended at both times.");
  }
  if (openEarly !== null && openLate !== null && openEarly > openLate) {
    bits.push(`${openEarly - openLate} fewer open places along the way.`);
  }
  if (b.continuity.longest_gap_m > a.continuity.longest_gap_m) {
    bits.push(`The longest empty stretch grows from ${formatMeters(a.continuity.longest_gap_m)} to ${formatMeters(b.continuity.longest_gap_m)}.`);
  }
  return {
    routeChanged, coverageEarly: ca, coverageLate: cb, coverageDelta: delta,
    openEarly, openLate, headline, detail: bits.join(" "),
  };
}
