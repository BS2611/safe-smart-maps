import Link from "next/link";

import { AppHeader } from "./AppHeader";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { InstallTip } from "./InstallTip";
import { ClockIcon, InfoIcon, LocationOffIcon, RouteIcon, SearchIcon, StoreIcon } from "./Icons";
import { RouteIllustration } from "./RouteIllustration";

const POINTS = [
  { icon: <RouteIcon />, title: "Three routes", text: "Time and street conditions, side by side." },
  { icon: <StoreIcon />, title: "Reasons shown", text: "Open places, lighting, and gaps." },
  { icon: <ClockIcon />, title: "Time matters", text: "What's open when you arrive." },
];

export function WelcomeScreen({ locationOff = false }: { locationOff?: boolean }) {
  return (
    <div className="screen welcome">
      {locationOff ? (
        <div className="banner info row" role="status">
          <LocationOffIcon />
          <div>
            <strong>Location is off. Enter a starting point to continue.</strong>
            <p className="small muted">You can search any address or landmark without enabling GPS.</p>
          </div>
        </div>
      ) : null}
      <AppHeader />
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">For walks home after dark</p>
          <h1>See more of the walk ahead.</h1>
          <p className="lede">Compare a few walks for the hour you&apos;ll be out.</p>
          <p className="hero-note">
            Lighting, open places, main roads, and quiet gaps, scored stretch by stretch.
          </p>
          <div className="hero-actions">
            <Link href="/plan" className="btn primary">
              {locationOff ? <SearchIcon /> : null}
              {locationOff ? "Enter starting point" : "Get started"}
            </Link>
            <Link href="/how-scores-work" className="btn secondary">
              <InfoIcon /> How scores work
            </Link>
          </div>
          <p className="caption">You can type your start. GPS is optional.</p>
        </div>
        <RouteIllustration />
      </section>
      <ul className="feature-grid">
        {POINTS.map((p) => (
          <li key={p.title} className="card-row">
            <span className="card-icon">{p.icon}</span>
            <div>
              <h3>{p.title}</h3>
              <p className="small muted">{p.text}</p>
            </div>
          </li>
        ))}
      </ul>
      <div className="welcome-foot">
        <DisclaimerBanner />
        <InstallTip />
        <p className="caption center">This trip stays in this tab. Sharing is optional.</p>
      </div>
    </div>
  );
}
