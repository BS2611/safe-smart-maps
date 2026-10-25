import Link from "next/link";

import { AppHeader } from "./AppHeader";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { InstallTip } from "./InstallTip";
import { ClockIcon, InfoIcon, LocationOffIcon, RouteIcon, SearchIcon, StoreIcon } from "./Icons";
import { RouteIllustration } from "./RouteIllustration";

const POINTS = [
  { icon: <RouteIcon />, title: "Three routes", text: "Compare time and street conditions." },
  { icon: <StoreIcon />, title: "Reasons shown", text: "See open places, lighting, and gaps." },
  { icon: <ClockIcon />, title: "Time matters", text: "Check what's open when you arrive." },
];

export function WelcomeScreen({ locationOff = false }: { locationOff?: boolean }) {
  return (
    <div className="screen stack">
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
      <section className="stack-sm" style={{ padding: "0 4px" }}>
        <h1>See more of the walk ahead.</h1>
        <p className="muted">Compare walking routes for the time you&apos;ll be on the street.</p>
      </section>
      <RouteIllustration />
      <ul className="stack-sm" style={{ listStyle: "none", padding: 0, margin: 0 }}>
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
      <DisclaimerBanner />
      <InstallTip />
      <p className="caption center">Trip location is temporary. Sharing is optional.</p>
      <div className="card tight stack-sm">
        <Link href="/plan" className="btn primary">
          {locationOff ? <SearchIcon /> : null}
          {locationOff ? "Enter starting point" : "Get started"}
        </Link>
        <Link href="/how-scores-work" className="btn ghost">
          <InfoIcon /> How scores work
        </Link>
        <p className="caption center">You can enter your start manually.</p>
      </div>
    </div>
  );
}
