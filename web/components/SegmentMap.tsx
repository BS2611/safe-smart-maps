"use client";

import { useRef, useState } from "react";

import { BAND_COLOR, BAND_DASH, frameOf, pathFor, segmentPath } from "@/lib/geometry";
import { BAND_TEXT, LABEL_NAMES } from "@/lib/format";
import { segmentMidpoint } from "@/lib/streetview/geo";
import type { Route } from "@/lib/types";

import { PEGMAN_LABEL } from "./Pegman";

type Props = {
  routes: Route[];
  selectedId: string;
  width?: number;
  height?: number;
  highlightSegment?: number | null;
  title?: string;
  onPickPoint?: (lng: number, lat: number) => void;
  pegman?: { lng: number; lat: number } | null;
};

/** Simple SVG drawing of the routes. Works without a map key or WebGL, and is used as the map fallback. */
export function SegmentMap({
  routes, selectedId, width = 360, height = 260, highlightSegment = null, title, onPickPoint, pegman = null,
}: Props) {
  const frame = frameOf(routes, width, height, 24);
  const project = frame.project;
  const selected = routes.find((r) => r.route_id === selectedId) ?? routes[0];
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);
  const [dragAt, setDragAt] = useState<{ lng: number; lat: number } | null>(null);
  if (!selected) return null;
  const first = selected.geometry.coordinates[0];
  const last = selected.geometry.coordinates[selected.geometry.coordinates.length - 1];
  const [sx, sy] = project(first[0], first[1]);
  const [ex, ey] = project(last[0], last[1]);
  const label = title ?? `Route drawing: ${LABEL_NAMES[selected.label]}`;
  const peg = dragAt ?? pegman ?? { lng: first[0], lat: first[1] };
  const [px, py] = project(peg.lng, peg.lat);

  function locate(event: { clientX: number; clientY: number }): [number, number] | null {
    const svg = svgRef.current;
    if (!svg) return null;
    try {
      if (typeof svg.createSVGPoint === "function" && svg.getScreenCTM()) {
        const pt = svg.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        const local = pt.matrixTransform(svg.getScreenCTM()!.inverse());
        return frame.unproject(local.x, local.y);
      }
    } catch {
      /* fall through to the box */
    }
    const rect = svg.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    const x = ((event.clientX - rect.left) / rect.width) * width;
    const y = ((event.clientY - rect.top) / rect.height) * height;
    return frame.unproject(x, y);
  }

  return (
    <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} className="svg-map"
      role={onPickPoint ? "group" : "img"} aria-label={label}
      onClick={(event) => {
        if (!onPickPoint) return;
        const target = event.target as Element | null;
        if (target?.closest?.("[data-hit], [data-pegman]")) return;
        const at = locate(event);
        if (at) onPickPoint(at[0], at[1]);
      }}>
      {routes.filter((r) => r.route_id !== selected.route_id).map((r) => (
        <path key={r.route_id} d={pathFor(r.geometry.coordinates, project)} stroke="#c6c8ba" strokeOpacity="0.35"
          strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      ))}
      <path d={pathFor(selected.geometry.coordinates, project)} stroke="#0b0f0e" strokeWidth="9" fill="none"
        strokeLinecap="round" strokeLinejoin="round" />
      {selected.segments.map((seg, i) => (
        <path key={seg.segment_id} d={segmentPath(seg, project)} stroke={BAND_COLOR[seg.band]}
          strokeWidth={highlightSegment === i ? 8 : 5} fill="none" strokeLinecap="butt"
          strokeDasharray={BAND_DASH[seg.band]} data-band={seg.band} />
      ))}
      {onPickPoint ? selected.segments.map((seg, i) => {
        const [mlng, mlat] = segmentMidpoint(seg);
        return (
          <path key={`${seg.segment_id}-hit`} data-hit="true" d={segmentPath(seg, project)} stroke="transparent"
            strokeWidth="18" fill="none" strokeLinecap="round" role="button" tabIndex={0}
            aria-label={`Open street view on stretch ${i + 1}, ${BAND_TEXT[seg.band]}`}
            onClick={(event) => { event.stopPropagation(); onPickPoint(mlng, mlat); }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onPickPoint(mlng, mlat);
              }
            }} />
        );
      }) : null}
      <circle cx={sx} cy={sy} r="8" fill="#0b0f0e" stroke="#e0e3e1" strokeWidth="2.5" />
      <circle cx={ex} cy={ey} r="8" fill="#a5f2d7" stroke="#0b0f0e" strokeWidth="2.5" />
      <text x={sx} y={sy - 14} fill="#e0e3e1" fontSize="11" fontWeight="600" textAnchor="middle">START</text>
      <text x={ex} y={ey - 14} fill="#e0e3e1" fontSize="11" fontWeight="600" textAnchor="middle">END</text>
      {onPickPoint ? (
        <g data-pegman="true" role="button" tabIndex={0} aria-label={PEGMAN_LABEL}
          transform={`translate(${px.toFixed(1)} ${py.toFixed(1)})`}
          onPointerDown={(event) => {
            event.stopPropagation();
            dragging.current = true;
            event.currentTarget.setPointerCapture?.(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (!dragging.current) return;
            const at = locate(event);
            if (at) setDragAt({ lng: at[0], lat: at[1] });
          }}
          onPointerUp={(event) => {
            if (!dragging.current) return;
            dragging.current = false;
            const at = locate(event);
            setDragAt(null);
            if (at) onPickPoint(at[0], at[1]);
            else onPickPoint(peg.lng, peg.lat);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onPickPoint(peg.lng, peg.lat);
            }
          }}>
          <circle r="22" fill="transparent" />
          <path d="M0 6 C -9 6 -11 -8 0 -18 C 11 -8 9 6 0 6 Z" fill="#a5f2d7" stroke="#07110e" strokeWidth="1.6" />
          <circle cy="-8" r="3" fill="#07110e" />
        </g>
      ) : null}
    </svg>
  );
}
