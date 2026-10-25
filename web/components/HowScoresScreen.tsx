import { AppHeader } from "./AppHeader";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { CONTINUITY_RULES, FACTORS, SCORE_FORMULA } from "@/lib/scoring-info";
import Link from "next/link";

export function HowScoresScreen({ backHref = "/" }: { backHref?: string }) {
  return (
    <div className="screen stack guide-page">
      <AppHeader title="How scores work" subtitle="What we check and what we cannot know" backHref={backHref} />

      <section className="card stack-sm guide-intro" aria-labelledby="intro-h">
        <h2 id="intro-h">Street conditions along your walk</h2>
        <p className="muted">
          We look at each stretch of about 50 m, at the time you will reach it, and combine eight checks.
          The result describes conditions. It is not a promise.
        </p>
      </section>

      <div className="guide-grid">
      <section className="card stack-sm" aria-labelledby="checks-h">
        <div className="row between">
          <h2 id="checks-h">1. What we check</h2>
          <span className="tag">100% total</span>
        </div>
        <div className="weight-bar" aria-hidden="true">
          {FACTORS.map((f) => <span key={f.id} style={{ width: `${f.weight}%` }} />)}
        </div>
        <ul className="stack" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {FACTORS.map((f) => (
            <li key={f.id}>
              <div className="row between">
                <h3>{f.label}{f.estimate ? <span className="badge">Estimate</span> : null}</h3>
                <strong>{f.weight}%</strong>
              </div>
              <div className="bar" style={{ margin: "6px 0" }} aria-hidden="true"><span style={{ width: `${f.weight * 4}%` }} /></div>
              <p className="small muted">{f.description}</p>
              <p className="caption">Source: {f.source}</p>
            </li>
          ))}
        </ul>
        <p className="small muted">Your preferences can make two checks count a little more. Activity is an estimate, not a live count.</p>
      </section>

      <section className="card stack-sm" aria-labelledby="whole-h">
        <h2 id="whole-h">2. The whole route matters</h2>
        <p className="muted">
          A 20-minute walk with 19 minutes of busy, lit streets can still have one empty 200 m stretch.
          An average would hide it, so we also look at the weakest stretch.
        </p>
        <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
          <li><strong>Coverage:</strong> the share of the walk within {CONTINUITY_RULES.coverageRadiusM} m of an open place, help point or active transit stop. Target {CONTINUITY_RULES.coverageTarget}%.</li>
          <li><strong>Longest gap:</strong> the longest stretch with nothing nearby. Anything over {CONTINUITY_RULES.gapLimitM} m lowers the score.</li>
          <li><strong>Lowest {CONTINUITY_RULES.windowM} m stretch:</strong> the weakest {CONTINUITY_RULES.windowM} m anywhere on the route.</li>
        </ul>
        <p className="banner small" style={{ fontFamily: "ui-monospace, monospace" }}>{SCORE_FORMULA}</p>
      </section>

      <section className="card stack-sm" aria-labelledby="src-h">
        <h2 id="src-h">3. Sources and freshness</h2>
        <p className="small muted">
          Every result shows when its data was fetched. If data is missing or old we say <strong>not sure</strong> instead of guessing.
        </p>
        <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
          <li><strong>Business listings and opening hours:</strong> public web pages, fetched live for your arrival time.</li>
          <li><strong>Streets and lighting tags:</strong> OpenStreetMap. Many streets have no lighting tag.</li>
          <li><strong>Streetlight outage reports:</strong> San Francisco 311, open reports only.</li>
          <li><strong>Past incidents:</strong> San Francisco open data. It can be late and uneven.</li>
          <li><strong>Transit:</strong> schedules are not connected yet, so transit shows as not sure.</li>
        </ul>
      </section>

      <section className="card stack-sm" aria-labelledby="limits-h">
        <h2 id="limits-h">4. Limits and privacy</h2>
        <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
          <li><strong>No cameras or tracking of people.</strong> Activity is estimated from open places and the time of day.</li>
          <li><strong>Opening hours can be wrong.</strong> Places close early, hours change, holidays differ.</li>
          <li><strong>Incident data can be unfair.</strong> It reflects policing as much as events, so it has a low weight (5%).</li>
          <li><strong>Missing data stays missing.</strong> We show &quot;not sure&quot; and never fill a blank with a guess.</li>
          <li><strong>AI can be wrong.</strong> The plain-language explanation is written by an AI from the numbers.</li>
          <li><strong>Your trip is temporary.</strong> It stays in this browser tab and is cleared when you close it. Sharing is optional.</li>
        </ul>
      </section>

      </div>
      <DisclaimerBanner />
      <a href="tel:911" className="btn secondary">Call 911</a>
      <Link href={backHref} className="btn primary">Return</Link>
    </div>
  );
}
