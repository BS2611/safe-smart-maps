"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { describeError } from "@/lib/api";
import {
  BAND_SYMBOL, BAND_TEXT, formatClock, formatMeters, formatMinutes, formatPercent, LABEL_NAMES, scoreWord, viaText,
} from "@/lib/format";
import { averageFactors } from "@/lib/routeStats";
import { CONTINUITY_RULES, FACTORS } from "@/lib/scoring-info";
import { darkestSegmentIndex, nearestSegmentIndex, segmentMidpoint } from "@/lib/streetview/geo";
import { isReady } from "@/lib/trip";
import type { Route } from "@/lib/types";
import { useRoutes } from "@/lib/useRoutes";

import { AppHeader } from "./AppHeader";
import { NavigationScreen } from "./NavigationScreen";
import { Banner } from "./Banner";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { RouteMap } from "./RouteMap";
import { ScoreRing } from "./ScoreVisuals";
import { StreetView } from "./StreetView";
import { useTrip } from "./TripProvider";

export function RouteDetailScreen({ routeId }: { routeId: string }) {
  const { trip, ready, updateTrip } = useTrip();
  const { state, retry } = useRoutes(trip);
  const [index, setIndex] = useState<number | null>(null);
  const [navigating, setNavigating] = useState(false);
  const shown = useRef<Route | null>(null);
  const [pegman, setPegman] = useState<{ lng: number; lat: number } | null>(null);
  const [street, setStreet] = useState<{ lng: number; lat: number; darkest: boolean } | null>(null);

  function openNav(active: Route) {
    shown.current = active;
    setNavigating(true);
  }

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
  if ((state.status === "idle" || state.status === "loading") && navigating && shown.current) {
    return (
      <NavigationScreen
        route={shown.current}
        recalculating
        onClose={() => setNavigating(false)}
        onReroute={(from) => updateTrip({ from })}
      />
    );
  }
  if (state.status === "idle" || state.status === "loading") {
    return <div className="screen" aria-busy="true"><p className="muted">Loading route…</p></div>;
  }
  if (state.status === "error") {
    return (
      <div className="screen stack">
        <AppHeader title="Route details" backHref="/routes" />
        <Banner kind="error" title="This route didn't load">{describeError(state.error)}</Banner>
        <div className="stack-sm">
          <button type="button" className="btn primary" onClick={retry}>Try again</button>
          <Link href="/plan" className="btn secondary">Plan a walk</Link>
        </div>
      </div>
    );
  }

  const route = state.data.routes.find((r) => r.route_id === routeId)
    ?? (navigating ? state.data.routes.find((r) => r.label === shown.current?.label) ?? state.data.routes[0] : undefined);
  if (route) shown.current = route;
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
  const darkest = darkestSegmentIndex(route.segments);
  const segments = route.segments;

  function openStreet(lng: number, lat: number, fromDarkest = false) {
    setPegman({ lng, lat });
    setIndex(nearestSegmentIndex(segments, lng, lat));
    setStreet({ lng, lat, darkest: fromDarkest });
  }

  return (
    <div className="screen stack detail-page">
      <AppHeader title={LABEL_NAMES[route.label]} subtitle={viaText(route.via)} backHref="/routes" />

      <div className="card detail-hero">
        <ScoreRing score={route.route_score} size={96} />
        <div>
          <p className="caption">Street conditions</p>
          <strong className="stat-xl">{scoreWord(route.route_score)}</strong>
        </div>
        <div className="detail-time">
          <p className="caption">Walk time</p>
          <strong className="stat-xl">{formatMinutes(route.duration_min)}</strong>
        </div>
      </div>

      <div className="detail-layout">
      <div className="map-col stack-sm">
      <RouteMap routes={state.data.routes} selectedId={route.route_id} highlightSegment={index}
        pegman={pegman} onPickPoint={(lng, lat) => openStreet(lng, lat)} />

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
        <p className="small muted">Tap a stretch to see why. Tap the map, or drag the peg, for a street-level photo.</p>
        <button type="button" className="btn secondary" disabled={darkest === null}
          onClick={() => {
            if (darkest === null) return;
            const [lng, lat] = segmentMidpoint(route.segments[darkest]);
            openStreet(lng, lat, true);
          }}>
          Preview the darkest stretch
        </button>
        {darkest === null ? <p className="caption">Not sure which stretch is darkest.</p> : null}
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
      </div>
      <div className="detail-col stack">

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
      <DisclaimerBanner compact />
      <div className="detail-actions">
        <button type="button" className="btn primary" onClick={() => openNav(route)}>Start</button>
        <Link href="/routes" className="btn secondary">Back to routes</Link>
      </div>
      {navigating ? (
        <NavigationScreen
          route={route}
          onClose={() => setNavigating(false)}
          onReroute={(from) => updateTrip({ from })}
        />
      ) : null}
      </div>
      </div>
      {street ? (
        <StreetView route={route} entry={street} onClose={() => setStreet(null)}
          onPosition={(lng, lat, segmentIndex) => { setPegman({ lng, lat }); setIndex(segmentIndex); }} />
      ) : null}
    </div>
  );
}
