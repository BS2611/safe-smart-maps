"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { describeError, devFixturesEnabled } from "@/lib/api";
import {
  fetchedAgo, formatClock, formatDayClock, formatMeters, formatMinutes, formatPercent, viaText,
} from "@/lib/format";
import { compareTimes, primaryRoute } from "@/lib/routeStats";
import { tonightTimes } from "@/lib/time";
import { isReady, type Trip } from "@/lib/trip";
import { useRoutes } from "@/lib/useRoutes";

import { AppHeader } from "./AppHeader";
import { Banner } from "./Banner";
import { CheckingScreen } from "./CheckingScreen";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { MapLegend } from "./MapLegend";
import { RouteMap } from "./RouteMap";
import { useTrip } from "./TripProvider";

export function CompareScreen({ now }: { now?: Date }) {
  const router = useRouter();
  const { trip, ready, updateTrip } = useTrip();
  const times = useMemo(() => tonightTimes(now ?? new Date()), [now]);
  const early: Trip = { ...trip, departISO: times.eightPm.toISOString() };
  const late: Trip = { ...trip, departISO: times.oneAm.toISOString() };
  const a = useRoutes(early);
  const b = useRoutes(late);
  const [which, setWhich] = useState<"early" | "late">("early");

  if (!ready) return <div className="screen" aria-busy="true" />;
  if (!isReady(trip)) {
    return (
      <div className="screen stack">
        <AppHeader title="The same walk, later" backHref="/plan" />
        <Banner kind="info" title="Choose a start and a destination first">
          <Link href="/plan" style={{ textDecoration: "underline" }}>Plan a walk</Link> to compare 8 PM with 1 AM.
        </Banner>
      </div>
    );
  }

  const loading = ["idle", "loading"].includes(a.state.status) || ["idle", "loading"].includes(b.state.status);
  if (loading && a.state.status !== "error" && b.state.status !== "error") {
    return <CheckingScreen trip={{ ...trip, departISO: times.eightPm.toISOString() }}
      onCancel={() => { a.cancel(); b.cancel(); }} />;
  }
  if (a.state.status === "error" || b.state.status === "error") {
    const error = a.state.status === "error" ? a.state.error : (b.state as { error: Error }).error;
    return (
      <div className="screen stack">
        <AppHeader title="The same walk, later" backHref="/routes" />
        <Banner kind="error" title="We could not compare the two times">{describeError(error)}</Banner>
        <button type="button" className="btn primary" onClick={() => { a.retry(); b.retry(); }}>Try again</button>
        <Link href="/routes" className="btn secondary">Back to routes</Link>
      </div>
    );
  }
  if (a.state.status !== "success" || b.state.status !== "success") return null;

  const dataA = a.state.data;
  const dataB = b.state.data;
  const pa = primaryRoute(dataA);
  const pb = primaryRoute(dataB);
  const diff = compareTimes(dataA, dataB);
  const shown = which === "early" ? dataA : dataB;
  const shownRoute = which === "early" ? pa : pb;
  const rows: { label: string; sub: string; a: string; b: string; worse: boolean | null }[] = [
    { label: "Primary route", sub: "Most lit & active", a: viaText(pa.via) || "—", b: viaText(pb.via) || "—", worse: null },
    { label: "Walk duration", sub: "Estimated pace", a: formatMinutes(pa.duration_min), b: formatMinutes(pb.duration_min), worse: pb.duration_min > pa.duration_min },
    { label: "Coverage", sub: "Within 75 m of an open place", a: formatPercent(pa.continuity.coverage_pct), b: formatPercent(pb.continuity.coverage_pct),
      worse: diff.coverageDelta === null ? null : diff.coverageDelta < 0 },
    { label: "Longest gap", sub: "No open place nearby", a: formatMeters(pa.continuity.longest_gap_m), b: formatMeters(pb.continuity.longest_gap_m),
      worse: pb.continuity.longest_gap_m > pa.continuity.longest_gap_m },
    { label: "Open places", sub: "When you arrive", a: String(pa.open_places_count ?? "Not sure"), b: String(pb.open_places_count ?? "Not sure"),
      worse: pa.open_places_count !== null && pb.open_places_count !== null ? pb.open_places_count < pa.open_places_count : null },
    { label: "Lowest 200 m", sub: "Weakest stretch score", a: pa.continuity.worst_window_score === null ? "Not sure" : String(Math.round(pa.continuity.worst_window_score)),
      b: pb.continuity.worst_window_score === null ? "Not sure" : String(Math.round(pb.continuity.worst_window_score)),
      worse: pa.continuity.worst_window_score !== null && pb.continuity.worst_window_score !== null
        ? pb.continuity.worst_window_score < pa.continuity.worst_window_score : null },
  ];
  const warnings = [...new Set([...dataA.warnings, ...dataB.warnings])];

  return (
    <div className="screen stack">
      <AppHeader title="The same walk, later" subtitle="Places may close before you reach them." backHref="/routes" />
      {devFixturesEnabled() ? <Banner kind="warn" title="Sample data">Saved sample data for design review, not a live check.</Banner> : null}
      <div className="card tight">
        <strong>{trip.from?.name} → {trip.to?.name}</strong>
        <p className="small muted">Up to {trip.settings.maxExtraMinutes} min extra · Los Angeles time zone</p>
      </div>

      <div className="tabs" role="group" aria-label="Departure time">
        <button type="button" className="tab" aria-pressed={which === "early"} onClick={() => setWhich("early")}>
          <span className="t">{formatClock(times.eightPm.toISOString())} · Tonight</span><br />
          <span className="c">{formatPercent(pa.continuity.coverage_pct)} coverage</span>
        </button>
        <button type="button" className="tab" aria-pressed={which === "late"} onClick={() => setWhich("late")}>
          <span className="t">{formatDayClock(times.oneAm.toISOString())}</span><br />
          <span className="c">
            {formatPercent(pb.continuity.coverage_pct)} coverage{diff.coverageDelta !== null && diff.coverageDelta !== 0 ? ` (${diff.coverageDelta > 0 ? "+" : ""}${diff.coverageDelta}%)` : ""}
          </span>
        </button>
      </div>

      <RouteMap routes={shown.routes} selectedId={shownRoute.route_id} />
      <MapLegend />

      <section className="card stack-sm" aria-labelledby="key-h">
        <div className="row between">
          <h2 id="key-h">Key difference at {formatClock(times.oneAm.toISOString())}</h2>
          {diff.routeChanged ? <span className="tag warn">Route changes</span> : null}
        </div>
        <p>{diff.headline}</p>
        <p className="small muted">{diff.detail}</p>
      </section>

      <section aria-labelledby="tbl-h">
        <h2 id="tbl-h" style={{ marginBottom: 8 }}>Route comparison</h2>
        <table className="compare">
          <thead>
            <tr><th scope="col">Metric</th><th scope="col">8 PM</th><th scope="col">1 AM</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <td>{r.label}<span className="sub">{r.sub}</span></td>
                <td>{r.a}</td>
                <td className={r.worse === true ? "worse" : r.worse === false ? "better" : undefined}>
                  {r.b}{r.worse === true ? " ▼" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="caption" style={{ marginTop: 6 }}>{fetchedAgo(dataB.data_fetched_at)}</p>
      </section>

      {warnings.length ? (
        <Banner kind="warn" title="Some information is missing">
          <ul style={{ margin: 0, paddingLeft: 18 }}>{warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Banner>
      ) : null}

      <div className="stack-sm sticky-cta">
        <button type="button" className="btn primary"
          onClick={() => { updateTrip({ departISO: times.eightPm.toISOString() }); router.push("/routes"); }}>
          Use 8:00 PM departure
        </button>
        <button type="button" className="btn secondary"
          onClick={() => { updateTrip({ departISO: times.oneAm.toISOString() }); router.push("/routes"); }}>
          Use 1:00 AM departure
        </button>
        <p className="caption center">Recalculates open places and routes for the time you choose.</p>
      </div>
      <DisclaimerBanner compact />
    </div>
  );
}
