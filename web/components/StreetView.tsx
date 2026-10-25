"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { BAND_TEXT, fetchedAgo, formatClock, formatDayClock } from "@/lib/format";
import { makeProjector, pathFor } from "@/lib/geometry";
import {
  darkestSegmentIndex, forwardBearing, nearestIndex, nearestSegmentIndex, sampleRoute,
} from "@/lib/streetview/geo";
import { selectStreetViewProvider, streetViewSourceName } from "@/lib/streetview/provider";
import { StreetViewError, type StreetViewHandle, type StreetViewPhoto, type StreetViewProvider } from "@/lib/streetview/types";
import type { Route } from "@/lib/types";

type Entry = { lng: number; lat: number; darkest: boolean };
type Phase = "loading" | "ready" | "empty" | "unavailable" | "failed";

function prefersReducedMotion(): boolean {
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function photoTime(value: string | null): string {
  if (!value) return "Photo time: not sure";
  if (/^\d{4}-\d{2}$/.test(value)) return `Photo from ${value}`;
  const time = new Date(value);
  if (Number.isNaN(time.getTime())) return "Photo time: not sure";
  return `Photo from ${formatDayClock(value)}`;
}

function MiniMap({ route, lng, lat, heading }: { route: Route; lng: number; lat: number; heading: number }) {
  const width = 168;
  const height = 112;
  const project = makeProjector([route], width, height, 16);
  const [x, y] = project(lng, lat);
  const deg = Math.round(((heading % 360) + 360) % 360);
  return (
    <svg className="sv-mini" viewBox={`0 0 ${width} ${height}`} role="img"
      aria-label={`Mini map. You are on the route. Heading ${deg} degrees. 0 is north.`}>
      <rect width={width} height={height} rx="12" fill="#07110e" />
      <text x="12" y="16" fill="#d7efe4" fontSize="11" fontWeight="700">N</text>
      <path d={pathFor(route.geometry.coordinates, project)} stroke="#a5f2d7" strokeWidth="3" fill="none"
        strokeLinecap="round" strokeLinejoin="round" />
      <g transform={`translate(${x.toFixed(1)} ${y.toFixed(1)})`}>
        <circle r="4" fill="#ff9b7a" stroke="#07110e" strokeWidth="1.5" />
        <g transform={`rotate(${deg})`}>
          <path d="M0 -16 L7 7 L0 3 L-7 7 Z" fill="#f4fff9" stroke="#07110e" strokeWidth="1" />
        </g>
      </g>
    </svg>
  );
}

export function StreetView({
  route, entry, onClose, onPosition, provider,
}: {
  route: Route;
  entry: Entry;
  onClose: () => void;
  onPosition: (lng: number, lat: number, segmentIndex: number) => void;
  provider?: StreetViewProvider;
}) {
  const resolved = useMemo(() => provider ?? selectStreetViewProvider(), [provider]);
  const samples = useMemo(() => sampleRoute(route.geometry.coordinates, 25), [route]);
  const [cursor, setCursor] = useState(() => nearestIndex(samples, entry.lng, entry.lat));
  const [phase, setPhase] = useState<Phase>(resolved.configured ? "loading" : "unavailable");
  const [photo, setPhoto] = useState<StreetViewPhoto | null>(null);
  const [viewerFailed, setViewerFailed] = useState(false);
  const [heading, setHeading] = useState(() => forwardBearing(samples, nearestIndex(samples, entry.lng, entry.lat)));
  const canvasRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onPositionRef = useRef(onPosition);
  onPositionRef.current = onPosition;
  const cursorRef = useRef(cursor);
  cursorRef.current = cursor;
  const indexed = samples[Math.max(0, Math.min(samples.length - 1, cursor))];
  const lng = indexed ? indexed[0] : entry.lng;
  const lat = indexed ? indexed[1] : entry.lat;
  const segmentIndex = nearestSegmentIndex(route.segments, lng, lat);
  const seg = route.segments[segmentIndex];
  const darkest = darkestSegmentIndex(route.segments);

  useEffect(() => {
    const previous = document.activeElement;
    closeRef.current?.focus();
    return () => {
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);

  useEffect(() => {
    setHeading(forwardBearing(samples, cursor));
  }, [samples, cursor]);

  useEffect(() => {
    onPositionRef.current(lng, lat, segmentIndex);
  }, [lng, lat, segmentIndex]);

  useEffect(() => {
    if (!resolved.configured) {
      setPhase("unavailable");
      setPhoto(null);
      return;
    }
    const ac = new AbortController();
    let dead = false;
    setPhase("loading");
    setViewerFailed(false);
    resolved.findNearest(lng, lat, ac.signal).then((hit) => {
      if (dead) return;
      setPhoto(hit);
      setPhase(hit ? "ready" : "empty");
    }).catch((err: unknown) => {
      if (dead || ac.signal.aborted) return;
      const kind = err instanceof StreetViewError ? err.kind : "failed";
      setPhoto(null);
      setPhase(kind === "unavailable" ? "unavailable" : "failed");
    });
    return () => {
      dead = true;
      ac.abort();
    };
  }, [resolved, lng, lat]);

  useEffect(() => {
    if (phase !== "ready" || !photo || !canvasRef.current) return;
    const container = canvasRef.current;
    let dead = false;
    let handle: StreetViewHandle | null = null;
    resolved.mount({
      container,
      photo,
      heading: forwardBearing(samples, cursorRef.current),
      reducedMotion: prefersReducedMotion(),
      onHeading: (degrees) => { if (!dead) setHeading(degrees); },
    }).then((next) => {
      if (dead) next.destroy();
      else handle = next;
    }).catch(() => {
      if (!dead) setViewerFailed(true);
    });
    return () => {
      dead = true;
      handle?.destroy();
    };
  }, [resolved, phase, photo, samples]);

  function step(dir: -1 | 1) {
    setCursor((current) => Math.max(0, Math.min(samples.length - 1, current + dir)));
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      step(1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      step(-1);
    }
  }

  const message = viewerFailed || phase === "failed"
    ? "Street view could not load this spot."
    : phase === "unavailable"
      ? "Street view is unavailable."
      : phase === "empty"
        ? "No street-level photo near this spot."
        : phase === "loading"
          ? "Looking for a street-level photo…"
          : null;
  const scoreLine = !seg
    ? "Not sure"
    : seg.score === null
      ? BAND_TEXT[seg.band]
      : `${BAND_TEXT[seg.band]} · ${Math.round(seg.score)} / 100`;

  return (
    <div className="street-view" role="dialog" aria-modal="true" aria-labelledby="sv-title" onKeyDown={onKeyDown}>
      <div className="sv-stage">
        <div ref={canvasRef} className="sv-canvas" />
        {message ? (
          <p className="sv-message" role="status">
            {message}
            {phase === "unavailable" ? " The rest of this walk still works." : ""}
            {phase === "empty" ? " Step along the route to try another spot." : ""}
          </p>
        ) : null}
        <section className="sv-card" aria-label="This stretch">
          <h2 id="sv-title">Street view</h2>
          <p className="sv-score">{scoreLine}</p>
          {entry.darkest && darkest !== null && segmentIndex === darkest
            ? <p className="caption">Darkest stretch on this route.</p> : null}
          {seg ? (
            <p className="caption">You reach this part at about {formatClock(seg.arrival_time)}.</p>
          ) : null}
          <ul className="reasons" aria-label="Reasons for this stretch">
            {(seg?.reasons ?? []).map((reason, i) => <li key={`${reason}-${i}`}>{reason}</li>)}
          </ul>
          <p className="caption">{photo ? photoTime(photo.capturedAt) : "Photo time: not sure"}</p>
          <p className="caption">{seg ? fetchedAgo(seg.data_fetched_at) : "Data time not available"}</p>
          {phase === "ready" && !viewerFailed ? <p className="caption">Drag the photo to look around.</p> : null}
          <p className="caption">Photos: {streetViewSourceName(resolved.id)}. We describe conditions. We do not guarantee safety.</p>
        </section>
        <MiniMap route={route} lng={lng} lat={lat} heading={heading} />
        <div className="sv-navs">
          <button type="button" className="sv-step" onClick={() => step(-1)} disabled={cursor <= 0}>
            Back along the route
          </button>
          <button type="button" className="sv-step" onClick={() => step(1)} disabled={cursor >= samples.length - 1}>
            Forward along the route
          </button>
        </div>
        <button ref={closeRef} type="button" className="icon-btn sv-close" onClick={onClose} aria-label="Close street view">
          <span aria-hidden="true">×</span>
        </button>
      </div>
    </div>
  );
}
