"use client";

import "mapbox-gl/dist/mapbox-gl.css"; // static on purpose: the map needs this CSS when it is created
import { useEffect, useRef, useState } from "react";

import { bandLayers, boundsOf, otherRoutesCollection, segmentCollection } from "@/lib/mapdata";
import type { Route } from "@/lib/types";

import { PEGMAN_LABEL, PEGMAN_MARKUP } from "./Pegman";
import { SegmentMap } from "./SegmentMap";

type Props = {
  routes: Route[];
  selectedId: string;
  highlightSegment?: number | null;
  onPickPoint?: (lng: number, lat: number) => void;
  pegman?: { lng: number; lat: number } | null;
};

type PegMarker = {
  setLngLat: (ll: [number, number]) => { addTo: (map: unknown) => void };
  getLngLat: () => { lng: number; lat: number };
  on: (event: string, cb: () => void) => void;
};

const SEL = "selected-route";
const OTHERS = "other-routes";

/** Mapbox map when a key and WebGL are available; otherwise the SVG drawing (never a blank box). */
export function RouteMap({ routes, selectedId, highlightSegment = null, onPickPoint, pegman = null }: Props) {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("mapbox-gl").Map | null>(null);
  const markerRef = useRef<PegMarker | null>(null);
  const onPickRef = useRef(onPickPoint);
  const pegmanRef = useRef(pegman);
  onPickRef.current = onPickPoint;
  pegmanRef.current = pegman;
  const [failed, setFailed] = useState(false);
  const [pegReady, setPegReady] = useState(0);
  const selected = routes.find((r) => r.route_id === selectedId) ?? routes[0];

  useEffect(() => {
    if (!token || failed || !container.current || !selected) return;
    let cancelled = false;
    let removeMap: (() => void) | null = null;
    (async () => {
      try {
        const mapboxgl = (await import("mapbox-gl")).default;
        if (cancelled || !container.current) return;
        mapboxgl.accessToken = token;
        const map = new mapboxgl.Map({
          container: container.current, style: "mapbox://styles/mapbox/dark-v11",
          interactive: true, attributionControl: true,
        });
        mapRef.current = map;
        removeMap = () => map.remove();
        const Nav = mapboxgl.NavigationControl;
        if (typeof map.addControl === "function" && typeof Nav === "function") {
          map.addControl(new Nav({ showCompass: false, visualizePitch: false }), "top-right");
        }
        if (onPickRef.current) {
          map.on("click", (event: { lngLat?: { lng: number; lat: number } }) => {
            const at = event?.lngLat;
            if (!at || !onPickRef.current) return;
            onPickRef.current(at.lng, at.lat);
          });
          const MarkerCtor = (mapboxgl as { Marker?: new (opts: {
            element: HTMLElement; draggable: boolean; anchor: string;
          }) => PegMarker }).Marker;
          if (typeof MarkerCtor === "function") {
            try {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "pegman";
              button.setAttribute("aria-label", PEGMAN_LABEL);
              button.innerHTML = PEGMAN_MARKUP;
              const start = pegmanRef.current
                ? [pegmanRef.current.lng, pegmanRef.current.lat] as [number, number]
                : selected.geometry.coordinates[0];
              const marker = new MarkerCtor({ element: button, draggable: true, anchor: "bottom" });
              marker.setLngLat(start).addTo(map);
              markerRef.current = marker;
              marker.on("dragend", () => {
                const at = marker.getLngLat();
                onPickRef.current?.(at.lng, at.lat);
              });
              button.addEventListener("click", (ev) => {
                ev.stopPropagation();
                const at = marker.getLngLat();
                onPickRef.current?.(at.lng, at.lat);
              });
              setPegReady((n) => n + 1);
            } catch {
              /* the map still works; tapping the route opens street view */
            }
          }
        }
        map.on("load", () => {
          map.addSource(OTHERS, { type: "geojson", data: otherRoutesCollection(routes, selected.route_id) as never });
          map.addLayer({ id: OTHERS, type: "line", source: OTHERS,
            paint: { "line-color": "#c6c8ba", "line-opacity": 0.35, "line-width": 3 } });
          map.addSource(SEL, { type: "geojson", data: segmentCollection(selected) as never });
          for (const layer of bandLayers(SEL)) map.addLayer(layer as never);
          const bounds = boundsOf(routes);
          if (bounds) map.fitBounds(bounds, { padding: 40, duration: 0 });
        });
        map.on("error", () => setFailed(true));
      } catch {
        if (!cancelled) setFailed(true); // no WebGL, blocked script, bad key: fall back to the drawing
      }
    })();
    return () => { cancelled = true; removeMap?.(); mapRef.current = null; markerRef.current = null; };
    // The map is created once per set of routes; selection changes update the sources below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, failed, routes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selected) return;
    const src = map.getSource(SEL) as import("mapbox-gl").GeoJSONSource | undefined;
    src?.setData(segmentCollection(selected) as never);
    (map.getSource(OTHERS) as import("mapbox-gl").GeoJSONSource | undefined)
      ?.setData(otherRoutesCollection(routes, selected.route_id) as never);
  }, [selected, routes]);

  useEffect(() => {
    if (!pegman || !markerRef.current) return;
    markerRef.current.setLngLat([pegman.lng, pegman.lat]);
  }, [pegman, pegReady]);

  if (!selected) return null;
  const hint = onPickPoint
    ? <p className="caption" style={{ padding: "6px 12px" }}>Tap the route, or drag the peg, to look at street level.</p>
    : null;
  if (!token || failed) {
    return (
      <div className="map-wrap">
        <SegmentMap routes={routes} selectedId={selectedId} highlightSegment={highlightSegment}
          onPickPoint={onPickPoint} pegman={pegman} />
        <p className="caption" style={{ padding: "6px 12px" }}>
          {failed ? "The map could not load, so this is a simple drawing of the route." :
            "Map tiles need a map key on this server, so this is a simple drawing of the route."}
        </p>
        {hint}
      </div>
    );
  }
  return (
    <div className="map-wrap">
      <div ref={container} className="map-box" role="region" aria-label="Map of the selected route" />
      {hint}
    </div>
  );
}
