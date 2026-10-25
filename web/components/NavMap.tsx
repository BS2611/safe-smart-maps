"use client";

import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef, useState } from "react";

import { toMeters, type LngLat } from "@/lib/nav/geo";

type Props = {
  coords: LngLat[];
  user: LngLat;
  mapBearing: number;
  arrowDeg: number;
  reducedMotion: boolean;
};

/** Dark walking map. The user stays in the center. Heading-up rotates the map under a fixed arrow. */
export function NavMap({ coords, user, mapBearing, arrowDeg, reducedMotion }: Props) {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("mapbox-gl").Map | null>(null);
  const [failed, setFailed] = useState(false);
  const showMap = Boolean(token) && !failed;

  useEffect(() => {
    if (!showMap || !container.current) return;
    let cancelled = false;
    let removeMap: (() => void) | null = null;
    (async () => {
      try {
        const mapboxgl = (await import("mapbox-gl")).default;
        if (cancelled || !container.current) return;
        mapboxgl.accessToken = token;
        const map = new mapboxgl.Map({
          container: container.current,
          style: "mapbox://styles/mapbox/dark-v11",
          center: user,
          zoom: 17,
          bearing: mapBearing,
          pitch: 0,
          interactive: false,
          attributionControl: true,
        });
        mapRef.current = map;
        removeMap = () => map.remove();
        map.on("load", () => {
          map.addSource("nav-route", {
            type: "geojson",
            data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: coords } },
          });
          map.addLayer({
            id: "nav-route",
            type: "line",
            source: "nav-route",
            paint: { "line-color": "#7ef0c8", "line-width": 6 },
          });
        });
        map.on("error", () => setFailed(true));
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      removeMap?.();
      mapRef.current = null;
    };
    // The map is created once. Position and bearing update below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showMap, token]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const duration = reducedMotion ? 0 : 350;
    map.easeTo({ center: user, bearing: mapBearing, duration });
  }, [user, mapBearing, reducedMotion]);

  return (
    <div className="nav-map">
      {showMap ? (
        <div ref={container} className="nav-canvas" role="region" aria-label="Walking map" />
      ) : (
        <NavDrawing coords={coords} user={user} mapBearing={mapBearing} />
      )}
      <div className="nav-puck" style={{ transform: `rotate(${arrowDeg}deg)` }} aria-hidden="true">
        <span />
      </div>
    </div>
  );
}

function NavDrawing({ coords, user, mapBearing }: { coords: LngLat[]; user: LngLat; mapBearing: number }) {
  const width = 360;
  const height = 520;
  const ppm = 2.1;
  const d = coords.map(([lng, lat], i) => {
    const [x, y] = toMeters(user, [lng, lat]);
    const px = width / 2 + x * ppm;
    const py = height / 2 - y * ppm;
    return `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`;
  }).join(" ");
  return (
    <svg className="nav-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Walking map">
      <rect width={width} height={height} fill="#07110e" />
      <g transform={`rotate(${(-mapBearing).toFixed(2)} ${width / 2} ${height / 2})`}>
        <path d={d} stroke="#7ef0c8" strokeWidth="7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}
