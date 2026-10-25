"use client";

import Link from "next/link";
import { useState } from "react";

import { describeError, devFixturesEnabled } from "@/lib/api";
import { fetchedAgo, formatDayClock, isStale } from "@/lib/format";
import { isReady } from "@/lib/trip";
import { useRoutes } from "@/lib/useRoutes";

import { AppHeader } from "./AppHeader";
import { Banner } from "./Banner";
import { CheckingScreen, SourcesPanel } from "./CheckingScreen";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { SlidersIcon } from "./Icons";
import { MapLegend } from "./MapLegend";
import { RouteCard } from "./RouteCard";
import { RouteMap } from "./RouteMap";
import { useTrip } from "./TripProvider";

export function RoutesScreen() {
  const { trip, ready } = useTrip();
  const { state, cancel, retry } = useRoutes(trip);
  const [picked, setPicked] = useState<string | null>(null);

  if (!ready) return <div className="screen" aria-busy="true" />;

  if (!isReady(trip)) {
    return (
      <div className="screen stack">
        <AppHeader title="Your routes" backHref="/plan" />
        <Banner kind="info" title="Choose a start and a destination first">
          Your trip is empty. <Link href="/plan" style={{ textDecoration: "underline" }}>Plan a walk</Link>.
        </Banner>
      </div>
    );
  }

  if (state.status === "idle" || state.status === "loading") {
    return <CheckingScreen trip={trip} onCancel={cancel} />;
  }

  if (state.status === "error") {
    return (
      <div className="screen stack">
        <AppHeader title="Your routes" backHref="/plan" />
        <Banner kind="error" title="We could not finish the check">{describeError(state.error)}</Banner>
        <div className="stack-sm">
          <button type="button" className="btn primary" onClick={retry}>Try again</button>
          <Link href="/plan" className="btn secondary">Change trip</Link>
        </div>
        <DisclaimerBanner compact />
      </div>
    );
  }

  const { data } = state;
  const routes = data.routes;
  const selected = routes.find((r) => r.route_id === picked) ?? routes[0];
  const hasAi = routes.some((r) => r.explanation_source === "ai");
  const stale = isStale(data.data_fetched_at);

  return (
    <div className="screen routes-page">
      <AppHeader title="Your routes" backHref="/plan" right={
        <Link href="/preferences?next=/routes" className="icon-btn" aria-label="Route preferences"><SlidersIcon /></Link>
      } />
      {devFixturesEnabled() ? (
        <Banner kind="warn" title="Sample data">
          This is saved sample data for design review, not a live check. It is turned off in normal use.
        </Banner>
      ) : null}
      <div className="card tight trip-summary">
        <strong>{trip.from?.name} → {trip.to?.name}</strong>
        <p className="small muted">
          {trip.departISO ? formatDayClock(trip.departISO) : "Now"} · up to {trip.settings.maxExtraMinutes} min extra
        </p>
      </div>
      <p className="section-kicker">Scores describe street conditions along the whole walk. They are not a promise.</p>

      <div className="routes-layout">
        <div className="map-col stack-sm">
          <RouteMap routes={routes} selectedId={selected.route_id} />
          <MapLegend />
        </div>
        <div className="detail-col stack">
          <div className="row between">
            <span className="tag accent" aria-label="When the data was fetched">{fetchedAgo(data.data_fetched_at)}</span>
            {data.data_fetched_at ? <span className="caption">at {formatDayClock(data.data_fetched_at)}</span> : null}
          </div>
          {stale ? <Banner kind="warn" title="This data is more than 2 hours old">Treat the results as not sure.</Banner> : null}
          {data.warnings.length ? (
            <Banner kind="warn" title="Some information is missing">
              <ul style={{ margin: 0, paddingLeft: 18 }}>{data.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </Banner>
          ) : null}

          <section className="route-list" aria-label="Routes">
            <h2>Street conditions</h2>
            {routes.map((r) => (
              <RouteCard key={r.route_id} route={r} selected={r.route_id === selected.route_id}
                onSelect={() => setPicked(r.route_id)} />
            ))}
          </section>

          <div className="card stack-sm why-card">
            <h2>Why this route</h2>
            <p>{selected.explanation}</p>
            <p className="caption">
              {selected.explanation_source === "ai" ? "Explained by AI, may be wrong. " : "Written from the numbers above. "}
              In an emergency, call 911.
            </p>
          </div>

          <Link href="/compare" className="btn secondary">Compare 8 PM vs 1 AM</Link>
          <SourcesPanel warnings={data.warnings} />
          <DisclaimerBanner compact />
          {hasAi ? <p className="caption center">Some explanations come from an AI.</p> : null}
        </div>
      </div>
    </div>
  );
}
