// A heads-up for the stretch just ahead. Never a safety claim.
import { BAND_TEXT } from "@/lib/format";
import type { Route, Segment } from "@/lib/types";

import { routeLength } from "./geo";

export type StretchAlert = {
  kind: "low" | "gap";
  title: string;
  detail: string;
};

const GAP = /no open places/i;

function isGap(seg: Segment): boolean {
  if (seg.factors.open_places === 0) return true;
  return seg.reasons.some((reason) => GAP.test(reason));
}

function isLow(seg: Segment): boolean {
  return seg.band === "red" || seg.band === "yellow";
}

/** The stretch `lookAheadM` past the walker, if it scores low or has no open places. */
export function alertAhead(route: Route, alongM: number, lookAheadM = 40): StretchAlert | null {
  const segments = route.segments;
  if (!segments.length) return null;
  const geom = routeLength(route.geometry.coordinates);
  const segTotal = segments.reduce((sum, seg) => sum + Math.max(0, seg.length_m), 0);
  const scaled = geom > 0 && segTotal > 0 ? alongM * (segTotal / geom) : alongM;
  const target = scaled + lookAheadM;
  let cum = 0;
  let index = segments.length - 1;
  for (let i = 0; i < segments.length; i++) {
    cum += Math.max(0, segments[i].length_m);
    if (cum >= target) {
      index = i;
      break;
    }
  }
  const seg = segments[index];
  const gap = isGap(seg);
  const low = isLow(seg);
  if (!gap && !low) return null;
  const score = seg.score === null ? "Not sure" : `${Math.round(seg.score)} / 100`;
  if (gap && low) {
    return {
      kind: "gap",
      title: `Next stretch: ${BAND_TEXT[seg.band]}`,
      detail: `Open places thin out ahead. Score ${score}.`,
    };
  }
  if (gap) {
    return { kind: "gap", title: "Open places thin out ahead", detail: `Score ${score}.` };
  }
  return {
    kind: "low",
    title: `Next stretch: ${BAND_TEXT[seg.band]}`,
    detail: `Score ${score}.`,
  };
}
