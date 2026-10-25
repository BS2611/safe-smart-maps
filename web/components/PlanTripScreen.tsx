"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { DEMO_PLACES } from "@/lib/places";
import { isReady } from "@/lib/trip";

import { AppHeader } from "./AppHeader";
import { DepartureField } from "./DepartureField";
import { SlidersIcon, SwapIcon } from "./Icons";
import { PlaceField } from "./PlaceField";
import { useTrip } from "./TripProvider";

export function PlanTripScreen() {
  const router = useRouter();
  const { trip, ready, updateTrip } = useTrip();

  function showRoutes() {
    // Fix "leave now" to a real instant so results, back button and retry all use the same time.
    updateTrip({ departISO: trip.departISO ?? new Date().toISOString() });
    router.push("/routes");
  }

  if (!ready) return <div className="screen" aria-busy="true" />;

  return (
    <div className="screen plan-page">
      <AppHeader title="Plan your walk" backHref="/" right={
        <Link href="/preferences" className="icon-btn" aria-label="Route preferences"><SlidersIcon /></Link>
      } />
      <div className="plan-layout">
      <div className="stack">
      <div className="card stack">
        <PlaceField
          label="From" value={trip.from} onChange={(from) => updateTrip({ from })}
          presets={DEMO_PLACES.filter((p) => p.id !== trip.to?.id)} placeholder="Start address or landmark"
          allowMyLocation
        />
        <div className="row" style={{ justifyContent: "center" }}>
          <button type="button" className="icon-btn" aria-label="Swap start and destination"
            onClick={() => updateTrip({ from: trip.to, to: trip.from })}><SwapIcon /></button>
        </div>
        <PlaceField
          label="To" value={trip.to} onChange={(to) => updateTrip({ to })}
          presets={DEMO_PLACES.filter((p) => p.id !== trip.from?.id)} placeholder="Destination address or landmark"
        />
      </div>
      <div className="card">
        <DepartureField value={trip.departISO} onChange={(departISO) => updateTrip({ departISO })} />
      </div>
      <p className="caption">
        Live data covers the demo area around Palace of Fine Arts and Montgomery BART. Trips up to about 5 km.
      </p>
      <div className="sticky-cta">
        <button type="button" className="btn primary" disabled={!isReady(trip)} onClick={showRoutes}>
          Show routes
        </button>
      </div>
      </div>
      <aside className="plan-aside card stack-sm">
        <p className="eyebrow">Demo corridor</p>
        <h2>A real late walk</h2>
        <p className="muted">Palace of Fine Arts to Montgomery BART. The score follows the minute you will be on each street.</p>
        <ol className="steps">
          <li>Set the start and the destination.</li>
          <li>Leave now, at 8 PM this evening, or at 1 AM after midnight.</li>
          <li>Read the score, the empty stretches, and the reasons.</li>
        </ol>
        <p className="caption">The same walk later shows what has closed.</p>
      </aside>
      </div>
    </div>
  );
}
