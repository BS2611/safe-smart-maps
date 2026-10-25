import Link from "next/link";

import {
  formatExtra, formatMeters, formatMinutes, formatPercent, LABEL_CLASS, LABEL_NAMES, scoreWord, viaText,
} from "@/lib/format";
import type { Route } from "@/lib/types";

type Props = { route: Route; selected: boolean; onSelect: () => void };


export function RouteCard({ route, selected, onSelect }: Props) {
  const c = route.continuity;
  const merged = route.also_labels.map((l) => LABEL_NAMES[l]);
  return (
    <div className={`route-card ${LABEL_CLASS[route.label]}`} aria-current={selected ? "true" : undefined} data-selected={selected}>
      <button
        type="button" className="route-select"
        aria-pressed={selected} onClick={onSelect}
      >
        <span className="row" style={{ alignItems: "stretch" }}>
          <span className="accent-bar" />
          <span className="grow" style={{ display: "block" }}>
            <span className="row between">
              <span className="name">
                {LABEL_NAMES[route.label]}
                {merged.map((m) => <span key={m} className="badge">{m}</span>)}
              </span>
              <span className="name">{formatMinutes(route.duration_min)}</span>
            </span>
            <span className="row between small muted">
              <span>{viaText(route.via) || formatMeters(route.distance_m)}</span>
              <span>{formatExtra(route.extra_min)}</span>
            </span>
            <span className="small" style={{ display: "block", marginTop: 4 }}>{scoreWord(route.route_score)}</span>
          </span>
        </span>
      </button>
      {merged.length ? (
        <p className="small muted" style={{ marginTop: 8 }}>
          {[LABEL_NAMES[route.label], ...merged].join(" and ")} are the same route.
        </p>
      ) : null}
      <dl className="stats" style={{ margin: "12px 0 0" }}>
        <div className="stat"><dt className="k">Coverage</dt><dd className="v" style={{ margin: 0 }}>{formatPercent(c.coverage_pct)}</dd></div>
        <div className="stat">
          <dt className="k">Longest empty stretch</dt>
          <dd className="v" style={{ margin: 0 }}>
            {formatMeters(c.longest_gap_m)}
            {c.longest_gap_note ? <span className="small muted"> {c.longest_gap_note}</span> : null}
          </dd>
        </div>
        <div className="stat">
          <dt className="k">Open places</dt>
          <dd className="v" style={{ margin: 0 }}>{route.open_places_count ?? "Not sure"}</dd>
        </div>
        <div className="stat">
          <dt className="k">Nearest help point</dt>
          <dd className="v" style={{ margin: 0 }}>
            {route.nearest_help_point
              ? `${formatMeters(route.nearest_help_point.distance_m)}`
              : "Not sure"}
            {route.nearest_help_point ? <span className="small muted"> {route.nearest_help_point.name}</span> : null}
          </dd>
        </div>
      </dl>
      <Link href={`/routes/${route.route_id}`} className="btn secondary" style={{ marginTop: 12 }}>
        Details
      </Link>
    </div>
  );
}
