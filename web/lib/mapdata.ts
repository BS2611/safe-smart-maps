// GeoJSON for the Mapbox layers (pure, so it can be tested without WebGL).
import { BAND_COLOR, BAND_DASH } from "./geometry";
import type { Band, Route } from "./types";

export type FeatureCollection = {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    properties: { band: Band; segment_id: string; index: number };
    geometry: { type: "LineString"; coordinates: [number, number][] };
  }[];
};

export function segmentCollection(route: Route): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: route.segments.map((s, index) => ({
      type: "Feature",
      properties: { band: s.band, segment_id: s.segment_id, index },
      geometry: { type: "LineString", coordinates: [s.start, s.end] },
    })),
  };
}

export function otherRoutesCollection(routes: Route[], selectedId: string) {
  return {
    type: "FeatureCollection" as const,
    features: routes.filter((r) => r.route_id !== selectedId).map((r) => ({
      type: "Feature" as const,
      properties: { route_id: r.route_id },
      geometry: r.geometry,
    })),
  };
}

/** One line layer per band, because Mapbox cannot style the dash pattern from data. */
export function bandLayers(sourceId: string) {
  return (["green", "yellow", "red", "unknown"] as Band[]).map((band) => ({
    id: `${sourceId}-${band}`,
    type: "line" as const,
    source: sourceId,
    filter: ["==", ["get", "band"], band] as unknown[],
    layout: { "line-cap": "butt" as const, "line-join": "round" as const },
    paint: {
      "line-color": BAND_COLOR[band],
      "line-width": 6,
      ...(BAND_DASH[band] ? { "line-dasharray": BAND_DASH[band]!.split(" ").map((n) => Number(n) / 3) } : {}),
    },
  }));
}

export function boundsOf(routes: Route[]): [[number, number], [number, number]] | null {
  const pts = routes.flatMap((r) => r.geometry.coordinates);
  if (!pts.length) return null;
  const lngs = pts.map((p) => p[0]);
  const lats = pts.map((p) => p[1]);
  return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
}
