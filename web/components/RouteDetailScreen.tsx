"use client";

import Link from "next/link";
import { useState } from "react";

import { describeError } from "@/lib/api";
import {
  BAND_SYMBOL, BAND_TEXT, formatClock, formatMeters, formatMinutes, formatPercent, LABEL_NAMES, scoreWord, viaText,
} from "@/lib/format";
import { averageFactors } from "@/lib/routeStats";
import { CONTINUITY_RULES, FACTORS } from "@/lib/scoring-info";
import { isReady } from "@/lib/trip";
import { useRoutes } from "@/lib/useRoutes";

import { AppHeader } from "./AppHeader";
import { Banner } from "./Banner";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { RouteMap } from "./RouteMap";
import { useTrip } from "./TripProvider";

export function RouteDetailScreen({ routeId }: { routeId: string }) {
  const { trip, ready } = useTrip();
  const { state, retry } = useRoutes(trip);
  const [index, setIndex] = useState<number | null>(null);

  if (!ready) return <div className="screen" aria-busy="true" />;
  if (!isReady(trip)) {
    return (
      <div className="screen stack">
        <AppHeader title="Route details" backHref="/plan" />
        <Banner kind="info" title="Choose a start and a destination first">
          Your trip is empty. <Link href="/plan" style={{ textDecoration: "underline" }}>Plan a walk</Link>.
        </Banner>
      </div>
    );
  }
  if (state.status === "idle" || state.status === "loading") {
    return <div className="screen" aria-busy="true"><p className="muted">Loading route…</p></div>;
  }
  if (state.status === "error") {
    return (
      <div className="screen stack">
        <AppHeader title="Route details" backHref="/routes" />
        <Banner kind="error" title="We could not load this route">{describeError(state.error)}</Banner>
        <div className="stack-sm">
          <button type="button" className="btn primary" onClick={retry}>Try again</button>
          <Link href="/plan" className="btn secondary">Plan a walk</Link>
        </div>
      </div>
    );
  }

  const route = state.data.routes.find((r) => r.route_id === routeId);
  if (!route) {
    return (
      <div className="screen stack">
        <AppHeader title="Route details" backHref="/routes" />
        <Banner kind="info" title="This route is not in your current results">
          Go back and pick one of your routes.
        </Banner>
        <Link href="/routes" className="btn primary">Back to routes</Link>
      </div>
    );
  }

  const c = route.continuity;
  const seg = index !== null ? route.segments[index] : null;
  const avg = averageFactors(route);
  const target = CONTINUITY_RULES.coverageTarget;

  return (
    <div className="screen stack">
      <AppHeader title={LABEL_NAMES[route.label]} subtitle={viaText(route.via)} backHref="/routes" />

      <div className="card row between">
        <div>
          <p className="caption">Walk time</p>
          <strong style={{ fontSize: 22 }}>{formatMinutes(route.duration_min)}</strong>
        </div>
        <div style={{ textAlign: "right" }}>
          <p className="caption">Overall</p>
          <strong style={{ fontSize: 22 }}>{scoreWord(route.route_score)}</strong>
        </div>
      </div>

      <RouteMap routes={state.data.routes} selectedId={route.route_id} highlightSegment={index} />

      <section className="card stack-sm" aria-labelledby="cont-h">
        <h2 id="cont-h">Along the whole walk</h2>
        <div>
          <div className="row between small"><span>Coverage</span><strong>{formatPercent(c.coverage_pct)}</strong></div>
          <div className="bar-wrap" style={{ marginTop: 6 }}>
            <div className="bar" role="img" aria-label={`Coverage ${formatPercent(c.coverage_pct)}, target ${target}%`}>
              <span style={{ width: `${c.coverage_pct ?? 0}%` }} />
            </div>
            <div className="bar-target" style={{ left: `${target}%` }} aria-hidden="true" />
          </div>
          <p className="caption" style={{ marginTop: 4 }}>
            Share of the walk within {CONTINUITY_RULES.coverageRadiusM} m of an open place, help point or active stop. Target {target}%.
          </p>
        </div>
        <div className="row between small">
          <span>Longest empty stretch</span>
          <strong>{formatMeters(c.longest_gap_m)}{c.longest_gap_note ? ` ${c.longest_gap_note}` : ""}</strong>
        </div>
        <div className="row between small">
          <span>Lowest {CONTINUITY_RULES.windowM} m stretch</span>
          <strong>{c.worst_window_score === null ? "Not sure" : `${Math.round(c.worst_window_score)} / 100`}</strong>
        </div>
      </section>

      <section className="card stack-sm" aria-labelledby="strip-h">
        <h2 id="strip-h">Every stretch of the route</h2>
        <p className="small muted">Tap a part to see why it is rated that way.</p>
        <div className="strip" role="group" aria-label="Route segments">
          {route.segments.map((s, i) => (
            <button key={s.segment_id} type="button" className={`band-${s.band}`}
              style={{ flexGrow: s.length_m }} aria-pressed={index === i}
              aria-label={`Stretch ${i + 1}: ${BAND_TEXT[s.band]}`} onClick={() => setIndex(i === index ? null : i)}>
              <span aria-hidden="true">{BAND_SYMBOL[s.band]}</span>
            </button>
          ))}
        </div>
        {seg ? (
          <div className="banner" role="status">
            <h3>{BAND_TEXT[seg.band]}{seg.score !== null ? ` · ${Math.round(seg.score)} / 100` : ""}</h3>
            <p className="small muted">
              You reach this part at about {formatClock(seg.arrival_time)}.
              {seg.confidence === "low" ? " Some data is missing here, so we are less sure." : ""}
              {seg.confidence === "unknown" ? " We are not sure about this part." : ""}
            </p>
            <ul className="reasons" aria-label="Reasons">
              {seg.reasons.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </div>
        ) : null}
      </section>

      <section className="card stack-sm" aria-labelledby="fac-h">
        <h2 id="fac-h">What we checked</h2>
        {FACTORS.map((f) => {
          const value = avg[f.id] ?? null;
          return (
            <div key={f.id} className="factor">
              <span>{f.label}{f.estimate ? <span className="badge">Estimate</span> : null}</span>
              <span className="small muted">{f.weight}% of score · {value === null ? "Not sure" : `${value}/100`}</span>
              <div className="bar" aria-hidden="true"><span style={{ width: `${value ?? 0}%` }} /></div>
            </div>
          );
        })}
      </section>

      <section className="card stack-sm" aria-labelledby="why-h">
        <h2 id="why-h">Why this route</h2>
        <p>{route.explanation}</p>
        <p className="caption">
          {route.explanation_source === "ai" ? "Explained by AI, may be wrong. " : "Written from the numbers above. "}
          In an emergency, call 911.
        </p>
      </section>

      <p className="caption">
        {route.open_places_count === null ? "Open places: not sure." : `${route.open_places_count} open places along the way.`}
        {route.nearest_help_point
          ? ` Nearest help point: ${route.nearest_help_point.name}, ${formatMeters(route.nearest_help_point.distance_m)}.` : ""}
      </p>
      <Link href="/routes" className="btn primary">Back to routes</Link>
      <DisclaimerBanner compact />
    </div>
  );
}
