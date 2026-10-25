// Turn-by-turn steps. Mapbox Directions steps when we have them; otherwise turns in the geometry.
import { bearing, haversine, projectOntoRoute, routeLength, signedDelta, type LngLat } from "./geo";
import { isOffRoute } from "./offroute";

export type NavStep = {
  instruction: string;
  street: string | null;
  modifier: string | null;
  type: string;
  location: LngLat;
  distanceM: number;
  durationS: number;
};

export type Progress = {
  stepIndex: number;
  instruction: string;
  street: string | null;
  distanceToManeuverM: number;
  remainingDistanceM: number;
  remainingFraction: number;
  crossTrackM: number;
  alongM: number;
  offRoute: boolean;
  bearing: number;
  snapped: LngLat;
};

const TURN_DEG = 40;
/** Switch to the next maneuver once the walker is this close to it. */
export const ADVANCE_M = 12;

function modifierName(delta: number): string {
  const mag = Math.abs(delta);
  const side = delta > 0 ? "right" : "left";
  if (mag >= 150) return "uturn";
  if (mag >= 100) return `sharp ${side}`;
  if (mag >= TURN_DEG) return side;
  return "straight";
}

function turnText(modifier: string | null): string {
  switch (modifier) {
    case "left": return "Turn left";
    case "right": return "Turn right";
    case "slight left": return "Bear left";
    case "slight right": return "Bear right";
    case "sharp left": return "Turn sharp left";
    case "sharp right": return "Turn sharp right";
    case "uturn": return "Make a U-turn";
    case "straight": return "Continue straight";
    default: return "Continue";
  }
}

function cardinal(degrees: number): string {
  const names = ["north", "east", "south", "west"];
  return names[Math.round(normalizePositive(degrees) / 90) % 4];
}

