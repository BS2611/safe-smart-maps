import { BAND_COLOR, BAND_DASH, makeProjector, pathFor, segmentPath } from "@/lib/geometry";
import { LABEL_NAMES } from "@/lib/format";
import type { Route } from "@/lib/types";

type Props = {
  routes: Route[];
  selectedId: string;
  width?: number;
  height?: number;
  highlightSegment?: number | null;
  title?: string;
};

/** Simple SVG drawing of the routes. Works without a map key or WebGL, and is used as the map fallback. */
export function SegmentMap({ routes, selectedId, width = 360, height = 260, highlightSegment = null, title }: Props) {
  const project = makeProjector(routes, width, height, 24);
  const selected = routes.find((r) => r.route_id === selectedId) ?? routes[0];
  if (!selected) return null;
  const first = selected.geometry.coordinates[0];
  const last = selected.geometry.coordinates[selected.geometry.coordinates.length - 1];
  const [sx, sy] = project(first[0], first[1]);
  const [ex, ey] = project(last[0], last[1]);
  const label = title ?? `Route drawing: ${LABEL_NAMES[selected.label]}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="svg-map" role="img" aria-label={label}>
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
      <circle cx={sx} cy={sy} r="8" fill="#0b0f0e" stroke="#e0e3e1" strokeWidth="2.5" />
      <circle cx={ex} cy={ey} r="8" fill="#a5f2d7" stroke="#0b0f0e" strokeWidth="2.5" />
      <text x={sx} y={sy - 14} fill="#e0e3e1" fontSize="11" fontWeight="600" textAnchor="middle">START</text>
      <text x={ex} y={ey - 14} fill="#e0e3e1" fontSize="11" fontWeight="600" textAnchor="middle">END</text>
    </svg>
  );
}
