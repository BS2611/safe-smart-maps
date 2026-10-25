// Points along a walk, in GeoJSON order: [longitude, latitude].

export type LngLat = [number, number];

const EARTH_M = 6_371_000;

export function haversineM(aLng: number, aLat: number, bLng: number, bLat: number): number {
  const rad = Math.PI / 180;
  const dLat = (bLat - aLat) * rad;
  const dLng = (bLng - aLng) * rad;
  const s1 = Math.sin(dLat / 2);
  const s2 = Math.sin(dLng / 2);
  const h = s1 * s1 + Math.cos(aLat * rad) * Math.cos(bLat * rad) * s2 * s2;
  return 2 * EARTH_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Degrees clockwise from north. */
export function bearingDeg(aLng: number, aLat: number, bLng: number, bLat: number): number {
  const rad = Math.PI / 180;
  const y = Math.sin((bLng - aLng) * rad) * Math.cos(bLat * rad);
  const x = Math.cos(aLat * rad) * Math.sin(bLat * rad)
    - Math.sin(aLat * rad) * Math.cos(bLat * rad) * Math.cos((bLng - aLng) * rad);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

/** A point about every `stepM` meters, always including the start and the end. */
export function sampleRoute(coords: LngLat[], stepM = 25): LngLat[] {
  if (coords.length === 0) return [];
  const first = coords[0];
  if (coords.length === 1) return [[first[0], first[1]]];
  const out: LngLat[] = [[first[0], first[1]]];
  let carry = 0;
  let prev = first;
  for (let i = 1; i < coords.length; i++) {
    const next = coords[i];
    const segLen = haversineM(prev[0], prev[1], next[0], next[1]);
    if (segLen < 0.5) {
      prev = next;
      continue;
    }
    let distInto = stepM - carry;
    while (distInto <= segLen + 1e-6) {
      const t = Math.min(1, distInto / segLen);
      out.push([prev[0] + (next[0] - prev[0]) * t, prev[1] + (next[1] - prev[1]) * t]);
      distInto += stepM;
    }
    carry = segLen - (distInto - stepM);
    prev = next;
  }
  const last = coords[coords.length - 1];
  const tail = out[out.length - 1];
  if (haversineM(tail[0], tail[1], last[0], last[1]) > 1) out.push([last[0], last[1]]);
  return out;
}

export function nearestIndex(points: LngLat[], lng: number, lat: number): number {
  let best = 0;
  let bestD = Infinity;
  for (let i = 0; i < points.length; i++) {
    const d = haversineM(points[i][0], points[i][1], lng, lat);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  }
  return best;
}

export function forwardBearing(samples: LngLat[], index: number): number {
  if (samples.length < 2) return 0;
  const i = Math.max(0, Math.min(samples.length - 1, index));
  if (i >= samples.length - 1) {
    return bearingDeg(samples[i - 1][0], samples[i - 1][1], samples[i][0], samples[i][1]);
  }
  return bearingDeg(samples[i][0], samples[i][1], samples[i + 1][0], samples[i + 1][1]);
}

type SegmentEnds = { start: LngLat; end: LngLat; score?: number | null };

function distanceToSegmentM(lng: number, lat: number, start: LngLat, end: LngLat): number {
  const cos = Math.cos(lat * Math.PI / 180) || 1e-6;
  const ax = start[0] * cos;
  const ay = start[1];
  const bx = end[0] * cos;
  const by = end[1];
  const px = lng * cos;
  const py = lat;
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2));
  return haversineM(lng, lat, (ax + t * dx) / cos, ay + t * dy);
}

export function nearestSegmentIndex(segments: SegmentEnds[], lng: number, lat: number): number {
  if (segments.length === 0) return 0;
  let best = 0;
  let bestD = Infinity;
  for (let i = 0; i < segments.length; i++) {
    const d = distanceToSegmentM(lng, lat, segments[i].start, segments[i].end);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  }
  return best;
}

/** Lowest known score. Unknown scores are skipped, never treated as zero. */
export function darkestSegmentIndex(segments: { score: number | null }[]): number | null {
  let best: number | null = null;
  let bestScore = Infinity;
  for (let i = 0; i < segments.length; i++) {
    const score = segments[i].score;
    if (score === null || Number.isNaN(score)) continue;
    if (score < bestScore) {
      bestScore = score;
      best = i;
    }
  }
  return best;
}

export function segmentMidpoint(seg: { start: LngLat; end: LngLat }): LngLat {
  return [(seg.start[0] + seg.end[0]) / 2, (seg.start[1] + seg.end[1]) / 2];
}

/**
 * Center of a 360 photo so the view looks along `heading` rather than the
 * camera's own compass. x is a fraction of the full turn; y 0.5 is level.
 */
export function basicCenterForHeading(compass: number, heading: number): [number, number] {
  let delta = ((heading - compass) % 360 + 360) % 360;
  if (delta > 180) delta -= 360;
  const x = ((0.5 + delta / 360) % 1 + 1) % 1;
  return [x, 0.5];
}
