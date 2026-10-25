"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  DEFAULT_SETTINGS, EXTRA_MINUTE_STEPS, MAX_PRIORITIES, PRIORITY_OPTIONS, togglePriority, type Settings,
} from "@/lib/trip";

import { AppHeader } from "./AppHeader";
import { RefreshIcon } from "./Icons";
import { useTrip } from "./TripProvider";

export function PreferencesScreen({ next = "/plan" }: { next?: string }) {
  const router = useRouter();
  const { trip, ready, updateTrip } = useTrip();
  const [draft, setDraft] = useState<Settings | null>(null);
  const settings = draft ?? trip.settings;
  if (!ready) return <div className="screen" aria-busy="true" />;

  const set = (patch: Partial<Settings>) => setDraft({ ...settings, ...patch });
  const full = settings.priorities.length >= MAX_PRIORITIES;

  return (
    <div className="screen stack prefs-page">
      <AppHeader title="Route preferences" backHref={next} />

      <section className="card stack-sm" aria-labelledby="detour-h">
        <div className="row between">
          <h2 id="detour-h">Detour tolerance</h2>
          <span className="caption">Max added time</span>
        </div>
        <p className="stat-xl" style={{ color: "var(--mint)" }} aria-live="polite">
          {settings.maxExtraMinutes === 0 ? "No extra time" : `Up to ${settings.maxExtraMinutes} extra min`}
        </p>
        <p className="small muted">Compared with the fastest route.</p>
        <input
          type="range" className="slider" min={0} max={20} step={5} value={settings.maxExtraMinutes}
          aria-label="Maximum extra minutes" aria-valuetext={`${settings.maxExtraMinutes} minutes`}
          onChange={(e) => set({ maxExtraMinutes: Number(e.target.value) })}
        />
        <div className="slider-labels" aria-hidden="true">
          {EXTRA_MINUTE_STEPS.map((m) => (
            <span key={m} className={m === settings.maxExtraMinutes ? "current" : undefined}>{m}m</span>
          ))}
        </div>
      </section>

      <section className="card stack-sm" aria-labelledby="party-h">
        <h2 id="party-h">Walking with</h2>
        <div className="segmented" role="group" aria-labelledby="party-h">
          <button type="button" aria-pressed={!settings.withCompanion} onClick={() => set({ withCompanion: false })}>Alone</button>
          <button type="button" aria-pressed={settings.withCompanion} onClick={() => set({ withCompanion: true })}>With someone</button>
        </div>
        <p className="small muted">
          Walking with someone does not change the scores yet. Your choice is saved.
        </p>
      </section>

      <section className="card stack-sm" aria-labelledby="matter-h">
        <div className="row between">
          <h2 id="matter-h">What matters most?</h2>
          <span className="tag">{settings.priorities.length} / {MAX_PRIORITIES} selected</span>
        </div>
        <p className="small muted">Choose up to two. They count a little more in the score.</p>
        <div className="chips" role="group" aria-labelledby="matter-h">
          {PRIORITY_OPTIONS.map((o) => {
            const on = settings.priorities.includes(o.id);
            return (
              <button key={o.id} type="button" className="chip" aria-pressed={on} disabled={full && !on}
                style={full && !on ? { opacity: 0.5 } : undefined}
                onClick={() => set({ priorities: togglePriority(settings.priorities, o.id) })}>
                {on ? "✓ " : ""}{o.label}
              </button>
            );
          })}
        </div>
        <div className="banner">
          <h3>About past incidents</h3>
          <p className="small muted">
            Past incidents stay a small part of the score (5%). The record can reflect policing as much as events.
          </p>
        </div>
      </section>

      <section className="card stack-sm" aria-labelledby="checkin-h">
        <h2 id="checkin-h">Watch check-in</h2>
        <div className="segmented" role="group" aria-labelledby="checkin-h">
          <button type="button" aria-pressed={!settings.watchCheckIn} onClick={() => set({ watchCheckIn: false })}>
            Check-in off
          </button>
          <button type="button" aria-pressed={settings.watchCheckIn} onClick={() => set({ watchCheckIn: true })}>
            Check-in on
          </button>
        </div>
        <p className="small muted">
          When this is on, the walk asks you to check in every few minutes and on the darkest stretch, and the phone buzzes.
          That buzz is meant for a paired watch. This does not guarantee safety.
        </p>
      </section>

      <section className="card stack-sm" aria-labelledby="watch-link-h">
        <h2 id="watch-link-h">Watch check (optional)</h2>
        <p className="small muted">Try a heart-rate check with your Galaxy Watch or a simulated reading.</p>
        <Link href="/watch" className="btn secondary">Open watch check</Link>
      </section>

      <p className="small muted row"><RefreshIcon /> Applying changes recalculates your routes.</p>

      <div className="stack-sm">
        <button type="button" className="btn primary" onClick={() => { updateTrip({ settings }); router.push(next); }}>
          Apply preferences
        </button>
        <button type="button" className="btn ghost" onClick={() => setDraft(DEFAULT_SETTINGS)}>
          Reset to defaults
        </button>
      </div>
    </div>
  );
}
