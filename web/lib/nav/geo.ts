// Distances and bearings for walking navigation. Coordinates are [lng, lat].

export type LngLat = [number, number];

const EARTH_M = 6_371_000;

export function normalizeDegrees(deg: number): number {
  if (!Number.isFinite(deg)) return 0;
  return ((deg % 360) + 360) % 360;
}

export function signedDelta(fromDeg: number, toDeg: number): number {
  return ((toDeg - fromDeg + 540) % 360) - 180;
}

export function haversine(a: LngLat, b: LngLat): number {
  const φ1 = (a[1] * Math.PI) / 180;
  const φ2 = (b[1] * Math.PI) / 180;
  const dφ = ((b[1] - a[1]) * Math.PI) / 180;
  const dλ = ((b[0] - a[0]) * Math.PI) / 180;
  const h = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2;
  return 2 * EARTH_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Degrees clockwise from north, from `a` to `b`. */
export function bearing(a: LngLat, b: LngLat): number {
  const φ1 = (a[1] * Math.PI) / 180;
  const φ2 = (b[1] * Math.PI) / 180;
  const dλ = ((b[0] - a[0]) * Math.PI) / 180;
  const y = Math.sin(dλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(dλ);
  return normalizeDegrees((Math.atan2(y, x) * 180) / Math.PI);
}

export function destination(origin: LngLat, distanceM: number, bearingDeg: number): LngLat {
  const δ = distanceM / EARTH_M;
  const θ = (bearingDeg * Math.PI) / 180;
  const φ1 = (origin[1] * Math.PI) / 180;
  const λ1 = (origin[0] * Math.PI) / 180;
  const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
  const λ2 = λ1 + Math.atan2(
    Math.sin(θ) * Math.sin(δ) * Math.cos(φ1),
    Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2),
  );
  const lng = ((λ2 * 180) / Math.PI + 540) % 360 - 180;
  return [lng, (φ2 * 180) / Math.PI];
}

/** East/north meters of `point` relative to `origin`. */
export function toMeters(origin: LngLat, point: LngLat): [number, number] {
  const latScale = Math.cos((origin[1] * Math.PI) / 180);
  const x = (point[0] - origin[0]) * latScale * (Math.PI / 180) * EARTH_M;
  const y = (point[1] - origin[1]) * (Math.PI / 180) * EARTH_M;
  return [x, y];
}

export function routeLength(coords: LngLat[]): number {
  let total = 0;
  for (let i = 1; i < coords.length; i++) total += haversine(coords[i - 1], coords[i]);
  return total;
}

export type Projection = {
  alongM: number;
  crossTrackM: number;
  snapped: LngLat;
  bearing: number;
  segmentIndex: number;
};

/** Closest point on the polyline, distance along it, and perpendicular distance. */
export function projectOntoRoute(coords: LngLat[], point: LngLat): Projection {
  if (coords.length === 0) {
    return { alongM: 0, crossTrackM: 0, snapped: point, bearing: 0, segmentIndex: 0 };
  }
  if (coords.length === 1) {
    return {
      alongM: 0, crossTrackM: haversine(coords[0], point), snapped: coords[0], bearing: 0, segmentIndex: 0,
    };
  }
  let bestDist = Infinity;
  let bestAlong = 0;
  let bestSnapped = coords[0];
  let bestBearing = bearing(coords[0], coords[1]);
  let bestIndex = 0;
  let cum = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const a = coords[i];
    const b = coords[i + 1];
    const segLen = haversine(a, b);
    const ab = toMeters(a, b);
    const ap = toMeters(a, point);
    const len2 = ab[0] * ab[0] + ab[1] * ab[1];
    const t = len2 < 1e-6 ? 0 : Math.max(0, Math.min(1, (ap[0] * ab[0] + ap[1] * ab[1]) / len2));
    const snapped: LngLat = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    const dist = haversine(snapped, point);
    const along = cum + segLen * t;
    if (dist < bestDist - 0.05 || (Math.abs(dist - bestDist) <= 0.05 && along > bestAlong)) {
      bestDist = dist;
      bestAlong = along;
      bestSnapped = snapped;
      bestBearing = segLen > 0.5 ? bearing(a, b) : bestBearing;
      bestIndex = i;
    }
    cum += segLen;
  }
  return {
    alongM: bestAlong, crossTrackM: bestDist, snapped: bestSnapped, bearing: bestBearing, segmentIndex: bestIndex,
  };
}

/** Point a distance along the polyline, and the forward bearing there. */
export function pointAtDistance(coords: LngLat[], distanceM: number): { point: LngLat; bearing: number } {
  if (coords.length === 0) return { point: [0, 0], bearing: 0 };
  if (coords.length === 1 || distanceM <= 0) {
    return { point: coords[0], bearing: coords.length > 1 ? bearing(coords[0], coords[1]) : 0 };
  }
  let left = distanceM;
  for (let i = 0; i < coords.length - 1; i++) {
    const len = haversine(coords[i], coords[i + 1]);
    const brg = bearing(coords[i], coords[i + 1]);
    if (left <= len || i === coords.length - 2) {
      const t = len === 0 ? 0 : Math.max(0, Math.min(1, left / len));
      return {
        point: [
          coords[i][0] + (coords[i + 1][0] - coords[i][0]) * t,
          coords[i][1] + (coords[i + 1][1] - coords[i][1]) * t,
        ],
        bearing: brg,
      };
    }
    left -= len;
  }
  return { point: coords[coords.length - 1], bearing: 0 };
}
