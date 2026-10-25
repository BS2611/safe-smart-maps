// Phone check-ins during a walk. A paired watch is the intended buzz target.
// No Capacitor wearable plugin: the Wear OS app is a separate project, and a native
// dependency here could break the Android build. pingPairedWatch is the seam.

import { darkestSegmentIndex, nearestSegmentIndex, type LngLat } from "@/lib/streetview/geo";

export const CHECK_IN_INTERVAL_MS = 3 * 60 * 1000;

export type CheckInReason = "interval" | "darkest";

export type CheckInDecision = {
  /** A new prompt. The caller buzzes once. Null when nothing new should open. */
  open: CheckInReason | null;
  darkestLatched: boolean;
};

/** Lowest known score, and the walker is on that stretch. Unknown scores are skipped. */
export function onDarkestStretch(
  segments: { score: number | null; start: LngLat; end: LngLat }[],
  lng: number,
  lat: number,
): boolean {
  const darkest = darkestSegmentIndex(segments);
  if (darkest === null) return false;
  return nearestSegmentIndex(segments, lng, lat) === darkest;
}

export function evaluateCheckIn(input: {
  enabled: boolean;
  nowMs: number;
  lastAckMs: number;
  intervalMs: number;
  onDarkest: boolean;
  /** A darkest prompt already fired and the walker has not left that stretch. */
  darkestLatched: boolean;
  showing: boolean;
}): CheckInDecision {
  if (!input.enabled) return { open: null, darkestLatched: false };
  const stillLatched = input.onDarkest ? input.darkestLatched : false;
  if (input.showing) {
    return { open: null, darkestLatched: input.onDarkest ? true : stillLatched };
  }
  if (input.onDarkest && !input.darkestLatched) {
    return { open: "darkest", darkestLatched: true };
  }
  if (input.intervalMs > 0 && input.nowMs - input.lastAckMs >= input.intervalMs) {
    return { open: "interval", darkestLatched: input.onDarkest ? true : stillLatched };
  }
  return { open: null, darkestLatched: stillLatched };
}

/** Always "unavailable" until a small watch bridge exists. Does not import a native plugin. */
export function pingPairedWatch(reason: CheckInReason): "unavailable" {
  void reason;
  return "unavailable";
}
