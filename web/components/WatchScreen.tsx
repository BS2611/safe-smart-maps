"use client";

import { useEffect, useRef, useState } from "react";

import { createSimulatedSource, sourceLabel, type ReadingSource, type WatchReading } from "@/lib/watch";

import { AppHeader } from "./AppHeader";
import { Banner } from "./Banner";
import { DisclaimerBanner } from "./DisclaimerBanner";

const STEPS = [
  "Install the Safe Smart Maps app on your Galaxy Watch (Watch 4 or newer).",
  "Open it on the watch and choose Pair.",
  "Type the 6-digit code from this screen.",
];

export function WatchScreen({ makeSource = () => createSimulatedSource() }: { makeSource?: () => ReadingSource }) {
  const [optedIn, setOptedIn] = useState(false);
  const [reading, setReading] = useState<WatchReading | null>(null);
  const sourceRef = useRef<ReadingSource | null>(null);
  const running = reading !== null;

  const stop = () => {
    sourceRef.current?.stop();
    sourceRef.current = null;
    setReading(null);
  };
  const start = () => {
    const src = makeSource();
    sourceRef.current = src;
    src.start(setReading);
  };
  // Readings are never kept: stop and forget when the screen closes.
  useEffect(() => () => sourceRef.current?.stop(), []);

  return (
    <div className="screen stack">
      <AppHeader title="Watch check" subtitle="Optional" backHref="/preferences" />

      <section className="card stack-sm" aria-labelledby="optin-h">
        <h2 id="optin-h">Heart-rate check</h2>
        <p className="small muted">
          Uses your heart rate during this walk only. It stays in memory on your phone and is deleted when you stop.
        </p>
        <div className="segmented" role="group" aria-labelledby="optin-h">
          <button type="button" aria-pressed={!optedIn} onClick={() => { stop(); setOptedIn(false); }}>Off</button>
          <button type="button" aria-pressed={optedIn} onClick={() => setOptedIn(true)}>On</button>
        </div>
      </section>

      <section className="card stack-sm" aria-labelledby="watch-h">
        <div className="row between">
          <h2 id="watch-h">Galaxy Watch</h2>
          <span className="tag">Not available yet</span>
        </div>
        <ol className="small muted" style={{ paddingLeft: 20 }}>
          {STEPS.map((s) => <li key={s}>{s}</li>)}
        </ol>
        <label className="small" htmlFor="pair-code">Pairing code</label>
        <input id="pair-code" className="input" inputMode="numeric" placeholder="------" disabled
          aria-describedby="pair-note" />
        <p id="pair-note" className="caption">
          The watch app is not built yet, so a real watch cannot connect. Use the simulated reading below to try the screen.
        </p>
      </section>

      <section className="card stack-sm" aria-labelledby="sim-h">
        <h2 id="sim-h">Try a simulated reading</h2>
        <div role="status" aria-live="polite">
          {running ? (
            <div className="stack-sm">
              <p style={{ fontSize: 40, fontWeight: 600 }}>
                {reading.bpm} <span className="small muted">bpm</span>
                <span className="badge">{sourceLabel(reading.source)}</span>
              </p>
              <p className="caption">Not a real reading. Last update {new Date(reading.ts).toLocaleTimeString()}.</p>
            </div>
          ) : (
            <p className="small muted">{optedIn ? "Not running." : "Turn the check on to try it."}</p>
          )}
        </div>
        {running ? (
          <button type="button" className="btn secondary" onClick={stop}>Stop and delete readings</button>
        ) : (
          <button type="button" className="btn primary" disabled={!optedIn} onClick={start}>Start simulated reading</button>
        )}
      </section>

      <Banner kind="info" title="What this check does">
        It can notice an unusual heart rate during a walk and ask if you are OK. It is not a medical tool and does not
        replace calling 911. Sending an alert to a contact is not built yet.
      </Banner>
      <DisclaimerBanner compact />
    </div>
  );
}
