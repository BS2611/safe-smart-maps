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
    <div className="screen stack">
      <AppHeader title="Plan your walk" backHref="/" right={
        <Link href="/preferences" className="icon-btn" aria-label="Route preferences"><SlidersIcon /></Link>
      } />
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
  );
}
