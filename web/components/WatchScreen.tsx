"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { sourceLabel, createSimulatedSource, isSimulated, type ReadingSource, type WatchReading } from "@/lib/watch";
import {
  createRelaySource, endTrip, LOST_AFTER_MS, startPairing, type PairingInfo, type RelayOptions,
} from "@/lib/watchRelay";

import { AppHeader } from "./AppHeader";
import { Banner } from "./Banner";
import { DisclaimerBanner } from "./DisclaimerBanner";

const STEPS = [
  "Install the Safe Smart Maps app on your Galaxy Watch (Watch 4 or newer).",
  "Open it on the watch.",
  "Type the 6-digit code shown here.",
];

type Link = "none" | "waiting" | "connected";

function clock(totalSeconds: number): string {
  const s = Math.max(0, totalSeconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function WatchScreen({
  makeSource = () => createSimulatedSource(),
  relay = {},
}: { makeSource?: () => ReadingSource; relay?: RelayOptions }) {
  const [optedIn, setOptedIn] = useState(false);
  const [reading, setReading] = useState<WatchReading | null>(null);
  const [pairing, setPairing] = useState<PairingInfo | null>(null);
  const [link, setLink] = useState<Link>("none");
  const [problem, setProblem] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [alertNote, setAlertNote] = useState<string | null>(null);
  const [okNote, setOkNote] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const sourceRef = useRef<ReadingSource | null>(null);
  const tripRef = useRef<string | null>(null);
  const expiresAt = useRef(0);
  const lastReadingAt = useRef(0);
  const relayRef = useRef(relay);

  const stopAll = useCallback(() => {
    sourceRef.current?.stop();
    sourceRef.current = null;
    if (tripRef.current) void endTrip(tripRef.current, relayRef.current);
    tripRef.current = null;
    setReading(null);
    setPairing(null);
    setLink("none");
    setProblem(null);
    setAsking(false);
    setAlertNote(null);
    setOkNote(false);
  }, []);

  // Readings are never kept: stop, tell the server to delete them, and forget when the screen closes.
  useEffect(() => () => {
    sourceRef.current?.stop();
    if (tripRef.current) void endTrip(tripRef.current, relayRef.current);
  }, []);

  const running = reading !== null;
  const usingRelay = pairing !== null;
  useEffect(() => {
    if (!usingRelay) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [usingRelay]);

  const getCode = async () => {
    stopAll();
    setProblem(null);
    try {
      const info = await startPairing(relayRef.current);
      tripRef.current = info.tripId;
      expiresAt.current = Date.now() + info.expiresInS * 1000;
      setNow(Date.now());
      setPairing(info);
      setLink("waiting");
      const src = createRelaySource(info.tripId, {
        onEvent: (e) => {
          if (e.type === "paired") setLink("connected");
          if (e.type === "prompt") { setAsking(true); setOkNote(false); }
          if (e.type === "alert_sent") {
            setAsking(false);
            setAlertNote("Alert would be sent to your contact (demo, not sent).");
          }
          if (e.type === "ack") { setAsking(false); setOkNote(Boolean(e.ok)); setAlertNote(null); }
        },
        onError: (err) => {
          if (err.kind === "NOT_FOUND") { setProblem("The watch check ended. Get a new code to start again."); setLink("none"); }
          else setProblem("Cannot reach the server right now. Trying again…");
        },
      }, relayRef.current);
      sourceRef.current = src;
      src.start((r) => { lastReadingAt.current = Date.now(); setProblem(null); setReading(r); });
    } catch {
      setProblem("We could not get a pairing code. Check your connection and try again.");
    }
  };

  const startSimulated = () => {
    stopAll();
    const src = makeSource();
    sourceRef.current = src;
    src.start(setReading);
  };

  const connected = link === "connected";
  const lost = connected && reading !== null && now - lastReadingAt.current > LOST_AFTER_MS;
  const secondsLeft = Math.ceil((expiresAt.current - now) / 1000);
  const codeExpired = link === "waiting" && secondsLeft <= 0;

  return (
    <div className="screen stack">
      <AppHeader title="Watch check" subtitle="Optional" backHref="/preferences" />

      <section className="card stack-sm" aria-labelledby="optin-h">
        <h2 id="optin-h">Heart-rate check</h2>
        <p className="small muted">
          Uses your heart rate during this walk only. It stays in memory and is deleted when you stop.
        </p>
        <div className="segmented" role="group" aria-labelledby="optin-h">
          <button type="button" aria-pressed={!optedIn} onClick={() => { stopAll(); setOptedIn(false); }}>Off</button>
          <button type="button" aria-pressed={optedIn} onClick={() => setOptedIn(true)}>On</button>
        </div>
      </section>

      <section className="card stack-sm" aria-labelledby="watch-h">
        <h2 id="watch-h">Galaxy Watch</h2>
        <ol className="small muted" style={{ paddingLeft: 20 }}>
          {STEPS.map((s) => <li key={s}>{s}</li>)}
        </ol>
        {pairing && link !== "connected" ? (
          <div className="stack-sm">
            <p className="caption">Pairing code</p>
            <p aria-label={`Pairing code ${pairing.pairCode.split("").join(" ")}`}
              style={{ fontSize: 40, fontWeight: 600, letterSpacing: 6 }}>{pairing.pairCode}</p>
            <p className="caption">{codeExpired ? "This code expired." : `Valid for ${clock(secondsLeft)}`}</p>
          </div>
        ) : null}
        <div role="status" aria-live="polite" className="small">
          {link === "waiting" ? "Waiting for the watch…" : null}
          {connected && !lost ? <strong>Connected: Galaxy Watch</strong> : null}
          {connected && lost ? "No reading for 15 seconds. Check the watch." : null}
          {link === "none" && !problem ? <span className="muted">Not connected.</span> : null}
          {problem ? <span>{problem}</span> : null}
        </div>
        {usingRelay ? (
          <button type="button" className="btn secondary" onClick={stopAll}>Stop and delete readings</button>
        ) : (
          <button type="button" className="btn primary" disabled={!optedIn} onClick={getCode}>Get pairing code</button>
        )}
      </section>

      {asking ? (
        <Banner kind="warn" title="Your watch is asking: are you OK?">
          Answer on the watch. If there is no answer, an alert would go to your contact.
        </Banner>
      ) : null}
      {alertNote ? <Banner kind="warn" title="Alert triggered">{alertNote}</Banner> : null}
      {okNote ? <Banner kind="info" title="You said you are OK">No alert was sent.</Banner> : null}

      <section className="card stack-sm" aria-labelledby="sim-h">
        <h2 id="sim-h">{usingRelay ? "Live reading" : "Try a simulated reading"}</h2>
        <div role="status" aria-live="polite">
          {running ? (
            <div className="stack-sm">
              <p style={{ fontSize: 40, fontWeight: 600 }}>
                {reading.bpm} <span className="small muted">bpm</span>
                <span className="badge">{sourceLabel(reading.source)}</span>
              </p>
              <p className="caption">
                {isSimulated(reading.source) ? "Not a real reading. " : ""}
                Last update {new Date(reading.ts).toLocaleTimeString()}.
              </p>
            </div>
          ) : (
            <p className="small muted">
              {usingRelay ? "Waiting for the first reading." : optedIn ? "Not running." : "Turn the check on to try it."}
            </p>
          )}
        </div>
        {!usingRelay ? (
          running ? (
            <button type="button" className="btn secondary" onClick={stopAll}>Stop and delete readings</button>
          ) : (
            <button type="button" className="btn primary" disabled={!optedIn} onClick={startSimulated}>
              Start simulated reading
            </button>
          )
        ) : null}
      </section>

      <Banner kind="info" title="What this check does">
        It can notice an unusual heart rate during a walk and ask if you are OK. It is not a medical tool and does not
        replace calling 911. Sending an alert to a contact is not built yet.
      </Banner>
      <DisclaimerBanner compact />
    </div>
  );
}
