"use client";

import { useEffect, useRef, useState } from "react";

import { formatMeters, formatMinutes } from "@/lib/format";
import { alertAhead } from "@/lib/nav/alerts";
import { pointAtDistance, routeLength, type LngLat } from "@/lib/nav/geo";
import { arrowRotation, chooseHeading, mapBearing, type HeadingMode } from "@/lib/nav/heading";
import { buzz, prefersReducedMotion, watchCompass, watchLocation, type GeoFix, type LocationStatus } from "@/lib/nav/sensors";
import { fetchMapboxSteps, navigationProgress, stepsFromGeometry, type NavStep } from "@/lib/nav/steps";
import type { Place, Route } from "@/lib/types";

import { NavMap } from "./NavMap";
import { StreetView } from "./StreetView";

const SIM_MPS = 22;

type Props = {
  route: Route;
  onClose: () => void;
  onReroute: (from: Place) => void;
  recalculating?: boolean;
};

export function NavigationScreen({ route, onClose, onReroute, recalculating = false }: Props) {
  const coords = route.geometry.coordinates as LngLat[];
  const [steps, setSteps] = useState<NavStep[]>(() => stepsFromGeometry(coords));
  const [simulated, setSimulated] = useState(false);
  const [simAlong, setSimAlong] = useState(0);
  const [fix, setFix] = useState<GeoFix | null>(null);
  const [locationStatus, setLocationStatus] = useState<LocationStatus | "waiting">("waiting");
  const [headingMode, setHeadingMode] = useState<HeadingMode>("north-up");
  const [compassDeg, setCompassDeg] = useState<number | null>(null);
  const [compassNote, setCompassNote] = useState<string | null>(null);
  const [hapticsOn, setHapticsOn] = useState(true);
  const [dismissedOff, setDismissedOff] = useState(false);
  const [streetOpen, setStreetOpen] = useState(false);
  const wasOffRef = useRef(false);
  const lastBuzz = useRef<string>("");
  const reducedMotion = prefersReducedMotion();

  useEffect(() => {
    setSteps(stepsFromGeometry(coords));
    setSimAlong(0);
    wasOffRef.current = false;
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";
    const ctl = new AbortController();
    void fetchMapboxSteps(coords, token, ctl.signal).then((next) => {
      if (next && !ctl.signal.aborted) setSteps(next);
    });
    return () => ctl.abort();
  }, [route.route_id, coords]);

  useEffect(() => {
    if (simulated) return;
    let stop = () => {};
    let dead = false;
    void watchLocation(
      (next) => { if (!dead) setFix(next); },
      (status) => { if (!dead) setLocationStatus(status); },
    ).then((handle) => {
      if (dead) handle.stop();
      else stop = handle.stop;
    });
    return () => { dead = true; stop(); };
  }, [simulated]);

  useEffect(() => {
    if (!simulated) return;
    const timer = window.setInterval(() => {
      setSimAlong((along) => Math.min(routeLength(coords), along + SIM_MPS * 0.2));
    }, 200);
    return () => window.clearInterval(timer);
  }, [simulated, coords]);

  const simPoint = pointAtDistance(coords, simAlong);
  const user: LngLat = simulated
    ? simPoint.point
    : fix
      ? [fix.lng, fix.lat]
      : coords[0] ?? [0, 0];
  const progress = navigationProgress(coords, steps, user, wasOffRef.current);
  wasOffRef.current = progress.offRoute;

  useEffect(() => {
    if (!progress.offRoute) setDismissedOff(false);
  }, [progress.offRoute]);

  const heading = chooseHeading(compassDeg, simulated ? simPoint.bearing : fix?.course ?? null);
  const bearing = mapBearing(heading.degrees, headingMode);
  const arrow = arrowRotation(heading.degrees, headingMode);
  const alert = alertAhead(route, progress.alongM);
  const showOff = progress.offRoute && !simulated && !dismissedOff && !recalculating;
  const remainingMin = route.duration_min * progress.remainingFraction;
  const buzzKey = `${progress.stepIndex}:${showOff ? "off" : ""}:${alert?.kind ?? ""}`;

  useEffect(() => {
    if (lastBuzz.current === buzzKey) return;
    const previous = lastBuzz.current;
    lastBuzz.current = buzzKey;
    if (!previous) return;
    void buzz(hapticsOn);
  }, [buzzKey, hapticsOn]);

  async function toggleHeading() {
    if (headingMode === "heading-up") {
      setHeadingMode("north-up");
      return;
    }
    const handle = await watchCompass((degrees) => setCompassDeg(degrees));
    if (handle.status === "denied") {
      setCompassNote("Compass permission is off. The map stays north up.");
      return;
    }
    if (handle.status === "unavailable") {
      setCompassNote("This device has no compass. Using direction of travel when GPS has it.");
    } else {
      setCompassNote(null);
    }
    setHeadingMode("heading-up");
  }

  const locationNote = simulated
    ? "Simulated"
    : locationStatus === "denied"
      ? "Location is off. You can simulate the walk."
      : locationStatus === "unavailable"
        ? "Location is unavailable. You can simulate the walk."
        : locationStatus === "waiting"
          ? "Waiting for location."
          : heading.source === "none"
            ? "Heading: not sure"
            : heading.source === "course"
              ? "Using direction of travel"
              : "Using the compass";

  return (
    <div className="nav-screen">
      <div className="nav-banner" role="region" aria-label="Next maneuver">
        <p className="nav-meters">{formatMeters(progress.distanceToManeuverM)}</p>
        <h2>{recalculating ? "Recalculating the walk from here" : progress.instruction}</h2>
        <p>{progress.street ?? "Street name: not sure"}</p>
        <p className="nav-remain">
          {formatMinutes(remainingMin)} left · {formatMeters(progress.remainingDistanceM)}
        </p>
        <p className="nav-note">{locationNote}</p>
      </div>

      {alert && !showOff ? (
        <div className="nav-alert" role="status">
          <strong>{alert.title}</strong>
          <p>{alert.detail}</p>
        </div>
      ) : null}

      {showOff ? (
        <div className="nav-prompt" role="alertdialog" aria-label="Off the route">
          <strong>You are away from this route.</strong>
          <p>Recalculate the walk from here?</p>
          <div className="nav-prompt-actions">
            <button type="button" className="btn primary" onClick={() => onReroute({
              id: "nav-here", name: "Your location", lat: user[1], lng: user[0],
            })}>Recalculate</button>
            <button type="button" className="btn secondary" onClick={() => setDismissedOff(true)}>Keep this route</button>
          </div>
        </div>
      ) : null}

      <NavMap coords={coords} user={user} mapBearing={bearing} arrowDeg={arrow} reducedMotion={reducedMotion} />

      <div className="nav-dock">
        <button type="button" className="btn secondary" onClick={onClose}>End</button>
        <button type="button" className="btn secondary" aria-pressed={simulated}
          onClick={() => { setSimulated((on) => !on); setSimAlong(progress.alongM); }}>
          {simulated ? "Stop simulation" : "Simulate walk"}
        </button>
        <button type="button" className="btn secondary" aria-pressed={headingMode === "heading-up"} onClick={() => void toggleHeading()}>
          {headingMode === "heading-up" ? "Heading up" : "North up"}
        </button>
        <button type="button" className="btn secondary" onClick={() => setStreetOpen(true)}>Street view</button>
        <button type="button" className="btn secondary" aria-pressed={hapticsOn} onClick={() => setHapticsOn((on) => !on)}>
          {hapticsOn ? "Vibrate on" : "Vibrate off"}
        </button>
      </div>
      {compassNote ? <p className="nav-compass-note">{compassNote}</p> : null}

      {streetOpen ? (
        <StreetView
          route={route}
          entry={{ lng: user[0], lat: user[1], darkest: false }}
          onClose={() => setStreetOpen(false)}
          onPosition={() => {}}
        />
      ) : null}
    </div>
  );
}
