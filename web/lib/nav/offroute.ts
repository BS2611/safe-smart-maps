// A walker counts as off the line past 35 m, and back on it inside 20 m.

export const OFF_ROUTE_ENTER_M = 35;
export const OFF_ROUTE_EXIT_M = 20;

export function isOffRoute(crossTrackM: number, wasOff: boolean): boolean {
  if (!Number.isFinite(crossTrackM)) return wasOff;
  return crossTrackM > (wasOff ? OFF_ROUTE_EXIT_M : OFF_ROUTE_ENTER_M);
}