function normalizePositive(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

function pathDistance(coords: LngLat[], from: number, to: number): number {
  let total = 0;
  for (let i = from + 1; i <= to && i < coords.length; i++) total += haversine(coords[i - 1], coords[i]);
  return total;
}

/** Maneuvers from corners in the line. Street names are unknown until Mapbox steps fill them. */
export function stepsFromGeometry(coords: LngLat[]): NavStep[] {
  if (coords.length < 2) return [];
  const turns: number[] = [];
  for (let i = 1; i < coords.length - 1; i++) {
    const delta = signedDelta(bearing(coords[i - 1], coords[i]), bearing(coords[i], coords[i + 1]));
    if (Math.abs(delta) >= TURN_DEG) turns.push(i);
  }
  const indices = [0, ...turns, coords.length - 1];
  return indices.map((at, k) => {
    const nextAt = indices[Math.min(k + 1, indices.length - 1)];
    const type = k === 0 ? "depart" : k === indices.length - 1 ? "arrive" : "turn";
    const before = at === 0 ? bearing(coords[0], coords[1]) : bearing(coords[Math.max(0, at - 1)], coords[at]);
    const after = at >= coords.length - 1 ? before : bearing(coords[at], coords[Math.min(at + 1, coords.length - 1)]);
    const modifier = type === "arrive" ? null : type === "depart" ? cardinal(after) : modifierName(signedDelta(before, after));
    const distanceM = type === "arrive" ? 0 : pathDistance(coords, at, nextAt);
    return {
      instruction: type === "arrive" ? "Arrive" : type === "depart" ? "Head out" : turnText(modifier),
      street: null,
      modifier,
      type,
      location: coords[at],
      distanceM,
      durationS: distanceM / 1.4,
    };
  });
}

function oneMapboxStep(value: unknown): NavStep | null {
  if (!value || typeof value !== "object") return null;
  const step = value as {
    name?: unknown;
    distance?: unknown;
    duration?: unknown;
    maneuver?: { type?: unknown; modifier?: unknown; instruction?: unknown; location?: unknown };
  };
  const loc = step.maneuver?.location;
  if (!Array.isArray(loc) || loc.length < 2 || typeof loc[0] !== "number" || typeof loc[1] !== "number") return null;
  const type = typeof step.maneuver?.type === "string" ? step.maneuver.type : "continue";
  const modifier = typeof step.maneuver?.modifier === "string" ? step.maneuver.modifier : null;
  const named = typeof step.name === "string" && step.name.trim() ? step.name.trim() : null;
  const given = typeof step.maneuver?.instruction === "string" ? step.maneuver.instruction.trim() : "";
  const instruction = given || (type === "arrive" ? "Arrive" : type === "depart" ? "Head out" : turnText(modifier));
  return {
    instruction,
    street: named,
    modifier,
    type,
    location: [loc[0], loc[1]],
    distanceM: typeof step.distance === "number" ? step.distance : 0,
    durationS: typeof step.duration === "number" ? step.duration : 0,
  };
}

/** Parse a Mapbox Directions response. Empty or unexpected JSON returns no steps. */
export function stepsFromMapbox(body: unknown): NavStep[] {
  if (!body || typeof body !== "object") return [];
  const routes = (body as { routes?: unknown }).routes;
  if (!Array.isArray(routes) || !routes[0] || typeof routes[0] !== "object") return [];
  const legs = (routes[0] as { legs?: unknown }).legs;
  if (!Array.isArray(legs)) return [];
  const steps: NavStep[] = [];
  for (const leg of legs) {
    const raw = (leg as { steps?: unknown }).steps;
    if (!Array.isArray(raw)) continue;
    for (const step of raw) {
      const parsed = oneMapboxStep(step);
      if (parsed) steps.push(parsed);
    }
  }
  return steps;
}

export function sampleCoords(coords: LngLat[], max: number): LngLat[] {
  if (coords.length <= max) return coords.slice();
  const out: LngLat[] = [];
  const last = coords.length - 1;
  for (let i = 0; i < max; i++) {
    const point = coords[Math.round((i * last) / (max - 1))];
    const prev = out[out.length - 1];
    if (!prev || prev[0] !== point[0] || prev[1] !== point[1]) out.push(point);
  }
  return out;
}

/** Browser Mapbox Directions steps for this line. Null when there is no token or the request fails. */
export async function fetchMapboxSteps(coords: LngLat[], token: string, signal?: AbortSignal): Promise<NavStep[] | null> {
  const key = token.trim();
  if (!key || coords.length < 2) return null;
  const path = sampleCoords(coords, 25).map(([lng, lat]) => `${lng},${lat}`).join(";");
  const url = `https://api.mapbox.com/directions/v5/mapbox/walking/${path}?alternatives=false&geometries=geojson&overview=full&steps=true&access_token=${encodeURIComponent(key)}`;
  try {
    const res = await fetch(url, { signal });
    if (!res.ok) return null;
    const steps = stepsFromMapbox(await res.json() as unknown);
    return steps.length ? steps : null;
  } catch {
    return null;
  }
}

function maneuverCopy(steps: NavStep[], upcoming: number, distanceToM: number): { instruction: string; street: string | null } {
  const step = steps[upcoming];
  if (!step) return { instruction: "Continue", street: null };
  if (step.type === "arrive" && distanceToM > 25) {
    const current = steps[upcoming - 1];
    const instruction = !current || current.type === "depart" ? "Head out" : "Continue straight";
    return { instruction, street: current?.street ?? null };
  }
  const current = steps[Math.max(0, upcoming - 1)];
  return { instruction: step.instruction, street: step.street ?? current?.street ?? null };
}

/**
 * Which maneuver is next, how far it is, and whether the walker has left the line.
 * `wasOff` keeps the off-route flag until they are clearly back.
 */
export function navigationProgress(coords: LngLat[], steps: NavStep[], point: LngLat, wasOff = false): Progress {
  const usable = steps.length ? steps : stepsFromGeometry(coords);
  const proj = coords.length ? projectOntoRoute(coords, point) : {
    alongM: 0, crossTrackM: 0, snapped: point, bearing: 0, segmentIndex: 0,
  };
  const total = routeLength(coords);
  const starts = usable.map((step) => (coords.length ? projectOntoRoute(coords, step.location).alongM : 0));
  let upcoming = usable.length - 1;
  for (let i = 0; i < usable.length; i++) {
    if (starts[i] > proj.alongM + ADVANCE_M) {
      upcoming = i;
      break;
    }
  }
  const target = upcoming >= 0 ? starts[upcoming] : total;
  const distanceToManeuverM = Math.max(0, target - proj.alongM);
  const remainingDistanceM = Math.max(0, total - proj.alongM);
  const copy = maneuverCopy(usable, Math.max(0, upcoming), distanceToManeuverM);
  return {
    stepIndex: Math.max(0, upcoming),
    instruction: copy.instruction,
    street: copy.street,
    distanceToManeuverM,
    remainingDistanceM,
    remainingFraction: total > 0 ? remainingDistanceM / total : 0,
    crossTrackM: proj.crossTrackM,
    alongM: proj.alongM,
    offRoute: isOffRoute(proj.crossTrackM, wasOff),
    bearing: proj.bearing,
    snapped: proj.snapped,
  };
}
