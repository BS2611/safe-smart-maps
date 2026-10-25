// Draws routes in plain SVG: used as the map fallback (no token, no WebGL) and for small previews.
import type { Band, Route, Segment } from "./types";

export type Projector = (lng: number, lat: number) => [number, number];

export type Frame = {
  project: Projector;
  unproject: (x: number, y: number) => [number, number];
};

/** Project route points into a box, and map a pixel in that box back to longitude, latitude. */
export function frameOf(routes: Route[], width: number, height: number, pad = 16): Frame {
  const pts = routes.flatMap((r) => r.geometry.coordinates);
  if (pts.length === 0) {
    return { project: () => [width / 2, height / 2], unproject: () => [0, 0] };
  }
  const lngs = pts.map((p) => p[0]);
  const lats = pts.map((p) => p[1]);
  const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const cosLat = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
  const spanX = Math.max((maxLng - minLng) * cosLat, 1e-9);
  const spanY = Math.max(maxLat - minLat, 1e-9);
  const scale = Math.min((width - 2 * pad) / spanX, (height - 2 * pad) / spanY);
  const offX = (width - spanX * scale) / 2;
  const offY = (height - spanY * scale) / 2;
  return {
    project: (lng, lat) => [offX + (lng - minLng) * cosLat * scale, height - offY - (lat - minLat) * scale],
    unproject: (x, y) => [minLng + (x - offX) / (cosLat * scale), minLat + (height - offY - y) / scale],
  };
}

export function makeProjector(routes: Route[], width: number, height: number, pad = 16): Projector {
  return frameOf(routes, width, height, pad).project;
}

export function pathFor(coords: [number, number][], project: Projector): string {
  return coords.map(([lng, lat], i) => {
    const [x, y] = project(lng, lat);
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

export function segmentPath(seg: Segment, project: Projector): string {
  return pathFor([seg.start, seg.end], project);
}

export const BAND_COLOR: Record<Band, string> = {
  green: "#a5f2d7",
  yellow: "#f2b632",
  red: "#ff9b7a",
  unknown: "#8a97a3",
};

/** Dash pattern per band so the map does not rely on color alone. */
export const BAND_DASH: Record<Band, string | undefined> = {
  green: undefined,
  yellow: "10 4",
  red: "3 5",
  unknown: "2 6",
};
